import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Code.common.protocol import decode_message
from Code.common.transfer import (
    FileReceiver,
    FileSender,
    MAX_FILE_SIZE,
    calculate_sha256,
)

HOST = "127.0.0.1"
PORT = 6000


def cleanup_artifacts():
    for path in ("test_dummy.txt", "./test_downloads"):
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


class DummySocket:
    def sendall(self, payload):
        pass


def mock_receiver_server(results_list):
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
            result = receiver.process_message(msg)
            if result:
                results_list.append(result)
            if result and result["status"] in ["completed", "corrupted"]:
                print(f"[SERVER] Nhận file kết thúc với trạng thái: {result['status']}")
                break
        except Exception:
            break

    conn.close()
    server.close()


class TestTransferIntegration(unittest.TestCase):
    def setUp(self):
        cleanup_artifacts()

    def tearDown(self):
        cleanup_artifacts()

    def test_send_receive_file_happy_path(self):
        dummy_filepath = "test_dummy.txt"
        with open(dummy_filepath, "w", encoding="utf-8") as f:
            f.write(
                "Đây là dữ liệu mẫu để thử nghiệm tính năng File Transfer P2P!\n"
                * 1000
            )

        results_list = []

        server_thread = threading.Thread(
            target=mock_receiver_server,
            args=(results_list,),
            daemon=True,
        )
        server_thread.start()
        time.sleep(0.5)

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((HOST, PORT))

        sender = FileSender(
            sock=client, sender_name="Khánh", receiver_name="Khang"
        )

        last_printed_pct = -1

        def print_progress(sent, total):
            nonlocal last_printed_pct
            pct = int((sent / total) * 100) if total > 0 else 0
            if pct != last_printed_pct:
                print(
                    f"\r[PROGRESS] Đã gửi: {sent}/{total} bytes ({pct}%)",
                    end="",
                    flush=True,
                )
                last_printed_pct = pct

        print("=== BẮT ĐẦU TEST CHỨC NĂNG GỬI FILE ===")
        send_result = sender.send_file(dummy_filepath, progress_callback=print_progress)
        print()

        server_thread.join(timeout=3)
        client.close()

        self.assertEqual(send_result["status"], "sent")
        self.assertEqual(send_result["filename"], "test_dummy.txt")

        received_result = results_list[-1] if results_list else None
        self.assertIsNotNone(received_result, "Receiver không trả về kết quả nhận file")
        self.assertEqual(received_result["status"], "completed")
        self.assertEqual(received_result["filename"], "test_dummy.txt")

        saved_path = os.path.join("./test_downloads", "test_dummy.txt")
        self.assertTrue(os.path.exists(saved_path), "File đã gửi không được lưu xuống thư mục downloads")
        self.assertEqual(os.path.getsize(saved_path), os.path.getsize(dummy_filepath))
        self.assertEqual(calculate_sha256(saved_path), calculate_sha256(dummy_filepath))

        print("=== HOÀN THÀNH KIỂM THỬ MÔ ĐUN FILE TRANSFER ===")


class TestTransferErrorCases(unittest.TestCase):
    def test_sender_missing_file_raises(self):
        sender = FileSender(sock=DummySocket(), sender_name="A", receiver_name="B")
        with self.assertRaises(FileNotFoundError):
            sender.send_file("/path/that/does/not/exist.txt")

    def test_sender_rejects_over_10mb_file(self):
        sender = FileSender(sock=DummySocket(), sender_name="A", receiver_name="B")
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            fp.write(b"a" * (MAX_FILE_SIZE + 1))
            tmp_path = fp.name

        try:
            with self.assertRaises(ValueError):
                sender.send_file(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_receiver_rejects_unknown_message(self):
        receiver = FileReceiver(save_dir=tempfile.mkdtemp())
        result = receiver.process_message({"type": "chat", "message": "hello"})
        self.assertIsNone(result)

    def test_receiver_chunk_without_meta_returns_none(self):
        receiver = FileReceiver(save_dir=tempfile.mkdtemp())
        result = receiver.receive_message({
            "type": "file_chunk",
            "filename": "ghost.bin",
            "data": "00",
        })
        self.assertIsNone(result)

    def test_receiver_corrupted_hash_status(self):
        src_dir = tempfile.mkdtemp()
        save_dir = tempfile.mkdtemp()
        src_path = os.path.join(src_dir, "source.txt")
        with open(src_path, "wb") as f:
            f.write(b"Xin chao file transfer")

        receiver = FileReceiver(save_dir=save_dir)
        file_hash = calculate_sha256(src_path)

        meta = {
            "type": "file_meta",
            "filename": "source.txt",
            "file_size": os.path.getsize(src_path),
            "file_hash": file_hash,
            "total_chunks": 1,
        }

        result = receiver.process_message(meta)
        self.assertEqual(result, {"status": "receiving", "filename": "source.txt", "progress": 0})

        chunked = {
            "type": "file_chunk",
            "filename": "source.txt",
            "data": b"wrong-data-not-same".hex(),
        }
        final = receiver.process_message(chunked)
        self.assertIsNotNone(final)
        self.assertEqual(final["filename"], "source.txt")
        self.assertEqual(final["status"], "corrupted")

        shutil.rmtree(src_dir)
        shutil.rmtree(save_dir)


if __name__ == "__main__":
    unittest.main()
