"""
Discovery Server Module - Peer Discovery & Registration
========================================================

Chức năng:
- Peer Registration (REGISTER): Peer đăng ký vào mạng
- Peer Lookup (LOOKUP): Tìm kiếm peer khác
- Heartbeat Mechanism: Kiểm tra peer còn online
- Peer Database: Quản lý danh sách peer
- Auto Cleanup: Xóa peer offline tự động

Architecture:
    Peer A ──┐
    Peer B ──┼─→ Discovery Server ←──┐
    Peer C ──┘                        │
             REGISTER, LOOKUP         │
             HEARTBEAT                └── Database

Protocol:
    REGISTER:  {type: 'register', peer_name, ip, port, fingerprint}
    LOOKUP:    {type: 'lookup', peer_name}
    HEARTBEAT: {type: 'heartbeat', peer_name}
    LIST:      {type: 'list_peers'}
"""

import logging
import socket
import threading
import time
import json
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from Code.P2PChat.src.message.protocol import encode_message, decode_message

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [DISCOVERY]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


@dataclass
class PeerInfo:
    """Thông tin của một Peer"""
    peer_name: str
    ip: str
    port: int
    fingerprint: str
    status: str = "online"  # online, offline
    last_heartbeat: float = field(default_factory=time.time)
    registered_at: datetime = field(default_factory=datetime.now)
    
    def is_alive(self, timeout: int = 30) -> bool:
        """Kiểm tra peer còn sống (heartbeat < timeout seconds)"""
        return time.time() - self.last_heartbeat < timeout
    
    def to_dict(self) -> dict:
        """Convert thành dict"""
        return {
            "peer_name": self.peer_name,
            "ip": self.ip,
            "port": self.port,
            "fingerprint": self.fingerprint,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at.isoformat()
        }


