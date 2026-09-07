from models import Peer


class PeerRepository:
    """Quản lý dữ liệu Peer."""

    def __init__(self):
        self._peers = [
            Peer("Khang", "Online", "192.168.1.10", "12000"),
            Peer("Tai", "Online", "192.168.1.11", "12001"),
            Peer("Minh Khoi", "Offline", "192.168.1.12", "12002"),
        ]

    def all(self):
        return list(self._peers)

    def find_by_name(self, name):
        return next(
            (peer for peer in self._peers if peer.name == name),
            None
        )
