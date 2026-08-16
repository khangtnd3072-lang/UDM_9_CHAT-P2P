import json
import struct
from typing import Any, Dict
import socket

# Try to reuse config if available
try:
    from config import MAX_PACKET_SIZE, PROTOCOL_VERSION
except Exception:
    MAX_PACKET_SIZE = 131072
    PROTOCOL_VERSION = "1.0"


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from socket or raise EOFError."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("Socket closed while reading")
        buf.extend(chunk)
    return bytes(buf)


def encode_message(payload: Dict[str, Any]) -> bytes:
    """Encode a JSON payload with 4-byte length prefix."""
    # Ensure PROTOCOL_VERSION present for handshake/version compatibility if desired
    if isinstance(payload, dict) and "protocol_version" not in payload:
        payload["protocol_version"] = PROTOCOL_VERSION

    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    length = len(body)
    if length > MAX_PACKET_SIZE:
        raise ValueError(f"Payload too large: {length} > {MAX_PACKET_SIZE}")
    return struct.pack(">I", length) + body


def decode_message(sock: socket.socket, timeout: float | None = None) -> Dict:
    """Blocking read: read 4-byte length then JSON body, return dict."""
    # Optionally set timeout for this operation
    old_timeout = sock.gettimeout()
    try:
        if timeout is not None:
            sock.settimeout(timeout)
        header = _recv_exact(sock, 4)
        length = struct.unpack(">I", header)[0]
        if length <= 0 or length > MAX_PACKET_SIZE:
            raise ValueError(f"Invalid payload length: {length}")
        body = _recv_exact(sock, length)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError("Invalid JSON payload") from e
    finally:
        sock.settimeout(old_timeout)
