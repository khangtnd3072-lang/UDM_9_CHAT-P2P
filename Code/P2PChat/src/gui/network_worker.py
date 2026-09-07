# Thư mục: ui/network_worker.py
import base64
import socket
from PySide6.QtCore import QThread, Signal

# Import core do các bạn khác viết (Không sửa code gốc của họ)
from Code.P2PChat.src.crypto import CryptoManager
from Code.P2PChat.src.handshake import (
    client_start_handshake,
    client_finish_handshake,
    server_handle_init_and_respond,
    send_encrypted,
    recv_encrypted,
)
from Code.P2PChat.src.transfer import FileReceiver, FileSender

class PeerWorker(QThread):
    # Signals bắn dữ liệu về giao diện
    sig_connected = Signal(str, str)  # (peer_id, fingerprint)
    sig_chat_received = Signal(str, str)  # (sender, text)
    sig_file_progress = Signal(float)  # (%)
    sig_error = Signal(str)

    def __init__(self, sock: socket.socket, is_server: bool, my_id: str):
        super().__init__()
        self.sock = sock
        self.is_server = is_server
        self.my_id = my_id
        self.crypto_mgr = CryptoManager()
        self.running = True

    def run(self):
        try:
            # Luồng Handshake
            if self.is_server:
                peer_id = server_handle_init_and_respond(self.sock, self.crypto_mgr)
            else:
                resp = client_start_handshake(self.sock, self.my_id, self.crypto_mgr)
                client_finish_handshake(resp, self.crypto_mgr)
                peer_id = resp.get("client_id", "Peer")

            fp = self.crypto_mgr.get_fingerprint()
            self.sig_connected.emit(peer_id, fp)

            # Lắng nghe dữ liệu mã hóa liên tục
            while self.running:
                payload = recv_encrypted(self.sock, self.crypto_mgr)
                p_type = payload.get("type")

                if p_type == "chat":
                    self.sig_chat_received.emit(payload.get("sender"), payload.get("text"))

        except Exception as e:
            if self.running:
                self.sig_error.emit(str(e))

    def send_chat_msg(self, text: str):
        payload = {"type": "chat", "sender": self.my_id, "text": text}
        send_encrypted(self.sock, self.crypto_mgr, payload)