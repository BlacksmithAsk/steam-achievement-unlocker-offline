"""Reverse an unlock — sets the bit back to zero."""
from __future__ import annotations

from sau.bootstrap.paths import SteamPaths
from sau.core.stats_codec import StatsCodec, StatsCodecError
from sau.handlers.unlock_handler import _Result
from sau.models.config import RuntimeConfig
from sau.models.schema import AppSchema
from sau.services.backup_service import BackupService
from sau.services.logging_service import get_logger
from sau.services.steam_state_writer import SteamStateWriter
from sau.utils.achievement_ids import resolve_ids

log = get_logger("lock")


class LockHandler:
    def __init__(self, paths: SteamPaths, codec: StatsCodec, config: RuntimeConfig) -> None:
        self._paths = paths
        self._codec = codec
        self._config = config
        self._backup = BackupService(paths, config)
        self._writer = SteamStateWriter(paths, config)

    def run(self, schema: AppSchema, ids: list[str]) -> _Result:
        targets = resolve_ids(schema, ids)
        total = 0
        skipped: list[str] = []
        for steamid in self._paths.iter_steamids():
            stats_path = self._paths.user_stats_dir(steamid) / f"UserGameStats_{steamid}_{schema.appid}.bin"
            if not stats_path.is_file():
                continue
            self._backup.snapshot(schema.appid, steamid, stats_path)
            try:
                blob = self._codec.decode(stats_path.read_bytes())
            except StatsCodecError as exc:
                log.warning("codec error on {}: {}", stats_path, exc)
                continue
            for ach in targets:
                idx = schema.index_of(ach.api_name)
                if idx is None or idx >= blob.achievement_count:
                    skipped.append(ach.api_name)
                    continue
                if blob.is_unlocked(idx):
                    blob.set_unlocked(idx, False)
                    total += 1
            self._writer.write(stats_path, self._codec.encode(blob), schema.appid, steamid)
        return _Result(
            appid=schema.appid,
            requested=len(ids),
            unlocked=total,
            skipped=sorted(set(skipped)),
        )