"""Codename note splash selection follows its XML data and owner scope."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


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


class CodenameNoteSplashTest(unittest.TestCase):
    def test_splash_xml_parsing_and_lane_selection(self):
        fixture = r'''class Main {
  static function main() {
    var xml = '<!DOCTYPE codename-engine-splashes><splashes sprite="game/splashes/ourple" alpha="0.6" scale="1.5" antialiasing="false">'
      + '<strum id="0"><anim name="leftA" anim="ourple left A" fps="18" x="3" y="-4" indices="0-2,5"/>'
      + '<anim name="leftB" anim="ourple left B"/></strum>'
      + '<strum id="1"><anim name="down" anim="ourple down"/></strum>'
      + '<anim name="shared" anim="shared splash" fps="12"/>'
      + '</splashes>';
    var data = CodenameSplashData.parse(xml);
    if (data == null || data.sprite != "game/splashes/ourple" || data.alpha != 0.6
      || data.scale != 1.5 || data.antialiasing || data.laneCount != 2)
      throw 'splash root fields did not parse';
    if (data.animationCountForLane(0) != 3 || data.animationCountForLane(2) != 3)
      throw 'lane/global animation mapping did not follow strum ids';
    var first = data.animationForLane(0, 0);
    if (first.name != "leftA" || first.prefix != "ourple left A" || first.fps != 18
      || first.x != 3 || first.y != -4 || first.indices.join(",") != "0,1,2,5")
      throw 'animation settings were not retained';
    if (data.animationForLane(0, 1).name != "leftB"
      || data.animationForLane(0, 2).name != "shared"
      || data.animationForLane(1, 0).name != "down"
      || data.animationForLane(2, 0).name != "leftA")
      throw 'random-choice index or modulo lane lookup failed';
    if (CodenameSplashData.parse('<splashes><strum id="0"/></splashes>') != null)
      throw 'missing sprite was accepted';
    if (CodenameSplashData.parse('<splashes sprite="../other/splash"><strum id="0"/></splashes>') != null)
      throw 'traversal sprite path was accepted';
  }
}'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(ROOT / "source"), "-cp", tmp, "-main", "Main", "--interp"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_smoke_marker_records_owner_animation_and_rendered_hit_state(self):
        smoke_source = (ROOT / "source/RuntimeSmokeHarness.hx").read_text()
        marker = extract_method(smoke_source, "public static function markCodenameNoteSplashRendered(")
        fixture = '''
class Note {
  public function new() {}
  public var splash:String = "ourple";
  public var strumTime:Float = 420;
  public var mustPress:Bool = true;
  public var isSustainNote:Bool = false;
  public var wasGoodHit:Bool = true;
}
class AnimationProbe { public function new() {} public var name:String = "codenameSplash"; public var curFrame:Int = 2; }
class ControllerProbe { public function new() {} public var curAnim:AnimationProbe = new AnimationProbe(); }
class ScaleProbe { public function new() {} public var x:Float = 1.5; public var y:Float = 1.5; }
class CodenameNoteSplash {
  public function new() {}
  public var animation:ControllerProbe = new ControllerProbe();
  public var renderable:Bool = true; public var exists:Bool = true;
  public var alive:Bool = true; public var visible:Bool = true;
  public var x:Float = 50; public var y:Float = 60;
  public var width:Float = 72; public var height:Float = 80;
  public var frameWidth:Int = 48; public var frameHeight:Int = 54;
  public var alpha:Float = 0.6; public var scale:ScaleProbe = new ScaleProbe();
  public var cameras:Array<Int> = [1];
}
class Main {
  static var finished:Bool = false;
  static var traceHits:Bool = true;
  static var lastMarker:Dynamic = null;
  static var markerCount:Int = 0;
  static function enabled():Bool return true;
  static function config():Dynamic return {tracePlayerHits:traceHits};
  static function emit(event:String, extra:Dynamic):Void {
    if (event == "codename_note_splash_rendered") { lastMarker = extra; markerCount++; }
  }
__METHOD__
  static function main() {
    var note = new Note();
    Main.markCodenameNoteSplashRendered(note, "assets/imported_mods/owner", "ourple",
      "game/splashes/ourple_splashes", "ourple left A", 0, new CodenameNoteSplash(), true);
    if (Main.markerCount != 1 || Reflect.field(Main.lastMarker, "ownerRoot") != "assets/imported_mods/owner"
      || Reflect.field(Main.lastMarker, "selectedSplash") != "ourple"
      || Reflect.field(Main.lastMarker, "noteSplash") != "ourple"
      || Reflect.field(Main.lastMarker, "noteWasGoodHit") != true
      || Reflect.field(Main.lastMarker, "noteMustPress") != true
      || Reflect.field(Main.lastMarker, "renderable") != true
      || Reflect.field(Main.lastMarker, "inSplashGroup") != true
      || Reflect.field(Main.lastMarker, "visible") != true || Reflect.field(Main.lastMarker, "alive") != true
      || Reflect.field(Main.lastMarker, "atlas") != "game/splashes/ourple_splashes"
      || Reflect.field(Main.lastMarker, "animationPrefix") != "ourple left A"
      || Reflect.field(Main.lastMarker, "animationFrame") != 2
      || Reflect.field(Main.lastMarker, "x") != 50 || Reflect.field(Main.lastMarker, "y") != 60
      || Reflect.field(Main.lastMarker, "width") != 72 || Reflect.field(Main.lastMarker, "height") != 80
      || Reflect.field(Main.lastMarker, "cameraCount") != 1)
      throw 'smoke marker omitted selected owner, hit or rendered splash evidence';
    Main.traceHits = false;
    Main.markCodenameNoteSplashRendered(note, "owner", "ourple", "atlas", "prefix", 0,
      new CodenameNoteSplash(), true);
    if (Main.markerCount != 1) throw 'smoke splash marker bypassed trace flag';
  }
}'''.replace("__METHOD__", marker)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", tmp, "-main", "Main", "--interp"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_codename_hit_uses_script_selected_splash_and_default_fallback(self):
        play_source = (ROOT / "source/PlayState.hx").read_text()
        note_source = (ROOT / "source/Note.hx").read_text()
        splash_source = (ROOT / "source/CodenameNoteSplash.hx").read_text()
        handler_source = (ROOT / "source/CodenameNoteSplashHandler.hx").read_text()
        dispatch = extract_method(play_source, "function hitCodenameNote(")
        select = extract_method(play_source, "function showCodenameNoteSplash(")
        self.assertNotIn("diagnoseUnsupportedCodenameNoteSplash", note_source)
        self.assertIn("super(0, 0, direction, 'normal', true)", splash_source)
        self.assertIn("MAX_ACTIVE_SPLASHES:Int = 8", handler_source)
        self.assertIn("while (members.length > MAX_ACTIVE_SPLASHES)", handler_source)
        self.assertIn("if (event.showSplash) showCodenameNoteSplash(event.note, strums, event.direction)", dispatch)
        self.assertIn("hasSplashDefinition(splashName)", select)
        self.assertIn("showSplash(splashName, receptor", select)
        self.assertIn("splashName == 'default'", select)
        self.assertIn("reportMissingSplash(splashName)", select)
        self.assertIn("markCodenameNoteSplashRendered(sourceNote, ownerRoot", handler_source)
        self.assertIn("codename_note_splash_rendered", (ROOT / "source/RuntimeSmokeHarness.hx").read_text())

        fixture = '''class Note { public var splash:String; public function new(value:String) splash = value; }
class Receptor { public function new() {} }
class Strumline {
  public var showNotesplash = true;
  public var sourceStrumScale = 1.25;
  public var members:Array<Receptor> = [new Receptor(), new Receptor(), new Receptor(), new Receptor()];
  public var spawned:Array<Int> = [];
  public function new() {}
  public function doSplash(direction:Int):Int { spawned.push(direction); return direction; }
}
class SplashGroup {
  public var spawned:Array<Int> = [];
  public function new() {}
  public function add(value:Int):Void spawned.push(value);
}
class CodenameNoteSplashHandler {
  public var exists:Bool = true;
  public var definitions:Array<String> = [];
  public var shown:Array<String> = [];
  public var reported:Array<String> = [];
  public function new() {}
  public function hasSplashDefinition(name:String):Bool return definitions.indexOf(name) >= 0;
  public function showSplash(name:String, receptor:Receptor, lineScale:Float, cameras:Array<Int>, ?sourceNote:Note):Bool {
    shown.push(name + ":" + lineScale);
    return true;
  }
  public function reportMissingSplash(name:String):Void reported.push(name);
}
class Main {
  public var codenameNoteSplashHandler:CodenameNoteSplashHandler;
  public var useNoteSplashes = true;
  public var grpNoteSplashes:SplashGroup = new SplashGroup();
  public var camHUD:Int = 1;
  public function new() {}
__METHOD__
  static function main() {
    var state = new Main();
    var line = new Strumline();
    var custom = new CodenameNoteSplashHandler();
    custom.definitions = ["ourple", "default"];
    state.codenameNoteSplashHandler = custom;
    state.showCodenameNoteSplash(new Note("ourple"), line, 2);
    if (custom.shown.join(",") != "ourple:1.25" || line.spawned.length != 0)
      throw 'custom owner splash did not take precedence';
    custom.definitions = ["ourple"];
    state.showCodenameNoteSplash(new Note("default"), line, 1);
    if (line.spawned.join(",") != "1") throw 'missing default definition did not retain native splash';
    state.showCodenameNoteSplash(new Note("not-staged"), line, 3);
    if (custom.reported.join(",") != "not-staged" || line.spawned.length != 1)
      throw 'missing custom definition fell back to a different splash';
    line.showNotesplash = false;
    state.showCodenameNoteSplash(new Note("ourple"), line, 0);
    if (custom.shown.length != 1) throw 'line splash gate was ignored';
    state.useNoteSplashes = false;
    line.showNotesplash = true;
    state.showCodenameNoteSplash(new Note("default"), line, 0);
    if (line.spawned.length != 1) throw 'global splash gate was ignored';
  }
}'''.replace("__METHOD__", select)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(tmp), "-main", "Main", "--interp"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cached_atlas_graphic_stays_alive_until_style_eviction(self):
        handler_source = (ROOT / "source/CodenameNoteSplashHandler.hx").read_text()
        retain = extract_method(handler_source, "function retainStyle(")
        release = extract_method(handler_source, "function releaseStyle(")
        self.assertIn("retainStyle(cached)", handler_source)
        self.assertIn("releaseStyle(evicted)", handler_source)
        self.assertIn("for (key in styleOrder.copy()) releaseStyle(key)", handler_source)

        fixture = '''
class GraphicProbe {
  public var useCount:Int = 0;
  public var isDestroyed:Bool = false;
  public function new() {}
  public function incrementUseCount():Void useCount++;
  public function decrementUseCount():Void {
    useCount--;
    if (useCount <= 0) isDestroyed = true;
  }
}
class FramesProbe {
  public var parent:GraphicProbe;
  public function new(parent:GraphicProbe) this.parent = parent;
}
typedef CachedCodenameSplash = { var frames:FramesProbe; }
class StyleMap {
  var values:Map<String, CachedCodenameSplash> = new Map();
  public function new() {}
  public function get(key:String):CachedCodenameSplash return values.get(key);
  public function set(key:String, value:CachedCodenameSplash):Void values.set(key, value);
  public function remove(key:String):Void values.remove(key);
}
class Main {
  var styles:StyleMap = new StyleMap();
  var styleOrder:Array<String> = [];
  public function new() {}
__METHODS__
  static function main() {
    var owner = new Main();
    var graphic = new GraphicProbe();
    var cached:CachedCodenameSplash = {frames:new FramesProbe(graphic)};
    owner.styles.set("ourple", cached);
    owner.styleOrder.push("ourple");
    owner.retainStyle(cached);
    graphic.incrementUseCount(); // one transient splash now uses the atlas
    graphic.decrementUseCount(); // destroying it must leave the cache's hold
    if (graphic.useCount != 1 || graphic.isDestroyed)
      throw 'transient splash destruction invalidated cached atlas frames';
    owner.releaseStyle("ourple");
    if (graphic.useCount != 0 || !graphic.isDestroyed
      || owner.styles.get("ourple") != null || owner.styleOrder.length != 0)
      throw 'style eviction did not release exactly one cache-held reference';
  }
}'''.replace("__METHODS__", retain + "\n" + release)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(HAXE), "-cp", str(tmp), "-main", "Main", "--interp"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
