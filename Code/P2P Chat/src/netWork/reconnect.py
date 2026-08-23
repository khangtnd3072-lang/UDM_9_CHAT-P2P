"""Reusable TCP reconnect logic for network-resilience handling."""
from __future__ import annotations

import logging
import socket
import time
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger("p2pchat.network.reconnect")


@dataclass(frozen=True)
class ReconnectPolicy:
    """Controls how aggressively a peer retries a failed TCP connection."""

    max_attempts: int = 5
    initial_delay: float = 0.5
    max_delay: float = 5.0
    backoff: float = 2.0
    connect_timeout: float = 3.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_delay < 0 or self.max_delay < 0:
            raise ValueError("delays must be >= 0")
        if self.backoff < 1:
            raise ValueError("backoff must be >= 1")
        if self.connect_timeout <= 0:
            raise ValueError("connect_timeout must be > 0")


class ReconnectingTCP:
    """Small TCP connection manager with bounded exponential-backoff retry.

    The manager deliberately does not know anything about chat/handshake data.
    ``on_reconnect`` can be used by a higher layer to restore a session after a
    new socket has been created.
    """

    def __init__(
        self,
        host: str,
        port: int,
        policy: ReconnectPolicy | None = None,
        socket_factory: Callable[..., socket.socket] = socket.socket,
    ) -> None:
        self.host = host
        self.port = port
        self.policy = policy or ReconnectPolicy()
        self.socket_factory = socket_factory
        self.sock: socket.socket | None = None

    @property
    def connected(self) -> bool:
        return self.sock is not None

    def connect(self) -> socket.socket:
        """Connect with bounded retries; raise the last OSError if exhausted."""
        delay = self.policy.initial_delay
        last_error: OSError | None = None

        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                sock = self.socket_factory(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.policy.connect_timeout)
                sock.connect((self.host, self.port))
                sock.settimeout(None)
                self.sock = sock
                logger.info("TCP connected to %s:%s (attempt %d)", self.host, self.port, attempt)
                return sock
            except OSError as exc:
                last_error = exc
                logger.warning(
                    "TCP connection attempt %d/%d to %s:%s failed: %s",
                    attempt, self.policy.max_attempts, self.host, self.port, exc,
                )
                try:
                    sock.close()
                except Exception:
                    pass
                if attempt < self.policy.max_attempts:
                    time.sleep(delay)
                    delay = min(self.policy.max_delay, delay * self.policy.backoff)

        assert last_error is not None
        logger.error("TCP reconnect exhausted after %d attempts", self.policy.max_attempts)
        raise last_error

    def reconnect(self) -> socket.socket:
        """Close the old socket and establish a fresh TCP connection."""
        self.close()
        logger.info("Starting TCP reconnect to %s:%s", self.host, self.port)
        return self.connect()

    def sendall(self, data: bytes, reconnect: bool = True) -> socket.socket:
        """Send bytes; optionally reconnect once when the socket is broken.

        Returns the active socket so callers can update their receive loop.
        The payload is retried only after a fresh connection is established.
        """
        if self.sock is None:
            self.connect()
        assert self.sock is not None
        try:
            self.sock.sendall(data)
            return self.sock
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError) as exc:
            logger.warning("TCP send failed: %s", exc)
            if not reconnect:
                raise
            self.reconnect()
            assert self.sock is not None
            self.sock.sendall(data)
            logger.info("TCP payload resent after reconnect")
            return self.sock

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                try:
                    self.sock.close()
                except OSError:
                    pass
                self.sock = None
                logger.info("TCP connection closed")


__all__ = ["ReconnectPolicy", "ReconnectingTCP"]
