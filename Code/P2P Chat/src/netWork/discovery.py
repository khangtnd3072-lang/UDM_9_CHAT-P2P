"""
Discovery Server Module - Peer Discovery & Registration
========================================================

Chức năng:
- Peer Registration (REGISTER): Peer đăng ký vào mạng
- Peer Lookup (LOOKUP): Tìm kiếm peer khác
- Heartbeat Mechanism: Kiểm tra peer còn online
- Peer Database: Quản lý danh sách peer
- Auto Cleanup: Xóa peer offline tự động
- LIST_PEERS: Lấy danh sách peer đang online

Architecture:
    Peer A ──┐
    Peer B ──┼─→ Discovery Server ←── Peer C
    Peer C ──┘
             │
             ├── REGISTER
             ├── LOOKUP
             ├── HEARTBEAT
             └── LIST_PEERS

Protocol:
    REGISTER:
        {
            "type": "register",
            "peer_name": "...",
            "ip": "...",
            "port": 5000,
            "fingerprint": "..."
        }

    LOOKUP:
        {
            "type": "lookup",
            "peer_name": "..."
        }

    HEARTBEAT:
        {
            "type": "heartbeat",
            "peer_name": "..."
        }

    LIST_PEERS:
        {
            "type": "list_peers"
        }
"""

import socket
import threading
import time
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# IMPORT COMMON PROTOCOL
# ============================================================================
#
# Project structure:
#
# Code/
# ├── common/
# │   └── protocol.py
# │
# └── P2P Chat/
#     └── src/
#         └── netWork/
#             └── discovery.py
#
# Khi chạy project từ root, common.protocol có thể được import trực tiếp.
# Phần fallback bên dưới giúp module vẫn tìm được Code/common khi cần.
# ============================================================================

try:
    from common.protocol import encode_message, decode_message
except ModuleNotFoundError:
    CODE_ROOT = Path(__file__).resolve().parents[3]

    if str(CODE_ROOT) not in sys.path:
        sys.path.insert(0, str(CODE_ROOT))

    from common.protocol import encode_message, decode_message


# ============================================================================
# PROJECT CONFIG + LOGGING
# ============================================================================

from ..config import (
    DISCOVERY_SERVER_HOST,
    DISCOVERY_SERVER_PORT,
)

from ..logging_config import (
    get_discovery_server_logger,
)


logger = get_discovery_server_logger()


# ============================================================================
# PEER INFO
# ============================================================================

@dataclass
class PeerInfo:
    """
    Thông tin của một Peer đã đăng ký với Discovery Server.
    """

    peer_name: str
    ip: str
    port: int
    fingerprint: str

    status: str = "online"

    last_heartbeat: float = field(
        default_factory=time.time
    )

    registered_at: datetime = field(
        default_factory=datetime.now
    )

    def is_alive(self, timeout: int = 30) -> bool:
        """
        Kiểm tra peer còn online dựa trên thời gian heartbeat gần nhất.

        Returns:
            True  -> peer vẫn online
            False -> peer đã timeout
        """

        return (
            time.time() - self.last_heartbeat
        ) < timeout

    def update_heartbeat(self) -> None:
        """
        Cập nhật thời gian heartbeat mới nhất.
        """

        self.last_heartbeat = time.time()
        self.status = "online"

    def to_dict(self) -> dict:
        """
        Chuyển thông tin peer thành dictionary.

        Fingerprint vẫn được trả về trong protocol response
        khi cần thiết, nhưng KHÔNG được ghi vào log.
        """

        return {
            "peer_name": self.peer_name,
            "ip": self.ip,
            "port": self.port,
            "fingerprint": self.fingerprint,
            "status": self.status,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at.isoformat(),
        }


# ============================================================================
# DISCOVERY SERVER
# ============================================================================

