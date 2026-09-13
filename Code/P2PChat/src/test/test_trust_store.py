from trust.trust_store import TrustStore


def test_get_all_peers():

    store = TrustStore()

    peers = store.get_all_peers()

    assert isinstance(
        peers,
        dict
    )


def test_remove_peer():

    store = TrustStore()

    peer_id = "remove_peer"

    store.add_peer(
        peer_id,
        "FP",
        "TRUSTED"
    )

    store.remove_peer(
        peer_id
    )

    assert (
        store.get_peer(peer_id)
        is None
    )


def test_update_peer():

    store = TrustStore()

    peer_id = "update_peer"

    store.add_peer(
        peer_id,
        "OLD",
        "TRUSTED"
    )

    store.update_peer(
        peer_id,
        "NEW",
        "BLOCKED"
    )

    peer = store.get_peer(
        peer_id
    )

    assert peer is not None
    assert peer["fingerprint"] == "NEW"
    assert peer["trust_state"] == "BLOCKED"