"""Locate Steam install paths on Windows.

Registry is checked first (HKCU/HKLM Software\\Valve\\Steam), then the
conventional Program Files locations, then any libraryfolders.vdf entries.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    import winreg  # type: ignore[import-not-found]
except ImportError:  # non-Windows dev boxes
    winreg = None  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class SteamPaths:
    root: Path
    userdata: Path
    appcache_stats: Path

    @classmethod
    def from_root(cls, root: Path) -> "SteamPaths":
        root = root.resolve()
        return cls(
            root=root,
            userdata=root / "userdata",
            appcache_stats=root / "appcache" / "stats",
        )

    def user_stats_dir(self, steamid64: int) -> Path:
        return self.userdata / str(steamid64) / "config"

    def iter_steamids(self) -> list[int]:
        if not self.userdata.is_dir():
            return []
        out: list[int] = []
        for child in self.userdata.iterdir():
            if child.is_dir() and child.name.isdigit():
                out.append(int(child.name))
        return sorted(out)


_REGISTRY_KEYS = (
    (r"Software\Valve\Steam", "SteamPath"),
    (r"Software\Valve\Steam", "InstallPath"),
)
_REGISTRY_ROOTS = ("HKCU", "HKLM")


def _read_registry_path() -> Path | None:
    if winreg is None:
        return None
    for hive_name in _REGISTRY_ROOTS:
        hive = getattr(winreg, hive_name, None)
        if hive is None:
            continue
        for subkey, value_name in _REGISTRY_KEYS:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    value, _ = winreg.QueryValueEx(key, value_name)
            except OSError:
                continue
            candidate = Path(str(value))
            if (candidate / "appcache" / "stats").is_dir():
                return candidate
    return None


_FALLBACKS = (
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
)


def discover_steam_paths() -> SteamPaths | None:
    env = os.environ.get("STEAM_ROOT")
    if env and (Path(env) / "appcache" / "stats").is_dir():
        return SteamPaths.from_root(Path(env))
    reg = _read_registry_path()
    if reg is not None:
        return SteamPaths.from_root(reg)
    for candidate in _FALLBACKS:
        p = Path(candidate)
        if (p / "appcache" / "stats").is_dir():
            return SteamPaths.from_root(p)
    return None