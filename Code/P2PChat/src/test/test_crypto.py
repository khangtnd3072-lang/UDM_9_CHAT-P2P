import pytest
from security.crypto import CryptoHandler

def test_encrypt_decrypt_round_trip():

    crypto = CryptoHandler()

    plaintext = "Hello P2PChat"

    encrypted = crypto.encrypt(
        plaintext
    )

    decrypted = crypto.decrypt(
        encrypted
    )

    assert decrypted == plaintext
    
def test_encrypt_changes_content():

    crypto = CryptoHandler()

    plaintext = "Hello"

    encrypted = crypto.encrypt(
        plaintext
    )

    assert encrypted != plaintext
    


def test_encrypt_rejects_non_string():

    crypto = CryptoHandler()

    with pytest.raises(
        ValueError
    ):
        crypto.encrypt(123) # type: ignore[arg-type]
        
def test_wrong_key_fails():

    crypto1 = CryptoHandler()
    crypto2 = CryptoHandler()

    encrypted = crypto1.encrypt(
        "secret"
    )

    with pytest.raises(Exception):
        crypto2.decrypt(encrypted)
        
def test_decrypt_rejects_non_string():

    crypto = CryptoHandler()

    with pytest.raises(
        ValueError
    ):
        crypto.decrypt(123)  # type: ignore[arg-type]