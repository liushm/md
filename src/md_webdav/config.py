from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    base_url: str
    remote_dir: str
    username: str
    password: str
    proxy: str
    timeout_seconds: float
    max_size_bytes: int
    source: Path


def _candidate_paths() -> list[Path]:
    paths: list[Path] = []

    if configured := os.getenv("MD_CONFIG"):
        paths.append(Path(configured).expanduser())

    paths.append(Path.cwd() / "md.toml")
    paths.append(Path(__file__).resolve().parents[2] / "md.toml")

    if appdata := os.getenv("APPDATA"):
        paths.append(Path(appdata) / "md" / "config.toml")
    paths.append(Path.home() / ".config" / "md" / "config.toml")

    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved not in result:
            result.append(resolved)
    return result


def load_settings() -> Settings:
    config_path = next((path for path in _candidate_paths() if path.is_file()), None)
    if config_path is None:
        searched = "\n".join(f"  - {path}" for path in _candidate_paths())
        raise ConfigError(
            "找不到配置文件 md.toml。已检查：\n"
            f"{searched}\n"
            "可以设置 MD_CONFIG 指向配置文件。"
        )

    try:
        with config_path.open("rb") as file:
            data = tomllib.load(file)["webdav"]
        base_url = str(data["base_url"]).rstrip("/")
        remote_dir = "/" + str(data["remote_dir"]).strip("/")
        username = str(data["username"])
        password = str(data["password"])
    except (KeyError, TypeError, ValueError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"配置文件格式错误：{config_path}: {exc}") from exc

    return Settings(
        base_url=base_url,
        remote_dir=remote_dir,
        username=username,
        password=password,
        proxy=str(data.get("proxy", "")),
        timeout_seconds=float(data.get("timeout_seconds", 120)),
        max_size_bytes=int(float(data.get("max_size_mib", 5)) * 1024 * 1024),
        source=config_path,
    )
