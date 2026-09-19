import pytest

from security.message_security import MessageSecurity


def test_message_security_round_trip():
    secure = MessageSecurity("0123456789abcdef0123456789abcdef")
    plain = "Xin chào, đây là tin nhắn bảo mật!"

    envelope = secure.encrypt(plain)
    result = secure.decrypt(envelope)

    assert result == plain
    assert envelope["ciphertext"] != plain
    assert envelope["mac"]


def test_message_security_rejects_invalid_mac():
    secure = MessageSecurity("0123456789abcdef0123456789abcdef")
    envelope = secure.encrypt("hello")
    envelope["mac"] = "bad-mac"

    with pytest.raises(ValueError):
        secure.decrypt(envelope)


def test_message_security_rejects_wrong_key():
    sender = MessageSecurity("0123456789abcdef0123456789abcdef")
    receiver = MessageSecurity("abcdef0123456789abcdef0123456789")

    envelope = sender.encrypt("secret")

    with pytest.raises(ValueError):
        receiver.decrypt(envelope)


def test_message_security_envelope_has_security_metadata():
    secure = MessageSecurity("0123456789abcdef0123456789abcdef")

    envelope = secure.encrypt("hello")

    assert envelope["version"] == "v1"
    assert envelope["alg"] == "AES-256-GCM"
    assert envelope["key_id"]
    assert envelope["timestamp"]


def test_message_security_accepts_legacy_envelope():
    secure = MessageSecurity("0123456789abcdef0123456789abcdef")
    envelope = secure.encrypt("legacy-message")
    legacy = {"nonce": envelope["nonce"], "ciphertext": envelope["ciphertext"], "mac": envelope["mac"]}

    assert secure.decrypt(legacy) == "legacy-message"


def test_message_security_rejects_non_string():
    secure = MessageSecurity("0123456789abcdef0123456789abcdef")

    with pytest.raises(ValueError):
        secure.encrypt(123)  # type: ignore[arg-type]
