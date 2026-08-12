"""
Loopback smoke test requested for the peer TCP path.

It starts two TCP listeners on 127.0.0.1 using different ports, connects
peer A to peer B, sends one CHAT frame, and verifies the exact message.
"""

import json
import os
import socket
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from controller.framing import recv_packet, encode_packet


def test_two_peers_exchange_chat():
    received = []
    ready = threading.Event()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port_b = server.getsockname()[1]

    def listener():
        ready.set()
        conn, _ = server.accept()
        try:
            data = recv_packet(conn)
            received.append(json.loads(data.decode("utf-8")))
        finally:
            conn.close()
            server.close()

    thread = threading.Thread(target=listener, daemon=True)
    thread.start()
    ready.wait(timeout=2)

    client = socket.create_connection(("127.0.0.1", port_b), timeout=2)
    message = {
        "type": "CHAT",
        "sender": "Khoi",
        "receiver": "Tai",
        "message": "Hello from peer A",
    }
    client.sendall(encode_packet(json.dumps(message, ensure_ascii=False).encode("utf-8")))
    client.close()
    thread.join(timeout=2)

    assert received == [message]


if __name__ == "__main__":
    test_two_peers_exchange_chat()
    print("SMOKE TEST: PASS")
