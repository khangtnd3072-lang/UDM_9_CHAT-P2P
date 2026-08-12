import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from controller.peer_discovery import PeerDiscovery


def test_insert_and_update():
    events = []
    d = PeerDiscovery("Khoi", 5001, peer_id="a",
                      on_peer_discovered=lambda p: events.append(("new", p)),
                      on_peer_updated=lambda p: events.append(("update", p)))
    d._upsert_peer("b", "Tai", "127.0.0.1", 5002)
    d._upsert_peer("b", "Tai2", "127.0.0.1", 5003)
    assert d.get_peer("b").username == "Tai2"
    assert d.get_peer("b").tcp_port == 5003
    assert [x[0] for x in events] == ["new", "update"]


def test_self_packet_is_ignored():
    d = PeerDiscovery("Khoi", 5001, peer_id="a")
    d._handle_packet(
        b'{"type":"PEER_INFO","peer_id":"a","username":"Khoi","tcp_port":5001}',
        ("127.0.0.1", 37020),
    )
    assert d.get_peers() == []
