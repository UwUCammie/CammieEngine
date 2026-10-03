"""Portable ASTC header/probe coverage for the V-Slice importer boundary."""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
EXAMPLES = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
DONOR_ASTC = (
    EXAMPLES
    / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/images/freeplay/albumRoll/takeover.astc"
)


def haxe_string(value: str) -> str:
    return json.dumps(str(value))


class VSliceAstcAdapterTest(unittest.TestCase):
    def run_fixture(self, main_source: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            main_path = Path(folder) / "Main.hx"
            main_path.write_text(main_source, newline='\n')
            return subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", folder, "-main", "Main", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )

    def test_header_validation_is_little_endian_and_rejects_bad_payload(self):
        main = r'''import haxe.io.Bytes;
class Main {
  static function fail(value:String):Void throw value;
  static function header(payload:Int):Bytes {
    var bytes = Bytes.alloc(16 + payload);
    bytes.set(0, 0x13); bytes.set(1, 0xAB); bytes.set(2, 0xA1); bytes.set(3, 0x5C);
    bytes.set(4, 5); bytes.set(5, 4); bytes.set(6, 1);
    bytes.set(7, 0xE8); bytes.set(8, 0x03); bytes.set(9, 0);
    bytes.set(10, 0xE8); bytes.set(11, 0x03); bytes.set(12, 0);
    bytes.set(13, 1); bytes.set(14, 0); bytes.set(15, 0);
    return bytes;
  }
  static function main() {
    var valid = VSliceAstcAdapter.parseHeader(header(800000), "takeover.astc");
    if (!valid.valid || !valid.payloadMatches) fail("valid header");
    if (valid.width != 1000 || valid.height != 1000 || valid.blockX != 5 || valid.blockY != 4) fail("dimensions");
    if (valid.expectedPayloadBytes != 800000) fail("payload size");
    var shortPayload = VSliceAstcAdapter.parseHeader(header(799999), "short.astc");
    if (!shortPayload.valid || shortPayload.payloadMatches) fail("payload mismatch");
    if (shortPayload.error.indexOf("800000") < 0) fail("payload diagnostic");
    var detail = VSliceAstcAdapter.diagnostic("takeover.astc", valid);
    if (detail.indexOf("1000x1000") < 0 || detail.indexOf("5x4x1") < 0)
      fail("valid ASTC diagnostic detail");
    var bad = Bytes.alloc(16);
    var invalid = VSliceAstcAdapter.parseHeader(bad, "bad.astc");
    if (invalid.valid || invalid.error.indexOf("magic") < 0) fail("bad magic");
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_donor_header_matches_standard_astc_layout(self):
        if not DONOR_ASTC.is_file():
            self.skipTest("the read-only donor ASTC fixture is not mounted")
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var header = VSliceAstcAdapter.inspectFile({haxe_string(str(DONOR_ASTC))});
    if (!header.valid || !header.payloadMatches) fail("donor header validation: " + header.error);
    if (header.width != 1000 || header.height != 1000 || header.depth != 1) fail("donor dimensions");
    if (header.blockX != 5 || header.blockY != 4 || header.blockZ != 1) fail("donor block dimensions");
    if (header.payloadBytes != 800000) fail("donor payload length");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_probe_and_process_boundary_are_explicit_and_shell_free(self):
        source = (ROOT / "source/VSliceAstcAdapter.hx").read_text()
        self.assertIn("new Process(available.executable, ['-ds', source, destination])", source)
        self.assertNotIn("Sys.command", source)
        self.assertNotIn("/bin/sh", source)
        self.assertIn("Sys.programPath()", source)
        self.assertIn("cachedProbeKey", source)
        diagnostic_harness = (ROOT / "tools/diagnose_example_auto_import.py").read_text()
        self.assertIn('(temp / "VSliceAstcAdapter.hx").write_text', diagnostic_harness)
        main = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    #if sys
    VSliceAstcAdapter.resetProbeCache();
    var probe = VSliceAstcAdapter.probe("/definitely/not-a-real-working-directory");
    if (probe.reason.indexOf("DISAPPOINTINGPLUS_ASTCENC") < 0 && !probe.available) fail("actionable probe");
    #end
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_probe_cache_is_scoped_to_runtime_root(self):
        """A decoder may be supplied beside different runtime/test roots."""
        main = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    #if sys
    // Exercise runtime-local candidate ordering independently of any decoder
    // override supplied by the outer test environment.
    Sys.putEnv("DISAPPOINTINGPLUS_ASTCENC", "");
    VSliceAstcAdapter.resetProbeCache();
    var first = VSliceAstcAdapter.probe("/tmp/vslice-astc-first");
    var second = VSliceAstcAdapter.probe("/tmp/vslice-astc-second");
    if (first.searched.length == 0 || second.searched.length == 0) fail("empty probe search");
    var firstLocal = false;
    var secondLocal = false;
    for (candidate in first.searched)
      if (candidate.indexOf("/tmp/vslice-astc-first/tools/astcenc") >= 0) firstLocal = true;
    for (candidate in second.searched)
      if (candidate.indexOf("/tmp/vslice-astc-second/tools/astcenc") >= 0) secondLocal = true;
    if (!firstLocal)
      fail("first working-directory candidates");
    if (!secondLocal)
      fail("probe cache reused another runtime root");
    #end
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_probe_includes_checkout_tools_decoder_root(self):
        """Read-only scans launched from the checkout can use .tools/astcenc."""
        main = r'''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    #if sys
    Sys.putEnv("DISAPPOINTINGPLUS_ASTCENC", "");
    VSliceAstcAdapter.resetProbeCache();
    var probe = VSliceAstcAdapter.probe("/tmp/vslice-checkout");
    var checkoutLocal = false;
    for (candidate in probe.searched)
      if (candidate.indexOf("/tmp/vslice-checkout/.tools/astcenc/astcenc") >= 0)
        checkoutLocal = true;
    if (!checkoutLocal) fail("checkout .tools decoder candidate");
    #end
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
