"""Execute icon metadata selection with independent menu and gameplay owners."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method

from tools.tests.test_psych_character_scope import extract_method

ROOT = Path(__file__).resolve().parents[2]


class HealthIconOwnerTest(unittest.TestCase):
    def test_gameplay_icon_uses_chart_storage_owner_and_menu_icons_stay_isolated(self):
        source = (ROOT / "source/HealthIcon.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "static function characterOwnerRoot(",
            "static function ownerRootForIcon(",
        ))
        fixture = r'''class ImportEngine {
 public static inline var V_SLICE="V-Slice";
}
class PlayState {
 public static var SONG:Dynamic={compatStorageFolder:"selected-chart-folder",song:"display-title"};
}
class Song {
 public static var requested:Array<String>=[];
 public static function storageFolder(chart:Dynamic):String return chart.compatStorageFolder;
 public static function characterRootForSong(song:String,?engine:String):String {
  requested.push(song+":"+(engine==null?"":engine));
  if(song=="selected-chart-folder" && engine==ImportEngine.V_SLICE)
   return "assets/imported_mods/selected-owner";
  if(song=="freeplay-row" && engine==ImportEngine.V_SLICE)
   return "assets/imported_mods/menu-owner";
  return "";
 }
}
class Main {
''' + methods + r'''
 static function check(ok:Bool,why:String):Void if(!ok)throw why;
 static function main():Void {
  check(ownerRootForIcon(null,true)=="assets/imported_mods/selected-owner",
   "normal gameplay icon did not bind to the chart's selected V-Slice owner");
  check(Song.requested.indexOf("selected-chart-folder:V-Slice")>=0
   && Song.requested.join(",").indexOf("display-title")==-1,
   "owner lookup used the global title instead of chart storage/provenance");
  check(ownerRootForIcon(null,false)==null,
   "unowned menu icon changed its existing active-owner behavior");
  check(ownerRootForIcon("freeplay-row",false)=="assets/imported_mods/menu-owner",
   "explicit Freeplay owner stopped selecting its own V-Slice root");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch) / "Main.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", scratch, "-main", "Main", "--interp"],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        play_state = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("new HealthIcon(SONG.player1, true, true)", play_state)
        self.assertIn("new HealthIcon(SONG.player2, false, true)", play_state)
        self.assertIn("iconOwnerRoot = ownerRootForIcon(ownerSong, isnormal)", source)

    def test_missing_icon_diagnostics_include_only_a_valid_selected_owner(self):
        source = (ROOT / "source/EngineCompat.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "public static function visualDependencySearchPaths(",
            "static function safeVisualOwnerRoot(",
        ))
        fixture = "using StringTools;\nclass CompatScriptManifest { " \
            "public static inline var ROOT_PREFIX='assets/imported_mods'; }\n" \
            "class Main {\n" + methods + r'''
 static function check(ok:Bool,why:String):Void if(!ok)throw why;
 static function main():Void {
  var paths=visualDependencySearchPaths("health-icon","our-harmony",
   "assets/imported_mods/v-slice-ddto-owner");
  check(paths[0]=="assets/imported_mods/v-slice-ddto-owner/images/custom_chars/our-harmony/icons.png",
   "diagnostic omitted the selected owner's character icon path");
  check(paths.indexOf("assets/imported_mods/v-slice-ddto-owner/images/icons/icon-our-harmony.png")>=0,
   "diagnostic omitted the selected owner's direct icon path");
  var invalid=visualDependencySearchPaths("health-icon","our-harmony","../foreign");
  for(path in invalid)
   if(path.indexOf("assets/imported_mods/")==0) throw "unsafe owner appeared in diagnostic paths";
  var invalidId=visualDependencySearchPaths("health-icon","../other",
   "assets/imported_mods/v-slice-ddto-owner");
  for(path in invalidId)
   if(path.indexOf("assets/imported_mods/")==0) throw "unsafe icon id appeared in owner paths";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch) / "Main.hx"
            path.write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", scratch, "-main", "Main", "--interp"],
                cwd=ROOT, text=True, capture_output=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        health_icon = (ROOT / "source/HealthIcon.hx").read_text()
        self.assertIn("iconRequest.ownerRoot == null", health_icon)

    def test_vslice_authored_icon_animation_uses_live_auto_update_gate(self):
        source = (ROOT / "source/HealthIcon.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "public function getCurrentAnimation(",
            "public function playAnimation(",
        ))
        fixture = '''class Anim {
 public var name:String;
 public function new(name:String) this.name=name;
}
class Controller {
 public var curAnim:Anim=new Anim("icon");
 public function new() {}
 public function exists(name:String):Bool return name=="icon" || name=="Depressed";
 public function play(name:String, restart:Bool=false):Void curAnim=new Anim(name);
}
class Main {
 public var animation:Controller=new Controller();
 public var autoUpdate:Bool=true;
 public function new() {}
''' + methods + '''
 static function main():Void {
  var icon=new Main();
  if(icon.getCurrentAnimation("Depressed")) throw "wrong initial animation";
  icon.playAnimation("Depressed");
  icon.autoUpdate=false;
  if(!icon.getCurrentAnimation("Depressed") || icon.getCurrentAnimation()!= "Depressed")
   throw "authored animation was not retained";
  icon.playAnimation("missing");
  if(icon.getCurrentAnimation()!= "Depressed") throw "missing animation replaced authored state";
  icon.autoUpdate=true;
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(path),
                                     "-main", "Main", "--interp"], cwd=ROOT,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        play = (ROOT / "source/PlayState.hx").read_text()
        self.assertIn("if (iconP2auto && iconP2.autoUpdate)", play)
        self.assertIn("if (iconP2.autoUpdate) iconP2.iconState = Winning;", play)

    def test_configured_hxc_placeholder_cancels_only_its_unresolved_fallback(self):
        source = (ROOT / "source/HealthIcon.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "function clearDeferredIconDiagnostic(",
            "function handleMissingIconDiagnostic(",
            "function reportDeferredIconDiagnostic(",
        ))
        fixture = '''class EngineCompat {
 public static var reports:Array<Dynamic> = [];
 public static function reportVisualFallback(plan:Dynamic):String {
  reports.push(plan); return "reported";
 }
}
class Main {
 var deferMissingIconDiagnostic:Bool = false;
 var deferredMissingIconDiagnostic:Dynamic = null;
 public function new() {}
''' + methods + '''
 static function check(ok:Bool, why:String):Void if (!ok) throw why;
 static function main():Void {
  var icon = new Main();
  icon.deferMissingIconDiagnostic = true;
  icon.handleMissingIconDiagnostic({id:"extra"});
  check(EngineCompat.reports.length == 0, "HXC placeholder was reported during construction");
  icon.clearDeferredIconDiagnostic(); // configure() selected its authored icon before the first frame
  icon.reportDeferredIconDiagnostic();
  check(EngineCompat.reports.length == 0, "configured HXC icon retained the placeholder diagnostic");

  icon.handleMissingIconDiagnostic({id:"unresolved-configured-icon"});
  icon.reportDeferredIconDiagnostic();
  check(EngineCompat.reports.length == 1
   && EngineCompat.reports[0].id == "unresolved-configured-icon",
   "still-missing HXC icon was not reported on its first update");

  var nativeIcon = new Main();
  nativeIcon.handleMissingIconDiagnostic({id:"native-missing-icon"});
  check(EngineCompat.reports.length == 2
   && EngineCompat.reports[1].id == "native-missing-icon",
   "native missing-icon diagnostics stopped being immediate");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(path),
                                     "-main", "Main", "--interp"], cwd=ROOT,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        self.assertIn("clearDeferredIconDiagnostic();", source)
        self.assertIn("reportDeferredIconDiagnostic();", source)
        adapter = (ROOT / "source/HxcHealthIconAdapter.hx").read_text()
        self.assertIn("ownerSong, true", adapter)

    def test_codename_set_icon_changes_the_existing_health_icon(self):
        source = (ROOT / "source/HealthIcon.hx").read_text()
        start = source.index("public function setIcon(")
        method = source[start:source.index(";", start) + 1]
        fixture = '''class Main {
 public var current:String = "before";
 public function new() {}
 public function switchAnim(name:String):Dynamic { current = name; return this; }
''' + method + '''
 static function main():Void {
  var icon = new Main();
  if (icon.setIcon("gf") != icon || icon.current != "gf")
   throw "Codename setIcon did not update the existing HUD icon";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(path),
                                     "--run", "Main"], cwd=ROOT, text=True,
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_wacky_health_icons_resolve_with_authored_case(self):
        registry = ROOT / "export/release/linux/bin/assets/images/custom_chars/custom_chars.jsonc"
        if not registry.is_file():
            self.skipTest("mounted imported character registry unavailable")
        source = (ROOT / "source/HealthIcon.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "static function iconRegistryKey", "static function globalIconRegistryKey"))
        fixture = r'''
class Main {
 static var charJson:Dynamic;
 static var iconJson:Dynamic={};
''' + methods + r'''
 static function main():Void {
  var root=Sys.args()[0];
  charJson=haxe.Json.parse(sys.io.File.getContent(root+"/assets/images/custom_chars/custom_chars.jsonc"));
  for(id in ["Pomni","Caine","WackyCaine","WackyPomni"]) {
   var key=globalIconRegistryKey(id);
   if(key==null || key!=id.toLowerCase()) throw "wrong registry key for "+id+": "+key;
   if(!sys.FileSystem.exists(root+"/assets/images/custom_chars/"+key+"/icons.png"))
    throw "matching donor icon missing for "+id;
  }
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(path),
                                     "--run", "Main", str(registry.parents[3])],
                                    cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_menu_owner_is_independent_of_active_gameplay_owner(self):
        source = (ROOT / "source/HealthIcon.hx").read_text()
        methods = "\n".join(extract_method(source, marker) for marker in (
            "static function getIconFromJsons", "static function iconRegistryKey",
            "static function globalIconRegistryKey", "static function getIconJson"))
        fixture = r'''typedef IconData={var json:Dynamic;var path:String;var assetRoot:String;};
class Song {
 public static var current="assets/imported_mods/B";
 public static var owners:Map<String,Dynamic>=[
  "assets/imported_mods/A"=>{bf:{icons:[0],color:"A"},alias:{icons:"bf"}},
  "assets/imported_mods/B"=>{bf:{icons:[0],color:"B"}}
 ];
 public static function currentCharacterRoot():String return current;
 public static function characterVisualRegistryEntryInManifest(name:String,root:String):Dynamic
  return owners.exists(root)?Reflect.field(owners.get(root),name):null;
}
class Main {
 static var missingIconReference="";
 static var charJson:Dynamic={bf:{icons:[0],color:"native"},
  wackycaine:{icons:[0],color:"red"},wackypomni:{icons:[0],color:"blue"},
  aliascase:{icons:"WackyCaine"}};
 static var iconJson:Dynamic={};
''' + methods + r'''
 static function check(ok:Bool,why:String):Void if(!ok)throw why;
 static function main():Void {
  var first=getIconFromJsons("bf","assets/imported_mods/A");
  var second=getIconFromJsons("bf","assets/imported_mods/B");
  check(first.json.color=="A" && second.json.color=="B","same-name menu rows shared an owner");
  check(first.assetRoot=="assets/imported_mods/A/images/custom_chars/","menu icon used active B assets");
  var alias=getIconFromJsons("alias","assets/imported_mods/A");
  check(alias.path=="bf" && alias.json.color=="A","alias escaped menu owner");
  check(getIconFromJsons("bf").json.color=="B","gameplay default lost active owner");
  check(getIconFromJsons("bf","").json.color=="native","unowned menu inherited active gameplay scope");
  var mixed=getIconFromJsons("WackyCaine","");
  check(mixed.path=="wackycaine" && mixed.json.color=="red",
   "mixed-case icon did not use matching on-disk character folder");
  var aliasCase=getIconFromJsons("AliasCase","");
  check(aliasCase.path=="wackycaine" && aliasCase.json.color=="red",
   "mixed-case icon alias did not resolve the donor-backed folder");
  Song.current="assets/imported_mods/A";
  check(getIconFromJsons("bf","assets/imported_mods/B").json.color=="B","explicit owner changed with state");
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as scratch:
            path = Path(scratch)
            (path / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", str(path), "--run", "Main"],
                                    cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
