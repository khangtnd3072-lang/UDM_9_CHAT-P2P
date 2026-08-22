import json
import struct
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

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


def _add_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add standard protocol metadata without modifying
    the original payload.

    Metadata:
    - protocol_version
    - message_id
    - timestamp
    """

    message = dict(payload)

    message.setdefault("protocol_version", PROTOCOL_VERSION)
    message.setdefault("message_id", str(uuid.uuid4()))
    message.setdefault(
        "timestamp",
        datetime.now(timezone.utc).isoformat()
    )

    return message


def _validate_message(payload: Dict[str, Any]) -> None:
    """Validate basic protocol message structure."""

    if not isinstance(payload, dict):
        raise ValueError("Message must be a JSON object")

    # Required metadata
    required_fields = [
        "protocol_version",
        "message_id",
        "timestamp",
        "type",
    ]

    for field in required_fields:
        if field not in payload:
            raise ValueError(
                f"Missing required field: {field}"
            )

    # Validate field types
    if not isinstance(payload["protocol_version"], str):
        raise ValueError(
            "protocol_version must be a string"
        )

    if not isinstance(payload["message_id"], str):
        raise ValueError(
            "message_id must be a string"
        )

    if not isinstance(payload["timestamp"], str):
        raise ValueError(
            "timestamp must be a string"
        )

    if not isinstance(payload["type"], str):
        raise ValueError(
            "type must be a string"
        )

    # Current project uses "chat"
    # Keep compatibility with existing node.py.
    allowed_types = {
        "chat",
        "text",
        "system",
        "ack",
        "file_meta",
        "file_chunk",
        "handshake_init",  # Thêm Handshake Init
        "handshake_resp",  # Thêm Handshake Resp
        "enc", # Thêm Tin Nhắn Mã Hóa E2EE
    }

    if payload["type"] not in allowed_types:
        raise ValueError(
            f"Unsupported message type: {payload['type']}"
        )


def encode_message(payload: Dict[str, Any]) -> bytes:
    """
    Encode a JSON payload using:

        [4-byte length prefix][UTF-8 JSON payload]

    Automatically adds:
        - protocol_version
        - message_id
        - timestamp
    """

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")

    # Do not modify the original dictionary
    message = _add_metadata(payload)

    _validate_message(message)

    body = json.dumps(
        message,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    length = len(body)

    if length <= 0:
        raise ValueError("Payload cannot be empty")

    if length > MAX_PACKET_SIZE:
        raise ValueError(
            f"Payload too large: {length} > {MAX_PACKET_SIZE}"
        )

    # 4-byte unsigned integer, big endian
    header = struct.pack(">I", length)

    return header + body


def decode_message(
    sock: socket.socket,
    timeout: float | None = None,
) -> Dict[str, Any]:
    """
    Decode one message from a TCP socket.

    Format:
        [4-byte length prefix][JSON payload]
    """

    old_timeout = sock.gettimeout()

    try:
        if timeout is not None:
            sock.settimeout(timeout)

        # Read 4-byte length prefix
        header = _recv_exact(sock, 4)

        length = struct.unpack(">I", header)[0]

        if length <= 0:
            raise ValueError(
                f"Invalid payload length: {length}"
            )

        if length > MAX_PACKET_SIZE:
            raise ValueError(
                f"Payload too large: {length} > {MAX_PACKET_SIZE}"
            )

        # Read exactly the JSON body
        body = _recv_exact(sock, length)

        # Decode UTF-8
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(
                "Invalid UTF-8 payload"
            ) from e

        # Decode JSON
        try:
            message = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(
                "Invalid JSON payload"
            ) from e

        # Validate protocol structure
        _validate_message(message)

        return message

    finally:
        sock.settimeout(old_timeout)