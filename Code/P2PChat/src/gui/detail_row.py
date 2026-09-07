from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class DetailRow(QFrame):
    """Một dòng thông tin trong Peer Details."""

    def __init__(self, label, value="—", parent=None):
        super().__init__(parent)
        self.setObjectName("detailRow")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(2)

        label_widget = QLabel(label)
        label_widget.setObjectName("detailLabel")

        self.value_widget = QLabel(value)
        self.value_widget.setObjectName("detailValue")

        layout.addWidget(label_widget)
        layout.addWidget(self.value_widget)

    def set_value(self, value):
        self.value_widget.setText(str(value))

    def value(self):
        return self.value_widget.text()
