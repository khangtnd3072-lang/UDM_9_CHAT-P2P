import socket
import threading

from protocol import decode_message, encode_message


HOST = "127.0.0.1"
PORT = 5000

clients = {}


def handle_client(conn, addr):
    print(f"[+] Client kết nối: {addr}")

    username = None

    try:
        while True:
            message = decode_message(conn)

            print(f"[RECV] {message}")

            username = message.get("sender")

            if username:
                clients[username] = conn

            receiver = message.get("receiver")

            if receiver in clients:

                receiver_socket = clients[receiver]

                data = encode_message(message)

                receiver_socket.sendall(data)

                print(f"[SEND] {username} -> {receiver}")

            else:
                print(f"[INFO] {receiver} chưa online")

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")

    finally:
        if username in clients:
            del clients[username]

        conn.close()

        print(f"[-] Client ngắt kết nối: {addr}")


def start_server():

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, PORT))

    server.listen()

    print(f"Server đang chạy tại {HOST}:{PORT}")

    while True:

        conn, addr = server.accept()

        thread = threading.Thread(
            target=handle_client,
            args=(conn, addr),
            daemon=True
        )

        thread.start()


if __name__ == "__main__":
    start_server()