import socket
import threading

from protocol import decode_message, encode_message


HOST = "127.0.0.1"
PORT = 5000


def receive_messages(sock):

    while True:
        try:
            message = decode_message(sock)

            print(
                f"\n[{message.get('sender')}] "
                f"{message.get('message')}"
            )

        except Exception as e:
            print(f"\n[ERROR] Mất kết nối server: {e}")
            break


def start_client():

    username = input("Nhập tên của bạn: ")
    receiver = input("Nhập tên người nhận: ")

    client = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    client.connect((HOST, PORT))

    print("Đã kết nối tới server.")
    print("Nhập tin nhắn, gõ 'exit' để thoát.")

    thread = threading.Thread(
        target=receive_messages,
        args=(client,),
        daemon=True
    )

    thread.start()

    while True:

        message_text = input("Bạn: ")

        if message_text.lower() == "exit":
            break

        message = {
            "type": "chat",
            "sender": username,
            "receiver": receiver,
            "message": message_text
        }

        # 1. Mã hóa tin nhắn
        data = encode_message(message)

        # 2. In kích thước gói tin ra terminal
        print(f"[DEBUG] Kích thước gói tin gửi đi: {len(data)} bytes")

        # 3. Gửi dữ liệu qua socket
        client.sendall(data)

    client.close()


if __name__ == "__main__":
    start_client()
