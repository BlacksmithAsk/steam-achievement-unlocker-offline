"""Parser for appcache/stats/UserGameStatsSchema_<appid>.bin.

The on-disk format is a Valve KeyValues binary blob. We only need the
achievement section: display name, list of (name, hidden, permission)
entries. Everything else is ignored.
"""
from __future__ import annotations

from pathlib import Path

from sau.models.schema import Achievement, AppSchema
from sau.services.logging_service import get_logger

log = get_logger("schema_parser")

# Valve KV binary type tags.
_KV_NONE = 0x00
_KV_STRING = 0x01
_KV_INT32 = 0x02
_KV_FLOAT32 = 0x03
_KV_PTR = 0x04
_KV_WIDESTRING = 0x05
_KV_COLOR = 0x06
_KV_UINT64 = 0x07
_KV_END = 0x08
_KV_INT64 = 0x0A

_SCHEMA_PREFIX = "UserGameStatsSchema_"
_MAX_ENTRIES = 8192  # hard cap — schema files are small; anything bigger is hostile


class SchemaParseError(RuntimeError):
    pass


class _Reader:
    __slots__ = ("_buf", "_pos")

    def __init__(self, buf: bytes) -> None:
        self._buf = buf
        self._pos = 0

    def eof(self) -> bool:
        return self._pos >= len(self._buf)

    def u8(self) -> int:
        if self._pos >= len(self._buf):
            raise SchemaParseError("unexpected eof (u8)")
        v = self._buf[self._pos]
        self._pos += 1
        return v

    def i32(self) -> int:
        if self._pos + 4 > len(self._buf):
            raise SchemaParseError("unexpected eof (i32)")
        v = int.from_bytes(self._buf[self._pos : self._pos + 4], "little", signed=True)
        self._pos += 4
        return v

    def cstr(self) -> str:
        start = self._pos
        while True:
            if self._pos >= len(self._buf):
                raise SchemaParseError("unterminated cstring")
            if self._buf[self._pos] == 0:
                break
            self._pos += 1
        raw = self._buf[start : self._pos]
        self._pos += 1
        return raw.decode("utf-8", errors="replace")


def _parse_kv(reader: _Reader, depth: int = 0) -> dict[str, object]:
    if depth > 16:
        raise SchemaParseError("kv nesting too deep")
    out: dict[str, object] = {}
    entries = 0
    while not reader.eof():
        tag = reader.u8()
        if tag == _KV_END:
            return out
        if tag == _KV_NONE:
            continue
        key = reader.cstr()
        entries += 1
        if entries > _MAX_ENTRIES:
            raise SchemaParseError("kv entry cap exceeded")
        if tag == _KV_STRING or tag == _KV_WIDESTRING:
            out[key] = reader.cstr()
        elif tag == _KV_INT32:
            out[key] = reader.i32()
        elif tag in (_KV_INT64, _KV_UINT64):
            out[key] = reader.i32()  # low word is enough for our fields
        elif tag == _KV_FLOAT32:
            reader.i32()
            out[key] = 0.0
        elif tag == _KV_COLOR:
            reader.i32()
            out[key] = 0
        elif tag == _KV_PTR:
            reader.i32()
            out[key] = None
        else:
            raise SchemaParseError(f"unknown kv tag 0x{tag:02x}")
    return out


def _extract_achievements(root: dict[str, object]) -> list[Achievement]:
    stats = root.get("stats")
    if not isinstance(stats, dict):
        return []
    out: list[Achievement] = []
    for key, value in stats.items():
        if not key.startswith("bits") or not isinstance(value, dict):
            continue
        for stat_key, stat_val in value.items():
            if not isinstance(stat_val, dict):
                continue
            name = stat_val.get("name")
            if not isinstance(name, str):
                continue
            out.append(
                Achievement(
                    api_name=stat_key,
                    display_name=name,
                    hidden=bool(stat_val.get("hidden", 0)),
                    permission=int(stat_val.get("permission", 0)),  # type: ignore[arg-type]
                )
            )
    return out


class SchemaParser:
    def __init__(self, stats_dir: Path) -> None:
        self._dir = stats_dir

    def list_appids(self) -> list[int]:
        if not self._dir.is_dir():
            return []
        out: list[int] = []
        for entry in self._dir.iterdir():
            name = entry.name
            if not name.startswith(_SCHEMA_PREFIX) or not name.endswith(".bin"):
                continue
            stem = name[len(_SCHEMA_PREFIX) : -len(".bin")]
            if stem.isdigit():
                out.append(int(stem))
        return sorted(out)

    def load(self, appid: int) -> AppSchema:
        path = self._dir / f"{_SCHEMA_PREFIX}{appid}.bin"
        if not path.is_file():
            raise SchemaParseError(f"no schema file for appid {appid}")
        try:
            blob = path.read_bytes()
        except OSError as exc:
            raise SchemaParseError(f"cannot read {path}: {exc}") from exc
        reader = _Reader(blob)
        root = _parse_kv(reader)
        display = root.get("appName")
        achievements = _extract_achievements(root)
        if not achievements:
            log.warning("no achievements parsed for appid {}", appid)
        return AppSchema(
            appid=appid,
            display_name=display if isinstance(display, str) else None,
            achievements=achievements,
            source=path,
        )