from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton
)

from peer_list_item import PeerListItemWidget


class PeerSidebar(QFrame):
    """Sidebar bên trái: tìm kiếm và danh sách Peer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(12)

        title = QLabel("PEERS")
        title.setObjectName("sectionTitle")

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search peers...")

        self.peer_list = QListWidget()
        self.peer_list.setObjectName("peerList")

        self.discover_btn = QPushButton("+  Add / Discover Peer")
        self.discover_btn.setObjectName("secondaryButton")

        layout.addWidget(title)
        layout.addWidget(self.search_box)
        layout.addWidget(self.peer_list, 1)
        layout.addWidget(self.discover_btn)

    def set_peers(self, peers):
        self.peer_list.clear()

        for peer in peers:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, peer)

            widget = PeerListItemWidget(peer)
            item.setSizeHint(QSize(220, 62))

            self.peer_list.addItem(item)
            self.peer_list.setItemWidget(item, widget)

    def filter_peers(self, text):
        text = text.lower().strip()

        for index in range(self.peer_list.count()):
            item = self.peer_list.item(index)
            peer = item.data(Qt.UserRole)
            item.setHidden(text not in peer.name.lower())
