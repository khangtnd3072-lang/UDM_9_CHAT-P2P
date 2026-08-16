# Basic tests for protocol framing and handshake scaffold.
# Run from repo root:
#   cd Code/P2PChat/src
#   python -m unittest ../../common/test_protocol_handshake.py
import threading
import socket
import time
import unittest

# Adjust imports depending on how you run tests (run from Code/P2PChat/src)
try:
    from protocol import encode_message, decode_message
    from handshake import generate_rsa_keypair, client_start_handshake, client_finish_handshake, server_handle_init_and_respond, send_encrypted, recv_encrypted
except Exception:
    # If test is invoked from repo root, adjust sys.path
    import sys
    sys.path.insert(0, "Code/P2PChat/src")
    from protocol import encode_message, decode_message
    from handshake import generate_rsa_keypair, client_start_handshake, client_finish_handshake, server_handle_init_and_respond, send_encrypted, recv_encrypted


HOST = "127.0.0.1"
PORT = 52001  # test port


class TestProtocolHandshake(unittest.TestCase):
    def test_encode_decode_roundtrip(self):
        s1, s2 = socket.socketpair() if hasattr(socket, "socketpair") else _make_local_pair()
        try:
            payload = {"type": "test", "msg": "xin chao"}
            s1.sendall(encode_message(payload))
            got = decode_message(s2, timeout=1.0)
            self.assertEqual(got["type"], "test")
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
            # server generates keys
            sk, spub = generate_rsa_keypair()
            try:
                f = server_handle_init_and_respond(conn, sk, spub)
                # receive encrypted payload from client, decrypt and assert
                msg = recv_encrypted(conn, f, timeout=5.0)
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
            csk, cpub = generate_rsa_keypair()
            # client sends init
            resp = client_start_handshake(cli, "client1", cpub)
            # finish (decrypt session key) using client's private key
            f_client = client_finish_handshake(resp, csk)
            # now send encrypted message
            send_encrypted(cli, f_client, {"hello": "world"})
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
