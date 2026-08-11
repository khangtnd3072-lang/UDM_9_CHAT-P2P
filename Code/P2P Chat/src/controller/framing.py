import struct

from .exceptions import InvalidPacketError, PeerDisconnectedError


HEADER_SIZE = 4
MAX_PACKET_SIZE = 1024 * 1024


def encode_packet(data: bytes) -> bytes:
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")

    if len(data) > MAX_PACKET_SIZE:
        raise InvalidPacketError("Packet is too large")

    header = struct.pack("!I", len(data))
    return header + data


def recv_exact(sock, size: int) -> bytes:
    data = b""

    while len(data) < size:
        chunk = sock.recv(size - len(data))

        if not chunk:
            raise PeerDisconnectedError(
                "Remote peer disconnected"
            )

        data += chunk

    return data


def recv_packet(sock) -> bytes:
    header = recv_exact(sock, HEADER_SIZE)

    try:
        length = struct.unpack("!I", header)[0]
    except struct.error as exc:
        raise InvalidPacketError(
            "Invalid packet header"
        ) from exc

    if length > MAX_PACKET_SIZE:
        raise InvalidPacketError(
            f"Packet too large: {length} bytes"
        )

    return recv_exact(sock, length)
