"""Owner switch rows collapse launchable states to one validated package row."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameModSwitchPlanTest(unittest.TestCase):
    def test_owner_rows_are_deduplicated_and_missing_roots_are_hidden(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "assets/imported_mods/alpha-owner"
            global_only = base / "assets/imported_mods/global-only-owner"
            states = owner / "data/states"
            states.mkdir(parents=True)
            (global_only / "data").mkdir(parents=True)
            (global_only / "data/global.hx").write_text("function update(elapsed) {}")
            for name in ("Menu", "Freeplay"):
                (states / f"{name}.hx").write_text("function create() {}")
            (base / "catalog.json").write_text('''
{"version":1,"entries":[
 {"root":"assets/imported_mods/missing-owner","label":"Missing","states":["data/states/Gone.hx"]},
 {"root":"assets/imported_mods/alpha-owner","label":"Alpha","states":["data/states/Menu.hx","data/states/Freeplay.hx"]},
 {"root":"assets/imported_mods/global-only-owner","label":"Global only","states":[]}
]}
''')
            (base / "Main.hx").write_text('''
class Main {
 static function main():Void {
  var raw=sys.io.File.getContent("catalog.json");
  var active=CodenameModSwitchPlan.fromCatalog(raw,Sys.args()[0]);
  if (!active.valid || active.entries.length!=3) throw "owner rows were not grouped";
  if (CodenameModSwitchPlan.initialSelection(active.entries)!=1) throw "active owner is not default selection";
  if (!active.entries[0].disable || active.entries[0].active) throw "native row";
  if (active.entries[1].label!="Alpha" || !active.entries[1].active
      || active.entries[1].root!=Sys.args()[0]) throw "owner row";
  if (active.entries[2].label!="Global only" || active.entries[2].active
      || active.entries[2].disable) throw "owner without launchable states was omitted";
  var disabled=CodenameModSwitchPlan.fromCatalog(raw,"");
  if (CodenameModSwitchPlan.initialSelection(disabled.entries)!=0) throw "native row is not default without an owner";
  if (!disabled.entries[0].active || disabled.entries[1].active) throw "disable mark";
  if (active.diagnostics.length!=0) throw "stale owner emitted a diagnostic";
 }
}''')
            process = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base), "--run", "Main",
                 "assets/imported_mods/alpha-owner"],
                cwd=base, text=True, capture_output=True,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
