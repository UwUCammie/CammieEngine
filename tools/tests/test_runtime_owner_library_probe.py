"""Generated native fixture contract for receipt-bound file-backed libraries."""

from __future__ import annotations

import json
import hashlib
from io import BytesIO
from pathlib import Path
from haxe_test_support import FixturePath as Path
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
import xml.etree.ElementTree as ET
import zlib


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "tools" / "prepare_owner_library_fixture.py"
RUNNER = ROOT / "tools" / "run_owner_library_native.ps1"
PROBE = ROOT / "source" / "RuntimeOwnerLibraryProbe.hx"
HARNESS = ROOT / "source" / "RuntimeSmokeHarness.hx"


def decode_rgba_png(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("fixture image is not PNG")
    offset = 8
    chunks = []
    width = height = None
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length:offset + 12 + length])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise AssertionError("fixture PNG chunk CRC mismatch")
        if kind == b"IHDR":
            width, height, depth, color_type, *_ = struct.unpack(">IIBBBBB", payload)
            if (depth, color_type) != (8, 6):
                raise AssertionError("fixture PNG is not 8-bit RGBA")
        elif kind == b"IDAT":
            chunks.append(payload)
        elif kind == b"IEND":
            break
        offset += 12 + length
    raw = zlib.decompress(b"".join(chunks))
    stride = width * 4
    rows = []
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        row = raw[cursor + 1:cursor + 1 + stride]
        if filter_type != 0:
            raise AssertionError("fixture PNG must use the simple unfiltered test rows")
        rows.extend(row)
        cursor += stride + 1
    return width, height, bytes(rows)


