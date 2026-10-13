"""Typer CLI — the `sau` entry point.

Commands:
  scan     list installed apps with achievement schemas
  unlock   unlock one or more achievements for an appid
  lock     reverse an unlock
  backup   snapshot UserGameStats + appcache/stats for an appid
  restore  restore the most recent backup for an appid
"""
from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from sau.bootstrap.paths import SteamPaths, discover_steam_paths
from sau.core.engine import AchievementEngine
from sau.models.config import RuntimeConfig
from sau.services.logging_service import get_logger

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
console = Console()
log = get_logger("cli")


def _resolve_paths(steam_root: Path | None) -> SteamPaths:
    if steam_root is not None:
        return SteamPaths.from_root(steam_root)
    found = discover_steam_paths()
    if found is None:
        console.print("[red]Could not locate Steam. Pass --steam-root.[/red]")
        raise typer.Exit(code=2)
    return found


@app.command()
def scan(steam_root: Path | None = typer.Option(None, "--steam-root")) -> None:
    """List apps that have a parseable achievement schema in appcache/stats."""
    paths = _resolve_paths(steam_root)
    engine = AchievementEngine(paths, RuntimeConfig.load())
    rows = engine.scan_apps()
    table = Table(title=f"Schemas under {paths.appcache_stats}")
    table.add_column("appid", justify="right")
    table.add_column("achievements", justify="right")
    table.add_column("name")
    for row in rows:
        table.add_row(str(row.appid), str(row.achievement_count), row.display_name or "-")
    console.print(table)


@app.command()
def unlock(
    appid: int = typer.Argument(..., help="Steam appid"),
    ids: list[str] = typer.Argument(..., help="Achievement API names, or 'all'"),
    steam_root: Path | None = typer.Option(None, "--steam-root"),
) -> None:
    """Unlock achievements for an appid. Steam must be closed."""
    paths = _resolve_paths(steam_root)
    engine = AchievementEngine(paths, RuntimeConfig.load())
    result = engine.unlock(appid, ids)
    console.print(f"[green]unlocked {result.unlocked} / {result.requested}[/green]")
    if result.skipped:
        console.print(f"[yellow]skipped: {', '.join(result.skipped)}[/yellow]")


@app.command()
def lock(
    appid: int = typer.Argument(...),
    ids: list[str] = typer.Argument(...),
    steam_root: Path | None = typer.Option(None, "--steam-root"),
) -> None:
    """Reverse an unlock (sets the bit back to locked)."""
    paths = _resolve_paths(steam_root)
    engine = AchievementEngine(paths, RuntimeConfig.load())
    result = engine.lock(appid, ids)
    console.print(f"[green]locked {result.unlocked} / {result.requested}[/green]")


@app.command()
def backup(
    appid: int = typer.Argument(...),
    steam_root: Path | None = typer.Option(None, "--steam-root"),
) -> None:
    """Snapshot the UserGameStats blobs for an appid."""
    paths = _resolve_paths(steam_root)
    engine = AchievementEngine(paths, RuntimeConfig.load())
    dest = engine.backup(appid)
    console.print(f"[green]backup -> {dest}[/green]")


@app.command()
def restore(
    appid: int = typer.Argument(...),
    steam_root: Path | None = typer.Option(None, "--steam-root"),
) -> None:
    """Restore the most recent backup for an appid."""
    paths = _resolve_paths(steam_root)
    engine = AchievementEngine(paths, RuntimeConfig.load())
    engine.restore(appid)
    console.print("[green]restored[/green]")


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        console.print("[yellow]interrupted[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()