"""Runtime configuration, sourced entirely from environment variables."""

import os
from dataclasses import dataclass, field
from typing import List


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str, default: List[str]) -> List[str]:
    val = os.environ.get(name)
    if not val:
        return list(default)
    return [item.strip() for item in val.split(",") if item.strip()]


DEFAULT_SERVICES = [
    "ssh",
    "cron",
    "nginx",
    "docker",
    "systemd-resolved",
    "ufw",
]


@dataclass
class Config:
    host: str = field(default_factory=lambda: os.environ.get("MONITOR_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("MONITOR_PORT", "8080")))
    token: str = field(default_factory=lambda: os.environ.get("MONITOR_TOKEN", "").strip())
    cors_origins: str = field(default_factory=lambda: os.environ.get("MONITOR_CORS_ORIGINS", "").strip())
    services: List[str] = field(default_factory=lambda: _env_list("MONITOR_SERVICES", DEFAULT_SERVICES))
    hide_processes: bool = field(default_factory=lambda: _env_bool("MONITOR_HIDE_PROCESSES", False))
    terminal_token: str = field(default_factory=lambda: os.environ.get("MONITOR_TERMINAL_TOKEN", "").strip())
    process_limit: int = field(default_factory=lambda: int(os.environ.get("MONITOR_PROCESS_LIMIT", "50")))
    history_points: int = field(default_factory=lambda: int(os.environ.get("MONITOR_HISTORY_POINTS", "60")))

    @property
    def auth_enabled(self) -> bool:
        return bool(self.token)

    @property
    def terminal_enabled(self) -> bool:
        return bool(self.terminal_token)

    @property
    def socketio_cors(self):
        if self.cors_origins:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return []

    def summary(self) -> str:
        lines = [
            f"  bind             {self.host}:{self.port}",
            f"  auth             {'token required' if self.auth_enabled else 'OPEN (no token)'}",
            f"  cors origins     {self.cors_origins or 'same-origin only'}",
            f"  web terminal     {'ENABLED (token required)' if self.terminal_enabled else 'disabled'}",
            f"  watched services {', '.join(self.services)}",
            f"  process list     {'hidden' if self.hide_processes else f'top {self.process_limit}'}",
        ]
        return "\n".join(lines)
