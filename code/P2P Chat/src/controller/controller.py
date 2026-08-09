"""
test_peer_connection.py
------------------------
Test "smoke test" cho peer_main.py: khoi dong 2 listener gia lap 2 peer
tren cung may (127.0.0.1, 2 port khac nhau), cho 1 ben connect() sang ben
kia, gui thu 1 tin nhan CHAT, va kiem tra ben nhan co nhan dung noi dung
khong.

Day la loopback local (127.0.0.1) - khong can ket noi Internet, khong can
mo cong ra ngoai, nhung van test duoc toan bo luong TCP that (bind/listen/
accept/connect/send/recv) giong het khi 2 peer that noi voi nhau.
"""

import socket
import sys
import os
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.protocol import MessageType, send_message, recv_message


def _echo_listener(port: int, received_box: list):
    """Peer B don gian: lang nghe 1 ket noi, nhan dung 1 message roi luu lai."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", port))
    server_sock.listen(1)

    conn, _addr = server_sock.accept()
    msg_type, payload = recv_message(conn)
    received_box.append((msg_type, payload))
    conn.close()
    server_sock.close()


def test_connect_and_send_chat_message():
    port = 51234
    received = []

    listener = threading.Thread(target=_echo_listener, args=(port, received), daemon=True)
    listener.start()
    time.sleep(0.2)  # doi listener san sang truoc khi connect

    # Peer A dong vai client: connect toi Peer B va gui CHAT
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))
    send_message(client_sock, MessageType.CHAT, {"text": "chao ban, day la test"})

    listener.join(timeout=3)
    client_sock.close()

    assert len(received) == 1, "Peer B phai nhan duoc dung 1 message"
    msg_type, payload = received[0]
    assert msg_type == "CHAT"
    assert payload["text"] == "chao ban, day la test"
    print("[OK] test_connect_and_send_chat_message")


def test_two_way_messages_on_same_connection():
    """Kiem tra gui nhieu message lien tiep tren CUNG 1 ket noi (khong bi lan/mat frame)."""
    port = 51235
    received = []

    def _multi_msg_listener():
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(("127.0.0.1", port))
        server_sock.listen(1)
        conn, _addr = server_sock.accept()
        for _ in range(3):
            received.append(recv_message(conn))
        conn.close()
        server_sock.close()

    listener = threading.Thread(target=_multi_msg_listener, daemon=True)
    listener.start()
    time.sleep(0.2)

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))
    send_message(client_sock, MessageType.CHAT, {"text": "tin 1"})
    send_message(client_sock, MessageType.CHAT, {"text": "tin 2"})
    send_message(client_sock, MessageType.CHAT, {"text": "tin 3"})

    listener.join(timeout=3)
    client_sock.close()

    assert [p["text"] for _, p in received] == ["tin 1", "tin 2", "tin 3"], (
        "3 message gui lien tiep phai duoc nhan dung thu tu, khong bi lan frame"
    )
    print("[OK] test_two_way_messages_on_same_connection")


if __name__ == "__main__":
    test_connect_and_send_chat_message()
    test_two_way_messages_on_same_connection()
    print("\nTat ca test PASS.")