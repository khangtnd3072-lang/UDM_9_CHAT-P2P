import argparse
import socket
import threading

from protocol import decode_message, encode_message


HOST = "127.0.0.1"
PORT = 5000


# SERVER

clients: dict[str, socket.socket] = {}
clients_lock = threading.Lock()


def handle_client(conn, addr):
    print(f"[+] Client ket noi: {addr}")

    username = None

    try:
        while True:
            message = decode_message(conn)

            print(f"[RECV] {message}")

            sender = message.get("sender")
            if sender and sender != username:
                # Lan dau nhan duoc ten, hoac ten thay doi -> dang ky/cap nhat.
                username = sender
                with clients_lock:
                    clients[username] = conn

            receiver = message.get("receiver")

            with clients_lock:
                receiver_socket = clients.get(receiver)

            if receiver_socket is not None:
                data = encode_message(message)
                try:
                    receiver_socket.sendall(data)
                    print(f"[SEND] {username} -> {receiver}")
                except OSError as e:
                    print(f"[ERROR] Gui toi {receiver} that bai: {e}")
            else:
                print(f"[INFO] {receiver} chua online")

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")

    finally:
        with clients_lock:
            if username in clients:
                del clients[username]
        conn.close()
        print(f"[-] Client ngat ket noi: {addr}")


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    print(f"Server dang chay tai {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(
            target=handle_client, args=(conn, addr), daemon=True
        )
        thread.start()


#CLIENT

def receive_messages(sock):
    while True:
        try:
            message = decode_message(sock)
            print(f"\n[{message.get('sender')}] {message.get('message')}")

        except Exception as e:
            print(f"\n[ERROR] Mat ket noi server: {e}")
            break


def start_client():
    username = input("Nhap ten cua ban: ")
    receiver = input("Nhap ten nguoi nhan: ")

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))

    print("Da ket noi toi server.")
    print("Nhap tin nhan, go 'exit' de thoat.")

    thread = threading.Thread(
        target=receive_messages, args=(client,), daemon=True
    )
    thread.start()

    while True:
        message_text = input("Ban: ")

        if message_text.lower() == "exit":
            break

        message = {
            "type": "chat",
            "sender": username,
            "receiver": receiver,
            "message": message_text,
        }

        data = encode_message(message)
        print(f"[DEBUG] Kich thuoc goi tin gui di: {len(data)} bytes")
        client.sendall(data)

    client.close()


# ==========================================================================
# ENTRY POINT: chọn chế độ chạy
# ==========================================================================
def main():
    parser = argparse.ArgumentParser(description="Chat relay Server/Client ")
    parser.add_argument(
        "--mode",
        choices=["server", "client"],
        required=True,
        help="Chay o che do server hay client",
    )
    args = parser.parse_args()

    if args.mode == "server":
        start_server()
    else:
        start_client()


if __name__ == "__main__":
    main()