class DiscoveryServer:
    """
    Discovery Server.

    Chức năng chính:
        - REGISTER
        - LOOKUP
        - HEARTBEAT
        - LIST_PEERS
        - Auto cleanup peer offline

    IP và port mặc định được lấy từ config.py/config.json.
    """

    def __init__(
        self,
        host: str = DISCOVERY_SERVER_HOST,
        port: int = DISCOVERY_SERVER_PORT,
        heartbeat_timeout: int = 30,
        cleanup_interval: int = 5,
    ):
        self.host = host
        self.port = int(port)

        self.heartbeat_timeout = int(
            heartbeat_timeout
        )

        self.cleanup_interval = int(
            cleanup_interval
        )

        # ------------------------------------------------------------
        # Peer database
        # ------------------------------------------------------------

        self.peers_db: Dict[str, PeerInfo] = {}

        self.peers_lock = threading.Lock()

        # ------------------------------------------------------------
        # Server control
        # ------------------------------------------------------------

        self.server_running = False

        self.server_socket: Optional[socket.socket] = None

        self.server_thread: Optional[
            threading.Thread
        ] = None

        self.cleanup_thread: Optional[
            threading.Thread
        ] = None

        # ------------------------------------------------------------
        # Logging
        # ------------------------------------------------------------

        logger.info(
            "Discovery Server initialized at %s:%s",
            self.host,
            self.port,
        )

    # ========================================================================
    # START SERVER
    # ========================================================================

    def start(self) -> bool:
        """
        Khởi động Discovery Server.

        Returns:
            True nếu thread server được khởi động.
        """

        if self.server_running:
            logger.warning(
                "Discovery Server đã đang chạy tại %s:%s",
                self.host,
                self.port,
            )
            return False

        self.server_thread = threading.Thread(
            target=self._run_server,
            name="DiscoveryServer",
            daemon=True,
        )

        self.server_thread.start()

        # Thread cleanup riêng
        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            name="DiscoveryCleanup",
            daemon=True,
        )

        self.cleanup_thread.start()

        logger.info(
            "Discovery Server start requested at %s:%s",
            self.host,
            self.port,
        )

        return True

    # ========================================================================
    # SERVER LOOP
    # ========================================================================

    def _run_server(self) -> None:
        """
        Thread chính của Discovery Server.
        """

        try:
            self.server_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )

            self.server_socket.setsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR,
                1,
            )

            # Timeout để server có thể kiểm tra server_running
            self.server_socket.settimeout(1.0)

            self.server_socket.bind(
                (self.host, self.port)
            )

            self.server_socket.listen(10)

            self.server_running = True

            logger.info(
                "[SERVER] Discovery Server listening on %s:%s",
                self.host,
                self.port,
            )

            while self.server_running:

                try:
                    conn, addr = self.server_socket.accept()

                except socket.timeout:
                    continue

                except OSError:

                    if self.server_running:
                        logger.exception(
                            "[SERVER] Socket accept error"
                        )

                    break

                except Exception:

                    logger.exception(
                        "[SERVER] Unexpected accept error"
                    )

                    continue

                logger.info(
                    "[CONNECT] Client connected from %s:%s",
                    addr[0],
                    addr[1],
                )

                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr),
                    name=f"DiscoveryClient-{addr[0]}-{addr[1]}",
                    daemon=True,
                )

                client_thread.start()

        except OSError as exc:

            self.server_running = False

            logger.error(
                "[SERVER] Cannot start Discovery Server at %s:%s: %s",
                self.host,
                self.port,
                exc,
            )

        except Exception:

            self.server_running = False

            logger.exception(
                "[SERVER] Fatal Discovery Server error"
            )

        finally:

            if self.server_socket is not None:

                try:
                    self.server_socket.close()
                except OSError:
                    pass

                self.server_socket = None

            self.server_running = False

            logger.info(
                "[SERVER] Discovery Server thread stopped"
            )

    # ========================================================================
    # CLIENT HANDLER
    # ========================================================================

    def _handle_client(
        self,
        conn: socket.socket,
        addr: Tuple[str, int],
    ) -> None:
        """
        Xử lý một request từ client/peer.
        """

        request_type = "unknown"

        try:
            # --------------------------------------------------------
            # Socket timeout
            # --------------------------------------------------------

            conn.settimeout(5.0)

            # --------------------------------------------------------
            # Receive request
            # --------------------------------------------------------

            request = decode_message(conn)

            if not isinstance(request, dict):

                response = {
                    "type": "error",
                    "status": "error",
                    "error": "Invalid request format",
                }

                conn.sendall(
                    encode_message(response)
                )

                logger.warning(
                    "[REQUEST] Invalid request format from %s:%s",
                    addr[0],
                    addr[1],
                )

                return

            request_type = request.get(
                "type",
                "unknown",
            )

            # --------------------------------------------------------
            # Dispatch request
            # --------------------------------------------------------

            if request_type == "register":

                response = self._handle_register(
                    request
                )

            elif request_type == "lookup":

                response = self._handle_lookup(
                    request
                )

            elif request_type == "heartbeat":

                response = self._handle_heartbeat(
                    request
                )

            elif request_type == "list_peers":

                response = self._handle_list_peers()

            else:

                response = {
                    "type": "error",
                    "status": "error",
                    "error": (
                        f"Unknown request type: "
                        f"{request_type}"
                    ),
                }

                logger.warning(
                    "[REQUEST] Unknown request type '%s' from %s:%s",
                    request_type,
                    addr[0],
                    addr[1],
                )

            # --------------------------------------------------------
            # Send response
            # --------------------------------------------------------

            conn.sendall(
                encode_message(response)
            )

            logger.info(
                "[RESPONSE] %s:%s request=%s status=%s",
                addr[0],
                addr[1],
                request_type,
                response.get("status", "error"),
            )

        except socket.timeout:

            logger.warning(
                "[TIMEOUT] Client %s:%s request=%s timed out",
                addr[0],
                addr[1],
                request_type,
            )

            self._send_error(
                conn,
                "Request timeout",
            )

        except Exception as exc:

            logger.error(
                "[ERROR] Client %s:%s request=%s failed: %s",
                addr[0],
                addr[1],
                request_type,
                exc,
            )

            self._send_error(
                conn,
                "Request processing failed",
            )

        finally:

            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                conn.close()
            except OSError:
                pass

            logger.info(
                "[DISCONNECT] Client disconnected from %s:%s",
                addr[0],
                addr[1],
            )

    # ========================================================================
    # ERROR RESPONSE
    # ========================================================================

    @staticmethod
    def _send_error(
        conn: socket.socket,
        message: str,
    ) -> None:
        """
        Gửi error response.

        Không đưa exception nội bộ vào response để tránh
        làm lộ thông tin implementation.
        """

        try:

            response = {
                "type": "error",
                "status": "error",
                "error": message,
            }

            conn.sendall(
                encode_message(response)
            )

        except Exception:
            pass

    # ========================================================================
    # REGISTER
    # ========================================================================

    def _handle_register(
        self,
        request: dict,
    ) -> dict:
        """
        REGISTER peer vào Discovery Server.
        """

        peer_name = request.get("peer_name")
        ip = request.get("ip")
        port = request.get("port")
        fingerprint = request.get("fingerprint")

        # ------------------------------------------------------------
        # Validate required fields
        # ------------------------------------------------------------

        if not peer_name:
            logger.warning(
                "[REGISTER] Missing peer_name"
            )

            return {
                "type": "register_response",
                "status": "error",
                "error": "Missing peer_name",
            }

        if not ip:
            logger.warning(
                "[REGISTER] Peer '%s' missing IP",
                peer_name,
            )

            return {
                "type": "register_response",
                "status": "error",
                "error": "Missing ip",
            }

        if port is None:
            logger.warning(
                "[REGISTER] Peer '%s' missing port",
                peer_name,
            )

            return {
                "type": "register_response",
                "status": "error",
                "error": "Missing port",
            }

        if not fingerprint:
            logger.warning(
                "[REGISTER] Peer '%s' missing fingerprint",
                peer_name,
            )

            return {
                "type": "register_response",
                "status": "error",
                "error": "Missing fingerprint",
            }

        # ------------------------------------------------------------
        # Validate port
        # ------------------------------------------------------------

        try:
            port = int(port)

        except (TypeError, ValueError):

            logger.warning(
                "[REGISTER] Peer '%s' supplied invalid port",
                peer_name,
            )

            return {
                "type": "register_response",
                "status": "error",
                "error": "Port must be an integer",
            }

        if not (1 <= port <= 65535):

            logger.warning(
                "[REGISTER] Peer '%s' supplied out-of-range port",
                peer_name,
            )

            return {
                "type": "register_response",
                "status": "error",
                "error": "Port must be between 1 and 65535",
            }

        # ------------------------------------------------------------
        # Register peer
        # ------------------------------------------------------------

        peer_info = PeerInfo(
            peer_name=str(peer_name),
            ip=str(ip),
            port=port,
            fingerprint=str(fingerprint),
        )

        with self.peers_lock:

            is_update = peer_name in self.peers_db

            self.peers_db[
                peer_name
            ] = peer_info

        if is_update:

            logger.info(
                "[REGISTER] Peer '%s' registration updated at %s:%s",
                peer_name,
                ip,
                port,
            )

        else:

            logger.info(
                "[REGISTER] Peer '%s' registered at %s:%s",
                peer_name,
                ip,
                port,
            )

        # Không log fingerprint.

        return {
            "type": "register_response",
            "status": "success",
            "peer_id": peer_name,
            "message": (
                f"Peer '{peer_name}' "
                "registered successfully"
            ),
        }

    # ========================================================================
    # LOOKUP
    # ========================================================================

    def _handle_lookup(
        self,
        request: dict,
    ) -> dict:
        """
        Tìm peer theo peer_name.
        """

        peer_name = request.get("peer_name")

        if not peer_name:

            logger.warning(
                "[LOOKUP] Missing peer_name"
            )

            return {
                "type": "lookup_response",
                "status": "error",
                "error": "Missing peer_name",
            }

        with self.peers_lock:
            peer = self.peers_db.get(peer_name)

        if peer is None:

            logger.info(
                "[LOOKUP] Peer '%s' not found",
                peer_name,
            )

            return {
                "type": "lookup_response",
                "status": "not_found",
                "error": (
                    f"Peer '{peer_name}' not found"
                ),
            }

        # ------------------------------------------------------------
        # Check heartbeat
        # ------------------------------------------------------------

        if not peer.is_alive(
            self.heartbeat_timeout
        ):

            with self.peers_lock:

                if peer_name in self.peers_db:
                    self.peers_db[
                        peer_name
                    ].status = "offline"

            logger.info(
                "[LOOKUP] Peer '%s' offline",
                peer_name,
            )

            return {
                "type": "lookup_response",
                "status": "offline",
                "error": (
                    f"Peer '{peer_name}' is offline"
                ),
            }

        logger.info(
            "[LOOKUP] Peer '%s' found at %s:%s",
            peer_name,
            peer.ip,
            peer.port,
        )

        # Không ghi fingerprint vào log.
        return {
            "type": "lookup_response",
            "status": "found",
            "peer_name": peer.peer_name,
            "ip": peer.ip,
            "port": peer.port,
            "fingerprint": peer.fingerprint,
        }

    # ========================================================================
    # HEARTBEAT
    # ========================================================================

    def _handle_heartbeat(
        self,
        request: dict,
    ) -> dict:
        """
        Cập nhật heartbeat của peer.
        """

        peer_name = request.get("peer_name")

        if not peer_name:

            logger.warning(
                "[HEARTBEAT] Missing peer_name"
            )

            return {
                "type": "heartbeat_response",
                "status": "error",
                "error": "Missing peer_name",
            }

        with self.peers_lock:

            peer = self.peers_db.get(peer_name)

            if peer is not None:
                peer.update_heartbeat()

        if peer is None:

            logger.warning(
                "[HEARTBEAT] Peer '%s' not registered",
                peer_name,
            )

            return {
                "type": "heartbeat_response",
                "status": "not_registered",
                "error": (
                    f"Peer '{peer_name}' "
                    "is not registered"
                ),
            }

        logger.debug(
            "[HEARTBEAT] Received heartbeat from '%s'",
            peer_name,
        )

        return {
            "type": "heartbeat_response",
            "status": "ack",
            "peer_name": peer_name,
            "timestamp": time.time(),
        }

    # ========================================================================
    # LIST PEERS
    # ========================================================================

    def _handle_list_peers(self) -> dict:
        """
        Trả về danh sách peer đang online.
        """

        with self.peers_lock:

            online_peers = []

            for peer in self.peers_db.values():

                if peer.is_alive(
                    self.heartbeat_timeout
                ):

                    peer.status = "online"

                    online_peers.append(
                        peer.to_dict()
                    )

                else:

                    peer.status = "offline"

        logger.info(
            "[LIST_PEERS] Returning %d online peers",
            len(online_peers),
        )

        return {
            "type": "list_peers_response",
            "status": "success",
            "peers": online_peers,
            "count": len(online_peers),
        }

    # ========================================================================
    # LOCAL HELPERS
    # ========================================================================

    def register_peer_local(
        self,
        peer_name: str,
        ip: str,
        port: int,
        fingerprint: str,
    ) -> bool:
        """
        Đăng ký peer trực tiếp vào database.

        Dùng chủ yếu cho test/development.
        """

        try:
            port = int(port)

        except (TypeError, ValueError):

            logger.warning(
                "[REGISTER_LOCAL] Invalid port"
            )

            return False

        if not (1 <= port <= 65535):

            logger.warning(
                "[REGISTER_LOCAL] Port out of range"
            )

            return False

        peer_info = PeerInfo(
            peer_name=str(peer_name),
            ip=str(ip),
            port=port,
            fingerprint=str(fingerprint),
        )

        with self.peers_lock:

            self.peers_db[
                peer_name
            ] = peer_info

        logger.info(
            "[REGISTER_LOCAL] Peer '%s' registered locally",
            peer_name,
        )

        return True

    def lookup_peer_local(
        self,
        peer_name: str,
    ) -> Optional[PeerInfo]:
        """
        Tìm peer trực tiếp trong database.
        """

        with self.peers_lock:
            peer = self.peers_db.get(peer_name)

        if peer is None:
            return None

        if peer.is_alive(
            self.heartbeat_timeout
        ):

            return peer

        return None

    def list_online_peers(self) -> List[PeerInfo]:
        """
        Trả về danh sách peer online.
        """

        with self.peers_lock:

            return [
                peer
                for peer in self.peers_db.values()
                if peer.is_alive(
                    self.heartbeat_timeout
                )
            ]

    def list_all_peers(self) -> List[PeerInfo]:
        """
        Trả về tất cả peer.
        """

        with self.peers_lock:
            return list(
                self.peers_db.values()
            )

    def remove_peer(
        self,
        peer_name: str,
    ) -> bool:
        """
        Xóa peer khỏi database.
        """

        with self.peers_lock:

            if peer_name not in self.peers_db:
                return False

            del self.peers_db[
                peer_name
            ]

        logger.info(
            "[REMOVE] Peer '%s' removed from database",
            peer_name,
        )

        return True

    # ========================================================================
    # AUTO CLEANUP
    # ========================================================================

    def cleanup_offline_peers(self) -> int:
        """
        Xóa tất cả peer đã timeout heartbeat.

        Returns:
            Số lượng peer đã bị xóa.
        """

        removed = []

        with self.peers_lock:

            for peer_name, peer in list(
                self.peers_db.items()
            ):

                if not peer.is_alive(
                    self.heartbeat_timeout
                ):

                    peer.status = "offline"

                    removed.append(
                        peer_name
                    )

                    del self.peers_db[
                        peer_name
                    ]

        if removed:

            logger.info(
                "[CLEANUP] Removed %d offline peer(s)",
                len(removed),
            )

        return len(removed)

    def _cleanup_loop(self) -> None:
        """
        Background thread tự động cleanup peer offline.
        """

        while self.server_running:

            time.sleep(
                self.cleanup_interval
            )

            if not self.server_running:
                break

            try:

                self.cleanup_offline_peers()

            except Exception:

                logger.exception(
                    "[CLEANUP] Cleanup error"
                )

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_peer_info(
        self,
        peer_name: str,
    ) -> Optional[dict]:
        """
        Lấy thông tin chi tiết của peer.
        """

        with self.peers_lock:

            peer = self.peers_db.get(
                peer_name
            )

            if peer is None:
                return None

            return peer.to_dict()

    def get_stats(self) -> dict:
        """
        Thống kê Discovery Server.
        """

        with self.peers_lock:

            total_peers = len(
                self.peers_db
            )

            online_peers = sum(
                1
                for peer in self.peers_db.values()
                if peer.is_alive(
                    self.heartbeat_timeout
                )
            )

        return {
            "host": self.host,
            "port": self.port,
            "total_peers": total_peers,
            "online_peers": online_peers,
            "offline_peers": (
                total_peers - online_peers
            ),
            "heartbeat_timeout": (
                self.heartbeat_timeout
            ),
            "server_running": (
                self.server_running
            ),
        }

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    def shutdown(self) -> None:
        """
        Tắt Discovery Server sạch.
        """

        logger.info(
            "[SHUTDOWN] Shutting down Discovery Server"
        )

        self.server_running = False

        # ------------------------------------------------------------
        # Close server socket
        # ------------------------------------------------------------

        if self.server_socket is not None:

            try:
                self.server_socket.close()
            except OSError:
                pass

            self.server_socket = None

        # ------------------------------------------------------------
        # Clear peer database
        # ------------------------------------------------------------

        with self.peers_lock:
            self.peers_db.clear()

        logger.info(
            "[SHUTDOWN] Discovery Server stopped"
        )


