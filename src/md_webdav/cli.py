from __future__ import annotations

import argparse
import sys
from pathlib import Path

from webdav4.client import Client

from . import config
from .store import MdError, Store, human_size


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="md", description="极简 WebDAV 文件备份工具")
    commands = parser.add_subparsers(dest="command", required=True)

    push = commands.add_parser("push", help="上传一个文件或文件夹")
    push.add_argument("filepath", type=Path, help="本地文件或文件夹路径")

    get = commands.add_parser("get", help="下载一个文件或文件夹到当前目录")
    get.add_argument("filename", help="远程目录中的名称")

    commands.add_parser("ls", help="列出远程目录中的内容")
    return parser


def build_client() -> Client:
    options = {
        "auth": (config.USERNAME, config.PASSWORD),
        "timeout": config.TIMEOUT_SECONDS,
        "trust_env": False,
    }
    if config.PROXY:
        options["proxy"] = config.PROXY
    return Client(config.BASE_URL, **options)


def confirm_large_file(size: int) -> bool:
    answer = input(
        f"目标大小为 {human_size(size)}，超过 5 MiB，是否继续上传？[y/N] "
    )
    return answer.strip().lower() in {"y", "yes"}


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = Store(build_client(), config.REMOTE_DIR, config.MAX_SIZE_BYTES)

    try:
        if args.command == "push":
            name, size = store.push(args.filepath, confirm_large_file)
            print(f"上传成功：{name} ({human_size(size)})")
        elif args.command == "get":
            destination = store.get(args.filename, Path.cwd())
            print(f"下载成功：{destination}")
        elif args.command == "ls":
            entries = store.list_entries()
            if not entries:
                print("远程目录为空")
            for entry in entries:
                suffix = "/" if entry.kind == "directory" else ""
                print(f"{entry.name}{suffix}\t{human_size(entry.size)}")
        return 0
    except MdError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"WebDAV 操作失败：{exc}", file=sys.stderr)
        return 1


def main() -> None:
    raise SystemExit(run())
