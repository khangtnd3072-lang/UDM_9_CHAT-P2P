# Basic tests for protocol framing and handshake scaffold.
# Run from repo root:
#   cd Code/P2PChat/src
#   python -m unittest ../../common/test_protocol_handshake.py
import threading
import socket
import time
import unittest

from Code.P2PChat.src.crypto import CryptoManager
from Code.P2PChat.src.message.protocol import encode_message, decode_message
from Code.P2PChat.src.handshake import (
    client_finish_handshake,
    client_start_handshake,
    recv_encrypted,
    send_encrypted,
    server_handle_init_and_respond,
)


HOST = "127.0.0.1"
PORT = 52001  # test port


class TestProtocolHandshake(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        s1, s2 = socket.socketpair() if hasattr(socket, "socketpair") else _make_local_pair()
        try:
            payload = {"type": "chat", "msg": "xin chao"}
            s1.sendall(encode_message(payload))
            got = decode_message(s2, timeout=1.0)
            self.assertEqual(got["type"], "chat")
            self.assertEqual(got["msg"], "xin chao")
        finally:
            s1.close(); s2.close()

    def test_handshake_exchange_and_encrypted_message(self):
        # Start server thread
        def server_worker():
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((HOST, PORT))
            srv.listen(1)
            conn, _ = srv.accept()
            server_crypto = CryptoManager()
            try:
                server_handle_init_and_respond(conn, server_crypto)
                # receive encrypted payload from client, decrypt and assert
                msg = recv_encrypted(conn, server_crypto, timeout=5.0)
                self.assertEqual(msg.get("hello"), "world")
            finally:
                conn.close()
                srv.close()

        thr = threading.Thread(target=server_worker, daemon=True)
        thr.start()
        time.sleep(0.1)

        # Client side
        cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cli.connect((HOST, PORT))
        try:
            client_crypto = CryptoManager()
            resp = client_start_handshake(cli, "client1", client_crypto)
            client_finish_handshake(resp, client_crypto)
            # now send encrypted message
            send_encrypted(cli, client_crypto, {"hello": "world"})
        finally:
            cli.close()

        thr.join(timeout=2.0)


# Helper for platforms without socketpair
def _make_local_pair():
    a = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    b = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    a.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    b.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    a.bind(("127.0.0.1", 0))
    a.listen(1)
    port = a.getsockname()[1]
    b.connect(("127.0.0.1", port))
    conn, _ = a.accept()
    a.close()
    return conn, b


if __name__ == "__main__":
    unittest.main()
