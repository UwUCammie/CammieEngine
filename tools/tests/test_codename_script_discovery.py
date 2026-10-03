"""Parse-free Codename companion discovery stays within the selected source root."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import json
import hashlib
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameScriptDiscoveryTest(unittest.TestCase):
    @unittest.skipIf(__import__("os").name == "nt", "fixture requires case-sensitive note type names")
    def test_selected_chart_note_types_resolve_same_owner_scripts_and_packs(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            notes = owner / "data/notes"
            notes.mkdir(parents=True)
            (notes / "Water.hx").write_text("hx has source precedence", newline='\n')
            (notes / "Water.hscript").write_text("lower priority source", newline='\n')
            (notes / "Packed.pack").write_text(
                "Packed.hx________PACKSEP________function noteHit(e) {}"
                "________PACKSEP________unused schema________PACKSEP________"
            , newline='\n')
            outside = base / "outside.hx"
            outside.write_text("foreign", newline='\n')
            try:
                (notes / "Escape.hx").symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var found=CodenameScriptDiscovery.discoverNoteTypesDetailed(root,
    ["Water", "water", "Packed", "NoScript", "Default Note", "Escape", "../unsafe"]);
  if(found.files.length!=2) throw haxe.Json.stringify(found);
  if(found.files[0].relative!="data/notes/Water.hx"
    || found.files[0].family!="note-type" || found.files[0].authoredId!="Water"
    || sys.io.File.getContent(found.files[0].path)!="hx has source precedence")
   throw "selected note script " + haxe.Json.stringify(found.files[0]);
  if(found.files[1].relative!="data/notes/Packed.hx"
    || found.files[1].family!="note-type"
    || found.files[1].embeddedScript!="function noteHit(e) {}")
   throw "packed note script " + haxe.Json.stringify(found.files[1]);
  if(found.diagnostics.length!=2
    || found.diagnostics[0].indexOf("Escape.hx escape")<0
    || found.diagnostics[1].indexOf("../unsafe")<0)
   throw "unsafe note paths were not diagnosed: " + found.diagnostics.join(";");
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_owner_character_inventory_includes_script_created_ids(self):
        self.assertIn("CodenameScriptDiscovery.discoverOwnerCharacterIds(root)",
                      (ROOT / "source/ModuleFunctions.hx").read_text())
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            defs = owner / "data/characters"
            defs.mkdir(parents=True)
            (defs / "chart.xml").write_text("<char/>", newline='\n')
            (defs / "scripted.xml").write_text("<char/>", newline='\n')
            (defs / "scripted.hx").write_text("// companion", newline='\n')
            (defs / "only-script.hx").write_text("// source class", newline='\n')
            foreign = base / "foreign.xml"
            foreign.write_text("<char/>", newline='\n')
            (defs / "escape.xml").symlink_to(foreign)
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var found=CodenameScriptDiscovery.discoverOwnerCharacterIds(root);
  if(found.ids.join(",")!="chart,only-script,scripted" || found.diagnostics.length!=0)
   throw haxe.Json.stringify(found);
  var discovered=CodenameScriptDiscovery.discoverCharactersDetailed(root,found.ids);
  var names=[for(file in discovered.files) file.relative];
  if(names.indexOf("data/characters/scripted.xml")<0
   || names.indexOf("data/characters/scripted.hx")<0)
   throw names.join(",");
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_owner_scoped_global_modules_states_and_song_hud(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            other = base / "other"
            files = {
                "data/global.hx": "global",
                "data/scripts/pause.hx": "pause",
                "data/scripts/nested/helper.hx": "helper",
                "data/states/Main.hx": "main",
                "data/states/credits.hx": "credits",
                "source/Bopper.hx": "class Bopper {}",
                "source/nested/Widget.hx": "class Widget {}",
                "songs/global-hud.hx": "shared song HUD",
                "songs/demo/hud.hx": "hud",
                "songs/other/hud.hx": "wrong song",
                "images/ignored.hx": "not a script tree",
            }
            for root in (owner, other):
                for relative, contents in files.items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(root.name + ":" + contents, newline='\n')
            escaped = base / "escaped.hx"
            escaped.write_text("foreign", newline='\n')
            (owner / "data/states/Escape.hx").symlink_to(escaped)
            (owner / "source/Escape.hx").symlink_to(escaped)
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var found=CodenameScriptDiscovery.discoverOwnerScriptsDetailed(root,"demo");
  var names=[for(file in found.files) file.relative];
  var expected=["data/global.hx","data/scripts/nested/helper.hx",
           "data/scripts/pause.hx","data/states/credits.hx","data/states/Main.hx",
   "source/Bopper.hx","source/nested/Widget.hx","songs/global-hud.hx",
   "songs/demo/hud.hx"];
  if(names.length!=expected.length) throw names.join(",");
  for(i in 0...expected.length) if(names[i]!=expected[i]) throw names.join(",");
  for(file in found.files) if(sys.io.File.getContent(file.path).indexOf("owner:")!=0)
    throw "cross-owner file " + file.relative;
  if(found.diagnostics.length!=0) throw found.diagnostics.join(",");
  if(CodenameScriptDiscovery.discoverOwnerScripts(root,"../other").length!=8)
    throw "unsafe song key selected HUD";
  var gameplay=CodenameScriptDiscovery.discover(root,"demo",[],null);
  if(gameplay.length!=2 || gameplay[0].relative!="songs/global-hud.hx"
    || gameplay[0].family!="global-song" || gameplay[1].relative!="songs/demo/hud.hx"
    || gameplay[1].family!="hud") throw haxe.Json.stringify(gameplay);
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_installation_script_layer_is_bounded_and_owner_first(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            installation = base / "installation"
            assets = installation / "assets"
            owner = installation / "mods/chosen"
            for relative, content in {
                "data/global.hx": "installation global",
                "data/scripts/pixel.hx": 'new CustomShader("pixelZoomShader");',
                "data/scripts/nested/helper.hx": "installation helper",
                "data/states/NotLaunchable.hx": "installation state",
                "shaders/pixelZoomShader.frag": "installation shader",
                "shaders/base-only.frag": "installation-only shader",
            }.items():
                path = assets / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            for relative, content in {
                "data/global.hx": "owner global",
                "data/scripts/pause.hx": "owner pause",
                "shaders/pixelZoomShader.frag": "owner shader",
                "shaders/escape.frag": "owner escape link",
            }.items():
                path = owner / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            outside = base / "outside.frag"
            outside.write_text("outside", newline='\n')
            try:
                (owner / "shaders/escape.frag").unlink()
                (owner / "shaders/escape.frag").symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            unrelated_assets = base / "unrelated/assets"
            (unrelated_assets / "shaders").mkdir(parents=True)
            (unrelated_assets / "shaders/foreign.frag").write_text("foreign", newline='\n')
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var owner=Sys.args()[0];
  var assets=Sys.args()[1];
  var unrelated=Sys.args()[2];
  var scripts=CodenameScriptDiscovery.discoverInstallationScriptsDetailed(assets);
  var paths=[for(file in scripts.files) file.relative];
  if(paths.join(",")!="data/global.hx,data/scripts/nested/helper.hx,data/scripts/pixel.hx")
    throw "shared script inventory="+paths.join(",");
  if(scripts.diagnostics.length!=0) throw scripts.diagnostics.join(";");
  var baseShader=CodenameInstallationAssetOverlay.resolve(owner,assets,"shaders/pixelZoomShader.frag");
  if(baseShader.origin!="owner" || !StringTools.endsWith(baseShader.source,"/mods/chosen/shaders/pixelZoomShader.frag"))
    throw "owner asset precedence="+haxe.Json.stringify(baseShader);
  var inherited=CodenameInstallationAssetOverlay.resolve(owner,assets,"shaders/base-only.frag");
  if(inherited.source==null || inherited.origin!="installation"
    || !StringTools.endsWith(inherited.source,"/assets/shaders/base-only.frag"))
    throw "base asset fallback="+haxe.Json.stringify(inherited);
  var escaped=CodenameInstallationAssetOverlay.resolve(owner,assets,"shaders/escape.frag");
  if(escaped.source!=null || escaped.status!="escape") throw "owner symlink escape fell through";
  var unrelatedFallback=CodenameInstallationAssetOverlay.resolve(owner,unrelated,"shaders/foreign.frag");
  if(unrelatedFallback.source!=null || unrelatedFallback.status!="missing")
    throw "unrelated assets root accepted";
  if(CodenameInstallationAssetOverlay.installationAssetsForOwner(owner)!=assets)
    throw "structural installation root not resolved";
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner), str(assets), str(unrelated_assets)],
                               cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_source_class_import_is_diagnosed_and_literal_method_assets_are_owner_scoped(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            bopper = owner / "source/Bopper.hx"
            bopper.parent.mkdir(parents=True)
            bopper.write_text('''class Bopper extends FlxSprite {
 public function new(x:Float,y:Float) super(x,y);
 public function setCharacter(char:String, ?animProperties:Array<Dynamic>) {
  frames = Paths.getSparrowAtlas(char);
  return this;
 }
}''', newline='\n')
            script = owner / "songs/demo/scripts/script.hx"
            script.parent.mkdir(parents=True)
            script.write_text('''import Bopper;
function create() {
 var prop = new Bopper(0, 0).setCharacter('characters/huggyteen/Banban');
 prop.setCharacter(runtimeCharacter);
}''', newline='\n')
            for suffix, content in (("png", "png"), ("xml", "xml")):
                atlas = owner / f"images/characters/huggyteen/Banban.{suffix}"
                atlas.parent.mkdir(parents=True, exist_ok=True)
                atlas.write_text(content, newline='\n')
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var found=CodenameScriptDiscovery.discoverOwnerScriptsDetailed(root,"demo");
  for(file in CodenameScriptDiscovery.discover(root,"demo",[],null)) found.files.push(file);
  var plan=CodenameClassScriptPlan.build(root,found.files);
  if(plan.dependencies.length!=1
   || plan.dependencies[0].kind!="sparrow"
   || plan.dependencies[0].key!="characters/huggyteen/Banban"
   || plan.dependencies[0].sourceClass!="source/Bopper.hx"
   || plan.dependencies[0].consumer!="songs/demo/scripts/script.hx")
    throw "class dependency plan " + haxe.Json.stringify(plan.dependencies)
     + " files=" + [for(file in found.files) file.relative+":"+file.family].join(",")
     + " diagnostics=" + plan.diagnostics.join(";");
  var staged=false, blocked=false, dynamicAsset=false;
  for(file in found.files) if(file.relative=="source/Bopper.hx" && file.family=="class") staged=true;
  for(message in plan.diagnostics) {
   if(message.indexOf("imports bopper from source/Bopper.hx")>=0
    && message.indexOf("cannot execute class declarations")>=0) blocked=true;
   if(message.indexOf("uses a non-literal asset key")>=0) dynamicAsset=true;
  }
  if(!staged || !blocked || !dynamicAsset) throw plan.diagnostics.join(";");
  var atlas=CodenameFrameAtlasAssets.plan(root,plan.dependencies[0].key);
  if(atlas.mode!="sparrow" || atlas.files.length!=2
    || atlas.files[0].relative!="images/characters/huggyteen/Banban.png"
    || atlas.files[1].relative!="images/characters/huggyteen/Banban.xml")
   throw "atlas assets were not resolved within the selected owner";
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_nested_character_xml_and_camera_identity(self):
        source = (ROOT / "source/ModuleFunctions.hx").read_text()
        start = source.index("\tstatic function findCodenameDefinitionXml(")
        brace = source.index("{", start)
        depth = 0
        end = brace
        for end in range(brace, len(source)):
            depth += (source[end] == "{") - (source[end] == "}")
            if depth == 0:
                break
        method = source[start:end + 1]
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            data = base / "owner/data"
            for relative in ("characters/team/Hero.xml", "characters/Room.xml",
                             "characters/room.xml"):
                path = data / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(relative, newline='\n')
            escaped = base / "escaped.xml"
            escaped.write_text("foreign", newline='\n')
            (data / "characters/Escape.xml").symlink_to(escaped)
            (base / "Main.hx").write_text('''import haxe.io.Path;
class Main {
''' + method + '''
 static function main():Void {
  var data=Sys.args()[0];
  var path=findCodenameDefinitionXml(data,"characters","TEAM/hero");
  if(path=="" || !StringTools.endsWith(path,"characters/team/Hero.xml")) throw "nested case lookup";
  if(findCodenameDefinitionXml(data,"characters","ROOM")!="") throw "ambiguous case lookup";
  if(findCodenameDefinitionXml(data,"characters","Escape")!="") throw "symlink escape";
  if(findCodenameDefinitionXml(data,"characters","../Escape")!="") throw "traversal";
  var id="team/Hero";
  var names:Dynamic={}; Reflect.setField(names,id,"native-hero");
  var entry:Dynamic={stage:"scene",lines:[{role:"player",type:1,position:null,
   visible:true,characters:[id]}],characters:{},nativeCharacters:names,
   stageOffsets:{},stageOffsetsKnown:true,missingCharacters:[id]};
  var plan=CodenameScriptPlan.createCamera("song",{hard:entry});
  if(plan.difficulties.hard.lines[0].characters[0]!=id
   || Reflect.field(plan.difficulties.hard.nativeCharacters,id)!="native-hero")
   throw "nested authored identity lost";
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(data)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_character_scripts_exact_nested_case_and_ownership(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner, other = base / "owner", base / "other"
            for root in (owner, other):
                for relative in (
                    "data/characters/Hero.hx", "data/characters/Hero.xml",
                    "data/characters/team/Voice.hx", "data/characters/team/Voice.xml",
                    "data/characters/Room.hx", "data/characters/room.hx",
                ):
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(root.name, newline='\n')
            outside = base / "outside.hx"
            outside.write_text("outside", newline='\n')
            (owner / "data/characters/Escape.hx").symlink_to(outside)
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var root=Sys.args()[0];
  var ids=["Hero","hero","team/Voice","TEAM/voice","Room","ROOM",
   "Escape","../outside","/Hero","team/../Voice","team\\\\Voice"];
  var files=CodenameScriptDiscovery.discoverCharacters(root,ids);
  var detailed=CodenameScriptDiscovery.discoverCharactersDetailed(root,ids);
  var names=[for(file in files) file.relative];
  if(names.join(",")!="data/characters/Hero.xml,data/characters/Hero.hx,"
   +"data/characters/hero.xml,data/characters/hero.hx,"
   +"data/characters/team/Voice.xml,data/characters/team/Voice.hx,"
   +"data/characters/TEAM/voice.xml,data/characters/TEAM/voice.hx,data/characters/Room.hx")
   throw names.join(",");
  for(file in files) if(sys.io.File.getContent(file.path)!="owner") throw "foreign owner";
  if(detailed.diagnostics.indexOf("Character ROOM.hx ambiguous")<0
   || detailed.diagnostics.indexOf("Character Escape.hx escape")<0
   || detailed.diagnostics.indexOf("Unsafe character ID: ../outside")<0)
   throw detailed.diagnostics.join(",");
  if(detailed.diagnostics.indexOf("Character Room.xml missing")<0)
   throw "missing XML diagnostic";
  if(!CodenameScriptDiscovery.safeRelativeName("team/Hero")
   || CodenameScriptDiscovery.safeRelativeName("team/../Hero")
   || CodenameScriptDiscovery.safeRelativeName("team//Hero")
   || CodenameScriptDiscovery.safeRelativeName("team\\\\Hero")) throw "unsafe relative id";
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_immediate_and_matching_difficulty_scripts_and_stage(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            other = base / "other"
            for root in (owner, other):
                for relative in (
                    "songs/demo/scripts/script.hx", "songs/demo/scripts/events.hx",
                    "songs/demo/scripts/hard/effect.hx", "songs/demo/scripts/easy/other.hx",
                    "data/stages/scene.hx",
                ):
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(root.name, newline='\n')
            escaped = base / "escaped.hx"
            escaped.write_text("outside", newline='\n')
            try:
                (owner / "songs/demo/scripts/escape.hx").symlink_to(escaped)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            (base / "Main.hx").write_text('''class Main {
  static function main() {
    var root = Sys.args()[0];
    var files = CodenameScriptDiscovery.discover(root, "demo", ["hard"], "scene");
    var names = [for (file in files) file.relative];
    if (names.length != 4 || names.indexOf("songs/demo/scripts/script.hx") < 0
        || names.indexOf("songs/demo/scripts/events.hx") < 0
        || names.indexOf("songs/demo/scripts/hard/effect.hx") < 0
        || names.indexOf("data/stages/scene.hx") < 0)
      throw names.join(",");
    if (names.indexOf("songs/demo/scripts/easy/other.hx") >= 0) throw "wrong difficulty";
    for (file in files) if (sys.io.File.getContent(file.path) != "owner") throw "wrong root";
    if (CodenameScriptDiscovery.discover(root, "../other", ["hard"], "../scene").length != 0)
      throw "unsafe name escaped root";
  }
}
''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_event_scripts_require_authored_name_and_upstream_schema_gate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            owner = base / "owner"
            other = base / "other"
            for root in (owner, other):
                for relative, content in {
                    "data/events/Custom Flash.hx": root.name,
                    "data/events/Custom Flash.json": '{"params":[]}',
                    "data/events/Camera Zoom.hx": root.name,
                    "data/events/No Schema.hx": root.name,
                    "data/events/Empty Schema.hx": root.name,
                    "data/events/Empty Schema.json": "",
                    "data/events/Uncharted.hx": root.name,
                    "data/events/Uncharted.json": '{"params":[]}',
                    "data/events/Packed Flash.pack": (
                        "Packed Flash.hx________PACKSEP________function onEvent(e) {}"
                        "________PACKSEP________{\"params\":[]}________PACKSEP________aWNvbg=="
                    ),
                    "data/events/Malformed.pack": (
                        "Malformed.hx________PACKSEP________function onEvent(e) {}"
                        "________PACKSEP________not-json"
                    ),
            }.items():
                    path = root / relative
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, newline='\n')
            outside = base / "outside.hx"
            outside.write_text("escape", newline='\n')
            (owner / "data/events/Escape.hx").symlink_to(outside)
            (owner / "data/events/Escape.json").write_text('{"params":[]}', newline='\n')
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var root=Sys.args()[0];
  if (!CodenameScriptDiscovery.isBuiltInEvent("Camera Zoom")
    || CodenameScriptDiscovery.isBuiltInEvent("Custom Flash")) throw "builtin registry";
  var names=["Custom Flash","Camera Zoom","No Schema","Empty Schema","Escape",
   "Uncharted/../Escape","Custom Flash","Packed Flash","Malformed"];
  var discovery=CodenameScriptDiscovery.discoverEventsDetailed(root,names);
  var files=discovery.files;
  var paths=[for(file in files) file.relative];
  if(paths.join(",")!="data/events/Camera Zoom.hx,data/events/Custom Flash.hx,data/events/Packed Flash.hx")
   throw paths.join(",");
  var packedSchema:Dynamic=haxe.Json.parse(files[2].embeddedSchema);
  if(files[2].family!="event-pack" || files[2].authoredId!="Packed Flash"
    || files[2].embeddedScript!="function onEvent(e) {}"
    || !Std.isOfType(Reflect.field(packedSchema,"params"),Array))
   throw "packed script/schema decode";
  if(discovery.diagnostics.length!=1
    || discovery.diagnostics[0].indexOf("Malformed.pack invalid-schema-json")<0)
   throw "malformed pack diagnostic: "+discovery.diagnostics.join(",");
  var schemas=CodenameScriptDiscovery.discoverEventSchemas(root,names);
  if(schemas.length!=2 || schemas[0].relative!="data/events/Custom Flash.json"
    || schemas[1].relative!="data/events/Packed Flash.pack")
   throw "schema selection";
  for(i in 0...files.length) if(i<2 && sys.io.File.getContent(files[i].path)!="owner") throw "foreign root";
  if(sys.io.File.getContent(schemas[1].path).indexOf("aWNvbg==")<0) throw "original pack not retained";
}
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "--run", "Main", str(owner)], cwd=ROOT, text=True,
                               capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_event_pack_decoder_and_runtime_callback(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            (base / "Main.hx").write_text('''class Main {
 static function main():Void {
  var sep=CodenameEventPack.SEPARATOR;
  var valid=CodenameEventPack.decode("Packed Event.hx"+sep+"function onEvent(e) {}"+sep+"{\\\"params\\\":[]}"+sep+"aWNvbg==", "packed event");
  if(valid.pack==null || valid.pack.eventName!="Packed Event"
    || valid.pack.script!="function onEvent(e) {}" || valid.pack.iconBase64!="aWNvbg==")
   throw "valid Codename pack rejected: "+valid.error;
  if(CodenameEventPack.decode("Other.hx"+sep+"x"+sep+"{}", "Packed Event").error!="event-name-mismatch")
   throw "name mismatch accepted";
  if(CodenameEventPack.decode("../Escape.hx"+sep+"x"+sep+"{}", "Escape").error!="unsafe-event-name")
   throw "unsafe event accepted";
  if(CodenameEventPack.decode("Bad.hx"+sep+"x"+sep+"not-json", "Bad").error!="invalid-schema-json")
   throw "bad schema accepted";
  if(CodenameEventPack.decode("Bad.hx"+sep+"x"+sep+"{\\\"params\\\":{}}", "Bad").error!="invalid-schema-params")
   throw "invalid params accepted";
  if(CodenameEventPack.decode("Bad.hx"+sep+"x", "Bad").error!="invalid-pack-sections")
   throw "truncated pack accepted";

  var executable=CodenameEventPack.decode("Runnable.hx"+sep+
    "function onEvent(e) { calls += e.delta; }"+sep+"{\\\"params\\\":[]}", "Runnable");
  var bindings:Map<String,Dynamic>=new Map();
  var prepared=CodenameScriptParser.prepare(executable.pack.script+"\\nonEvent({delta:2});",bindings,"packed-event-test");
  if(prepared.program==null || prepared.diagnostics.length!=0) throw "pack event script parse";
  var interp=new hscript.Interp();
  interp.variables.set("calls",0);
  interp.execute(prepared.program);
  if(interp.variables.get("calls")!=2) throw "pack event callback did not run: "+Std.string(interp.variables.get("calls"));

  var unsupported=CodenameEventPack.decode("Unsupported.hx"+sep+
    "import hxvlc.flixel.FlxVideoSprite; function onEvent(e) {}"+sep+"{\\\"params\\\":[]}", "Unsupported");
  var rejected=CodenameScriptParser.prepare(unsupported.pack.script,bindings,"packed-event-unsupported");
  if(rejected.program!=null || rejected.diagnostics.length==0
    || rejected.diagnostics[0].code!="unsupported-import")
   throw "unsupported import must remain explicit";
 }
}''', newline='\n')
            p = subprocess.run([*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                                "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                                "-cp", str(ROOT / ".haxelib/hscript-ex/git/src"),
                                "--run", "Main"], cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_importer_wires_copy_and_repair_to_same_file_plan(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        self.assertIn("var runtimeFiles = codenameRuntimeFiles(songData);", module)
        self.assertIn("var expected = codenameRuntimeFiles(songData);", module)
        self.assertIn("mergeCodenameRuntimeAssets(songData)", module)
        self.assertIn("Reflect.setField(songData, 'codenameStageSource', stageReference)", module)
        self.assertIn("CodenameScriptDiscovery.discover(root, song, difficulties, stage)", module)
        self.assertIn("Reflect.setField(songData, 'codenameAuthoredStages', authoredStages)", module)
        self.assertIn("CodenameScriptPlan.metadataPath(namespace, song)", module)

    def test_scoped_copy_nonoverwrite_and_repair_of_literal_dependencies(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        def method(marker):
            start = module.index(marker)
            brace = module.index("{\n", start)
            depth = 0
            for index in range(brace, len(module)):
                depth += (module[index] == "{") - (module[index] == "}")
                if depth == 0:
                    return module[start:index + 1]
            raise AssertionError(marker)
        methods = "\n".join(method("static function " + name) for name in (
            "codenameAuthoredEventNames", "codenameScriptFiles", "codenameSafeAssetKey", "codenameRuntimeFiles",
            "codenameMetadataStagesMatch", "codenameNoteTypesByDifficulty",
            "writeCodenameNoteTypePlanIfMissing", "reconcileCodenameOwnerMetadata",
            "mergeCodenameRuntimeAssets", "copyImportFileNonOverwriting",
            "writeImportContentNonOverwriting",
            "compatScriptManifestNeedsRepair", "importOwnerDisplayLabel"))
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            base = Path(work)
            installation = base / "installation"
            owner = installation / "mods/fnas"
            for relative, content in {
                "songs/demo/scripts/script.hx": 'var card = Paths.image("game/card"); var atlas = Paths.image("game/animated"); var escape = Paths.image("game/escape"); Paths.font("face.ttf"); Paths.json("timing"); Paths.video("clip"); Paths.obj("plane"); CoolUtil.playMenuSFX(); Paths.sound("local"); Assets.getPath(Paths.file("videos/raw.mp4")); var label = new FlxText().setFormat("fonts/Technology.ttf", 28); label.font = "./fonts/851MkPOP.ttf"; var shader = new CustomShader("spark"); function onNoteCreation(e) if (e.strumLineID == 0) e.noteSprite = "hud/oppNOTE"; function onStrumCreation(e) if (e.player == 0) e.sprite = "hud/oppNOTE";',
                # D-Sides keeps this selector in an immediate songs/*.hx file.
                # The importer must follow it and stage the selected helper too.
                "songs/stickerTransition.hx": 'MusicBeatTransition.script = "data/stickerTransition.hx"; function onGamePause(e) {}',
                "songs/demo/scripts/events.hx": "function stepHit(s) { iconP2.setIcon('zephmoldy', false); }",
                "songs/demo/scripts/hard/hard.hx": "function create() {}",
                "songs/demo/scripts/easy/easy.hx": "function create() {}",
                "songs/demo/lyrics.json": '{"stuff":[]}',
                "songs/demo/hud.hx": "function postCreate() {}",
                "songs/other/hud.hx": "function postCreate() {}",
                "data/global.hx": 'function preStateSwitch() { CoolUtil.playMenuSong("opening"); }',
                "data/scripts/pause.hx": "function create(event) {}",
                "data/stickerTransition.hx": 'Paths.getFolderDirectories("sounds/stickersounds/", true); function create(event) {}',
                "data/states/Main.hx": "CoolUtil.playMenuSong(); var sonic = Paths.getFrames('main/sonic'); function create() {}",
                "data/states/PlayState.hx": "var lastHealth = health; function create() { scripts.set('camHuggy', camHUD); } function postCreate() { for (i in 0...4) Paths.image('hud/damage/' + i); }",
                "data/stages/Scene.hx": "function create() {}",
                "data/stages/Other.hx": "function create() {}",
                "data/stickerpacks/default.json": (
                    '{"name":"Default","artist":"D-Sides",'
                    '"stickers":["stickers/default/a","stickers/default/b"]}'
                ),
                "data/stickerpacks/alternate.json": (
                    '{"name":"Alternate","stickers":["stickers/alternate/c"]}'
                ),
                "images/game/card.png": "owner image",
                "images/hud/oppNOTE.png": "owner opponent note atlas",
                "images/hud/oppNOTE.xml": "owner opponent note frames",
                "images/icons/zephmoldy/icon.png": "owner direct icon",
                "images/hud/damage/0.png": "damage zero",
                "images/hud/damage/1.png": "damage one",
                "images/hud/damage/2.png": "damage two",
                "images/hud/damage/3.png": "damage three",
                "images/hud/damage/readme.txt": "not an image",
                "images/game/score/epic.png": "owner score epic",
                "images/game/score/num0.png": "owner score zero",
                "images/game/score/num1.png": "owner score one",
                "images/game/score/num2.png": "owner score two",
                "images/game/score/num3.png": "owner score three",
                "images/game/score/num4.png": "owner score four",
                "images/game/score/num5.png": "owner score five",
                "images/game/score/num6.png": "owner score six",
                "images/game/score/num7.png": "owner score seven",
                "images/game/score/num8.png": "owner score eight",
                "images/game/score/num9.png": "owner score nine",
                "images/game/animated/Animation.json": "{}",
                "images/game/animated/spritemap1.json": "{}",
                "images/game/animated/spritemap1.png": "owner Animate page",
                "fonts/face.ttf": "owner font",
                "fonts/Technology.ttf": "owner direct text format font",
                "fonts/851MkPOP.ttf": "owner direct font property",
                "data/timing.json": "owner timing",
                "videos/clip.mp4": "real owner video bytes",
                "videos/raw.mp4": "raw owner video bytes",
                "models/plane.obj": "o owner plane\n",
                "shaders/spark.frag": "#pragma header\n#import <base/postprocess.frag>\nvoid main() {}\n",
                "shaders/spark.vert": "owner vertex shader source\n",
                "shaders/base/postprocess.frag": "#import <shared/coords.glsl>\nuniform vec4 uCameraBounds;\n",
                "shaders/shared/coords.glsl": "vec2 screenCoord;\n",
                "music/freakyMenu.ogg": "owner default menu track bytes",
                "music/opening.ogg": "owner named menu track bytes",
                "sounds/local.wav": "owner local wav bytes",
                "sounds/stickersounds/keys/pop.ogg": "owner enumerated sound bytes",
                "images/main/sonic.png": "owner FNAS sprite image",
                "images/main/sonic.xml": "owner FNAS sprite frames",
                "images/stickers/default/a.png": "owner default sticker A",
                "images/stickers/default/b.png": "owner default sticker B",
                "images/stickers/alternate/c.png": "owner alternate sticker C",
                "data/events/Custom Flash.hx": 'var card = Paths.image("game/event-card"); function onEvent(e) {}',
                "data/events/Custom Flash.json": '{"params":[]}',
                "data/events/Packed Flash.pack": (
                    "Packed Flash.hx________PACKSEP________function onEvent(e) {}"
                    "________PACKSEP________{\"params\":[]}________PACKSEP________aWNvbg=="
                ),
                "data/events/Uncharted.hx": "function onEvent(e) {}",
                "data/events/Uncharted.json": '{"params":[]}',
                "images/game/event-card.png": "event image",
                "data/characters/Actor.hx": 'var badge = Paths.image("characters/actor-badge");',
                "data/characters/Actor.xml": '<character name="Actor"/>',
                "data/notes/Authored Note.hx": "function noteHit(event) {}",
                "images/characters/actor-badge.png": "character image",
                "images/characters/Actor.png": "source actor atlas",
                "images/characters/Actor.xml": "source actor frames",
                "images/game/notes/Authored Note.png": "authored note atlas",
                "images/game/notes/Authored Note.xml": "authored note frames",
                "images/game/notes/Atlas Only.png": "atlas-only note atlas",
                "images/game/notes/Atlas Only.xml": "atlas-only note frames",
                # Owner Haxe classes can make the same dynamic image-folder
                # calls as HScript modules. Keep those finite direct children
                # in the selected-owner import plan too.
                "source/MenuWindow.hx": '''class MenuWindow {
 public function changeSelection() {
  var graphic = Paths.image("songSelect/" + selectedSong.pointer);
 }
}''',
                "images/songSelect/first.png": "first song portrait",
                "images/songSelect/second.png": "second song portrait",
            }.items():
                path = owner / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, newline='\n')
            installation_sound = installation / "assets/sounds/menu/scroll.ogg"
            installation_sound.parent.mkdir(parents=True, exist_ok=True)
            installation_sound.write_bytes(b"installation menu scroll bytes")
            installation_score = installation / "assets/images/game/score/foreign.png"
            installation_score.parent.mkdir(parents=True, exist_ok=True)
            installation_score.write_bytes(b"foreign installation score image")
            installation_default_atlas = installation / "assets/images/game/notes/default.png"
            installation_default_atlas.parent.mkdir(parents=True, exist_ok=True)
            installation_default_atlas.write_bytes(b"installation default note atlas")
            (installation_default_atlas.parent / "default.xml").write_bytes(
                b"installation default note frames"
            )
            installation_icon = installation / "assets/images/icons/zephmoldy/icon.png"
            installation_icon.parent.mkdir(parents=True, exist_ok=True)
            installation_icon.write_bytes(b"foreign icon must not shadow owner")
            installation_local_ogg = installation / "assets/sounds/local.ogg"
            installation_local_ogg.parent.mkdir(parents=True, exist_ok=True)
            installation_local_ogg.write_bytes(b"installation local ogg must not shadow owner wav")
            shared_scripts = installation / "assets/data/scripts"
            shared_scripts.mkdir(parents=True, exist_ok=True)
            (shared_scripts / "pixel.hx").write_text(
                'var pixelShader = new CustomShader("pixelZoomShader");'
            , newline='\n')
            (shared_scripts / "pause.hx").write_text("base pause must not shadow owner", newline='\n')
            shared_global = installation / "assets/data/global.hx"
            shared_global.parent.mkdir(parents=True, exist_ok=True)
            shared_global.write_text("base global must not shadow owner", newline='\n')
            shared_state = installation / "assets/data/states/NotAnOwnerState.hx"
            shared_state.parent.mkdir(parents=True, exist_ok=True)
            shared_state.write_text("function create() {}", newline='\n')
            pixel_shader = installation / "assets/shaders/pixelZoomShader.frag"
            pixel_shader.parent.mkdir(parents=True, exist_ok=True)
            pixel_shader.write_text("#import <pixel/coords.glsl>\nvoid main() {}\n", newline='\n')
            pixel_shader_include = installation / "assets/shaders/pixel/coords.glsl"
            pixel_shader_include.parent.mkdir(parents=True, exist_ok=True)
            pixel_shader_include.write_text("vec2 sharedCoord;\n", newline='\n')
            outside = base / "outside.png"
            outside.write_text("outside image", newline='\n')
            try:
                (owner / "images/game/escape.png").symlink_to(outside)
                (owner / "sounds/stickersounds/keys/foreign.ogg").symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink fixture unavailable: {error}")
            (base / "Main.hx").write_text('''import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import CodenameScriptDiscovery.CodenameScriptFile;
import CompatScriptManifest.CompatScriptManifestData;
using StringTools;
typedef SongImport = { var name:String; var engine:String; var sourceRoot:String;
  var vSliceRoot:String; var sourceFolder:String; var codenameStageSource:String;
  @:optional var codenameEngineBaseAssetRoot:String;
  var codenameAuthoredStages:Dynamic; var codenameAuthoredCamera:Dynamic;
  @:optional var diagnostics:Array<String>;
  var codenameOriginalMeta:Dynamic;
  var codenameResolvedMeta:Dynamic;
  var convertedCharts:Array<Dynamic>;
  @:optional var sourceModName:String;
  @:optional var importSourceInfo:SongImportSource; };
typedef SongImportSource = { var song:String; var data:String; var destination:String;
  @:optional var sourceRoot:String; @:optional var engine:String; };
typedef ImportAssetMergeResult = { var copied:Int; var skipped:Int; var failed:Int;
  @:optional var errors:Array<String>; };
class ImportEngine {
  public static inline var CODENAME = "Codename Engine";
  public static inline var NIGHTMARE_VISION = "Nightmare Vision";
}
class CodenameImporter {
  public static function resolveAsset(root:String, relative:String):String {
    var path = Path.join([root, relative]);
    return FileSystem.exists(path) ? path : "";
  }
}
class Main {
  static function importWorkCancelled():Bool return false;
  static function importPathKey(path:String):String return Path.normalize(FileSystem.fullPath(path));
  static function ensureDirectory(path:String):Void {
    if (path == null || path == "" || FileSystem.exists(path)) return;
    ensureDirectory(Path.directory(path)); FileSystem.createDirectory(path);
  }
  static function isImportFile(path:String):Bool return path != null && FileSystem.exists(path) && !FileSystem.isDirectory(path);
  static function compatScriptManifestPath(_song:SongImport):String return "assets/data/demo/compatScripts.json";
  static function sourceHasCompatScriptTree(_root:String, _engine:String):Bool return false;
  static function compatScriptNamespaceHasExpectedFiles(_root:String, _dest:String, _engine:String):Bool return false;
  static function hasCompatScriptFile(_root:String, _depth:Int = 0,
      _includeHaxe:Bool = false):Bool return false;
'''+methods+'''
  static function main():Void {
    var owner = Sys.args()[0];
    var eventRow:Array<Dynamic> = ["Custom Flash", "", "", ""];
    eventRow.push(CodenameEventMetadata.create("Custom Flash", 125,
      ([true, 4.5]:Array<Dynamic>), "chart", 0, false, eventRow));
    var packedRow:Array<Dynamic> = ["Packed Flash", "", "", ""];
    packedRow.push(CodenameEventMetadata.create("Packed Flash", 125,
      ([]:Array<Dynamic>), "chart", 1, false, packedRow));
    var eventGroups:Array<Dynamic> = [[125, [eventRow, packedRow]]];
    var song:SongImport = {name:"demo", engine:ImportEngine.CODENAME, sourceRoot:owner,
      vSliceRoot:owner, sourceFolder:"demo", codenameStageSource:"scene",
      codenameEngineBaseAssetRoot:Path.join([Path.directory(Path.directory(owner)),"assets"]),
      codenameAuthoredStages:{hard:"other"},
      codenameOriginalMeta:{name:"demo",displayName:"Demo Display",customValues:{chapter:3}},
      codenameResolvedMeta:CodenameSongMetadata.createResolved("demo",["hard"],
        {hard:{selectedFile:"meta.json",fileMeta:{name:"demo",displayName:"Demo Display"},
          inlineMeta:null}}),
      codenameAuthoredCamera:{hard:{stage:"other",lines:[
        {role:"opponent",type:0,position:"dad",visible:true,characters:["Actor"]}],
        characters:{Actor:{globalX:2,globalY:3,cameraX:4,cameraY:5,
          centeredCamera:null,playerOffsets:false}},missingCharacters:[],
        stageOffsets:{dad:{cameraX:6,cameraY:7}},stageOffsetsKnown:true,
        stageStartCamera:{x:0,y:250}}},
      convertedCharts:[{difficulty:"hard",noteTypes:["Authored Note","Atlas Only"],
        chart:{song:{events:eventGroups,codenameNoteTypes:["Authored Note","Atlas Only"]}}}]};
    var merged = mergeCodenameRuntimeAssets(song);
    if (merged.failed != 0 || merged.copied != 87) throw "copy count " + merged.copied + "/" + merged.failed;
    var ns = CompatScriptManifest.destinationRoot(owner, song.engine);
    var defaultImage = Path.join([ns, "images/game/notes/default.png"]);
    var defaultFrames = Path.join([ns, "images/game/notes/default.xml"]);
    if (File.getContent(defaultImage) != "installation default note atlas"
        || File.getContent(defaultFrames) != "installation default note frames")
      throw "installation default note/receptor atlas was not materialized";
    var plannedDefaultImage = "";
    for (runtimeFile in codenameRuntimeFiles(song))
      if (runtimeFile.relative == "images/game/notes/default.png") plannedDefaultImage = runtimeFile.source;
    if (plannedDefaultImage != Path.join([Path.directory(Path.directory(owner)),
        "assets/images/game/notes/default.png"]))
      throw "default atlas did not use selected installation fallback: " + plannedDefaultImage;
    File.saveContent(Path.join([owner, "images/game/notes/default.png"]), "owner default atlas");
    File.saveContent(Path.join([owner, "images/game/notes/default.xml"]), "owner default frames");
    plannedDefaultImage = "";
    for (runtimeFile in codenameRuntimeFiles(song))
      if (runtimeFile.relative == "images/game/notes/default.png") plannedDefaultImage = runtimeFile.source;
    if (plannedDefaultImage != Path.join([owner, "images/game/notes/default.png"]))
      throw "selected owner default atlas did not take precedence: " + plannedDefaultImage;
    var script = Path.join([ns, "songs/demo/scripts/script.hx"]);
    for (relative in ["songs/stickerTransition.hx", "data/global.hx", "data/scripts/pause.hx", "data/stickerTransition.hx", "data/states/Main.hx", "data/states/PlayState.hx",
      "songs/demo/hud.hx"])
      if (!isImportFile(Path.join([ns, relative]))) throw "owner script not staged: " + relative;
    if (isImportFile(Path.join([ns, "songs/other/hud.hx"]))) throw "wrong song HUD staged";
    var image = Path.join([ns, "images/game/card.png"]);
    var opponentNoteImage = Path.join([ns, "images/hud/oppNOTE.png"]);
    var opponentNoteFrames = Path.join([ns, "images/hud/oppNOTE.xml"]);
    if (File.getContent(opponentNoteImage) != "owner opponent note atlas"
        || File.getContent(opponentNoteFrames) != "owner opponent note frames")
      throw "literal note and strum creation sprite dependencies were not staged";
    if (File.getContent(Path.join([ns, "images/icons/zephmoldy/icon.png"])) != "owner direct icon")
      throw "direct setIcon dependency was not staged from its selected owner";
    var importedGameplayState = Path.join([ns, "data/states/PlayState.hx"]);
    if (File.getContent(importedGameplayState).indexOf("var lastHealth = health") < 0
        || File.getContent(importedGameplayState).indexOf("function create()") < 0
        || File.getContent(importedGameplayState).indexOf("function postCreate()") < 0)
      throw "gameplay state companion path or lifecycle was not staged";
    for (number in 0...4)
      if (File.getContent(Path.join([ns, "images/hud/damage/" + number + ".png"]))
          != "damage " + ["zero", "one", "two", "three"][number])
        throw "dynamic image asset " + number;
    if (File.getContent(Path.join([ns, "images/songSelect/first.png"])) != "first song portrait"
        || File.getContent(Path.join([ns, "images/songSelect/second.png"])) != "second song portrait")
      throw "dynamic image assets from owner class source";
    if (File.getContent(Path.join([ns, "fonts/face.ttf"])) != "owner font"
        || File.getContent(Path.join([ns, "fonts/Technology.ttf"])) != "owner direct text format font"
        || File.getContent(Path.join([ns, "fonts/851MkPOP.ttf"])) != "owner direct font property"
        || File.getContent(Path.join([ns, "data/timing.json"])) != "owner timing") throw "data dependencies";
    var scopedVideo = Path.join([ns, "videos/clip.mp4"]);
    var rawVideo = Path.join([ns, "videos/raw.mp4"]);
    var scopedModel = Path.join([ns, "models/plane.obj"]);
    var shader = Path.join([ns, "shaders/spark.frag"]);
    var shaderVertex = Path.join([ns, "shaders/spark.vert"]);
    var shaderInclude = Path.join([ns, "shaders/base/postprocess.frag"]);
    var installationPixelShader = Path.join([ns, "shaders/pixelZoomShader.frag"]);
    var installationPixelShaderInclude = Path.join([ns, "shaders/pixel/coords.glsl"]);
    var shaderNestedInclude = Path.join([ns, "shaders/shared/coords.glsl"]);
    var defaultMenuMusic = Path.join([ns, "music/freakyMenu.ogg"]);
    var namedMenuMusic = Path.join([ns, "music/opening.ogg"]);
    var frameImage = Path.join([ns, "images/main/sonic.png"]);
    var frameXml = Path.join([ns, "images/main/sonic.xml"]);
    var defaultSticker = Path.join([ns, "images/stickers/default/a.png"]);
    var alternateSticker = Path.join([ns, "images/stickers/alternate/c.png"]);
    var installationSound = Path.join([ns, "sounds/menu/scroll.ogg"]);
    var ownerSound = Path.join([ns, "sounds/local.wav"]);
    var enumeratedSound = Path.join([ns, "sounds/stickersounds/keys/pop.ogg"]);
    if (File.getContent(scopedVideo) != "real owner video bytes"
        || File.getContent(rawVideo) != "raw owner video bytes"
        || File.getContent(scopedModel) != "o owner plane\n"
        || File.getContent(shader).indexOf("#import <base/postprocess.frag>") < 0
        || File.getContent(shaderVertex) != "owner vertex shader source\n"
        || File.getContent(shaderInclude).indexOf("#import <shared/coords.glsl>") < 0
        || File.getContent(installationPixelShader).indexOf("#import <pixel/coords.glsl>") < 0
        || File.getContent(installationPixelShaderInclude) != "vec2 sharedCoord;\\n"
        || File.getContent(shaderNestedInclude) != "vec2 screenCoord;\n"
        || File.getContent(defaultMenuMusic) != "owner default menu track bytes"
        || File.getContent(namedMenuMusic) != "owner named menu track bytes"
        || File.getContent(defaultSticker) != "owner default sticker A"
        || File.getContent(Path.join([ns, "images/stickers/default/b.png"])) != "owner default sticker B"
        || File.getContent(alternateSticker) != "owner alternate sticker C"
        || File.getContent(Path.join([ns, "images/game/score/epic.png"])) != "owner score epic"
        || File.getContent(Path.join([ns, "images/game/score/num0.png"])) != "owner score zero"
        || File.getContent(Path.join([ns, "data/stickerpacks/default.json"])).indexOf("D-Sides") < 0
        || !isImportFile(Path.join([ns, "data/stickerpacks/alternate.json"]))
        || File.getContent(installationSound) != "installation menu scroll bytes"
        || File.getContent(ownerSound) != "owner local wav bytes"
        || File.getContent(enumeratedSound) != "owner enumerated sound bytes"
        || isImportFile(Path.join([ns, "sounds/stickersounds/keys/foreign.ogg"]))
        || isImportFile(Path.join([ns, "sounds/local.ogg"]))
        || File.getContent(frameImage) != "owner FNAS sprite image"
        || File.getContent(frameXml) != "owner FNAS sprite frames") throw "video/shader/frame/menu dependencies";
    for (number in 0...10)
      if (File.getContent(Path.join([ns, "images/game/score/num" + number + ".png"]))
          != "owner score " + ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][number])
        throw "dynamic score asset num" + number;
    var hard = Path.join([ns, "songs/demo/scripts/hard/hard.hx"]);
    var easy = Path.join([ns, "songs/demo/scripts/easy/easy.hx"]);
    var stage = Path.join([ns, "data/stages/Scene.hx"]);
    var otherStage = Path.join([ns, "data/stages/Other.hx"]);
    var customEvent = Path.join([ns, "data/events/Custom Flash.hx"]);
    var customSchema = Path.join([ns, "data/events/Custom Flash.json"]);
    var packedEvent = Path.join([ns, "data/events/Packed Flash.hx"]);
    var packedPackage = Path.join([ns, "data/events/Packed Flash.pack"]);
    var eventImage = Path.join([ns, "images/game/event-card.png"]);
    var actorScript = Path.join([ns, "data/characters/Actor.hx"]);
    var actorXml = Path.join([ns, "data/characters/Actor.xml"]);
    var actorImage = Path.join([ns, "images/characters/actor-badge.png"]);
    var actorAtlas = Path.join([ns, "images/characters/Actor.png"]);
    var actorFrames = Path.join([ns, "images/characters/Actor.xml"]);
    var noteScript = Path.join([ns, "data/notes/Authored Note.hx"]);
    var noteAtlas = Path.join([ns, "images/game/notes/Authored Note.png"]);
    var noteFrames = Path.join([ns, "images/game/notes/Authored Note.xml"]);
    var atlasOnlyNote = Path.join([ns, "images/game/notes/Atlas Only.png"]);
    var atlasOnlyFrames = Path.join([ns, "images/game/notes/Atlas Only.xml"]);
    var planPath = CodenameScriptPlan.metadataPath(ns, "demo");
    var cameraPath = CodenameScriptPlan.cameraMetadataPath(ns, "demo");
    var noteTypesPath = CodenameScriptPlan.noteTypesMetadataPath(ns, "demo");
    var songMetaPath = CodenameSongMetadata.path(ns, "demo");
    var resolvedMetaPath = CodenameSongMetadata.resolvedPath(ns, "demo");
    if (!isImportFile(script) || !isImportFile(image)
        || !isImportFile(defaultSticker) || !isImportFile(alternateSticker)
        || File.getContent(Path.join([ns, "songs/demo/lyrics.json"])) != '{"stuff":[]}'
        || !isImportFile(Path.join([ns, "images/game/animated/Animation.json"]))
        || !isImportFile(Path.join([ns, "images/game/animated/spritemap1.json"]))
        || !isImportFile(Path.join([ns, "images/game/animated/spritemap1.png"]))
        || !isImportFile(hard) || !isImportFile(stage)
        || !isImportFile(otherStage) || !isImportFile(planPath) || !isImportFile(cameraPath)
        || !isImportFile(noteTypesPath)
        || !isImportFile(songMetaPath) || !isImportFile(resolvedMetaPath)
        || !isImportFile(customEvent) || !isImportFile(customSchema) || !isImportFile(eventImage)
        || !isImportFile(packedEvent) || !isImportFile(packedPackage)
        || !isImportFile(actorScript) || !isImportFile(actorXml) || !isImportFile(actorImage)
        || !isImportFile(actorAtlas) || !isImportFile(actorFrames)
        || File.getContent(noteScript) != "function noteHit(event) {}"
        || File.getContent(noteAtlas) != "authored note atlas"
        || File.getContent(noteFrames) != "authored note frames"
        || File.getContent(atlasOnlyNote) != "atlas-only note atlas"
        || File.getContent(atlasOnlyFrames) != "atlas-only note frames"
        || !isImportFile(Path.join([ns, "data/scripts/pixel.hx"]))
        || isImportFile(Path.join([ns, "data/states/NotAnOwnerState.hx"]))
        || File.getContent(Path.join([ns, "data/scripts/pause.hx"])) != "function create(event) {}"
        || File.getContent(Path.join([ns, "data/global.hx"]))
            != 'function preStateSwitch() { CoolUtil.playMenuSong("opening"); }'
        || isImportFile(Path.join([ns, "data/events/Uncharted.hx"]))
        || isImportFile(easy) || isImportFile("assets/images/game/card.png")
        || isImportFile(Path.join([ns, "images/game/score/foreign.png"]))
        || isImportFile(Path.join([ns, "images/game/escape.png"]))
        || isImportFile(Path.join([ns, "images/hud/damage/readme.txt"]))) throw "scoped selection";
    if (File.getContent(packedEvent)!="function onEvent(e) {}"
        || File.getContent(packedPackage).indexOf("aWNvbg==")<0) throw "packed source staging";
    var runtimeEvents=CodenameScriptDiscovery.discoverEvents(ns,["Packed Flash"]);
    if (runtimeEvents.length!=1 || runtimeEvents[0].family!="event"
        || File.getContent(runtimeEvents[0].path)!="function onEvent(e) {}")
      throw "staged pack did not enter selected-owner runtime discovery";
    var plan = CodenameScriptPlan.parse(File.getContent(planPath));
    if (plan.song != "demo" || CodenameScriptPlan.selectedStage(plan, "hard") != "other")
      throw "authored stage missing";
    var camera = CodenameScriptPlan.selectedCamera(
      CodenameScriptPlan.parseCamera(File.getContent(cameraPath)), "hard");
    if (camera == null || camera.stage != "other" || camera.lines[0].characters[0] != "Actor"
        || camera.characters.Actor.cameraX != 4 || camera.characters.Actor.playerOffsets != false
        || camera.stageOffsets.dad.cameraY != 7 || camera.stageStartCamera.y != 250)
      throw "authored camera missing";
    var generatedPlan = File.getContent(planPath);
    var generatedCamera = File.getContent(cameraPath);
    var generatedNoteTypes = File.getContent(noteTypesPath);
    if (CodenameScriptPlan.selectedNoteTypes(
        CodenameScriptPlan.parseNoteTypes(generatedNoteTypes), "hard").join("|")
        != "Authored Note|Atlas Only") throw "authored note type metadata missing";
    var songMeta = CodenameSongMetadata.parse(File.getContent(songMetaPath), "demo");
    if (songMeta.meta.displayName != "Demo Display" || songMeta.meta.customValues.chapter != 3)
      throw "original song meta missing";
    if (CodenameSongMetadata.selectedResolved(CodenameSongMetadata.parseResolved(
        File.getContent(resolvedMetaPath),"demo"),"hard").name != "demo")
      throw "resolved song meta missing";
    var manifestPath = compatScriptManifestPath(song);
    ensureDirectory(Path.directory(manifestPath));
    File.saveContent(manifestPath, CompatScriptManifest.stringify(CompatScriptManifest.create(owner, song.engine)));
    if (compatScriptManifestNeedsRepair(song)) throw "complete namespace needs repair";
    File.saveContent(script, "custom edit");
    for (relative in ["songs/stickerTransition.hx", "data/global.hx", "data/scripts/pause.hx", "data/stickerTransition.hx", "data/states/Main.hx", "data/states/PlayState.hx",
      "songs/demo/hud.hx"])
      File.saveContent(Path.join([ns, relative]), "custom owner script: " + relative);
    File.saveContent(actorScript, "custom character script");
    File.saveContent(actorXml, "custom character XML");
    File.saveContent(customEvent, "custom event edit");
    File.saveContent(packedEvent, "custom packed event edit");
    File.saveContent(packedPackage, "custom packed package edit");
    File.saveContent(planPath, "custom metadata");
    File.saveContent(cameraPath, "custom camera metadata");
    File.saveContent(noteTypesPath, "custom note type metadata");
    File.saveContent(songMetaPath, "custom song meta");
    File.saveContent(resolvedMetaPath, "custom resolved meta");
    File.saveContent(installationSound, "custom scoped audio edit");
    File.saveContent(defaultSticker, "custom sticker image edit");
    var scoreEpic = Path.join([ns, "images/game/score/epic.png"]);
    File.saveContent(scoreEpic, "custom score image edit");
    mergeCodenameRuntimeAssets(song);
    var customDestinations:Array<{name:String,path:String,content:String}> = [
      {name:"song script",path:script,content:"custom edit"},
      {name:"global script",path:Path.join([ns, "data/global.hx"]),content:"custom owner script: data/global.hx"},
      {name:"transition selector",path:Path.join([ns, "songs/stickerTransition.hx"]),content:"custom owner script: songs/stickerTransition.hx"},
      {name:"pause script",path:Path.join([ns, "data/scripts/pause.hx"]),content:"custom owner script: data/scripts/pause.hx"},
      {name:"transition helper",path:Path.join([ns, "data/stickerTransition.hx"]),content:"custom owner script: data/stickerTransition.hx"},
      {name:"main state",path:Path.join([ns, "data/states/Main.hx"]),content:"custom owner script: data/states/Main.hx"},
      {name:"song HUD",path:Path.join([ns, "songs/demo/hud.hx"]),content:"custom owner script: songs/demo/hud.hx"},
      {name:"character script",path:actorScript,content:"custom character script"},
      {name:"character XML",path:actorXml,content:"custom character XML"},
      {name:"event script",path:customEvent,content:"custom event edit"},
      {name:"packed event script",path:packedEvent,content:"custom packed event edit"},
      {name:"packed event package",path:packedPackage,content:"custom packed package edit"},
      // These generated owner sidecars are a paired import product. Existing
      // authored copies must survive refresh together, even when stale.
      {name:"script metadata",path:planPath,content:"custom metadata"},
      {name:"camera metadata",path:cameraPath,content:"custom camera metadata"},
      {name:"note type metadata",path:noteTypesPath,content:"custom note type metadata"},
      {name:"song metadata",path:songMetaPath,content:"custom song meta"},
      {name:"resolved song metadata",path:resolvedMetaPath,content:"custom resolved meta"},
      {name:"sticker image",path:defaultSticker,content:"custom sticker image edit"},
      {name:"score image",path:scoreEpic,content:"custom score image edit"},
      {name:"installation audio",path:installationSound,content:"custom scoped audio edit"}
    ];
    var changedDestinations:Array<String> = [];
    for (destination in customDestinations)
      if (File.getContent(destination.path) != destination.content)
        changedDestinations.push(destination.name + " (" + destination.path + ")");
    if (changedDestinations.length != 0)
      throw "overwrote custom destination(s): " + changedDestinations.join(", ");
    // The custom-byte preservation case above intentionally leaves a stale,
    // unparsable metadata pair. Restore the generated pair before the later
    // missing-file repair cases, which verify recovery from a coherent pair.
    File.saveContent(planPath, generatedPlan);
    File.saveContent(cameraPath, generatedCamera);
    File.saveContent(noteTypesPath, generatedNoteTypes);
    File.saveContent(installationSound, "installation menu scroll bytes");
    FileSystem.deleteFile(image);
    FileSystem.deleteFile(defaultSticker);
    var scoreNumber = Path.join([ns, "images/game/score/num0.png"]);
    FileSystem.deleteFile(scoreNumber);
    var damageZero = Path.join([ns, "images/hud/damage/0.png"]);
    FileSystem.deleteFile(damageZero);
    if (!compatScriptManifestNeedsRepair(song)) throw "missing dependency not repaired";
    mergeCodenameRuntimeAssets(song);
    if (compatScriptManifestNeedsRepair(song) || File.getContent(image) != "owner image"
        || File.getContent(defaultSticker) != "owner default sticker A"
        || File.getContent(scoreNumber) != "owner score zero"
        || File.getContent(damageZero) != "damage zero") throw "repair failed";
    for (path in [scopedVideo, rawVideo, shader, shaderInclude, shaderNestedInclude,
        installationPixelShader, installationPixelShaderInclude,
        Path.join([ns, "songs/demo/lyrics.json"]),
        defaultMenuMusic, namedMenuMusic, shaderVertex, frameImage, frameXml,
        installationSound, ownerSound, enumeratedSound, opponentNoteImage, opponentNoteFrames]) {
      var bytes = File.getContent(path);
      FileSystem.deleteFile(path);
      if (!compatScriptManifestNeedsRepair(song)) throw "missing video/shader needs repair";
      mergeCodenameRuntimeAssets(song);
      if (File.getContent(path) != bytes || compatScriptManifestNeedsRepair(song))
        throw "video/shader repair failed: " + path;
    }
    for (relative in ["songs/stickerTransition.hx", "data/global.hx", "data/scripts/pause.hx", "data/scripts/pixel.hx", "data/stickerTransition.hx", "data/states/Main.hx", "data/states/PlayState.hx",
      "songs/demo/hud.hx"]) {
      var ownerScript = Path.join([ns, relative]);
      FileSystem.deleteFile(ownerScript);
      if (!compatScriptManifestNeedsRepair(song)) throw "missing owner script not detected: " + relative;
      mergeCodenameRuntimeAssets(song);
      var repairedScript = File.getContent(ownerScript);
      var scriptWasRepaired = relative == "data/scripts/pixel.hx"
        ? repairedScript.indexOf('CustomShader("pixelZoomShader")') >= 0
        : repairedScript.indexOf("function ") >= 0;
      if (!scriptWasRepaired
          || compatScriptManifestNeedsRepair(song)) throw "owner script repair failed: " + relative;
    }
    FileSystem.deleteFile(actorXml);
    if (!compatScriptManifestNeedsRepair(song)) throw "character XML needs repair";
    mergeCodenameRuntimeAssets(song);
    if (File.getContent(actorXml) != '<character name="Actor"/>'
        || File.getContent(actorScript) != "custom character script") throw "scoped character repair";
    FileSystem.deleteFile(customSchema);
    if (!compatScriptManifestNeedsRepair(song)) throw "event schema needs repair";
    mergeCodenameRuntimeAssets(song);
    if (File.getContent(customSchema) != '{"params":[]}') throw "event schema repair failed";
    FileSystem.deleteFile(packedEvent);
    if (!compatScriptManifestNeedsRepair(song)) throw "packed event script needs repair";
    mergeCodenameRuntimeAssets(song);
    if (File.getContent(packedEvent) != "function onEvent(e) {}"
        || !isImportFile(packedPackage)) throw "packed event script repair failed";
    FileSystem.deleteFile(planPath);
    if (!compatScriptManifestNeedsRepair(song)) throw "metadata needs repair";
    mergeCodenameRuntimeAssets(song);
    if (CodenameScriptPlan.selectedStage(CodenameScriptPlan.parse(File.getContent(planPath)), "hard") != "other")
      throw "metadata repair failed";
    FileSystem.deleteFile(cameraPath);
    if (!compatScriptManifestNeedsRepair(song)) throw "camera metadata needs repair";
    mergeCodenameRuntimeAssets(song);
    camera = CodenameScriptPlan.selectedCamera(
      CodenameScriptPlan.parseCamera(File.getContent(cameraPath)), "hard");
    if (camera == null || camera.stageStartCamera.x != 0 || camera.characters.Actor.globalY != 3
        || compatScriptManifestNeedsRepair(song)) throw "camera metadata repair failed";
    FileSystem.deleteFile(songMetaPath);
    // This additive sidecar is repaired by the complete-song skipped branch;
    // it must not force importSong to revisit an existing native chart.
    if (compatScriptManifestNeedsRepair(song)) throw "song meta repair would reimport chart";
    mergeCodenameRuntimeAssets(song);
    if (CodenameSongMetadata.parse(File.getContent(songMetaPath), "demo").meta.customValues.chapter != 3)
      throw "song meta repair failed";
    FileSystem.deleteFile(resolvedMetaPath);
    mergeCodenameRuntimeAssets(song);
    if (CodenameSongMetadata.selectedResolved(CodenameSongMetadata.parseResolved(
        File.getContent(resolvedMetaPath),"demo"),"hard").name != "demo")
      throw "resolved meta repair failed";
    FileSystem.deleteFile(Path.join([owner, "images/game/notes/default.png"]));
    FileSystem.deleteFile(Path.join([owner, "images/game/notes/default.xml"]));
    var animatedDefault = Path.join([owner, "images/game/notes/default"]);
    FileSystem.createDirectory(animatedDefault);
    File.saveContent(Path.join([animatedDefault, "Animation.json"]), "{} ");
    File.saveContent(Path.join([animatedDefault, "spritemap1.png"]), "owner animated atlas page");
    var animatedPlan = codenameRuntimeFiles(song);
    var sawManifest = false;
    var sawPage = false;
    for (runtimeFile in animatedPlan) {
      if (runtimeFile.relative == "images/game/notes/default/Animation.json") sawManifest = true;
      if (runtimeFile.relative == "images/game/notes/default/spritemap1.png") sawPage = true;
    }
    if (!sawManifest || !sawPage)
      throw "Animate default atlas folder was not staged without base PNG/XML: " + sawManifest + "/" + sawPage;
    if (song.diagnostics != null)
      for (diagnostic in song.diagnostics)
        if (diagnostic.indexOf("Codename default note/receptor atlas") >= 0)
          throw "Animate default atlas incorrectly required base PNG/XML: " + diagnostic;
    if (Sys.args().length > 1) {
      var donorRoot = Sys.args()[1];
      var donorImportRoot = Path.directory(Path.directory(donorRoot));
      var donorSong:SongImport = {name:"D-Sides REDUX", engine:ImportEngine.CODENAME,
        sourceRoot:donorImportRoot, vSliceRoot:donorRoot, sourceFolder:"", codenameStageSource:"",
        codenameAuthoredStages:{}, codenameAuthoredCamera:{}, codenameOriginalMeta:{},
        codenameResolvedMeta:{}, convertedCharts:[]};
      var atlasFiles:Array<{source:String,relative:String}> = [];
      for (file in codenameRuntimeFiles(donorSong))
        if (file.relative == "images/game/notes/default.png"
            || file.relative == "images/game/notes/default.xml")
          atlasFiles.push({source:file.source,relative:file.relative});
      Sys.println("DEFAULT_ATLAS_IMPORT_PREVIEW=" + haxe.Json.stringify({
        sourceRoot:donorImportRoot,
        ownerRoot:donorRoot,
        destinationRoot:CompatScriptManifest.destinationRoot(donorImportRoot, donorSong.engine),
        files:atlasFiles}));
    }
  }
}
''', newline='\n')
            donor_root = (ROOT.parent / "FNF-Example-Mods/codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX")
            args = [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(base),
                    "--run", "Main", str(owner)]
            if donor_root.is_dir():
                args.append(str(donor_root))
            p = subprocess.run(args, cwd=base, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            if donor_root.is_dir():
                preview_line = next((line for line in p.stdout.splitlines()
                                     if line.startswith("DEFAULT_ATLAS_IMPORT_PREVIEW=")), None)
                self.assertIsNotNone(preview_line, p.stdout)
                preview = json.loads(preview_line.split("=", 1)[1])
                self.assertEqual(len(preview["files"]), 2, preview)
                self.assertEqual({item["relative"] for item in preview["files"]},
                                 {"images/game/notes/default.png", "images/game/notes/default.xml"})
                for item in preview["files"]:
                    source = Path(item["source"])
                    self.assertTrue(source.is_file(), item)
                    item["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
                receipt = ROOT / "tmp/codename-default-atlas-import-preview-20260930.json"
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text(json.dumps(preview, indent=2) + "\n", newline='\n')
