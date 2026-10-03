"""Invalidate OpenFL's cached blend mode after cached-child rendering."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENFL_SOURCE = ROOT / ".haxelib/openfl/9,5,2/src/openfl/display/DisplayObjectRenderer.hx"
SOURCE_SHA256 = "79e2b7e0e10bdb20163d4dca82b8619748f50f19e6f5f48362db493adc39dbc0"
PATCHED_SHA256 = "fa55249eeb30bc6ddfeda0e38fcb108dd2ac0dd1ce7f9032eb9446f81205ddab"

OLD_RESTORE = (
    b"\t\t\t\t\tparentRenderer.__blendMode = NORMAL;\n"
    b"\t\t\t\t\tparentRenderer.__setBlendMode(cacheBlendMode);\n"
)
NEW_RESTORE = (
    b"\t\t\t\t\t// Cached child/filter rendering shares Context3D and can change GL state.\n"
    b"\t\t\t\t\tparentRenderer.__blendMode = null;\n"
    b"\t\t\t\t\tparentRenderer.__setBlendMode(cacheBlendMode);\n"
)


def sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def patch_source(source: bytes) -> bytes:
    """Patch only the pinned OpenFL 9.5.2 source and accept exact reruns."""
    actual_hash = sha256(source)
    if PATCHED_SHA256 and actual_hash == PATCHED_SHA256:
        return source
    if actual_hash != SOURCE_SHA256:
        raise ValueError(
            "OpenFL DisplayObjectRenderer.hx differs from pinned 9.5.2 source; refusing patch "
            f"(sha256 {actual_hash})"
        )

    count = source.count(OLD_RESTORE)
    if count != 1:
        raise ValueError(f"pinned OpenFL blend-restore site was not unique (found {count})")
    patched = source.replace(OLD_RESTORE, NEW_RESTORE, 1)
    if PATCHED_SHA256 and sha256(patched) != PATCHED_SHA256:
        raise ValueError(f"patched OpenFL DisplayObjectRenderer.hx hash did not match ({sha256(patched)})")
    return patched


def patch_file(path: Path = OPENFL_SOURCE) -> bool:
    original = path.read_bytes()
    patched = patch_source(original)
    if patched == original:
        return False
    path.write_bytes(patched)
    return True


def main() -> int:
    try:
        changed = patch_file()
    except (OSError, ValueError) as error:
        print(f"!! OpenFL blend-state restore patch failed: {error}")
        return 1
    if changed:
        print(">> patched OpenFL cached-child blend-state restore")
    else:
        print(">> OpenFL cached-child blend-state restore already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
