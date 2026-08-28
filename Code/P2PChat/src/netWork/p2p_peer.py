import argparse
import json
import logging
import socket
import sys
import threading
import traceback
import time
from pathlib import Path
from typing import Dict, Optional, Callable
from collections import defaultdict

# Ensure repo root is importable when this file is launched directly as a script
for parent in Path(__file__).resolve().parents:
    if (parent / "Code").exists():
        sys.path.insert(0, str(parent))
        break

from Code.P2PChat.src.crypto import CryptoManager
from Code.P2PChat.src.handshake import (
    client_start_handshake,
    client_finish_handshake,
    server_handle_init_and_respond,
    send_encrypted,
    recv_encrypted,
)
from Code.P2PChat.src.message.protocol import decode_message, encode_message

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [P2P]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class P2PPeer:

    def __init__(self, peer_name: str, listen_host: str = "127.0.0.1", listen_port: int = 5000, secure: bool = True):
        self.peer_name = peer_name
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.use_secure = secure
        
        # Crypto cho peer này
        self.crypto = CryptoManager()
        
        # Lưu trữ các kết nối tới peer khác: {peer_name -> (socket, crypto)}
        self.peers: Dict[str, tuple] = {}
        self.peers_lock = threading.Lock()
        
        # Callbacks
        self.message_callbacks: list[Callable] = []
        
        # Server socket
        self.server_socket: Optional[socket.socket] = None
        self.server_running = False
        
        logger.info(f" Peer '{self.peer_name}' khởi tạo: {peer_name} @ {listen_host}:{listen_port} (secure={secure})")
    
    def start_listening(self):
        """Khởi động server để accept kết nối từ peer khác"""
        thread = threading.Thread(target=self._listen_for_peers, daemon=True)
        thread.start()
        logger.info(f" Peer '{self.peer_name}' bắt đầu listening trên {self.listen_host}:{self.listen_port}")
    
    def _listen_for_peers(self):
        """Server thread - chấp nhận kết nối từ peer khác"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.listen_host, self.listen_port))
        self.server_socket.listen(5)
        self.server_running = True
        
        logger.info(f"[SERVER] {self.peer_name} listening on {self.listen_host}:{self.listen_port}")
        
        try:
            while self.server_running:
                try:
                    conn, addr = self.server_socket.accept()
                    logger.info(f"[SERVER] Nhận kết nối từ {addr}")
                    
                    # Xử lý peer mới trên thread riêng
                    thread = threading.Thread(
                        target=self._handle_incoming_peer,
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
    
    def _handle_incoming_peer(self, conn: socket.socket, addr: tuple):
        """Xử lý kết nối từ peer khác (vừa nhận Handshake)"""
        peer_crypto = CryptoManager()
        peer_name = None
        
        try:
            if self.use_secure:
                # Handshake E2EE (Server side)
                peer_name = server_handle_init_and_respond(conn, peer_crypto)
                logger.info(f"[SERVER] Handshake hoàn tất với peer: {peer_name}")
            
            # Lưu trữ kết nối
            with self.peers_lock:
                self.peers[peer_name] = (conn, peer_crypto)
            
            # Nhận tin nhắn từ peer này
            self._receive_from_peer(peer_name, conn, peer_crypto)
        
        except Exception as e:
            logger.error(f"[SERVER] Lỗi với {addr}: {e}")
            traceback.print_exc()
        finally:
            with self.peers_lock:
                if peer_name and peer_name in self.peers:
                    del self.peers[peer_name]
            try:
                conn.close()
            except:
                pass
            logger.info(f"[SERVER] Đóng kết nối với {peer_name or addr}")
    
    def connect_to_peer(self, peer_name: str, peer_host: str, peer_port: int) -> bool:
        """
        Kết nối tới peer khác (Client side)
        
        Returns:
            True nếu kết nối thành công, False nếu thất bại
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_host, peer_port))
            logger.info(f"[CLIENT] Đã kết nối tới {peer_name} @ {peer_host}:{peer_port}")
            
            peer_crypto = CryptoManager()
            
            if self.use_secure:
                # Handshake E2EE (Client side)
                resp = client_start_handshake(sock, self.peer_name, peer_crypto)
                client_finish_handshake(resp, peer_crypto)
                logger.info(f"[CLIENT] Handshake hoàn tất với {peer_name}")
            
            # Lưu trữ kết nối
            with self.peers_lock:
                self.peers[peer_name] = (sock, peer_crypto)
            
            # Nhận tin nhắn từ peer này trên thread riêng
            thread = threading.Thread(
                target=self._receive_from_peer,
                args=(peer_name, sock, peer_crypto),
                daemon=True
            )
            thread.start()
            
            return True
        
        except Exception as e:
            logger.error(f"[CLIENT] Lỗi kết nối tới {peer_name} @ {peer_host}:{peer_port}: {e}")
            return False
    
    def _receive_from_peer(self, peer_name: str, sock: socket.socket, peer_crypto: CryptoManager):
        """Nhận tin nhắn từ một peer (chạy trên thread riêng)"""
        try:
            while True:
                if self.use_secure:
                    msg = recv_encrypted(sock, peer_crypto, timeout=1.0)
                else:
                    try:
                        msg = decode_message(sock, timeout=1.0)
                    except socket.timeout:
                        continue
                
                # Xử lý tin nhắn
                self._handle_message(peer_name, msg)
        
        except EOFError:
            logger.info(f"[RECV] Peer '{peer_name}' đóng kết nối")
        except socket.timeout:
            pass
        except Exception as e:
            logger.error(f"[RECV] Lỗi nhận từ {peer_name}: {e}")
        finally:
            with self.peers_lock:
                if peer_name in self.peers:
                    del self.peers[peer_name]
    
    def _handle_message(self, peer_name: str, msg: dict):
        """Xử lý tin nhắn nhận được từ peer"""
        msg_type = msg.get("type", "chat")
        
        if msg_type == "chat":
            content = msg.get("message", msg.get("text", ""))
            sender = msg.get("sender", peer_name)
            logger.info(f"[CHAT] {sender}: {content}")
            
            # Trigger callback
            for callback in self.message_callbacks:
                try:
                    callback(sender, content)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        elif msg_type == "system":
            logger.info(f"[SYSTEM] {msg.get('content', 'N/A')}")
    
    def send_message(self, peer_name: str, message: str) -> bool:
        """
        Gửi tin nhắn tới một peer
        
        Returns:
            True nếu gửi thành công, False nếu thất bại
        """
        with self.peers_lock:
            peer_entry = self.peers.get(peer_name)
            if not peer_entry:
                logger.warning(f"[SEND] Peer '{peer_name}' không online")
                return False
            
            sock, peer_crypto = peer_entry
        
        try:
            payload = {
                "type": "chat",
                "sender": self.peer_name,
                "message": message,
            }
            
            if self.use_secure:
                send_encrypted(sock, peer_crypto, payload)
            else:
                sock.sendall(encode_message(payload))
            
            logger.info(f"[SEND] {self.peer_name} -> {peer_name}: {message}")
            return True
        
        except Exception as e:
            logger.error(f"[SEND] Lỗi gửi tới {peer_name}: {e}")
            return False
    
    def broadcast_message(self, message: str):
        """Gửi tin nhắn tới tất cả peer kết nối"""
        with self.peers_lock:
            peer_names = list(self.peers.keys())
        
        for peer_name in peer_names:
            self.send_message(peer_name, message)
    
    def list_connected_peers(self) -> list[str]:
        """Danh sách các peer đang kết nối"""
        with self.peers_lock:
            return list(self.peers.keys())
    
    def get_peer_fingerprint(self, peer_name: str) -> Optional[str]:
        """Lấy fingerprint của peer (để xác minh)"""
        with self.peers_lock:
            peer_entry = self.peers.get(peer_name)
            if peer_entry:
                sock, peer_crypto = peer_entry
                return peer_crypto.get_fingerprint()
        return None
    
    def get_public_key_pem(self) -> str:
        """Lấy public key của peer này (để share với peer khác)"""
        return self.crypto.get_public_key_pem()
    
    def get_fingerprint(self) -> str:
        """Lấy fingerprint của peer này"""
        return self.crypto.get_fingerprint()
    
    def shutdown(self):
        """Đóng tất cả kết nối và shutdown peer"""
        logger.info(f"[SHUTDOWN] Đóng peer '{self.peer_name}'...")
        
        self.server_running = False
        
        with self.peers_lock:
            for peer_name, (sock, _) in self.peers.items():
                try:
                    sock.close()
                except:
                    pass
            self.peers.clear()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        logger.info(f"[SHUTDOWN] Peer '{self.peer_name}' đã tắt")


