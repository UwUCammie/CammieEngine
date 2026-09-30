#!/usr/bin/env python3
"""Install the exact Away3D fork required by the legacy Codename Flx3D API.

The repository's run.sh sets HAXELIB_PATH/HAXEPATH before calling this helper.
No registry release is accepted: the wrapper uses APIs present in the pinned
CodenameCrew fork revision only.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


LIBRARY = "away3d"
REPOSITORY = "https://github.com/CodenameCrew/away3d.git"
REVISION = "ca30a80ca3c56f266fb3cd067fdeb43b0bb9784d"
EXPECTED_VERSION = "5.1.0"


def haxelib_executable() -> str:
    haxe_path = os.environ.get("HAXEPATH")
    if haxe_path:
        candidate = Path(haxe_path) / "haxelib"
        if candidate.is_file():
            return str(candidate)
    candidate = shutil.which("haxelib")
    if candidate:
        return candidate
    raise RuntimeError("haxelib is unavailable; run this through run.sh after toolchain setup")


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, check=check, capture_output=True)


def selected_library_path(haxelib: str) -> Path | None:
    result = run([haxelib, "path", LIBRARY], check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        candidate = Path(line.strip())
        if candidate.is_dir() and (candidate / "haxelib.json").is_file():
            return candidate.resolve()
    return None


def verify_haxelib_repository(haxelib: str) -> None:
    """Fail closed if haxelib would install outside run.sh's selected store."""
    expected = Path(os.environ["HAXELIB_PATH"]).expanduser().resolve()
    result = run([haxelib, "config"])
    configured = Path(result.stdout.strip()).expanduser().resolve()
    if configured != expected:
        raise RuntimeError(
            f"haxelib config points at {configured}, but HAXELIB_PATH selects {expected}"
        )


def checkout_revision(library_path: Path | None) -> str | None:
    if library_path is None or not (library_path / ".git").exists():
        return None
    result = run(["git", "-C", str(library_path), "rev-parse", "HEAD"], check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def package_version(library_path: Path | None) -> str | None:
    if library_path is None:
        return None
    try:
        import json

        return json.loads((library_path / "haxelib.json").read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError, AttributeError):
        return None


def ensure_pinned(haxelib: str) -> Path:
    current_path = selected_library_path(haxelib)
    if checkout_revision(current_path) == REVISION and package_version(current_path) == EXPECTED_VERSION:
        print(f">> away3d already pinned at {REVISION}")
        return current_path

    print(f">> installing pinned CodenameCrew/away3d revision {REVISION}")
    run([haxelib, "git", LIBRARY, REPOSITORY, REVISION, "--always"])
    run([haxelib, "set", LIBRARY, "git"])

    pinned_path = selected_library_path(haxelib)
    actual_revision = checkout_revision(pinned_path)
    actual_version = package_version(pinned_path)
    if actual_revision != REVISION or actual_version != EXPECTED_VERSION:
        raise RuntimeError(
            "away3d pin verification failed: "
            f"expected {REVISION} / {EXPECTED_VERSION}, found "
            f"{actual_revision!r} / {actual_version!r} at {pinned_path}"
        )
    return pinned_path


def main() -> int:
    if not os.environ.get("HAXELIB_PATH"):
        print("HAXELIB_PATH must point at the repository's pinned haxelib store", file=sys.stderr)
        return 2
    try:
        haxelib = haxelib_executable()
        verify_haxelib_repository(haxelib)
        ensure_pinned(haxelib)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"[away3d-setup] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
