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

from Code.P2PChat.src.gui.peer_repository import PeerRepository
from Code.P2PChat.src.gui.peer_sidebar import PeerSidebar
from Code.P2PChat.src.gui.chat_panel import ChatPanel
from Code.P2PChat.src.gui.peer_details_panel import PeerDetailsPanel
from Code.P2PChat.src.gui.styles import STYLE


class MainWindow(QMainWindow):
    """Cửa sổ chính điều phối toàn bộ giao diện P2PChat."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("P2PChat")
        self.resize(1200, 720)
        self.setMinimumSize(950, 600)

        self.selected_peer = None
        self.repository = PeerRepository()

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

    def connect_peer(self):
        if not self.selected_peer:
            QMessageBox.information(
                self,
                "Connect",
                "Hãy chọn một Peer trước."
            )
            return

        if not self.selected_peer.is_online:
            QMessageBox.warning(
                self,
                "Connect",
                "Peer này đang Offline."
            )
            return

        self.chat_panel.set_connection_status("Connected")
        self.details_panel.set_status("Connected")
        self.chat_panel.append_system_message()

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
