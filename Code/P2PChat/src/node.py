import argparse
import socket
import threading
import traceback

from protocol import decode_message, encode_message

# Handshake / crypto helpers (optional secure mode)
try:
    from handshake import (
        generate_rsa_keypair,
        client_start_handshake,
        client_finish_handshake,
        server_handle_init_and_respond,
        send_encrypted,
        recv_encrypted,
    )
except Exception:
    # If running tests from different cwd, imports may fail; let errors surface at runtime
    generate_rsa_keypair = None
    client_start_handshake = None
    client_finish_handshake = None
    server_handle_init_and_respond = None
    send_encrypted = None
    recv_encrypted = None


HOST = "127.0.0.1"
PORT = 5000


# SERVER
# clients maps username -> (socket, Fernet|None)
clients: dict[str, tuple[socket.socket, object | None]] = {}
clients_lock = threading.Lock()
USE_SECURE = False  # set per server instance based on CLI arg
server_priv = None
server_pub = None


def handle_client(conn, addr):
    print(f"[+] Client ket noi: {addr}")

    username = None
    conn_f = None

    try:
        # If server is in secure mode, perform handshake with this client
        if USE_SECURE:
            if server_handle_init_and_respond is None:
                raise RuntimeError("handshake support not available (missing dependency)")
            try:
                conn_f = server_handle_init_and_respond(conn, server_priv, server_pub)
                print(f"[+] Handshake completed with {addr}")
            except Exception as e:
                print(f"[ERROR] Handshake failed with {addr}: {e}")
                conn.close()
                return

        while True:
            try:
                if conn_f is not None:
                    message = recv_encrypted(conn, conn_f)
                else:
                    message = decode_message(conn)
            except EOFError:
                print(f"[-] Client closed connection: {addr}")
                break
            except Exception as e:
                print(f"[ERROR] Receiving from {addr}: {e}")
                break

            print(f"[RECV] {message}")

            sender = message.get("sender")
            if sender and sender != username:
                # Lan dau nhan duoc ten, hoac ten thay doi -> dang ky/cap nhat.
                username = sender
                with clients_lock:
                    clients[username] = (conn, conn_f)

            receiver = message.get("receiver")

            with clients_lock:
                receiver_entry = clients.get(receiver)
                receiver_socket = receiver_entry[0] if receiver_entry else None
                receiver_f = receiver_entry[1] if receiver_entry else None

            if receiver_socket is not None:
                try:
                    # If receiver has a secure session, encrypt for them using their Fernet
                    if receiver_f is not None:
                        send_encrypted(receiver_socket, receiver_f, message)
                    else:
                        data = encode_message(message)
                        receiver_socket.sendall(data)
                    print(f"[SEND] {username} -> {receiver}")
                except OSError as e:
                    print(f"[ERROR] Gui toi {receiver} that bai: {e}")
            else:
                print(f"[INFO] {receiver} chua online")

    except Exception as e:
        print(f"[ERROR] {addr}: {e}")
        traceback.print_exc()

    finally:
        with clients_lock:
            if username in clients:
                del clients[username]
        try:
            conn.close()
        except Exception:
            pass
        print(f"[-] Client ngat ket noi: {addr}")


def start_server(host: str, port: int, secure: bool):
    global USE_SECURE, server_priv, server_pub
    USE_SECURE = secure

    if USE_SECURE:
        if generate_rsa_keypair is None:
            raise RuntimeError("handshake support not available (missing dependency)")
        server_priv, server_pub = generate_rsa_keypair()
        print("[+] Server RSA keypair generated for handshake")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()

    print(f"Server dang chay tai {host}:{port} (secure={USE_SECURE})")

    while True:
        conn, addr = server.accept()
        thread = threading.Thread(
            target=handle_client, args=(conn, addr), daemon=True
        )
        thread.start()


# CLIENT

def receive_messages(sock, secure: bool, client_priv=None, client_pub=None):
    f_client = None
    try:
        if secure:
            if client_start_handshake is None:
                raise RuntimeError("handshake support not available (missing dependency)")
            # start handshake and obtain session Fernet
            resp = client_start_handshake(sock, username_global, client_pub)
            f_client = client_finish_handshake(resp, client_priv)
            print("[+] Handshake completed with server")

        while True:
            try:
                if f_client is not None:
                    msg = recv_encrypted(sock, f_client)
                else:
                    msg = decode_message(sock)
                print(f"\n[{msg.get('sender')}] {msg.get('message')}")
            except EOFError:
                print("\n[INFO] Server closed connection")
                break
            except Exception as e:
                print(f"\n[ERROR] Mat ket noi server: {e}")
                break
    finally:
        try:
            sock.close()
        except Exception:
            pass


def start_client(host: str, port: int, secure: bool):
    global username_global
    username_global = input("Nhap ten cua ban: ")
    receiver = input("Nhap ten nguoi nhan: ")

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))

    client_priv = None
    client_pub = None

    if secure:
        if generate_rsa_keypair is None:
            raise RuntimeError("handshake support not available (missing dependency)")
        client_priv, client_pub = generate_rsa_keypair()

    print("Da ket noi toi server.")
    print("Nhap tin nhan, go 'exit' de thoat.")

    thread = threading.Thread(
        target=receive_messages, args=(client, secure, client_priv, client_pub), daemon=True
    )
    thread.start()

    # If secure, we must finish handshake from client side when sending first message
    f_client = None
    handshake_done = False

    while True:
        message_text = input("Ban: ")

        if message_text.lower() == "exit":
            break

        message = {
            "type": "chat",
            "sender": username_global,
            "receiver": receiver,
            "message": message_text,
        }

        try:
            if secure:
                # finish handshake lazily on first send if not done
                if not handshake_done:
                    # perform handshake and obtain Fernet
                    resp = client_start_handshake(client, username_global, client_pub)
                    f_client = client_finish_handshake(resp, client_priv)
                    handshake_done = True
                send_encrypted(client, f_client, message)
            else:
                data = encode_message(message)
                print(f"[DEBUG] Kich thuoc goi tin gui di: {len(data)} bytes")
                client.sendall(data)
        except Exception as e:
            print(f"[ERROR] Loi khi gui: {e}")
            break

    try:
        client.close()
    except Exception:
        pass


# ==========================================================================
# ENTRY POINT: chọn chế độ chạy
# ==========================================================================

def main():
    parser = argparse.ArgumentParser(description="Chat relay Server/Client (gop 1 file)")
    parser.add_argument(
        "--mode",
        choices=["server", "client"],
        required=True,
        help="Chay o che do server hay client",
    )
    parser.add_argument("--host", default=HOST, help="Host to bind/connect")
    parser.add_argument("--port", type=int, default=PORT, help="Port to bind/connect")
    parser.add_argument("--secure", action="store_true", help="Enable handshake+encrypted channel between client and server")
    args = parser.parse_args()

    if args.mode == "server":
        start_server(args.host, args.port, args.secure)
    else:
        start_client(args.host, args.port, args.secure)


if __name__ == "__main__":
    main()
