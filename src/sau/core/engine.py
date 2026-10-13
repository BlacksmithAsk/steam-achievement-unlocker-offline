"""AchievementEngine — top-level orchestration for scan/unlock/lock/backup/restore."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sau.bootstrap.paths import SteamPaths
from sau.core.schema_parser import SchemaParser, SchemaParseError
from sau.core.stats_codec import StatsCodec, StatsCodecError
from sau.handlers.unlock_handler import UnlockHandler
from sau.handlers.lock_handler import LockHandler
from sau.handlers.backup_handler import BackupHandler
from sau.handlers.restore_handler import RestoreHandler
from sau.models.config import RuntimeConfig
from sau.models.schema import AppSchema
from sau.services.logging_service import get_logger

log = get_logger("engine")


@dataclass(slots=True)
class ScanRow:
    appid: int
    achievement_count: int
    display_name: str | None


@dataclass(slots=True)
class MutationResult:
    appid: int
    requested: int
    unlocked: int
    skipped: list[str] = field(default_factory=list)


class AchievementEngine:
    def __init__(self, paths: SteamPaths, config: RuntimeConfig) -> None:
        self._paths = paths
        self._config = config
        self._parser = SchemaParser(paths.appcache_stats)
        self._codec = StatsCodec()

    def _load_schema(self, appid: int) -> AppSchema:
        return self._parser.load(appid)

    def scan_apps(self) -> list[ScanRow]:
        rows: list[ScanRow] = []
        for appid in self._parser.list_appids():
            try:
                schema = self._load_schema(appid)
            except SchemaParseError as exc:
                log.warning("schema parse failed for {}: {}", appid, exc)
                continue
            rows.append(
                ScanRow(
                    appid=appid,
                    achievement_count=len(schema.achievements),
                    display_name=schema.display_name,
                )
            )
        return rows

    def unlock(self, appid: int, ids: list[str]) -> MutationResult:
        schema = self._load_schema(appid)
        handler = UnlockHandler(self._paths, self._codec, self._config)
        return handler.run(schema, ids)

    def lock(self, appid: int, ids: list[str]) -> MutationResult:
        schema = self._load_schema(appid)
        handler = LockHandler(self._paths, self._codec, self._config)
        return handler.run(schema, ids)

    def backup(self, appid: int) -> Path:
        schema = self._load_schema(appid)
        handler = BackupHandler(self._paths, self._config)
        return handler.run(schema)

    def restore(self, appid: int) -> None:
        handler = RestoreHandler(self._paths, self._config)
        handler.run(appid)


__all__ = ["AchievementEngine", "MutationResult", "ScanRow", "StatsCodecError"]