# ============================================================================
# CLIENT SIDE HELPERS
# ============================================================================

def _send_discovery_request(
    discovery_host: str,
    discovery_port: int,
    request: dict,
    timeout: float = 5.0,
) -> dict:
    """
    Hàm dùng chung để gửi request tới Discovery Server.

    Lưu ý:
        decode_message() của common.protocol.py không nhận
        tham số timeout.

        Vì vậy timeout được đặt trực tiếp trên socket trước
        khi gọi decode_message().
    """

    sock: Optional[socket.socket] = None

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        )

        sock.settimeout(timeout)

        sock.connect(
            (
                discovery_host,
                int(discovery_port),
            )
        )

        sock.sendall(
            encode_message(request)
        )

        response = decode_message(sock)

        if not isinstance(response, dict):

            return {
                "type": "error",
                "status": "error",
                "error": "Invalid response from Discovery Server",
            }

        return response

    except socket.timeout:

        logger.error(
            "[DISCOVERY_CLIENT] Request timeout"
        )

        return {
            "type": "error",
            "status": "error",
            "error": "Discovery Server request timeout",
        }

    except ConnectionRefusedError:

        logger.error(
            "[DISCOVERY_CLIENT] Connection refused"
        )

        return {
            "type": "error",
            "status": "error",
            "error": "Discovery Server unavailable",
        }

    except Exception as exc:

        logger.error(
            "[DISCOVERY_CLIENT] Request failed: %s",
            exc,
        )

        return {
            "type": "error",
            "status": "error",
            "error": "Discovery Server request failed",
        }

    finally:

        if sock is not None:

            try:
                sock.shutdown(
                    socket.SHUT_RDWR
                )
            except OSError:
                pass

            try:
                sock.close()
            except OSError:
                pass


