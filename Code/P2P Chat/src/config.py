"""Centralized application configuration loaded from config/config.json."""
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.json"


def _load_config():
    with CONFIG_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = _load_config()
CLIENT_HOST = CONFIG["client"]["host"]
CLIENT_PORT = int(CONFIG["client"]["port"])
DISCOVERY_SERVER_HOST = CONFIG["discovery_server"]["host"]
DISCOVERY_SERVER_PORT = int(CONFIG["discovery_server"]["port"])
LOG_LEVEL = CONFIG["logging"]["level"]
LOG_DIRECTORY = CONFIG["logging"]["directory"]
CLIENT_LOG_FILE = CONFIG["logging"]["client_file"]
DISCOVERY_SERVER_LOG_FILE = CONFIG["logging"]["discovery_server_file"]
LOG_MAX_BYTES = int(CONFIG["logging"]["max_bytes"])
LOG_BACKUP_COUNT = int(CONFIG["logging"]["backup_count"])
MAX_PACKET_SIZE = int(CONFIG["protocol"]["max_packet_size"])
PROTOCOL_VERSION = CONFIG["protocol"]["version"]
CHUNK_SIZE = int(CONFIG["transfer"]["chunk_size"])
MAX_FILE_SIZE = int(CONFIG["transfer"]["max_file_size"])


def get_client_config():
    return dict(CONFIG["client"])


def get_discovery_server_config():
    return dict(CONFIG["discovery_server"])
