import os
import socket
import threading
import logging
from Code.P2PChat.src.crypto import CryptoManager
from Code.P2PChat.src.handshake import (
    client_start_handshake,
    client_finish_handshake,
    server_handle_init_and_respond,
    send_encrypted,
    recv_encrypted,
)
from Code.P2PChat.src.transfer import FileSender, FileReceiver, CHUNK_SIZE

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(threadName)s]: %(message)s", datefmt="%H:%M:%S")


def run_server(server_sock: socket.socket, crypto_server: CryptoManager):
    """Giả lập luồng Server xử lý Handshake, nhận Tin nhắn và nhận File."""
    try:
        # 1. Server xử lý Handshake
        client_id = server_handle_init_and_respond(server_sock, crypto_server)

        # 2. Server nhận tin nhắn chat mã hóa
        msg_obj = recv_encrypted(server_sock, crypto_server)
        logging.info(f"Server nhận tin nhắn giải mã: '{msg_obj['text']}' từ {msg_obj['sender']}")

        # Phản hồi lại tin nhắn
        send_encrypted(server_sock, crypto_server, {"text": "Chào Khánh, Server đã sẵn sàng nhận file!", "sender": "Server"})

        # 3. Server nhận thông tin file & hứng các Chunk mã hóa
        file_meta = recv_encrypted(server_sock, crypto_server)
        save_path = "recv_" + file_meta["filename"]
        receiver = FileReceiver(save_path, file_meta["filesize"], crypto_mgr=crypto_server)

        for i in range(file_meta["total_chunks"]):
            chunk_data = server_sock.recv(CHUNK_SIZE + 100)  # Thêm buffer cho Fernet overhead
            receiver.write_chunk(i, chunk_data)

        logging.info(f"Server nhận file hoàn tất! Trạng thái: {receiver.is_complete()}")

        # Dọn dẹp file nhận sau khi test thành công
        if os.path.exists(save_path):
            os.remove(save_path)

    except Exception as e:
        logging.error(f"Lỗi Server: {e}")
    finally:
        server_sock.close()


def run_client(client_sock: socket.socket, crypto_client: CryptoManager):
    """Giả lập luồng Client khởi tạo Handshake, gửi Tin nhắn và truyền File."""
    try:
        # 1. Client bắt đầu Handshake
        resp = client_start_handshake(client_sock, client_id="Khanh_Client", crypto=crypto_client)
        client_finish_handshake(resp, crypto_client)

        # 2. Client gửi tin nhắn mã hóa
        send_encrypted(client_sock, crypto_client, {"text": "Hello Server! Kiểm thử E2EE thành công chưa?", "sender": "Khanh_Client"})

        # Nhận phản hồi từ Server
        reply = recv_encrypted(client_sock, crypto_client)
        logging.info(f"Client nhận phản hồi: '{reply['text']}' từ {reply['sender']}")

        # 3. Client gửi File mã hóa
        test_file = "test_data.bin"
        dummy_data = os.urandom(70 * 1024)  # 70KB dữ liệu ngẫu nhiên (chạy qua ~3 chunks)
        with open(test_file, "wb") as f:
            f.write(dummy_data)

        sender = FileSender(test_file, crypto_mgr=crypto_client)
        
        # Gửi Metadata của file trước
        send_encrypted(client_sock, crypto_client, {
            "filename": sender.filename,
            "filesize": sender.file_size,
            "total_chunks": sender.total_chunks
        })

        # Gửi từng Chunk đã mã hóa
        while not sender.is_complete():
            chunk_enc = sender.get_next_chunk()
            client_sock.sendall(chunk_enc)

        logging.info("Client đã gửi toàn bộ Chunk file mã hóa thành công!")

        # Dọn dẹp file test
        if os.path.exists(test_file):
            os.remove(test_file)

    except Exception as e:
        logging.error(f"Lỗi Client: {e}")
    finally:
        client_sock.close()


if __name__ == "__main__":
    print("\n========================================================")
    print("  TEST KẾT HỢP CRYPTO + HANDSHAKE + TRANSFER (P2P)   ")
    print("========================================================\n")

    # Tạo cặp Socket kết nối trực tiếp với nhau trong RAM
    server_sock, client_sock = socket.socketpair()

    # Khởi tạo 2 CryptoManager độc lập cho Client và Server
    crypto_server = CryptoManager()
    crypto_client = CryptoManager()

    # Chạy Server trên Thread riêng và Client ở Thread chính
    server_thread = threading.Thread(target=run_server, args=(server_sock, crypto_server), name="SERVER_THREAD")
    client_thread = threading.Thread(target=run_client, args=(client_sock, crypto_client), name="CLIENT_THREAD")

    server_thread.start()
    client_thread.start()

    server_thread.join()
    client_thread.join()

    print("\n========================================================")
    print("       KIỂM THỬ TÍCH HỢP LIÊN HOÀN THÀNH CÔNG!          ")
    print("========================================================\n")