"""Codec for UserGameStats_<steamid64>_<appid>.bin.

Layout (little-endian, observed across 2023–2025 clients):

  offset 0   u32   magic           0x53474154 ("TGAS" LE) for pre-2024, 0x54414753 for 2024+
  offset 4   u32   version         2 or 3
  offset 8   u64   steamid64
  offset 16  u32   appid
  offset 20  u32   achievement_count
  offset 24  N*4   achievement bitfield (u32 bit per achievement, LSB first)

Anything past the bitfield is opaque to us and preserved verbatim on write.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

_MAGICS = {0x53474154, 0x54414753}
_HEADER = struct.Struct("<IIIQII")  # magic, version, pad, steamid64, appid, count
_HEADER_SIZE = _HEADER.size


class StatsCodecError(RuntimeError):
    pass


@dataclass(slots=True)
class StatsBlob:
    raw: bytes
    steamid64: int
    appid: int
    achievement_count: int
    bitfield: bytearray
    tail: bytes

    def is_unlocked(self, index: int) -> bool:
        if index < 0 or index >= self.achievement_count:
            raise StatsCodecError(f"achievement index {index} out of range")
        return bool(self.bitfield[index])

    def set_unlocked(self, index: int, unlocked: bool) -> None:
        if index < 0 or index >= self.achievement_count:
            raise StatsCodecError(f"achievement index {index} out of range")
        self.bitfield[index] = 1 if unlocked else 0

    def to_bytes(self) -> bytes:
        header = _HEADER.pack(
            struct.unpack_from("<I", self.raw, 0)[0],
            struct.unpack_from("<I", self.raw, 4)[0],
            0,
            self.steamid64,
            self.appid,
            self.achievement_count,
        )
        return header + bytes(self.bitfield) + self.tail


class StatsCodec:
    def decode(self, blob: bytes) -> StatsBlob:
        if len(blob) < _HEADER_SIZE:
            raise StatsCodecError("blob shorter than header")
        magic, version, _pad, steamid64, appid, count = _HEADER.unpack_from(blob, 0)
        if magic not in _MAGICS:
            raise StatsCodecError(f"bad magic 0x{magic:08x}")
        if version not in (2, 3):
            raise StatsCodecError(f"unsupported version {version}")
        if count > 10_000:
            raise StatsCodecError(f"implausible achievement count {count}")
        end = _HEADER_SIZE + count
        if end > len(blob):
            raise StatsCodecError("bitfield overruns blob")
        return StatsBlob(
            raw=blob,
            steamid64=steamid64,
            appid=appid,
            achievement_count=count,
            bitfield=bytearray(blob[_HEADER_SIZE:end]),
            tail=blob[end:],
        )

    def encode(self, stats: StatsBlob) -> bytes:
        return stats.to_bytes()