# ============================================================================
# REGISTER CLIENT
# ============================================================================

def register_with_discovery(
    discovery_host: str,
    discovery_port: int,
    peer_name: str,
    peer_ip: str,
    peer_port: int,
    fingerprint: str,
    timeout: float = 5.0,
) -> dict:
    """
    Đăng ký peer với Discovery Server.
    """

    request = {
        "type": "register",
        "peer_name": peer_name,
        "ip": peer_ip,
        "port": peer_port,
        "fingerprint": fingerprint,
    }

    response = _send_discovery_request(
        discovery_host,
        discovery_port,
        request,
        timeout,
    )

    logger.info(
        "[REGISTER_CLIENT] status=%s",
        response.get("status", "error"),
    )

    return response


# ============================================================================
# LOOKUP CLIENT
# ============================================================================

def lookup_peer_from_discovery(
    discovery_host: str,
    discovery_port: int,
    peer_name: str,
    timeout: float = 5.0,
) -> dict:
    """
    Tìm peer từ Discovery Server.
    """

    request = {
        "type": "lookup",
        "peer_name": peer_name,
    }

    response = _send_discovery_request(
        discovery_host,
        discovery_port,
        request,
        timeout,
    )

    if response.get("status") == "found":

        logger.info(
            "[LOOKUP_CLIENT] Peer '%s' found at %s:%s",
            peer_name,
            response.get("ip"),
            response.get("port"),
        )

    else:

        logger.warning(
            "[LOOKUP_CLIENT] Peer '%s' not found or offline",
            peer_name,
        )

    return response


