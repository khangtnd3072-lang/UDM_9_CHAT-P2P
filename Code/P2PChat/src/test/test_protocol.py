import json
import struct

from security.crypto import CryptoHandler
from message.protocol import (
    ProtocolHandler,
    PacketType
)

def test_create_plain_packet():

    protocol = ProtocolHandler()

    packet = protocol.create_packet(
        PacketType.MESSAGE,
        "Tai",
        "Hello"
    )

    assert packet["type"] == PacketType.MESSAGE
    assert packet["sender"] == "Tai"
    assert packet["payload"] == "Hello"


def test_create_encrypted_packet():

    protocol = ProtocolHandler()
    crypto = CryptoHandler()

    packet = protocol.create_packet(
        PacketType.MESSAGE,
        "Tai",
        "Secret",
        crypto
    )

    assert packet["payload"] != "Secret"


def test_serialize_returns_bytes():

    protocol = ProtocolHandler()

    packet = protocol.create_packet(
        PacketType.MESSAGE,
        "Tai",
        "Hello"
    )

    data = protocol.serialize(packet)

    assert isinstance(data, bytes)


def test_validate_valid_message():

    protocol = ProtocolHandler()

    packet = protocol.create_packet(
        PacketType.MESSAGE,
        "Tai",
        "Hello"
    )

    assert protocol.validate_packet(packet)


def test_validate_missing_field():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.MESSAGE
    }

    assert not protocol.validate_packet(packet)


def test_validate_unknown_type():

    protocol = ProtocolHandler()

    packet = {
        "type": "UNKNOWN"
    }

    assert not protocol.validate_packet(packet)


def test_validate_handshake():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.HANDSHAKE,
        "username": "Tai",
        "version": "1.0",
        "listen_port": 5000,
        "public_key": "PUBLIC_KEY"
    }

    assert protocol.validate_packet(packet)


def test_validate_handshake_ack():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.HANDSHAKE_ACK,
        "status": "ok",
        "public_key": "PUBLIC_KEY"
    }

    assert protocol.validate_packet(packet)


def test_validate_session_key():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.SESSION_KEY,
        "payload": "encrypted_key"
    }

    assert protocol.validate_packet(packet)


def test_validate_session_key_payload_type():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.SESSION_KEY,
        "payload": 123
    }

    assert not protocol.validate_packet(packet)


def test_validate_and_decrypt_success():

    protocol = ProtocolHandler()
    crypto = CryptoHandler()

    packet = protocol.create_packet(
        PacketType.MESSAGE,
        "Tai",
        "Hello",
        crypto
    )

    result = protocol.validate_and_decrypt(
        packet,
        crypto
    )

    assert result == "Hello"


def test_validate_and_decrypt_wrong_key():

    protocol = ProtocolHandler()

    crypto1 = CryptoHandler()
    crypto2 = CryptoHandler()

    packet = protocol.create_packet(
        PacketType.MESSAGE,
        "Tai",
        "Secret",
        crypto1
    )

    result = protocol.validate_and_decrypt(
        packet,
        crypto2
    )

    assert result is None
    
class FakeSocket:

    def __init__(self, chunks):
        self.chunks = chunks

    def recv(self, size):

        if not self.chunks:
            return b""

        return self.chunks.pop(0)
    
def test_receive_exact():

    protocol = ProtocolHandler()

    sock = FakeSocket([
        b"ab",
        b"cd"
    ])

    result = protocol.receive_exact(
        sock,
        4
    )

    assert result == b"abcd"
    
def test_receive_exact_closed():

    protocol = ProtocolHandler()

    sock = FakeSocket([])

    result = protocol.receive_exact(
        sock,
        4
    )

    assert result == b""

def test_decrypt_payload_plain():

    protocol = ProtocolHandler()

    packet = {
        "payload": "hello"
    }

    result = protocol.decrypt_payload(
        packet
    )

    assert result == "hello"
    
def test_validate_message_sender_type():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.MESSAGE,
        "sender": 123,
        "payload": "hello",
        "timestamp": "now",
        "message_id": "id"
    }

    assert not protocol.validate_packet(
        packet
    )
    
def test_validate_message_timestamp_type():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.MESSAGE,
        "sender": "Tai",
        "payload": "hello",
        "timestamp": 123,
        "message_id": "id"
    }

    assert not protocol.validate_packet(
        packet
    )
    
def test_validate_message_id_type():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.MESSAGE,
        "sender": "Tai",
        "payload": "hello",
        "timestamp": "now",
        "message_id": 123
    }

    assert not protocol.validate_packet(
        packet
    )
    
class PacketSocket:

    def __init__(self, packet):

        payload = json.dumps(
            packet
        ).encode("utf-8")

        self.data = (
            struct.pack(
                "!I",
                len(payload)
            )
            +
            payload
        )

    def recv(self, size):

        if not self.data:
            return b""

        chunk = self.data[:size]

        self.data = self.data[size:]

        return chunk
    
def test_receive_packet_success():

    protocol = ProtocolHandler()

    packet = protocol.create_packet(
        PacketType.MESSAGE,
        "Tai",
        "Hello"
    )

    sock = PacketSocket(
        packet
    )

    result = protocol.receive_packet(
        sock
    )

    assert result is not None
    assert result["sender"] == "Tai"
    
class ClosedSocket:

    def recv(self, size):
        return b""
    
def test_receive_packet_closed():

    protocol = ProtocolHandler()

    result = protocol.receive_packet(
        ClosedSocket()
    )

    assert result is None
    
class OversizedSocket:

    def recv(self, size):

        return struct.pack(
            "!I",
            ProtocolHandler.MAX_PACKET_SIZE + 1
        )
        
def test_oversized_packet():

    protocol = ProtocolHandler()

    result = protocol.receive_packet(
        OversizedSocket()
    )

    assert result is None
    
class InvalidJsonSocket:

    def __init__(self):

        payload = b"NOT_JSON"

        self.data = (
            struct.pack(
                "!I",
                len(payload)
            )
            +
            payload
        )

    def recv(self, size):

        if not self.data:
            return b""

        chunk = self.data[:size]

        self.data = self.data[size:]

        return chunk
    
def test_invalid_json():

    protocol = ProtocolHandler()

    result = protocol.receive_packet(
        InvalidJsonSocket()
    )

    assert result is None
    
def test_receive_exact_multiple_reads():

    protocol = ProtocolHandler()

    sock = FakeSocket(
        [
            b"a",
            b"b",
            b"c",
            b"d"
        ]
    )

    result = protocol.receive_exact(
        sock,
        4
    )

    assert result == b"abcd"
    
def test_validate_non_dict():

    protocol = ProtocolHandler()

    assert (
        protocol.validate_packet(
            "hello" # type: ignore[arg-type]
        )
        is False
    )
    
def test_validate_handshake_missing_field():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.HANDSHAKE,
        "username": "Tai"
    }

    assert not protocol.validate_packet(
        packet
    )
    
def test_validate_handshake_ack_missing_field():

    protocol = ProtocolHandler()

    packet = {
        "type": PacketType.HANDSHAKE_ACK
    }

    assert not protocol.validate_packet(
        packet
    )
    
