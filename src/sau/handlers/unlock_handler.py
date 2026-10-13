"""Unlock achievements for one appid — writes the bitfield, snapshots first."""
from __future__ import annotations

from dataclasses import dataclass

from sau.bootstrap.paths import SteamPaths
from sau.core.stats_codec import StatsCodec, StatsCodecError
from sau.models.config import RuntimeConfig
from sau.models.schema import AppSchema
from sau.services.backup_service import BackupService
from sau.services.logging_service import get_logger
from sau.services.steam_state_writer import SteamStateWriter
from sau.utils.achievement_ids import resolve_ids


@dataclass(slots=True)
class _Result:
    appid: int
    requested: int
    unlocked: int
    skipped: list[str]


log = get_logger("unlock")


class UnlockHandler:
    def __init__(self, paths: SteamPaths, codec: StatsCodec, config: RuntimeConfig) -> None:
        self._paths = paths
        self._codec = codec
        self._config = config
        self._backup = BackupService(paths, config)
        self._writer = SteamStateWriter(paths, config)

    def run(self, schema: AppSchema, ids: list[str]) -> _Result:
        targets = resolve_ids(schema, ids)
        skipped = [t for t in ids if t not in {a.api_name for a in schema.achievements} and t != "all"]
        if not targets:
            return _Result(appid=schema.appid, requested=len(ids), unlocked=0, skipped=skipped)

        total = 0
        for steamid in self._steamids_for_appid(schema.appid):
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
                if not blob.is_unlocked(idx):
                    blob.set_unlocked(idx, True)
                    total += 1
            self._writer.write(stats_path, self._codec.encode(blob), schema.appid, steamid)
        return _Result(
            appid=schema.appid,
            requested=len(ids),
            unlocked=total,
            skipped=sorted(set(skipped)),
        )

    def _steamids_for_appid(self, appid: int) -> list[int]:
        return self._paths.iter_steamids()