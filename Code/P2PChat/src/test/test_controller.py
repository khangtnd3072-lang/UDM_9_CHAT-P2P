# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=protected-access

from typing import cast
from unittest.mock import MagicMock

from controllers.controller import ChatController


def create_controller():

    return ChatController(
        on_system=MagicMock(),
        on_message=MagicMock(),
        on_connected=MagicMock(),
        on_disconnect=MagicMock(),
        on_peers_update=MagicMock(),
        on_peer_discovered=MagicMock()
    )


def test_connect_without_node():

    controller = create_controller()

    result = controller.connect_to_peer(
        "127.0.0.1",
        5000
    )

    assert result is False

    cast(
        MagicMock,
        controller.on_system
    ).assert_called_once()


def test_send_message_without_node():

    controller = create_controller()

    result = controller.send_message(
        "hello",
        "peer1"
    )

    assert result is False

    cast(
        MagicMock,
        controller.on_system
    ).assert_called_once()


def test_broadcast_without_node():

    controller = create_controller()

    sent, failed = controller.broadcast_message(
        "hello"
    )

    assert sent == 0
    assert failed == 0


def test_get_discovered_peers_without_node():

    controller = create_controller()

    assert controller.get_discovered_peers() == {}


def test_get_local_peer_id_without_node():

    controller = create_controller()

    assert controller.get_local_peer_id() == ""


def test_get_local_fingerprint_without_node():

    controller = create_controller()

    assert controller.get_local_fingerprint() == ""


def test_get_trust_state_without_node():

    controller = create_controller()

    assert controller.get_trust_state(
        "peer1"
    ) == "NEW"


def test_trust_peer_without_node():

    controller = create_controller()

    controller.trust_peer(
        "peer1"
    )


def test_block_peer_without_node():

    controller = create_controller()

    controller.block_peer(
        "peer1"
    )


def test_safe_fire():

    controller = create_controller()

    called = []

    def callback(value):
        called.append(value)

    controller._safe_fire(
        callback,
        "hello"
    )

    assert called == ["hello"]


def test_safe_fire_exception():

    controller = create_controller()

    def callback(_):
        raise ValueError()

    controller._safe_fire(
        callback,
        "hello"
    )


def test_on_message():

    controller = create_controller()

    controller._on_message(
        "peer_abc",
        "Tai",
        "Hello"
    )

    cast(
        MagicMock,
        controller.on_message
    ).assert_called_once_with(
        "peer_abc",
        "Tai",
        "Hello"
    )


def test_on_connected():

    controller = create_controller()

    controller._on_connected(
        "peer_abc",
        "172.19.64.1:100"
    )

    cast(
        MagicMock,
        controller.on_connected
    ).assert_called_once_with(
        "peer_abc",
        "172.19.64.1:100"
    )

    cast(
        MagicMock,
        controller.on_peers_update
    ).assert_called_once()


def test_on_disconnect():

    controller = create_controller()

    controller._on_disconnect(
        "peer1"
    )

    cast(
        MagicMock,
        controller.on_disconnect
    ).assert_called_once_with(
        "peer1"
    )

    cast(
        MagicMock,
        controller.on_peers_update
    ).assert_called_once()


def test_on_peer_discovered():

    controller = create_controller()

    controller._on_peer_discovered(
        "peer1",
        {
            "username": "Tai"
        }
    )

    assert controller.on_peer_discovered is not None

    cast(
        MagicMock,
        controller.on_peer_discovered
    ).assert_called_once()


def test_on_peer_discovered_none():

    controller = ChatController(
        on_system=MagicMock(),
        on_message=MagicMock(),
        on_connected=MagicMock(),
        on_disconnect=MagicMock(),
        on_peers_update=MagicMock(),
        on_peer_discovered=None
    )

    controller._on_peer_discovered(
        "peer1",
        {}
    )


def test_get_peer_info():

    controller = create_controller()

    controller.get_discovered_peers = MagicMock(
        return_value={
            "peer1": {
                "username": "Tai"
            }
        }
    )

    peer = controller.get_peer_info(
        "peer1"
    )

    assert peer is not None
    assert peer["username"] == "Tai"


def test_get_peer_info_missing():

    controller = create_controller()

    controller.get_discovered_peers = MagicMock(
        return_value={}
    )

    assert (
        controller.get_peer_info(
            "unknown"
        )
        is None
    )


def test_connect_with_node():

    controller = create_controller()

    controller.node = MagicMock()

    controller.node.connect_to_peer.return_value = True

    result = controller.connect_to_peer(
        "127.0.0.1",
        5000
    )

    assert result is True


def test_send_message_with_node():

    controller = create_controller()

    controller.node = MagicMock()

    controller.node.send_message.return_value = True

    result = controller.send_message(
        "hello",
        "peer1"
    )

    assert result is True


def test_broadcast_with_node():

    controller = create_controller()

    controller.node = MagicMock()

    controller.node.broadcast_message.return_value = (
        3,
        0
    )

    sent, failed = controller.broadcast_message(
        "hello"
    )

    assert sent == 3
    assert failed == 0


def test_discover_peers():

    controller = create_controller()

    controller.node = MagicMock()

    controller.discover_peers()

    controller.node.discover_peers.assert_called_once()


def test_stop():

    controller = create_controller()

    node_mock = MagicMock()

    controller.node = node_mock

    controller.stop()

    node_mock.stop_server.assert_called_once()

    assert controller.node is None


def test_get_local_peer_id():

    controller = create_controller()

    controller.node = MagicMock()

    controller.node.identity_manager.get_peer_id.return_value = (
        "peer123"
    )

    assert (
        controller.get_local_peer_id()
        ==
        "peer123"
    )


def test_get_local_fingerprint():

    controller = create_controller()

    controller.node = MagicMock()

    controller.node.identity_manager.get_fingerprint.return_value = (
        "FP123"
    )

    assert (
        controller.get_local_fingerprint()
        ==
        "FP123"
    )


def test_get_trust_state():

    controller = create_controller()

    controller.node = MagicMock()

    controller.node.get_trust_state.return_value = (
        "TRUSTED"
    )

    assert (
        controller.get_trust_state(
            "peer1"
        )
        ==
        "TRUSTED"
    )


def test_trust_peer():

    controller = create_controller()

    controller.node = MagicMock()

    controller.trust_peer(
        "peer1"
    )

    controller.node.trust_peer.assert_called_once_with(
        "peer1"
    )


def test_block_peer():

    controller = create_controller()

    controller.node = MagicMock()

    controller.block_peer(
        "peer1"
    )

    controller.node.block_peer.assert_called_once_with(
        "peer1"
    )
    
def test_stop_without_node():

    controller = create_controller()

    controller.stop()

    assert controller.node is None
