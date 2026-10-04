#!/usr/bin/env python3
"""Install the exact Away3D fork required by the legacy Codename Flx3D API.

The repository's run.sh sets HAXELIB_PATH/HAXEPATH before calling this helper.
No registry release is accepted: the wrapper uses APIs present in the pinned
CodenameCrew fork revision only.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
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
    if library_path is None:
        return None
    git_entry = library_path / ".git"
    if not git_entry.exists():
        return None
    git = shutil.which("git")
    if git:
        result = run([git, "-C", str(library_path), "rev-parse", "HEAD"], check=False)
        revision = result.stdout.strip().lower()
        if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", revision):
            return revision
    return checkout_revision_from_metadata(library_path)


def checkout_revision_from_metadata(library_path: Path) -> str | None:
    """Read the checked-out commit from local Git metadata without Git installed.

    Haxelib keeps Git checkouts under its git/ directory. Read only HEAD and
    refs; never infer the pin from the package version, which is not unique to
    the CodenameCrew fork revision.
    """
    git_entry = library_path / ".git"
    if git_entry.is_dir():
        git_dir = git_entry.resolve()
    elif git_entry.is_file():
        try:
            pointer = git_entry.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        match = re.fullmatch(r"gitdir:\s*(.+)", pointer, flags=re.IGNORECASE)
        if not match:
            return None
        target = Path(match.group(1))
        if not target.is_absolute():
            target = library_path / target
        git_dir = target.resolve()
    else:
        return None

    try:
        head = (git_dir / "HEAD").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return None
    if re.fullmatch(r"[0-9a-fA-F]{40}", head):
        return head.lower()
    if not head.startswith("ref:"):
        return None
    ref = head[4:].strip()
    ref_parts = ref.split("/")
    if not ref.startswith("refs/") or any(part in ("", ".", "..") for part in ref_parts):
        return None

    metadata_roots = [git_dir]
    common_dir_file = git_dir / "commondir"
    if common_dir_file.is_file():
        try:
            common_dir = Path(common_dir_file.read_text(encoding="utf-8").strip())
            if not common_dir.is_absolute():
                common_dir = git_dir / common_dir
            metadata_roots.append(common_dir.resolve())
        except OSError:
            pass

    for metadata_root in metadata_roots:
        try:
            loose_ref = (metadata_root / ref).read_text(encoding="ascii").strip()
        except (OSError, UnicodeError):
            loose_ref = ""
        if re.fullmatch(r"[0-9a-fA-F]{40}", loose_ref):
            return loose_ref.lower()

        try:
            packed_refs = (metadata_root / "packed-refs").read_text(encoding="ascii")
        except (OSError, UnicodeError):
            continue
        for line in packed_refs.splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[1] == ref and re.fullmatch(r"[0-9a-fA-F]{40}", fields[0]):
                return fields[0].lower()
    return None


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

    if not shutil.which("git"):
        raise RuntimeError(
            "Git is required to install or re-pin Away3D because the existing "
            "checkout metadata does not prove the required revision. Add Git to "
            "PATH or rerun project setup so its pinned Git tool is available."
        )

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
