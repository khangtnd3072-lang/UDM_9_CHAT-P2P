"""Message-level security for P2P chat payloads.

This adds an integrity-protected encrypted envelope around each text message.
The encrypted payload is authenticated with HMAC-SHA256 and the message content
is encrypted with AES-GCM, which is stronger and more explicit than plain session
Fernet usage alone.
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import hmac
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class MessageSecurity:
    """Encrypt and decrypt a chat message with AES-GCM and HMAC integrity.

    Envelope format includes version metadata for future compatibility. Legacy
    envelopes without metadata are still accepted during migration.
    """

    _AAD = b"p2pchat:v1"

    def __init__(self, key: str | bytes) -> None:
        self.key = self._normalize_key(key)
        self.key_id = hashlib.sha256(self.key).hexdigest()[:16]

    @staticmethod
    def _normalize_key(key: str | bytes) -> bytes:
        if isinstance(key, str):
            key = key.strip()
            if len(key) in (16, 24, 32):
                return key.encode("utf-8")
            try:
                decoded = bytes.fromhex(key)
                if len(decoded) in (16, 24, 32):
                    return decoded
            except ValueError:
                pass
            return hashlib.sha256(key.encode("utf-8")).digest()

        if not isinstance(key, (bytes, bytearray)):
            raise ValueError("Key must be a string or bytes-like value.")

        key_bytes = bytes(key)
        if len(key_bytes) not in (16, 24, 32):
            return hashlib.sha256(key_bytes).digest()
        return key_bytes

    def _mac_key(self) -> bytes:
        return hashlib.sha256(self.key + b"::p2pchat-mac").digest()

    @staticmethod
    def _b64encode(data: bytes) -> str:
        return base64.b64encode(data).decode("utf-8")

    @staticmethod
    def _b64decode(value: str) -> bytes:
        if not isinstance(value, str):
            raise ValueError("Encrypted field must be a string.")
        try:
            return base64.b64decode(value.encode("utf-8"))
        except ValueError as exc:
            raise ValueError("Invalid base64 payload.") from exc

    @staticmethod
    def _timestamp_now() -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def encrypt(self, plaintext: str) -> dict[str, str]:
        """Return an encrypted message envelope with metadata for versioning."""
        if not isinstance(plaintext, str):
            raise ValueError("Message text must be a string.")

        nonce = os.urandom(12)
        ciphertext = AESGCM(self.key).encrypt(nonce, plaintext.encode("utf-8"), self._AAD)
        mac = hmac.new(self._mac_key(), nonce + ciphertext, hashlib.sha256).hexdigest()
        # ciphertext_fake = ciphertext[:-1] + b"X"
        # mac_fake = "0" * 64

        return {
            "version": "v1",
            "alg": "AES-256-GCM",
            "key_id": self.key_id,
            "timestamp": self._timestamp_now(),
            "nonce": self._b64encode(nonce),
            "ciphertext": self._b64encode(ciphertext),
            "mac": mac,
        }

    def decrypt(self, envelope: dict[str, Any]) -> str:
        """Decrypt a message envelope and validate its integrity."""
        if not isinstance(envelope, dict):
            raise ValueError("Encrypted message must be a dictionary.")

        if "nonce" not in envelope or "ciphertext" not in envelope or "mac" not in envelope:
            raise ValueError("Message envelope is missing required fields.")

        if "version" in envelope and envelope["version"] != "v1":
            raise ValueError("Unsupported message version.")

        if "alg" in envelope and envelope["alg"] != "AES-256-GCM":
            raise ValueError("Unsupported encryption algorithm.")

        if "key_id" in envelope and envelope["key_id"] != self.key_id:
            raise ValueError("Message key_id does not match the current key.")

        if "timestamp" in envelope and not isinstance(envelope["timestamp"], str):
            raise ValueError("Message timestamp must be a string if present.")

        nonce = self._b64decode(envelope["nonce"])
        ciphertext = self._b64decode(envelope["ciphertext"])
        received_mac = envelope["mac"]

        expected_mac = hmac.new(
            self._mac_key(),
            nonce + ciphertext,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_mac, received_mac):
            raise ValueError("Message integrity check failed.")

        try:
            plain = AESGCM(self.key).decrypt(nonce, ciphertext, self._AAD)
        except InvalidTag as exc:
            raise ValueError("Invalid message key or ciphertext.") from exc

        return plain.decode("utf-8")
