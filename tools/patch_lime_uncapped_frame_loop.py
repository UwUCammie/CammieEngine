"""Enable the zero-rate uncapped loop in pinned Lime 8.3.2's SDL backend."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "ee3df9731971ce5c3e98988da878a4280484100707d0bdce1d9d39cb65174cb0"
PATCHED_SHA256 = "67bab1126d0066d6d87c0535d5c89fc69dcf0eedd03bc407a213270d46ed9f09"

# The pinned Lime 8.3.2 source omits the standard header that declares
# std::wcstombs. LLVM-MinGW's libc headers do not expose it transitively.
FONT_SOURCE_SHA256 = "1517d8457c0d93747da8c3516d7b6de7ffb9e16c837a9d7d257acc0119716ce2"
FONT_PATCHED_SHA256 = "c454c3351eae242649be1eab36e388cad657ee60600cc472543c17089895a684"
PATCHED_PATHS = (
    "project/src/backend/sdl/SDLApplication.cpp",
    "project/src/text/Font.cpp",
)

OLD_RATE = (
    b"\t\t} else {\n"
    b"\n"
    b"\t\t\tframePeriod = 1000.0;\n"
    b"\n"
    b"\t\t}\n"
)
NEW_RATE = (
    b"\t\t} else {\n"
    b"\n"
    b"\t\t\t// Flixel uses zero to request an uncapped native frame loop.\n"
    b"\t\t\tframePeriod = 0.0;\n"
    b"\n"
    b"\t\t}\n"
)

OLD_EVENT_SCHEDULE = (
    b"\t\t\t\t\tnextUpdate += NextFrameStep(framePeriod);\n"
    b"\n"
    b"\t\t\t\t\twhile (nextUpdate <= currentUpdate) {\n"
    b"\t\t\t\t\t\tnextUpdate += NextFrameStep(framePeriod);\n"
    b"\t\t\t\t\t}\n"
)
NEW_EVENT_SCHEDULE = (
    b"\t\t\t\t\tif (framePeriod <= 0.0) {\n"
    b"\t\t\t\t\t\tnextUpdate = currentUpdate;\n"
    b"\t\t\t\t\t} else {\n"
    b"\t\t\t\t\t\tnextUpdate += NextFrameStep(framePeriod);\n"
    b"\n"
    b"\t\t\t\t\t\twhile (nextUpdate <= currentUpdate) {\n"
    b"\t\t\t\t\t\t\tnextUpdate += NextFrameStep(framePeriod);\n"
    b"\t\t\t\t\t\t}\n"
    b"\t\t\t\t\t}\n"
)

OLD_UPDATE_DECL = (
    b"\t\tSDL_Event event;\n"
    b"\t\tevent.type = -1;\n"
)
NEW_UPDATE_DECL = (
    b"\t\tSDL_Event event;\n"
    b"\t\tevent.type = -1;\n"
    b"\t\tbool frameDispatched = false;\n"
)

OLD_WAIT_BLOCK = (
    b"\t\tif (active && (firstTime || WaitEvent (&event))) {\n"
    b"\n"
    b"\t\t\tfirstTime = false;\n"
    b"\n"
    b"\t\t\tHandleEvent (&event);\n"
    b"\t\t\tevent.type = -1;\n"
)
NEW_WAIT_BLOCK = (
    b"\t\tif (active && (firstTime || (framePeriod <= 0.0 && !inBackground) || WaitEvent (&event))) {\n"
    b"\n"
    b"\t\t\tfirstTime = false;\n"
    b"\n"
    b"\t\t\tif (event.type == SDL_USEREVENT) frameDispatched = true;\n"
    b"\t\t\tHandleEvent (&event);\n"
    b"\t\t\tevent.type = -1;\n"
)

OLD_POLL_LOOP = (
    b"\t\t\twhile (SDL_PollEvent (&event)) {\n"
    b"\n"
    b"\t\t\t\tHandleEvent (&event);\n"
    b"\t\t\t\tevent.type = -1;\n"
)
NEW_POLL_LOOP = (
    b"\t\t\twhile (SDL_PollEvent (&event)) {\n"
    b"\n"
    b"\t\t\t\tif (framePeriod > 0.0 || event.type != SDL_USEREVENT) {\n"
    b"\t\t\t\t\tif (event.type == SDL_USEREVENT) frameDispatched = true;\n"
    b"\t\t\t\t\tHandleEvent (&event);\n"
    b"\t\t\t\t}\n"
    b"\t\t\t\tevent.type = -1;\n"
)

OLD_FRAME_PUMP = (
    b"\t\t#if defined (IPHONE) || defined (EMSCRIPTEN)\n"
    b"\n"
    b"\t\t\tif (currentUpdate >= nextUpdate) {\n"
    b"\n"
    b"\t\t\t\tevent.type = SDL_USEREVENT;\n"
    b"\t\t\t\tHandleEvent (&event);\n"
    b"\t\t\t\tevent.type = -1;\n"
    b"\n"
    b"\t\t\t}\n"
    b"\n"
    b"\t\t#else\n"
    b"\n"
    b"\t\t\tif (currentUpdate >= nextUpdate) {\n"
    b"\n"
    b"\t\t\t\tif (timerActive) SDL_RemoveTimer (timerID);\n"
    b"\t\t\t\tOnTimer (0, 0);\n"
    b"\n"
    b"\t\t\t} else if (!timerActive) {\n"
    b"\n"
    b"\t\t\t\ttimerActive = true;\n"
    b"\t\t\t\ttimerID = SDL_AddTimer (nextUpdate - currentUpdate, OnTimer, 0);\n"
    b"\n"
    b"\t\t\t}\n"
    b"\n"
    b"\t\t}\n"
    b"\n"
    b"\t\t#endif\n"
)
NEW_FRAME_PUMP = (
    b"\t\t#if defined (IPHONE) || defined (EMSCRIPTEN)\n"
    b"\n"
    b"\t\t\tif (framePeriod <= 0.0) {\n"
    b"\t\t\t\tif (!inBackground && !frameDispatched) {\n"
    b"\t\t\t\t\tevent.type = SDL_USEREVENT;\n"
    b"\t\t\t\t\tHandleEvent (&event);\n"
    b"\t\t\t\t\tevent.type = -1;\n"
    b"\t\t\t\t}\n"
    b"\t\t\t} else if (currentUpdate >= nextUpdate) {\n"
    b"\n"
    b"\t\t\t\tevent.type = SDL_USEREVENT;\n"
    b"\t\t\t\tHandleEvent (&event);\n"
    b"\t\t\t\tevent.type = -1;\n"
    b"\n"
    b"\t\t\t}\n"
    b"\n"
    b"\t\t#else\n"
    b"\n"
    b"\t\t\tif (framePeriod <= 0.0) {\n"
    b"\t\t\t\tif (!inBackground && !frameDispatched) {\n"
    b"\t\t\t\t\tevent.type = SDL_USEREVENT;\n"
    b"\t\t\t\t\tHandleEvent (&event);\n"
    b"\t\t\t\t\tevent.type = -1;\n"
    b"\t\t\t\t}\n"
    b"\t\t\t} else if (currentUpdate >= nextUpdate) {\n"
    b"\n"
    b"\t\t\t\tif (timerActive) SDL_RemoveTimer (timerID);\n"
    b"\t\t\t\tOnTimer (0, 0);\n"
    b"\n"
    b"\t\t\t} else if (!timerActive) {\n"
    b"\n"
    b"\t\t\t\ttimerActive = true;\n"
    b"\t\t\t\ttimerID = SDL_AddTimer (nextUpdate - currentUpdate, OnTimer, 0);\n"
    b"\n"
    b"\t\t\t}\n"
    b"\n"
    b"\t\t}\n"
    b"\t\t#endif\n"
)

OLD_FONT_HEADERS = (
    b"#include <algorithm>\n"
    b"#include <list>\n"
    b"#include <vector>\n"
)
NEW_FONT_HEADERS = (
    b"#include <algorithm>\n"
    b"#include <cstdlib>\n"
    b"#include <list>\n"
    b"#include <vector>\n"
)


def _sha256(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _normalized_sha256(source: bytes) -> str:
    return _sha256(source.replace(b"\r\n", b"\n"))


def _replace_once(source: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = source.count(old)
    if count != 1:
        raise ValueError(f"pinned Lime {label} site was not unique (found {count})")
    return source.replace(old, new, 1)


def patch_source(source: bytes) -> bytes:
    """Patch only the exact upstream SDLApplication.cpp from Lime 8.3.2."""
    actual_hash = _normalized_sha256(source)
    if actual_hash == PATCHED_SHA256:
        return source
    if actual_hash != SOURCE_SHA256:
        raise ValueError(
            "Lime SDLApplication.cpp differs from pinned 8.3.2; refusing patch "
            f"(sha256 {actual_hash})"
        )

    normalized = source.replace(b"\r\n", b"\n")
    patched = _replace_once(normalized, OLD_RATE, NEW_RATE, "frame-rate")
    patched = _replace_once(patched, OLD_EVENT_SCHEDULE, NEW_EVENT_SCHEDULE, "event schedule")
    patched = _replace_once(patched, OLD_UPDATE_DECL, NEW_UPDATE_DECL, "update declaration")
    patched = _replace_once(patched, OLD_WAIT_BLOCK, NEW_WAIT_BLOCK, "wait guard")
    patched = _replace_once(patched, OLD_POLL_LOOP, NEW_POLL_LOOP, "poll loop")
    patched = _replace_once(patched, OLD_FRAME_PUMP, NEW_FRAME_PUMP, "frame pump")
    if _normalized_sha256(patched) != PATCHED_SHA256:
        raise ValueError(
            "Lime uncapped frame-loop patch output did not match its pinned hash "
            f"(sha256 {_normalized_sha256(patched)})"
        )
    if b"\r\n" in source:
        patched = patched.replace(b"\n", b"\r\n")
    return patched


def patch_font_source(source: bytes) -> bytes:
    """Add the one portable C standard header missing from pinned Font.cpp."""
    actual_hash = _normalized_sha256(source)
    if actual_hash == FONT_PATCHED_SHA256:
        return source
    if actual_hash != FONT_SOURCE_SHA256:
        raise ValueError(
            "Lime Font.cpp differs from pinned 8.3.2; refusing patch "
            f"(sha256 {actual_hash})"
        )

    normalized = source.replace(b"\r\n", b"\n")
    patched = _replace_once(normalized, OLD_FONT_HEADERS, NEW_FONT_HEADERS, "Font.cpp headers")
    if _normalized_sha256(patched) != FONT_PATCHED_SHA256:
        raise ValueError(
            "Lime MinGW portability patch output did not match its pinned hash "
            f"(sha256 {_normalized_sha256(patched)})"
        )
    if b"\r\n" in source:
        patched = patched.replace(b"\n", b"\r\n")
    return patched


def patch_file(lime_root: Path) -> bool:
    path = lime_root / "project/src/backend/sdl/SDLApplication.cpp"
    source = path.read_bytes()
    patched = patch_source(source)
    font_path = lime_root / "project/src/text/Font.cpp"
    font_source = font_path.read_bytes()
    font_patched = patch_font_source(font_source)

    changed = patched != source or font_patched != font_source
    if changed:
        path.write_bytes(patched)
        font_path.write_bytes(font_patched)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lime_root", type=Path, help="root of an exact Lime 8.3.2 checkout")
    args = parser.parse_args()
    try:
        changed = patch_file(args.lime_root)
    except (OSError, ValueError) as error:
        print(f"!! Lime uncapped frame-loop patch failed: {error}")
        return 1
    print(
        ">> patched pinned Lime for uncapped frames and LLVM-MinGW headers"
        if changed else ">> pinned Lime uncapped and LLVM-MinGW patches already present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
