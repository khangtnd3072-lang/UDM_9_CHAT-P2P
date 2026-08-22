# import base64
# from typing import Tuple
# import socket

# from cryptography.hazmat.primitives.asymmetric import rsa, padding
# from cryptography.hazmat.primitives import serialization, hashes
# from cryptography.fernet import Fernet

# from protocol import encode_message, decode_message


# # RSA helpers 

# def generate_rsa_keypair(key_size: int = 2048) -> Tuple[rsa.RSAPrivateKey, bytes]:
#     """Generate RSA private key and return (private_key, public_pem_bytes)."""
#     private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
#     public_pem = private_key.public_key().public_bytes(
#         encoding=serialization.Encoding.PEM,
#         format=serialization.PublicFormat.SubjectPublicKeyInfo,
#     )
#     return private_key, public_pem


# def load_public_key(pem_bytes: bytes):
#     return serialization.load_pem_public_key(pem_bytes)


# def rsa_encrypt(pubkey_pem: bytes, plaintext: bytes) -> bytes:
#     pub = load_public_key(pubkey_pem)
#     return pub.encrypt(
#         plaintext,
#         padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
#     )


# def rsa_decrypt(private_key, ciphertext: bytes) -> bytes:
#     return private_key.decrypt(
#         ciphertext,
#         padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
#     )


# # ---------- Handshake sequence (minimal) ----------
# # Messages are JSON objects encoded by protocol.encode_message.
# # Client -> Server:
# #   { "type":"handshake_init", "client_id": "...", "client_pub": "<PEM str>" }
# # Server -> Client:
# #   { "type":"handshake_resp", "server_pub": "<PEM str>", "enc_session_key": "<base64>" }
# #
# # After client decrypts enc_session_key -> gets raw 32-byte key usable by Fernet.

# def client_start_handshake(sock: socket.socket, client_id: str, client_pub_pem: bytes, timeout: float = 5.0):
#     """Client sends handshake_init and waits for response, returns Fernet object."""
#     payload = {
#         "type": "handshake_init",
#         "client_id": client_id,
#         "client_pub": client_pub_pem.decode("utf-8"),
#     }
#     sock.sendall(encode_message(payload))
#     resp = decode_message(sock, timeout=timeout)
#     if resp.get("type") != "handshake_resp":
#         raise ValueError("Unexpected handshake response type")
#     enc_b64 = resp.get("enc_session_key")
#     if not enc_b64:
#         raise ValueError("Missing enc_session_key in handshake_resp")
#     enc_bytes = base64.b64decode(enc_b64)
#     # Client must have its private key to decrypt (the caller should provide it)
#     # Note: this function does not hold private key; caller should call client_finish_handshake()
#     return resp  # return raw response for caller to decrypt


# def client_finish_handshake(response: dict, client_private_key) -> Fernet:
#     """Given server response dict and client's private key, return Fernet object."""
#     enc_b64 = response["enc_session_key"]
#     enc_bytes = base64.b64decode(enc_b64)
#     session_key = rsa_decrypt(client_private_key, enc_bytes)
#     # session_key expected to be a Fernet key (base64 urlsafe 32 bytes)
#     return Fernet(session_key)


# def server_handle_init_and_respond(sock: socket.socket, server_private_key, server_pub_pem: bytes, timeout: float = 5.0):
#     """Server waits for handshake_init, then generates session key, sends encrypted session key back.
#     Returns the generated Fernet object (so server can decrypt/encrypt payloads with same key).
#     """
#     req = decode_message(sock, timeout=timeout)
#     if req.get("type") != "handshake_init":
#         raise ValueError("Expected handshake_init")
#     client_pub_pem_str = req.get("client_pub")
#     if not client_pub_pem_str:
#         raise ValueError("handshake_init missing client_pub")
#     client_pub_pem = client_pub_pem_str.encode("utf-8")
#     # generate session key (Fernet key)
#     session_key = Fernet.generate_key()  # already base64 urlsafe bytes
#     # encrypt session key with client's RSA public key
#     enc = rsa_encrypt(client_pub_pem, session_key)
#     enc_b64 = base64.b64encode(enc).decode("utf-8")
#     resp = {
#         "type": "handshake_resp",
#         "server_pub": server_pub_pem.decode("utf-8"),
#         "enc_session_key": enc_b64,
#     }
#     sock.sendall(encode_message(resp))
#     # server returns a Fernet object to use for this connection
#     return Fernet(session_key)


