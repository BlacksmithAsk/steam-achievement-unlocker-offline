"""Snapshot UserGameStats blobs and the schema for one appid."""
from __future__ import annotations

from pathlib import Path

from sau.bootstrap.paths import SteamPaths
from sau.models.config import RuntimeConfig
from sau.models.schema import AppSchema
from sau.services.backup_service import BackupService
from sau.services.logging_service import get_logger

log = get_logger("backup")


class BackupHandler:
    def __init__(self, paths: SteamPaths, config: RuntimeConfig) -> None:
        self._paths = paths
        self._config = config
        self._backup = BackupService(paths, config)

    def run(self, schema: AppSchema) -> Path:
        dest = self._backup.session_dir(schema.appid)
        for steamid in self._paths.iter_steamids():
            stats_path = self._paths.user_stats_dir(steamid) / f"UserGameStats_{steamid}_{schema.appid}.bin"
            if stats_path.is_file():
                self._backup.snapshot(schema.appid, steamid, stats_path)
        schema_path = self._paths.appcache_stats / f"UserGameStatsSchema_{schema.appid}.bin"
        if schema_path.is_file():
            self._backup.copy_into(schema_path, dest)
        log.info("backup complete for appid {} -> {}", schema.appid, dest)
        return dest