def interactive_peer_cli(peer: P2PPeer):
    """CLI tương tác cho P2P Peer"""
    print(f"\n{'='*60}")
    print(f"  P2P Chat - Peer: {peer.peer_name}")
    print(f"  Listening on: {peer.listen_host}:{peer.listen_port}")
    print(f"  Fingerprint: {peer.get_fingerprint()}")
    print(f"{'='*60}\n")
    
    print("Các lệnh:")
    print("  /connect <peer_name> <host> <port>  - Kết nối tới peer khác")
    print("  /send <peer_name> <message>         - Gửi tin nhắn")
    print("  /broadcast <message>                - Gửi broadcast")
    print("  /peers                              - Danh sách peer kết nối")
    print("  /fingerprint <peer_name>            - Xem fingerprint peer")
    print("  /help                               - Xem trợ giúp")
    print("  /exit                               - Thoát\n")
    
    # Callback để in tin nhắn nhận được
    def on_message(sender, content):
        print(f"\n💬 [{sender}]: {content}")
        print(f"{peer.peer_name}: ", end="", flush=True)
    
    peer.message_callbacks.append(on_message)
    
    while True:
        try:
            user_input = input(f"{peer.peer_name}: ").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith("/"):
                # Xử lý lệnh
                parts = user_input.split()
                cmd = parts[0].lower()
                
                if cmd == "/connect":
                    if len(parts) >= 4:
                        target_peer = parts[1]
                        target_host = parts[2]
                        target_port = int(parts[3])
                        success = peer.connect_to_peer(target_peer, target_host, target_port)
                        if success:
                            print(f" Đã kết nối tới {target_peer}")
                        else:
                            print(f" Kết nối tới {target_peer} thất bại")
                    else:
                        print("Usage: /connect <peer_name> <host> <port>")
                
                elif cmd == "/send":
                    if len(parts) >= 3:
                        target_peer = parts[1]
                        message = " ".join(parts[2:])
                        peer.send_message(target_peer, message)
                    else:
                        print("Usage: /send <peer_name> <message>")
                
                elif cmd == "/broadcast":
                    if len(parts) >= 2:
                        message = " ".join(parts[1:])
                        peer.broadcast_message(message)
                    else:
                        print("Usage: /broadcast <message>")
                
                elif cmd == "/peers":
                    peers = peer.list_connected_peers()
                    if peers:
                        print(f"Đang kết nối với: {', '.join(peers)}")
                    else:
                        print("Chưa kết nối với peer nào")
                
                elif cmd == "/fingerprint":
                    if len(parts) >= 2:
                        target_peer = parts[1]
                        fp = peer.get_peer_fingerprint(target_peer)
                        if fp:
                            print(f"{target_peer} fingerprint: {fp}")
                        else:
                            print(f"Peer '{target_peer}' không kết nối")
                    else:
                        print("Usage: /fingerprint <peer_name>")
                
                elif cmd == "/help":
                    print("\nCac Lenh:")
                    print("  /connect <peer_name> <host> <port>")
                    print("  /send <peer_name> <message>")
                    print("  /broadcast <message>")
                    print("  /peers")
                    print("  /fingerprint <peer_name>")
                    print("  /exit")
                
                elif cmd == "/exit":
                    peer.shutdown()
                    print("Tam biet!")
                    break
                
                else:
                    print(f"Lenh khong biet: {cmd}")
            
            else:
                # Nếu đã kết nối với 1 peer, gửi tin nhắn tới peer đó
                peers = peer.list_connected_peers()
                if len(peers) == 1:
                    peer.send_message(peers[0], user_input)
                elif len(peers) > 1:
                    print(f"Kết nối với nhiều peer: {', '.join(peers)}")
                    print("Dùng: /send <peer_name> <message>")
                else:
                    print("Chưa kết nối với peer nào. Dùng: /connect <peer_name> <host> <port>")
        
        except KeyboardInterrupt:
            print("\n\nTạm biệt!")
            peer.shutdown()
            break
        except Exception as e:
            logger.error(f"Lỗi: {e}")


def main():
    parser = argparse.ArgumentParser(description="P2P Chat - True Peer-to-Peer (No Relay Server)")
    parser.add_argument("--name", required=True, help="Tên của Peer ")
    parser.add_argument("--host", default="127.0.0.1", help="Host để listening")
    parser.add_argument("--port", type=int, default=5000, help="Port để listening")
    parser.add_argument("--secure", action="store_true", default=True, help="Dùng E2EE encryption")
    parser.add_argument("--no-secure", action="store_true", help="Không dùng encryption")
    
    args = parser.parse_args()
    
    use_secure = not args.no_secure
    
    # Tạo peer
    peer = P2PPeer(
        peer_name=args.name,
        listen_host=args.host,
        listen_port=args.port,
        secure=use_secure
    )
    
    # Bắt đầu listening
    peer.start_listening()
    
    # CLI tương tác
    interactive_peer_cli(peer)


if __name__ == "__main__":
    main()
