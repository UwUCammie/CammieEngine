"""Direct imported Freeplay returns to its caller without crossing owners."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ImportedFreeplayCallerTest(unittest.TestCase):
    def test_caller_survives_gameplay_return_but_not_owner_or_native_navigation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "ImportedFreeplayCaller.hx").write_text(
                (ROOT / "source/ImportedFreeplayCaller.hx").read_text())
            (base / "CompatScriptManifest.hx").write_text('''class CompatScriptManifest {
 public static function destinationKey(value:String):String
  return value == null ? '' : StringTools.trim(value).toLowerCase();
}''')
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var ownerA = 'assets/imported_mods/owner-a';
  var ownerB = 'assets/imported_mods/owner-b';
  ImportedFreeplayCaller.capture(ownerA, 'data/states/Menu.hx');
  ImportedFreeplayCaller.keepFor(ownerA, true);
  var route = ImportedFreeplayCaller.take(ownerA);
  if (route == null || route.ownerRoot != ownerA
   || route.scriptPath != 'data/states/Menu.hx') throw 'lost gameplay return';
  if (ImportedFreeplayCaller.take(ownerA) != null) throw 'return reused';
  ImportedFreeplayCaller.capture(ownerA, 'data/states/Menu.hx');
  if (ImportedFreeplayCaller.take(ownerB) != null) throw 'cross-owner return';
  ImportedFreeplayCaller.capture(ownerA, 'data/states/Menu.hx');
  ImportedFreeplayCaller.keepFor(ownerA, false);
  if (ImportedFreeplayCaller.take(ownerA) != null) throw 'native launch inherited caller';
  ImportedFreeplayCaller.capture('', 'data/states/Menu.hx');
  if (ImportedFreeplayCaller.take(ownerA) != null) throw 'empty owner retained';
  ImportedFreeplayCaller.capturePackage(ownerA);
  ImportedFreeplayCaller.keepFor('', false);
  if (ImportedFreeplayCaller.ownerForFreeplay('') != ownerA)
   throw 'package owner was not retained for native Freeplay filtering';
  ImportedFreeplayCaller.keepFor('', true);
  var packageRoute = ImportedFreeplayCaller.take(ownerA);
  if (packageRoute == null || packageRoute.ownerRoot != ownerA
   || packageRoute.scriptPath != '' || packageRoute.returnKind != 'package-picker')
   throw 'native Freeplay did not return to the package picker';
  if (ImportedFreeplayCaller.take(ownerA) != null) throw 'package return reused';
  ImportedFreeplayCaller.capturePackage(ownerA);
  ImportedFreeplayCaller.keepFor(ownerB, true);
  if (ImportedFreeplayCaller.take(ownerA) != null) throw 'package token crossed owners';
 }
}''')
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(base),
                 "-main", "Main", "--interp"], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_freeplay_captures_and_consumes_imported_caller(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        self.assertIn("ImportedFreeplayCaller.capture(source.ownerRoot, source.scriptPath)", source)
        self.assertIn("ImportedFreeplayCaller.keepFor(CodenameModRuntime.activeRoot()", source)
        self.assertIn("ImportedFreeplayCaller.take(directOwnerRoot)", source)


if __name__ == "__main__":
    unittest.main()
