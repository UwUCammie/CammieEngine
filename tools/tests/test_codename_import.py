"""Codename Engine import-family coverage.

Covers classification (source mods and compiled releases), the pure
meta.json/charts converter, the XML character/stage converters, discovery into
the native SongImport payload, and the real bully-mod donor (skipped gracefully
when the mounted donor is absent).
"""

from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONORS = Path("/run/media/cammie/External Storage/FNF-Example-Mods")
BULLY = DONORS / "codename/bully-mod"
HL17 = DONORS / "codename/hl17_v3"
FNAS = DONORS / "fnas_after_hours"
DSIDES_BLAMMED = DONORS / "codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/songs/blammed/charts"
DSIDES_SONGS = DONORS / "codename/D-Sides REDUX Codename Engine (Cancelled)/mods/D-Sides REDUX/songs"


def haxe_string(value: str) -> str:
    return json.dumps(str(value))


def extract_method(source: str, marker: str) -> str:
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated method: {marker}")


class CodenameImportTest(unittest.TestCase):
    def run_fixture(self, main_source: str, extra_cps=None, files=None, args=None) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            temp_path = Path(folder)
            for name, content in (files or {}).items():
                target = temp_path / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            (temp_path / "Main.hx").write_text(main_source)
            # The fixture class path comes last so fixture stubs shadow the real
            # repo modules (including its flixel Main.hx).  --run interprets the
            # module and forwards the remaining arguments to Sys.args().
            command = [str(HAXE), "-cp", str(ROOT / "source")]
            for cp in extra_cps or []:
                command += ["-cp", str(cp)]
            command += ["-cp", str(temp_path), "--run", "Main"] + [str(a) for a in (args or [])]
            return subprocess.run(command, cwd=ROOT, capture_output=True, text=True)

    # ------------------------------------------------------------------
    # Pure converter units
    # ------------------------------------------------------------------

    def test_nested_authored_character_default_atlas(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            root = Path(work)
            atlas = root / "images/characters/team/Hero"
            atlas.parent.mkdir(parents=True)
            atlas.with_suffix(".png").write_text("png")
            atlas.with_suffix(".xml").write_text("<TextureAtlas/>")
            main = f'''class Main {{
 static function main():Void {{
  var converted=CodenameImporter.parseCharacterXml(
   '<character name="Hero"><anim name="idle" anim="Idle"/></character>',
   {haxe_string(str(root))}, "native-hero", false, null, "fixture", "team/Hero");
  if(converted.name!="native-hero" || converted.assets.length!=2
   || !StringTools.endsWith(converted.assets[0].source,"images/characters/team/Hero.png"))
   throw "authored nested default sprite not used";
 }}
}}'''
            result = self.run_fixture(main)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_atlas_formats_and_nested_installation_icons(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            package = Path(work)
            root = package / "mods/D-Sides"
            animate = root / "images/characters/BF/BF_assets"
            pages = root / "images/characters/BF/retros"
            unique = root / "images/characters/spooky"
            case_variant = root / "images/characters/GF"
            for folder in (animate, pages, unique, case_variant,
                           root / "images/icons/mod-id", root / "images/icons/gf",
                           package / "assets/images/icons/base-id"):
                folder.mkdir(parents=True, exist_ok=True)
            (animate / "Animation.json").write_text('{"AN":{"SD":["spritemap1"]}}')
            (animate / "spritemap1.json").write_text('{"ATFD":[]}')
            (animate / "spritemap1.png").write_bytes(b"animate page")
            for page in (1, 2):
                (pages / f"{page}.png").write_bytes(f"page {page}".encode())
                (pages / f"{page}.xml").write_text("<TextureAtlas/>")
            (unique / "lilasheet.png").write_bytes(b"unique")
            (unique / "lilasheet.xml").write_text("<TextureAtlas/>")
            (case_variant / "Grunt_GF.png").write_bytes(b"case")
            (case_variant / "Grunt_GF.xml").write_text("<TextureAtlas/>")
            (root / "images/icons/mod-id/icon.png").write_bytes(b"mod icon")
            (root / "images/icons/gf/icon.png").write_bytes(b"nested gf icon")
            (package / "assets/images/icons/base-id/icon.png").write_bytes(b"base icon")

            main = f'''import sys.FileSystem;
class Main {{
 static function check(ok:Bool,message:String):Void if(!ok)throw message;
 static function hasAsset(result:Dynamic,destination:String):Bool {{
  for(asset in (cast result.assets:Array<Dynamic>)) if(asset.destination==destination)return true;
  return false;
 }}
 static function hasDiagnostic(result:Dynamic,code:String):Bool {{
  for(diagnostic in (cast result.diagnostics:Array<Dynamic>)) if(diagnostic.code==code)return true;
  return false;
 }}
 static function main():Void {{
  var root={haxe_string(str(root))};
  var animate=CodenameImporter.parseCharacterXml(
   '<character sprite="BF/BF_assets"><anim name="idle" anim="Boyfriend/BFIdle"/></character>',
   root,"bf-assets",true,null,"fixture","BF/BF_assets");
  var animateFiles:Array<String>=[for(file in CodenameImporter.characterAtlasFiles(root,"BF/BF_assets")) file.relative];
  check(animate.registryEntry.codenameCharacter.animateAtlas==true,"Animate atlas not detected");
  check(animateFiles.indexOf("Animation.json")>=0 && animateFiles.indexOf("spritemap1.json")>=0
   && animateFiles.indexOf("spritemap1.png")>=0,"Animate dependency set incomplete: "+animateFiles.join("|"));
  check(hasAsset(animate,"char/Animation.json") && hasAsset(animate,"char/spritemap1.png"),"Animate files not emitted");
  check(animate.hscript.indexOf("char.loadTextureAtlas(hscriptPath + 'char');")>=0
   && animate.hscript.indexOf("char.animation.addBySymbol(\\\"idle\\\", \\\"Boyfriend/BFIdle\\\"")>=0,
   "Animate symbol adapter missing: "+animate.hscript);

  var paged=CodenameImporter.parseCharacterXml(
   '<character sprite="BF/retros"><anim name="idle" anim="RetrosIdle"/></character>',
   root,"retros",true,null,"fixture","BF/retros");
  check(paged.registryEntry.codenameCharacter.animateAtlas==false
   && hasAsset(paged,"char/1.png") && hasAsset(paged,"char/2.xml"),"numbered Sparrow pages missing");
  check(paged.hscript.indexOf("char.frames.addAtlas(FlxAtlasFrames.fromSparrow")>=0
   && paged.hscript.indexOf("char/2.png")>=0,"numbered Sparrow pages were not merged");

  var fallback=CodenameImporter.parseCharacterXml(
   '<character sprite="lilasheet"><anim name="idle" anim="Idle"/></character>',
   root,"lilasheet",true,null,"fixture","lilasheet");
  check(!hasDiagnostic(fallback,"missing-character-asset") && hasAsset(fallback,"char.png")
   && hasAsset(fallback,"char.xml"),"unique nested basename was not resolved: files="
   +CodenameImporter.characterAtlasFiles(root,"lilasheet").length+" diagnostics="
   +[for(d in (cast fallback.diagnostics:Array<Dynamic>)) d.code+":"+d.message].join("|"));
  var folded=CodenameImporter.characterAtlasFiles(root,"gf/Grunt_GF");
  check(folded.length==2,"case-insensitive atlas lookup failed");

  var nested=CodenameImporter.parseCharacterXml('<character icon="gf"/>',root,"nested",true);
  var base=CodenameImporter.parseCharacterXml('<character icon="base-id"/>',root,"base",true);
  var absent=CodenameImporter.parseCharacterXml('<character icon="arrows"/>',root,"absent",true);
  check(hasAsset(nested,"icons.png") && nested.assets[nested.assets.length-1].source.indexOf("images/icons/gf/icon.png")>=0,
   "nested mod icon was not used");
  check(hasAsset(base,"icons.png") && base.assets[base.assets.length-1].source.indexOf("assets/images/icons/base-id/icon.png")>=0,
   "installation base icon was not used");
  check(hasDiagnostic(absent,"missing-health-icon"),"true missing icon was hidden");
 }}
}}'''
            result = self.run_fixture(main)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DSIDES_SONGS.is_dir(), "mounted D-Sides donor unavailable")
    def test_d_sides_character_atlas_inventory_has_no_unresolved_atlases(self):
        main = '''import haxe.io.Path;
import sys.FileSystem;
using StringTools;
class Main {
 static function fail(value:String):Void throw value;
 static function main():Void {
  var root=Sys.args()[0];var characterRoot=root+"/data/characters";
  var total=0,animate=0,paged=0,unique=0;
  var missingIcons:Array<String>=[];
  for(file in FileSystem.readDirectory(characterRoot)) {
   if(!file.toLowerCase().endsWith(".xml"))continue;
   var definition=Path.join([characterRoot,file]);
   var authored=Path.withoutExtension(file);
   var result=CodenameImporter.convertCharacterXml(definition,root,authored,true);
   total++;
   var metadata:Dynamic=result.registryEntry.codenameCharacter;
   if(metadata.animateAtlas==true)animate++;
   var sprite=Xml.parse(sys.io.File.getContent(definition)).firstElement().get("sprite");
   if(sprite==null || sprite=="")sprite=authored;
   var files:Array<Dynamic>=CodenameImporter.characterAtlasFiles(root,sprite);
   if(files.length>0 && files[0].relative=="1.png")paged++;
   if(Path.withoutDirectory(sprite).toLowerCase()=="lilasheet")unique++;
   for(diagnostic in result.diagnostics) {
    if(diagnostic.code=="missing-character-asset")
     fail("unresolved atlas: "+authored+" sprite="+sprite);
    if(diagnostic.code=="missing-health-icon") {
     if(diagnostic.message.indexOf("arrows")>=0)missingIcons.push("arrows");
     else if(diagnostic.message.indexOf("gfgrunt")>=0)missingIcons.push("gfgrunt");
     else fail("unexpected missing icon: "+diagnostic.message);
    }
   }
  }
  if(total!=51 || animate!=22 || paged!=1 || unique!=1)
   fail("character format coverage changed: total="+total+" animate="+animate+" pages="+paged+" unique="+unique);
  missingIcons.sort(Reflect.compare);
  if(missingIcons.join(",")!="arrows,gfgrunt")fail("unexpected missing icon set: "+missingIcons.join(","));
 }
}'''
        result = self.run_fixture(main, args=[DSIDES_SONGS.parent])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_meta_and_chart_shape_guards(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    // Codename meta always carries difficulties + bpm + stepsPerBeat.
    if (!CodenameImporter.isCodenameMeta(haxe.Json.parse('{"difficulties":["hard"],"bpm":98,"stepsPerBeat":4}')))
      fail("codename meta rejected");
    // A loose meta.json marker must not collide with FPS Plus metadata.
    if (CodenameImporter.isCodenameMeta(haxe.Json.parse('{"description":"FPS Plus","bpm":100}')))
      fail("fps-plus style meta accepted");
    if (CodenameImporter.isCodenameMeta(haxe.Json.parse('{"difficulties":[],"bpm":0,"stepsPerBeat":4}')))
      fail("zero-bpm meta accepted");
    if (!CodenameImporter.isCodenameChart(haxe.Json.parse('{"codenameChart":true}')))
      fail("codenameChart flag rejected");
    if (!CodenameImporter.isCodenameChart(haxe.Json.parse('{"chartVersion":"1.6.0","strumLines":[]}')))
      fail("legacy chart shape rejected");
    if (CodenameImporter.isCodenameChart(haxe.Json.parse('{"notes":{}}')))
      fail("foreign chart accepted");
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_embedded_section_chart_conversion_preserves_authored_rows(self):
        main = '''class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  var original:Dynamic = haxe.Json.parse('{"song":{"player1":"hero","player2":"villain","gfVersion":"gf-custom","bpm":125,"events":[[0,[["Hey!","","year"]]]],"notes":[{"sectionBeats":3,"mustHitSection":false,"changeBPM":true,"bpm":150,"sectionNotes":[[100,4,250,"GunshotNote",true]]}]}}');
  if (!CodenameImporter.isEmbeddedSectionChart(original)) fail('section shape rejected');
  var shared:Dynamic = haxe.Json.parse('{"events":[{"time":200,"name":"Unknown Authored Event","params":["x"]}]}');
  var converted = CodenameImporter.convertEmbeddedSectionChart(original, 'expert', shared);
  var song:Dynamic = converted.chart.song;
  if (converted.difficulty != 'expert' || song.gf != 'gf-custom'
    || song.notes[0].lengthInSteps != 12 || song.notes[0].changeBPM != true
    || song.notes[0].bpm != 150 || song.notes[0].mustHitSection != false
    || song.notes[0].sectionNotes[0][1] != 4
    || song.notes[0].sectionNotes[0][3] != 'GunshotNote'
    || song.notes[0].sectionNotes[0][4] != true
    || song.events[0][1][0][0] != 'Hey!' || song.events.length != 2
    || song.events[1][0] != 200
    || song.events[1][1][0][0] != 'Unknown Authored Event') fail('authored semantics changed');
  if (Reflect.hasField(original.song, 'gf') || Reflect.hasField(original.song.notes[0], 'lengthInSteps'))
    fail('donor object mutated');
  var lines = converted.cameraLines;
  if (lines == null || lines.length != 3 || lines[0].role != 'opponent'
    || lines[0].position != 'dad' || lines[0].characters[0] != 'villain'
    || lines[1].role != 'player' || lines[1].position != 'boyfriend'
    || lines[1].characters[0] != 'hero' || lines[2].role != 'gf'
    || lines[2].characters[0] != 'gf-custom' || lines[2].visible != false)
    fail('legacy camera lines do not match source parser');
  var gfOpponent = CodenameImporter.cameraLegacyStrumlines({player1:'hero', player2:'gf-rival'});
  if (gfOpponent.length != 2 || gfOpponent[0].position != 'girlfriend'
    || gfOpponent[0].characters[0] != 'gf-rival') fail('gf opponent line mismatch');
  var noGf = CodenameImporter.cameraLegacyStrumlines({player1:'hero', player2:'villain', gf:'none'});
  if (noGf.length != 2) fail('none girlfriend should omit line');
  for (bad in ['{"song":{"notes":{}}}', '{"song":{"notes":[{"sectionNotes":[]}]}}',
    '{"song":{"notes":[{"mustHitSection":true,"sectionNotes":[["oops",0,0]]}]}}',
    '{"events":[]}'])
    if (CodenameImporter.isEmbeddedSectionChart(haxe.Json.parse(bad))) fail('nonchart accepted');
 }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DSIDES_BLAMMED.is_dir(), 'mounted D-Sides donor unavailable')
    def test_mixed_codename_and_embedded_donor_chart_shapes(self):
        main = '''import sys.io.File;
class Main {
 static function fail(value:String):Void throw value;
 static function main() {
  var root = Sys.args()[0];
  var hard:Dynamic = haxe.Json.parse(File.getContent(root + '/hard.json'));
  if (!CodenameImporter.isCodenameChart(hard)
    || CodenameImporter.isEmbeddedSectionChart(hard)) fail('hard misclassified');
  for (diff in ['normal', 'easy']) {
   var source:Dynamic = haxe.Json.parse(File.getContent(root + '/' + diff + '.json'));
   var output = CodenameImporter.convertEmbeddedSectionChart(source, diff);
   var before:Dynamic = source.song;
   var after:Dynamic = output.chart.song;
   var lines = output.cameraLines;
   if (lines == null || lines.length != 3
     || lines[0].characters[0] != before.player2
     || lines[1].characters[0] != before.player1
     || lines[2].characters[0] != before.gfVersion
     || lines[2].visible != false)
    fail(diff + ' legacy camera-line identities lost');
   if (after.notes.length != before.notes.length || after.bpm != before.bpm
     || after.gf != before.gfVersion || after.player1 != before.player1
     || after.player2 != before.player2 || after.stage != before.stage)
    fail(diff + ' song fields changed');
   var beforeRows = 0; var afterRows = 0;
   for (section in (cast before.notes:Array<Dynamic>)) beforeRows += section.sectionNotes.length;
   for (section in (cast after.notes:Array<Dynamic>)) afterRows += section.sectionNotes.length;
   if (beforeRows != afterRows || beforeRows < 700) fail(diff + ' rows lost');
   if (haxe.Json.stringify(before.notes[1].sectionNotes)
     != haxe.Json.stringify(after.notes[1].sectionNotes)) fail(diff + ' row payload changed');
  }
 }
}'''
        result = self.run_fixture(main, args=[DSIDES_BLAMMED])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_convert_lanes_sides_and_visual_identity(self):
        meta = {
            "color": "#9271FD", "icon": "bald-fuck",
            "difficulties": ["hard"], "displayName": "Hopkins",
            "needsVoices": False, "bpm": 98, "stepsPerBeat": 4,
            "beatsPerMeasure": 4, "opponentModeAllowed": False, "coopAllowed": False,
            "customValues": {"chapter": 3, "flags": [True, "authored"]},
        }
        chart = {
            "chartVersion": "1.6.0", "codenameChart": True, "scrollSpeed": 2.8,
            "stage": "dorm", "events": [], "noteTypes": [],
            "strumLines": [
                {"type": 0, "position": "dad", "keyCount": 4, "characters": ["jimmy-hopkins"],
                 "notes": [{"id": 2, "time": 8165.84, "sLen": 0, "type": 0},
                           {"id": 0, "time": 8324.01, "sLen": 500, "type": 0}]},
                # Bully-mod authors the player line with position "dad" and type 1;
                # the type marker must win over the position token.
                {"type": 1, "position": "dad", "keyCount": 4, "characters": ["boyfriend"],
                 "notes": [{"id": 3, "time": 3061.22, "sLen": 204.08, "type": 0}]},
                {"type": 2, "position": "girlfriend", "keyCount": 4, "characters": ["pico-scholar"],
                 "notes": [{"id": 1, "time": 83724.48, "sLen": 0, "type": 0}]},
            ],
        }

        def fixture_dir(folder: Path):
            (folder / "meta.json").write_text(json.dumps(meta))
            (folder / "hard.json").write_text(json.dumps(chart))

        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            fixture_dir(fixture)
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = CodenameImporter.convertFiles({haxe_string(str(fixture / "meta.json"))},
      {haxe_string(str(fixture / "hard.json"))}, "hard", {haxe_string(str(fixture))});
    if (result.charts.length != 1) fail("chart count");
    if (result.originalMeta.customValues.chapter != 3
        || result.originalMeta.customValues.flags[1] != "authored") fail("original meta lost");
    if (result.charts[0].fileName != "hopkins-hard.json") fail("file name");
    var song:Dynamic = result.charts[0].chart.song;
    if (song.song != "Hopkins") fail("display name identity");
    if (song.bpm != 98 || song.speed != 2.8) fail("tempo/speed");
    if (song.player1 != "boyfriend" || song.player2 != "jimmy-hopkins" || song.gf != "pico-scholar")
      fail("strum line character slots: " + song.player1 + "/" + song.player2 + "/" + song.gf);
    if (song.stage != "dorm") fail("authored stage preserved");
    var sections:Array<Dynamic> = song.notes;
    var notes:Array<Dynamic> = [];
    for (section in sections) {{
      var rows:Array<Dynamic> = section.sectionNotes;
      for (row in rows) notes.push(row);
    }}
    if (notes.length != 4) fail("native note projection count " + notes.length);
    // Player lanes stay in 0-3, opponent lanes in 4-7; sustains are copied in ms.
    var sorted:Array<Dynamic> = [];
    for (row in notes) {{
      var index = sorted.length;
      while (index > 0 && sorted[index - 1][0] > row[0]) index--;
      sorted.insert(index, row);
    }}
    if (sorted[0][1] != 3 || sorted[0][0] != 3061.22) fail("player lane mapping");
    if (sorted[1][1] != 6 || sorted[1][0] != 8165.84) fail("opponent lane mapping");
    if (sorted[2][1] != 4 || sorted[2][2] != 500) fail("opponent sustain mapping");
    var gfOrigin = CodenameNoteMetadata.read(sorted[3], true);
    if (gfOrigin == null || gfOrigin.lineIndex != 2 || gfOrigin.noteIndex != 0
      || gfOrigin.lineType != 2 || gfOrigin.nativeSide != 1 || sorted[3][1] != 5)
      fail("GF line must be a non-playable native note with source identity");
    var codes:Array<String> = [];
    for (d in result.diagnostics) codes.push(d.code);
    if (codes.indexOf("gf-strumline-notes-routed") < 0)
      fail("GF line routing must be diagnosed: " + codes.join("|"));
    if (result.diagnostics[[for (d in result.diagnostics) d.code].indexOf("gf-strumline-notes-routed")].severity != "info")
      fail("routed GF notes must not be diagnosed as loss");
    for (section in sections)
      if (section.lengthInSteps != 16) fail("16-step sections from 4x4 meta");
  }}
}}
'''
            result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_events_route_recognized_kinds_and_preserve_foreign(self):
        sidecar = {
            "events": [
                {"time": 0, "name": "Camera Zoom",
                 "params": [False, 0.9, "camGame", 16, "cube", "InOut", "direct", False]},
                {"time": 612.24, "name": "Camera Movement", "params": [0, True, 14, "cube", "InOut"]},
                {"time": 1000, "name": "Camera Movement", "params": [1, False, 4, "CLASSIC", "In"]},
                {"time": 1836.73, "name": "Play Animation", "params": [0, "line1", True, "NONE"]},
                {"time": 2000, "name": "Camera Position", "params": [650, 450, False, 16, "cube", "InOut", False]},
                {"time": 2100, "name": "Change Character", "params": ["dad", "pico-scholar"]},
                {"time": 2200, "name": "Totally Custom Event", "params": [1, "x"]},
            ]
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "events.json").write_text(json.dumps(sidecar))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function rowOf(group:Dynamic, name:String):Array<Dynamic> {{
    for (row in (group[1]:Array<Dynamic>))
      if (Std.string(row[0]) == name) return row;
    return null;
  }}
  static function main() {{
    var sidecar = Json.parse(sys.io.File.getContent({haxe_string(str(fixture / "events.json"))}));
    var findings:Array<CodenameImporter.CodenameDiagnostic> = [];
    var groups:Array<Dynamic> = cast CodenameImporter.convertEvents(
      CodenameImporter.sidecarEvents(sidecar), findings, "origin", "hard");
    if (groups.length != 7) fail("group count " + groups.length);
    // Camera Zoom packs exactly the layout the native pump splits by comma.
    var zoom = rowOf(groups[0], "Camera Zoom");
    if (zoom == null || zoom[1] != "false,0.9,camGame,16" || zoom[2] != "cube,InOut,direct,false")
      fail("camera zoom packing: " + Json.stringify(zoom));
    // Codename orders characters dad(0)/bf(1); native Focus Camera is bf(0)/dad(1).
    var dadFocus = rowOf(groups[1], "Focus Camera");
    if (dadFocus == null) fail("dad focus row missing");
    var dadOptions:Dynamic = Json.parse(dadFocus[3]);
    if (Std.string(dadOptions.char) != "1") fail("codename dad must map to native char 1");
    if (Std.string(dadOptions.duration) != "14" || Std.string(dadOptions.ease) != "cube") fail("dad focus payload");
    var bfFocus:Dynamic = Json.parse(rowOf(groups[2], "Focus Camera")[3]);
    if (Std.string(bfFocus.char) != "0") fail("codename bf must map to native char 0");
    var anim = rowOf(groups[3], "Play Animation");
    if (anim == null || anim[1] != "line1" || anim[2] != "dad") fail("play animation routing");
    var position = rowOf(groups[4], "Focus Camera");
    if (position == null || position[1] != "650" || position[2] != "450") fail("camera position routing");
    var positionOptions:Dynamic = Json.parse(position[3]);
    if (Std.string(positionOptions.char) != "-1") fail("absolute camera target must skip character focus");
    var swap = rowOf(groups[5], "Change Character");
    if (swap == null || swap[1] != "dad" || swap[2] != "pico-scholar") fail("change character routing");
    var foreign = rowOf(groups[6], "Totally Custom Event");
    if (foreign == null) fail("foreign event dropped");
    var foreignPayload:Dynamic = Json.parse(foreign[1]);
    if (foreignPayload.engine != "codename" || foreignPayload.params[1] != "x")
      fail("foreign payload lost its params");
    var codes:Array<String> = [for (d in findings) d.code];
    if (codes.indexOf("foreign-event-preserved") < 0) fail("foreign preservation diagnostic missing");
  }}
}}
'''
            result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_camera_flash_maps_codename_schema_to_native_flash_and_fade(self):
        main = '''import haxe.Json;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    // Codename's built-in event schema is reversed/color/time-in-steps/camera.
    var flash = CodenameImporter.routeCodenameEvent("Camera Flash",
      [false, -16777216, 80, "camHUD"]);
    if (flash == null || flash.name != "Camera Flash" || flash.v1 != "hud" || flash.v2 != "")
      fail("regular camera flash target route");
    var flashOptions:Dynamic = Json.parse(flash.v3);
    if (flashOptions.color != "#FF000000" || flashOptions.duration != "80"
      || flashOptions.durationSteps != true)
      fail("regular camera flash color/step duration: " + flash.v3);

    var reversed = CodenameImporter.routeCodenameEvent("Camera Flash",
      ["true", -1, 50, "camOther"]);
    if (reversed == null || reversed.name != "Camera Fade" || reversed.v1 != "false" || reversed.v2 != "50")
      fail("reversed camera flash must become a fade into color");
    var fadeOptions:Dynamic = Json.parse(reversed.v3);
    if (fadeOptions.color != "#FFFFFFFF" || fadeOptions.duration != "50"
      || fadeOptions.shouldFadeIn != false || fadeOptions.applyToOther != true
      || fadeOptions.applyToHud != false)
      fail("reversed camera flash options: " + reversed.v3);
  }
}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_fnas_camera_flash_sidecar_routes_every_authored_row(self):
        sidecar = FNAS / "mods/fnas/songs/better-clone/events.json"
        if not sidecar.is_file():
            self.skipTest("mounted FNAS event sidecar is unavailable")
        main = '''import haxe.Json;
import sys.io.File;
class Main {
  static function fail(value:String):Void throw value;
  static function main():Void {
    var events = CodenameImporter.sidecarEvents(Json.parse(File.getContent(Sys.args()[0])));
    var findings:Array<CodenameImporter.CodenameDiagnostic> = [];
    var groups:Array<Dynamic> = cast CodenameImporter.convertEvents(events, findings, "mounted", "normal");
    var sourceCount = 0;
    for (event in events) if (Std.string(Reflect.field(event, "name")).toLowerCase() == "camera flash") sourceCount++;
    var outputCount = 0;
    for (group in groups) {
      var time:Float = group[0];
      for (row in (group[1]:Array<Dynamic>)) {
        if (row[0] != "Camera Flash" && row[0] != "Camera Fade") continue;
        var metadata:Dynamic = CodenameEventMetadata.read(row, time);
        if (metadata == null || metadata.name != "Camera Flash") fail("authored Camera Flash provenance was lost");
        var params:Array<Dynamic> = cast metadata.params;
        var duration = Std.string(params[2]);
        var color = "#" + StringTools.hex(Std.int(params[1]), 8);
        var options:Dynamic = Json.parse(row[3]);
        if (options.color != color || Std.string(options.duration) != duration)
          fail("authored color or step duration changed: " + Json.stringify(row));
        if (Std.string(params[0]).toLowerCase() == "true") {
          if (row[0] != "Camera Fade" || row[1] != "false" || options.shouldFadeIn != false)
            fail("reversed Codename flash no longer fades into its color");
          if (params[3] == "camHUD" && options.applyToHud != true)
            fail("reversed HUD flash target changed");
        } else {
          if (row[0] != "Camera Flash" || row[1] != "hud" || options.durationSteps != true)
            fail("regular Codename flash lost its camera or step units");
        }
        outputCount++;
      }
    }
    if (sourceCount == 0 || outputCount != sourceCount)
      fail("Camera Flash rows changed count: " + sourceCount + " -> " + outputCount);
  }
}
'''
        result = self.run_fixture(main, args=[sidecar])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_note_types_become_identity_note_definitions(self):
        meta = {"difficulties": ["normal"], "bpm": 100, "stepsPerBeat": 4, "displayName": "Kinds"}
        chart = {
            "codenameChart": True, "scrollSpeed": 2, "stage": "stage",
            "noteTypes": ["Halo Note", "Mine"],
            "strumLines": [
                {"type": 1, "position": "bf", "keyCount": 4, "characters": ["bf"], "notes": [
                    {"id": 0, "time": 100, "sLen": 0, "type": 0},
                    {"id": 1, "time": 200, "sLen": 0, "type": 1},
                    {"id": 2, "time": 300, "sLen": 0, "type": "Halo Note"},
                    {"id": 3, "time": 400, "sLen": 0, "type": 2, "alt": True},
                ]},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "meta.json").write_text(json.dumps(meta))
            (fixture / "normal.json").write_text(json.dumps(chart))
            main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var shared:Array<Dynamic> = [];
    var indexes:Map<String, Int> = new Map<String, Int>();
    var result = CodenameImporter.convertFiles({haxe_string(str(fixture / "meta.json"))},
      {haxe_string(str(fixture / "normal.json"))}, "normal", {haxe_string(str(fixture))}, null, shared, indexes);
    var song:Dynamic = result.charts[0].chart.song;
    var chartTypes:Array<Dynamic> = result.charts[0].noteTypes;
    var songTypes:Array<Dynamic> = song.codenameNoteTypes;
    if (chartTypes.join("|") != "Halo Note|Mine"
        || songTypes.join("|") != "Halo Note|Mine")
      fail("authored note type table was not preserved: " + chartTypes + " / " + songTypes);
    var notes:Array<Dynamic> = [];
    for (section in (cast song.notes:Array<Dynamic>))
      for (row in (cast section.sectionNotes:Array<Dynamic>)) notes.push(row);
    if (notes.length != 4) fail("note count");
    if (notes[0][1] != 0) fail("default kind stays in the normal lane block");
    // Index 1 -> noteTypes[0] = "Halo Note"; both spellings share one definition
    // (and one custom block), while each note keeps its authored lane inside it.
    if (notes[1][1] != 1 + 5 * 8) fail("noteTypes index mapping: " + notes[1][1]);
    if (notes[2][1] != 2 + 5 * 8) fail("string kind must reuse the same custom block: " + notes[2][1]);
    if (shared.length != 1) fail("one shared definition, got " + shared.length);
    if (shared[0].sourceKind != "Halo Note" || shared[0].sourceEngine != "Codename Engine")
      fail("definition identity: " + Json.stringify(shared[0]));
    if (shared[0].id != "codename:Halo_Note:0") fail("definition id");
    // alt notes keep the native alt row marker, not a custom block.
    if (notes[3].length < 4 || notes[3][3] != 1) fail("alt marker missing");
    // The "Mine" kind at index 2 was never used by a note, so no definition exists for it.
    var codes:Array<String> = [for (d in result.diagnostics) d.code];
    if (codes.indexOf("note-kind-generic") < 0) fail("identity preservation diagnostic missing");
  }}
}}
'''
            result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_note_provenance_tracks_authored_line_and_ordinal_without_changing_native_rows(self):
        meta = {"difficulties": ["hard", "normal"], "bpm": 100, "stepsPerBeat": 4,
                "displayName": "Provenance"}
        hard = {"codenameChart": True, "scrollSpeed": 1, "stage": "stage",
                "noteTypes": ["Halo Note"], "strumLines": [
                    {"type": 1, "position": "bf", "keyCount": 4, "characters": ["bf"], "notes": [
                        {"id": 0, "time": 200, "sLen": 0, "type": 0},
                        {"id": 1, "time": 100, "sLen": 50, "type": 1},
                        {"id": 2, "time": 150, "sLen": 0, "type": 0, "alt": True}]},
                    {"type": 1, "position": "bf", "keyCount": 4, "characters": ["bf"], "notes": [
                        {"id": 2, "time": 300, "sLen": 0, "type": 0}]},
                    {"type": 0, "position": "dad", "keyCount": 4, "characters": ["dad"], "notes": [
                        {"id": 3, "time": 400, "sLen": 0, "type": 0}]},
                    {"type": 2, "position": "gf", "keyCount": 4, "characters": ["gf"], "notes": [
                        {"id": 0, "time": 500, "sLen": 0, "payload": {"voice": "gf"}}]},
                    {"type": 3, "position": "extra", "keyCount": 4, "characters": ["extra"], "notes": [
                        {"id": 1, "time": 600, "sLen": 5, "payload": [1, False, "x"]}]},
                ]}
        normal = {"codenameChart": True, "scrollSpeed": 1, "stage": "stage",
                  "strumLines": [
                      {"type": 0, "position": "dad", "keyCount": 4, "characters": ["dad"],
                       "notes": [{"id": 0, "time": 25, "sLen": 0}]},
                      {"type": 1, "position": "bf", "keyCount": 4, "characters": ["bf"],
                       "notes": [{"id": 1, "time": 50, "sLen": 0}]},
                  ]}
        main = f'''import haxe.Json;
