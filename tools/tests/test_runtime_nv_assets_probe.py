"""Generated retained-source contract for Nightmare Vision raw Assets smoke QA."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zlib


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "tools" / "prepare_nv_assets_fixture.py"
RUNNER = ROOT / "tools" / "run_nv_assets_native.ps1"
PROBE = ROOT / "source" / "RuntimeNvAssetsProbe.hx"
HARNESS = ROOT / "source" / "RuntimeSmokeHarness.hx"
ASSET_BINDINGS = ROOT / "source" / "NightmareVisionAssetsBindings.hx"


def decode_rgba_png(data: bytes) -> tuple[int, int, bytes]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("fixture image is not PNG")
    offset = 8
    image_data = []
    width = height = None
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        crc = struct.unpack(">I", data[offset + 8 + length:offset + 12 + length])[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise AssertionError("PNG chunk checksum mismatch")
        if kind == b"IHDR":
            width, height, depth, color_type, *_ = struct.unpack(">IIBBBBB", payload)
            if (depth, color_type) != (8, 6):
                raise AssertionError("fixture must be an 8-bit RGBA image")
        elif kind == b"IDAT":
            image_data.append(payload)
        elif kind == b"IEND":
            break
        offset += 12 + length
    raw = zlib.decompress(b"".join(image_data))
    stride = width * 4
    output = bytearray()
    cursor = 0
    for _ in range(height):
        if raw[cursor] != 0:
            raise AssertionError("fixture PNG must use unfiltered rows")
        output.extend(raw[cursor + 1:cursor + 1 + stride])
        cursor += stride + 1
    return width, height, bytes(output)


def first_argb(rgba: bytes) -> str:
    return f"{rgba[3]:02X}{rgba[0]:02X}{rgba[1]:02X}{rgba[2]:02X}"


class RuntimeNvAssetsProbeTest(unittest.TestCase):
    def test_generated_source_has_outer_provider_and_two_real_content_roots(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="nv-assets-fixture-", dir=ROOT / "tmp") as scratch:
            output = Path(scratch) / "fixture"
            result = subprocess.run(
                [sys.executable, str(GENERATOR), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            details = json.loads(result.stdout)
            request = json.loads((output / "request.json").read_text(encoding="utf-8"))
            source = output / "source"
            self.assertEqual(request["kind"], "nightmare-vision-raw-assets")
            self.assertEqual(request["buildTarget"], "windows")
            self.assertEqual(details["sourceRoot"], request["sourceRoot"])
            self.assertEqual([owner["directory"] for owner in request["owners"]], ["alpha", "beta"])
            self.assertTrue((source / "NightmareVision.exe").read_bytes().startswith(b"MZ"))
            self.assertIn(b"com.nmvTeam.nightmareEngine", (source / "NightmareVision.exe").read_bytes())
            outer = ET.parse(source / "Project.xml").getroot()
            self.assertEqual(outer.find("app").attrib["packageName"], "com.nmvTeam.nightmareEngine")
            self.assertEqual(outer.find("library").attrib["name"], request["library"])
            self.assertEqual(outer.find("library").attrib["embed"], "false")
            outer_groups = {group.attrib["path"]: group.attrib["rename"] for group in outer.findall("assets")}
            self.assertEqual(outer_groups, {"assets/images": "assets/images", "assets/text": "assets/text"})
            outer_ids = {asset.attrib["id"]: asset.attrib for asset in outer.findall(".//asset")}
            self.assertEqual(outer_ids["core-only"]["type"], "image")
            self.assertEqual(outer_ids["core-text"]["type"], "text")
            self.assertEqual(outer_ids["shared-image"]["rename"], "shared-image.png")

            core_png = (source / "assets" / "images" / "core-only.png").read_bytes()
            width, height, pixels = decode_rgba_png(core_png)
            self.assertEqual((width, height), (2, 2))
            self.assertEqual(first_argb(pixels[:4]), request["corePixel"])
            self.assertEqual(hashlib.sha256(core_png).hexdigest(), request["coreSharedSha256"])
            for owner in request["owners"]:
                package = source / "content" / owner["directory"]
                self.assertTrue((package / "meta.json").is_file())
                project = ET.parse(package / "assets" / "Project.xml").getroot()
                self.assertIsNone(project.find("app"), "content packages must inherit family identity, not claim an outer game")
                self.assertEqual(project.find("library").attrib["name"], request["library"])
                package_groups = {group.attrib["path"]: group.attrib["rename"] for group in project.findall("assets")}
                self.assertEqual(package_groups, {"images": "assets/images", "shared": "assets/text"})
                ids = {asset.attrib["id"]: asset.attrib for asset in project.findall(".//asset")}
                self.assertEqual(ids["shared-image"]["type"], "image")
                self.assertEqual(ids["shared-image"]["rename"], "shared-image.png")
                self.assertEqual(ids["type-shadow"]["type"], "text")
                self.assertEqual(ids[f"{owner['directory']}-only"]["type"], "image")
                for asset in ids.values():
                    self.assertEqual(asset["embed"], "false")
                package_png = (package / "assets" / "images" / "shared-image.png").read_bytes()
                self.assertEqual(hashlib.sha256(package_png).hexdigest(), owner["sharedSha256"])
                self.assertEqual(first_argb(decode_rgba_png(package_png)[2][:4]), owner["sharedPixel"])
                self.assertTrue((package / "assets" / "images" / "unmapped.png").is_file())
                self.assertTrue((package / "assets" / "shared" / "package-text.txt").is_file())
            self.assertTrue((source / "assets" / "data").is_dir())
            self.assertTrue((source / "assets" / "songs").is_dir())

            repeated = subprocess.run(
                [sys.executable, str(GENERATOR), "--output", str(output)],
                cwd=ROOT, capture_output=True, text=True, timeout=20,
            )
            self.assertNotEqual(repeated.returncode, 0)
            self.assertIn("Refusing to overwrite", repeated.stderr)

    def test_probe_and_runner_are_opt_in_and_use_actual_receipt_imports(self):
        probe = PROBE.read_text(encoding="utf-8")
        harness = HARNESS.read_text(encoding="utf-8")
        runner = RUNNER.read_text(encoding="utf-8")
        bindings = ASSET_BINDINGS.read_text(encoding="utf-8")
        self.assertIn("RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_NV_ASSETS_SMOKE') == '1'", probe)
        self.assertIn("CAMMIE_SMOKE_SAVE_ROOT", probe)
        self.assertIn("FlxG.sound.muted", probe)
        self.assertIn("ImportWorkflow.scanNow(source, ImportEngine.NIGHTMARE_VISION)", probe)
        self.assertIn("ImportRefreshManager.importOnce(source, ImportEngine.NIGHTMARE_VISION, scan", probe)
        self.assertIn("build:{target:'windows', command:'', flags:[], values:[], flagsComplete:true}", probe)
        self.assertIn("PlayState.seedNightmareVisionCommon(interp, paths, prefs, plugins, mods, difficulty)", probe)
        self.assertIn("import lime.utils.Assets as LimeAssetsApi", probe)
        self.assertIn("import openfl.utils.Assets as OpenFlAssetsApi", probe)
        self.assertIn("import openfl.Assets as LegacyOpenFlAssetsApi", probe)
        self.assertIn("import openfl.Assets;", probe)
        self.assertIn("import lime.utils.Assets;", probe)
        self.assertIn("Type.resolveClass('lime.utils.Assets')", probe)
        self.assertIn("Type.resolveClass('openfl.Assets')", probe)
        self.assertIn("variables.set('__nvAssetProbeResults', probeResults)", probe)
        self.assertIn("__nvAssetProbeResults.bareLimeText", probe)
        self.assertIn("__nvAssetProbeResults.bareOpenFlText", probe)
        self.assertIn("Reflect.field(probeResults, 'coreText')", probe)
        self.assertNotIn("variables.get('coreText')", probe)
        self.assertIn("RuntimeOwnerAssetIdentity.acquire(owner.ownerRoot,", probe)
        self.assertIn("RuntimeOwnerAssetIdentity.acquire(provider.ownerRoot,", probe)
        self.assertIn("ImportEngine.NIGHTMARE_VISION, 'core');", probe)
        self.assertIn("provider.ownerRoot + '/__nmv_core/'", probe)
        self.assertIn("ImportRefreshManager.ownerAssetIndexBinding(owner.ownerRoot", probe)
        self.assertIn("Reflect.field(committedHandoff, 'receiverNamespace') == receiverNamespace", probe)
        self.assertIn("Reflect.field(committedCoreBinding, 'namespace') == receiverNamespace", probe)
        self.assertIn("SourceCompositeAssetLibrary", (ROOT / "source" / "SourceCompositeAssetLibrary.hx").read_text(encoding="utf-8"))
        self.assertIn("AssetType.IMAGE", probe)
        self.assertIn("getPath'),", probe)
        self.assertIn("loadLibrary", probe)
        self.assertIn("loadImage", probe)
        self.assertIn("loadBitmapData", probe)
        self.assertIn("onChange.dispatch()", probe)
        self.assertIn("releaseOwnerAssets()", probe)
        self.assertIn("RuntimeNvAssetsProbe.enabled()", harness)
        self.assertIn("'openfl.Assets', openFlAssets", bindings)
        self.assertIn("$ExpectedExeSha256", runner)
        self.assertIn("$env:CAMMIE_NV_ASSETS_SMOKE = '1'", runner)
        self.assertIn("$env:CAMMIE_SMOKE_SAVE_ROOT = $saveRoot", runner)
        self.assertIn("-WindowStyle Hidden", runner)
        self.assertIn("[Environment]::SetEnvironmentVariable($name, $envBefore[$name], 'Process')", runner)
        self.assertIn("nv_assets_native_verified", runner)
        self.assertIn("RuntimeDir must be a private runtime outside the checkout", runner)


if __name__ == "__main__":
    unittest.main()
