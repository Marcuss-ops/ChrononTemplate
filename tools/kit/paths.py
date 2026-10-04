"""Workspace and Chronon3D CLI discovery, shared by every suite script.

Every showcase script used to hardcode BASE_DIR and one CLI build directory;
when the active build moved (fast-dev vs release vs release-validation) the
script silently kept pointing at a stale binary. The workspace is discovered
once here, and the CLI resolves through an explicit candidate chain with an
environment override.

Overrides:
    VELOX_WORKSPACE  repo root (default: discovered by walking up from here)
    CHRONON_CLI      chronon3d_cli executable (default: candidate chain)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_MARKERS = ("Chronon3d", "ChrononTemplate")

# Priority: fast dev lane first (what the module README and dev presets use),
# then the release lanes, then ad-hoc .tmp builds.
CLI_CANDIDATES = (
    "Chronon3d/build/chronon/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    "Chronon3d/build/chronon/linux-video-release/apps/chronon3d_cli/chronon3d_cli",
    "Chronon3d/build/chronon/linux-release-validation/apps/chronon3d_cli/chronon3d_cli",
    "Chronon3d/build/chronon/linux-fast-dev/apps/chronon3d_cli/chronon3d_cli",
    "Chronon3d/.tmp/chronon-builds/linux-video-fast-dev/apps/chronon3d_cli/chronon3d_cli",
)


@dataclass(frozen=True)
class Workspace:
    """The one discovery answer for a suite script: everything is derived."""

    root: Path
    cli: Path | None
    assets_root: Path
    template_dir: Path
    token_path: Path
    creds_path: Path

    def first_existing_cli(self, override: Path | str | None = None) -> Path | None:
        if override:
            cli = Path(override).expanduser()
            return cli if cli.is_file() else None
        return self.cli

    def require_cli(self, override: Path | str | None = None) -> Path:
        """CLI path or SystemExit with the candidate list that was searched."""
        cli = self.first_existing_cli(override)
        if cli is None:
            searched = ", ".join(CLI_CANDIDATES)
            raise SystemExit(
                "Chronon3D CLI non trovato. Passa --cli, imposta CHRONON_CLI, "
                f"o costruisci una di queste destinazioni:\n  {searched}"
            )
        return cli


def _find_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if all((candidate / marker).is_dir() for marker in _MARKERS):
            return candidate
    return None


def find_workspace(start: Path | str | None = None) -> Workspace:
    """Discover the repo root from `start` (default: this file's location)."""
    env_root = os.environ.get("VELOX_WORKSPACE")
    if env_root:
        root = Path(env_root).expanduser().resolve()
        missing = [m for m in _MARKERS if not (root / m).is_dir()]
        if missing:
            raise SystemExit(
                f"VELOX_WORKSPACE={root} non contiene {', '.join(missing)}"
            )
    else:
        origin = Path(start) if start else Path(__file__).resolve()
        root = _find_root(origin.resolve())
        if root is None:
            raise SystemExit(
                "Root della repo non trovato salendo da "
                f"{origin}: serve un albero con {', '.join(_MARKERS)} "
                "(o imposta VELOX_WORKSPACE)"
            )

    cli: Path | None = None
    cli_env = os.environ.get("CHRONON_CLI")
    if cli_env:
        resolved = Path(cli_env).expanduser()
        cli = resolved if resolved.is_file() else None
    else:
        for candidate in CLI_CANDIDATES:
            resolved = root / candidate
            if resolved.is_file():
                cli = resolved
                break

    return Workspace(
        root=root,
        cli=cli,
        assets_root=root / "Chronon3d",
        template_dir=root / "ChrononTemplate",
        token_path=root / "refactored" / "token.json",
        creds_path=root / "refactored" / "credentials.json",
    )
