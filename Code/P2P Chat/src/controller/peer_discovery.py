import json
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

DISCOVERY_PORT = 37020
DEFAULT_DISCOVERY_INTERVAL = 5.0
DEFAULT_PEER_TIMEOUT = 15.0
MAX_PACKET_SIZE = 4096

DISCOVER_PEER = "DISCOVER_PEER"
PEER_INFO = "PEER_INFO"


@dataclass
class Peer:
    peer_id: str
    username: str
    ip: str
    tcp_port: int
    last_seen: float

    def to_dict(self) -> dict:
        return {
            "peer_id": self.peer_id,
            "username": self.username,
            "ip": self.ip,
            "tcp_port": self.tcp_port,
            "last_seen": self.last_seen,
        }


class PeerDiscovery:
    """UDP LAN peer discovery. Independent from the GUI and TCP chat layer."""

    def __init__(
        self,
        username: str,
        tcp_port: int,
        discovery_port: int = DISCOVERY_PORT,
        discovery_interval: float = DEFAULT_DISCOVERY_INTERVAL,
        peer_timeout: float = DEFAULT_PEER_TIMEOUT,
        peer_id: Optional[str] = None,
        on_peer_discovered: Optional[Callable[[Peer], None]] = None,
        on_peer_updated: Optional[Callable[[Peer], None]] = None,
        on_peer_removed: Optional[Callable[[Peer], None]] = None,
    ):
        self.username = username
        self.tcp_port = int(tcp_port)
        self.discovery_port = int(discovery_port)
        self.discovery_interval = float(discovery_interval)
        self.peer_timeout = float(peer_timeout)
        self.peer_id = peer_id or str(uuid.uuid4())

        self.on_peer_discovered = on_peer_discovered
        self.on_peer_updated = on_peer_updated
        self.on_peer_removed = on_peer_removed

        self._socket: Optional[socket.socket] = None
        self._running = False
        self._listener_thread = None
        self._heartbeat_thread = None
        self._peers: Dict[str, Peer] = {}
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._running:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self.discovery_port))
        sock.settimeout(1.0)

        self._socket = sock
        self._running = True
        self._listener_thread = threading.Thread(
            target=self._listen_loop, name="PeerDiscoveryListener", daemon=True
        )
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, name="PeerDiscoveryHeartbeat", daemon=True
        )
        self._listener_thread.start()
        self._heartbeat_thread.start()
        self.broadcast_discovery()

    def stop(self) -> None:
        self._running = False
        sock = self._socket
        self._socket = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        for thread in (self._listener_thread, self._heartbeat_thread):
            if thread and thread.is_alive():
                thread.join(timeout=2)
        self._listener_thread = None
        self._heartbeat_thread = None

    def broadcast_discovery(self) -> None:
        self._send_packet(
            {
                "type": DISCOVER_PEER,
                "peer_id": self.peer_id,
                "username": self.username,
                "tcp_port": self.tcp_port,
            },
            ("255.255.255.255", self.discovery_port),
        )

    def get_peers(self) -> List[Peer]:
        with self._lock:
            return list(self._peers.values())

    def get_peer(self, peer_id: str) -> Optional[Peer]:
        with self._lock:
            return self._peers.get(peer_id)

    def clear_peers(self) -> None:
        with self._lock:
            self._peers.clear()

    def _listen_loop(self) -> None:
        while self._running:
            sock = self._socket
            if sock is None:
                break
            try:
                data, addr = sock.recvfrom(MAX_PACKET_SIZE)
            except socket.timeout:
                self._remove_expired_peers()
                continue
            except OSError:
                break
            self._handle_packet(data, addr)

    def _handle_packet(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            packet = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(packet, dict):
            return
        packet_type = packet.get("type")
        peer_id = packet.get("peer_id")
        if not isinstance(peer_id, str) or not peer_id or peer_id == self.peer_id:
            return
        if packet_type == DISCOVER_PEER:
            self._handle_discover(packet, addr[0])
        elif packet_type == PEER_INFO:
            self._handle_peer_info(packet, addr[0])

    def _handle_discover(self, packet: dict, sender_ip: str) -> None:
        tcp_port = self._safe_port(packet.get("tcp_port"))
        username = str(packet.get("username") or packet["peer_id"])
        self._upsert_peer(packet["peer_id"], username, sender_ip, tcp_port)
        self._send_packet(
            {
                "type": PEER_INFO,
                "peer_id": self.peer_id,
                "username": self.username,
                "tcp_port": self.tcp_port,
            },
            (sender_ip, self.discovery_port),
        )

    def _handle_peer_info(self, packet: dict, sender_ip: str) -> None:
        tcp_port = self._safe_port(packet.get("tcp_port"))
        self._upsert_peer(
            packet["peer_id"],
            str(packet.get("username") or packet["peer_id"]),
            sender_ip,
            tcp_port,
        )

    @staticmethod
    def _safe_port(value) -> int:
        try:
            port = int(value)
            return port if 1 <= port <= 65535 else 0
        except (TypeError, ValueError):
            return 0

    def _upsert_peer(self, peer_id: str, username: str, ip: str, tcp_port: int) -> None:
        now = time.time()
        with self._lock:
            old_peer = self._peers.get(peer_id)
            peer = Peer(peer_id, username, ip, tcp_port, now)
            self._peers[peer_id] = peer

        callback = self.on_peer_discovered if old_peer is None else self.on_peer_updated
        if callback:
            callback(peer)

    def _remove_expired_peers(self) -> None:
        now = time.time()
        removed = []
        with self._lock:
            for peer_id, peer in list(self._peers.items()):
                if now - peer.last_seen > self.peer_timeout:
                    removed.append(self._peers.pop(peer_id))
        if self.on_peer_removed:
            for peer in removed:
                self.on_peer_removed(peer)

    def _send_packet(self, packet: dict, address: Tuple[str, int]) -> None:
        sock = self._socket
        if sock is None:
            return
        data = json.dumps(packet, ensure_ascii=False).encode("utf-8")
        if len(data) > MAX_PACKET_SIZE:
            raise ValueError("UDP discovery packet too large")
        try:
            sock.sendto(data, address)
        except OSError:
            if self._running:
                raise

    def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                self.broadcast_discovery()
            except OSError:
                if not self._running:
                    break
            end = time.time() + self.discovery_interval
            while self._running and time.time() < end:
                time.sleep(0.1)
