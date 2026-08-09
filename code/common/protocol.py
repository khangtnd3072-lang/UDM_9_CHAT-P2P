import json
import struct


# Giới hạn kích thước message: 1 MB
MAX_MESSAGE_SIZE = 1024 * 1024


def encode_message(message):
    """
    Dictionary -> JSON -> [4 byte length] + [JSON bytes]
    """

    # Chuyển dictionary thành JSON rồi encode UTF-8
    json_data = json.dumps(
        message,
        ensure_ascii=False
    ).encode("utf-8")

    # Kiểm tra kích thước message
    if len(json_data) > MAX_MESSAGE_SIZE:
        raise ValueError("Tin nhắn vượt quá 1 MB")

    # Tạo 4 byte chứa độ dài JSON
    header = struct.pack("!I", len(json_data))

    # Ghép Length Prefix + JSON
    return header + json_data


def recv_all(sock, size):
    """
    Nhận đủ 'size' bytes từ socket.
    """

    data = b""

    while len(data) < size:
        packet = sock.recv(size - len(data))

        if not packet:
            raise ConnectionError("Kết nối đã bị đóng")

        data += packet

    return data


def decode_message(sock):
    """
    Nhận [4 byte length] + [JSON]
    rồi chuyển JSON thành Dictionary.
    """

    # Nhận 4 byte đầu tiên
    header = recv_all(sock, 4)

    # Đọc độ dài JSON
    message_length = struct.unpack("!I", header)[0]

    # Kiểm tra kích thước
    if message_length > MAX_MESSAGE_SIZE:
        raise ValueError("Tin nhắn vượt quá 1 MB")

    # Nhận phần JSON
    json_data = recv_all(sock, message_length)

    # JSON -> Dictionary
    return json.loads(json_data.decode("utf-8"))
