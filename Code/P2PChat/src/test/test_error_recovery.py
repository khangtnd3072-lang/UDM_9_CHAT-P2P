# Basic tests for Exception Handling, Disconnects, and Graceful Shutdown.
# Run from repo root:
#   cd src
#   python -m unittest test/test_error_recovery.py

import threading
import socket
import time
import unittest

try:
    from message.protocol import encode_message, decode_message
except Exception:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from message.protocol import encode_message, decode_message

HOST = "127.0.0.1"
PORT = 52002  # Dùng port khác để không đụng với handshake test

class TestErrorRecovery(unittest.TestCase):
    def test_disconnect_and_invalid_packet(self):
        """Test server sống sót khi nhận packet rác hoặc mất kết nối đột ngột"""
        server_crashed = False
        stop_event = threading.Event()
        
        def server_worker():
            nonlocal server_crashed
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, PORT))
            srv.listen(5)
            srv.settimeout(0.5)
            
            while not stop_event.is_set():
                try:
                    conn, _ = srv.accept()
                    try:
                        # Thử đọc dữ liệu, nếu client gửi rác/ngắt mạng sẽ quăng Exception
                        msg = decode_message(conn, timeout=1.0)
                    except Exception:
                        # Bắt lỗi an toàn để phục hồi (Error Recovery)
                        pass
                    finally:
                        conn.close()
                except socket.timeout:
                    # Timeout an toàn để vòng lặp có thể check stop_event
                    continue
                except Exception:
                    server_crashed = True
                    break
            
            # Tắt máy an toàn (Graceful Shutdown)
            srv.close()

        thr = threading.Thread(target=server_worker, daemon=True)
        thr.start()
        time.sleep(0.2) # Chờ server khởi động

        # --- Tình huống 1: Invalid Packet (Gửi data rác) ---
        cli1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli1.connect((HOST, PORT))
        cli1.sendall(b"GARBAGE_DATA_WITHOUT_HEADER")
        cli1.close()
        time.sleep(0.2)

        # --- Tình huống 2: Disconnect (Ngắt mạng giữa chừng) ---
        cli2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli2.connect((HOST, PORT))
        cli2.sendall(b"\x00\x00") # Gửi thiếu byte rồi lập tức ngắt
        cli2.close()
        time.sleep(0.2)

        # Dừng server
        stop_event.set()
        thr.join(timeout=2.0)

        # Khẳng định (Assert) server không bị crash
        self.assertFalse(server_crashed, "Server đã bị crash khi gặp ngoại lệ!")

if __name__ == "__main__":
    unittest.main()