class DiscoveryServer:
    """
    Discovery Server - Quản lý peer registration & lookup
    
    Attributes:
        host: IP để binding
        port: Port để listening
        peers_db: Database lưu trữ peer info {peer_name -> PeerInfo}
        peers_lock: Lock cho thread-safe access
        server_running: Flag để control server
        heartbeat_timeout: Timeout để coi peer offline (seconds)
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5555, heartbeat_timeout: int = 30):
        self.host = host
        self.port = port
        self.heartbeat_timeout = heartbeat_timeout
        
        # Peer database
        self.peers_db: Dict[str, PeerInfo] = {}
        self.peers_lock = threading.Lock()
        
        # Server control
        self.server_running = False
        self.server_socket: Optional[socket.socket] = None
        
        logger.info(f"✓ Khởi tạo Discovery Server @ {host}:{port}")
    
    def start(self):
        """Khởi động discovery server"""
        thread = threading.Thread(target=self._run_server, daemon=True)
        thread.start()
        logger.info(f"✓ Discovery Server bắt đầu listening trên {self.host}:{self.port}")
    
    def _run_server(self):
        """Server thread - chấp nhận kết nối từ peer"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        self.server_running = True
        
        logger.info(f"[SERVER] Discovery Server listening on {self.host}:{self.port}")
        
        try:
            while self.server_running:
                try:
                    conn, addr = self.server_socket.accept()
                    logger.info(f"[SERVER] Nhận kết nối từ {addr}")
                    
                    # Xử lý request trên thread riêng
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"[SERVER] Lỗi accept: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def _handle_client(self, conn: socket.socket, addr: Tuple[str, int]):
        """Xử lý request từ peer"""
        try:
            request = decode_message(conn, timeout=5.0)
            request_type = request.get("type")
            
            if request_type == "register":
                response = self._handle_register(request)
            elif request_type == "lookup":
                response = self._handle_lookup(request)
            elif request_type == "heartbeat":
                response = self._handle_heartbeat(request)
            elif request_type == "list_peers":
                response = self._handle_list_peers()
            else:
                response = {"error": "Unknown request type"}
            
            # Gửi response
            conn.sendall(encode_message(response))
            logger.info(f"[RESPONSE] {addr}: {request_type} → {response.get('status', 'error')}")
        
        except Exception as e:
            logger.error(f"[ERROR] Xử lý client {addr}: {e}")
            try:
                error_response = {
                    "type": "error",
                    "error": str(e)
                }
                conn.sendall(encode_message(error_response))
            except:
                pass
        
        finally:
            try:
                conn.close()
            except:
                pass
    
    def _handle_register(self, request: dict) -> dict:
        """Xử lý REGISTER request"""
        peer_name = request.get("peer_name")
        ip = request.get("ip")
        port = request.get("port")
        fingerprint = request.get("fingerprint")
        
        # Validate input
        if not all([peer_name, ip, port, fingerprint]):
            return {
                "type": "error",
                "error": "Missing required fields: peer_name, ip, port, fingerprint"
            }
        
        # Register peer
        peer_info = PeerInfo(
            peer_name=peer_name,
            ip=ip,
            port=int(port),
            fingerprint=fingerprint
        )
        
        with self.peers_lock:
            self.peers_db[peer_name] = peer_info
        
        logger.info(f"[REGISTER] Peer '{peer_name}' đã đăng ký: {ip}:{port}")
        
        return {
            "type": "register_response",
            "status": "success",
            "peer_id": peer_name,
            "message": f"Peer '{peer_name}' registered successfully"
        }
    
    def _handle_lookup(self, request: dict) -> dict:
        """Xử lý LOOKUP request"""
        peer_name = request.get("peer_name")
        
        if not peer_name:
            return {"type": "error", "error": "Missing peer_name"}
        
        with self.peers_lock:
            peer = self.peers_db.get(peer_name)
        
        if not peer:
            logger.warning(f"[LOOKUP] Peer '{peer_name}' không tìm thấy")
            return {
                "type": "lookup_response",
                "status": "not_found",
                "error": f"Peer '{peer_name}' not found"
            }
        
        if not peer.is_alive(self.heartbeat_timeout):
            logger.warning(f"[LOOKUP] Peer '{peer_name}' offline")
            return {
                "type": "lookup_response",
                "status": "offline",
                "error": f"Peer '{peer_name}' is offline"
            }
        
        logger.info(f"[LOOKUP] Tìm thấy peer '{peer_name}': {peer.ip}:{peer.port}")
        
        return {
            "type": "lookup_response",
            "status": "found",
            "peer_name": peer.peer_name,
            "ip": peer.ip,
            "port": peer.port,
            "fingerprint": peer.fingerprint
        }
    
    def _handle_heartbeat(self, request: dict) -> dict:
        """Xử lý HEARTBEAT request"""
        peer_name = request.get("peer_name")
        
        if not peer_name:
            return {"type": "error", "error": "Missing peer_name"}
        
        with self.peers_lock:
            peer = self.peers_db.get(peer_name)
            if peer:
                peer.last_heartbeat = time.time()
                peer.status = "online"
        
        if not peer:
            logger.warning(f"[HEARTBEAT] Peer '{peer_name}' chưa register")
            return {
                "type": "heartbeat_response",
                "status": "not_registered",
                "error": f"Peer '{peer_name}' is not registered"
            }
        
        logger.debug(f"[HEARTBEAT] Nhận heartbeat từ '{peer_name}'")
        
        return {
            "type": "heartbeat_response",
            "status": "ack",
            "peer_name": peer_name,
            "timestamp": time.time()
        }
    
    def _handle_list_peers(self) -> dict:
        """Xử lý LIST_PEERS request"""
        with self.peers_lock:
            online_peers = [
                peer.to_dict()
                for peer in self.peers_db.values()
                if peer.is_alive(self.heartbeat_timeout)
            ]
        
        logger.info(f"[LIST_PEERS] Trả về {len(online_peers)} peer online")
        
        return {
            "type": "list_peers_response",
            "status": "success",
            "peers": online_peers,
            "count": len(online_peers)
        }
    
    def register_peer_local(self, peer_name: str, ip: str, port: int, fingerprint: str) -> bool:
        """
        Đăng ký peer locally (không qua network)
        Dùng cho testing/development
        """
        peer_info = PeerInfo(
            peer_name=peer_name,
            ip=ip,
            port=port,
            fingerprint=fingerprint
        )
        
        with self.peers_lock:
            self.peers_db[peer_name] = peer_info
        
        logger.info(f"[REGISTER_LOCAL] Peer '{peer_name}' đã đăng ký locally")
        return True
    
    def lookup_peer_local(self, peer_name: str) -> Optional[PeerInfo]:
        """
        Tìm peer locally (không qua network)
        Dùng cho testing/development
        """
        with self.peers_lock:
            peer = self.peers_db.get(peer_name)
        
        if peer and peer.is_alive(self.heartbeat_timeout):
            return peer
        
        return None
    
    def list_online_peers(self) -> List[PeerInfo]:
        """Danh sách peer online"""
        with self.peers_lock:
            return [
                peer for peer in self.peers_db.values()
                if peer.is_alive(self.heartbeat_timeout)
            ]
    
    def list_all_peers(self) -> List[PeerInfo]:
        """Danh sách tất cả peer (online + offline)"""
        with self.peers_lock:
            return list(self.peers_db.values())
    
    def remove_peer(self, peer_name: str) -> bool:
        """Xóa peer khỏi database"""
        with self.peers_lock:
            if peer_name in self.peers_db:
                del self.peers_db[peer_name]
                logger.info(f"[REMOVE] Peer '{peer_name}' đã xóa khỏi database")
                return True
        return False
    
    def cleanup_offline_peers(self) -> int:
        """Xóa tất cả peer offline"""
        with self.peers_lock:
            offline_peers = [
                name for name, peer in self.peers_db.items()
                if not peer.is_alive(self.heartbeat_timeout)
            ]
            for name in offline_peers:
                del self.peers_db[name]
        
        if offline_peers:
            logger.info(f"[CLEANUP] Xóa {len(offline_peers)} peer offline: {offline_peers}")
        
        return len(offline_peers)
    
    def get_peer_info(self, peer_name: str) -> Optional[dict]:
        """Lấy thông tin chi tiết của peer"""
        with self.peers_lock:
            peer = self.peers_db.get(peer_name)
        
        if peer:
            return peer.to_dict()
        return None
    
    def get_stats(self) -> dict:
        """Lấy thống kê server"""
        with self.peers_lock:
            total_peers = len(self.peers_db)
            online_peers = sum(
                1 for peer in self.peers_db.values()
                if peer.is_alive(self.heartbeat_timeout)
            )
        
        return {
            "host": self.host,
            "port": self.port,
            "total_peers": total_peers,
            "online_peers": online_peers,
            "offline_peers": total_peers - online_peers,
            "heartbeat_timeout": self.heartbeat_timeout
        }
    
    def shutdown(self):
        """Đóng discovery server"""
        logger.info("[SHUTDOWN] Đóng Discovery Server...")
        
        self.server_running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        with self.peers_lock:
            self.peers_db.clear()
        
        logger.info("[SHUTDOWN] Discovery Server đã tắt")


