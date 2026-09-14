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