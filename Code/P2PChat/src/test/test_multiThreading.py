import threading
import socket
import time
import unittest

HOST = "127.0.0.1"
RACE_PORT = 53002

class TestRaceCondition(unittest.TestCase):
    def test_concurrent_connections(self):
        shared_counter = 0
        lock = threading.Lock()
        server_running = True
        
        def mock_server():
            nonlocal shared_counter
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, RACE_PORT))
            srv.listen(50)
            srv.settimeout(0.5)
            
            def handle_client(conn):
                nonlocal shared_counter
                try:
                    data = conn.recv(1024)
                    if data == b"INCREMENT":
                        with lock:
                            temp = shared_counter
                            time.sleep(0.01) # Ép độ trễ để dễ bộc lộ race condition nếu mất lock
                            shared_counter = temp + 1
                finally:
                    conn.close()

            while server_running:
                try:
                    conn, _ = srv.accept()
                    threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
                except socket.timeout:
                    continue
            srv.close()

        thr = threading.Thread(target=mock_server, daemon=True)
        thr.start()
        time.sleep(0.2)

        # Tạo 20 luồng client kết nối đồng thời
        def client_worker():
            try:
                cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli.connect((HOST, RACE_PORT))
                cli.sendall(b"INCREMENT")
                cli.close()
            except Exception:
                pass

        threads = []
        for _ in range(20):
            t = threading.Thread(target=client_worker)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()

        server_running = False
        thr.join(timeout=2.0)

        # Nếu không có race condition, biến đếm phải đạt chuẩn số lượng thread
        self.assertEqual(shared_counter, 20, "Xảy ra Race Condition! Dữ liệu bị ghi đè.")

if __name__ == "__main__":
    unittest.main()