#!/usr/bin/env python3
"""Stop Flixel dispatching animation-finished signals on a sprite its callback destroyed."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FLIXEL_DIR = ROOT / ".haxelib/flixel/6,1,2/flixel"
MARKER = "cammie-finish-destroy-guard"

# Imported scripts destroy a one-shot sprite from its own finishCallback. That
# also destroys onFinish, and dispatching a destroyed signal is a native crash.
OLD = """\t\tif (finishCallback != null)
\t\t{
\t\t\tfinishCallback(name);
\t\t}
\t\t
\t\tonFinish.dispatch(name);"""
NEW = """\t\tif (finishCallback != null)
\t\t{
\t\t\tfinishCallback(name);
\t\t}
\t\t
\t\t// local patch (Cammie Engine): """ + MARKER + """
\t\t// a callback may destroy its own sprite, which also destroys this signal
\t\tif (_sprite == null)
\t\t\treturn;
\t\t
\t\tonFinish.dispatch(name);"""


def patch_source(source: str) -> str:
	newline = "\r\n" if "\r\n" in source else "\n"
	old, new = OLD.replace("\n", newline), NEW.replace("\n", newline)
	if MARKER in source:
		if source.count(new) != 1:
			raise ValueError("FlxAnimationController has a partial or unexpected finish guard")
		return source
	if source.count(old) != 1:
		raise ValueError("pinned Flixel fireFinishCallback site was not unique")
	return source.replace(old, new, 1)


def patch_files(flixel_dir: Path) -> bool:
	path = flixel_dir / "animation/FlxAnimationController.hx"
	with path.open(encoding="utf-8", newline="") as handle:
		source = handle.read()
	patched = patch_source(source)
	if patched == source:
		return False
	with path.open("w", encoding="utf-8", newline="") as handle:
		handle.write(patched)
	return True


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("flixel_dir", type=Path, nargs="?", default=DEFAULT_FLIXEL_DIR,
		help="Flixel source directory (default: pinned .haxelib Flixel 6.1.2)")
	args = parser.parse_args()
	try:
		changed = patch_files(args.flixel_dir)
	except (OSError, UnicodeError, ValueError) as error:
		print(f"!! Flixel animation finish guard patch failed: {error}")
		return 1
	print(
		">> patched pinned Flixel animation finish guard"
		if changed else ">> pinned Flixel animation finish guard already present"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
