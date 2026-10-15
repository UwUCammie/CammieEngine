"""V-Slice Animate atlas characters and stage props are converted.

V-Slice characters with renderType animateatlas or multianimateatlas, and
stage props with animType animateatlas, ship an Adobe Animate export folder
(Animation.json plus spritemaps) instead of a Sparrow sheet.  The importer
used to reject them, so those characters dropped out of the import and the
props vanished.  They now copy the export folder and generate script that
loads it through the base-game AnimateAtlasUtil, the same flixel-animate path
the engine uses for the other engine families.
"""
from haxe_test_support import HAXE_COMMAND

import json
import subprocess
import tempfile
import unittest
from haxe_test_support import FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]
HSCRIPT = ROOT / ".haxelib/hscript/2,5,0"


def haxe_string(value) -> str:
    return json.dumps(str(value))


def write_export(folder: Path) -> None:
    folder.mkdir(parents=True)
    (folder / "Animation.json").write_text("{}", newline='\n')
    (folder / "spritemap1.json").write_text('{"meta":{"image":"spritemap1.png"}}', newline='\n')
    (folder / "spritemap1.png").write_bytes(b"png")
    (folder / "notes.txt").write_text("not part of the export", newline='\n')


class VSliceAnimateAtlasTest(unittest.TestCase):
    def run_haxe(self, body: str) -> str:
        with tempfile.TemporaryDirectory() as build:
            Path(build, "Main.hx").write_text(body, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HSCRIPT),
                 "-cp", build, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def convert_character(self, fixture: Path, character: dict) -> dict:
        source = fixture / "character.json"
        source.write_text(json.dumps(character), newline='\n')
        output = fixture / "out.json"
        self.run_haxe(f'''import haxe.Json;
class Main {{
  static function main() {{
    var c = VSliceImporter.convertCharacter(Json.parse(sys.io.File.getContent({haxe_string(source)})),
      {haxe_string(fixture)}, "hero", true, {haxe_string(source)});
    sys.io.File.saveContent({haxe_string(output)}, Json.stringify({{
      supported: c.supported, hscript: c.hscript,
      destinations: [for (a in c.assets) a.destination],
      codes: [for (d in c.diagnostics) d.code]
    }}));
  }}
}}
''')
        return json.loads(output.read_text())

    def test_multi_animate_character_combines_its_atlases(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            write_export(fixture / "shared/images/characters/hero/main")
            write_export(fixture / "shared/images/characters/hero/intro")
            (fixture / "shared/images/characters/hero/death.png").write_bytes(b"png")
            (fixture / "shared/images/characters/hero/death.xml").write_text("<TextureAtlas/>", newline='\n')
            (fixture / "images/icons").mkdir(parents=True)
            (fixture / "images/icons/icon-hero.png").write_bytes(b"icon")
            converted = self.convert_character(fixture, {
                "version": "1.0.0", "name": "Hero", "renderType": "multianimateatlas",
                "assetPath": "shared:characters/hero/main",
                "atlasSettings": {"useRenderTexture": True},
                "healthIcon": {"id": "hero"},
                "animations": [
                    {"name": "idle", "prefix": "idle", "animType": "framelabel", "looped": True},
                    {"name": "singLEFT", "prefix": "Hero Left", "animType": "symbol", "frameIndices": [0, 2]},
                    {"name": "intro", "prefix": "intro", "assetPath": "shared:characters/hero/intro"},
                    {"name": "firstDeath", "prefix": "Hero Dies", "renderType": "sparrow",
                     "assetPath": "shared:characters/hero/death"},
                    {"name": "gone", "prefix": "gone", "assetPath": "shared:characters/hero/missing"},
                ],
            })
        self.assertTrue(converted["supported"], converted)
        self.assertNotIn("unsupported-character-render-type", converted["codes"])
        self.assertNotIn("unsupported-character-field", converted["codes"])
        destinations = converted["destinations"]
        for expected in ("char/Animation.json", "char/spritemap1.json", "char/spritemap1.png",
                         "part1/Animation.json", "part2.png", "part2.xml"):
            self.assertIn(expected, destinations)
        self.assertNotIn("char/notes.txt", destinations)
        script = converted["hscript"]
        self.assertIn('char.frames = AnimateAtlasUtil.combine([AnimateAtlasUtil.folder(hscriptPath + "char"), '
                      'AnimateAtlasUtil.folder(hscriptPath + "part1"), '
                      'FlxAtlasFrames.fromSparrow(hscriptPath + "part2.png", hscriptPath + "part2.xml")]);', script)
        self.assertIn("char.useRenderTexture = true;", script)
        self.assertIn('AnimateAtlasUtil.addAnimation(char, "idle", "idle", null, 24, true, "framelabel", false, false);', script)
        self.assertIn('AnimateAtlasUtil.addAnimation(char, "singLEFT", "Hero Left", [0, 2], 24, false, "symbol", false, false);', script)
        # No authored animType: label first, then symbol, at runtime.
        self.assertIn('AnimateAtlasUtil.addAnimation(char, "intro", "intro", null, 24, false, null, false, false);', script)
        self.assertIn('char.animation.addByPrefix("firstDeath", "Hero Dies", 24, false);', script)
        # The missing atlas leaves its animation out instead of an empty alias.
        self.assertNotIn('"gone"', script)
        self.assertNotIn("registerVSliceAnimationAsset", script)

        # The generated script runs against a stand-in character and helper.
        stdout = self.run_haxe(f'''class Helper {{
  public var calls:Array<String> = [];
  public function new() {{}}
  public function folder(path:String):Dynamic return "atlas:" + path;
  public function combine(parts:Array<Dynamic>):Dynamic return parts.join("+");
  public function addAnimation(sprite:Dynamic, name:String, label:String, indices:Array<Int>, fps:Float,
      loop:Bool, type:String, fx:Bool, fy:Bool):Bool {{
    calls.push(name + "=" + label + "/" + type);
    return true;
  }}
}}
class Point {{ public var x:Float = 1; public var y:Float = 1; public function new() {{}}
  public function set(a:Float, b:Float) {{ x = a; y = b; }} }}
class Anim {{ public function new() {{}}
  public function addByPrefix(a:String, b:String, c:Float, d:Bool) {{}} }}
class Sparrow {{ public static function fromSparrow(png:String, xml:String):Dynamic return "sparrow:" + png; }}
class Char {{
  public var frames:Dynamic; public var scale = new Point(); public var animation = new Anim();
  public var flipX = false; public var antialiasing = true; public var useRenderTexture = false;
  public var played:String; public var offsets:Array<String> = [];
  public function new() {{}}
  public function updateHitbox() {{}}
  public function rememberVSliceBaseFrames() {{}}
  public function addOffset(name:String, x:Float, y:Float) offsets.push(name);
  public function playAnim(name:String, ?force:Bool) played = name;
}}
class Main {{
  static function main() {{
    var interp = new hscript.Interp();
    var helper = new Helper();
    var hero:Dynamic = new Char();
    interp.variables.set("AnimateAtlasUtil", helper);
    interp.variables.set("FlxAtlasFrames", Sparrow);
    interp.variables.set("hscriptPath", "dir/");
    interp.execute(new hscript.Parser().parseString({haxe_string(script)}));
    interp.variables.get("init")(hero);
    if (hero.frames != "atlas:dir/char+atlas:dir/part1+sparrow:dir/part2.png") throw "frames " + hero.frames;
    if (!hero.useRenderTexture) throw "atlasSettings.useRenderTexture lost";
    if (helper.calls.join(",") != "idle=idle/framelabel,singLEFT=Hero Left/symbol,intro=intro/null")
      throw "calls " + helper.calls.join(",");
    if (hero.played != "idle") throw "opening pose " + hero.played;
    Sys.println("animate-character-script-ok");
  }}
}}
''')
        self.assertIn("animate-character-script-ok", stdout)

    def test_animate_atlas_util_picks_label_or_symbol(self):
        # The shared helper runs against stand-ins for flixel-animate, so the
        # lookup rule itself is checked: an authored type uses only that lookup,
        # no type tries the frame label first and then the symbol, and a lookup
        # that registers nothing reports false.
        stubs = {
            "animate/internal/Timeline.hx": '''package animate.internal;
class Timeline {
  public var labels:Array<String>;
  public function new(labels:Array<String>) this.labels = labels;
  public function findFrameLabelIndices(label:String):Array<Int> return labels.indexOf(label) >= 0 ? [0] : [];
}
''',
            "animate/FlxAnimateController.hx": '''package animate;
import animate.internal.Timeline;
class FlxAnimateController {
  public var labels:Array<String> = []; public var symbols:Array<String> = [];
  // Labels of atlases combined into this one, searched by the label adders too.
  public var collections:Array<Timeline> = [];
  public var added:Map<String, String> = new Map(); public var calls:Array<String> = [];
  public function new() {}
  public function findFrameLabelIndices(label:String):Array<Int> return labels.indexOf(label) >= 0 ? [0] : [];
  public function getCollectionTimelines():Array<Timeline> return collections;
  function anyLabel(l:String):Bool {
    if (labels.indexOf(l) >= 0) return true;
    for (t in collections) if (t.labels.indexOf(l) >= 0) return true;
    return false;
  }
  public function addByFrameLabel(n:String, l:String, fps:Float, loop:Bool, fx:Bool, fy:Bool) {
    calls.push("label:" + n + ":" + fps + ":" + loop); if (anyLabel(l)) added.set(n, l); }
  public function addByFrameLabelIndices(n:String, l:String, i:Array<Int>, fps:Float, loop:Bool, fx:Bool, fy:Bool) {
    calls.push("labelIdx:" + n + ":" + i.join(".")); if (anyLabel(l)) added.set(n, l); }
  public function addBySymbol(n:String, s:String, fps:Float, loop:Bool, fx:Bool, fy:Bool) {
    calls.push("symbol:" + n); if (symbols.indexOf(s) >= 0) added.set(n, s); }
  public function addBySymbolIndices(n:String, s:String, i:Array<Int>, fps:Float, loop:Bool, fx:Bool, fy:Bool) {
    calls.push("symbolIdx:" + n + ":" + i.join(".")); if (symbols.indexOf(s) >= 0) added.set(n, s); }
  public function exists(n:String):Bool return added.exists(n);
}
''',
            "animate/FlxAnimate.hx": '''package animate;
class FlxAnimate {
  public var anim = new FlxAnimateController(); public var isAnimate = true;
  public function new() {}
}
''',
            "animate/FlxAnimateFrames.hx": '''package animate;
class FlxAnimateFrames extends flixel.graphics.frames.FlxAtlasFrames {
  public static function fromAnimate(path:String):flixel.graphics.frames.FlxAtlasFrames
    return new flixel.graphics.frames.FlxAtlasFrames("animate:" + path);
  public static function combineAtlas(parts:Array<flixel.graphics.frames.FlxAtlasFrames>):flixel.graphics.frames.FlxAtlasFrames
    return new flixel.graphics.frames.FlxAtlasFrames([for (p in parts) p.id].join("+"));
}
''',
            "flixel/graphics/frames/FlxAtlasFrames.hx": '''package flixel.graphics.frames;
class FlxAtlasFrames { public var id:String; public function new(id:String) this.id = id; }
''',
            "FNFAssets.hx": '''class FNFAssets {
  public static function exists(path:String):Bool return path == "mods/x/char/Animation.json";
}
''',
        }
        with tempfile.TemporaryDirectory() as build:
            for relative, text in stubs.items():
                target = Path(build, relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, newline='\n')
            Path(build, "AnimateAtlasUtil.hx").write_text(
                (ROOT / "source/AnimateAtlasUtil.hx").read_text(), newline='\n')
            Path(build, "Main.hx").write_text('''import animate.FlxAnimate;
import flixel.graphics.frames.FlxAtlasFrames;
class Main {
  static function check(ok:Bool, what:String) if (!ok) throw what;
  static function main() {
    var s = new FlxAnimate();
    s.anim.labels = ["idle", "both"]; s.anim.symbols = ["Hero Left", "both", "idle sym"];
    check(AnimateAtlasUtil.addAnimation(s, "idle", "idle", null, 30, true), "auto label");
    check(AnimateAtlasUtil.addAnimation(s, "left", "Hero Left"), "auto falls back to symbol");
    check(!AnimateAtlasUtil.addAnimation(s, "fl", "Hero Left", null, 24, false, "framelabel"), "framelabel must not fall back");
    check(AnimateAtlasUtil.addAnimation(s, "sym", "both", [1, 2], 24, false, " Symbol "), "symbol type with indices");
    check(!AnimateAtlasUtil.addAnimation(s, "none", "nothing"), "missing reports false");
    check(AnimateAtlasUtil.addAnimation(s, "zero", "idle", [], 0), "zero fps and empty indices still register the label");
    // A label that lives only in a combined atlas's timeline is still a label.
    s.anim.collections = [new animate.internal.Timeline(["part label"])];
    check(AnimateAtlasUtil.addAnimation(s, "part", "part label"), "combined atlas label");
    var calls = s.anim.calls.join(",");
    check(calls == "label:idle:30:true,symbol:left,label:fl:24:false,symbolIdx:sym:1.2,symbol:none,label:zero:24:false,label:part:24:false", calls);
    s.isAnimate = false;
    check(!AnimateAtlasUtil.addAnimation(s, "flat", "idle"), "non-Animate sprite rejected");
    check(AnimateAtlasUtil.folder(null) == null && AnimateAtlasUtil.folder("mods/other") == null, "non-export folder");
    var bs = String.fromCharCode(92);
    check(AnimateAtlasUtil.folder(" mods" + bs + "x" + bs + "char// ").id == "animate:mods/x/char", "folder path cleanup");
    var a = new FlxAtlasFrames("a"), b = new FlxAtlasFrames("b");
    check(AnimateAtlasUtil.combine([null, a]) == a, "single part kept as is");
    check(AnimateAtlasUtil.combine([a, null, b]).id == "a+b", "parts combined in order");
    check(AnimateAtlasUtil.combine([null]) == null && AnimateAtlasUtil.combine(null) == null, "nothing to combine");
    Sys.println("animate-util-ok");
  }
}
''', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", build, "-main", "Main", "--interp"],
                                    cwd=build, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("animate-util-ok", result.stdout)

    def test_single_animate_character_registers_every_animation_on_its_export(self):
        # V-Slice's single Animate character ignores a per-animation renderType
        # and assetPath: every animation is a label or symbol of its one export.
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            write_export(fixture / "images/characters/solo")
            converted = self.convert_character(fixture, {
                "version": "1.0.0", "name": "Solo", "renderType": "animateatlas",
                "assetPath": "characters/solo",
                "animations": [
                    {"name": "idle", "prefix": "idle"},
                    {"name": "hey", "prefix": "Solo Hey", "renderType": "sparrow",
                     "assetPath": "characters/elsewhere"},
                ],
            })
        self.assertTrue(converted["supported"], converted)
        script = converted["hscript"]
        self.assertIn('char.frames = AnimateAtlasUtil.folder(hscriptPath + "char");', script)
        self.assertIn('AnimateAtlasUtil.addAnimation(char, "hey", "Solo Hey", null, 24, false, null, false, false);', script)
        self.assertNotIn("addByPrefix", script)
        self.assertEqual([], [d for d in converted["destinations"] if not d.startswith("char/")])

    def test_missing_export_folder_keeps_character_unsupported(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            # A folder with Animation.json but no spritemap is not an export.
            (fixture / "images/characters/hero").mkdir(parents=True)
            (fixture / "images/characters/hero/Animation.json").write_text("{}", newline='\n')
            converted = self.convert_character(fixture, {
                "version": "1.0.0", "name": "Hero", "renderType": "animateatlas",
                "assetPath": "characters/hero",
                "animations": [{"name": "idle", "prefix": "idle"}],
            })
        self.assertFalse(converted["supported"])
        self.assertIn("missing-asset", converted["codes"])
        self.assertEqual([], [d for d in converted["destinations"] if d.startswith("char/")])

    def test_animate_stage_props_share_one_export(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder)
            write_export(fixture / "images/stage/sign")
            stage = fixture / "stage.json"
            stage.write_text(json.dumps({
                "version": "1.0.0", "name": "Street", "cameraZoom": 1,
                "props": [
                    {"name": "signBack", "assetPath": "stage/sign", "animType": "animateatlas", "zIndex": 5,
                     "startingAnimation": "idle",
                     "animations": [{"name": "idle", "prefix": "Sign Back", "animType": "symbol"}]},
                    {"name": "signFront", "assetPath": "stage/sign", "animType": "animateatlas", "zIndex": 6,
                     "atlasSettings": {"applyStageMatrix": True},
                     "animations": [{"name": "idle", "prefix": "front", "frameIndices": [3], "looped": True}]},
                ],
            }), newline='\n')
            output = fixture / "out.json"
            self.run_haxe(f'''import haxe.Json;
class Main {{
  static function main() {{
    var c = VSliceImporter.convertStage(Json.parse(sys.io.File.getContent({haxe_string(stage)})),
      {haxe_string(fixture)}, "street", {haxe_string(stage)});
    new hscript.Parser().parseString(c.hscript);
    sys.io.File.saveContent({haxe_string(output)}, Json.stringify({{hscript: c.hscript,
      destinations: [for (a in c.assets) a.destination], codes: [for (d in c.diagnostics) d.code]}}));
  }}
}}
''')
            converted = json.loads(output.read_text())
        self.assertNotIn("missing-asset", converted["codes"])
        self.assertEqual(sorted(converted["destinations"]), sorted([
            "prop-signback-0/Animation.json", "prop-signback-0/spritemap1.json", "prop-signback-0/spritemap1.png"]))
        script = converted["hscript"]
        self.assertEqual(script.count("new FlxAnimate()"), 2)
        self.assertEqual(script.count('AnimateAtlasUtil.folder(hscriptPath + "prop-signback-0")'), 2)
        self.assertIn('AnimateAtlasUtil.addAnimation(vSliceProp_signback_0, "idle", "Sign Back", null, 24, false, "symbol", false, false);', script)
        self.assertIn('AnimateAtlasUtil.addAnimation(vSliceProp_signfront_1, "idle", "front", [3], 24, true, null, false, false);', script)
        self.assertIn("vSliceProp_signfront_1.applyStageMatrix = true;", script)
        self.assertNotIn("FlxAtlasFrames.fromSparrow", script)


if __name__ == "__main__":
    unittest.main()
