"""Restore the most recent backup for an appid."""
from __future__ import annotations

from sau.bootstrap.paths import SteamPaths
from sau.models.config import RuntimeConfig
from sau.services.backup_service import BackupService
from sau.services.logging_service import get_logger

log = get_logger("restore")


class RestoreHandler:
    def __init__(self, paths: SteamPaths, config: RuntimeConfig) -> None:
        self._paths = paths
        self._config = config
        self._backup = BackupService(paths, config)

    def run(self, appid: int) -> None:
        session = self._backup.latest_session(appid)
        if session is None:
            raise FileNotFoundError(f"no backups for appid {appid}")
        self._backup.restore_session(session)
        log.info("restored appid {} from {}", appid, session)