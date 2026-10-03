"""Virtual reads apply retained Polymod overlays without touching files."""
from haxe_test_support import HAXE_COMMAND

import base64
import json
import os
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = ROOT / "tmp"
HAXE = ROOT / ".tools/haxe/haxe"
SEO_ROOT = Path("/run/media/cammie/External Storage/FNF-Example-Mods/SeoS")


FIXTURE = r'''import haxe.io.Bytes;
import sys.io.File;

class Main {
  static function fail(message:String):Void throw message;
  static function hex(value:Bytes):String {
    var output = new StringBuf();
    for (index in 0...value.length) {
      var byte = value.get(index);
      var text = StringTools.hex(byte, 2);
      output.add(text);
    }
    return output.toString().toLowerCase();
  }
  static function hasDiagnostic(needle:String):Bool {
    for (message in ImportOverlayResolver.getDiagnostics())
      if (message != null && message.indexOf(needle) >= 0) return true;
    return false;
  }
  static function main() {
    var mode = Sys.args()[0];
    if (mode == "malformed") {
      var intro = ImportOverlayResolver.applyText(
        "assets/data/introText.txt", File.getContent("assets/data/introText.txt"));
      if (intro != "base\n") fail("malformed manifest changed base: " + intro);
      var replaced = ImportOverlayResolver.applyBytes(
        "assets/data/replaced.bin", File.getBytes("assets/data/replaced.bin"));
      if (hex(replaced) != "6f6c64") fail("malformed replacement changed base: " + hex(replaced));
      var merged = ImportOverlayResolver.applyText(
        "assets/data/config.json", File.getContent("assets/data/config.json"));
      if (merged.indexOf("pico-doki") >= 0) fail("malformed merge changed base: " + merged);
      trace(ImportOverlayResolver.getDiagnostics().join("\n"));
      return;
    }
    if (mode == "cache") {
      var first = ImportOverlayResolver.applyText(
        "assets/data/introText.txt", File.getContent("assets/data/introText.txt"));
      if (first != "base\n+old") fail("initial cache view: " + first);
      File.saveContent("assets/imported_mods/compatOverlays.json",
        '{"version":1,"roots":[],"overlays":[{"engine":"fixture","mod":"fixture","operation":"_append","kind":"textAppend","relativePath":"data/introText.txt","targetPath":"data/introText.txt","provenance":"cache/_append/new","reason":"destination-exists","payload":"+new"}]}');
      ImportOverlayResolver.invalidate();
      var second = ImportOverlayResolver.applyText(
        "assets/data/introText.txt", File.getContent("assets/data/introText.txt"));
      if (second != "base\n+new") fail("invalidated cache view: " + second);
      trace("resolver-cache-ok");
      return;
    }
    if (mode == "mounted") {
      var suffix = Sys.args()[1];
      var mounted = ImportOverlayResolver.applyText(
        "assets/data/introText.txt", File.getContent("assets/data/introText.txt"));
      if (mounted != File.getContent("assets/data/introText.txt") + suffix)
        fail("mounted virtual intro text");
      trace("resolver-mounted-ok");
      return;
    }
    if (mode == "ordered") {
      var ordered = ImportOverlayResolver.applyText(
        "assets/data/introText.txt", File.getContent("assets/data/introText.txt"));
      if (ordered != "replaced+first+second") fail("plan order: " + ordered);
      trace("resolver-order-ok");
      return;
    }
    var intro = ImportOverlayResolver.applyText(
      "assets/data/introText.txt", File.getContent("assets/data/introText.txt"));
    if (intro != "base\n+tail+tail") fail("append identity/order: " + intro);
    var replaced = ImportOverlayResolver.applyBytes(
      "assets/data/replaced.bin", File.getBytes("assets/data/replaced.bin"));
    if (hex(replaced) != "00ff41") fail("binary replace: " + hex(replaced));
    var merged = ImportOverlayResolver.applyText(
      "assets/data/config.json", File.getContent("assets/data/config.json"));
    if (merged.indexOf("pico-doki") < 0) fail("json patch: " + merged);
    var untouched = ImportOverlayResolver.applyText(
      "assets/data/other.txt", File.getContent("assets/data/other.txt"));
    if (untouched != "other") fail("nonmatching target: " + untouched);
    trace("resolver-ok");
  }
}'''


