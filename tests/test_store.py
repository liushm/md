from __future__ import annotations

import tempfile
import unittest
from pathlib import Path, PurePosixPath

from md_webdav.store import (
    MdError,
    RemoteEntry,
    Store,
    display_width,
    format_entries,
    local_size,
)


class FakeClient:
    def __init__(self) -> None:
        self.entries = {"/": {"type": "directory"}}

    @staticmethod
    def norm(path: str) -> str:
        value = "/" + path.strip("/")
        return value if value != "" else "/"

    def exists(self, path: str) -> bool:
        return self.norm(path) in self.entries

    def isdir(self, path: str) -> bool:
        return self.entries[self.norm(path)]["type"] == "directory"

    def mkdir(self, path: str) -> None:
        path = self.norm(path)
        if path in self.entries:
            raise RuntimeError("already exists")
        parent = str(PurePosixPath(path).parent)
        if parent not in self.entries:
            raise RuntimeError("parent missing")
        self.entries[path] = {"type": "directory"}

    def upload_file(self, from_path, to_path: str, overwrite: bool = False) -> None:
        path = self.norm(to_path)
        if path in self.entries and not overwrite:
            raise RuntimeError("already exists")
        self.entries[path] = {
            "type": "file",
            "data": Path(from_path).read_bytes(),
        }

    def download_file(self, from_path: str, to_path) -> None:
        Path(to_path).write_bytes(self.entries[self.norm(from_path)]["data"])

    def ls(self, path: str, detail: bool = True):
        path = self.norm(path)
        prefix = path.rstrip("/") + "/"
        result = []
        for item_path, item in self.entries.items():
            if not item_path.startswith(prefix):
                continue
            remainder = item_path[len(prefix) :]
            if not remainder or "/" in remainder:
                continue
            result.append(
                {
                    "name": item_path.lstrip("/"),
                    "type": item["type"],
                    "content_length": len(item.get("data", b"")),
                }
            )
        return result

    def info(self, path: str):
        item = self.entries[self.norm(path)]
        return {
            "name": self.norm(path).lstrip("/"),
            "type": item["type"],
            "content_length": len(item.get("data", b"")),
        }

    def remove(self, path: str) -> None:
        path = self.norm(path)
        for item_path in list(self.entries):
            if item_path == path or item_path.startswith(path.rstrip("/") + "/"):
                del self.entries[item_path]


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.store = Store(self.client, "/backup", 5 * 1024 * 1024)
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_push_file_and_reject_duplicate(self) -> None:
        source = self.root / "a.txt"
        source.write_text("hello", encoding="utf-8")

        name, size = self.store.push(source, lambda _: True)

        self.assertEqual(name, "a.txt")
        self.assertEqual(size, 5)
        self.assertEqual(self.client.entries["/backup/a.txt"]["data"], b"hello")
        with self.assertRaisesRegex(MdError, "同名"):
            self.store.push(source, lambda _: True)

    def test_large_file_requires_confirmation(self) -> None:
        source = self.root / "large.bin"
        source.write_bytes(b"123456")
        store = Store(self.client, "/backup", 5)

        with self.assertRaisesRegex(MdError, "取消"):
            store.push(source, lambda _: False)

        self.assertNotIn("/backup/large.bin", self.client.entries)

    def test_push_and_get_directory(self) -> None:
        source = self.root / "config"
        (source / "nested").mkdir(parents=True)
        (source / "a.txt").write_text("a", encoding="utf-8")
        (source / "nested" / "b.txt").write_text("bb", encoding="utf-8")

        self.store.push(source, lambda _: True)
        destination_root = self.root / "downloads"
        destination_root.mkdir()
        destination = self.store.get("config", destination_root)

        self.assertEqual((destination / "a.txt").read_text(encoding="utf-8"), "a")
        self.assertEqual(
            (destination / "nested" / "b.txt").read_text(encoding="utf-8"),
            "bb",
        )

    def test_get_rejects_existing_local_name(self) -> None:
        self.client.mkdir("/backup")
        source = self.root / "a.txt"
        source.write_text("remote", encoding="utf-8")
        self.client.upload_file(source, "/backup/a.txt")
        local = self.root / "download"
        local.mkdir()
        (local / "a.txt").write_text("local", encoding="utf-8")

        with self.assertRaisesRegex(MdError, "本地已存在"):
            self.store.get("a.txt", local)


    def test_remove_file_and_reject_missing_name(self) -> None:
        self.client.mkdir("/backup")
        source = self.root / "a.txt"
        source.write_text("remote", encoding="utf-8")
        self.client.upload_file(source, "/backup/a.txt")

        name, kind = self.store.remove("a.txt", lambda *_: True)

        self.assertEqual((name, kind), ("a.txt", "file"))
        self.assertNotIn("/backup/a.txt", self.client.entries)
        with self.assertRaisesRegex(MdError, "不存在"):
            self.store.remove("a.txt", lambda *_: True)

    def test_remove_can_be_cancelled(self) -> None:
        self.client.mkdir("/backup")
        source = self.root / "a.txt"
        source.write_text("remote", encoding="utf-8")
        self.client.upload_file(source, "/backup/a.txt")

        with self.assertRaisesRegex(MdError, "取消"):
            self.store.remove("a.txt", lambda *_: False)

        self.assertIn("/backup/a.txt", self.client.entries)

    def test_list_output_aligns_chinese_and_ascii_names(self) -> None:
        lines = format_entries(
            [
                RemoteEntry("a.md", "file", 1024),
                RemoteEntry("中文笔记.md", "file", 10 * 1024),
            ]
        )

        first_size_column = display_width(lines[0][: lines[0].index("1.00 KiB")])
        second_size_column = display_width(lines[1][: lines[1].index("10.00 KiB")])
        self.assertEqual(first_size_column, second_size_column)

    def test_list_includes_recursive_directory_size(self) -> None:
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "one").write_bytes(b"123")
        (folder / "two").write_bytes(b"4567")
        self.store.push(folder, lambda _: True)

        entries = self.store.list_entries()

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].name, "folder")
        self.assertEqual(entries[0].kind, "directory")
        self.assertEqual(entries[0].size, 7)

    def test_local_size_sums_directory(self) -> None:
        folder = self.root / "folder"
        folder.mkdir()
        (folder / "a").write_bytes(b"12")
        (folder / "b").write_bytes(b"345")
        self.assertEqual(local_size(folder), 5)


if __name__ == "__main__":
    unittest.main()
