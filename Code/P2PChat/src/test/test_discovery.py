import time

from network.discovery import (
    DiscoveryService,
    PEER_TIMEOUT
)

def create_discovery():

    return DiscoveryService(
        username="Tai",
        listen_port=5000,
        peer_id="self_peer",
        fingerprint="SELF_FP",
        public_key_pem="PUB",
        private_key_pem="PRI"
    )


def test_registry_add_peer():

    discovery = create_discovery()

    packet = {
        "peer_id": "peer_1",
        "username": "User A",
        "fingerprint": "FP_A",
        "port": 6000,
        "status": "online"
    }

    discovery.update_peer_registry(
        packet,
        ("192.168.1.10", 15000)
    )

    peers = discovery.get_nearby_peers()

    assert "peer_1" in peers
    
def test_registry_store_peer_info():

    discovery = create_discovery()

    packet = {
        "peer_id": "peer_2",
        "username": "User B",
        "fingerprint": "FP_B",
        "port": 7000,
        "status": "online"
    }

    discovery.update_peer_registry(
        packet,
        ("192.168.1.20", 15000)
    )

    peer = discovery.get_nearby_peers()["peer_2"]

    assert peer["username"] == "User B"
    assert peer["ip"] == "192.168.1.20"
    assert peer["tcp_port"] == 7000
    
def test_duplicate_peer_updates_record():

    discovery = create_discovery()

    packet1 = {
        "peer_id": "peer_dup",
        "username": "User",
        "fingerprint": "FP",
        "port": 6000
    }

    packet2 = {
        "peer_id": "peer_dup",
        "username": "User",
        "fingerprint": "FP",
        "port": 7000
    }

    discovery.update_peer_registry(
        packet1,
        ("192.168.1.10", 15000)
    )

    discovery.update_peer_registry(
        packet2,
        ("192.168.1.99", 15000)
    )

    peer = discovery.get_nearby_peers()["peer_dup"]

    assert peer["ip"] == "192.168.1.99"
    assert peer["tcp_port"] == 7000
    
def test_ignore_invalid_peer():

    discovery = create_discovery()

    discovery.update_peer_registry(
        {},
        ("192.168.1.10", 15000)
    )

    assert len(
        discovery.get_nearby_peers()
    ) == 0
    
def test_peer_expiration():

    discovery = create_discovery()

    packet = {
        "peer_id": "peer_old",
        "username": "Old User",
        "fingerprint": "FP",
        "port": 6000
    }

    discovery.update_peer_registry(
        packet,
        ("192.168.1.10", 15000)
    )

    discovery.nearby_peers[
        "peer_old"
    ]["last_seen"] = (
        time.time()
        - PEER_TIMEOUT
        - 1
    )

    discovery.cleanup_expired_peers()

    assert (
        "peer_old"
        not in discovery.nearby_peers
    )
    
def test_on_peer_found_called():

    discovery = create_discovery()

    called = False

    def callback(packet, address):
        nonlocal called
        called = True

    discovery.on_peer_found = callback

    packet = {
        "type": "discovery_response",
        "peer_id": "peer1",
        "username": "User",
        "fingerprint": "FP",
        "port": 6000
    }

    discovery._handle_packet(
        packet,
        ("127.0.0.1", 15000)
    )

    assert called
    
