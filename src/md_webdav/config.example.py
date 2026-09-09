from __future__ import annotations

from pathlib import PurePosixPath

# Copy this file to config.py and fill in your own values.
BASE_URL = "https://dav.example.com"
REMOTE_DIR = "/backup"
USERNAME = "username"
PASSWORD = "password"
PROXY = "socks5h://127.0.0.1:7890"
TIMEOUT_SECONDS = 120.0
MAX_SIZE_BYTES = 5 * 1024 * 1024


def remote_path(name: str = "") -> str:
    root = "/" + REMOTE_DIR.strip("/") if REMOTE_DIR.strip("/") else "/"
    if not name:
        return root
    return str(PurePosixPath(root) / name)
