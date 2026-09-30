"""Reuse the pinned OpenFL Context3D bitmap-readback staging buffer."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENFL_SOURCE = ROOT / ".haxelib/openfl/9,5,2/src/openfl/display3D/Context3D.hx"
SOURCE_SHA256 = "3c831d9c1e06afc4b1d682a1474db2372fcf2aa0fd1ef53ff6c461c1ca494a81"
PATCHED_SHA256 = "6ab02ac34fb4ca524b41c4148bc3c1588dfe924e6781626488a1b1b4fc814819"

OLD_FIELDS = (
    b"\t@:noCompletion private var __positionScale:Float32Array; // TODO: Better approach?\n"
)
NEW_FIELDS = (
    b"\t@:noCompletion private var __positionScale:Float32Array; // TODO: Better approach?\n"
    b"\t#if lime\n"
    b"\t@:noCompletion private var __readbackPixels:UInt8Array;\n"
    b"\t@:noCompletion private var __readbackImage:Image;\n"
    b"\t@:noCompletion private var __readbackWidth:Int = 0;\n"
    b"\t@:noCompletion private var __readbackHeight:Int = 0;\n"
    b"\t#end\n"
)

OLD_SNAPSHOT = (
    b"\t\t\tvar data = new UInt8Array(backBufferWidth * backBufferHeight * 4);\n"
    b"\t\t\tgl.readPixels(0, 0, backBufferWidth, backBufferHeight, __backBufferTexture.__format, gl.UNSIGNED_BYTE, data);\n"
    b"\n"
    b"\t\t\tvar image = new Image(new ImageBuffer(data, backBufferWidth, backBufferHeight, 32, BGRA32));\n"
    b"\t\t\tdestination.image.copyPixels(image, sourceRect, destVector);\n"
)
NEW_SNAPSHOT = (
    b"\t\t\tif (__readbackPixels == null || __readbackWidth != backBufferWidth || __readbackHeight != backBufferHeight)\n"
    b"\t\t\t{\n"
    b"\t\t\t\t// Drop the previous size before allocating its replacement so the old\n"
    b"\t\t\t\t// full-frame staging storage is no longer retained by this context.\n"
    b"\t\t\t\t__readbackImage = null;\n"
    b"\t\t\t\t__readbackPixels = null;\n"
    b"\t\t\t\t__readbackWidth = backBufferWidth;\n"
    b"\t\t\t\t__readbackHeight = backBufferHeight;\n"
    b"\t\t\t\t__readbackPixels = new UInt8Array(backBufferWidth * backBufferHeight * 4);\n"
    b"\t\t\t\t__readbackImage = new Image(new ImageBuffer(__readbackPixels, backBufferWidth, backBufferHeight, 32, BGRA32));\n"
    b"\t\t\t}\n"
    b"\n"
    b"\t\t\tgl.readPixels(0, 0, backBufferWidth, backBufferHeight, __backBufferTexture.__format, gl.UNSIGNED_BYTE, __readbackPixels);\n"
    b"\t\t\tdestination.image.copyPixels(__readbackImage, sourceRect, destVector);\n"
)

OLD_DISPOSE = b'\t\tdriverInfo += " (Disposed)";\n'
NEW_DISPOSE = (
    b'\t\tdriverInfo += " (Disposed)";\n'
    b"\t\t#if lime\n"
    b"\t\t__readbackImage = null;\n"
    b"\t\t__readbackPixels = null;\n"
    b"\t\t__readbackWidth = 0;\n"
    b"\t\t__readbackHeight = 0;\n"
    b"\t\t#end\n"
)


def sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _replace_once(source: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"pinned OpenFL {label} site was not unique (found {count})")
    return source.replace(old, new, 1)


def patch_source(source: bytes) -> bytes:
    """Patch exactly OpenFL 9.5.2; accept only our exact output on reruns."""
    actual_hash = sha256(source)
    if actual_hash == PATCHED_SHA256:
        return source
    if actual_hash != SOURCE_SHA256:
        raise ValueError(
            "OpenFL Context3D.hx differs from the pinned 9.5.2 source; refusing patch "
            f"(sha256 {actual_hash})"
        )

    patched = _replace_once(source, OLD_FIELDS, NEW_FIELDS, "context fields")
    patched = _replace_once(patched, OLD_SNAPSHOT, NEW_SNAPSHOT, "snapshot")
    patched = _replace_once(patched, OLD_DISPOSE, NEW_DISPOSE, "dispose")
    patched_hash = sha256(patched)
    if patched_hash != PATCHED_SHA256:
        raise ValueError(
            "OpenFL Context3D readback patch output did not match its pinned hash "
            f"(sha256 {patched_hash})"
        )
    return patched


def patch_file(path: Path = OPENFL_SOURCE) -> bool:
    """Patch one OpenFL source file; return whether bytes were changed."""
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
        print(f"!! OpenFL Context3D readback-buffer patch failed: {error}")
        return 1
    if changed:
        print(">> patched OpenFL Context3D readback buffer reuse")
    else:
        print(">> OpenFL Context3D readback buffer reuse already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
