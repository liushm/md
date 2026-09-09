from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import unicodedata
from typing import Callable, Protocol


class MdError(Exception):
    """An expected, user-facing error."""


class WebDavClient(Protocol):
    def exists(self, path: str) -> bool: ...
    def isdir(self, path: str) -> bool: ...
    def mkdir(self, path: str) -> None: ...
    def ls(self, path: str, detail: bool = True): ...
    def info(self, path: str): ...
    def upload_file(self, from_path, to_path: str, overwrite: bool = False) -> None: ...
    def download_file(self, from_path: str, to_path) -> None: ...
    def remove(self, path: str) -> None: ...


@dataclass(frozen=True)
class RemoteEntry:
    name: str
    kind: str
    size: int


def join_remote(root: str, name: str = "") -> str:
    normalized_root = "/" + root.strip("/") if root.strip("/") else "/"
    if not name:
        return normalized_root
    return str(PurePosixPath(normalized_root) / name)


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= 1024
    return f"{size} B"


def display_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        width += 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
    return width


def pad_display(text: str, width: int) -> str:
    return text + " " * max(0, width - display_width(text))


def format_entries(entries: list[RemoteEntry]) -> list[str]:
    if not entries:
        return []

    names = [entry.name + ("/" if entry.kind == "directory" else "") for entry in entries]
    sizes = [human_size(entry.size) for entry in entries]
    name_width = max(display_width(name) for name in names)
    return [
        f"{pad_display(name, name_width)}  {size}"
        for name, size in zip(names, sizes)
    ]


def local_size(path: Path) -> int:
    if path.is_symlink():
        raise MdError(f"不支持符号链接：{path}")
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        raise MdError(f"路径不存在或不是普通文件/目录：{path}")

    total = 0
    for item in path.rglob("*"):
        if item.is_symlink():
            raise MdError(f"目录中包含符号链接，不支持上传：{item}")
        if item.is_file():
            total += item.stat().st_size
    return total


def validate_remote_name(name: str) -> str:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        raise MdError("FILENAME 只能是远程目录中的单个文件或文件夹名称")
    return name


class Store:
    def __init__(self, client: WebDavClient, remote_dir: str, size_limit: int) -> None:
        self.client = client
        self.remote_dir = join_remote(remote_dir)
        self.size_limit = size_limit

    def _ensure_remote_dir(self) -> None:
        current = ""
        for part in PurePosixPath(self.remote_dir).parts:
            if part == "/":
                continue
            current = join_remote(current, part)
            if not self.client.exists(current):
                self.client.mkdir(current)

    def push(self, source: Path, confirm: Callable[[int], bool]) -> tuple[str, int]:
        source = source.expanduser().resolve()
        size = local_size(source)

        if size > self.size_limit and not confirm(size):
            raise MdError("已取消上传")

        self._ensure_remote_dir()
        remote_target = join_remote(self.remote_dir, source.name)
        if self.client.exists(remote_target):
            raise MdError(f"远程已存在同名内容：{source.name}")

        if source.is_file():
            self.client.upload_file(source, remote_target, overwrite=False)
            return source.name, size

        self.client.mkdir(remote_target)
        try:
            for item in sorted(source.rglob("*"), key=lambda p: (len(p.parts), str(p))):
                relative = item.relative_to(source).as_posix()
                remote_item = join_remote(remote_target, relative)
                if item.is_dir():
                    self.client.mkdir(remote_item)
                elif item.is_file():
                    self.client.upload_file(item, remote_item, overwrite=False)
        except Exception:
            try:
                self.client.remove(remote_target)
            except Exception:
                pass
            raise

        return source.name, size

    def get(self, name: str, destination_dir: Path) -> Path:
        name = validate_remote_name(name)
        remote_source = join_remote(self.remote_dir, name)
        destination = destination_dir.resolve() / name

        if destination.exists():
            raise MdError(f"本地已存在同名内容：{destination}")
        if not self.client.exists(remote_source):
            raise MdError(f"远程内容不存在：{name}")

        if self.client.isdir(remote_source):
            destination.mkdir()
            self._download_directory(remote_source, destination)
        else:
            self.client.download_file(remote_source, destination)

        return destination

    def _download_directory(self, remote_dir: str, local_dir: Path) -> None:
        for item in self.client.ls(remote_dir, detail=True):
            remote_item = "/" + str(item["name"]).lstrip("/")
            item_name = PurePosixPath(remote_item.rstrip("/")).name
            if not item_name or item_name in {".", ".."}:
                raise MdError(f"服务端返回了无效名称：{item_name!r}")

            local_item = local_dir / item_name
            if item.get("type") == "directory":
                local_item.mkdir()
                self._download_directory(remote_item, local_item)
            else:
                self.client.download_file(remote_item, local_item)

    def remove(self, name: str, confirm: Callable[[str, str], bool]) -> tuple[str, str]:
        name = validate_remote_name(name)
        remote_target = join_remote(self.remote_dir, name)
        if not self.client.exists(remote_target):
            raise MdError(f"远程内容不存在：{name}")

        kind = "directory" if self.client.isdir(remote_target) else "file"
        if not confirm(name, kind):
            raise MdError("已取消删除")

        self.client.remove(remote_target)
        return name, kind

    def list_entries(self) -> list[RemoteEntry]:
        if not self.client.exists(self.remote_dir):
            return []

        entries = []
        for item in self.client.ls(self.remote_dir, detail=True):
            remote_item = "/" + str(item["name"]).lstrip("/")
            kind = str(item.get("type") or "file")
            name = PurePosixPath(remote_item.rstrip("/")).name
            size = self.remote_size(remote_item) if kind == "directory" else int(
                item.get("content_length") or item.get("size") or 0
            )
            entries.append(RemoteEntry(name=name, kind=kind, size=size))
        return sorted(entries, key=lambda entry: entry.name.casefold())

    def remote_size(self, path: str) -> int:
        if not self.client.isdir(path):
            info = self.client.info(path)
            return int(info.get("content_length") or info.get("size") or 0)

        total = 0
        for item in self.client.ls(path, detail=True):
            remote_item = "/" + str(item["name"]).lstrip("/")
            if item.get("type") == "directory":
                total += self.remote_size(remote_item)
            else:
                total += int(item.get("content_length") or item.get("size") or 0)
        return total