# ============================================================================
# HEARTBEAT CLIENT
# ============================================================================

def send_heartbeat_to_discovery(
    discovery_host: str,
    discovery_port: int,
    peer_name: str,
    timeout: float = 5.0,
) -> dict:
    """
    Gửi heartbeat tới Discovery Server.
    """

    request = {
        "type": "heartbeat",
        "peer_name": peer_name,
    }

    response = _send_discovery_request(
        discovery_host,
        discovery_port,
        request,
        timeout,
    )

    if response.get("status") == "ack":

        logger.debug(
            "[HEARTBEAT_CLIENT] Heartbeat acknowledged"
        )

    else:

        logger.warning(
            "[HEARTBEAT_CLIENT] Heartbeat failed"
        )

    return response


# ============================================================================
# LIST PEERS CLIENT
# ============================================================================

def list_peers_from_discovery(
    discovery_host: str,
    discovery_port: int,
    timeout: float = 5.0,
) -> dict:
    """
    Lấy danh sách peer online từ Discovery Server.
    """

    request = {
        "type": "list_peers",
    }

    response = _send_discovery_request(
        discovery_host,
        discovery_port,
        request,
        timeout,
    )

    if response.get("status") == "success":

        logger.info(
            "[LIST_CLIENT] Received %d online peer(s)",
            response.get("count", 0),
        )

    else:

        logger.warning(
            "[LIST_CLIENT] Failed to get peer list"
        )

    return response


# ============================================================================
# DEMO
# ============================================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("  Discovery Server Demo")
    print("=" * 60)
    print()

    print(
        f"Host : {DISCOVERY_SERVER_HOST}"
    )

    print(
        f"Port : {DISCOVERY_SERVER_PORT}"
    )

    print()

    server = DiscoveryServer()

    if not server.start():

        print(
            "Discovery Server không thể khởi động."
        )

        sys.exit(1)

    print(
        "Discovery Server đang chạy..."
    )

    print(
        f"Listening: "
        f"{DISCOVERY_SERVER_HOST}:"
        f"{DISCOVERY_SERVER_PORT}"
    )

    print(
        "Nhấn Ctrl+C để thoát."
    )

    print()

    try:

        while server.server_running:

            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print(
            "Đang đóng Discovery Server..."
        )

    finally:

        server.shutdown()

        print(
            "Discovery Server đã tắt."
        )