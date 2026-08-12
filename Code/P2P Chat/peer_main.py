"""
Small runnable P2P peer used by the project for discovery + direct TCP chat.

Run two copies on the same PC with different TCP ports:

    python peer_main.py --name Khoi --port 5001
    python peer_main.py --name Tai --port 5002

Then type the discovered peer username to connect and send a message.
"""

import argparse
import json
import os
import socket
import sys
import threading


# Allow this file to be run directly from:
# Code/P2P Chat/
#
# while the project modules are inside:
# Code/P2P Chat/src/
SRC_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "src",
)

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


from controller.framing import recv_packet, encode_packet
from controller.peer_discovery import PeerDiscovery, Peer


def make_chat_message(sender: str, receiver: str, text: str) -> bytes:
    """Create a CHAT packet."""
    message = {
        "type": "CHAT",
        "sender": sender,
        "receiver": receiver,
        "message": text,
    }

    payload = json.dumps(
        message,
        ensure_ascii=False,
    ).encode("utf-8")

    return encode_packet(payload)


def recv_loop(conn: socket.socket) -> None:
    """Receive CHAT messages from a TCP connection."""
    while True:
        try:
            data = recv_packet(conn)

            msg = json.loads(
                data.decode("utf-8")
            )

            if msg.get("type") == "CHAT":
                print(
                    f"\n[{msg.get('sender')}] "
                    f"{msg.get('message')}"
                )
                print("> ", end="", flush=True)

        except Exception as exc:
            print(
                f"\n[INFO] Peer connection closed: {exc}"
            )
            return


def run_peer(
    name: str,
    port: int,
    discovery_port: int,
) -> None:
    """Start one P2P peer."""

    # username -> Peer
    peers = {}

    peers_lock = threading.Lock()

    def on_peer(peer: Peer) -> None:
        """
        Called when Peer Discovery finds or updates a peer.

        The peer is always updated in the dictionary,
        but the console message is printed only the
        first time that peer is discovered.
        """
        with peers_lock:
            is_new = peer.username not in peers
            peers[peer.username] = peer

        if is_new:
            print(
                f"\n[DISCOVERY] "
                f"{peer.username} @ "
                f"{peer.ip}:{peer.tcp_port}"
            )
            print("> ", end="", flush=True)

    # Start UDP Peer Discovery
    discovery = PeerDiscovery(
        username=name,
        tcp_port=port,
        discovery_port=discovery_port,
        on_peer_discovered=on_peer,
        on_peer_updated=on_peer,
    )

    # TCP listener
    listener = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM,
    )

    listener.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1,
    )

    listener.bind(
        ("0.0.0.0", port)
    )

    listener.listen(10)

    def accept_loop() -> None:
        """Accept incoming TCP connections."""
        while True:
            try:
                conn, addr = listener.accept()

                print(
                    f"\n[TCP] Incoming connection "
                    f"from {addr}"
                )

                threading.Thread(
                    target=recv_loop,
                    args=(conn,),
                    daemon=True,
                ).start()

            except OSError:
                # Listener was closed during shutdown.
                return

    # Start TCP accept thread
    threading.Thread(
        target=accept_loop,
        daemon=True,
    ).start()

    # Start Peer Discovery
    discovery.start()

    print(
        f"[PEER] {name} listening on TCP {port}"
    )

    print(
        "[PEER] UDP discovery started. "
        "Type a peer username to connect, "
        "or 'peers'."
    )

    try:
        while True:
            command = input("> ").strip()

            # Exit the program
            if command.lower() == "exit":
                break

            # Show discovered peers
            if command.lower() == "peers":
                with peers_lock:
                    current = list(peers.values())

                if not current:
                    print(
                        "[DISCOVERY] No peers discovered."
                    )
                else:
                    print("\n--- PEERS ---")

                    for peer in current:
                        print(
                            f"- {peer.username}: "
                            f"{peer.ip}:{peer.tcp_port}"
                        )

                    print("-------------")

                continue

            # Find selected peer
            with peers_lock:
                peer = peers.get(command)

            if peer is None:
                print(
                    "[INFO] Unknown peer. "
                    "Use 'peers' first."
                )
                continue

            # Connect to selected peer
            conn = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )

            try:
                conn.connect(
                    (peer.ip, peer.tcp_port)
                )

            except OSError as exc:
                print(
                    f"[TCP] Could not connect to "
                    f"{peer.username}: {exc}"
                )
                conn.close()
                continue

            print(
                f"[TCP] Connected to "
                f"{peer.username} at "
                f"{peer.ip}:{peer.tcp_port}"
            )

            # Receive messages in background
            threading.Thread(
                target=recv_loop,
                args=(conn,),
                daemon=True,
            ).start()

            # Chat loop
            while True:
                try:
                    text = input(
                        f"{name} -> "
                        f"{peer.username}: "
                    ).strip()

                except (KeyboardInterrupt, EOFError):
                    conn.close()
                    return

                # Return to peer selection
                if text.lower() == "/back":
                    conn.close()
                    break

                # Exit completely
                if text.lower() == "/exit":
                    conn.close()
                    return

                # Ignore empty messages
                if not text:
                    continue

                try:
                    conn.sendall(
                        make_chat_message(
                            name,
                            peer.username,
                            text,
                        )
                    )

                except OSError as exc:
                    print(
                        f"[TCP] Send failed: {exc}"
                    )
                    conn.close()
                    break

    except KeyboardInterrupt:
        print("\n[PEER] Stopping...")

    finally:
        discovery.stop()

        try:
            listener.close()
        except OSError:
            pass

        print("[PEER] Stopped.")


def main() -> None:
    """Program entry point."""

    parser = argparse.ArgumentParser(
        description="P2P Peer Discovery + TCP Chat"
    )

    parser.add_argument(
        "--name",
        required=True,
        help="Peer username",
    )

    parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="TCP listening port",
    )

    parser.add_argument(
        "--discovery-port",
        type=int,
        default=37020,
        help="UDP discovery port",
    )

    args = parser.parse_args()

    run_peer(
        args.name,
        args.port,
        args.discovery_port,
    )


if __name__ == "__main__":
    main()