# ============================================================================
# CLIENT SIDE - Helper functions để connect tới discovery server
# ============================================================================

def register_with_discovery(
    discovery_host: str,
    discovery_port: int,
    peer_name: str,
    peer_ip: str,
    peer_port: int,
    fingerprint: str,
    timeout: float = 5.0
) -> dict:
    """
    Đăng ký peer với Discovery Server
    
    Returns:
        dict: Response từ server
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((discovery_host, discovery_port))
        
        request = {
            "type": "register",
            "peer_name": peer_name,
            "ip": peer_ip,
            "port": peer_port,
            "fingerprint": fingerprint
        }
        
        sock.sendall(encode_message(request))
        response = decode_message(sock, timeout=timeout)
        sock.close()
        
        logger.info(f"✓ Đã đăng ký với Discovery Server: {response}")
        return response
    
    except Exception as e:
        logger.error(f"✗ Lỗi đăng ký: {e}")
        return {"error": str(e)}


def lookup_peer_from_discovery(
    discovery_host: str,
    discovery_port: int,
    peer_name: str,
    timeout: float = 5.0
) -> dict:
    """
    Tìm peer từ Discovery Server
    
    Returns:
        dict: Thông tin peer (ip, port, fingerprint)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((discovery_host, discovery_port))
        
        request = {
            "type": "lookup",
            "peer_name": peer_name
        }
        
        sock.sendall(encode_message(request))
        response = decode_message(sock, timeout=timeout)
        sock.close()
        
        if response.get("status") == "found":
            logger.info(f"✓ Tìm thấy peer '{peer_name}': {response['ip']}:{response['port']}")
        else:
            logger.warning(f"✗ Peer '{peer_name}' không tìm thấy hoặc offline")
        
        return response
    
    except Exception as e:
        logger.error(f"✗ Lỗi lookup: {e}")
        return {"error": str(e)}


def send_heartbeat_to_discovery(
    discovery_host: str,
    discovery_port: int,
    peer_name: str,
    timeout: float = 5.0
) -> dict:
    """
    Gửi heartbeat tới Discovery Server
    
    Returns:
        dict: Response từ server
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((discovery_host, discovery_port))
        
        request = {
            "type": "heartbeat",
            "peer_name": peer_name
        }
        
        sock.sendall(encode_message(request))
        response = decode_message(sock, timeout=timeout)
        sock.close()
        
        logger.debug(f"✓ Heartbeat gửi tới Discovery Server")
        return response
    
    except Exception as e:
        logger.error(f"✗ Lỗi gửi heartbeat: {e}")
        return {"error": str(e)}


def list_peers_from_discovery(
    discovery_host: str,
    discovery_port: int,
    timeout: float = 5.0
) -> dict:
    """
    Lấy danh sách peer từ Discovery Server
    
    Returns:
        dict: Danh sách peer online
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((discovery_host, discovery_port))
        
        request = {
            "type": "list_peers"
        }
        
        sock.sendall(encode_message(request))
        response = decode_message(sock, timeout=timeout)
        sock.close()
        
        if response.get("status") == "success":
            peers = response.get("peers", [])
            logger.info(f"✓ Tìm thấy {len(peers)} peer online")
        
        return response
    
    except Exception as e:
        logger.error(f"✗ Lỗi list peers: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Demo: Start discovery server
    print("\n" + "="*60)
    print("  Discovery Server Demo")
    print("="*60 + "\n")
    
    server = DiscoveryServer(host="127.0.0.1", port=5555, heartbeat_timeout=30)
    server.start()
    
    print("Discovery Server đang chạy trên 127.0.0.1:5555")
    print("Nhấn Ctrl+C để thoát\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nĐóng server...")
        server.shutdown()
