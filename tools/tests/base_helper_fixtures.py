"""Real base-game helpers for fixtures that compile extracted PlayState methods.

Compatibility methods are thin calls into shared helpers, so a fixture that
lifts one of them out of PlayState needs the helper it calls. These functions
hand the fixture the real helper source instead of a stand-in, which keeps the
behaviour under test the behaviour that ships.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def extract_block(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated block: {marker}")


def cool_util_class(*names: str, extra: str = "") -> str:
    """A CoolUtil holding only the named real static functions.

    The fixture supplies whatever those functions touch (FlxColor, FlxEase).
    `extra` is raw Haxe for members a fixture has to stand in for.
    """
    source = (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8")
    methods = "\n".join(
        extract_block(source, f"public static function {name}(") for name in names
    )
    return "\nclass CoolUtil {\n" + extra + "\n" + methods + "\n}\n"


COLOR_HELPERS = ("colorFromStringOrNull", "colorFromString")


def cool_util_colors() -> str:
    return cool_util_class(*COLOR_HELPERS)


def copy_sources(folder, *names: str) -> None:
    """Copy dependency-free source files next to a fixture."""
    for name in names:
        shutil.copyfile(ROOT / "source" / name, Path(str(folder)) / name)


def play_state_method(marker: str, public: bool = False) -> str:
    source = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")
    method = extract_block(source, marker)
    if public and not method.startswith("public "):
        method = "public " + method
    return method
