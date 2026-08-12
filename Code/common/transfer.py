import hashlib
import math
import os
from typing import Callable, Dict, Optional

from Code.common.protocol import encode_message


def log_transfer(message: str, level: str = "INFO"):
    """Ghi log rõ ràng cho từng bước truyền file để debug dễ hơn."""
    print(f"[TRANSFER] {level}: {message}")

# Giới hạn kích thước file gửi tối đa: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024
CHUNK_SIZE = 64 * 1024  # 64 KB mỗi chunk gửi qua socket
DEFAULT_SAVE_DIR = "./downloads"


def calculate_sha256(filepath: str) -> str:
    """Tính mã băm SHA-256 của file để kiểm tra tính toàn vẹn."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as file_obj:
        while True:
            chunk = file_obj.read(8192)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


class FileTransferSender:
    """Xử lý chia file, đóng gói và gửi qua socket TCP/P2P."""

    def __init__(self, sock, sender_name: str, receiver_name: str):
        self.sock = sock
        self.sender = sender_name
        self.receiver = receiver_name

    def send_file(self, filepath: str, progress_callback: Optional[Callable[[int, int], None]] = None):
        log_transfer(f"Bắt đầu gửi file: {filepath}")

        if not os.path.exists(filepath):
            log_transfer(f"Lỗi: file không tồn tại -> {filepath}", "ERROR")
            raise FileNotFoundError(f"File không tồn tại: {filepath}")

        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            log_transfer(
                f"Lỗi: kích thước file vượt quá giới hạn ({file_size} bytes > {MAX_FILE_SIZE} bytes)",
                "ERROR",
            )
            raise ValueError(
                f"Dung lượng file ({file_size / (1024 * 1024):.2f}MB) vượt quá giới hạn cho phép (10MB)."
            )

        filename = os.path.basename(filepath)
        file_hash = calculate_sha256(filepath)
        total_chunks = math.ceil(file_size / CHUNK_SIZE) if file_size > 0 else 1

        log_transfer(f"File hợp lệ: {filename}, size={file_size} bytes, chunks={total_chunks}, sha256={file_hash}")

        meta_payload = {
            "type": "file_meta",
            "sender": self.sender,
            "receiver": self.receiver,
            "filename": filename,
            "file_size": file_size,
            "file_hash": file_hash,
            "total_chunks": total_chunks,
            "chunk_size": CHUNK_SIZE,
        }
        log_transfer(f"Gửi metadata cho file {filename}")
        self._send_message(meta_payload)

        bytes_sent = 0
        with open(filepath, "rb") as file_obj:
            for chunk_index in range(total_chunks):
                chunk_data = file_obj.read(CHUNK_SIZE)
                if not chunk_data:
                    log_transfer(f"Lỗi: chunk rỗng ở index {chunk_index} khi gửi {filename}", "ERROR")
                    break

                chunk_payload = {
                    "type": "file_chunk",
                    "sender": self.sender,
                    "receiver": self.receiver,
                    "filename": filename,
                    "chunk_index": chunk_index,
                    "data": chunk_data.hex(),
                }
                self._send_message(chunk_payload)

                bytes_sent += len(chunk_data)
                log_transfer(f"Đã gửi chunk {chunk_index + 1}/{total_chunks} cho {filename} ({bytes_sent}/{file_size} bytes)")
                if progress_callback:
                    progress_callback(bytes_sent, file_size)

        result = {
            "status": "sent",
            "filename": filename,
            "file_size": file_size,
            "sha256": file_hash,
            "total_chunks": total_chunks,
        }
        log_transfer(f"Gửi file thành công: {filename} | SHA256={file_hash}", "SUCCESS")
        return result

    def _send_message(self, payload: dict) -> None:
        if self.sock is None:
            log_transfer("Lỗi: socket gửi file không hợp lệ", "ERROR")
            raise ValueError("Socket không hợp lệ để gửi file")
        self.sock.sendall(encode_message(payload))


class FileTransferReceiver:
    """Xử lý nhận các chunk, ghép file và kiểm tra checksum SHA-256."""

    def __init__(self, save_dir: str = DEFAULT_SAVE_DIR):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.active_transfers: Dict[str, dict] = {}

    def process_message(self, msg):
        """API chuẩn hóa: nhận một message file transfer và xử lý."""
        return self.handle_incoming_message(msg)

    def receive_message(self, msg):
        """Alias tương thích ngược cho API cũ."""
        return self.handle_incoming_message(msg)

    def handle_incoming_message(self, msg):
        if not isinstance(msg, dict):
            return None

        msg_type = msg.get("type")

        if msg_type == "file_meta":
            return self._handle_meta(msg)

        if msg_type == "file_chunk":
            return self._handle_chunk(msg)

        return None

    def _handle_meta(self, msg: dict):
        filename = msg.get("filename")
        if not filename:
            log_transfer("Lỗi: metadata file thiếu filename", "ERROR")
            return None

        filepath = os.path.join(self.save_dir, filename)
        transfer = {
            "filepath": filepath,
            "file_size": msg.get("file_size"),
            "expected_hash": msg.get("file_hash"),
            "total_chunks": msg.get("total_chunks"),
            "received_chunks": 0,
            "file_obj": open(filepath, "wb"),
        }
        self.active_transfers[filename] = transfer
        log_transfer(f"Bắt đầu nhận file: {filename} | expected_hash={transfer['expected_hash']} | total_chunks={transfer['total_chunks']}")
        return {"status": "receiving", "filename": filename, "progress": 0}

    def _handle_chunk(self, msg: dict):
        filename = msg.get("filename")
        transfer = self.active_transfers.get(filename)

        if transfer is None:
            log_transfer(f"Lỗi: nhận chunk cho file chưa đăng ký -> {filename}", "ERROR")
            return None

        chunk_data = msg.get("data")
        if chunk_data is None:
            log_transfer(f"Lỗi: chunk dữ liệu rỗng cho file {filename}", "ERROR")
            return None

        try:
            chunk_bytes = bytes.fromhex(chunk_data)
        except (TypeError, ValueError):
            log_transfer(f"Lỗi: chunk hex không hợp lệ cho file {filename}", "ERROR")
            return None

        transfer["file_obj"].write(chunk_bytes)
        transfer["received_chunks"] += 1

        total_chunks = transfer.get("total_chunks") or 1
        progress = (transfer["received_chunks"] / total_chunks) * 100 if total_chunks > 0 else 0
        log_transfer(f"Nhận chunk {transfer['received_chunks']}/{total_chunks} cho {filename} ({progress:.1f}%)")

        if transfer["received_chunks"] >= total_chunks:
            transfer["file_obj"].close()
            filepath = transfer["filepath"]

            computed_hash = calculate_sha256(filepath)
            expected_hash = str(transfer.get("expected_hash") or "").lower()
            if computed_hash.lower() == expected_hash:
                del self.active_transfers[filename]
                log_transfer(f"Checksum đúng: {filename} | sha256={computed_hash}", "SUCCESS")
                return {
                    "status": "completed",
                    "filename": filename,
                    "filepath": filepath,
                    "progress": 100,
                }

            del self.active_transfers[filename]
            log_transfer(
                f"Checksum sai: {filename} | expected={expected_hash} | actual={computed_hash}",
                "ERROR",
            )
            return {
                "status": "corrupted",
                "filename": filename,
                "filepath": filepath,
                "progress": 100,
            }

        return {"status": "receiving", "filename": filename, "progress": progress}


# Giữ tên cũ để tương thích ngược với code hiện có.
FileSender = FileTransferSender
FileReceiver = FileTransferReceiver

__all__ = [
    "MAX_FILE_SIZE",
    "CHUNK_SIZE",
    "DEFAULT_SAVE_DIR",
    "calculate_sha256",
    "FileTransferSender",
    "FileTransferReceiver",
    "FileSender",
    "FileReceiver",
]
