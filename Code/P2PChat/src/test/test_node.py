# pylint: disable=protected-access
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from typing import cast
import socket
from unittest.mock import MagicMock

from network.node import P2PNode


class FakeSocket:

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def create_node():

    return P2PNode(
        host="127.0.0.1",
        port=5000,
        username="Tai"
    )


def test_register_peer():

    node = create_node()

    sock = cast(
        socket.socket,
        FakeSocket()
    )

    result = node._register_peer(
        "peer1",
        sock,
        True
    )

    assert result is True
    assert "peer1" in node.peers
    assert "peer1" in node.peer_sessions


def test_register_duplicate_peer():

    node = create_node()

    sock1 = cast(
        socket.socket,
        FakeSocket()
    )

    sock2 = cast(
        socket.socket,
        FakeSocket()
    )

    node._register_peer(
        "peer1",
        sock1,
        True
    )

    result = node._register_peer(
        "peer1",
        sock2,
        True
    )

    assert result is False


def test_remove_peer():

    node = create_node()

    sock = cast(
        socket.socket,
        FakeSocket()
    )

    node._register_peer(
        "peer1",
        sock,
        True
    )

    node._remove_peer(sock)

    assert "peer1" not in node.peers
    assert "peer1" not in node.peer_sessions


def test_get_peer_id():

    node = create_node()

    sock = cast(
        socket.socket,
        FakeSocket()
    )

    node._register_peer(
        "peer1",
        sock,
        True
    )

    result = node._get_peer_id(sock)

    assert result == "peer1"


def test_fire_callback():

    node = create_node()

    called = []

    def callback(value):
        called.append(value)

    node._fire_callback(
        callback,
        "hello"
    )

    assert called == ["hello"]


def test_fire_callback_none():

    node = create_node()

    node._fire_callback(None)


def test_broadcast_no_active_peers():

    node = create_node()

    sent, failed = node.broadcast_message(
        "hello"
    )

    assert sent == 0
    assert failed == 0


def test_broadcast_active_peer():

    node = create_node()

    node.send_message = MagicMock(
        return_value=True
    )

    node.peer_sessions["peer1"] = {
        "state": "active"
    }

    sent, failed = node.broadcast_message(
        "hello"
    )

    assert sent == 1
    assert failed == 0


def test_broadcast_failed_peer():

    node = create_node()

    node.send_message = MagicMock(
        return_value=False
    )

    node.peer_sessions["peer1"] = {
        "state": "active"
    }

    sent, failed = node.broadcast_message(
        "hello"
    )

    assert sent == 0
    assert failed == 1


def test_get_discovered_peers():

    node = create_node()

    node.discovered_peers["peer1"] = {
        "username": "Alice"
    }

    peers = node.get_discovered_peers()

    assert "peer1" in peers


def test_trust_peer():

    node = create_node()

    node.tofu.trust_peer = MagicMock()

    node.trust_peer("peer1")

    node.tofu.trust_peer.assert_called_once_with(
        "peer1"
    )


def test_block_peer():

    node = create_node()

    node.tofu.block_peer = MagicMock()

    node.block_peer("peer1")

    node.tofu.block_peer.assert_called_once_with(
        "peer1"
    )