from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel

from models import Peer


class PeerListItemWidget(QWidget):
    """Widget hiển thị một Peer trong danh sách."""

    def __init__(self, peer: Peer, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)

        avatar = QLabel(peer.avatar)
        avatar.setObjectName("smallAvatar")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(38, 38)

        text_layout = QVBoxLayout()

        name_label = QLabel(peer.name)
        name_label.setObjectName("peerName")

        status_label = QLabel("● " + peer.status)
        status_label.setObjectName(
            "onlineText" if peer.is_online else "offlineText"
        )

        text_layout.addWidget(name_label)
        text_layout.addWidget(status_label)

        layout.addWidget(avatar)
        layout.addLayout(text_layout)
        layout.addStretch()
