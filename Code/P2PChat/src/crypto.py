import base64
import hashlib
import logging
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet

# Cấu hình logging hệ thống
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [CRYPTO]: %(message)s", datefmt="%H:%M:%S")


class CryptoManager:
    def __init__(self):
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.fernet: Optional[Fernet] = None
        self.session_key: Optional[bytes] = None
        logging.info("Khởi tạo CryptoManager - Đã tạo xong cặp khóa RSA 2048-bit.")

    def get_public_key_pem(self) -> str:
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode("utf-8")

    def get_fingerprint(self, pem_str: Optional[str] = None) -> str:
        target_pem = pem_str or self.get_public_key_pem()
        digest = hashlib.sha256(target_pem.encode("utf-8")).digest()
        fp = ":".join(f"{b:02X}" for b in digest[:16])
        logging.info(f"Đã xuất Fingerprint SHA-256: {fp}")
        return fp

    def generate_session_key(self) -> bytes:
        self.session_key = Fernet.generate_key()
        self.fernet = Fernet(self.session_key)
        logging.info(f"Sinh Session Key Fernet mới: {self.session_key.decode()}")
        return self.session_key

    def set_session_key(self, raw_session_key: bytes) -> None:
        self.session_key = raw_session_key
        self.fernet = Fernet(raw_session_key)
        logging.info("Đã thiết lập Session Key Fernet thành công.")

    def encrypt_session_key(self, peer_public_key_pem: str) -> str:
        if not self.session_key:
            raise ValueError("Chưa khởi tạo Session Key!")
            
        peer_public_key = serialization.load_pem_public_key(peer_public_key_pem.encode("utf-8"))
        encrypted = peer_public_key.encrypt(
            self.session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        enc_b64 = base64.b64encode(encrypted).decode("utf-8")
        logging.info(f"Mã hóa Session Key bằng RSA Public Key đối phương: {enc_b64[:30]}...")
        return enc_b64

    def decrypt_session_key(self, encrypted_session_key_b64: str) -> bytes:
        encrypted_bytes = base64.b64decode(encrypted_session_key_b64)
        raw_session_key = self.private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        self.set_session_key(raw_session_key)
        logging.info("Giải mã Session Key bằng RSA Private Key thành công!")
        return raw_session_key

    def sign_message(self, message: str) -> str:
        signature = self.private_key.sign(
            message.encode("utf-8"),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        sig_b64 = base64.b64encode(signature).decode("utf-8")
        logging.info(f"Ký số thành công trên dữ liệu - Signature: {sig_b64[:30]}...")
        return sig_b64

    def verify_signature(self, message: str, signature_b64: str, peer_public_key_pem: str) -> bool:
        peer_public_key = serialization.load_pem_public_key(peer_public_key_pem.encode("utf-8"))
        try:
            peer_public_key.verify(
                base64.b64decode(signature_b64),
                message.encode("utf-8"),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            logging.info("Xác minh Chữ ký số thành công: HỢP LỆ")
            return True
        except Exception:
            logging.warning("Xác minh Chữ ký số thất bại: CÓ DẤU HIỆU BỊ SỬA ĐỔI HOẶC GIẢ MẠO!")
            return False

    def encrypt_message(self, plaintext: str) -> str:
        if not self.fernet:
            raise ValueError("Chưa có Session Key!")
        cipher = self.fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
        logging.info(f"Mã hóa tin nhắn text -> Ciphertext: {cipher[:30]}...")
        return cipher

    def decrypt_message(self, ciphertext: str) -> str:
        if not self.fernet:
            raise ValueError("Chưa có Session Key!")
        plain = self.fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        logging.info(f"Giải mã tin nhắn text -> Plaintext: {plain}")
        return plain

    def encrypt_bytes(self, raw_data: bytes) -> bytes:
        if not self.fernet:
            raise ValueError("Chưa có Session Key!")
        return self.fernet.encrypt(raw_data)

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        if not self.fernet:
            raise ValueError("Chưa có Session Key!")
        return self.fernet.decrypt(encrypted_data)