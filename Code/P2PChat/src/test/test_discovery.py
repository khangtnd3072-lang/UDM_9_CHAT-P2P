<<<<<<< HEAD
import threading
import socket
import json
import time
import unittest

HOST = "127.0.0.1"
DISCOVERY_PORT = 53001

class TestDiscoveryServer(unittest.TestCase):
    def setUp(self):
        self.server_running = True
        self.peers = []
        self.server_thread = threading.Thread(target=self.mock_discovery_server, daemon=True)
        self.server_thread.start()
        time.sleep(0.2)

    def tearDown(self):
        self.server_running = False

    def mock_discovery_server(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, DISCOVERY_PORT))
        srv.listen(5)
        srv.settimeout(0.5)
        
        while self.server_running:
            try:
                conn, addr = srv.accept()
                data = conn.recv(1024).decode('utf-8')
                if not data: continue
                
                req = json.loads(data)
                if req.get("action") == "REGISTER":
                    self.peers.append(req.get("address"))
                    conn.sendall(json.dumps({"status": "OK"}).encode('utf-8'))
                elif req.get("action") == "LOOKUP":
                    conn.sendall(json.dumps({"peers": self.peers}).encode('utf-8'))
                conn.close()
            except socket.timeout:
                continue
            except Exception:
                break
        srv.close()

    def test_register_and_lookup_peer(self):
        # 1. Đăng ký peer mới
        cli1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli1.connect((HOST, DISCOVERY_PORT))
        cli1.sendall(json.dumps({"action": "REGISTER", "address": "127.0.0.1:6000"}).encode('utf-8'))
        resp1 = json.loads(cli1.recv(1024).decode('utf-8'))
        cli1.close()
        self.assertEqual(resp1.get("status"), "OK")

        # 2. Truy vấn danh sách peer
        cli2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli2.connect((HOST, DISCOVERY_PORT))
        cli2.sendall(json.dumps({"action": "LOOKUP"}).encode('utf-8'))
        resp2 = json.loads(cli2.recv(1024).decode('utf-8'))
        cli2.close()
        self.assertIn("127.0.0.1:6000", resp2.get("peers"))

if __name__ == "__main__":
    unittest.main()
=======
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
    
>>>>>>> 6da704b1a6b7681890bf5cc62d813d12dd0960ae
