import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Code.P2PChat.src.crypto import CryptoManager


class TestCryptoAdvanced(unittest.TestCase):

    def test_full_security_flow(self):
        print("\n========================================================")
        print("          BẮT ĐẦU CHẠY TEST LUỒNG BẢO MẬT E2EE         ")
        print("========================================================")

        # 1. Khởi tạo
        print("\n[STEP 1] Khởi tạo CryptoManager cho Peer A và Peer B")
        peer_a = CryptoManager()
        peer_b = CryptoManager()
        print(" -> Đã tạo xong cặp khóa RSA 2048-bit riêng biệt cho 2 bên.")

        # 2. Key Fingerprint (Vân tay)
        print("\n[STEP 2] Kiểm tra Vân tay (Key Fingerprint SHA-256)")
        fp_a = peer_a.get_fingerprint()
        fp_b = peer_b.get_fingerprint()
        print(f" -> Fingerprint Peer A: {fp_a}")
        print(f" -> Fingerprint Peer B: {fp_b}")
        self.assertIsNotNone(fp_a)

        # 3. Trao đổi khóa Handshake (RSA -> Fernet Key)
        print("\n[STEP 3] Thực hiện Handshake trao đổi Session Key")
        pub_a = peer_a.get_public_key_pem()
        pub_b = peer_b.get_public_key_pem()

        session_key_a = peer_a.generate_session_key()
        print(f" -> Peer A sinh Session Key: {session_key_a.decode()}")

        encrypted_sk = peer_a.encrypt_session_key(pub_b)
        print(f" -> Peer A mã hóa Session Key bằng RSA Public Key của B (Base64): {encrypted_sk[:40]}...")

        session_key_b = peer_b.decrypt_session_key(encrypted_sk)
        print(f" -> Peer B giải mã bằng RSA Private Key thu được: {session_key_b.decode()}")
        self.assertEqual(session_key_a, session_key_b)

        # 4. Chữ ký số RSA (Digital Signature)
        print("\n[STEP 4] Kiểm tra Chữ ký số (Digital Signature)")
        msg = "Tin nhắn chính chủ từ Peer A (Chống mạo danh)"
        signature_b64 = peer_a.sign_message(msg)
        print(f" -> Nội dung gốc: '{msg}'")
        print(f" -> Chữ ký số của A (Base64): {signature_b64[:40]}...")

        is_valid = peer_b.verify_signature(msg, signature_b64, pub_a)
        print(f" -> Peer B xác minh chữ ký với Public Key A: {is_valid} (HỢP LỆ)")
        self.assertTrue(is_valid)

        is_fake_valid = peer_b.verify_signature(msg + " [ĐÃ BỊ SỬA DỮ LIỆU]", signature_b64, pub_a)
        print(f" -> Thử giả mạo nội dung: {is_fake_valid} (TỪ CHỐI BẢO MẬT)")
        self.assertFalse(is_fake_valid)

        # 5. Mã hóa file chunk
        print("\n[STEP 5] Kiểm tra Mã hóa/Giải mã dữ liệu File (Chunk Bytes)")
        file_chunk = b"Du lieu file nhi phan demo test Sprint 3"
        print(f" -> Chunk gốc: {file_chunk}")

        enc_chunk = peer_a.encrypt_bytes(file_chunk)
        print(f" -> Chunk đã mã hóa (Bytes): {enc_chunk[:30]}...")

        dec_chunk = peer_b.decrypt_bytes(enc_chunk)
        print(f" -> Chunk sau khi B giải mã: {dec_chunk}")
        self.assertEqual(file_chunk, dec_chunk)

        print("\n========================================================")
        print("          HOÀN THÀNH TẤT CẢ CÁC BƯỚC KIỂM THỬ          ")
        print("========================================================\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)