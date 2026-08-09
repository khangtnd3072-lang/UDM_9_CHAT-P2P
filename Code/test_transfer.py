import socket
import threading
import time
import os

from transfer import FileSender, FileReceiver
from protocol import decode_message

HOST = "127.0.0.1"
PORT = 6000

def mock_receiver_server():
    """Server giả lập để test việc nhận file P2P."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    conn, addr = server.accept()
    receiver = FileReceiver(save_dir="./test_downloads")

    while True:
        try:
            msg = decode_message(conn)
            result = receiver.handle_incoming_message(msg)
            if result and result["status"] in ["completed", "corrupted"]:
                break
        except Exception:
            break

    conn.close()
    server.close()

def run_test():
    # 1. Tạo file dữ liệu giả định để gửi
    dummy_filepath = "test_dummy.txt"
    with open(dummy_filepath, "w", encoding="utf-8") as f:
        f.write("Đây là dữ liệu mẫu để thử nghiệm tính năng File Transfer P2P!\n" * 1000)

    # 2. Chạy Thread Server Nhận
    server_thread = threading.Thread(target=mock_receiver_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # 3. Client kết nối và gửi File
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    sender = FileSender(sock=client, sender_name="Khánh", receiver_name="Khang")

    def print_progress(sent, total):
        print(f"[PROGRESS] Đã gửi: {sent}/{total} bytes ({sent/total*100:.1f}%)")

    print("=== BẮT ĐẦU TEST CHỨC NĂNG GỬI FILE ===")
    sender.send_file(dummy_filepath, progress_callback=print_progress)

    time.sleep(1)
    client.close()

    # Dọn dẹp file test tạm
    if os.path.exists(dummy_filepath):
        os.remove(dummy_filepath)

    print("=== HOÀN THÀNH KIỂM THỬ MÔ ĐUN FILE TRANSFER ===")

if __name__ == "__main__":
    run_test()
