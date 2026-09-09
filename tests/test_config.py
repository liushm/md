from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from md_webdav.config import load_settings


class ConfigTests(unittest.TestCase):
    def test_loads_external_toml_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.toml"
            path.write_text(
                """[webdav]
base_url = "https://dav.example.com/"
remote_dir = "backup"
username = "alice"
password = "secret"
proxy = "socks5h://127.0.0.1:7890"
timeout_seconds = 30
max_size_mib = 7
""",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"MD_CONFIG": str(path)}):
                settings = load_settings()

            self.assertEqual(settings.base_url, "https://dav.example.com")
            self.assertEqual(settings.remote_dir, "/backup")
            self.assertEqual(settings.max_size_bytes, 7 * 1024 * 1024)
            self.assertEqual(settings.source, path.resolve())


if __name__ == "__main__":
    unittest.main()
