from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit
)


class ChatPanel(QFrame):
    """Khu vực chat trung tâm."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("chatHeader")

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)

        self.peer_avatar = QLabel("?")
        self.peer_avatar.setObjectName("peerAvatar")
        self.peer_avatar.setAlignment(Qt.AlignCenter)
        self.peer_avatar.setFixedSize(46, 46)

        info_layout = QVBoxLayout()

        self.peer_name = QLabel("No peer selected")
        self.peer_name.setObjectName("chatPeerName")

        self.status = QLabel("Offline")
        self.status.setObjectName("offlineStatus")

        info_layout.addWidget(self.peer_name)
        info_layout.addWidget(self.status)

        self.connect_btn = QPushButton("🔗  Connect")
        self.connect_btn.setObjectName("connectButton")

        header_layout.addWidget(self.peer_avatar)
        header_layout.addLayout(info_layout)
        header_layout.addStretch()
        header_layout.addWidget(self.connect_btn)

        # Messages
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setObjectName("chatView")

        # Input
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")

        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(14, 12, 14, 12)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Type a message...")

        self.send_btn = QPushButton("Send")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.setFixedWidth(100)

        input_layout.addWidget(self.message_input, 1)
        input_layout.addWidget(self.send_btn)

        layout.addWidget(header)
        layout.addWidget(self.chat_view, 1)
        layout.addWidget(input_frame)

    def set_peer(self, peer):
        self.peer_name.setText(peer.name)
        self.peer_avatar.setText(peer.avatar)
        self.set_connection_status(peer.status)

        self.chat_view.clear()
        self.chat_view.append(
            "<div style='text-align:center; color:#999;'>"
            f"Secure session with <b>{peer.name}</b>"
            "</div><br>"
        )

    def set_connection_status(self, status):
        if status == "Connected":
            self.status.setText("● Connected")
            self.status.setObjectName("onlineStatus")
            self.connect_btn.setText("✓ Connected")
        elif status == "Online":
            self.status.setText("● Online")
            self.status.setObjectName("onlineStatus")
            self.connect_btn.setText("🔗  Connect")
        else:
            self.status.setText("● Offline")
            self.status.setObjectName("offlineStatus")
            self.connect_btn.setText("🔗  Connect")

        self._refresh_style(self.status)
        self._refresh_style(self.connect_btn)

    def append_system_message(self):
        self.chat_view.append(
            "<div style='color:#555;'>"
            "System: Direct P2P connection established."
            "</div>"
        )

    def append_user_message(self, text):
        self.chat_view.append(
            "<div style='margin:8px;'>"
            f"<b>You:</b> {text}"
            "</div>"
        )

    @staticmethod
    def _refresh_style(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
