from dataclasses import dataclass


@dataclass
class Peer:
    """Dữ liệu của một Peer."""
    name: str
    status: str
    ip: str
    port: str
    fingerprint: str = "A4:9C:••:7F"
    trust: str = "Not verified"

    @property
    def peer_id(self):
        return self.name.lower()

    @property
    def avatar(self):
        return self.name[0].upper() if self.name else "?"

    @property
    def is_online(self):
        return self.status == "Online"