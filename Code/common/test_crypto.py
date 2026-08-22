import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Code.P2PChat.src.crypto import CryptoManager


class TestCryptoIntegration(unittest.TestCase):

    def test_rsa_handshake_and_fernet_chat(self):
        print("\n--- [TEST] 1. Khởi tạo CryptoManager cho Peer A và Peer B ---")
        peer_a = CryptoManager()
        peer_b = CryptoManager()

        print("--- [TEST] 2. Xuất Public Key RSA ---")
        pub_a = peer_a.get_public_key_pem()
        pub_b = peer_b.get_public_key_pem()
        print(f"[Peer A Public Key]:\n{pub_a[:60]}...")
        print(f"[Peer B Public Key]:\n{pub_b[:60]}...")

        print("--- [TEST] 3. Tạo Session Key (A) và Mã hóa bằng Public Key (B) ---")
        session_key_a = peer_a.generate_session_key()
        encrypted_session_key = peer_a.encrypt_session_key(peer_public_key_pem=pub_b)
        print(f"[Session Key Gốc A]: {session_key_a.decode()}")
        print(f"[Session Key Đã Mã Hóa (B64)]: {encrypted_session_key[:50]}...")

        print("--- [TEST] 4. Peer B Giải mã Session Key ---")
        session_key_b = peer_b.decrypt_session_key(encrypted_session_key)
        print(f"[Session Key B Giải Mã]: {session_key_b.decode()}")
        self.assertEqual(session_key_a, session_key_b)

        print("--- [TEST] 5. Mã hóa & Giải mã tin nhắn Text (Fernet) ---")
        secret_msg = "Xin chào! Đây là tin nhắn bảo mật E2EE qua mạng P2P."
        ciphertext = peer_a.encrypt_message(secret_msg)
        print(f"[Tin nhắn gốc]: {secret_msg}")
        print(f"[Tin nhắn mã hóa]: {ciphertext}")

        decrypted_msg = peer_b.decrypt_message(ciphertext)
        print(f"[Tin nhắn giải mã]: {decrypted_msg}")

        self.assertNotEqual(secret_msg, ciphertext)
        self.assertEqual(secret_msg, decrypted_msg)

    def test_uninitialized_fernet_raises_error(self):
        print("\n--- [TEST] Test bắt lỗi khi chưa Handshake mà đòi mã hóa ---")
        crypto = CryptoManager()
        with self.assertRaises(ValueError) as ctx:
            crypto.encrypt_message("Hello")
        print(f"[Bắt lỗi thành công]: {ctx.exception}")


if __name__ == "__main__":
    unittest.main(verbosity=2)