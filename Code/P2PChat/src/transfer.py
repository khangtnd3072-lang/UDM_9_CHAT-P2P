import hashlib
import logging
import math
import os
from pathlib import Path
from typing import Optional

from Code.P2PChat.src.crypto import CryptoManager
from Code.P2PChat.src.message.protocol import decode_message, encode_message

CHUNK_SIZE = 32 * 1024
MAX_FILE_SIZE = 10 * 1024 * 1024

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [TRANSFER]: %(message)s",
    datefmt="%H:%M:%S",
)


def calculate_sha256(filepath: str) -> str:
    digest = hashlib.sha256()
    with open(filepath, "rb") as file_handle:
        for block in iter(lambda: file_handle.read(CHUNK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


class FileSender:
    """Send files using framed protocol messages or expose chunk-level API."""

    def __init__(
        self,
        filepath: Optional[str] = None,
        crypto_mgr: Optional[CryptoManager] = None,
        sock=None,
        sender_name: str = "",
        receiver_name: str = "",
    ):
        self.sock = sock
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.crypto_mgr = crypto_mgr
        self.filepath = None
        self.filename = ""
        self.file_size = 0
        self.total_chunks = 0
        self.current_chunk = 0

        if filepath is not None:
            self._load_file(filepath)

    def _load_file(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File không tồn tại: {filepath}")
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.file_size = os.path.getsize(filepath)
        if self.file_size > MAX_FILE_SIZE:
            raise ValueError(f"File vượt quá giới hạn {MAX_FILE_SIZE} bytes")
        self.total_chunks = math.ceil(self.file_size / CHUNK_SIZE) if self.file_size else 1
        self.current_chunk = 0

    def get_next_chunk(self) -> bytes:
        if self.is_complete():
            return b""
        with open(self.filepath, "rb") as file_handle:
            file_handle.seek(self.current_chunk * CHUNK_SIZE)
            raw_data = file_handle.read(CHUNK_SIZE)
        self.current_chunk += 1
        if self.crypto_mgr and self.crypto_mgr.fernet:
            return self.crypto_mgr.encrypt_bytes(raw_data)
        return raw_data

    def send_file(self, filepath: str, progress_callback=None) -> dict:
        if self.sock is None:
            raise ValueError("FileSender cần sock để dùng send_file()")
        self._load_file(filepath)

        # Metadata and every chunk use the same length-prefixed protocol.
        self.sock.sendall(encode_message({
            "type": "file_meta",
            "filename": self.filename,
            "file_size": self.file_size,
            "file_hash": calculate_sha256(self.filepath),
            "total_chunks": self.total_chunks,
            "sender": self.sender_name,
            "receiver": self.receiver_name,
        }))

        sent = 0
        while not self.is_complete():
            chunk_index = self.current_chunk
            chunk_data = self.get_next_chunk()
            self.sock.sendall(encode_message({
                "type": "file_chunk",
                "filename": self.filename,
                "chunk_index": chunk_index,
                "data": chunk_data.hex(),
            }))
            sent += min(CHUNK_SIZE, self.file_size - sent)
            if progress_callback:
                progress_callback(sent, self.file_size)

        return {"status": "sent", "filename": self.filename}

    def is_complete(self) -> bool:
        return self.current_chunk >= self.total_chunks


class FileReceiver:
    """Receive framed file messages or write already-decoded chunks directly."""

    def __init__(
        self,
        save_path: Optional[str] = None,
        file_size: Optional[int] = None,
        crypto_mgr: Optional[CryptoManager] = None,
        save_dir: Optional[str] = None,
    ):
        self.crypto_mgr = crypto_mgr
        self.save_dir = Path(save_dir) if save_dir else None
        self.save_path = save_path
        self.file_size = file_size or 0
        self.total_chunks = 0
        self.received_chunks = set()
        self.expected_hash = None
        self.filename = Path(save_path).name if save_path else None
        if save_path is not None and file_size is not None:
            self._initialize_file()

    def _initialize_file(self) -> None:
        self.total_chunks = math.ceil(self.file_size / CHUNK_SIZE) if self.file_size else 1
        os.makedirs(os.path.dirname(os.path.abspath(self.save_path)), exist_ok=True)
        with open(self.save_path, "wb"):
            pass

    def _start_metadata(self, message: dict) -> dict:
        self.filename = os.path.basename(message["filename"])
        self.file_size = int(message.get("file_size", message.get("filesize", 0)))
        if self.file_size > MAX_FILE_SIZE:
            raise ValueError(f"File vượt quá giới hạn {MAX_FILE_SIZE} bytes")
        self.total_chunks = int(message.get("total_chunks") or (math.ceil(self.file_size / CHUNK_SIZE) if self.file_size else 1))
        self.expected_hash = message.get("file_hash")
        self.save_path = str((self.save_dir or Path(".")) / self.filename)
        self.received_chunks.clear()
        # save_dir may be created lazily because metadata defines the filename.
        os.makedirs(os.path.dirname(os.path.abspath(self.save_path)), exist_ok=True)
        with open(self.save_path, "wb"):
            pass
        return {"status": "receiving", "filename": self.filename, "progress": 0}

    def write_chunk(self, chunk_index: int, chunk_data: bytes) -> bool:
        if chunk_index < 0 or chunk_index >= self.total_chunks or chunk_index in self.received_chunks:
            return False
        decrypted_data = self.crypto_mgr.decrypt_bytes(chunk_data) if self.crypto_mgr and self.crypto_mgr.fernet else chunk_data
        with open(self.save_path, "r+b") as file_handle:
            file_handle.seek(chunk_index * CHUNK_SIZE)
            file_handle.write(decrypted_data)
        self.received_chunks.add(chunk_index)
        return True

    def process_message(self, message: dict) -> Optional[dict]:
        message_type = message.get("type")
        if message_type == "file_meta":
            return self._start_metadata(message)
        if message_type != "file_chunk" or self.save_path is None:
            return None
        try:
            chunk_index = int(message.get("chunk_index", len(self.received_chunks)))
            chunk_data = bytes.fromhex(message["data"])
            self.write_chunk(chunk_index, chunk_data)
        except (KeyError, ValueError, TypeError):
            return {"status": "corrupted", "filename": self.filename}
        if not self.is_complete():
            return {"status": "receiving", "filename": self.filename, "progress": self.get_progress()}
        status = "completed"
        if self.expected_hash and calculate_sha256(self.save_path) != self.expected_hash:
            status = "corrupted"
        return {"status": status, "filename": self.filename}

    def receive_message(self, message: dict) -> Optional[dict]:
        return self.process_message(message)

    def get_progress(self) -> float:
        return round((len(self.received_chunks) / self.total_chunks) * 100, 2) if self.total_chunks else 100.0

    def is_complete(self) -> bool:
        return len(self.received_chunks) >= self.total_chunks