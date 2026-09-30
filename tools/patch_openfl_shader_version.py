"""Keep authored GLSL #version directives ahead of OpenFL's precision prefix."""

from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPENFL_SOURCE = ROOT / ".haxelib/openfl/9,5,2/src/openfl/display/Shader.hx"
SOURCE_SHA256 = "b512cc2473067f79d4789045c12ff1bc18ebc1e0a0ebc0125a1cf800cd4d26e4"
PATCHED_SHA256 = "3f2d46a583b223cbb48a292f86be1b6f0446cd2100e7f8a58cb329c7a0d50064"

OLD_SOURCES = (
    b"\t\t\tvar vertex = prefix + glVertexSource;\n"
    b"\t\t\tvar fragment = prefix + glFragmentSource;\n"
)
NEW_SOURCES = (
    b"\t\t\tvar vertex = __withGLSLVersion(glVertexSource, prefix);\n"
    b"\t\t\tvar fragment = __withGLSLVersion(glFragmentSource, prefix);\n"
)

OLD_CREATE_SHADER = b"\t@:noCompletion private function __createGLShader(source:String, type:Int):GLShader\n"
NEW_CREATE_SHADER = b'''\t// DisappointingPlus local patch (openfl-glsl-version): GLSL requires
	// #version to appear before the precision prefix OpenFL prepends here.
	@:noCompletion private function __withGLSLVersion(source:String, prefix:String):String
	{
		if (source == null) return prefix;
		var lines = source.split("\\n");
		var versionLine = -1;
		var inBlockComment = false;
		var versionPattern = ~/^#version[ \\t]+[0-9]+/;
		for (i in 0...lines.length)
		{
			var candidate = StringTools.trim(lines[i]);
			if (inBlockComment)
			{
				var close = candidate.indexOf("*/");
				if (close < 0) continue;
				candidate = StringTools.trim(candidate.substr(close + 2));
				inBlockComment = false;
			}
			while (StringTools.startsWith(candidate, "/*"))
			{
				var close = candidate.indexOf("*/", 2);
				if (close < 0)
				{
					inBlockComment = true;
					candidate = "";
					break;
				}
				candidate = StringTools.trim(candidate.substr(close + 2));
			}
			if (candidate == "" || StringTools.startsWith(candidate, "//")) continue;
			if (versionPattern.match(candidate)) versionLine = i;
			break;
		}
		if (versionLine < 0) return prefix + source;
		var directive = StringTools.trim(lines[versionLine]);
		lines.splice(versionLine, 1);
		return directive + "\\n" + prefix + lines.join("\\n");
	}

'''+OLD_CREATE_SHADER


def sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def replace_once(source: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"pinned OpenFL {label} site was not unique (found {count})")
    return source.replace(old, new, 1)


def patch_source(source: bytes) -> bytes:
    actual_hash = sha256(source)
    if PATCHED_SHA256 and actual_hash == PATCHED_SHA256:
        return source
    if actual_hash != SOURCE_SHA256:
        raise ValueError(
            "OpenFL Shader.hx differs from pinned 9.5.2 source; refusing patch "
            f"(sha256 {actual_hash})"
        )

    patched = replace_once(source, OLD_SOURCES, NEW_SOURCES, "shader source prefixes")
    patched = replace_once(patched, OLD_CREATE_SHADER, NEW_CREATE_SHADER, "GLSL source helper")
    if PATCHED_SHA256 and sha256(patched) != PATCHED_SHA256:
        raise ValueError(f"patched OpenFL Shader.hx hash did not match ({sha256(patched)})")
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
        print(f"!! OpenFL GLSL version patch failed: {error}")
        return 1
    if changed:
        print(">> patched OpenFL GLSL version directive ordering")
    else:
        print(">> OpenFL GLSL version directive ordering already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