class ImportOverlayResolverTest(unittest.TestCase):
    def run_fixture(self, workspace: Path, *args: str) -> subprocess.CompletedProcess:
        folder = workspace / "fixture"
        folder.mkdir(exist_ok=True)
        (folder / "Main.hx").write_text(FIXTURE, newline='\n')
        env = os.environ.copy()
        env["TMPDIR"] = str(TMP_ROOT)
        return subprocess.run(
            [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(folder), "--run", "Main", *args],
            cwd=workspace,
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )

    @staticmethod
    def write_manifest(workspace: Path, overlays):
        path = workspace / "assets/imported_mods/compatOverlays.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 1, "roots": [], "overlays": overlays}), newline='\n')
        return path

    @staticmethod
    def record(operation, kind, target, payload, provenance, engine="Legacy FNF/Polymod", order=None, mod="fixture"):
        result = {
            "engine": engine,
            "mod": mod,
            "operation": operation,
            "kind": kind,
            "relativePath": target,
            "targetPath": target,
            "provenance": provenance,
            "reason": "destination-exists",
            "payload": payload,
        }
        if order is not None:
            result["order"] = order
        return result

    def make_workspace(self):
        workspace = Path(tempfile.mkdtemp(dir=TMP_ROOT))
        (workspace / "assets/data").mkdir(parents=True)
        (workspace / "assets/data/introText.txt").write_text("base\n", newline='\n')
        (workspace / "assets/data/replaced.bin").write_bytes(b"old")
        (workspace / "assets/data/config.json").write_text('{"ownedChars":["bf"]}', newline='\n')
        (workspace / "assets/data/other.txt").write_text("other", newline='\n')
        return workspace

    def test_existing_targets_apply_append_replace_merge_and_deduplicate(self):
        workspace = self.make_workspace()
        overlays = [
            self.record("_append", "textAppend", "data/introText.txt", "+tail", "a/_append/data/introText.txt"),
            # An exact persisted duplicate is normalized away, but the same
            # payload from another mod is a distinct authored operation and
            # must remain visible.
            self.record("_append", "textAppend", "data/introText.txt", "+tail", "a/_append/data/introText.txt", order=99),
            self.record("_append", "textAppend", "data/introText.txt", "+tail", "b/_append/data/introText.txt", mod="second-mod"),
            self.record(
                "_replace", "replace", "data/replaced.bin",
                "base64:" + base64.b64encode(b"\x00\xffA").decode(), "replace/_replace/data/replaced.bin"
            ),
            self.record(
                "_merge", "jsonPatch", "data/config.json",
                '[{"op":"add","path":"/ownedChars/-","value":"pico-doki"}]',
                "merge/_merge/data/config.json"
            ),
        ]
        self.write_manifest(workspace, overlays)
        result = self.run_fixture(workspace, "synthetic")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("resolver-ok", result.stdout + result.stderr)
        self.assertEqual((workspace / "assets/data/introText.txt").read_text(), "base\n")
        self.assertEqual((workspace / "assets/data/replaced.bin").read_bytes(), b"old")
        self.assertEqual((workspace / "assets/data/config.json").read_text(), '{"ownedChars":["bf"]}')

    def test_malformed_manifest_and_payloads_fall_back_safely(self):
        workspace = self.make_workspace()
        path = workspace / "assets/imported_mods/compatOverlays.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not-json", newline='\n')
        result = self.run_fixture(workspace, "malformed")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("overlay-manifest-invalid", result.stdout + result.stderr)

        overlays = [
            self.record("_replace", "replace", "data/replaced.bin", "base64:not-valid", "bad/_replace/data/replaced.bin"),
            self.record("_merge", "jsonPatch", "data/config.json", "not-json", "bad/_merge/data/config.json"),
        ]
        self.write_manifest(workspace, overlays)
        result = self.run_fixture(workspace, "malformed")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr
        self.assertTrue(
            "overlay-payload-base64-invalid" in output or "overlay-merge-invalid" in output,
            output,
        )

    def test_manifest_cache_can_be_invalidated(self):
        workspace = self.make_workspace()
        self.write_manifest(workspace, [
            self.record("_append", "textAppend", "data/introText.txt", "+old", "cache/_append/old")
        ])
        (workspace / "assets/data/introText.txt").write_text("base\n", newline='\n')
        self.write_manifest(workspace, [
            self.record("_append", "textAppend", "data/introText.txt", "+old", "cache/_append/old")
        ])
        result = self.run_fixture(workspace, "cache")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("resolver-cache-ok", result.stdout + result.stderr)

    def test_native_read_boundaries_use_the_virtual_resolver(self):
        assets_source = (ROOT / "source/FNFAssets.hx").read_text()
        title_source = (ROOT / "source/TitleState.hx").read_text()
        self.assertIn("ImportOverlayResolver.applyText", assets_source)
        self.assertIn("ImportOverlayResolver.applyBytes", assets_source)
        self.assertIn('FNFAssets.getText(\'assets/data/introText.txt\')', title_source)

    def test_explicit_plan_order_wins_for_noncommutative_operations(self):
        workspace = self.make_workspace()
        (workspace / "assets/data/introText.txt").write_text("base\n", newline='\n')
        self.write_manifest(workspace, [
            # Deliberately reverse provenance order: the ordinal is the source
            # planner order and must produce replacement, then first, then
            # second regardless of mod names.
            self.record("_append", "textAppend", "data/introText.txt", "+second", "aaa/_append/data/introText.txt", order=2),
            self.record("_replace", "replace", "data/introText.txt", "base64:cmVwbGFjZWQ=", "zzz/_replace/data/introText.txt", order=0),
            self.record("_append", "textAppend", "data/introText.txt", "+first", "000/_append/data/introText.txt", order=1),
        ])
        result = self.run_fixture(workspace, "ordered")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("resolver-order-ok", result.stdout + result.stderr)

    @unittest.skipUnless(SEO_ROOT.is_dir(), "mounted SeoS donor is unavailable")
    def test_mounted_intro_text_overlay_is_virtual_and_read_only(self):
        workspace = self.make_workspace()
        donor_base = (SEO_ROOT / "assets/data/introText.txt").read_bytes()
        donor_append = (SEO_ROOT / "mods/introMod/_append/data/introText.txt").read_bytes()
        (workspace / "assets/data/introText.txt").write_bytes(donor_base)
        self.write_manifest(workspace, [
            self.record(
                "_append", "textAppend", "data/introText.txt", donor_append.decode(),
                "introMod/_append/data/introText.txt", "Legacy FNF/Polymod"
            )
        ])
        before_donor = {
            "base": (SEO_ROOT / "assets/data/introText.txt").read_bytes(),
            "append": (SEO_ROOT / "mods/introMod/_append/data/introText.txt").read_bytes(),
        }
        before_destination = (workspace / "assets/data/introText.txt").read_bytes()
        result = self.run_fixture(workspace, "mounted", donor_append.decode())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("resolver-mounted-ok", result.stdout + result.stderr)
        self.assertEqual(before_donor["base"], (SEO_ROOT / "assets/data/introText.txt").read_bytes())
        self.assertEqual(before_donor["append"], (SEO_ROOT / "mods/introMod/_append/data/introText.txt").read_bytes())
        self.assertEqual(before_destination, (workspace / "assets/data/introText.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
