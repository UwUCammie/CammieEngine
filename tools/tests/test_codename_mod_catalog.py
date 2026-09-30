"""Codename launch catalog merges only validated destination owner state paths."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameModCatalogTest(unittest.TestCase):
    def test_additive_owner_merge_and_unsafe_state_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "assets/imported_mods/fnas-owner"
            other = base / "assets/imported_mods/other-owner"
            for root, names in ((owner, ("FnasMainState", "bigasscredits")),
                                (other, ("OtherMenu",))):
                for name in names:
                    state = root / "data/states" / (name + ".hx")
                    state.parent.mkdir(parents=True, exist_ok=True)
                    state.write_text("function create() {}")
            outside = base / "outside.hx"
            outside.write_text("function create() {}")
            (owner / "data/states/Escape.hx").symlink_to(outside)
            (base / "Main.hx").write_text('''
class Main {
 static function main():Void {
  var owner=Sys.args()[0];
  var other=Sys.args()[1];
  var first=CodenameModCatalog.merge("",owner,"FNAS",[
    "data/states/FnasMainState.hx", "data/states/../global.hx",
    "data/states/Escape.hx", "data/states/bigasscredits.hx"]);
  if (!first.valid || !first.changed || first.data.entries.length!=1
      || first.data.entries[0].states.join(",")!="data/states/FnasMainState.hx,data/states/bigasscredits.hx")
    throw "first merge: " + first.error;
  var raw=CodenameModCatalog.stringify(first.data);
  var second=CodenameModCatalog.merge(raw,other,"Other",["data/states/OtherMenu.hx"]);
  if (!second.changed || second.data.entries.length!=2
      || second.data.entries[0].root!=owner || second.data.entries[0].label!="FNAS")
    throw "other owner merge";
  var extended=CodenameModCatalog.merge(CodenameModCatalog.stringify(second.data),owner,
    "replacement label",["data/states/FnasMainState.hx"]);
  if (extended.changed || extended.data.entries.length!=2
      || extended.data.entries[0].label!="FNAS") throw "existing entry not stable";
  var malicious=CodenameModCatalog.merge(CodenameModCatalog.stringify(extended.data),
    "assets/imported_mods/../foreign","bad",["data/states/OtherMenu.hx"]);
  if (malicious.valid || malicious.changed) throw "unsafe root accepted";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", "assets/imported_mods/fnas-owner",
                                "assets/imported_mods/other-owner"], cwd=base,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_malformed_catalog_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "assets/imported_mods/fnas-owner"
            state = owner / "data/states/FnasMainState.hx"
            state.parent.mkdir(parents=True)
            state.write_text("function create() {}")
            (base / "Main.hx").write_text('''
class Main {
 static function main():Void {
  var merged=CodenameModCatalog.merge("{truncated",Sys.args()[0],"FNAS",
    ["data/states/FnasMainState.hx"]);
  if (merged.valid || merged.changed || merged.error=="") throw "malformed catalog overwritten";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", "assets/imported_mods/fnas-owner"], cwd=base,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_transition_helpers_and_missing_owners_are_reconciled(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "assets/imported_mods/owner"
            states = owner / "data/states"
            states.mkdir(parents=True)
            (states / "MainMenu.hx").write_text("""
MusicBeatTransition.script = 'data/states/Dsides/StickerTransition';
MusicBeatTransition.script = 'data/states/Dsides/noTrans';
function create() {}
""")
            (states / "MusicBeatTransition.hx").write_text("function create() {}")
            for name in ("StickerTransition", "noTrans"):
                path = states / "Dsides" / (name + ".hx")
                path.parent.mkdir(exist_ok=True)
                path.write_text("function create() {}")
            (states / "AppTransitionMenu.hx").write_text("function create() {}")
            (base / "Main.hx").write_text('''
class Main {
 static function main():Void {
  var owner=Sys.args()[0];
  var merged=CodenameModCatalog.merge("",owner,"Owner",[
    "data/states/MainMenu.hx", "data/states/MusicBeatTransition.hx",
    "data/states/Dsides/StickerTransition.hx", "data/states/Dsides/noTrans.hx",
    "data/states/AppTransitionMenu.hx"]);
  if (!merged.valid || !merged.changed || merged.data.entries.length!=1) throw "initial catalog";
  var states=merged.data.entries[0].states.join(",");
  if (states!="data/states/AppTransitionMenu.hx,data/states/MainMenu.hx")
    throw "transition helpers exposed: " + states;
  var raw=CodenameModCatalog.stringify({version:1,entries:[
    {root:"assets/imported_mods/missing",label:"Missing",states:["data/states/Old.hx"]},
    {root:owner,label:"Owner",states:["data/states/MainMenu.hx", "data/states/Dsides/StickerTransition.hx"]}
  ]});
  var cleaned=CodenameModCatalog.merge(raw,owner,"Owner",[]);
  if (!cleaned.valid || !cleaned.changed || cleaned.data.entries.length!=1
      || cleaned.data.entries[0].states.join(",")!="data/states/MainMenu.hx")
    throw "stale catalog rows were not reconciled";
  if (!sys.FileSystem.exists(owner+"/data/states/Dsides/StickerTransition.hx"))
    throw "catalog cleanup removed owner file";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", "assets/imported_mods/owner"], cwd=base,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_catalog_retains_owner_with_only_global_scripts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "assets/imported_mods/global-only"
            global_script = owner / "data/global.hx"
            global_script.parent.mkdir(parents=True)
            global_script.write_text("function update(elapsed) {}")
            (base / "Main.hx").write_text('''
class Main {
 static function main():Void {
  var merged=CodenameModCatalog.merge("",Sys.args()[0],"Global only",[]);
  if (!merged.valid || !merged.changed || merged.data.entries.length!=1
      || merged.data.entries[0].states.length!=0) throw "global-only owner was omitted";
  var parsed=CodenameModCatalog.parse(CodenameModCatalog.stringify(merged.data));
  if (!parsed.valid || parsed.data.entries.length!=1 || parsed.data.entries[0].states.length!=0)
    throw "empty owner catalog entry did not round-trip";
  var switches=CodenameModSwitchPlan.fromCatalog(CodenameModCatalog.stringify(merged.data),"");
  if (!switches.valid || switches.entries.length!=2 || switches.entries[1].label!="Global only")
    throw "global-only owner missing from switch menu";
 }
}''')
            p = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", "assets/imported_mods/global-only"], cwd=base,
                               text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


if __name__ == "__main__":
    unittest.main()
