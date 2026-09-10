import threading
import socket
import time
import unittest

HOST = "127.0.0.1"
PERF_PORT = 53003

class TestLoadAndPerformance(unittest.TestCase):
    def run_stress_test(self, peer_count):
        server_running = True
        def dummy_echo_server():
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, PERF_PORT))
            srv.listen(100)
            srv.settimeout(0.5)
            while server_running:
                try:
                    conn, _ = srv.accept()
                    data = conn.recv(1024)
                    conn.sendall(data) # Echo lại
                    conn.close()
                except socket.timeout:
                    continue
                except Exception:
                    break
            srv.close()

        srv_thread = threading.Thread(target=dummy_echo_server, daemon=True)
        srv_thread.start()
        time.sleep(0.2)

        errors = 0
        response_times = []

        def client_load():
            nonlocal errors
            start_time = time.time()
            try:
                cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                cli.settimeout(2.0)
                cli.connect((HOST, PERF_PORT))
                cli.sendall(b"PING")
                cli.recv(1024)
                cli.close()
                response_times.append(time.time() - start_time)
            except Exception:
                errors += 1

        threads = []
        for _ in range(peer_count):
            t = threading.Thread(target=client_load)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        server_running = False
        srv_thread.join(timeout=2.0)

        avg_time = sum(response_times) / len(response_times) if response_times else 0
        error_rate = (errors / peer_count) * 100
        
        print(f"\n[Stress Test - {peer_count} peers]")
        print(f"Thời gian phản hồi trung bình: {avg_time:.4f}s")
        print(f"Tỷ lệ lỗi: {error_rate}%")
        
        self.assertLess(avg_time, 1.0, "Thời gian phản hồi quá chậm!")
        self.assertEqual(error_rate, 0.0, "Có lỗi xảy ra trong quá trình chịu tải!")

    def test_load_5_peers(self):
        self.run_stress_test(5)

    def test_load_20_peers(self):
        self.run_stress_test(20)

if __name__ == "__main__":
    unittest.main()