import os
import hashlib
import math
from Code.common.protocol import encode_message, decode_message

# Giới hạn kích thước file gửi tối đa: 10 MB (theo YCKT đề tài)
MAX_FILE_SIZE = 10 * 1024 * 1024  
CHUNK_SIZE = 64 * 1024  # 64 KB mỗi chunk gửi qua socket

def calculate_sha256(filepath):
    """Tính mã băm SHA-256 của file để kiểm tra tính toàn vẹn."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

class FileSender:
    """Xử lý chia file, đóng gói và gửi qua Socket P2P/TCP."""
    def __init__(self, sock, sender_name, receiver_name):
        self.sock = sock
        self.sender = sender_name
        self.receiver = receiver_name

    def send_file(self, filepath, progress_callback=None):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File không tồn tại: {filepath}")

        file_size = os.path.getsize(filepath)
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"Dung lượng file ({file_size / (1024*1024):.2f}MB) vượt quá giới hạn cho phép (10MB).")

        filename = os.path.basename(filepath)
        file_hash = calculate_sha256(filepath)
        total_chunks = math.ceil(file_size / CHUNK_SIZE) if file_size > 0 else 1

        # Step 1: Gửi Metadata khởi tạo file
        meta_payload = {
            "type": "file_meta",
            "sender": self.sender,
            "receiver": self.receiver,
            "filename": filename,
            "file_size": file_size,
            "file_hash": file_hash,
            "total_chunks": total_chunks
        }
        self.sock.sendall(encode_message(meta_payload))

        # Step 2: Đọc từng chunk và gửi dữ liệu (Data Chunks)
        bytes_sent = 0
        with open(filepath, "rb") as f:
            for chunk_index in range(total_chunks):
                chunk_data = f.read(CHUNK_SIZE)
                
                # Mã hóa binary chunk sang chuỗi hex để đóng gói JSON an toàn
                chunk_payload = {
                    "type": "file_chunk",
                    "sender": self.sender,
                    "receiver": self.receiver,
                    "filename": filename,
                    "chunk_index": chunk_index,
                    "data": chunk_data.hex()
                }
                self.sock.sendall(encode_message(chunk_payload))
                
                bytes_sent += len(chunk_data)
                if progress_callback:
                    progress_callback(bytes_sent, file_size)

        print(f"[FILE TRANSFER] Đã gửi hoàn tất file: {filename} ({file_size} bytes)")


class FileReceiver:
    """Xử lý nhận các chunk, ghép file và kiểm tra checksum SHA-256."""
    def __init__(self, save_dir="./downloads"):
        self.save_dir = save_dir
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        self.active_transfers = {}

    def handle_incoming_message(self, msg):
        msg_type = msg.get("type")

        if msg_type == "file_meta":
            filename = msg.get("filename")
            filepath = os.path.join(self.save_dir, filename)
            
            self.active_transfers[filename] = {
                "filepath": filepath,
                "file_size": msg.get("file_size"),
                "expected_hash": msg.get("file_hash"),
                "total_chunks": msg.get("total_chunks"),
                "received_chunks": 0,
                "file_obj": open(filepath, "wb")
            }
            print(f"[FILE TRANSFER] Bắt đầu nhận file: {filename} ({msg.get('file_size')} bytes)")
            return {"status": "receiving", "filename": filename, "progress": 0}

        elif msg_type == "file_chunk":
            filename = msg.get("filename")
            transfer = self.active_transfers.get(filename)

            if not transfer:
                print(f"[ERROR] Nhận chunk cho file chưa đăng ký: {filename}")
                return None

            # Giải mã hex trở lại byte dữ liệu
            chunk_bytes = bytes.fromhex(msg.get("data"))
            transfer["file_obj"].write(chunk_bytes)
            transfer["received_chunks"] += 1

            progress = (transfer["received_chunks"] / transfer["total_chunks"]) * 100

            # Sau khi nhận xong toàn bộ chunk
            if transfer["received_chunks"] == transfer["total_chunks"]:
                transfer["file_obj"].close()
                filepath = transfer["filepath"]
                
                # Kiểm tra tính toàn vẹn SHA-256
                computed_hash = calculate_sha256(filepath)
                if computed_hash.lower() == transfer["expected_hash"].lower():
                    print(f"[FILE TRANSFER] Nhận file {filename} THÀNH CÔNG! Checksum SHA-256 khớp.")
                    status = "completed"
                else:
                    print(f"[FILE TRANSFER] LỖI TOÀN VẸN FILE: Checksum không khớp cho {filename}!")
                    status = "corrupted"

                del self.active_transfers[filename]
                return {"status": status, "filename": filename, "filepath": filepath, "progress": 100}

            return {"status": "receiving", "filename": filename, "progress": progress}

        return None
