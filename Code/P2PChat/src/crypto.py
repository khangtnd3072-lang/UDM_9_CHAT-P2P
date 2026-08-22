import base64
from typing import Optional, Tuple
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet


class CryptoManager:
    """
    Quản lý mã hóa End-to-End cho P2P Chat:
    - RSA (2048-bit): Trao đổi Session Key an toàn qua quá trình Handshake.
    - Fernet (AES-128-CBC): Mã hóa/giải mã tin nhắn text và dữ liệu nhanh chóng.
    """

    def __init__(self):
        # Tạo cặp khóa RSA cho bản thân khi khởi tạo instance
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        self.fernet: Optional[Fernet] = None
        self.session_key: Optional[bytes] = None

    # 1. RSA HANDSHAKE & SESSION KEY EXCHANGE

    def get_public_key_pem(self) -> str:
        """Xuất Public Key RSA dưới dạng chuỗi PEM (B64/String) để gửi trong HANDSHAKE."""
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode("utf-8")

    def generate_session_key(self) -> bytes:
        """Tạo Fernet Key đối xứng ngẫu nhiên cho phiên làm việc này."""
        self.session_key = Fernet.generate_key()
        self.fernet = Fernet(self.session_key)
        return self.session_key

    def set_session_key(self, raw_session_key: bytes) -> None:
        """Gán trực tiếp Session Key (dành cho bên nhận)."""
        self.session_key = raw_session_key
        self.fernet = Fernet(raw_session_key)

    def encrypt_session_key(self, peer_public_key_pem: str, raw_session_key: Optional[bytes] = None) -> str:
        """
        Dùng Public Key RSA của đối phương để mã hóa Session Key.
        Trả về chuỗi Base64 để gửi qua gói tin JSON 'SESSION_KEY'.
        """
        key_to_encrypt = raw_session_key or self.session_key
        if not key_to_encrypt:
            raise ValueError("Chưa có Session Key để mã hóa!")

        peer_public_key = serialization.load_pem_public_key(
            peer_public_key_pem.encode("utf-8")
        )

        encrypted = peer_public_key.encrypt(
            key_to_encrypt,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return base64.b64encode(encrypted).decode("utf-8")

    def decrypt_session_key(self, encrypted_session_key_b64: str) -> bytes:
        """
        Dùng Private Key RSA của mình để giải mã Session Key nhận từ đối phương,
        sau đó khởi tạo Fernet engine.
        """
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
        return raw_session_key


    # 2. FERNET PAYLOAD ENCRYPTION / DECRYPTION


    def encrypt_message(self, plaintext: str) -> str:
        """Mã hóa tin nhắn văn bản bản rõ bằng Session Key."""
        if not self.fernet:
            raise ValueError("Session Key chưa được thiết lập! Hãy hoàn thành Handshake trước.")
        
        cipher_bytes = self.fernet.encrypt(plaintext.encode("utf-8"))
        return cipher_bytes.decode("utf-8")

    def decrypt_message(self, ciphertext: str) -> str:
        """Giải mã tin nhắn văn bản mã hóa bằng Session Key."""
        if not self.fernet:
            raise ValueError("Session Key chưa được thiết lập! Hãy hoàn thành Handshake trước.")

        plain_bytes = self.fernet.decrypt(ciphertext.encode("utf-8"))
        return plain_bytes.decode("utf-8")