class RuntimeOwnerLibraryProbeTest(unittest.TestCase):
    def test_generated_source_has_two_receipt_roots_and_real_rgba_pixels(self):
        with tempfile.TemporaryDirectory(prefix="owner-library-fixture-", dir=ROOT / "tmp") as work:
            output = Path(work) / "fixture"
            result = subprocess.run(
                [sys.executable, str(GENERATOR), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            details = json.loads(result.stdout)
            request = json.loads((output / "request.json").read_text(encoding="utf-8"))
            self.assertEqual(request["kind"], "psych-owner-library-typed-media")
            self.assertEqual(details["sourceRoot"], request["sourceRoot"])
            self.assertEqual(details["cppSourceRoot"], request["cppSourceRoot"])
            self.assertEqual(details["unknownSourceRoot"], request["unknownSourceRoot"])
            self.assertEqual([entry["rootRelative"] for entry in request["owners"]], ["alpha", "beta"])
            self.assertNotEqual(request["warmLibrary"], request["lazyLibrary"])
            self.assertNotEqual(request["warmLibrary"], request["unknownLibrary"])
            self.assertEqual([entry["rootRelative"] for entry in request["cppOwners"]], ["alpha", "beta"])
            self.assertTrue(request["cppLibrary"].startswith("codex_owner_cpp_"))
            self.assertEqual(request["cppSoundId"], "shared-sound")
            self.assertEqual(request["cppMusicId"], "shared-music")
            self.assertEqual(request["cppStreamMusicId"], "stream-music")
            self.assertEqual(request["cppFontId"], "shared-font")

            for owner in ("alpha", "beta"):
                root = output / "source" / owner
                project = ET.parse(root / "Project.xml").getroot()
                libraries = {element.attrib["name"]: element.attrib for element in project.findall("library")}
                self.assertEqual(libraries[request["warmLibrary"]]["preload"], "true")
                self.assertEqual(libraries[request["lazyLibrary"]]["preload"], "false")
                self.assertEqual(libraries[request["warmLibrary"]]["embed"], "false")
                self.assertEqual(libraries[request["lazyLibrary"]]["embed"], "false")
                assets = project.findall("assets")
                self.assertEqual(len(assets), 2)
                self.assertEqual(assets[0].attrib["library"], request["warmLibrary"])
                self.assertEqual(assets[1].attrib["library"], request["lazyLibrary"])
                self.assertTrue(all(asset.attrib["embed"] == "false"
                                    for group in assets for asset in group.findall("asset")))
                width, height, rgba = decode_rgba_png(
                    (root / "assets" / "payload" / "pixels.png").read_bytes()
                )
                self.assertEqual((width, height), (2, 2))
                self.assertEqual(rgba[3], 0)
                self.assertNotEqual(rgba[7], 0)
                self.assertNotEqual(rgba[11:15], rgba[15:19])
                self.assertTrue((root / "source" / "psychlua" / "OwnerLibraryMarker.hx").is_file())
                self.assertTrue((root / "assets" / "data").is_dir())
                self.assertTrue((root / "assets" / "songs").is_dir())

            unknown = output / "unknown-source"
            self.assertTrue((unknown / "Project.xml").is_file())
            self.assertTrue((unknown / "source" / "psychlua" / "OwnerLibraryMarker.hx").is_file())
            self.assertTrue((unknown / "assets" / "data").is_dir())
            self.assertTrue((unknown / "assets" / "songs").is_dir())
            self.assertIn("unknown-text", (unknown / "Project.xml").read_text(encoding="utf-8"))

            hashes = []
            for expected in request["cppOwners"]:
                root = output / "cpp-source" / expected["rootRelative"]
                project = ET.parse(root / "Project.xml").getroot()
                libraries = {element.attrib["name"]: element.attrib for element in project.findall("library")}
                self.assertEqual(libraries[request["cppLibrary"]]["preload"], "false")
                self.assertEqual(libraries[request["cppLibrary"]]["embed"], "false")
                assets = project.findall("assets")
                self.assertEqual(len(assets), 1)
                self.assertEqual(assets[0].attrib["library"], request["cppLibrary"])
                declared = {asset.attrib["id"]: asset.attrib for asset in assets[0].findall("asset")}
                self.assertEqual(declared[request["cppSoundId"]]["type"], "sound")
                self.assertEqual(declared[request["cppMusicId"]]["type"], "music")
                expected_stream_type = "music" if expected["rootRelative"] == "alpha" else "sound"
                self.assertEqual(declared[request["cppStreamMusicId"]]["type"], expected_stream_type)
                self.assertEqual(declared[request["cppFontId"]]["type"], "font")
                self.assertTrue(all(asset["embed"] == "false" for asset in declared.values()))

                for name, digest_key, source_key in (
                    ("sound.wav", "soundSha256", None),
                    ("music.wav", "musicSha256", None),
                    ("stream.ogg", "streamSha256", "streamSource"),
                    ("font.otf", "fontSha256", "fontSource"),
                ):
                    path = root / "assets" / "runtime" / name
                    data = path.read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), expected[digest_key])
                    if source_key:
                        source = ROOT / expected[source_key]
                        self.assertEqual(data, source.read_bytes())
                        self.assertEqual(expected[digest_key], hashlib.sha256(source.read_bytes()).hexdigest())
                        if name.endswith(".ogg"):
                            self.assertTrue(data.startswith(b"OggS"))
                            self.assertLess(len(data), 40_000)
                    elif name.endswith(".wav"):
                        with wave.open(BytesIO(data), "rb") as audio:
                            self.assertEqual((audio.getnchannels(), audio.getsampwidth(), audio.getframerate()),
                                             (1, 2, 8000))
                            self.assertEqual(audio.getnframes(), 32)
                hashes.append((expected["soundSha256"], expected["musicSha256"],
                               expected["streamSha256"], expected["fontSha256"]))
            self.assertNotEqual(hashes[0], hashes[1], "same-ID CPP assets must have owner-distinct source bytes")

    def test_native_probe_is_gated_and_waits_for_real_third_owner_revision(self):
        probe = PROBE.read_text(encoding="utf-8")
        harness = HARNESS.read_text(encoding="utf-8")
        runner = RUNNER.read_text(encoding="utf-8")
        self.assertIn("RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_OWNER_LIBRARY_SMOKE') == '1'", probe)
        self.assertIn("ImportRefreshManager.importOnce(source, ImportEngine.PSYCH, scan", probe)
        self.assertIn("build:{target:'html5', command:'', flags:[], values:[], flagsComplete:true}", probe)
        self.assertIn("build:{target:'windows', command:'', flags:[], values:[], flagsComplete:true}", probe)
        self.assertLess(probe.index("verifyLoadedLibraries();"), probe.index("startUnknownImport(unknownSource);"))
        self.assertIn("verifyCppLoadedLibraries();", probe)
        self.assertIn("AudioBuffer.fromFile", probe)
        self.assertIn("LimeFont.fromFile", probe)
        self.assertEqual(probe.count("LimeFont.fromFile("), 1)
        self.assertIn("font.getGlyphs(characters)", probe)
        self.assertIn("font.getGlyphMetrics(glyph)", probe)
        self.assertIn("font.renderGlyph(glyph, 32)", probe)
        font_samples = probe[probe.index("static function fontSampleParts"):probe.index("static function futureSetPending")]
        self.assertLess(font_samples.index("font.renderGlyph(glyph, 32)"),
                        font_samples.index("font.getGlyphMetrics(glyph)"))
        self.assertIn("normalize it before reading size-dependent metrics", font_samples)
        self.assertIn("rendered.getPixel32(x, y, lime.graphics.PixelFormat.ARGB32)", probe)
        self.assertIn("fontMismatch(font, fontBaseline)", probe)
        self.assertIn("fontMismatch(openFont, fontBaseline)", probe)
        self.assertIn("glyph-metrics-", probe)
        self.assertIn("glyph-raster-", probe)
        self.assertIn("glyph-pixel-", probe)
        self.assertIn("owner-library-font-baseline-", probe)
        self.assertIn("fontBaselineFromPrivateCopy(File.getBytes(Std.string(ownerInfo.fontPath)))", probe)
        self.assertIn("fontBaselineFromPrivateCopy(fontBytes)", probe)
        self.assertIn("loadMusic", probe)
        self.assertIn("VorbisFile.fromFile", probe)
        self.assertIn("isVorbisBacked(openStreamMusic)", probe)
        self.assertIn("sameVorbisStream(openStreamMusic, streamSourceBytes)", probe)
        self.assertIn("sameVorbisStream(oldStream, cppAlphaOriginalStream)", probe)
        self.assertIn("request.cppStreamMusicId", probe)
        self.assertIn("view.getPath(Std.string(request.cppStreamMusicId))", probe)
        self.assertIn("hasOnlyIds(view.list('MUSIC')", probe)
        self.assertIn("Std.string(request.cppSoundId), Std.string(request.cppMusicId)", probe)
        self.assertIn("openSoundCacheHit", probe)
        self.assertIn("openWavMusicCacheHit", probe)
        self.assertIn("openStreamDistinctDefault", probe)
        self.assertIn("openStreamDistinctUncached", probe)
        self.assertIn("openStreamBuffersDistinct", probe)
        self.assertIn("openStreamFilesDistinct", probe)
        self.assertIn("openFontCacheHit", probe)
        self.assertIn("sameBytes(File.getBytes(cppAlphaChangedStreamPath), streamBytes)", probe)
        self.assertIn("loadSound", probe)
        self.assertIn("loadFont", probe)
        self.assertIn("sameAudio", probe)
        self.assertIn("verifyCppSourceFailures", probe)
        self.assertIn("musicCompatible.state == 'found'", probe)
        self.assertIn("AssetType.MUSIC]) == true", probe)
        self.assertIn("getMusic'), [soundId]", probe)
        self.assertIn("getMusic'), [fontId]", probe)
        self.assertIn("BitmapData.fromFile(warmImage.path)", probe)
        self.assertIn("samePixels(routedPixels, nativePixels)", probe)
        self.assertIn("imagePixels(rawImage)", probe)
        self.assertIn("sourceSha256:sourceHash", probe)
        self.assertIn("samePixels(bitmapPixels(bitmap), cast ownerInfo.expectedBitmapPixels)", probe)
        self.assertIn("ImportRefreshManager.availabilityRevision() > revisionBeforeUnrelatedImport", probe)
        self.assertIn("owner_library_native_verified", probe)
        phase_seven = probe[probe.index("verifyCppOwnerRelease();"):probe.index("RuntimeSmokeHarness.succeed();")]
        self.assertIn("restoreCppFixtureInputs();", phase_seven)
        self.assertIn("if (RuntimeOwnerLibraryProbe.enabled()) { RuntimeOwnerLibraryProbe.tick(); return; }", harness)
        self.assertIn("$env:CAMMIE_OWNER_LIBRARY_SMOKE = '1'", runner)
        self.assertIn("$env:CAMMIE_SMOKE_SAVE_ROOT = $saveRoot", runner)
        self.assertIn("[Environment]::SetEnvironmentVariable($name, $envBefore[$name], 'Process')", runner)
        self.assertIn("$ExpectedExeSha256", runner)
        self.assertIn("owner_library_native_verified", runner)


if __name__ == "__main__":
    unittest.main()
