#!/usr/bin/env python3
"""Apply the narrow Flixel 6.1.2 hold-UV and camera compatibility patches in a haxelib checkout."""

from pathlib import Path
import re
import sys


MARKER = "// DisappointingPlus: FlxUVRect field order + hold UV stride fix"
IMPORT = "import ModchartHoldUVCompat;"
CALL = "return ModchartHoldUVCompat.getHoldUVT("
METHOD = re.compile(
    r"(?ms)^(\tinline static public function getHoldUVT\(arrow:FlxSprite, subs:Int\):Vector<Float> \{\n)"
    r".*?(\n\t\}\n\n\t/\*\*)"
)
BODY = """\t\tvar frameUV = arrow.frame.uv;
\t\t// DisappointingPlus: FlxUVRect field order + hold UV stride fix
\t\treturn ModchartHoldUVCompat.getHoldUVT(frameUV.left, frameUV.top, frameUV.right, frameUV.bottom,
\t\t\t-ModchartUtil.getFrameAngle(arrow), subs);"""


CAMERA_MARKER = "// DisappointingPlus: resolve explicit cameras before arrow-group fallback"
CAMERA_IMPORT = "import ModchartCameraCompat;"
CAMERA_METHOD = re.compile(
    r"(?ms)^(\tinline public static function resolveCameras\(playfield:modchart.engine.PlayField, item:FlxSprite\):Array<FlxCamera> \{\n)"
    r".*?(\n\t\}\n)"
)


def patch_cameras(source: str) -> str:
    if CAMERA_MARKER in source:
        if CAMERA_IMPORT not in source or "ModchartCameraCompat.resolve(item, playfield" not in source:
            raise RuntimeError("ModchartUtil has a partial camera compatibility patch")
        return source
    match = CAMERA_METHOD.search(source)
    if match is None:
        raise RuntimeError("expected ModchartUtil.resolveCameras implementation was not found")
    body = "\t\t" + CAMERA_MARKER + "\n\t\treturn ModchartCameraCompat.resolve(item, playfield, Adapter.instance.getArrowCamera);"
    source = source[:match.start()] + match.group(1) + body + match.group(2) + source[match.end():]
    return source.replace("import haxe.ds.Vector;", "import haxe.ds.Vector;\n" + CAMERA_IMPORT, 1)


def patch_text(source: str) -> str:
    source = patch_cameras(source)
    if MARKER in source:
        if CALL not in source or IMPORT not in source:
            raise RuntimeError("ModchartUtil has a partial or unexpected hold-UV patch")
        return source

    match = METHOD.search(source)
    if match is None:
        raise RuntimeError("expected ModchartUtil.getHoldUVT implementation was not found")
    source = source[:match.start()] + match.group(1) + BODY + match.group(2) + source[match.end():]

    vector_import = "import haxe.ds.Vector;"
    if vector_import not in source:
        raise RuntimeError("expected ModchartUtil Vector import was not found")
    if IMPORT not in source:
        source = source.replace(vector_import, vector_import + "\n" + IMPORT, 1)
    return source


def patch_file(path: Path) -> bool:
    raw = path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    source = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    patched = patch_text(source)
    if patched == source:
        return False
    path.write_bytes(patched.replace("\n", newline).encode("utf-8"))
    return True


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_funkin_modchart_uv.py ModchartUtil.hx", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"FunkinModchart UV patch target not found: {path}", file=sys.stderr)
        return 2
    try:
        changed = patch_file(path)
    except RuntimeError as error:
        print(f"FunkinModchart UV patch failed: {error}", file=sys.stderr)
        return 1
    if changed:
        print(">> patched FunkinModchart hold UVs and camera resolution for Flixel 6.1.2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