class Main {{
  static function fail(message:String):Void throw message;
  static function rows(chart:Dynamic):Array<Dynamic> {{
    var output:Array<Dynamic> = [];
    for (section in (cast chart.song.notes:Array<Dynamic>))
      for (row in (cast section.sectionNotes:Array<Dynamic>)) output.push(row);
    return output;
  }}
  static function main() {{
    var meta = Json.parse({haxe_string(json.dumps(meta))});
    var hard = CodenameImporter.convert(meta, Json.parse({haxe_string(json.dumps(hard))}), "hard");
    var normal = CodenameImporter.convert(meta, Json.parse({haxe_string(json.dumps(normal))}), "normal");
    var hardRows = rows(hard.charts[0].chart);
    if (hardRows.length != 6) fail("native note projection changed");
    var origins:Array<Dynamic> = [for (row in hardRows) CodenameNoteMetadata.read(row)];
    // Sorting by native time does not change source indices.
    if (origins[0].lineIndex != 0 || origins[0].noteIndex != 1
        || origins[1].lineIndex != 0 || origins[1].noteIndex != 2
        || origins[2].lineIndex != 0 || origins[2].noteIndex != 0
        || origins[3].lineIndex != 1 || origins[3].noteIndex != 0
        || origins[4].lineIndex != 2 || origins[4].noteIndex != 0
        || origins[5].lineIndex != 3 || origins[5].noteIndex != 0)
      fail("authored line/note order lost");
    if (origins[0].lineType != 1 || origins[4].lineType != 0
        || origins[0].nativeSide != 0 || origins[4].nativeSide != 1
        || origins[5].lineType != 2 || origins[5].nativeSide != 1)
      fail("type or side provenance lost");
    if (hardRows[0][0] != 100 || hardRows[0][1] != 41 || hardRows[0][2] != 50
        || hardRows[0][3] != null || hardRows[1][3] != 1)
      fail("custom, sustain or alt native semantics changed");
    for (i in 4...13) if (hardRows[0][i] != null) fail("native reserved column changed");
    var unsupported:Array<Dynamic> = cast Reflect.field(hard.charts[0].chart.song, 'codenameUnsupportedNotes');
    if (unsupported == null || unsupported.length != 2
        || unsupported[0].lineIndex != 3 || unsupported[0].noteIndex != 0
        || unsupported[0].role != 'gf' || unsupported[0].note.payload.voice != 'gf'
        || unsupported[1].lineIndex != 4 || unsupported[1].role != 'extra'
        || unsupported[1].note.payload[1] != false)
      fail("unsupported authored note records lost");
    var later = rows(normal.charts[0].chart);
    if (later.length != 2 || CodenameNoteMetadata.read(later[0]).lineIndex != 0
        || CodenameNoteMetadata.read(later[1]).lineIndex != 1)
      fail("later difficulty note provenance lost");
    if (Reflect.hasField(normal.charts[0].chart.song, 'codenameUnsupportedNotes'))
      fail("unsupported records leaked into a different difficulty");
    var copy:Array<Dynamic> = cast hardRows[0].copy();
    copy[1] = 45; // Crosses to opponent lane within the custom 8-key block.
    if (CodenameNoteMetadata.read(copy) != null) fail("cross-side edit retained stale provenance");
    copy = hardRows[0].copy(); copy[13] = {{engine:'codename',version:1,lineIndex:true,noteIndex:1,lineType:1,nativeSide:0}};
    if (CodenameNoteMetadata.read(copy) != null) fail("boolean index accepted");
    copy = hardRows[0].copy(); copy[13] = {{engine:'codename',version:2,lineIndex:0,noteIndex:1,lineType:1,nativeSide:0}};
    if (CodenameNoteMetadata.read(copy) != null) fail("unknown schema version accepted");
    copy = hardRows[0].copy(); copy[13] = 1;
    if (CodenameNoteMetadata.read(copy) != null) fail("primitive metadata accepted");
    copy = hardRows[0].copy(); copy[13] = {{engine:'codename',version:1,lineIndex:0,noteIndex:1,lineType:'player',nativeSide:0}};
    if (CodenameNoteMetadata.read(copy) != null) fail("malformed line type accepted");
    copy = hardRows[0].copy(); copy[13] = {{engine:'codename',version:1,lineIndex:0,noteIndex:-1,lineType:1,nativeSide:0}};
    if (CodenameNoteMetadata.read(copy) != null) fail("negative note index accepted");
    if (CodenameNoteMetadata.read(hardRows[0], false) != null
        || CodenameNoteMetadata.read(hardRows[0], true, 5) != null)
      fail("section side/key count validation failed");
    copy = hardRows[0].copy(); copy[1] = 45;
    if (CodenameNoteMetadata.read(copy, false).nativeSide != 0)
      fail("mustHitSection inversion rejected matching absolute side");
    var original = [1, 2, 3];
    var attached = CodenameNoteMetadata.apply(original, CodenameNoteMetadata.create(1, 2, null, 0));
    if (original.length != 3 || attached.length != 14 || attached[13].noteIndex != 2)
      fail("apply mutated native input row");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DSIDES_SONGS.is_dir(), 'mounted D-Sides donor unavailable')
    def test_mounted_d_sides_strumline_note_and_event_parity(self):
        main = '''import haxe.Json;
import sys.io.File;
class Main {
 static function fail(value:String):Void throw value;
 static function eventCount(value:Dynamic):Int {
  if (!Std.isOfType(value, Array)) return 0;
  var result=0;
  for (group in (cast value:Array<Dynamic>)) {
   if (group != null && Std.isOfType(group, Array) && group.length > 1
     && Std.isOfType(group[1], Array)) {
    var nested:Array<Dynamic>=cast group[1]; result += nested.length;
   } else result++;
  }
  return result;
 }
 static function main() {
  var root=Sys.args()[0];
  for (name in ['dad-battle','endless','monster','tutorial']) {
   var folder=root+'/'+name;
   var meta:Dynamic=Json.parse(File.getContent(folder+'/meta.json'));
   var source:Dynamic=Json.parse(File.getContent(folder+'/charts/hard.json'));
   var lines:Array<Dynamic>=cast source.strumLines;
   var expected=0; var gfExpected=0; var playableExpected=0;
   for (line in lines) for (_ in (cast line.notes:Array<Dynamic>)) {
    expected++;
    var side=CodenameImporter.strumLineSide(line, lines.indexOf(line));
    if (side=='gf') gfExpected++ else if (side=='player'||side=='opponent') playableExpected++;
   }
   var converted=CodenameImporter.convert(meta, source, 'hard', folder);
   var song=converted.charts[0].chart.song;
   var seen:Map<String, Bool>=new Map(); var rows=0; var gfRows=0;
   for (section in (cast song.notes:Array<Dynamic>)) for (row in (cast section.sectionNotes:Array<Dynamic>)) {
    rows++;
    var origin=CodenameNoteMetadata.read(row, true);
    if (origin==null) fail(name+': missing/invalid source origin on row '+rows);
    var line=lines[origin.lineIndex];
    var role=CodenameImporter.strumLineSide(line, origin.lineIndex);
    var sourceNotes:Array<Dynamic>=cast line.notes;
    if (origin.noteIndex<0 || origin.noteIndex>=sourceNotes.length) fail(name+': source note index out of range');
    var raw=sourceNotes[origin.noteIndex];
    var key=origin.lineIndex+':'+origin.noteIndex;
    if (seen.exists(key)) fail(name+': duplicate source note '+key);
    seen.set(key,true);
    var side=role=='player'?0:1;
    if (origin.lineType != line.type || origin.nativeSide != side
      || (Std.int(row[1])%8>=4 ? 1:0)!=side)
     fail(name+': role/side mismatch for '+key+' role='+role);
    if (row[0]!=raw.time || row[2]!=raw.sLen || Std.int(row[1])%4!=raw.id)
     fail(name+': timing/lane/sustain mismatch for '+key);
    if (role=='gf') gfRows++;
   }
   if (rows!=expected || seen.keys().hasNext()==false || gfRows!=gfExpected
     || rows!=playableExpected+gfExpected)
    fail(name+': source row parity lost expected='+expected+' actual='+rows+' gf='+gfRows+'/'+gfExpected);
   var expectedEvents=eventCount(source.events);
   var actualEvents=eventCount(song.events);
   if (actualEvents<expectedEvents)
    fail(name+': chart event payloads lost expected='+expectedEvents+' actual='+actualEvents);
   trace(name+': rows='+rows+' gf='+gfRows+' events='+actualEvents);
  }
 }
}'''
        result = self.run_fixture(main, args=[DSIDES_SONGS])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(DSIDES_SONGS.is_dir(), 'mounted D-Sides donor unavailable')
    def test_mounted_d_sides_every_chart_retains_source_notes(self):
        main = '''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {
 static function fail(message:String):Void throw message;
 static function countSections(sections:Array<Dynamic>):Int {
  var count=0;
  for (section in sections) count+=(cast section.sectionNotes:Array<Dynamic>).length;
  return count;
 }
 static function main() {
  var root=Sys.args()[0]; var chartCount=0;
  for (name in FileSystem.readDirectory(root)) {
   var folder=root+'/'+name; var charts=folder+'/charts';
   if (!FileSystem.isDirectory(folder) || !FileSystem.exists(charts)) continue;
   for (file in FileSystem.readDirectory(charts)) {
    if (!StringTools.endsWith(file,'.json')) continue;
    if (file=='events.json') continue; // shared sidecar, not a difficulty chart
    var difficulty=file.substr(0,file.length-5);
    var source:Dynamic=Json.parse(File.getContent(charts+'/'+file));
    var output:Dynamic=null; var expected=0;
    if (CodenameImporter.isCodenameChart(source)) {
     var lines:Array<Dynamic>=cast source.strumLines;
     for (line in lines) expected+=(cast line.notes:Array<Dynamic>).length;
     var meta:Dynamic=Json.parse(File.getContent(folder+'/meta.json'));
     output=CodenameImporter.convert(meta,source,difficulty,folder).charts[0].chart.song;
     if (output.stage!=source.stage) fail(name+'/'+file+': stage changed');
     var seen:Map<String,Bool>=new Map();
     for (section in (cast output.notes:Array<Dynamic>))
      for (row in (cast section.sectionNotes:Array<Dynamic>)) {
       var origin=CodenameNoteMetadata.read(row,true);
       if (origin==null || origin.lineIndex<0 || origin.lineIndex>=lines.length)
        fail(name+'/'+file+': source origin missing');
       var sourceNotes:Array<Dynamic>=cast lines[origin.lineIndex].notes;
       if (origin.noteIndex<0 || origin.noteIndex>=sourceNotes.length)
        fail(name+'/'+file+': source note index escaped');
       var key=origin.lineIndex+':'+origin.noteIndex;
       if (seen.exists(key)) fail(name+'/'+file+': source note duplicated '+key);
       seen.set(key,true);
       var authored=sourceNotes[origin.noteIndex];
       if (row[0]!=authored.time || row[2]!=authored.sLen || Std.int(row[1])%4!=authored.id)
        fail(name+'/'+file+': note timing, lane or sustain changed at '+key);
      }
     if (Lambda.count(seen)!=expected) fail(name+'/'+file+': source note origins lost');
    } else if (CodenameImporter.isEmbeddedSectionChart(source)) {
     expected=countSections(cast source.song.notes);
     output=CodenameImporter.convertEmbeddedSectionChart(source,difficulty).chart.song;
     if (output.stage!=source.song.stage) fail(name+'/'+file+': section stage changed');
     var authoredSections:Array<Dynamic>=cast source.song.notes;
     var convertedSections:Array<Dynamic>=cast output.notes;
     if (authoredSections.length!=convertedSections.length)
      fail(name+'/'+file+': authored section count changed');
     for (index in 0...authoredSections.length)
      if (Json.stringify(authoredSections[index].sectionNotes)
       !=Json.stringify(convertedSections[index].sectionNotes))
       fail(name+'/'+file+': authored section rows changed at '+index);
    } else continue; // metadata and event sidecars are not charts
    var actual=countSections(cast output.notes);
    if (actual!=expected) fail(name+'/'+file+': '+actual+' of '+expected+' source notes');
    chartCount++;
   }
  }
  if (chartCount!=22) fail('D-Sides chart inventory changed: '+chartCount);
 }
}'''
        result = self.run_fixture(main, args=[DSIDES_SONGS])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_and_stage_xml_convert_to_native_shapes(self):
        character_xml = '''<?DOCTYPE codename-engine-character?>
<character x="-250" y="-260" antialiasing="false" camx="-600" camy="150" icon="bald-fuck" color="#F89B62" flipX="true">
	<anim name="idle" anim="jimmy idle"/>
	<anim name="singLEFT" anim="jimmy left"/>
	<anim name="danceLeft" anim="jimmy dance a" fps="30" indices="0,1,2" loop="true" offsets="4, -6"/>
	<anim name="danceRight" anim="jimmy dance b" fps="30" indices="3,4,5"/>
</character>
'''
        stage_xml = '''<?DOCTYPE codename-engine-stage?>
<stage folder="stages/" name="dorm" zoom="0.9">
	<sprite x="0" sprite="dorm" y="0" name="dorm" scale="1.5" antialiasing="false" skewx="-20"/>
	<sprite x="5" name="wash" color="#FF0000"/>
	<dad/>
	<girlfriend x="173" y="-30"/>
	<boyfriend x="900"/>
	<sprite x="740" sprite="dorm" y="485" name="frontProp"/>
</stage>
'''
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            (fixture / "images/characters").mkdir(parents=True)
            (fixture / "images/stages").mkdir(parents=True)
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/characters/jimmy.png").write_text("png")
            (fixture / "images/characters/jimmy.xml").write_text("<xml/>")
            (fixture / "images/stages/dorm.png").write_text("png")
            (fixture / "images/icons/icon-bald-fuck.png").write_text("png")
            (fixture / "char.xml").write_text(character_xml)
            (fixture / "stage.xml").write_text(stage_xml)
            main = f'''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var root = {haxe_string(str(fixture))};
    var character = CodenameImporter.convertCharacterXml({haxe_string(str(fixture / "char.xml"))},
      root, "jimmy", true, null);
    if (character.name != "jimmy") fail("character name");
    if (character.registryEntry.like != "jimmy") fail("registry like");
    if (character.registryEntry.colors[0] != "#FFF89B62") fail("healthbar color: " + character.registryEntry.colors[0]);
    var charMeta:Dynamic = character.registryEntry.codenameCharacter;
    if (charMeta.x != -250 || charMeta.y != -260) fail("donor placement offset preserved");
    if (charMeta.flipX != true || charMeta.playerOffsets != false) fail("donor orientation preserved");
    var destinations:Array<String> = [for (a in character.assets) a.destination];
    if (destinations.indexOf("char.png") < 0 || destinations.indexOf("char.xml") < 0)
      fail("atlas bundle incomplete: " + destinations.join("|"));
    if (destinations.indexOf("icons.png") < 0) fail("health icon bundle missing");
    if (character.hscript.indexOf("char.animation.addByIndices(\\"danceLeft\\", \\"jimmy dance a\\", [0,1,2], \\'\\', 30, true);") < 0)
      fail("indices animation registration missing: " + character.hscript);
    if (character.hscript.indexOf("char.addOffset(\\"danceLeft\\", 4, -6);") < 0)
      fail("anim offsets missing");
    if (character.hscript.indexOf("char.antialiasing = false;") < 0) fail("antialiasing");
    if (character.hscript.indexOf("char.noFlip = true;") < 0) fail("dance pair flips like gf");
    if (character.hscript.indexOf("char.playAnim(\\"idle\\");") < 0) fail("opening animation");

    var offsets:Map<String, Array<Float>> = new Map();
    offsets.set("dad", [-250.0, -260.0]);
    offsets.set("gf", [0.0, 0.0]);
    offsets.set("bf", [-1200.0, -320.0]);
    var playerOffsets:Map<String, Bool> = ["bf" => true];
    var stage = CodenameImporter.convertStageXml({haxe_string(str(fixture / "stage.xml"))},
      root, "dorm", offsets, null, playerOffsets);
    if (stage.name != "dorm" || stage.registryValue != "dorm") fail("stage identity");
    if (stage.hscript.indexOf("setDefaultZoom(0.9);") < 0) fail("stage zoom");
	// Props and character anchors retain their authored XML child ordinals.
	if (stage.hscript.indexOf("stage.addCodenameProp(codenameProp_dorm_0, 0);") < 0)
	  fail("background prop order: " + stage.hscript);
	if (stage.hscript.indexOf("stage.addCodenameAnchor(\\\"dad\\\", 2);") < 0
	    || stage.hscript.indexOf("stage.addCodenameAnchor(\\\"girlfriend\\\", 3);") < 0
	    || stage.hscript.indexOf("stage.addCodenameAnchor(\\\"boyfriend\\\", 4);") < 0)
	  fail("authored role anchors: " + stage.hscript);
	if (stage.hscript.indexOf("stage.addCodenameProp(codenameProp_frontProp_2, 5);") < 0)
	  fail("front prop order: " + stage.hscript);
	if (stage.hscript.indexOf("addSprite(") >= 0) fail("legacy layer split still used");
    // Codename plants actors at stage position + character position.
    if (stage.hscript.indexOf("stage.setOffsets(\\"dad\\", -150, -160, false);") < 0)
      fail("dad placement: " + stage.hscript);
    if (stage.hscript.indexOf("stage.setOffsets(\\"bf\\", -300, -220, false);") < 0)
      fail("bf placement (900 + -1200, 100 + -320)");
    if (stage.hscript.indexOf("stage.setOffsets(\\"gf\\", 173, -30, false);") < 0)
      fail("gf placement");
    if (stage.hscript.indexOf("dad.x = -150;") < 0 || stage.hscript.indexOf("boyfriend.y = -220;") < 0)
      fail("opening frame placement lines");
    var stageAssets:Array<String> = [for (a in stage.assets) a.destination];
	// The upstream-invalid color-only sprite is omitted, leaving its XML ordinal gap.
	if (stageAssets.join("|") != "prop-0.png|prop-2.png") fail("solid-color prop is data-only: " + stageAssets.join("|"));
	var codes:Array<String> = [for (d in stage.diagnostics) d.code];
	if (codes.indexOf("unsupported-attribute") < 0) fail("unknown attribute must be diagnosed");
	if (codes.indexOf("unsupported-stage-placement") < 0) fail("invalid color-only sprite must be diagnosed");
    // Destination files land beside the generated script.
    for (asset in stage.assets)
      if (!sys.FileSystem.exists(asset.source)) fail("stage asset source missing");
  }}
}}
'''
            result = self.run_fixture(main, files={"char.xml": character_xml, "stage.xml": stage_xml})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # ------------------------------------------------------------------
    # Classification (scanner with stubbed pure-context dependencies)
    # ------------------------------------------------------------------

    # Full stub set copied from the mixed-Auto fixture so the real
    # VSliceImporter/ImportRootScanner sources type-check without flixel.
    SCANNER_STUBS = {
        "CoolUtil.hx": '''class CoolUtil {
  public static function parseJson(raw:String):Dynamic return haxe.Json.parse(raw);
  public static function stringifyJson(value:Dynamic):String return haxe.Json.stringify(value);
}''',
        "EngineCompat.hx": '''typedef EngineCompatEventRoute = { var name:String; var v1:String; var v2:String; var v3:String; };
class EngineCompat {
  public static function eventName(name:Dynamic):String {
    if (name == null) return "";
    var original = StringTools.trim(Std.string(name));
    switch (original.toLowerCase()) {
      case 'changecharacter' | 'change character cl' | 'charchange': return 'Change Character';
      case 'focuscamera' | 'focus camera': return 'Focus Camera';
      default: return original;
    }
  }
  public static function scriptFunctionNames(contents:String):Array<String> return [];
  public static function knownScriptFunction(name:String):Bool return false;
  public static function unknownScriptFunctions(contents:String):Array<String> return [];
  public static function routeVSliceEvent(name:String, values:Dynamic):EngineCompatEventRoute return null;
  public static function vSliceNativeCharacterCandidates(path:String):Array<String> return [];
  public static function resolveStageResolution(reference:String):Dynamic return {nativeName: reference, stageID: 0, standard: false};
  public static function isBuiltinStageReference(reference:String):Bool return false;
  public static function visualFallbackName(kind:String):String return 'stage';
  public static function legacyDialogueText(data:Dynamic, player1:String, player2:String):String return null;
  public static function legacyCutsceneScript(data:Dynamic):String return null;
  public static function legacyCutsceneBool(data:Dynamic, field:String, fallback:Bool):Bool return fallback;
}''',
        "LuaCompat.hx": '''typedef LuaCompatResult = {
  var hscript:String;
  var supported:Bool;
  var diagnostics:Array<String>;
};
class LuaCompat {
  public static function translate(source:String, ?origin:String):LuaCompatResult
    return {hscript: source, supported: true, diagnostics: []};
}''',
        "HxcCompat.hx": '''typedef HxcCompatDiagnostic = { var code:String; var message:String; };
typedef HxcCompatEventAdapter = { var sourceName:String; var canonicalName:String; var fields:Array<String>; };
typedef HxcCompatCallbackAdapter = {
  var sourceName:String;
  var canonicalName:String;
  var arguments:Array<String>;
  var body:String;
  var safe:Bool;
};
typedef HxcCompatResult = {
  var kind:String;
  var generatedHscript:String;
  var diagnostics:Array<HxcCompatDiagnostic>;
  var eventAdapters:Array<HxcCompatEventAdapter>;
  var nativeNoteDefinitions:Array<Dynamic>;
  var className:String;
  var canonicalCallbacks:Array<String>;
  var noteKinds:Array<String>;
  var callbackAdapters:Array<HxcCompatCallbackAdapter>;
  var noteBehaviorPatterns:Array<String>;
  var moduleDisabled:Bool;
  var customEventKind:String;
  var customEventBody:String;
};
class HxcCompat {
  public static function noteKindAvoidsHits(source:String):Bool return false;
  public static function analyze(source:String, ?path:String):HxcCompatResult
    return {kind: '', generatedHscript: '', diagnostics: [], eventAdapters: [], nativeNoteDefinitions: [],
      className: '', canonicalCallbacks: [], noteKinds: [], callbackAdapters: [],
      noteBehaviorPatterns: [], moduleDisabled: false, customEventKind: '', customEventBody: ''};
}''',
    }

    def make_codename_source_root(self, parent: Path) -> Path:
        root = parent / "codename-mod"
        (root / "songs/hopkins/charts").mkdir(parents=True)
        (root / "songs/hopkins/song").mkdir(parents=True)
        (root / "data/characters").mkdir(parents=True)
        (root / "data/stages").mkdir(parents=True)
        (root / "data/config").mkdir(parents=True)
        (root / "songs/hopkins/meta.json").write_text(json.dumps(
            {"difficulties": ["hard"], "bpm": 98, "stepsPerBeat": 4, "displayName": "Hopkins"}))
        (root / "songs/hopkins/charts/hard.json").write_text(json.dumps(
            {"codenameChart": True, "scrollSpeed": 2.8, "stage": "dorm", "strumLines": []}))
        (root / "data/characters/jimmy-hopkins.xml").write_text(
            '<!DOCTYPE codename-engine-character>\n<character icon="bald-fuck"/>\n')
        (root / "data/stages/dorm.xml").write_text(
            '<!DOCTYPE codename-engine-stage>\n<stage name="dorm"/>\n')
        (root / "data/config/modpack.ini").write_text("[mod]\n")
        return root

    def make_compiled_release_root(self, parent: Path) -> Path:
        root = parent / "codename-release"
        (root / "mods/HL17/songs/gordon/charts").mkdir(parents=True)
        (root / "mods/HL17/data/config").mkdir(parents=True)
        # Compiled releases carry the engine's own sample content tree beside
        # the mods folders; the importer needs the generic layout shape first.
        (root / "assets/data").mkdir(parents=True)
        (root / "assets/songs").mkdir(parents=True)
        (root / "mods/HL17/songs/gordon/meta.json").write_text(json.dumps(
            {"difficulties": ["BUCK"], "bpm": 172, "stepsPerBeat": 4, "displayName": "Gordon"}))
        (root / "mods/HL17/songs/gordon/charts/buck.json").write_text(json.dumps(
            {"codenameChart": True, "scrollSpeed": 2, "stage": "stage", "strumLines": []}))
        (root / "mods/HL17/data/config/modpack.ini").write_text("[mod]\n")
        (root / "Engine.exe").write_text("MZ fake bytecode")
        return root

    def test_classification_source_mod_and_compiled_release(self):
        scanner = (ROOT / "source/ImportRootScanner.hx").read_text()
        engine = (ROOT / "source/ImportEngine.hx").read_text()
        codename = (ROOT / "source/CodenameImporter.hx").read_text()
        vslice = (ROOT / "source/VSliceImporter.hx").read_text()
        astc = (ROOT / "source/VSliceAstcAdapter.hx").read_text()
        files = dict(self.SCANNER_STUBS)
        files["ImportEngine.hx"] = engine
        files["ImportRootScanner.hx"] = scanner
        files["CodenameImporter.hx"] = codename
        files["CodenameCharacterAtlas.hx"] = (ROOT / "source/CodenameCharacterAtlas.hx").read_text()
        files["CodenameStrumlineLayout.hx"] = (ROOT / "source/CodenameStrumlineLayout.hx").read_text()
        files["CodenameNoteMetadata.hx"] = (ROOT / "source/CodenameNoteMetadata.hx").read_text()
        files["CodenameStagePlacement.hx"] = (ROOT / "source/CodenameStagePlacement.hx").read_text()
        files["CodenameScriptDiscovery.hx"] = (ROOT / "source/CodenameScriptDiscovery.hx").read_text()
        files["CodenameInstallationAssetOverlay.hx"] = (ROOT / "source/CodenameInstallationAssetOverlay.hx").read_text()
        files["CodenameEventPack.hx"] = (ROOT / "source/CodenameEventPack.hx").read_text()
        files["CodenameBaseCharacterDependency.hx"] = (ROOT / "source/CodenameBaseCharacterDependency.hx").read_text()
        files["VSliceImporter.hx"] = vslice
        files["VSliceAstcAdapter.hx"] = astc
        files["NoteTypeCompat.hx"] = (
            "class NoteTypeCompat {\n"
            "  public static function applyVSliceKind(definition:Dynamic, value:Dynamic):Bool return false;\n"
            "  public static function isStringType(value:Dynamic):Bool return Std.isOfType(value, String);\n"
            "}\n")
        files["Main.hx"] = '''import sys.FileSystem;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var sourceRoot = ImportRootScanner.inspectRoot(Sys.args()[0], ImportEngine.AUTO);
    if (sourceRoot == null) fail("codename source mod not detected");
    if (sourceRoot.engine != ImportEngine.CODENAME) fail("source mod engine " + sourceRoot.engine);
    if (sourceRoot.confidence < 0.6) fail("source mod confidence " + sourceRoot.confidence);
    var compiledRoot = ImportRootScanner.inspectRoot(Sys.args()[1], ImportEngine.AUTO);
    if (compiledRoot == null) fail("compiled release not detected");
    if (compiledRoot.engine != ImportEngine.CODENAME) fail("compiled engine " + compiledRoot.engine);
    if (!ImportRootScanner.isCompiledCodenameRelease(compiledRoot.root))
      fail("compiled release not classified as compiled");
    if (ImportRootScanner.codenameModsFolders(compiledRoot.root).length != 1)
      fail("mods folder recovery");
    var detail = ImportRootScanner.scanDetailed(Sys.args()[1], ImportEngine.AUTO);
    var foundCompiled = false;
    for (d in detail.diagnostics)
      if (d.code == "codename-compiled-release" && d.severity == "info")
        foundCompiled = true;
    if (!foundCompiled) fail("compiled-release diagnostic missing");
    // An empty directory must not classify.
    FileSystem.createDirectory(Sys.args()[2] + "/empty");
    if (ImportRootScanner.inspectRoot(Sys.args()[2] + "/empty", ImportEngine.AUTO) != null)
      fail("empty directory classified");
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            source_root = self.make_codename_source_root(parent)
            compiled_root = self.make_compiled_release_root(parent)
            empty_parent = parent / "scans"
            empty_parent.mkdir()
            main = files.pop("Main.hx")
            result = self.run_fixture(main, extra_cps=[parent], files=files,
                                      args=[source_root, compiled_root, empty_parent])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # ------------------------------------------------------------------
    # Discovery + importSong end-to-end on a synthetic donor
    # ------------------------------------------------------------------

    def test_discovery_imports_native_song_audio_and_registries(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        engine = (ROOT / "source/ImportEngine.hx").read_text()
        scanner = (ROOT / "source/ImportRootScanner.hx").read_text()
        codename = (ROOT / "source/CodenameImporter.hx").read_text()
        vslice = (ROOT / "source/VSliceImporter.hx").read_text()
        astc = (ROOT / "source/VSliceAstcAdapter.hx").read_text()
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function importPathKey",
                "static function normalizedImportFileName",
                "static function isImportFile",
                "static function validImportPath",
                "static function validModuleName",
                "static function findImportFile",
                "static function findImportAudio",
                "static function findNamedDirectory",
                "static function findChildDirectory",
                "static function chartFieldString",
                "static function chartFieldBool",
                "static function getImportDifficultyNames",
                "static function readSongChart",
                "static function appendCodenameDiagnostic",
                "static function appendCodenameDiagnostics",
                "static function discoverCodenameSongImports",
                "static function discoverCodenameSongsFromBase",
                "static function appendCodenameRootScriptDiagnostics",
                "static function collectCodenameScriptDiagnostics",
                "static function findCodenameDefinitionXml",
                "static function safeSortedDirectoryListing",
                "static function vSliceNativeCharacterName",
                "static function codenameConvertedCharacterName",
                "static function codenameNativeCharacterName",
                "static function vSliceNativeCharacterReference",
                "static function importSongFolderName",
                "static function ensureDirectory",
                "static function psychDestinationAssetRoot",
                "static function existingImportChild",
                "static function chooseVSliceRegistry",
                "static function mergeVSliceMapping",
                "static function writeVSliceHScript",
                "static function registryHasVSliceKey",
                "static function mergeVSliceRegistryEntry",
                "static function importVSliceCharacterConversion",
                "static function importCodenameCharacterRuntimeSource",
                "static function importVSliceStageConversion",
                "static function importVSliceNoteKindStyleConversion",
                "static function importVSliceVisuals",
                "static function vSliceMappingDestination",
                "static function copyIfPresent",
                "static function copyRequired",
                "static function hasMaterializedFile",
                "static function hasExistingSongInstrumental",
                "static function requireChartMaterialized",
                "public static function importedCameraZoomMode",
                "static function applyImportedSidecars",
                "static function applyImportedVisualMetadata",
                "static function prepareImportedSongIdentity",
                "static function writeGeneratedDialogue",
                "static function importedChartFileName",
                "static function freeplayRegistryPath",
                "static function readFreeplayRegistry",
                "static function freeplayRegistryHasSong",
                "static function prepareSongNoteDefinitions",
                "static function collectSongNoteDefinitions",
                "static public function importSong(songData:SongImport)",
                "static public function validateSongImport",
            )
        )
        files = dict(self.SCANNER_STUBS)
        # This fixture's donor owns dorm.xml even when the destination also
        # treats dorm as a native alias. The donor definition must win.
        files["EngineCompat.hx"] = files["EngineCompat.hx"].replace(
            "return {nativeName: reference, stageID: 0, standard: false};",
            "return {nativeName: reference == 'dorm' ? 'stage' : reference, stageID: 0, standard: false};"
        ).replace(
            "public static function isBuiltinStageReference(reference:String):Bool return false;",
            "public static function isBuiltinStageReference(reference:String):Bool return reference == 'dorm';"
        )
        files["ImportEngine.hx"] = engine
        files["ImportRootScanner.hx"] = scanner
        files["NightmareVisionChartCompat.hx"] = (ROOT / "source/NightmareVisionChartCompat.hx").read_text()
        files["NightmareVisionScriptDiscovery.hx"] = (ROOT / "source/NightmareVisionScriptDiscovery.hx").read_text()
        files["CodenameImporter.hx"] = codename
        files["CodenameCharacterAtlas.hx"] = (ROOT / "source/CodenameCharacterAtlas.hx").read_text()
        files["CodenameStrumlineLayout.hx"] = (ROOT / "source/CodenameStrumlineLayout.hx").read_text()
        files["CodenameNoteMetadata.hx"] = (ROOT / "source/CodenameNoteMetadata.hx").read_text()
        files["CodenameStagePlacement.hx"] = (ROOT / "source/CodenameStagePlacement.hx").read_text()
        files["CodenameScriptDiscovery.hx"] = (ROOT / "source/CodenameScriptDiscovery.hx").read_text()
        files["CodenameInstallationAssetOverlay.hx"] = (ROOT / "source/CodenameInstallationAssetOverlay.hx").read_text()
        files["CodenameEventPack.hx"] = (ROOT / "source/CodenameEventPack.hx").read_text()
        files["CodenameBaseCharacterDependency.hx"] = (ROOT / "source/CodenameBaseCharacterDependency.hx").read_text()
        files["CodenameScriptPlan.hx"] = (ROOT / "source/CodenameScriptPlan.hx").read_text()
        files["CodenameSongMetadata.hx"] = (ROOT / "source/CodenameSongMetadata.hx").read_text()
        files["VSliceImporter.hx"] = vslice
        files["VSliceAstcAdapter.hx"] = astc
        files["NoteTypeCompat.hx"] = (
            "class NoteTypeCompat {\n"
            "  public static function applyVSliceKind(definition:Dynamic, value:Dynamic):Bool return false;\n"
            "  public static function isStringType(value:Dynamic):Bool return Std.isOfType(value, String);\n"
            "  public static function ensureDefinition(value:Dynamic, definitions:Array<Dynamic>):Int {\n"
            "    var type = Std.string(value);\n"
            "    for (i in 0...definitions.length)\n"
            "      if (Std.string(definitions[i].sourceNoteType) == type) return i;\n"
            "    definitions.push({sourceNoteType:type}); return definitions.length - 1;\n"
            "  }\n"
            "}\n")
        files["ModuleFunctions.hx"] = f'''import haxe.Json;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;

typedef VSliceCharacterImport = {{
  var reference:String; var source:String; var conversion:VSliceImporter.VSliceCharacterConversion;
}};
typedef VSliceStageImport = {{
  var reference:String; var source:String; var conversion:VSliceImporter.VSliceStageConversion;
}};
typedef ConvertedSongChart = {{
  var difficulty:String; var fileName:String; var source:String; var chart:Dynamic;
  @:optional var noteTypes:Array<Dynamic>;
  @:optional var cameraLines:Array<Dynamic>;
  @:optional var authoredSongTitle:Bool;
}};
typedef VSliceNoteStyleImport = {{
  var reference:String; var source:String; var conversion:VSliceImporter.VSliceNoteStyleConversion;
}};
typedef SongImportVocalStem = {{
  var source:String; var destination:String; @:optional var id:String; @:optional var role:String;
}};
typedef SongImport = {{
  var name:String; var p1:String; var p2:String; var gf:String; var stage:String;
  var ui:String; var cutscene:String; var category:String; var isHey:Bool;
  var isCheer:Bool; var isMoody:Bool; var isSpooky:Bool; var stageID:Int; var week:Int;
  var char:String; var display:String; var inst:String; var voices:String; var dialog:String;
  @:optional var dialogueJson:String; @:optional var dialogueText:String;
  @:optional var cutsceneJson:String; @:optional var cutsceneScript:String;
  @:optional var events:String;
  @:optional var cutsceneStoryOnly:Bool; @:optional var cutscenePlayOnce:Bool;
  var modchart:String; var diffFiles:Array<String>;
  @:optional var convertedCharts:Array<ConvertedSongChart>;
  @:optional var noteDefinitions:Array<Dynamic>;
  @:optional var convertedCharacters:Array<VSliceCharacterImport>;
  @:optional var freeplayIconSource:String;
  @:optional var convertedStage:VSliceStageImport;
  @:optional var convertedNoteStyle:VSliceNoteStyleImport;
  @:optional var convertedNoteStyles:Array<VSliceNoteStyleImport>;
  @:optional var vSliceRoot:String; @:optional var engine:String; @:optional var sourceRoot:String;
  @:optional var codenameEngineBaseAssetRoot:String; @:optional var codenameDefaultCharacter:String;
  @:optional var importSourceInfo:SongImportSource;
  @:optional var diagnostics:Array<String>;
  @:optional var generatedModchart:String;
  @:optional var vocalStems:Array<SongImportVocalStem>;
}};
typedef SongImportSource = {{ var song:String; var data:String; var destination:String;
  @:optional var sourceRoot:String; @:optional var engine:String; }};
typedef SongImportRejectionCollector = {{ var entries:Array<Dynamic>; var total:Int;
  var truncated:Bool; var seen:Map<String, Bool>; }};
typedef ImportAssetMergeResult = {{
  var copied:Int; var skipped:Int; var failed:Int; @:optional var errors:Array<String>;
}};

class FNFAssets {{
  public static function exists(path:String):Bool return FileSystem.exists(path);
  public static function getText(path:String):String return File.getContent(path);
}}
class FreeplayRegistry {{
  public static function getPath():String {{
    var jsonc = 'assets/data/freeplaySongJson.jsonc';
    var json = 'assets/data/freeplaySongJson.json';
    if (FileSystem.exists(jsonc) && !FileSystem.isDirectory(jsonc)) return jsonc;
    if (FileSystem.exists(json) && !FileSystem.isDirectory(json)) return json;
    return jsonc;
  }}
}}

class ImportSettings {{
  public static function normalizeSourcePath(value:Dynamic):String {{
    if (value == null) return '';
    var result = StringTools.replace(StringTools.trim(Std.string(value)), '\\\\', '/');
    return Path.normalize(result);
  }}
  public static function getImportRoot(?kind:String):String return 'assets/module/import';
}}
class ModuleFunctions {{
  static var importBackgroundMode:Bool = false;
  public static function testCodenameFallbackResolution(ownerDefinitionExists:Bool):Null<String> {{
    var noCharacters:Array<VSliceCharacterImport> = [];
    return codenameNativeCharacterName(noCharacters, "bf-dark", ownerDefinitionExists, "bf", "bf");
  }}
  static function importWorkCancelled():Bool return false;
  static function yieldImportWork(?force:Bool = false):Void {{}}
  static function reportImportProgress(phase:String, current:String, completed:Int = 0, total:Int = 0,
    copied:Int = 0, skipped:Int = 0, failed:Int = 0, work:Int = 0):Void {{}}
  static function songTargetExists(songName:String, ?sourceFolder:String):Bool return false;
  static function songNeedsRepair(songData:SongImport):Bool return false;
  static function validateAndRecordSongImport(_rejections:SongImportRejectionCollector,
      songData:SongImport, _sourceRoot:String, _sourcePath:String, _engine:String):Bool
    return validateSongImport(songData) == null;
  static function importPathIsWithin(path:String, root:String):Bool {{
    var a = importPathKey(path); var b = importPathKey(root);
    return a == b || (b != '' && a.startsWith(b + '/'));
  }}
  static function importVSliceNoteStyleConversion(importData:VSliceNoteStyleImport,
    result:ImportAssetMergeResult):Void {{}}
{methods}
  public static function discoverCodename(root:ImportRootScanner.ImportRoot):Array<SongImport> {{
    return discoverCodenameSongImports(root);
  }}
  public static function commitVisuals(song:SongImport):ImportAssetMergeResult {{
    return importVSliceVisuals(song);
  }}
}}
'''
        files["DifficultyManager.hx"] = '''import sys.FileSystem;
using StringTools;
class DifficultyManager {
  public static var supportedDiff:Map<String, Bool> = new Map<String, Bool>();
  public static function addSongSupport(song:String):Void {
    var key = song.toLowerCase();
    if (!FileSystem.exists('assets/data/' + key)) return;
    for (entry in FileSystem.readDirectory('assets/data/' + key))
      if (entry.toLowerCase().endsWith('.json'))
        supportedDiff.set(key, true);
  }
}
'''
        files["Main.hx"] = '''import haxe.Json;
import sys.FileSystem;
import sys.io.File;
using StringTools;
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    if (ModuleFunctions.testCodenameFallbackResolution(false) != "bf")
      fail("engine-default Codename fallback did not resolve to bf");
    if (ModuleFunctions.testCodenameFallbackResolution(true) != null)
      fail("owner XML failure incorrectly borrowed source fallback");
    // Seed the destination freeplay registry before the writer reads it.
    FileSystem.createDirectory("assets");
    FileSystem.createDirectory("assets/data");
    File.saveContent("assets/data/baseSongKeys.json", "[]");
    File.saveContent("assets/data/freeplaySongJson.jsonc", '[{"name":"Imported","songs":[]}]');
    var root = ImportRootScanner.inspectRoot(Sys.args()[0], ImportEngine.AUTO);
    if (root == null || root.engine != ImportEngine.CODENAME) fail("root not classified as Codename");
    var songs = ModuleFunctions.discoverCodename(root);
    if (songs.length != 1) fail("expected one song, got " + songs.length);
    var song = songs[0];
    if (song.name != "hopkins") fail("storage key");
    if (song.display != "Hopkins") fail("display name");
    var originalMeta:Dynamic = Reflect.field(song, 'codenameOriginalMeta');
    if (originalMeta == null || originalMeta.displayName != "Hopkins"
        || originalMeta.customValues.chapter != 7) fail("original donor meta missing");
    var resolvedPlan:Dynamic = Reflect.field(song, 'codenameResolvedMeta');
    var hardMeta:Dynamic = CodenameSongMetadata.selectedResolved(resolvedPlan, 'hard');
    var normalMeta:Dynamic = CodenameSongMetadata.selectedResolved(resolvedPlan, 'normal');
    if (hardMeta == null || hardMeta.name != 'hopkins' || hardMeta.bpm != 130
        || hardMeta.displayName != 'Inline Title' || hardMeta.customValues.chapter != 9
        || hardMeta.icon != 'face' || hardMeta.color != 0xFF112233
        || normalMeta == null || normalMeta.bpm != 98
        || normalMeta.displayName != 'Hopkins') fail('per-difficulty meta resolution lost');
    var hardProvenance:Dynamic = Reflect.field(Reflect.field(resolvedPlan, 'difficulties'), 'hard');
    if (hardProvenance.selectedFile != 'meta-hard.json' || hardProvenance.fileMeta.bpm != 123
        || hardProvenance.inlineMeta.bpm != 130) fail('resolved meta provenance lost');
    if (song.p2 != "jimmy-hopkins" || song.p1 != "boyfriend") fail("character slots: " + song.p1 + "/" + song.p2);
    if (song.convertedCharts == null || song.convertedCharts.length != 5) fail("converted charts");
    if (CodenameSongMetadata.selectedResolved(resolvedPlan, 'events') != null
        || CodenameSongMetadata.selectedResolved(resolvedPlan, 'metadata') != null
        || (cast resolvedPlan.chartDifficulties:Array<String>).length != 5)
      fail("chart sidecars entered playable difficulty metadata");
    if (song.convertedStage == null || song.convertedStage.conversion.name != "dorm")
      fail("converted stage missing");
    var extraStages:Array<Dynamic> = cast Reflect.field(song, 'convertedStages');
    var extraNames:Array<String> = extraStages == null ? [] : [for (entry in extraStages) entry.conversion.name];
    var missingDeclaration:Dynamic = extraStages == null ? null :
      (extraNames.indexOf("missing-stage") < 0 ? null : extraStages[extraNames.indexOf("missing-stage")]);
    if (extraStages == null || extraStages.length != 2
        || extraNames.indexOf("Dorm") < 0 || missingDeclaration == null
        || missingDeclaration.conversion.hscript != null || missingDeclaration.conversion.assets.length != 0)
      fail("per-difficulty owned stage conversion/declaration missing");
    var characterNames:Array<String> = [for (c in song.convertedCharacters) c.conversion.name];
    if (characterNames.indexOf("jimmy-hopkins") < 0) fail("opponent conversion missing");
    if (characterNames.indexOf("boyfriend") < 0) fail("owner boyfriend XML lost to native alias");
    for (id in ["standin", "Alice", "alice", "camera-extra", "normal-only", "event-only"])
      if (characterNames.indexOf(id) < 0) fail("nonprimary/difficulty character missing: " + id);
    var camera:Dynamic = Reflect.field(song, 'codenameAuthoredCamera');
    camera = CodenameScriptPlan.parseCamera(CodenameScriptPlan.stringifyCamera(
      CodenameScriptPlan.createCamera("hopkins", camera))).difficulties;
    var hardLines:Array<Dynamic> = cast Reflect.field(Reflect.field(camera, 'hard'), 'lines');
    var normalLines:Array<Dynamic> = cast Reflect.field(Reflect.field(camera, 'normal'), 'lines');
    var hardOpp:Array<String> = cast hardLines[0].characters;
    if (hardOpp.length != 3 || hardOpp[0] != "jimmy-hopkins" || hardOpp[1] != "standin"
        || hardOpp[2] != "standin") fail("duplicate occurrence IDs collapsed");
    var hardPlayers:Array<String> = cast hardLines[1].characters;
    if (hardPlayers[0] != "boyfriend" || hardPlayers[1] != "Alice" || hardPlayers[2] != "alice")
      fail("case-distinct ordered IDs collapsed");
    if ((cast normalLines[0].characters:Array<String>)[1] != "normal-only")
      fail("later difficulty occurrence lost");
    if ((cast normalLines[1].characters:Array<String>)[0] != "alice")
      fail("later difficulty primary actor lost");
    if (Reflect.field(Reflect.field(camera, 'normal'), 'stage') != "Dorm"
        || Reflect.field(Reflect.field(camera, 'missing'), 'stage') != "missing-stage")
      fail("per-difficulty authored stage metadata collapsed");
    if (Reflect.field(Reflect.field(camera, 'hard'), 'nativeStage') != 'dorm'
        || Reflect.field(Reflect.field(camera, 'normal'), 'nativeStage') != 'Dorm'
        || Reflect.field(Reflect.field(camera, 'missing'), 'nativeStage') != 'missing-stage')
      fail('per-difficulty native stage registry identity lost');
    var hardMissing:Array<String> = cast Reflect.field(Reflect.field(camera, 'hard'), 'missingCharacters');
    if (hardMissing.indexOf("ghost") < 0 || hardMissing.indexOf("ALICE") < 0)
      fail("unresolved/ambiguous occurrence not diagnosed in camera metadata");
    var hardNative:Dynamic = Reflect.field(Reflect.field(camera, 'hard'), 'nativeCharacters');
    if (hardNative == null || Reflect.field(hardNative, 'camera extra') != 'camera-extra'
        || Reflect.field(hardNative, 'standin') != 'standin'
        || Reflect.field(hardNative, 'ghost') != 'owner-default'
        || Reflect.field(hardNative, 'ALICE') != 'owner-default')
      fail('authored-to-native actor mapping or unresolved identity lost');
    var hardPlacement:Dynamic = Reflect.field(Reflect.field(camera, 'hard'), 'stagePlacement');
    if (hardPlacement == null || Reflect.field(hardPlacement.slots, 'boyfriend') == null
        || (cast hardPlacement.unsupported:Array<String>).indexOf('stage-script') >= 0)
      fail("harmless camera-only companion script invalidated stage placement");
    if (song.vocalStems == null || song.vocalStems.length != 2) fail("split stems missing");
    var scriptDiagnostics:String = song.diagnostics.join("\\n");
    if (scriptDiagnostics.indexOf("[codename-nonchart-json]") < 0)
      fail("ignored chart sidecars were not diagnosed");
    if (scriptDiagnostics.indexOf("[codename-character-source-fallback]") < 0
        || scriptDiagnostics.indexOf("ghost") < 0 || scriptDiagnostics.indexOf("ALICE") < 0)
      fail("source missing-character fallback lacked importer diagnostic");
    if (scriptDiagnostics.indexOf('DEFAULT_CHARACTER "owner-default"') < 0)
      fail("configured Codename DEFAULT_CHARACTER override was not honored");
    if (scriptDiagnostics.indexOf("[codename-song-script]") < 0) fail("song script gap not diagnosed");
    if (scriptDiagnostics.indexOf("[codename-meta-variant-unsupported]") < 0
        || scriptDiagnostics.indexOf("[codename-meta-flags-unsupported]") < 0)
      fail("unsupported Codename meta selection was silent");
    if (scriptDiagnostics.indexOf("[codename-stage-script]") < 0
        || scriptDiagnostics.indexOf("dorm.hx") < 0) fail("stage sidecar gap not diagnosed");
    if (song.modchart != null) fail("untranslated Codename scripts must not be loaded as native modcharts");
    if (scriptDiagnostics.indexOf("[missing-stage-definition]") < 0
        || scriptDiagnostics.indexOf("missing-stage") < 0)
      fail("missing authored stage not diagnosed");
    if (scriptDiagnostics.indexOf("[codename-stage-difficulty-placement]") < 0)
      fail("shared static stage placement difference not diagnosed");
    if (!ModuleFunctions.importSong(song)) fail("importSong failed");
    FileSystem.createDirectory("assets/images/custom_chars");
    File.saveContent("assets/images/custom_chars/boyfriend.hscript", "global sentinel");
    File.saveContent("assets/images/custom_chars/custom_chars.jsonc", '{"boyfriend":{"like":"bf"}}');
    FileSystem.createDirectory("assets/images/custom_stages");
    File.saveContent("assets/images/custom_stages/dorm.hscript", "global stage sentinel");
    File.saveContent("assets/images/custom_stages/custom_stages.json", '{"dorm":"existing-stage"}');
    extraStages.push({reference:'event-stage', source:'',
      conversion:CodenameImporter.parseStageXml('<stage name="event-stage"/>', '', 'event-stage')});
    var visualMerge = ModuleFunctions.commitVisuals(song);
    if (visualMerge.failed != 0) fail("visual conversion failed");
    var owner = CompatScriptManifest.destinationRoot(song.sourceRoot, ImportEngine.CODENAME);
    if (File.getContent("assets/images/custom_chars/boyfriend.hscript") != "global sentinel")
      fail("global character implementation overwritten");
    if (File.getContent("assets/images/custom_chars/custom_chars.jsonc") != '{"boyfriend":{"like":"bf"}}')
      fail("global registry overwritten");
    if (File.getContent("assets/images/custom_stages/dorm.hscript") != "global stage sentinel"
        || File.getContent("assets/images/custom_stages/custom_stages.json") != '{"dorm":"existing-stage"}')
      fail("global stage overwritten");
    var chart = Json.parse(File.getContent("assets/data/hopkins/hopkins-hard.json")).song;
    var normalChart = Json.parse(File.getContent("assets/data/hopkins/hopkins.json")).song;
    var expertChart = Json.parse(File.getContent("assets/data/hopkins/hopkins-special.json")).song;
    var missingChart = Json.parse(File.getContent("assets/data/hopkins/hopkins-missing.json")).song;
    if (chart.song != "hopkins") fail("generated chart identity");
    if (expertChart.song != "Hopkins" || expertChart.compatPreserveSongTitle != true)
      fail("authored section-chart title was replaced");
    if (chart.bpm != 130 || normalChart.bpm != 98) fail('native chart did not use effective meta BPM');
    if (chart.stage != "dorm" || chart.player2 != "jimmy-hopkins" || chart.player1 != "boyfriend") fail("chart visuals");
    if (normalChart.player1 != "alice" || normalChart.player2 != "jimmy-hopkins")
      fail("later difficulty primary actor replaced by first chart's actor");
    if (normalChart.stage != "Dorm" || missingChart.stage != "missing-stage")
      fail("per-difficulty stage replaced by first chart's stage");
    if (expertChart.bpm != 140 || expertChart.gf != "alice"
        || expertChart.notes[0].lengthInSteps != 12
        || expertChart.notes[0].changeBPM != true
        || expertChart.notes[0].mustHitSection != false
        || expertChart.notes[0].sectionNotes[0][1] != 4
        || Std.string(expertChart.notes[0].sectionNotes[0][3]) != "Special Note")
      fail("embedded section chart was not imported intact");
    if (chart.needsVoices != true) fail("split stems did not enable voices");
    var stems:Array<Dynamic> = cast chart.vocalStems;
    var stemFiles:Array<String> = [for (s in stems) Std.string(s.file)];
    if (stemFiles.indexOf("Voices-Player.ogg") < 0 || stemFiles.indexOf("Voices-Opponent.ogg") < 0)
      fail("stem metadata incomplete: " + stemFiles.join("|"));
    if (!FileSystem.exists("assets/songs/hopkins/Inst.ogg")) fail("inst audio");
    if (!FileSystem.exists("assets/songs/hopkins/Voices-Player.ogg")) fail("player stem audio");
    if (!FileSystem.exists("assets/songs/hopkins/Voices-Opponent.ogg")) fail("opponent stem audio");
    if (!FileSystem.exists(owner + "/images/custom_chars/jimmy-hopkins/char.png")) fail("scoped opponent atlas");
    if (!FileSystem.exists(owner + "/data/characters/jimmy-hopkins.xml")
        || !FileSystem.exists(owner + "/images/characters/jimmy-hopkins.png")
        || !FileSystem.exists(owner + "/images/characters/jimmy-hopkins.xml"))
      fail("scoped Codename actor source missing");
    if (!FileSystem.exists(owner + "/images/custom_chars/jimmy-hopkins/icons.png")) fail("scoped health icon");
    if (!FileSystem.exists(owner + "/images/custom_chars/jimmy-hopkins.hscript")) fail("scoped opponent script");
    if (!FileSystem.exists(owner + "/images/custom_chars/boyfriend/char.png")) fail("scoped player override atlas");
    if (!FileSystem.exists(owner + "/images/custom_chars/boyfriend.hscript")) fail("scoped player override script");
    if (!FileSystem.exists(owner + "/data/characters/boyfriend.xml")
        || !FileSystem.exists(owner + "/images/characters/boyfriend.png"))
      fail("scoped Codename player source missing");
    for (id in ["standin", "Alice", "alice", "camera-extra", "normal-only", "event-only"])
      if (!FileSystem.exists(owner + "/images/custom_chars/" + id + "/char.png")
          || !FileSystem.exists(owner + "/images/custom_chars/" + id + ".hscript"))
        fail("nonprimary actor was not materialized: " + id);
    if (File.getContent(owner + "/images/custom_chars/Alice/char.png")
        == File.getContent(owner + "/images/custom_chars/alice/char.png"))
      fail("case-distinct donor assets were aliased");
    if (FileSystem.exists("assets/images/custom_chars/jimmy-hopkins.hscript")) fail("Codename leaked global script");
    if (FileSystem.exists("assets/data/characters/jimmy-hopkins.xml")
        || FileSystem.exists("assets/images/characters/jimmy-hopkins.png"))
      fail("Codename source leaked outside its owner");
    if (!FileSystem.exists(owner + "/images/custom_stages/dorm/prop-0.png")) fail("scoped stage prop asset");
    if (!FileSystem.exists(owner + "/images/custom_stages/dorm.hscript")) fail("scoped stage script");
    if (!FileSystem.exists(owner + "/images/custom_stages/Dorm.hscript")
        || !FileSystem.exists(owner + "/images/custom_stages/Dorm/prop-0.png"))
      fail("case-distinct second stage not materialized");
    if (FileSystem.exists(owner + "/images/custom_stages/missing-stage.hscript"))
      fail("unavailable owned stage acquired a substitute script");
    if (!FileSystem.exists(owner + "/images/custom_stages/event-stage.hscript")
        || FileSystem.exists("assets/images/custom_stages/event-stage.hscript"))
      fail("event stage not owner scoped");
    File.saveContent(owner + "/images/custom_chars/boyfriend.hscript", "owner custom script");
    File.saveContent(owner + "/images/custom_stages/dorm.hscript", "owner custom stage");
    FileSystem.deleteFile(owner + "/images/custom_chars/jimmy-hopkins/icons.png");
    FileSystem.deleteFile(owner + "/images/custom_stages/dorm/prop-0.png");
    var repair = ModuleFunctions.commitVisuals(song);
    if (repair.failed != 0 || !FileSystem.exists(owner + "/images/custom_chars/jimmy-hopkins/icons.png"))
      fail("same-owner missing file not repaired");
    if (!FileSystem.exists(owner + "/images/custom_stages/dorm/prop-0.png"))
      fail("same-owner missing stage prop not repaired");
    if (File.getContent(owner + "/images/custom_chars/boyfriend.hscript") != "owner custom script")
      fail("same-owner custom script overwritten");
    if (File.getContent(owner + "/images/custom_stages/dorm.hscript") != "owner custom stage")
      fail("same-owner custom stage overwritten");
    var originalOwner = song.sourceRoot;
    song.sourceRoot = null;
    var missingOwner = ModuleFunctions.commitVisuals(song);
    if (missingOwner.failed == 0 || File.getContent("assets/images/custom_chars/boyfriend.hscript") != "global sentinel")
      fail("missing owner root silently wrote global character");
    song.sourceRoot = originalOwner;
    var registryPath = FileSystem.exists(owner + "/images/custom_chars/custom_chars.jsonc")
      ? owner + "/images/custom_chars/custom_chars.jsonc" : owner + "/images/custom_chars/custom_chars.json";
    var registry:Dynamic = Json.parse(File.getContent(registryPath));
    if (Reflect.field(registry, "jimmy-hopkins") == null) fail("character registry entry");
    if (Reflect.field(registry, "boyfriend") == null) fail("owner boyfriend registry entry");
    if (Reflect.field(registry, "Alice") == null || Reflect.field(registry, "alice") == null)
      fail("case-distinct owner registry entries collapsed");
    var stageRegistry:Dynamic = Json.parse(File.getContent(owner + "/images/custom_stages/custom_stages.json"));
    if (Reflect.field(stageRegistry, "dorm") == null) fail("stage registry entry");
    if (Reflect.field(stageRegistry, "Dorm") == null
        || Reflect.field(stageRegistry, "missing-stage") != "missing-stage")
      fail("exact-case or unavailable stage declaration missing");
    if (Reflect.field(stageRegistry, "event-stage") == null) fail("event stage registry entry");
    var freeplay:Array<Dynamic> = cast Json.parse(File.getContent("assets/data/freeplaySongJson.jsonc"));
    var registered = false;
    for (category in freeplay)
      for (entry in (cast category.songs:Array<Dynamic>))
        if (entry.name == "hopkins" && entry.display == "Hopkins") registered = true;
    if (!registered) fail("freeplay registration");
    trace("CODENAME_IMPORT_OK");
  }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            workdir = Path(folder)
            donor = self.make_codename_source_root(workdir / "donor")
            (donor / "data/characters/event-only.xml").write_text(
                '<character><anim name="idle" anim="idle"/></character>')
            (donor / "images/characters").mkdir(parents=True, exist_ok=True)
            (donor / "images/characters/event-only.png").write_bytes(b"event-only-atlas")
            (donor / "images/characters/event-only.xml").write_text("<TextureAtlas/>")
            (donor / "songs/hopkins/events.json").write_text(json.dumps({"events": [
                {"time": 1000, "name": "Change Character",
                 "params": [True, 1, 0, "event-only", 0, 0]}
            ]}))
            (donor / "songs/hopkins/song/Inst.ogg").write_text("inst-bytes")
            (donor / "songs/hopkins/song/Voices-Player.ogg").write_text("player-bytes")
            (donor / "songs/hopkins/song/Voices-Opponent.ogg").write_text("opp-bytes")
            (donor / "songs/hopkins/meta.json").write_text(json.dumps(
                {"difficulties": ["hard", "hard-alt", "normal", "missing", "special"], "bpm": 98, "stepsPerBeat": 4,
                 "displayName": "Hopkins", "variants": ["pico"],
                 "customValues": {"chapter": 7}}))
            (donor / "flags.ini").write_text("chartDefaultBPM=101\n")
            (donor / "data/config").mkdir(parents=True, exist_ok=True)
            (donor / "data/config/modpack.ini").write_text(
                "[Common]\nNAME=Fixture\n[Flags]\nDEFAULT_COLOR=0xFF112233\nDEFAULT_CHARACTER=owner-default\n")
            (donor / "songs/hopkins/meta-hard.json").write_text(json.dumps(
                {"bpm": 123, "stepsPerBeat": 4, "customValues": {"chapter": 9}}))
            (donor / "songs/hopkins/charts/hard.json").write_text(json.dumps(
                {"chartVersion": "1.6.0", "codenameChart": True, "scrollSpeed": 2.8, "stage": "dorm",
                 "meta": {"bpm": 130, "displayName": "Inline Title", "icon": None},
                 "noteTypes": [], "events": [],
                 "strumLines": [
                     {"type": 0, "position": "dad", "keyCount": 4,
                      "characters": ["jimmy-hopkins", "standin", "standin"],
                      "notes": [{"id": 2, "time": 8165.84, "sLen": 0, "type": 0}]},
                     {"type": 1, "position": "dad", "keyCount": 4,
                      "characters": ["boyfriend", "Alice", "alice"],
                      "notes": [{"id": 3, "time": 3061.22, "sLen": 204.08, "type": 0}]},
                     {"type": 3, "position": "extra", "keyCount": 4,
                      "characters": ["camera extra", "ghost", "ALICE"], "notes": []},
                 ]}))
            (donor / "songs/hopkins/charts/hard-alt.json").write_text(json.dumps(
                {"chartVersion": "1.6.0", "codenameChart": True, "scrollSpeed": 2.8,
                 "stage": "dorm", "noteTypes": [], "events": [],
                 "strumLines": [
                     {"type": 0, "position": "boyfriend", "keyCount": 4,
                      "characters": ["jimmy-hopkins"], "notes": []},
                     {"type": 1, "position": "dad", "keyCount": 4,
                      "characters": ["boyfriend"], "notes": []},
                ]}))
            (donor / "songs/hopkins/charts/events.json").write_text(json.dumps(
                {"song": {"events": []}}))
            (donor / "songs/hopkins/charts/metadata.json").write_text(json.dumps(
                {"composer": "Fixture Composer"}))
            (donor / "songs/hopkins/charts/normal.json").write_text(json.dumps(
                {"chartVersion": "1.6.0", "codenameChart": True, "scrollSpeed": 2.8,
                 "stage": "Dorm", "noteTypes": [], "events": [],
                 "strumLines": [
                     {"type": 0, "position": "dad", "keyCount": 4,
                      "characters": ["jimmy-hopkins", "normal-only"], "notes": []},
                     {"type": 1, "position": "boyfriend", "keyCount": 4,
                      "characters": ["alice"], "notes": []},
                 ]}))
            (donor / "songs/hopkins/charts/missing.json").write_text(json.dumps(
                {"chartVersion": "1.6.0", "codenameChart": True, "scrollSpeed": 2.8,
                 "stage": "missing-stage", "noteTypes": [], "events": [],
                 "strumLines": [
                     {"type": 0, "position": "dad", "keyCount": 4,
                      "characters": ["jimmy-hopkins"], "notes": []},
                     {"type": 1, "position": "boyfriend", "keyCount": 4,
                      "characters": ["boyfriend"], "notes": []},
                ]}))
            (donor / "songs/hopkins/charts/special.json").write_text(json.dumps(
                {"song": {"song": "Hopkins", "player1": "alice", "player2": "jimmy-hopkins",
                          "gfVersion": "alice", "stage": "Dorm", "bpm": 140, "speed": 2.3,
                          "events": [[0, [["Hey!", "", ""]]]],
                          "notes": [{"sectionBeats": 3, "mustHitSection": False,
                                     "changeBPM": True, "bpm": 150,
                                     "sectionNotes": [[100, 4, 250, "Special Note", True]]}]}}))
            (donor / "songs/hopkins/scripts").mkdir()
            (donor / "songs/hopkins/scripts/script.hx").write_text("function create() {}\n")
            (donor / "images/characters").mkdir(parents=True, exist_ok=True)
            (donor / "images/characters/jimmy-hopkins.png").write_text("png")
            (donor / "images/characters/jimmy-hopkins.xml").write_text(
                '<TextureAtlas><SubTexture name="jimmy-hopkins idle" x="0" y="0" width="10" height="10"/></TextureAtlas>')
            (donor / "data/characters/jimmy-hopkins.xml").write_text(
                '<!DOCTYPE codename-engine-character>\n'
                '<character x="-250" y="-260" icon="bald-fuck" color="#F89B62">\n'
                '<anim name="idle" anim="jimmy-hopkins idle"/>\n</character>\n')
            (donor / "images/characters/boyfriend.png").write_text("boyfriend png")
            (donor / "images/characters/boyfriend.xml").write_text(
                '<TextureAtlas><SubTexture name="boyfriend idle" x="0" y="0" width="10" height="10"/></TextureAtlas>')
            (donor / "data/characters/boyfriend.xml").write_text(
                '<!DOCTYPE codename-engine-character>\n<character><anim name="idle" anim="boyfriend idle"/></character>\n')
            (donor / "images/characters/owner-default.png").write_text("fallback png")
            (donor / "images/characters/owner-default.xml").write_text(
                '<TextureAtlas><SubTexture name="fallback idle" x="0" y="0" width="10" height="10"/></TextureAtlas>')
            (donor / "data/characters/owner-default.xml").write_text(
                '<!DOCTYPE codename-engine-character>\n<character><anim name="idle" anim="fallback idle"/></character>\n')
            for id in ("standin", "Alice", "alice", "camera-extra", "normal-only"):
                (donor / f"images/characters/{id}.png").write_text(f"owned:{id}")
                (donor / f"images/characters/{id}.xml").write_text(
                    f'<TextureAtlas><SubTexture name="{id} idle" x="0" y="0" width="10" height="10"/></TextureAtlas>')
                definition_id = "camera extra" if id == "camera-extra" else id
                sprite_attr = ' sprite="camera-extra"' if id == "camera-extra" else ""
                (donor / f"data/characters/{definition_id}.xml").write_text(
                    f'<!DOCTYPE codename-engine-character>\n<character{sprite_attr}><anim name="idle" anim="{id} idle"/></character>\n')
            (donor / "data/stages/dorm.xml").write_text(
                '<!DOCTYPE codename-engine-stage>\n<stage folder="stages/" name="dorm" zoom="1">\n'
                '<sprite x="0" sprite="dorm" y="0" name="dorm"/>\n'
                '<dad/>\n<girlfriend x="173" y="-30"/>\n<boyfriend x="900"/>\n</stage>\n')
            (donor / "data/stages/dorm.hx").write_text(
                "function postCreate() { overlay.updateHitbox(); FlxG.camera.zoom = 1.25; }\n")
            (donor / "data/stages/Dorm.xml").write_text(
                '<!DOCTYPE codename-engine-stage>\n<stage folder="stages/" name="Dorm" zoom="1">\n'
                '<sprite x="5" sprite="Dorm" y="7" name="prop"/>\n'
                '<dad/>\n<boyfriend/>\n</stage>\n')
            (donor / "images/stages").mkdir(parents=True)
            (donor / "images/stages/dorm.png").write_text("png")
            (donor / "images/stages/Dorm.png").write_text("case-distinct png")
            # Two authored stage IDs can collapse through the converter's
            # safeStem. The whole candidate must be rejected before either
            # owned registry row could make the other difficulty borrow it.
            (donor / "songs/collision/charts").mkdir(parents=True)
            (donor / "songs/collision/song").mkdir()
            (donor / "songs/collision/song/Inst.ogg").write_text("inst")
            (donor / "songs/collision/meta.json").write_text(json.dumps(
                {"difficulties": ["hard", "normal"], "bpm": 100, "stepsPerBeat": 4}))
            for diff, stage in (("hard", "a?"), ("normal", "a")):
                (donor / f"songs/collision/charts/{diff}.json").write_text(json.dumps(
                    {"codenameChart": True, "scrollSpeed": 1, "stage": stage,
                     "strumLines": [{"type": 0, "position": "dad", "keyCount": 4,
                                     "characters": ["dad"], "notes": []},
                                    {"type": 1, "position": "boyfriend", "keyCount": 4,
                                     "characters": ["bf"], "notes": []}]}))
                (donor / f"data/stages/{stage}.xml").write_text(
                    f'<!DOCTYPE codename-engine-stage>\n<stage name="{stage}"/>\n')
            (donor / "songs/character-collision/charts").mkdir(parents=True)
            (donor / "songs/character-collision/song").mkdir()
            (donor / "songs/character-collision/song/Inst.ogg").write_text("inst")
            (donor / "songs/character-collision/meta.json").write_text(json.dumps(
                {"difficulties": ["hard"], "bpm": 100, "stepsPerBeat": 4}))
            (donor / "songs/character-collision/charts/hard.json").write_text(json.dumps(
                {"codenameChart": True, "scrollSpeed": 1, "stage": "stage",
                 "strumLines": [{"type": 0, "position": "dad", "keyCount": 4,
                                 "characters": ["dad"], "notes": []},
                                {"type": 1, "position": "boyfriend", "keyCount": 4,
                                 "characters": ["bf"], "notes": []},
                                {"type": 3, "position": "extra", "keyCount": 4,
                                 "characters": ["X?", "X"], "notes": []}]}))
            (donor / "data/characters/X?.xml").write_text(
                '<!DOCTYPE codename-engine-character>\n<character><anim name="idle" anim="X idle"/></character>\n')
            (donor / "data/characters/X.xml").write_text(
                '<!DOCTYPE codename-engine-character>\n<character><anim name="idle" anim="X idle"/></character>\n')
            (donor / "images/characters/X?.png").write_text("owned X")
            (donor / "images/characters/X?.xml").write_text(
                '<TextureAtlas><SubTexture name="X idle" x="0" y="0" width="10" height="10"/></TextureAtlas>')
            (donor / "images/characters/X.png").write_text("owned X")
            (donor / "images/characters/X.xml").write_text(
                '<TextureAtlas><SubTexture name="X idle" x="0" y="0" width="10" height="10"/></TextureAtlas>')
            (donor / "images/icons").mkdir(parents=True)
            (donor / "images/icons/bald-fuck.png").write_text("png")
            # Materialize the fixture module beside the donor.  The import writes
            # are relative to the compile/run cwd, so the freeplay seed sits at
            # workdir/assets/data like a real runtime.
            for dependency in ("ImportSongOwnership.hx", "CompatScriptManifest.hx",
                               "CodenameEventMetadata.hx"):
                files[dependency] = (ROOT / "source" / dependency).read_text()
            for name, content in files.items():
                if name == "freeplaySongJson.jsonc":
                    continue
                (workdir / name).write_text(content)
            (workdir / "assets/data").mkdir(parents=True, exist_ok=True)
            (workdir / "assets/data/freeplaySongJson.jsonc").write_text(
                json.dumps([{"name": "Imported", "songs": []}]))
            result = subprocess.run(
                [str(HAXE), "-cp", str(workdir), "--run", "Main", str(donor)],
                cwd=workdir, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("CODENAME_IMPORT_OK", result.stdout)
        self.assertIn("[codename-stage-name-collision]", result.stdout)
        self.assertIn("[codename-character-name-collision]", result.stdout)

    def test_reimport_preserves_existing_codename_script_and_camera_sidecars_as_pair(self):
        module = (ROOT / "source/ModuleFunctions.hx").read_text()
        methods = "\n".join(
            extract_method(module, marker)
            for marker in (
                "static function ensureDirectory(",
                "static function codenameMetadataStagesMatch(",
                "static function codenameNoteTypesByDifficulty(",
                "static function writeCodenameNoteTypePlanIfMissing(",
                "static function reconcileCodenameOwnerMetadata(",
            )
        )
        main = '''class Main {
 static function fail(value:String):Void throw value;
 static function check(ok:Bool,value:String):Void if(!ok)fail(value);
 static function cameraEntry(stage:String):Dynamic return {
  stage:stage,nativeStage:stage,lines:[],characters:{},nativeCharacters:{},
  stageOffsets:{},missingCharacters:[],stageOffsetsKnown:true,
  stageStartCamera:{x:null,y:null},stagePlacement:null
 };
''' + methods + '''
 static function main():Void {
  var namespace=Path.join([Sys.args()[0],"assets/imported_mods/owner-a"]);
  var song="blammed";
  var scriptPath=CodenameScriptPlan.metadataPath(namespace,song);
  var cameraPath=CodenameScriptPlan.cameraMetadataPath(namespace,song);
  var noteTypesPath=CodenameScriptPlan.noteTypesMetadataPath(namespace,song);
  ensureDirectory(Path.directory(scriptPath));
  // Simulate the existing generated pair: the script plan predates Easy and
  // Normal, while the camera plan already carries all three chart identities.
  File.saveContent(scriptPath,CodenameScriptPlan.stringify(
   CodenameScriptPlan.create(song,{hard:"phillyDark"})));
  var oldCamera=CodenameScriptPlan.createCamera(song,{
   hard:cameraEntry("phillyDark"),easy:cameraEntry("philly"),normal:cameraEntry("philly")
  });
  File.saveContent(cameraPath,CodenameScriptPlan.stringifyCamera(oldCamera));
  var oldScriptRaw=File.getContent(scriptPath);
  var oldCameraRaw=File.getContent(cameraPath);

  var songData:SongImport=cast {
   sourceFolder:song,
   convertedCharts:[{difficulty:"hard",noteTypes:["Mine","Fire"]},
     {difficulty:"normal",noteTypes:["Shield"]}],
   codenameAuthoredStages:{easy:"philly",normal:"philly",hard:"phillyDark"},
   codenameAuthoredCamera:{
    easy:cameraEntry("philly"),normal:cameraEntry("philly"),hard:cameraEntry("phillyDark")
   }
  };
  var result:ImportAssetMergeResult={copied:0,skipped:0,failed:0,errors:[]};
  reconcileCodenameOwnerMetadata(songData,namespace,result);
  check(result.failed==0 && result.copied==1 && result.skipped==2,
   "existing paired sidecars or missing note sidecar were mishandled: "+result.errors);
  check(File.getContent(scriptPath)==oldScriptRaw && File.getContent(cameraPath)==oldCameraRaw,
   "reimport changed an existing generated metadata pair");
  var generatedTypes=File.getContent(noteTypesPath);
  check(CodenameScriptPlan.selectedNoteTypes(CodenameScriptPlan.parseNoteTypes(generatedTypes),"hard")
    .join("|")=="Mine|Fire"
    && CodenameScriptPlan.selectedNoteTypes(CodenameScriptPlan.parseNoteTypes(generatedTypes),"normal")
      .join("|")=="Shield", "missing sidecar not emitted from converted charts");
  songData.convertedCharts[0].noteTypes=["Changed"];

  var repeated:ImportAssetMergeResult={copied:0,skipped:0,failed:0,errors:[]};
  reconcileCodenameOwnerMetadata(songData,namespace,repeated);
  check(repeated.failed==0 && repeated.copied==0 && repeated.skipped==3
    && File.getContent(noteTypesPath)==generatedTypes,
   "existing note sidecar was overwritten on refresh");
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            files = {
                "CodenameScriptPlan.hx": (ROOT / "source/CodenameScriptPlan.hx").read_text(),
                "Main.hx": """import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
using StringTools;
typedef SongImport = { var sourceFolder:String; @:optional var convertedCharts:Array<Dynamic>; };
typedef ImportAssetMergeResult = {
 var copied:Int; var skipped:Int; var failed:Int; @:optional var errors:Array<String>;
};
""" + main,
            }
            for name, content in files.items():
                target = work / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main", str(work)],
                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # ------------------------------------------------------------------
    # Real donor coverage (skip gracefully when not mounted)
    # ------------------------------------------------------------------

    def test_real_bully_mod_donor_converts(self):
        if not BULLY.is_dir():
            self.skipTest("mounted bully-mod Codename donor is not available")
        meta_path = BULLY / "songs/hopkins/meta.json"
        chart_path = BULLY / "songs/hopkins/charts/hard.json"
        if not meta_path.is_file() or not chart_path.is_file():
            self.skipTest("mounted hopkins chart is not available")
        main = f'''import haxe.Json;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    // The donor authors its camera work in the shared events.json sidecar;
    // Codename merges it with every chart's own events.
    var sidecar = Json.parse(sys.io.File.getContent({haxe_string(str(BULLY / "songs/hopkins/events.json"))}));
    var result = CodenameImporter.convertFiles({haxe_string(str(meta_path))},
      {haxe_string(str(chart_path))}, "hard", {haxe_string(str(BULLY))}, sidecar);
    var song:Dynamic = result.charts[0].chart.song;
    if (song.bpm != 98 || song.speed != 2.8) fail("tempo/speed");
    if (song.player2 != "jimmy-hopkins" || song.player1 != "boyfriend" || song.gf != "pico-scholar")
      fail("character slots");
    var notes:Array<Dynamic> = [];
    for (section in (cast song.notes:Array<Dynamic>))
      for (row in (cast section.sectionNotes:Array<Dynamic>)) notes.push(row);
    // The 90 hidden girlfriend-line notes are preserved on the non-playable
    // side so their Codename CPU events and GF singing can run.
    if (notes.length != 526) fail("native note projection count " + notes.length);
    var opponent = 0;
    var player = 0;
    var girlfriend = 0;
    for (row in notes)
      if (row[1] >= 4) {{
        opponent++;
        var origin=CodenameNoteMetadata.read(row, true);
        if (origin != null && origin.lineType == 2) {{
          girlfriend++;
          if (origin.nativeSide != 1 || origin.lineIndex != 2)
            fail("GF line ownership/provenance");
        }}
      }} else player++;
    if (opponent != 362 || player != 164 || girlfriend != 90)
      fail("lane split " + opponent + "/" + player + "/gf=" + girlfriend);
    var events:Array<Dynamic> = song.events;
    var cameraZooms = 0;
    var focus = 0;
    for (group in events)
      for (row in (group[1]:Array<Dynamic>)) {{
        if (Std.string(row[0]) == "Camera Zoom") cameraZooms++;
        if (Std.string(row[0]) == "Focus Camera") focus++;
      }}
    // The donor sidecar carries 9 Camera Zoom rows; every one routes to the
    // native packed layout, and the Camera Movement/Position rows to Focus Camera.
    if (cameraZooms != 9) fail("camera zoom routing " + cameraZooms);
    if (focus != 25) fail("camera movement/position routing " + focus);
    var playerOffsets:Map<String, Bool> = ["bf" => true];
    var stage = CodenameImporter.convertStageXml(
      {haxe_string(str(BULLY / "data/stages/dorm.xml"))}, {haxe_string(str(BULLY))}, "dorm", null);
    if (stage.name != "dorm") fail("stage conversion");
    if (stage.assets.length != 3) fail("stage prop assets " + stage.assets.length);
    var character = CodenameImporter.convertCharacterXml(
      {haxe_string(str(BULLY / "data/characters/jimmy-hopkins.xml"))},
      {haxe_string(str(BULLY))}, "jimmy-hopkins", true, null);
    var destinations:Array<String> = [for (a in character.assets) a.destination];
    if (destinations.indexOf("icons.png") < 0) fail("bald-fuck icon resolution");
    trace("DONOR_CONVERT_OK");
  }}
}}
'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DONOR_CONVERT_OK", result.stdout)

    def test_real_compiled_releases_classify_as_codename(self):
        scanner = (ROOT / "source/ImportRootScanner.hx").read_text()
        engine = (ROOT / "source/ImportEngine.hx").read_text()
        codename = (ROOT / "source/CodenameImporter.hx").read_text()
        vslice = (ROOT / "source/VSliceImporter.hx").read_text()
        astc = (ROOT / "source/VSliceAstcAdapter.hx").read_text()
        files = dict(self.SCANNER_STUBS)
        files["ImportEngine.hx"] = engine
        files["ImportRootScanner.hx"] = scanner
        files["CodenameImporter.hx"] = codename
        files["CodenameCharacterAtlas.hx"] = (ROOT / "source/CodenameCharacterAtlas.hx").read_text()
        files["CodenameStrumlineLayout.hx"] = (ROOT / "source/CodenameStrumlineLayout.hx").read_text()
        files["CodenameNoteMetadata.hx"] = (ROOT / "source/CodenameNoteMetadata.hx").read_text()
        files["CodenameStagePlacement.hx"] = (ROOT / "source/CodenameStagePlacement.hx").read_text()
        files["CodenameScriptDiscovery.hx"] = (ROOT / "source/CodenameScriptDiscovery.hx").read_text()
        files["CodenameInstallationAssetOverlay.hx"] = (ROOT / "source/CodenameInstallationAssetOverlay.hx").read_text()
        files["CodenameEventPack.hx"] = (ROOT / "source/CodenameEventPack.hx").read_text()
        files["VSliceImporter.hx"] = vslice
        files["VSliceAstcAdapter.hx"] = astc
        files["NoteTypeCompat.hx"] = (
            "class NoteTypeCompat {\n"
            "  public static function applyVSliceKind(definition:Dynamic, value:Dynamic):Bool return false;\n"
            "  public static function isStringType(value:Dynamic):Bool return Std.isOfType(value, String);\n"
            "}\n")
        files["Main.hx"] = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    for (path in [Sys.args()[0], Sys.args()[1]]) {
      var root = ImportRootScanner.inspectRoot(path, ImportEngine.AUTO);
      if (root == null) fail("release not detected: " + path);
      if (root.engine != ImportEngine.CODENAME) fail("release engine " + root.engine + " for " + path);
      if (!ImportRootScanner.isCompiledCodenameRelease(root.root))
        fail("release not classified as compiled: " + path);
      if (ImportRootScanner.codenameModsFolders(root.root).length == 0)
        fail("no recoverable mods folders: " + path);
      var detail = ImportRootScanner.scanDetailed(path, ImportEngine.AUTO);
      var found = false;
      for (d in detail.diagnostics)
        if (d.code == "codename-compiled-release") found = true;
      if (!found) fail("compiled-release diagnostic missing for " + path);
      trace("COMPILED_OK " + path);
    }
  }
}
'''
        missing = [path for path in (HL17, FNAS) if not path.is_dir()]
        if missing:
            self.skipTest("mounted compiled Codename releases are not available: " + ", ".join(str(m) for m in missing))
        main = files.pop("Main.hx")
        result = self.run_fixture(main, files=files, args=[HL17, FNAS])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("COMPILED_OK"), 2, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
