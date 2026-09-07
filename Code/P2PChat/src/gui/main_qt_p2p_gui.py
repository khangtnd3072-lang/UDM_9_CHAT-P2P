import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFrame,
    QMessageBox,
)


from peer_repository import PeerRepository
from peer_sidebar import PeerSidebar
from chat_panel import ChatPanel
from peer_details_panel import PeerDetailsPanel
from styles import STYLE

from gui.network_worker import PeerWorker


class MainWindow(QMainWindow):
    """Cửa sổ chính điều phối toàn bộ giao diện P2PChat."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("P2PChat")
        self.resize(1200, 720)
        self.setMinimumSize(950, 600)

        self.selected_peer = None
        self.repository = PeerRepository()
        self.worker = None  ## khởi tạo khi kết nối Peer

        self.build_ui()
        self.apply_style()
        self.load_peers()
        self.connect_signals()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.create_top_bar())

        body = QFrame()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        self.sidebar = PeerSidebar()
        self.chat_panel = ChatPanel()
        self.details_panel = PeerDetailsPanel()

        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.chat_panel, 1)
        body_layout.addWidget(self.details_panel)

        main_layout.addWidget(body, 1)

        self.statusBar().showMessage(
            "Online • Discovery: Active • Peers: 0"
        )

    def create_top_bar(self):
        top_bar = QFrame()
        top_bar.setObjectName("topBar")

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(22, 12, 22, 12)

        logo = QLabel("P²")
        logo.setObjectName("logo")

        title_box = QVBoxLayout()

        title = QLabel("P2PChat")
        title.setObjectName("appTitle")

        subtitle = QLabel("Secure local network messaging")
        subtitle.setObjectName("subtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        encrypted = QLabel("🔒 End-to-End Encrypted")
        encrypted.setObjectName("encrypted")

        layout.addWidget(logo)
        layout.addLayout(title_box)
        layout.addStretch()
        layout.addWidget(encrypted)

        return top_bar

    def connect_signals(self):
        self.sidebar.search_box.textChanged.connect(
            self.sidebar.filter_peers
        )
        self.sidebar.peer_list.itemClicked.connect(
            self.select_peer
        )
        self.sidebar.discover_btn.clicked.connect(
            self.discover_peer
        )

        self.chat_panel.connect_btn.clicked.connect(
            self.connect_peer
        )
        self.chat_panel.send_btn.clicked.connect(
            self.send_message
        )
        self.chat_panel.message_input.returnPressed.connect(
            self.send_message
        )

        self.details_panel.block_btn.clicked.connect(
            self.block_peer
        )

    def load_peers(self):
        peers = self.repository.all()
        self.sidebar.set_peers(peers)

        self.statusBar().showMessage(
            f"Online • Discovery: Active • Peers: {len(peers)}"
        )

    def select_peer(self, item):
        peer = item.data(Qt.UserRole)

        if peer is None:
            return

        self.selected_peer = peer
        self.chat_panel.set_peer(peer)
        self.details_panel.set_peer(peer)

    # def connect_peer(self):
    #     if not self.selected_peer:
    #         QMessageBox.information(
    #             self,
    #             "Connect",
    #             "Hãy chọn một Peer trước."
    #         )
    #         return

    #     if not self.selected_peer.is_online:
    #         QMessageBox.warning(
    #             self,
    #             "Connect",
    #             "Peer này đang Offline."
    #         )
    #         return

    #     self.chat_panel.set_connection_status("Connected")
    #     self.details_panel.set_status("Connected")
    #     self.chat_panel.append_system_message()

    def connect_peer(self):
        if not self.selected_peer:
            QMessageBox.information(self, "Connect", "Hãy chọn một Peer trước.")
            return
        
        if not self.selected_peer.is_online:
            QMessageBox.warning(self, "Connect", "Peer này đang Offline.")
            return

        # Nếu đang có kết nối cũ thì ngắt trước khi tạo kết nối mới
        if self.worker and self.worker.isRunning():
            self.worker.stop()

        try:
            import socket

            # Lấy IP và Port từ object peer được chọn
            peer_ip = getattr(self.selected_peer, "ip", "127.0.0.1")
            peer_port = int(getattr(self.selected_peer, "port", 8080))

            # 1. Khởi tạo Socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_ip, peer_port))

            # 2. Khởi tạo Worker (Đóng vai trò Client gửi kết nối)
            self.worker = PeerWorker(sock=sock, is_server=False, my_id="My_Node")

            # 3. Kết nối các Signal từ Worker vào các Slot xử lý UI
            self.worker.sig_connected.connect(self.on_peer_connected)
            self.worker.sig_chat_received.connect(self.on_chat_received)
            self.worker.sig_error.connect(self.on_network_error)

            # 4. Kích hoạt QThread
            self.worker.start()
            self.statusBar().showMessage(f"Đang kết nối (Handshake) với {peer_ip}:{peer_port}...")

        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối", f"Không thể kết nối Socket: {str(e)}")
    def send_message(self):
        text = self.chat_panel.message_input.text().strip()

        if not text:
            return

        if not self.selected_peer:
            QMessageBox.information(
                self,
                "Send",
                "Hãy chọn một Peer trước."
            )
            return

        if self.chat_panel.connect_btn.text() != "✓ Connected":
            QMessageBox.information(
                self,
                "Send",
                "Hãy bấm Connect trước."
            )
            return

        self.worker.send_chat_msg(text)
        self.chat_panel.append_user_message(text)
        self.chat_panel.message_input.clear()

    def discover_peer(self):
        QMessageBox.information(
            self,
            "Discover Peer",
            "Đây là giao diện mẫu.\n"
            "Sau khi nối backend P2P, nút này sẽ gọi Peer Discovery."
        )

    def block_peer(self):
        if not self.selected_peer:
            return

        QMessageBox.information(
            self,
            "Block Peer",
            f"Block: {self.selected_peer.name}"
        )

    def apply_style(self):
        self.setStyleSheet(STYLE)



    # --- XỬ LÝ DỮ LIỆU TỪ WORKER ---

    def on_peer_connected(self, peer_id: str, fingerprint: str):
        """Gọi khi Handshake thành công: Cập nhật giao diện & Fingerprint SHA-256."""
        self.chat_panel.set_connection_status("Connected")
        self.details_panel.set_status("Connected")
        
        # Cập nhật thông tin Fingerprint lên panel thông tin chi tiết
        if hasattr(self.details_panel, "lbl_fingerprint"):
            self.details_panel.lbl_fingerprint.setText(fingerprint)

        self.chat_panel.append_system_message()
        self.statusBar().showMessage(f"Đã kết nối an toàn với {peer_id} | FP: {fingerprint[:16]}...")

    def on_chat_received(self, sender: str, text: str):
        """Gọi khi nhận được tin nhắn chat đã giải mã từ Worker."""
        self.chat_panel.append_user_message(f"[{sender}]: {text}")

    def on_network_error(self, err_msg: str):
        """Xử lý khi ngắt kết nối hoặc lỗi giải mã."""
        self.chat_panel.set_connection_status("Disconnected")
        self.details_panel.set_status("Disconnected")
        QMessageBox.warning(self, "Lỗi Mạng", f"Kết nối bị ngắt hoặc gặp lỗi: {err_msg}")


class P2PChatApplication:
    """Wrapper OOP cho QApplication."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        self.window = MainWindow()

    def run(self):
        self.window.show()
        return self.app.exec()


def main():
    application = P2PChatApplication()
    sys.exit(application.run())


if __name__ == "__main__":
    main()