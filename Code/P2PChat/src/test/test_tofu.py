import uuid

from trust.tofu_engine import TOFUEngine
from trust.trust_state import TrustState


def unique_peer_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4()}"


def test_new_peer():

    tofu = TOFUEngine()

    peer_id = unique_peer_id("new")
    fingerprint = "ABC123"

    state = tofu.verify_peer(
        peer_id,
        fingerprint
    )

    assert state == TrustState.NEW


def test_verified_peer():

    tofu = TOFUEngine()

    peer_id = unique_peer_id("verified")
    fingerprint = "ABC123"

    tofu.add_peer(
        peer_id,
        fingerprint
    )

    state = tofu.verify_peer(
        peer_id,
        fingerprint
    )

    assert state == TrustState.VERIFIED


def test_mismatch_peer():

    tofu = TOFUEngine()

    peer_id = unique_peer_id("mismatch")

    tofu.add_peer(
        peer_id,
        "OLD_FP"
    )

    state = tofu.verify_peer(
        peer_id,
        "NEW_FP"
    )

    assert state == TrustState.MISMATCH


def test_block_peer():

    tofu = TOFUEngine()

    peer_id = unique_peer_id("blocked")

    tofu.add_peer(
        peer_id,
        "FP"
    )

    tofu.block_peer(
        peer_id
    )

    state = tofu.get_trust_state(
        peer_id
    )

    assert state == TrustState.BLOCKED


def test_trust_peer():

    tofu = TOFUEngine()

    peer_id = unique_peer_id("trusted")

    tofu.add_peer(
        peer_id,
        "FP"
    )

    tofu.block_peer(
        peer_id
    )

    tofu.trust_peer(
        peer_id
    )

    state = tofu.get_trust_state(
        peer_id
    )

    assert state == TrustState.TRUSTED