# # ---------- Helpers for encrypted messaging after handshake ----------

# def send_encrypted(sock: socket.socket, f: Fernet, payload: dict):
#     """Encrypt JSON-serializable payload (dict) using Fernet; wrap into {type: 'enc', data: '<token>'}"""
#     import json
#     body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
#     token = f.encrypt(body)  
#     b64 = token.decode("utf-8")  
#     msg = {"type": "enc", "data": b64}
#     sock.sendall(encode_message(msg))


# def recv_encrypted(sock: socket.socket, f: Fernet, timeout: float = None):
#     obj = decode_message(sock, timeout=timeout)
#     if obj.get("type") != "enc":
#         raise ValueError("Expected enc message")
#     token = obj["data"].encode("utf-8")
#     plain = f.decrypt(token)
#     import json
#     return json.loads(plain.decode("utf-8"))



import logging
from typing import Dict, Any

from Code.P2PChat.src.crypto import CryptoManager
from Code.P2PChat.src.protocol import encode_message, decode_message

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [HANDSHAKE]: %(message)s", datefmt="%H:%M:%S")


def client_start_handshake(sock, client_id: str, crypto: CryptoManager, timeout: float = 5.0) -> Dict[str, Any]:
    payload = {
        "type": "handshake_init",
        "client_id": client_id,
        "client_pub": crypto.get_public_key_pem(),
        "fingerprint": crypto.get_fingerprint(),
    }
    payload["signature"] = crypto.sign_message(client_id)
    sock.sendall(encode_message(payload))
    
    resp = decode_message(sock, timeout=timeout)
    if resp.get("type") != "handshake_resp":
        raise ValueError(f"Lỗi Handshake: Nhận phản hồi không hợp lệ ({resp.get('type')})")
    return resp


def client_finish_handshake(response: dict, crypto: CryptoManager) -> None:
    enc_b64 = response.get("enc_session_key")
    if not enc_b64:
        raise ValueError("Thiếu enc_session_key trong handshake_resp!")
    crypto.decrypt_session_key(enc_b64)


def server_handle_init_and_respond(sock, crypto: CryptoManager, timeout: float = 5.0) -> str:
    req = decode_message(sock, timeout=timeout)
    if req.get("type") != "handshake_init":
        raise ValueError(f"Lỗi Handshake: Kỳ vọng handshake_init nhưng nhận {req.get('type')}")

    client_pub_pem = req.get("client_pub")
    client_id = req.get("client_id")

    if not client_pub_pem or not client_id:
        raise ValueError("handshake_init thiếu thông tin client_pub hoặc client_id!")

    crypto.generate_session_key()
    enc_b64 = crypto.encrypt_session_key(client_pub_pem)

    resp = {
        "type": "handshake_resp",
        "server_pub": crypto.get_public_key_pem(),
        "enc_session_key": enc_b64,
        "fingerprint": crypto.get_fingerprint(),
    }
    sock.sendall(encode_message(resp))
    return client_id


def send_encrypted(sock, crypto: CryptoManager, payload: dict):
    import json
    raw_str = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    enc_data = crypto.encrypt_message(raw_str)
    msg = {"type": "enc", "data": enc_data}
    sock.sendall(encode_message(msg))


def recv_encrypted(sock, crypto: CryptoManager, timeout: float = None) -> dict:
    import json
    obj = decode_message(sock, timeout=timeout)
    if obj.get("type") != "enc":
        raise ValueError("Kỳ vọng gói tin mã hóa dạng 'enc'!")
    decrypted_str = crypto.decrypt_message(obj["data"])
    return json.loads(decrypted_str)