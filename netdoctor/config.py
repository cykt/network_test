"""Application configuration and validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_CONFIG: dict[str, Any] = {
    "repetitions": 5,
    "timeout_seconds": 5.0,
    "pause_between_runs_seconds": 0.25,
    "target": {
        "name": "Example target",
        "host": "example.com",
        "tcp_port": 443,
        "http_url": "https://example.com/",
        "download_url": None,
    },
}


def _validate_url(value: str, field_name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError(f"{field_name} must be an absolute http(s) URL")


@dataclass(frozen=True, slots=True)
class TargetConfig:
    """One endpoint group used for a diagnostic run."""

    name: str
    host: str
    tcp_port: int
    http_url: str
    download_url: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("target.name must not be empty")
        if not self.host.strip() or any(character.isspace() for character in self.host):
            raise ValueError("target.host must be a non-empty host name or IP address")
        if not 1 <= self.tcp_port <= 65535:
            raise ValueError("target.tcp_port must be between 1 and 65535")
        _validate_url(self.http_url, "target.http_url")
        if self.download_url is not None:
            _validate_url(self.download_url, "target.download_url")

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> TargetConfig:
        return cls(
            name=str(values["name"]),
            host=str(values["host"]),
            tcp_port=int(values["tcp_port"]),
            http_url=str(values["http_url"]),
            download_url=(
                None if values.get("download_url") is None else str(values["download_url"])
            ),
        )


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated settings for one NetDoctor execution."""

    repetitions: int
    timeout_seconds: float
    pause_between_runs_seconds: float
    target: TargetConfig

    def __post_init__(self) -> None:
        if not 5 <= self.repetitions <= 10:
            raise ValueError("repetitions must be between 5 and 10")
        if not 0 < self.timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be greater than 0 and at most 60")
        if not 0 <= self.pause_between_runs_seconds <= 10:
            raise ValueError("pause_between_runs_seconds must be between 0 and 10")

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> AppConfig:
        try:
            return cls(
                repetitions=int(values["repetitions"]),
                timeout_seconds=float(values["timeout_seconds"]),
                pause_between_runs_seconds=float(values["pause_between_runs_seconds"]),
                target=TargetConfig.from_dict(values["target"]),
            )
        except KeyError as error:
            raise ValueError(f"missing configuration field: {error.args[0]}") from error

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load and validate a UTF-8 JSON configuration file."""

    if path is None:
        return AppConfig.from_dict(DEFAULT_CONFIG)

    config_path = Path(path)
    try:
        values = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"configuration file not found: {config_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {config_path}: {error.msg}") from error

    if not isinstance(values, dict):
        raise ValueError("configuration root must be a JSON object")
    return AppConfig.from_dict(values)
