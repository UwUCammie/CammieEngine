"""Pin the Lime uncapped-loop patch to its unique, idempotent source sites."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import patch_lime_uncapped_frame_loop as patcher  # noqa: E402


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def normalized_digest(contents):
    return digest(contents.replace(b"\r\n", b"\n"))


def synthetic_sdl_source(old=True):
    names = (
        "OLD_RATE",
        "OLD_EVENT_SCHEDULE",
        "OLD_UPDATE_DECL",
        "OLD_WAIT_BLOCK",
        "OLD_POLL_LOOP",
        "OLD_FRAME_PUMP",
    ) if old else (
        "NEW_RATE",
        "NEW_EVENT_SCHEDULE",
        "NEW_UPDATE_DECL",
        "NEW_WAIT_BLOCK",
        "NEW_POLL_LOOP",
        "NEW_FRAME_PUMP",
    )
    return b"".join(getattr(patcher, name) for name in names)


class LimeUncappedFrameLoopPatchTest(unittest.TestCase):
    def test_sdl_patch_is_exact_and_idempotent_for_lf_and_crlf(self):
        for newline in (b"\n", b"\r\n"):
            with self.subTest(newline=newline):
                source = synthetic_sdl_source().replace(b"\n", newline)
                expected = synthetic_sdl_source(old=False).replace(b"\n", newline)
                with mock.patch.object(patcher, "SOURCE_SHA256", normalized_digest(source)), \
                     mock.patch.object(patcher, "PATCHED_SHA256", normalized_digest(expected)):
                    patched = patcher.patch_source(source)
                    self.assertEqual(patched, expected)
                    self.assertEqual(patcher.patch_source(patched), patched)

    def test_font_patch_adds_only_cstdlib_and_is_idempotent(self):
        source = (
            b"#include <text/Font.h>\r\n"
            b"#include <algorithm>\r\n"
            b"#include <list>\r\n"
            b"#include <vector>\r\n"
        )
        expected = source.replace(
            b"#include <algorithm>\r\n#include <list>",
            b"#include <algorithm>\r\n#include <cstdlib>\r\n#include <list>",
            1,
        )
        with mock.patch.object(patcher, "FONT_SOURCE_SHA256", normalized_digest(source)), \
             mock.patch.object(patcher, "FONT_PATCHED_SHA256", normalized_digest(expected)):
            patched = patcher.patch_font_source(source)
            self.assertEqual(patched, expected)
            self.assertEqual(patcher.patch_font_source(patched), patched)

    def test_patch_file_refuses_unknown_source_without_partial_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            lime_root = Path(directory)
            sdl_path = lime_root / "project/src/backend/sdl/SDLApplication.cpp"
            font_path = lime_root / "project/src/text/Font.cpp"
            sdl_path.parent.mkdir(parents=True)
            font_path.parent.mkdir(parents=True)
            sdl_path.write_bytes(synthetic_sdl_source())
            font_original = b"different Font.cpp source\n"
            font_path.write_bytes(font_original)

            with mock.patch.object(patcher, "SOURCE_SHA256", digest(sdl_path.read_bytes())), \
                 mock.patch.object(patcher, "PATCHED_SHA256", digest(synthetic_sdl_source(old=False))):
                with self.assertRaisesRegex(ValueError, "Font.cpp differs"):
                    patcher.patch_file(lime_root)

            self.assertEqual(sdl_path.read_bytes(), synthetic_sdl_source())
            self.assertEqual(font_path.read_bytes(), font_original)


if __name__ == "__main__":
    unittest.main()
