"""Owner-scoped HXC font registration and cache coverage."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


@unittest.skipUnless(HAXE.is_file(), "portable Haxe toolchain is not mounted")
class HxcOwnerFontTest(unittest.TestCase):
    def test_owner_font_family_is_registered_cached_and_never_crosses_roots(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hxc-owner-font-", dir=ROOT / "tmp") as folder:
            base = Path(folder)
            owner_a = base / "owner-a"
            owner_b = base / "owner-b"
            (owner_a / "fonts").mkdir(parents=True)
            (owner_b / "fonts").mkdir(parents=True)
            (owner_a / "fonts/Shared.ttf").write_text("Owner A Family")
            (owner_b / "fonts/Shared.ttf").write_text("Owner B Family")
            native_font = base / "native/Native.ttf"
            native_font.parent.mkdir()
            native_font.write_text("Native Family")

            font_stub = base / "openfl/text/Font.hx"
            font_stub.parent.mkdir(parents=True)
            font_stub.write_text('''package openfl.text;
import sys.FileSystem;
import sys.io.File;
class Font {
 public var fontName:String;
 public static var loaded:Array<String> = [];
 public static var registered:Array<String> = [];
 public function new(name:String) this.fontName=name;
 public static function fromFile(path:String):Font {
  loaded.push(path);
  return FileSystem.exists(path) ? new Font(File.getContent(path)) : null;
 }
 public static function registerFont(font:Font):Void registered.push(font.fontName);
}''')

            main = base / "Main.hx"
            main.write_text(f'''class Main {{
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main() {{
  var a = HxcOwnerFont.family({str(owner_a)!r}, "Shared.ttf");
  check(a == "Owner A Family", "owner A family: " + a);
  check(openfl.text.Font.loaded.length == 1
    && openfl.text.Font.loaded[0].indexOf({str(owner_a)!r}) == 0,
    "font must load from owner A only");
  check(HxcOwnerFont.family({str(owner_a)!r}, "Shared.ttf") == a
    && openfl.text.Font.registered.length == 1, "owner font should register once");

  var b = HxcOwnerFont.family({str(owner_b)!r}, "Shared.ttf");
  check(b == "Owner B Family", "owner B family: " + b);
  check(openfl.text.Font.loaded.length == 2
    && openfl.text.Font.loaded[1].indexOf({str(owner_b)!r}) == 0,
    "same key must resolve only inside owner B");

  check(HxcOwnerFont.family({str(owner_a)!r}, "../owner-b/fonts/Shared.ttf") == null,
    "traversal key must be rejected");
  check(openfl.text.Font.loaded.length == 2, "rejected key must not be opened");
  check(HxcOwnerFont.family({str(owner_a)!r}, "Missing.ttf") == null,
    "missing owner font must not resolve from another root");
  check(HxcOwnerFont.family({str(owner_a)!r}, "Native.ttf", {str(native_font)!r}) == null,
    "native font should remain the caller's fallback");
  check(HxcOwnerFont.family("assets", "Shared.ttf") == null,
    "native root must retain native Paths.font handling");
  Sys.println("hxc-owner-font-ok");
 }}
}}''')

            env = os.environ.copy()
            env["TMPDIR"] = str(ROOT / "tmp")
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", folder,
                 "-main", "Main", "--interp"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=300,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("hxc-owner-font-ok", result.stdout)
            self.assertIn("[hxc-font-asset-missing]", result.stdout + result.stderr)
            self.assertEqual((result.stdout + result.stderr).count("[hxc-font-asset-missing]"), 1)

    def test_hxc_paths_font_uses_registered_family_for_the_current_owner(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        start = source.index("Reflect.setField(proxy, 'font'")
        end = source.index("});", start)
        self.assertIn("HxcOwnerFont.family(root, key, nativeFont)", source[start:end])


if __name__ == "__main__":
    unittest.main()
