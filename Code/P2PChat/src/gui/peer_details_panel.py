from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton
)

from detail_row import DetailRow


class PeerDetailsPanel(QFrame):
    """Panel bên phải hiển thị thông tin Peer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("details")
        self.setFixedWidth(260)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 18, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Peer Details")
        title.setObjectName("sectionTitle")

        card = QFrame()
        card.setObjectName("detailsCard")

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 18, 14, 18)
        card_layout.setSpacing(12)

        self.avatar = QLabel("?")
        self.avatar.setObjectName("detailAvatar")
        self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setFixedSize(72, 72)

        self.name = QLabel("No peer selected")
        self.name.setObjectName("detahilName")
        self.name.setAlignment(Qt.AlignCenter)

        self.status = QLabel("● Offline")
        self.status.setObjectName("offlineStatus")
        self.status.setAlignment(Qt.AlignCenter)

        card_layout.addWidget(self.avatar, alignment=Qt.AlignCenter)
        card_layout.addWidget(self.name)
        card_layout.addWidget(self.status)

        info_card = QFrame()
        info_card.setObjectName("infoCard")

        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 14, 14, 14)
        info_layout.setSpacing(8)

        self.peer_id = DetailRow("Peer ID")
        self.peer_ip = DetailRow("IP")
        self.peer_port = DetailRow("Port")
        self.peer_fingerprint = DetailRow("Fingerprint")
        self.peer_trust = DetailRow("Trust")

        for row in (
            self.peer_id,
            self.peer_ip,
            self.peer_port,
            self.peer_fingerprint,
            self.peer_trust,
        ):
            info_layout.addWidget(row)

        self.block_btn = QPushButton("⊘  Block Peer")
        self.block_btn.setObjectName("blockButton")

        layout.addWidget(title)
        layout.addWidget(card)
        layout.addWidget(info_card)
        layout.addStretch()
        layout.addWidget(self.block_btn)

    def set_peer(self, peer):
        self.avatar.setText(peer.avatar)
        self.name.setText(peer.name)
        self.set_status(peer.status)

        self.peer_id.set_value(peer.peer_id)
        self.peer_ip.set_value(peer.ip)
        self.peer_port.set_value(peer.port)
        self.peer_fingerprint.set_value(peer.fingerprint)
        self.peer_trust.set_value(peer.trust)

    def set_status(self, status):
        if status == "Connected":
            self.status.setText("● Connected")
            self.status.setObjectName("onlineStatus")
        elif status == "Online":
            self.status.setText("● Online")
            self.status.setObjectName("onlineStatus")
        else:
            self.status.setText("● Offline")
            self.status.setObjectName("offlineStatus")

        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.status.update()