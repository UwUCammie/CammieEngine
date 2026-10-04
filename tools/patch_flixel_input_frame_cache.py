#!/usr/bin/env python3
"""Key Flixel action input caching to update steps instead of millisecond ticks."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FLIXEL_DIR = ROOT / ".haxelib/flixel/6,1,2/flixel"

OLD_TICKS_FIELD = "\tpublic var ticks(default, null):Int = 0;\n"
NEW_TICKS_FIELD = OLD_TICKS_FIELD + """\t/**
	 * Monotonic count of input update steps. `ticks` can repeat within one
	 * millisecond when the native frame loop runs faster than its timer resolution.
	 */
	public var inputFrame(default, null):Int = 0; // dpui-input-frame-field
"""
INPUT_UPDATE_METHOD = "\tfunction updateInput():Void\n\t{\n"
INPUT_UPDATE_MARKER = "\t\tinputFrame++; // dpui-input-frame-increment\n"

OLD_ACTION_CACHE_FIELD = "\tvar _timestamp:Int = 0;\n"
NEW_ACTION_CACHE_FIELD = "\tvar _inputFrame:Int = -1; // dpui-input-frame-cache\n"
OLD_ACTION_GUARD = "\t\tif (_timestamp == FlxG.game.ticks)\n"
NEW_ACTION_GUARD = "\t\tif (_inputFrame == FlxG.game.inputFrame)\n"
OLD_ACTION_ASSIGNMENT = "\t\t_timestamp = FlxG.game.ticks;\n"
NEW_ACTION_ASSIGNMENT = "\t\t_inputFrame = FlxG.game.inputFrame;\n"


def _replace_once(source: str, old: str, new: str, label: str) -> str:
	count = source.count(old)
	if count != 1:
		raise ValueError(f"pinned Flixel {label} site was not unique (found {count})")
	return source.replace(old, new, 1)


def patch_game_source(source: str) -> str:
	"""Add a per-update serial to FlxGame and advance it before input polling."""
	field_marker = "dpui-input-frame-field"
	if field_marker in source or "dpui-input-frame-increment" in source:
		if (
			source.count(field_marker) != 1
			or source.count("dpui-input-frame-increment") != 1
			or NEW_TICKS_FIELD not in source
			or INPUT_UPDATE_MARKER not in source
		):
			raise ValueError("FlxGame has a partial or unexpected input-frame patch")
		return source

	patched = _replace_once(source, OLD_TICKS_FIELD, NEW_TICKS_FIELD, "FlxGame ticks field")
	patched = _replace_once(
		patched,
		INPUT_UPDATE_METHOD,
		INPUT_UPDATE_METHOD + INPUT_UPDATE_MARKER,
		"FlxGame.updateInput",
	)
	return patched


def patch_action_source(source: str) -> str:
	"""Memoize each action's result once per Flixel update step."""
	marker = "dpui-input-frame-cache"
	if marker in source:
		if (
			source.count(marker) != 1
			or NEW_ACTION_CACHE_FIELD not in source
			or source.count(NEW_ACTION_GUARD) != 1
			or source.count(NEW_ACTION_ASSIGNMENT) != 1
			or OLD_ACTION_GUARD in source
			or OLD_ACTION_ASSIGNMENT in source
		):
			raise ValueError("FlxAction has a partial or unexpected input-frame patch")
		return source

	patched = _replace_once(source, OLD_ACTION_CACHE_FIELD, NEW_ACTION_CACHE_FIELD, "FlxAction cache field")
	patched = _replace_once(patched, OLD_ACTION_GUARD, NEW_ACTION_GUARD, "FlxAction cache guard")
	patched = _replace_once(patched, OLD_ACTION_ASSIGNMENT, NEW_ACTION_ASSIGNMENT, "FlxAction cache assignment")
	return patched


def _read_text(path: Path) -> tuple[str, str]:
	raw = path.read_bytes()
	newline = "\r\n" if b"\r\n" in raw else "\n"
	return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n"), newline


def patch_files(flixel_dir: Path = DEFAULT_FLIXEL_DIR) -> bool:
	game_path = flixel_dir / "FlxGame.hx"
	action_path = flixel_dir / "input/actions/FlxAction.hx"
	game_original, game_newline = _read_text(game_path)
	action_original, action_newline = _read_text(action_path)
	game_patched = patch_game_source(game_original)
	action_patched = patch_action_source(action_original)
	changed = game_patched != game_original or action_patched != action_original
	if changed:
		game_path.write_bytes(game_patched.replace("\n", game_newline).encode("utf-8"))
		action_path.write_bytes(action_patched.replace("\n", action_newline).encode("utf-8"))
	return changed


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("flixel_dir", type=Path, nargs="?", default=DEFAULT_FLIXEL_DIR,
		help="Flixel source directory (default: pinned .haxelib Flixel 6.1.2)")
	args = parser.parse_args()
	try:
		changed = patch_files(args.flixel_dir)
	except (OSError, UnicodeError, ValueError) as error:
		print(f"!! Flixel input-frame cache patch failed: {error}")
		return 1
	print(
		">> patched pinned Flixel action cache to use update-frame serials"
		if changed else ">> pinned Flixel input-frame cache patch already present"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
