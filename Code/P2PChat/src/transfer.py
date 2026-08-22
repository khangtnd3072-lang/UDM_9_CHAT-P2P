import os
import math
import logging
from typing import Optional
from Code.P2PChat.src.crypto import CryptoManager

CHUNK_SIZE = 32 * 1024  # 32 KB per chunk
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [TRANSFER]: %(message)s", datefmt="%H:%M:%S")


class FileSender:
    def __init__(self, filepath: str, crypto_mgr: Optional[CryptoManager] = None):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File không tồn tại: {filepath}")

        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.file_size = os.path.getsize(filepath)
        self.total_chunks = math.ceil(self.file_size / CHUNK_SIZE) if self.file_size > 0 else 1
        self.current_chunk = 0
        self.crypto_mgr = crypto_mgr
        logging.info(f"Bắt đầu gửi file: '{self.filename}' ({self.file_size} bytes, {self.total_chunks} chunks)")

    def get_next_chunk(self) -> bytes:
        if self.is_complete():
            return b""

        with open(self.filepath, "rb") as f:
            f.seek(self.current_chunk * CHUNK_SIZE)
            raw_data = f.read(CHUNK_SIZE)

        chunk_idx = self.current_chunk
        self.current_chunk += 1

        if self.crypto_mgr and self.crypto_mgr.fernet:
            enc_data = self.crypto_mgr.encrypt_bytes(raw_data)
            logging.info(f"Đã đọc & MÃ HÓA Chunk #{chunk_idx + 1}/{self.total_chunks} ({len(enc_data)} bytes)")
            return enc_data

        logging.info(f"Đã đọc Chunk #{chunk_idx + 1}/{self.total_chunks} ({len(raw_data)} bytes)")
        return raw_data

    def is_complete(self) -> bool:
        return self.current_chunk >= self.total_chunks


class FileReceiver:
    def __init__(self, save_path: str, file_size: int, crypto_mgr: Optional[CryptoManager] = None):
        self.save_path = save_path
        self.file_size = file_size
        self.total_chunks = math.ceil(file_size / CHUNK_SIZE) if file_size > 0 else 1
        self.received_chunks = set()
        self.crypto_mgr = crypto_mgr

        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        with open(self.save_path, "wb") as f:
            pass
        logging.info(f"Khởi tạo nhận file: Save path = '{save_path}' ({self.total_chunks} chunks dự kiến)")

    def write_chunk(self, chunk_index: int, chunk_data: bytes) -> bool:
        if chunk_index in self.received_chunks:
            return False

        if self.crypto_mgr and self.crypto_mgr.fernet:
            decrypted_data = self.crypto_mgr.decrypt_bytes(chunk_data)
            logging.info(f"Đã GIẢI MÃ & Ghi Chunk #{chunk_index + 1}/{self.total_chunks}")
        else:
            decrypted_data = chunk_data
            logging.info(f"Đã ghi Chunk #{chunk_index + 1}/{self.total_chunks}")

        with open(self.save_path, "r+b") as f:
            f.seek(chunk_index * CHUNK_SIZE)
            f.write(decrypted_data)

        self.received_chunks.add(chunk_index)
        logging.info(f"Tiến độ nhận file: {self.get_progress()}%")
        return True

    def get_progress(self) -> float:
        if self.total_chunks == 0:
            return 100.0
        return round((len(self.received_chunks) / self.total_chunks) * 100, 2)

    def is_complete(self) -> bool:
        return len(self.received_chunks) >= self.total_chunks