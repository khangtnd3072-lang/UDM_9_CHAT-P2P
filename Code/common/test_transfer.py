import os
import shutil
import socket
import threading
import time

from Code.common.protocol import decode_message
from Code.common.transfer import FileReceiver, FileSender

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
                print(f"[SERVER] Nhận file kết thúc với trạng thái: {result['status']}")
                break
        except Exception:
            break

    conn.close()
    server.close()


def run_test():
    # 1. Tạo file dữ liệu giả định để gửi (~65 KB)
    dummy_filepath = "test_dummy.txt"
    with open(dummy_filepath, "w", encoding="utf-8") as f:
        f.write(
            "Đây là dữ liệu mẫu để thử nghiệm tính năng File Transfer P2P!\n"
            * 1000
        )

    # 2. Chạy Thread Server Nhận
    server_thread = threading.Thread(target=mock_receiver_server, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    # 3. Client kết nối và gửi File
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    sender = FileSender(
        sock=client, sender_name="Khánh", receiver_name="Khang"
    )

    # Biến theo dõi để chỉ print tiến độ khi đạt mốc % nguyên mới (tránh spam Terminal)
    last_printed_pct = -1

    def print_progress(sent, total):
        nonlocal last_printed_pct
        pct = int((sent / total) * 100) if total > 0 else 0
        # Chỉ in log khi tiến độ tăng thêm % nguyên (hoặc mốc 100%)
        if pct != last_printed_pct:
            # Dùng \r để ghi đè trên đúng 1 dòng Terminal
            print(
                f"\r[PROGRESS] Đã gửi: {sent}/{total} bytes ({pct}%)",
                end="",
                flush=True,
            )
            last_printed_pct = pct

    print("=== BẮT ĐẦU TEST CHỨC NĂNG GỬI FILE ===")
    sender.send_file(dummy_filepath, progress_callback=print_progress)
    print()  # Xuống dòng sau khi ghi đè progress xong

    # Chờ thread Server xử lý xong việc lưu file & check SHA256
    server_thread.join(timeout=3)
    client.close()

    # 4. Dọn dẹp file và thư mục test tạm bên trong hàm run_test
    if os.path.exists(dummy_filepath):
        os.remove(dummy_filepath)


    # Xóa file test khi kết thúc test
    if os.path.exists("./test_downloads"):
        shutil.rmtree("./test_downloads")

    print("=== HOÀN THÀNH KIỂM THỬ MÔ ĐUN FILE TRANSFER ===")


if __name__ == "__main__":
    run_test()
