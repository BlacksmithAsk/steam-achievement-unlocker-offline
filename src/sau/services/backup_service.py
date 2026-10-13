"""Timestamped backups under data/backups/<appid>/<utc-iso>/."""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from sau.bootstrap.paths import SteamPaths
from sau.models.config import RuntimeConfig
from sau.services.logging_service import get_logger

log = get_logger("backup_service")


class BackupService:
    def __init__(self, paths: SteamPaths, config: RuntimeConfig) -> None:
        self._paths = paths
        self._config = config
        self._root = config.backup_root

    def session_dir(self, appid: int) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H