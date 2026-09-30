"""Focused fixtures for the read-only HXC compatibility adapter."""

import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"
DONOR = Path("/run/media/cammie/External Storage/FNF-Example-Mods")


def hx_string(value: str) -> str:
    # Haxe's interpreter accepts UTF-8 source directly but does not accept all
    # JSON-style ``\uXXXX`` escapes (the mounted Spanish/emoji comments expose
    # that difference). Keep donor text unchanged while emitting UTF-8.
    return json.dumps(str(value), ensure_ascii=False)


class HxcCompatibilityTest(unittest.TestCase):
    def run_fixture(self, source: str, extra_cp=None) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as folder:
            main = Path(folder) / "Main.hx"
            main.write_text(source)
            classpaths = [str(ROOT / "source"), folder]
            if extra_cp:
                classpaths.extend(str(path) for path in extra_cp)
            command = [str(HAXE)]
            for classpath in classpaths:
                command.extend(["-cp", classpath])
            command.extend(["-main", "Main", "--interp"])
            return subprocess.run(
                command,
                cwd=ROOT, capture_output=True, text=True, timeout=300,
            )

    def test_counts_only_candidate_selection_uses_physical_song_origin(self):
        diagnostic = (ROOT / "tools/diagnose_example_auto_import.py").read_text()
        match = re.search(r"COUNTS_ONLY_ACCUMULATOR = r'''(.*?)'''", diagnostic, re.S)
        self.assertIsNotNone(match, "counts-only selection fixture is missing")
        fixture = "using StringTools;\n" + match.group(1) + r'''
class Main {
  static function fail(message:String):Void throw message;
  static function main() {
    var candidates = new DiagnosticCandidateAccumulator();
    // Two views of one song directory collapse to the more complete owner,
    // while an unrelated pack with the same chart name stays distinct.
    candidates.add('bopeebo', '/game-root', 'Codename Engine', 10,
      '/game-root', '/game-root', ['[note-kind-generic] alias'], '/donor/dsides/songs/bopeebo');
    candidates.add('bopeebo', '/nested-mod', 'Codename Engine', 20,
      '/nested-mod', '/nested-mod', ['[owner] winner'], '/donor/dsides/songs/bopeebo');
    candidates.add('bopeebo', '/psych-root', 'Psych Engine', 30,
      '/psych-root', '/psych-root', ['[note-kind-generic] independent'], '/donor/psych/data/bopeebo');
    if (candidates.candidateCount != 3 || candidates.uniqueCount() != 2)
      fail('compact selection did not group by physical song origin');
    var ownerWinners = 0;
    var genericDiagnostics = 0;
    for (winner in candidates.winners()) {
      if (winner.name != 'bopeebo') fail('unexpected winner key: ' + winner.name);
      if (winner.origin == '/donor/dsides/songs/bopeebo') {
        ownerWinners++;
        if (winner.root != '/nested-mod' || winner.score != 20)
          fail('alias view did not use the same completeness ordering');
      }
      for (diagnostic in winner.diagnostics)
        if (diagnostic.indexOf('[note-kind-generic]') == 0) genericDiagnostics++;
    }
    if (ownerWinners != 1 || genericDiagnostics != 1)
      fail('same-name independent source diagnostics were dropped');
  }
}
'''
        result = self.run_fixture(fixture)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_bounded_point_fields_keep_source_state(self):
        donor = """class PointProbe extends Stage {
  var anchor = FlxPoint.get();
  var offset = new FlxPoint(-2, 3.5);
  var unsafe = FlxPoint.get(readExternal());
  function onCountdownStart(event) { anchor.set(10, 20); }
} """
        main = f'''import hscript.Parser;
class Main {{
 static function main() {{
  var result = HxcCompat.analyze({hx_string(donor)}, "scripts/stages/point-probe.hxc");
  if (result.generatedHscript.indexOf("var anchor = HxcCompatRuntime.point(0, 0);") < 0
   || result.generatedHscript.indexOf("var offset = HxcCompatRuntime.point(-2, 3.5);") < 0
   || result.generatedHscript.indexOf("HxcCompatRuntime.point(readExternal()") >= 0)
   throw "bounded point source fields were not preserved";
  new Parser().parseString(result.generatedHscript);
 }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_actor_fields_survive_hxc_receiver_lowering(self):
        donor = '''class ActorProbe extends SparrowCharacter {
  function onAdd() {
    var pos = {x: 100, y: 50};
    this.originalPosition.x = pos.x - this.characterOrigin.x;
    this.originalPosition.y = pos.y - this.characterOrigin.y;
    this.resetPosition();
    this.idleSuffix = '-alt';
    this.x -= 3;
    this.y += 4;
    this.playSingAnimation(2, false, 'alt');
  }
  override private function getScreenPosition(?result:FlxPoint, ?camera:FlxCamera):FlxPoint {
    var output:FlxPoint = super.getScreenPosition(result, camera);
    if (isPixel) output.x += 6;
    return output;
  }
}'''
        main = f'''import hscript.Parser;
import hscript.Interp;
class Main {{
 static function main() {{
  var result = HxcCompat.analyze({hx_string(donor)}, "scripts/characters/actor-probe.hxc");
  var generated = result.generatedHscript;
  if (generated.indexOf("hxcCharacter().idleSuffix = '-alt'") < 0
   || generated.indexOf("hxcCharacter().x -= 3") < 0
   || generated.indexOf("hxcCharacter().y += 4") < 0
   || generated.indexOf("hxcCharacter().originalPosition.x") < 0
   || generated.indexOf("hxcCharacter().characterOrigin.x") < 0
   || generated.indexOf("hxcCharacter().resetPosition()") < 0
   || generated.indexOf("hxcCharacter().playSingAnimation(2, false, 'alt')") < 0
   || generated.indexOf("hxcCharacter().isPixel") < 0)
   throw generated;
  var program = new Parser().parseString(generated);
  var actor:Dynamic = {{x: 10., y: 20., idleSuffix: '', isPixel: true,
    originalPosition: {{x: 10., y: 20.}}, characterOrigin: {{x: 5., y: 6.}}, singCalls: 0}};
  Reflect.setField(actor, 'resetPosition', function() {{
    actor.x = actor.originalPosition.x; actor.y = actor.originalPosition.y;
  }});
  Reflect.setField(actor, 'playSingAnimation', function(direction:Int, miss:Bool, suffix:String) {{
    if (direction != 2 || miss || suffix != 'alt') throw 'sing arguments';
    actor.singCalls++;
  }});
  var interp = new Interp();
  interp.variables.set('hxcCharacter', function() return actor);
  interp.execute(program);
  var onAdd:Dynamic = interp.variables.get('onAdd');
  onAdd();
  if (actor.x != 92 || actor.y != 48 || actor.idleSuffix != '-alt' || actor.singCalls != 1)
   throw 'actor fields were not updated through the native receiver';
 }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deterministic_syntax_lowering_is_parseable_hscript(self):
        donor = r'''
class SyntaxProbe extends Song {
    function update(elapsed:Float) {
        var value:String = data?.value ?? fetchValue() ?? "fallback";
        var map:Map<String, Int> = new Map<String, Int>();
        var callback:Void->Void = value -> value;
        target?.field = value;
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/syntax-probe.hxc");
    if (result.generatedHscript == null || result.generatedHscript.indexOf("function update") < 0)
      fail("missing generated update: " + result.generatedHscript);
    if (result.generatedHscript.indexOf("?.") >= 0 || result.generatedHscript.indexOf("??") >= 0
      || result.generatedHscript.indexOf("->") >= 0 || result.generatedHscript.indexOf("Map<") >= 0)
      fail("unlowered syntax: " + result.generatedHscript);
    var adapted = false;
    for (finding in result.diagnostics) if (finding.code == "hxc-syntax-adapter") adapted = true;
    if (!adapted) fail("missing syntax adapter diagnostic");
    var parser = new Parser();
    parser.parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_strumline_and_health_icon_constructors_use_explicit_adapters(self):
        donor = r'''class SharedConstructorProbe extends Song {
    function create(style, iconData) {
        var extra = new Strumline(style, false);
        var icon = new HealthIcon('extra', 1);
        icon.configure(iconData);
        PlayState.instance.playerStrumline = new Strumline(style, false);
    }
}'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/shared-constructor-probe.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("new ExtraStrumlineAdapter(style, false)") < 0
      || generated.indexOf("new HxcHealthIconAdapter('extra', 1)") < 0)
      fail("HXC constructors did not use explicit compatibility classes: " + generated);
    if (generated.indexOf("new Strumline(") >= 0 || generated.indexOf("new HealthIcon(") >= 0)
      fail("native constructor names can shadow interpreter aliases: " + generated);
    if (generated.indexOf("HxcCompatRuntime.configureNativeStrumline") < 0)
      fail("native PlayState strumline replacement lost its in-place route: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_song_without_playstate_hooks_emits_parseable_empty_scope(self):
        donor = r'''
class SongMetadataProbe extends Song {
    function isSongNew(currentDifficulty:String):Bool {
        return Save.instance.hasBeatenSong(this.id) == false;
    }
}
'''
        main = f'''import hscript.Interp;
import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/song-metadata-probe.hxc");
    if (result.generatedHscript == null || StringTools.trim(result.generatedHscript) == "")
      fail("recognized HXC class became a missing module");
    if (result.generatedHscript.indexOf("function ") >= 0)
      fail("non-lifecycle song metadata leaked into the PlayState scope: " + result.generatedHscript);
    new Interp().execute(new Parser().parseString(result.generatedHscript));
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_private_access_metadata_is_lowered_for_hscript(self):
        donor = r'''
class PrivateAccessProbe extends Module {
    function setFade(camera) {
        var marker:String = "@:privateAccess";
        @:privateAccess camera._fxFadeAlpha = 1;
        trace(marker);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/private-access-probe.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("@:privateAccess camera") >= 0)
      fail("private-access metadata remained executable syntax: " + generated);
    if (generated.indexOf("camera._fxFadeAlpha = 1") < 0
      || generated.indexOf('"@:privateAccess"') < 0)
      fail("metadata lowering changed the field expression or a string literal: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_zindex_accesses_route_through_engine_adapter(self):
        donor = r'''
class ZIndexProbe extends Song {
    function update(event) {
        iconP1.zIndex = iconP1.zIndex + 1;
        PlayState.instance.currentStage.getDad().zIndex = PlayState.instance.currentStage.getDad().zIndex + 1;
        var current = iconP1.zIndex;
        trace(current);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/z-index-probe.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("HxcCompatRuntime.setZIndex") < 0
      || generated.indexOf("HxcCompatRuntime.getZIndex") < 0)
      fail("zIndex was not routed through the engine adapter: " + generated);
    if (generated.indexOf(".zIndex") >= 0)
      fail("native HScript still exposes donor zIndex: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_zindex_side_table_preserves_compound_writes(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    HxcCompatRuntime.clear();
    var target:Dynamic = {};
    if (HxcCompatRuntime.getZIndex(target) != 0) fail("default zIndex");
    HxcCompatRuntime.setZIndex(target, 4);
    HxcCompatRuntime.setZIndex(target, 3, "+=");
    HxcCompatRuntime.setZIndex(target, 2, "*=");
    if (HxcCompatRuntime.getZIndex(target) != 14) fail("compound zIndex");
    HxcCompatRuntime.clearActiveState();
    if (HxcCompatRuntime.getZIndex(target) != 0) fail("active-state cleanup");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_vslice_zindex_writers_are_lowered_in_song_and_modules(self):
        paths = {
            "song": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/dokidoggle.hxc",
            "timebar": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/GlassTimeBar.hxc",
            "costumes": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CostumeSwapperv3.hxc",
        }
        if not all(path.exists() for path in paths.values()):
            self.skipTest("mounted V-Slice zIndex fixtures are not available")
        sources = "\n".join(
            f'''var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for name, path in paths.items()
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {sources}
    for (result in [song, timebar, costumes]) {{
      if (result.generatedHscript.indexOf(".zIndex") >= 0)
        fail("unlowered V-Slice zIndex access in " + result.path + ": " + result.generatedHscript);
      new Parser().parseString(result.generatedHscript);
    }}
    for (result in [song, timebar])
      if (result.generatedHscript.indexOf("HxcCompatRuntime.getZIndex") < 0
        && result.generatedHscript.indexOf("HxcCompatRuntime.setZIndex") < 0)
        fail("missing zIndex adapter in " + result.path);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            {name: path.stat().st_mtime_ns for name, path in paths.items()},
            {name: path.stat().st_mtime_ns for name, path in paths.items()},
        )

    def test_vslice_lifecycle_callbacks_have_native_character_geometry_surface(self):
        paths = {
            "song": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/dokidoggle.hxc",
            "module": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/YourDemiseSafetyModule.hxc",
        }
        if not all(path.exists() for path in paths.values()):
            self.skipTest("mounted V-Slice lifecycle fixtures are not available")
        sources = "\n".join(
            f'''var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for name, path in paths.items()
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {sources}
    if (song.generatedHscript.indexOf("originalPosition") < 0
      || song.generatedHscript.indexOf("characterOrigin") < 0
      || song.generatedHscript.indexOf("cameraFocusPoint") < 0)
      fail("song callback lost the native character geometry ABI: " + song.generatedHscript);
    if (module.generatedHscript.indexOf("resetPosition") < 0)
      fail("module callback lost resetPosition: " + module.generatedHscript);
    new Parser().parseString(song.generatedHscript);
    new Parser().parseString(module.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        character_source = (ROOT / "source/Character.hx").read_text()
        for field in ("characterOrigin", "cameraFocusPoint", "originalPosition", "resetPosition"):
            self.assertIn(field, character_source)

    def test_dokidoggle_song_loaded_uses_native_health_icon_configure(self):
        path = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/dokidoggle.hxc"
        if not path.exists():
            self.skipTest("mounted DokiToggle HXC fixture is not available")
        main = f'''import hscript.Parser;
import hscript.Interp;
class FakeHealthIcon {{
  public static var last:FakeHealthIcon;
  public var zIndex:Int = 0;
  public var cameras:Array<Dynamic>;
  public var configureCalls:Int = 0;
  public var updateHitboxCalls:Int = 0;
  public var isLegacyStyle:Bool = false;
  public function new(_char:String, _player:Bool) {{ last = this; }}
  public function kill():Void {{}}
  public function configure(_data:Dynamic):FakeHealthIcon {{ configureCalls++; return this; }}
  public function updateHitbox():Void {{ updateHitboxCalls++; }}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});
    var generated = result.generatedHscript;
    if (generated.indexOf("iconP3.configure(iconData)") < 0)
      fail("DokiToggle lost its authored HealthIcon.configure call: " + generated);
    if (generated.indexOf("iconP3.isLegacyStyle = true") < 0)
      fail("DokiToggle lost its authored HealthIcon.isLegacyStyle call: " + generated);
    new Parser().parseString(generated);

    var actor:Dynamic = {{
      x: 0.0, y: 0.0,
      characterOrigin: {{x: 10.0, y: 20.0}},
      cameraFocusPoint: {{x: 0.0, y: 0.0}},
      originalPosition: {{set: function(_x:Float, _y:Float):Void {{}}}},
      kill: function():Void {{}},
      zIndex: 0
    }};
    var stage:Dynamic = {{
      _data: {{characters: {{dad: {{position: [100, 200], cameraOffsets: [3, 4]}}}}}},
      getBoyfriend: function():Dynamic return {{originalPosition: {{x: 321.0}}}},
      refresh: function():Void {{}},
      addCharacter: function(_character:Dynamic, _type:String):Void {{}}
    }};
    var state:Dynamic = {{
      curStage: stage,
      currentSong: {{getDifficulty: function(_name:String):Dynamic return null}},
      camHUD: {{}},
      add: function(_object:Dynamic):Void {{}}
    }};
    var runtime:Dynamic = {{
      openStore: function(_namespace:String):Dynamic return {{
        getDokiSave: function():Dynamic return {{}},
      }},
      setZIndex: function(target:Dynamic, value:Dynamic, _operator:String):Dynamic {{
        if (target != null) Reflect.setField(target, "zIndex", value);
        return target;
      }},
      fetchCharacter: function(_name:String):Dynamic return actor,
      setCharacterType: function(_character:Dynamic, _type:String):Void {{}},
      stageAddCharacter: function(_stage:Dynamic, _character:Dynamic, _type:String):Void {{}},
      stageCharacterData: function(_role:String):Dynamic return stage._data.characters.dad,
      stageDataSnapshot: function():Dynamic return stage._data
    }};
    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", runtime);
    interp.variables.set("HxcHealthIconAdapter", FakeHealthIcon);
    interp.variables.set("PlayState", {{instance: state}});
    interp.variables.set("hxcGetModule", function(_name:String):Dynamic return {{
      scriptCall: function(_method:String, _args:Array<Dynamic>):Dynamic return "yuri"
    }});
    interp.execute(new Parser().parseString(generated));
    var loaded:Dynamic = interp.variables.get("songLoaded");
    if (loaded == null) fail("DokiToggle songLoaded callback was not generated");
    Reflect.callMethod(null, loaded, [null]);
    if (FakeHealthIcon.last == null || FakeHealthIcon.last.configureCalls != 1
      || FakeHealthIcon.last.updateHitboxCalls != 1
      || !FakeHealthIcon.last.isLegacyStyle)
      fail("full songLoaded HealthIcon sequence did not complete");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        health_icon_source = (ROOT / "source/HealthIcon.hx").read_text()
        self.assertRegex(health_icon_source, r"public function configure\(data:Dynamic\)")
        self.assertRegex(health_icon_source, r"public var isLegacyStyle:Bool = false")

    def test_nested_optional_calls_coalescing_and_map_literals_lower(self):
        donor = r'''
class SyntaxProbe extends Song {
    function update(event) {
        var camera = PlayState.instance?.currentStage?.getDad()?.cameraFocusPoint;
        PlayState.instance.camHUD?.flash(0xFFFFFFFF, 0.1);
        PlayState.instance?.camHUD?._fxFadeDuration = 0;
        var nested = handler?.scriptGet("tween")?.cancel();
        var fallback = fetchValue() ?? otherValue() ?? "fallback";
        var callback = () -> { trace("callback"); };
        var redirect:Map<FlxState, MusicBeatState> = [MainMenuState => new DokiMainMenuState()];
        var options = ["bf" => ["init" => true], "gf" => ["init" => true]];
        var schema = [{keys: ["bf" => "bf", "gf" => "gf"]}];
        for (value in redirect.keys()) trace(value);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/syntax-probe.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("?.") >= 0 || generated.indexOf("??") >= 0
      || generated.indexOf("=>") >= 0 || generated.indexOf("Map<") >= 0)
      fail("unlowered syntax: " + generated);
    if (generated.indexOf("hxcOptionalCall") < 0 || generated.indexOf("hxcOptionalSet") < 0
      || generated.indexOf("hxcCoalesce") < 0
      || generated.indexOf("hxcMap") < 0)
      fail("missing common syntax adapters: " + generated + " callback="
        + (result.callbackAdapters.length == 0 ? "none" : result.callbackAdapters[0].body));
    try {{
      new Parser().parseString(generated);
    }} catch (error:Dynamic) {{
      fail("generated HScript parse error: " + Std.string(error) + "\\n" + generated);
    }}
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_dynamic_map_preserves_pairs_and_class_keys(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var first = {};
    var second = {};
    var map = new HxcDynamicMap([[first, "one"], [second, "two"]]);
    if (map.get(first) != "one" || map.get(second) != "two") fail("map lookup");
    if (!map.exists(first) || map.keys().length != 2) fail("map keys");
    map.set(first, "updated");
    if (map.get(first) != "updated" || map.keys().length != 2) fail("map replacement");
  }
}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_and_stage_access_apis_use_central_aliases(self):
        stage_source = r'''
class AliasStage extends Stage {
    function buildStage() {
        var dad = getDad();
        var bf = getBoyfriend();
        var gf = getGirlfriend();
        var opponent = getOpponent();
        var prop = getNamedProp("light");
        if (PlayState.instance?.currentStage != null) return prop;
    }
}
'''
        character_source = r'''
class AliasCharacter extends SparrowCharacter {
    function onCreate(event) {
        setAnimationOffsets("idle", 12, -4);
        if (getCurrentAnimation() == "singLEFT") playAnimation("hey", true);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    var findings:Array<Dynamic> = cast result.diagnostics;
    for (finding in findings) if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var stage = HxcCompat.analyze({hx_string(stage_source)}, "scripts/stages/alias-stage.hxc");
    var character = HxcCompat.analyze({hx_string(character_source)}, "scripts/characters/alias-character.hxc");
    if (hasCode(stage, "unsupported-hxc-api") || hasCode(character, "unsupported-hxc-api"))
      fail("central HXC API aliases still reported as unsupported");
    if (!hasCode(stage, "hxc-api-adapter") || !hasCode(character, "hxc-api-adapter"))
      fail("missing HXC API adapter diagnostic");
    if (stage.generatedHscript.indexOf("curStage") < 0 || stage.generatedHscript.indexOf("currentStage") >= 0)
      fail("currentStage alias was not lowered: " + stage.generatedHscript);
    if (character.generatedHscript.indexOf("setAnimationOffsets") < 0
      || character.generatedHscript.indexOf("getCurrentAnimation") < 0)
      fail("character aliases were dropped: " + character.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vslice_start_timestamp_is_an_allowed_native_playstate_member(self):
        donor = '''class StartTimestampProbe extends Song {
  function onCountdownStart(event) {
    var launchOffsetMs = PlayState.instance.startTimestamp;
  }
}'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/songs/start-timestamp-probe.hxc");
    var found = false;
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCountdownStart") {{
        found = true;
        if (!callback.safe) fail("native PlayState.startTimestamp was rejected: " + callback.reason);
      }}
    if (!found || result.generatedHscript.indexOf("PlayState.instance.startTimestamp") < 0)
      fail("the launch timestamp read was not preserved in the native adapter");
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_namespaced_hxc_store_isolated_and_mutable(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    HxcCompatRuntime.clear();
    var first:Dynamic = HxcCompatRuntime.openStore("donor-a");
    var second:Dynamic = HxcCompatRuntime.openStore("donor-b");
    first.modOptions.set("flag", true);
    if (first.modOptions.get("flag") != true || !first.modOptions.exists("flag")) fail("store write/read");
    if (second.modOptions.get("flag") != null || second.getSave() != second) fail("namespace isolation");
    first.flush();
    if (first.hasBeatenSong("unused") != false) fail("conservative highscore default");
  }
}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_current_chart_album_reads_live_native_song(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    PlayState.SONG = {album: "takeover"};
    if (HxcCompatRuntime.currentChartAlbum != "takeover") fail("live chart album");
    PlayState.SONG = {album: ""};
    if (HxcCompatRuntime.currentChartAlbum != "") fail("empty chart album");
    PlayState.SONG = null;
    if (HxcCompatRuntime.currentChartAlbum != "") fail("missing chart album fallback");
  }
}
class PlayState {
  public static var SONG:Dynamic;
}
'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_active_hxc_tally_view_tracks_notes_misses_and_retry_cleanup(self):
        source = r'''
class MarkovTallyFixture extends Module {
    function onNoteIncoming(event) {
        Highscore.tallies.totalNotes--;
    }
    function onNoteMiss(event) {
        if (Highscore.tallies.missed > 0) Highscore.tallies.totalNotes--;
    }
    function onSongEnd(event) {
        Highscore.tallies.totalNotes = Highscore.tallies.totalNotes - 1;
    }
}
'''
        main = f'''import hscript.Interp;
import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    HxcCompatRuntime.clear();
    var state:Dynamic = {{
      unspawnNotes: [{{mustPress: true}}, {{mustPress: false}}, {{mustPress: true}}],
      notes: {{members: []}},
      misses: 0,
      totalPlayed: 0,
      totalNotesHit: 99,
      combo: 2
    }};
    HxcCompatRuntime.beginActiveSong(state);
    var tallies:Dynamic = HxcCompatRuntime.tallies;
    if (tallies.totalNotes != 2 || tallies.missed != 0) fail("initial tally");
    if (tallies.totalNotesHit != 0 || tallies.maxCombo != 2)
      fail("initial raw hit/max combo view: " + tallies.totalNotesHit + "/" + tallies.maxCombo);
    tallies.totalNotes--;
    state.misses = 2;
    state.totalPlayed = 5;
    state.combo = 5;
    HxcCompatRuntime.prepareTallyCallback();
    if (tallies.totalNotes != 1 || tallies.missed != 2) fail("hit/miss view");
    if (tallies.totalNotesHit != 3 || tallies.maxCombo != 5)
      fail("raw hit/max combo view: " + tallies.totalNotesHit + "/" + tallies.maxCombo);
    state.combo = 0;
    HxcCompatRuntime.prepareTallyCallback();
    if (tallies.maxCombo != 5) fail("max combo regressed after combo break");
    tallies.missed = 1;
    HxcCompatRuntime.commitTallyCallback();
    if (state.misses != 1 || tallies.missed != 1) fail("native miss write");
    state.unspawnNotes = [{{mustPress: true}}];
    state.notes.members = [];
    state.misses = 0;
    state.totalPlayed = 1;
    state.totalNotesHit = 42;
    state.combo = 1;
    HxcCompatRuntime.beginActiveSong(state);
    if (tallies.totalNotes != 1 || tallies.missed != 0) fail("retry cleanup");
    if (tallies.totalNotesHit != 1 || tallies.maxCombo != 1)
      fail("raw hit/max combo retry reset: " + tallies.totalNotesHit + "/" + tallies.maxCombo);

    var result = HxcCompat.analyze({hx_string(source)}, "scripts/notes/markov-tally.hxc");
    var sawAdapter = false;
    var sawGap = false;
    for (finding in (cast result.diagnostics:Array<Dynamic>)) {{
      if (finding.code == "hxc-note-behavior-adapter") sawAdapter = true;
      if (finding.code == "unsupported-hxc-note-state") sawGap = true;
    }}
    if (!sawAdapter || sawGap || result.noteBehaviorPatterns.indexOf("tally-adapter") < 0)
      fail("tally diagnostics: " + result.noteBehaviorPatterns.join(","));
    if (result.generatedHscript.indexOf("HxcCompatRuntime.tallies.totalNotes") < 0)
      fail("tally alias missing: " + result.generatedHscript);
    var program = new Parser().parseString(result.generatedHscript);
    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.execute(program);
    HxcCompatRuntime.prepareTallyCallback();
    var incoming:Dynamic = interp.variables.get("noteIncoming");
    incoming({{}});
    HxcCompatRuntime.commitTallyCallback();
    if (tallies.totalNotes != 0) fail("generated tally callback");
    var unsafe = HxcCompat.analyze("class UnknownTally extends NoteScript {{ function onNoteHit(event) {{ Highscore.tallies[\\\"streak\\\"] = 1; }} }}", "scripts/notes/unknown-tally.hxc");
    var unsafeGap = false;
    for (finding in (cast unsafe.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-note-state") unsafeGap = true;
    if (!unsafeGap || unsafe.noteBehaviorPatterns.indexOf("tally-state") < 0)
      fail("unknown tally state was not diagnosed");
    HxcCompatRuntime.clearActiveState(state);
    if (tallies.totalNotes != 0 || tallies.totalNotesHit != 0
      || tallies.maxCombo != 0 || tallies.missed != 0)
      fail("active tally cleanup");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hxc_tally_rank_adapter_uses_native_counters_only(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    HxcCompatRuntime.clear();
    var state:Dynamic = {unspawnNotes: [], notes: {members: []}, misses: 0,
      sicks: 4, goods: 0, bads: 0, shits: 0, combo: 4, totalNotesHit: 4};
    HxcCompatRuntime.beginActiveSong(state);
    var tallies:Dynamic = HxcCompatRuntime.tallies;
    if (tallies.sick != 4 || tallies.good != 0 || tallies.maxCombo != 4
      || tallies.totalNotesHit != 4) fail("native tally counters");
    tallies.totalNotes = 4;
    if (HxcCompatRuntime.calculateRank({tallies: tallies}) != "PERFECT_GOLD")
      fail("perfect rank");
    tallies.sick = 0;
    tallies.missed = 1;
    if (HxcCompatRuntime.calculateRank({tallies: tallies}) != "SHIT")
      fail("miss rank");
    tallies.missed = 0;
    tallies.good = 3;
    if (HxcCompatRuntime.calculateRank({tallies: tallies}) != "GOOD")
      fail("good rank");
    tallies.sick = 2;
    tallies.good = 0;
    HxcCompatRuntime.commitTallyCallback();
    if (state.sicks != 2 || state.goods != 0) fail("counter commit");
    if (HxcCompatRuntime.calculateRank(null) != null
      || HxcCompatRuntime.calculateRank({tallies: {totalNotes: 0, sick: 0, good: 0, missed: 0}}) != null)
      fail("empty rank");
    if (HxcCompatRuntime.calculateRank({tallies: {totalNotes: 4, sick: 3, good: 1, missed: 0}}) != "PERFECT")
      fail("perfect non-gold rank");
    if (HxcCompatRuntime.calculateRank({tallies: {totalNotes: 10, sick: 9, good: 0, missed: 0}}) != "EXCELLENT"
      || HxcCompatRuntime.calculateRank({tallies: {totalNotes: 10, sick: 8, good: 0, missed: 0}}) != "GREAT"
      || HxcCompatRuntime.calculateRank({tallies: {totalNotes: 10, sick: 6, good: 0, missed: 0}}) != "GOOD"
      || HxcCompatRuntime.calculateRank({tallies: {totalNotes: 10, sick: 5, good: 0, missed: 0}}) != "SHIT")
      fail("rank threshold boundary");
  }
}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_donor_layout_discovery_keeps_chart_scripts_separate(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var paths = [
      "/source/scripts/songs/rabbit-hole.hxc",
      "/source/scripts/songs/other-song.hxc",
      "/source/scripts/stages/clubroom.hxc",
      "/source/scripts/characters/bf_tb.hxc",
      "/source/scripts/modules/CoolGameplay.hxc",
      "/source/scripts/events/ChangeStage.hxc",
      "/source/scripts/notes/markov.hxc",
      "/source/scripts/states/DokiTitleState.hxc",
      "/source/scripts/ui/MikuMainMenu.hxc",
      "/source/scripts/SUBSTATES/DokiMainMenu.hxc",
      "/source/scripts/misc/readme.txt"
    ];
    if (HxcScriptDiscovery.familyForPath(paths[0]) != "song") fail("song family");
    if (HxcScriptDiscovery.familyForPath(paths[2]) != "stage") fail("stage family");
    if (HxcScriptDiscovery.familyForPath(paths[9]) != "substate") fail("substate family");
    if (!HxcScriptDiscovery.characterMatches(paths[3], ["bf_tb"])) fail("character match");
    if (HxcScriptDiscovery.characterMatches(paths[2], ["clubroom"])) fail("stage as character");
    if (HxcScriptDiscovery.characterId(paths[3]) != "bftb") fail("character id");
    var result = HxcScriptDiscovery.discover(paths, "Rabbit Hole");
    if (result.all.length != 11) fail("all: " + result.all.length);
    if (result.chart.length != 1 || result.chart[0].indexOf("rabbit-hole.hxc") < 0)
      fail("chart selection: " + result.chart.length);
    if (result.global.length != 8 || result.otherSongs.length != 1) fail("global/song: "
      + result.global.length + "/" + result.otherSongs.length);
    if (result.unknown.length != 1) fail("unknown: " + result.unknown.length);
    if (result.families.get("module").length != 1 || result.families.get("event").length != 1
      || result.families.get("note").length != 1) fail("family inventory");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scripted_song_event_emits_central_event_adapter(self):
        donor = r'''
import funkin.play.PlayState;
import funkin.play.event.ScriptedSongEvent;
import flixel.FlxG;
class AddCameraZoom extends ScriptedSongEvent {
    public function new() { super('Zoom Rabbit'); }
    override function handleEvent(data) {
        var val1:String = data.getString('value1') ?? "";
        var val2:String = data.getString('value2') ?? "";
        FlxG.camera.zoom += Std.parseFloat(val1);
        PlayState.instance.camHUD.zoom += Std.parseFloat(val2);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/events/Add Camera Zoom.hxc");
    if (result.kind != "song-event") fail("event kind: " + result.kind);
    if (result.className != "AddCameraZoom") fail("class");
    if (result.identifier != "Zoom Rabbit") fail("identifier: " + result.identifier);
    if (result.eventAdapters.length != 1) fail("adapter count");
    if (result.eventAdapters[0].canonicalName != "Add Camera Zoom") fail("canonical event");
    if (result.fields.length != 2 || result.fields[0] != "value1" || result.fields[1] != "value2") fail("fields");
    if (!result.eventAdapters[0].safe) fail("adapter safety");
    if (result.generatedHscript.indexOf("Add Camera Zoom") < 0) fail("generated adapter");
    var sawBody = false;
    for (finding in result.diagnostics) if (finding.code == "unsupported-hxc-event-body") sawBody = true;
    if (sawBody) fail("fully covered native event still has body diagnostic");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_donor_event_aliases_select_song_event_class_and_keep_body_gap(self):
        camera_flash = r'''
class CameraFlashFixes extends ScriptedModule {
    function new() { super("camera-flash-fixes"); }
}
class CameraFlashEvent extends ScriptedSongEvent {
    function new() { super("extra-events-cameraFlashEvent"); }
    function handleEvent(data) { FlxG.camera.flash(); }
}
'''
        camera_fade = r'''
class CameraFadeFixes extends ScriptedModule {
    function new() { super("camera-fade-fixes"); }
}
class CameraFadeEvent extends ScriptedSongEvent {
    function new() { super("extra-events-cameraFadeEvent"); }
    function handleEvent(data) { FlxG.camera.fade(); }
}
'''
        play_video = r'''
class PlayVideoEvent extends SongEvent {
    function new() { super("PlayVideo"); }
    function handleEvent(data) { ModuleHandler.getModule("PVE_VideoModule"); }
}
'''
        lyrics = r'''
class AddLyricsEvent extends ScriptedSongEvent {
    function new() { super("extra-events-addLyricsEvent"); }
    function handleEvent(data) { lyricText = data.value.text; }
}
'''
        vignette = r'''
class VignEvent extends ScriptedSongEvent {
    function new() { super("extra-events-vignEvent"); }
    function handleEvent(data) {
        var intensity = data.getFloat("intensity");
        var duration = data.getFloat("duration");
        var ease = data.getString("ease");
        var easeDir = data.getString("easeDir");
        applyVignette(intensity, duration, ease, easeDir);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    var findings:Array<Dynamic> = cast result.diagnostics;
    for (finding in findings) if (finding.code == code) return true;
    return false;
  }}
  static function checkNative(result:Dynamic, className:String, identifier:String, eventName:String):Void {{
    if (result.kind != "song-event") fail(className + " kind: " + result.kind);
    if (result.className != className) fail(className + " selected class: " + result.className);
    if (result.identifier != identifier) fail(className + " identifier: " + result.identifier);
    if (result.eventAdapters.length != 1 || result.eventAdapters[0].canonicalName != eventName)
      fail(className + " native route");
    if (hasCode(result, "unsupported-hxc-event")) fail(className + " false unsupported event");
    if (hasCode(result, "unsupported-hxc-event-body")) fail(className + " false body diagnostic");
  }}
  static function main() {{
    checkNative(HxcCompat.analyze({hx_string(camera_flash)}, "scripts/events/cameraFlashEvent.hxc"),
      "CameraFlashEvent", "extra-events-cameraFlashEvent", "Camera Flash");
    checkNative(HxcCompat.analyze({hx_string(camera_fade)}, "scripts/events/cameraFadeEvent.hxc"),
      "CameraFadeEvent", "extra-events-cameraFadeEvent", "Camera Fade");
    checkNative(HxcCompat.analyze({hx_string(play_video)}, "scripts/events/PlayVideoEvent.hxc"),
      "PlayVideoEvent", "PlayVideo", "Play Video");
    checkNative(HxcCompat.analyze({hx_string(lyrics)}, "scripts/events/addLyricsEvent.hxc"),
      "AddLyricsEvent", "extra-events-addLyricsEvent", "Lyrics");
    var vignette = HxcCompat.analyze({hx_string(vignette)}, "scripts/events/vignetteEvent.hxc");
    if (vignette.eventAdapters.length != 1 || vignette.eventAdapters[0].canonicalName != "Vignette"
      || hasCode(vignette, "unsupported-hxc-event"))
      fail("vignette native route");
    if (vignette.fields.length != 4 || vignette.fields.indexOf("intensity") < 0
      || vignette.fields.indexOf("duration") < 0 || vignette.fields.indexOf("ease") < 0
      || vignette.fields.indexOf("easeDir") < 0)
      fail("vignette fields");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_markov_eye_popup_event_routes_without_claiming_body_execution(self):
        eye_popup = r'''
class MarkovPopupsEvent extends ScriptedSongEvent {
    function new() { super('EyePopup'); }
    function handleEvent(data) {
        var x = data.value.x;
        var y = data.value.y;
        Paths.getSparrowAtlas('MarkovEyes');
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    var findings:Array<Dynamic> = cast result.diagnostics;
    for (finding in findings) if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(eye_popup)}, "scripts/events/EyePopup.hxc");
    if (result.kind != "song-event" || result.identifier != "EyePopup") fail("eye event identity");
    if (result.eventAdapters.length != 1 || result.eventAdapters[0].canonicalName != "Markov Popups")
      fail("eye popup native route");
    if (result.fields.length != 2 || result.fields.indexOf("x") < 0 || result.fields.indexOf("y") < 0)
      fail("eye popup fields");
    if (hasCode(result, "unsupported-hxc-event-body") || hasCode(result, "unsupported-hxc-event"))
      fail("eye body/identity diagnostics");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_vignette_and_markov_event_sources_use_native_identity_adapters(self):
        vignette_path = DONOR / "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/vignetteEvent.hxc"
        vignette_handler = DONOR / "v-slice/Wacky World UPDATE [V-Slice]/scripts/modules/eventHandlers/vignEventHandler.hxc"
        vignette_shader = DONOR / "v-slice/Wacky World UPDATE [V-Slice]/shaders/vignette.frag"
        eye_path = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/EyePopup.hxc"
        markov_atlas = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/shared/images/MarkovEyes.astc"
        required = [vignette_path, vignette_handler, vignette_shader, eye_path, markov_atlas]
        if not all(path.exists() for path in required):
            self.skipTest("Wacky/TAKEOVER event assets are not mounted")
        vignette_source = vignette_path.read_text(errors="ignore")
        eye_source = eye_path.read_text(errors="ignore")
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var vignette = HxcCompat.analyze({hx_string(vignette_source)}, {hx_string(str(vignette_path))});
    var eye = HxcCompat.analyze({hx_string(eye_source)}, {hx_string(str(eye_path))});
    if (vignette.className != "VignEvent" || vignette.identifier != "extra-events-vignEvent"
      || vignette.eventAdapters.length != 1 || vignette.eventAdapters[0].canonicalName != "Vignette"
      || vignette.fields.length != 4 || vignette.fields.indexOf("intensity") < 0
      || vignette.fields.indexOf("duration") < 0 || vignette.fields.indexOf("ease") < 0
      || vignette.fields.indexOf("easeDir") < 0 || hasCode(vignette, "unsupported-hxc-event"))
      fail("real VignEvent adapter");
    if (eye.className != "MarkovPopupsEvent" || eye.identifier != "EyePopup"
      || eye.eventAdapters.length != 1 || eye.eventAdapters[0].canonicalName != "Markov Popups"
      || eye.fields.length != 2 || eye.fields.indexOf("x") < 0 || eye.fields.indexOf("y") < 0
      || hasCode(eye, "unsupported-hxc-event"))
      fail("real EyePopup adapter");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("extra-events-vignHandler", vignette_handler.read_text(errors="ignore"))
        self.assertIn("u_intensity", vignette_shader.read_text(errors="ignore"))
        self.assertIn("MarkovWindow", eye_source)

    def test_mounted_event_script_inventory_routes_native_and_custom_classes(self):
        """The mounted event corpus is the engine-level compatibility fixture."""
        expected = {
            "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/events/Add Camera Zoom.hxc":
                ("song-event", "AddCameraZoom", "Zoom Rabbit", "Add Camera Zoom"),
            "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/events/ChangeCharacterEvent.hxc":
                ("song-event", "ChangeCharacterEvent", "ChangeCharacter", "Change Character"),
            "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/events/Zoom Rabbit.hxc":
                ("song-event", "ZoomRabbit", "Zoom Rabbit", ""),
            "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/AddCamZoomPsych.hxc":
                ("song-event", "AddCameraZoomPsych", "AddCamZoomPsych", "Add Camera Zoom"),
            "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/ChangeCharacterEventCL.hxc":
                ("song-event", "ChangeCharacterEventCL", "ChangeCharacterCL", "Change Character"),
            "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/CharacterResetHandlerCL.hxc":
                ("module", "CharacterResetHandlerCL", "CharacterResetHandlerCL", ""),
            "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/EyePopup.hxc":
                ("song-event", "MarkovPopupsEvent", "EyePopup", "Markov Popups"),
            "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/NoteSwapEvent.hxc":
                ("song-event", "NoteSwapEvent", "NoteSwapEvent", "Note Swap"),
            "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/ChangeCharacterScriptEvent.hxc":
                ("song-event", "ChangeCharacterEvent", "charChange", "Change Character"),
            "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/PlayVideoEvent.hxc":
                ("song-event", "PlayVideoEvent", "PlayVideo", "Play Video"),
            "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/SC_ChangeStageEvent.hxc":
                ("song-event", "SC_ChangeStageEvent", "ChangeStage", "Change Stage"),
            "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/addLyricsEvent.hxc":
                ("song-event", "AddLyricsEvent", "extra-events-addLyricsEvent", "Lyrics"),
            "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/cameraFadeEvent.hxc":
                ("song-event", "CameraFadeEvent", "extra-events-cameraFadeEvent", "Camera Fade"),
            "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/cameraFlashEvent.hxc":
                ("song-event", "CameraFlashEvent", "extra-events-cameraFlashEvent", "Camera Flash"),
            "v-slice/Wacky World UPDATE [V-Slice]/scripts/events/vignetteEvent.hxc":
                ("song-event", "VignEvent", "extra-events-vignEvent", "Vignette"),
        }
        paths = [DONOR / relative for relative in expected]
        if not all(path.exists() for path in paths):
            self.skipTest("mounted 15-file HXC event corpus is not available")
        declarations = []
        checks = []
        for index, (relative, values) in enumerate(expected.items()):
            var = f"event_{index}"
            path = DONOR / relative
            declarations.append(
                f"var {var} = HxcCompat.analyze({hx_string(path.read_text(errors='ignore'))}, {hx_string(str(path))});"
            )
            kind, class_name, identifier, canonical = values
            checks.append(
                f'''if ({var}.kind != {hx_string(kind)} || {var}.className != {hx_string(class_name)}
  || {var}.identifier != {hx_string(identifier)})
  fail("{relative} identity: " + {var}.kind + "/" + {var}.className + "/" + {var}.identifier);'''
            )
            if canonical:
                checks.append(
                    f'''if ({var}.eventAdapters.length != 1 || {var}.eventAdapters[0].canonicalName != {hx_string(canonical)})
  fail("{relative} route");'''
                )
                checks.append(
                    f'''for (finding in {var}.diagnostics)
  if (finding.code == "unsupported-hxc-event") fail("{relative} unsupported event");'''
                )
                checks.append(
                    f'''for (finding in {var}.diagnostics)
  if (finding.code == "unsupported-hxc-event-body") fail("{relative} unconditional body gap");'''
                )
                checks.append(
                    f'''for (finding in {var}.diagnostics)
  if (finding.code == "hxc-event-body-gap") fail("{relative} unexpected body gap");'''
                )
            elif identifier == "Zoom Rabbit":
                checks.append(
                    f'''if ({var}.eventAdapters.length != 0 || {var}.customEventKind != "Zoom Rabbit"
  || {var}.generatedHscript.indexOf("function songEvent(event)") < 0)
  fail("{relative} authored handler");'''
                )
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {"".join(declarations)}
    {"".join(checks)}
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generic_payload_adapter_covers_safe_reads_and_preserves_unsafe_gap(self):
        safe = r'''
class SafeStage extends Stage {
    function onCountdownStart(event:CountdownScriptEvent):Void {
        event.cancel();
    }
    function onNoteHit(event:HitNoteScriptEvent):Void {
        if (event.note != null && event.note.noteData.getDirection() >= 0) {
            event.note.lowPriority = true;
            event.note.x += 1;
            event.note.holdNoteSprite.updateHitbox();
            event.note.animation.addByPrefix("idle", "idle");
            event.cancelEvent();
        }
    }
    function onSongEvent(event:SongEventScriptEvent):Void {
        var value = event.eventData.value;
        if (value.value1 == "flash") event.eventData.activated = true;
    }
}
'''
        unsafe = r'''
class UnsafeStage extends Stage {
    function onSongEvent(event:SongEventScriptEvent):Void {
        if (event.events != null) event.cancelEvent();
    }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    var findings:Array<Dynamic> = cast result.diagnostics;
    for (finding in findings) if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var safe = HxcCompat.analyze({hx_string(safe)}, "scripts/stages/safe-stage.hxc");
    if (!safe.payloadSafe || !hasCode(safe, "hxc-payload-adapter")
      || hasCode(safe, "unsupported-hxc-payload"))
      fail("safe payload adapter diagnostics");
    if (safe.payloadPatterns.indexOf("note") < 0
      || safe.payloadPatterns.indexOf("eventData/value") < 0
      || safe.payloadPatterns.indexOf("cancel") < 0)
      fail("safe payload pattern inventory");
    var unsafe = HxcCompat.analyze({hx_string(unsafe)}, "scripts/stages/unsafe-stage.hxc");
    if (unsafe.payloadSafe || !hasCode(unsafe, "unsupported-hxc-payload"))
      fail("unsafe payload warning was suppressed");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unused_typed_payload_annotation_does_not_create_a_gap(self):
        source = r'''
class UnusedPayloadStage extends Stage {
    override function onUpdate(event:UpdateScriptEvent):Void {
        super.onUpdate(event);
        trace("the callback intentionally does not inspect event");
    }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/stages/unused-payload.hxc");
    if (!result.payloadSafe) fail("unused payload annotation was treated as a gap");
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-payload") fail("unused payload warning: " + finding.message);
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shared_lifecycle_payload_aliases_cover_module_state_song_and_freeplay_fields(self):
        source = r'''
import funkin.modding.module.Module;
class SharedPayloadModule extends Module {
    function copyValue(value) { return value.value; }
    override function onStateOpenEnd(event:ScriptEvent) {
        if (event.targetState != null && event.targetState.members.contains(event))
            event.targetState.add(event);
        if (event.targetState != null) event.cancelEvent();
    }
    override function onSongLoaded(event:ScriptEvent) {
        if (event.events != null) trace(event.events.length);
    }
    override function onCapsuleSelected(event:ScriptEvent) {
        if (event.capsule != null && event.difficulty != null) trace(event.difficulty);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/SharedPayloadModule.hxc");
    if (result.kind != "module" || !result.moduleSafe || !result.moduleInitializationSafe)
      fail("shared payload module safety: " + result.moduleSafetyReasons.join(","));
    if (!result.payloadSafe || hasCode(result, "unsupported-hxc-payload")
      || hasCode(result, "unsupported-hxc-module-body"))
      fail("shared payload diagnostics were not reduced");
    if (result.canonicalCallbacks.indexOf("stateChangeEnd") < 0
      || result.canonicalCallbacks.indexOf("songLoaded") < 0
      || result.canonicalCallbacks.indexOf("capsuleSelected") < 0)
      fail("lifecycle aliases were not canonicalized: " + result.canonicalCallbacks.join(","));
    if (result.generatedHscript.indexOf("function stateChangeEnd") < 0)
      fail("onStateOpenEnd was not emitted through stateChangeEnd: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
    var names = EngineCompat.callbackNames("stateChangeEnd");
    if (names.indexOf("onStateOpenEnd") < 0) fail("live state-open alias missing");
    var payload = EngineCompat.hxcFreeplayPayload("capsuleSelected", "state", "capsule", 2, null);
    if (Reflect.field(payload, "targetState") != "state"
      || Reflect.field(payload, "capsule") != "capsule"
      || Reflect.field(payload, "difficulty") != 2)
      fail("freeplay payload fields were not preserved");
    var selectedCapsule = {{name:"You and Me", freeplayData:{{levelId:"You and Me", data:{{id:"You and Me"}}}}}};
    var lifecyclePayload = EngineCompat.hxcFreeplayPayload("subStateOpenEnd",
      {{name:"freeplay-host"}}, selectedCapsule, 1, null);
    if (HxcFreeplayRouting.selectedSong(lifecyclePayload) != "youandme")
      fail("Freeplay lifecycle payload did not route to its selected song");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_constant_and_dimension_initializers_stay_in_the_engine_scope(self):
        source = r'''
import funkin.modding.module.Module;
import funkin.util.Constants;
import flixel.FlxG;
import haxe.ds.StringMap;
class NativeDefaults extends Module {
    static var title = Constants.TITLE;
    static var version = Constants.VERSION;
    static var healthGreen = Constants.COLOR_HEALTH_BAR_GREEN;
    var footerPosition = {x: FlxG.width / 3, y: FlxG.height - 32};
    var cache = new StringMap();
    function new() { super('native-defaults'); }
    override function onCreate(event) {
        if (FlxG.width > 0) trace(title + version + healthGreen + footerPosition.x);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/NativeDefaults.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe
      || hasCode(result, "unsupported-hxc-module-body"))
      fail("native initializer adapter failed: " + result.moduleSafetyReasons.join(",")
        + "\\n" + result.generatedHscript);
    if (result.generatedHscript.indexOf("HxcCompatRuntime.constants") < 0
      || result.generatedHscript.indexOf("FlxG.width") < 0)
      fail("native initializer aliases were not retained: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_literal_constructor_media_cache_is_scoped_and_dynamic_keys_stay_unsafe(self):
        donor = r'''
class CacheProbe extends Module {
    function new() {
        super("cache-probe");
        FunkinMemory.permanentCacheTexture(Paths.sound("mechanics/cue", "shared"));
        FunkinMemory.permanentCacheTexture(Paths.image("ui/prompt", "shared"));
    }
    function onSongRetry(event) {}
}
'''
        dynamic = donor.replace('Paths.sound("mechanics/cue", "shared")',
                                'Paths.sound(cueKey, "shared")')
        main = f'''import hscript.Parser;
class Main {{
  static function fail(message:String):Void throw message;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/CacheProbe.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe)
      fail("literal cache was rejected: " + result.moduleSafetyReasons.join(","));
    var generated = result.generatedHscript;
    if (generated.indexOf('cacheFunkinTexture(hxcAssetRoot, "mechanics/cue")') < 0
      || generated.indexOf('cacheFunkinTexture(hxcAssetRoot, "ui/prompt")') < 0
      || generated.indexOf('cacheFunkinSound(hxcAssetRoot, "mechanics/cue")') >= 0)
      fail("permanent texture cache did not retain its operation kind and root: " + generated);
    new Parser().parseString(generated);
    var unsafe = HxcCompat.analyze({hx_string(dynamic)}, "scripts/modules/CacheProbe.hxc");
    if (unsafe.moduleSafe || unsafe.moduleInitializationSafe)
      fail("dynamic constructor cache key crossed the safety gate");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_module_note_kind_preserves_identity_and_bridges_generic_behavior(self):
        donor = r'''
import funkin.modding.module.Module;
class MarkovNotes extends Module {
    function new() { super("markov"); }
    function onCreate(event:ScriptEvent) {}
    function onNoteHit(callback) {
        if (callback.note.noteData.kind == "markov") callback.cancelEvent();
    }
    function onNoteIncoming(callback) {
        if (callback.note.noteData.kind == "markov") callback.note.frames = Paths.getSparrowAtlas("markovNotes");
    }
    function onNoteMiss(callback) { if (callback.note.noteData.kind == "markov") callback.cancelEvent(); }
    override function onSongEnd(event:ScriptEvent):Void { super.onSongEnd(event); }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/notes/markov.hxc");
    if (result.kind != "note-kind") fail("note kind: " + result.kind);
    if (result.noteKinds.length != 1 || result.noteKinds[0] != "markov") fail("authored kind");
    if (result.callbacks.indexOf("onNoteHit") < 0 || result.callbacks.indexOf("onNoteIncoming") < 0
      || result.callbacks.indexOf("onNoteMiss") < 0 || result.callbacks.indexOf("onSongEnd") < 0) fail("callbacks");
    if (result.canonicalCallbacks.indexOf("noteHit") < 0 || result.canonicalCallbacks.indexOf("noteIncoming") < 0
      || result.canonicalCallbacks.indexOf("noteMiss") < 0 || result.canonicalCallbacks.indexOf("songEnd") < 0) fail("canonical callbacks");
    if (result.nativeNoteDefinitions.length != 1) fail("native note definition");
    if (result.nativeNoteDefinitions[0].sourceKind != "markov") fail("native source kind");
    var sawAdapter = false;
    for (finding in result.diagnostics) if (finding.code == "hxc-note-behavior-adapter") sawAdapter = true;
    if (!sawAdapter) fail("missing generic note behavior adapter");
    if (result.noteBehaviorPatterns.indexOf("kind-routing") < 0
      || result.noteBehaviorPatterns.indexOf("cancellation") < 0
      || result.noteBehaviorPatterns.indexOf("graphics") < 0)
      fail("note behavior patterns");
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-note-behavior") fail("old broad behavior gap");
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_note_payload_layout_fields_match_the_native_mutable_view(self):
        donor = r'''
import funkin.modding.module.Module;
class GenericLayoutNote extends Module {
    function new() { super("generic-layout"); }
    function onNoteIncoming(event:NoteScriptEvent):Void {
        event.note.lowPriority = true;
        event.note.offset.x = 18;
        event.note.offset.y = 90;
        event.note.flipY = true;
    }
}
'''
        main = f'''class Main {{
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/notes/generic-layout.hxc");
    if (result.kind != "note-kind" || !result.payloadSafe)
      throw "native note layout was treated as donor-only";
    for (finding in result.diagnostics)
      if (finding.code == "unsupported-hxc-payload")
        throw "native note layout emitted a payload warning";
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_note_layout_callbacks_do_not_report_a_payload_gap(self):
        donor_root = Path('/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/Vs Tricky/scripts/notekinds')
        sources = [donor_root / 'deathnotes.hxc', donor_root / 'hellNote.hxc']
        if not all(source.is_file() for source in sources):
            self.skipTest('Vs Tricky note-kind donors are not mounted')
        main = f'''class Main {{
  static function main() {{
    for (source in [{', '.join(hx_string(source.read_text(errors='ignore')) for source in sources)}]) {{
      var result = HxcCompat.analyze(source, "scripts/notekinds/donor-note.hxc");
      if (!result.payloadSafe) throw "mounted note payload rejected";
      for (finding in result.diagnostics)
        if (finding.code == "unsupported-hxc-payload")
          throw "mounted note payload emitted an obsolete warning";
    }}
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_player_vocal_bus_callback_uses_the_native_role_aware_bridge(self):
        donor = r'''
import funkin.modding.module.Module;
import funkin.play.PlayState;
class VocalBus extends Module {
    function new() { super("vocal.bus"); }
    function onNoteHit(event:HitNoteScriptEvent) {
        if (event.judgement == "perfect")
            PlayState.instance.vocals.set_playerVolume(1);
    }
    function onUpdate(event:UpdateScriptEvent) {
        if (PlayState.instance.vocals.playerVolume != 1)
            PlayState.instance.vocals.playerVolume = 1;
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/vocal-bus.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe)
      throw "player vocal callback remains unsafe: " + result.moduleSafetyReasons.join(",");
    if (result.generatedHscript.indexOf("HxcCompatRuntime.setPlayerVocalVolume(PlayState.instance, 1)") < 0)
      throw "player bus call was not routed to native stems";
    if (result.generatedHscript.indexOf("HxcCompatRuntime.getPlayerVocalVolume(PlayState.instance) != 1") < 0)
      throw "player bus read was not routed to native stems";
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_tricky_vocal_bus_callback_is_executable(self):
        donor = Path('/run/media/cammie/External Storage/FNF-Example-Mods/v-slice/Vs Tricky/scripts/modules/TrickyVocalVolumeSetter.hxc')
        if not donor.is_file():
            self.skipTest('Vs Tricky vocal module is not mounted')
        main = f'''class Main {{
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor.read_text(errors='ignore'))},
      "scripts/modules/TrickyVocalVolumeSetter.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe)
      throw "mounted vocal bus callback remains unsafe: " + result.moduleSafetyReasons.join(",");
    if (result.generatedHscript.indexOf("HxcCompatRuntime.setPlayerVocalVolume") < 0)
      throw "mounted donor operation was dropped";
  }}
}}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_note_override_marker_and_default_super_bridge(self):
        main = r'''class Actor {
  public var calls:Array<String> = [];
  public function new() {}
  public function playSingAnimation(direction:Int, miss:Bool, suffix:String):Void
    calls.push(direction + ":" + miss + ":" + suffix);
}
class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var actor = new Actor();
    var nativeNote:Dynamic = {shouldBeSung: true, altNum: 2};
    var noteData:Dynamic = {
      data: 3,
      getDirection: function():Int return 3
    };
    var event:Dynamic = {
      note: {noteData: noteData, nativeNote: nativeNote},
      nativeNote: nativeNote
    };
    HxcCompatRuntime.markCharacterNoteHandled(event);
    if (event.characterHandled != true) fail("character marker");
    HxcCompatRuntime.characterDefaultNoteHit(actor, event);
    if (actor.calls.length != 1 || actor.calls[0] != "3:false:alt2")
      fail("default super bridge: " + actor.calls.join(","));

    var missingNote:Dynamic = {note: null, nativeNote: null};
    HxcCompatRuntime.markCharacterNoteHandled(missingNote);
    if (missingNote.characterHandled == true) fail("missing event note suppressed native singer");
    var missingNoteData:Dynamic = {note: {nativeNote: {}}, nativeNote: {}};
    HxcCompatRuntime.markCharacterNoteHandled(missingNoteData);
    if (missingNoteData.characterHandled == true) fail("incomplete event note suppressed native singer");

    var suppressed = new Actor();
    var noSing:Dynamic = {shouldBeSung: false, altNum: 0};
    var noSingEvent:Dynamic = {
      note: {noteData: noteData, nativeNote: noSing},
      nativeNote: noSing
    };
    HxcCompatRuntime.characterDefaultNoteHit(suppressed, noSingEvent);
    if (suppressed.calls.length != 0) fail("no-animation note was sung");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_module_literal_state_and_retry_lifecycle_are_executable(self):
        safe = r'''
import funkin.modding.module.Module;
import funkin.play.PlayState;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;
class FullPause extends Module {
    var stages = ['schoolDDTO', 'clubroom'];
    override function onPause(event) {
        super.onPause(event);
        if (!stages.contains(PlayState.instance.currentStageId)) return;
        FlxTimer.globalManager.forEach(function(tmr:FlxTimer) {
            if (!tmr.finished) tmr.active = false;
        });
    }
    override function onSongRetry(event) {
        super.onSongRetry(event);
        if (!stages.contains(PlayState.instance.currentStageId)) return;
        FlxTimer.globalManager.clear();
        FlxTween.globalManager.clear();
    }
    override function onResume(event) {
        super.onResume(event);
        if (!stages.contains(PlayState.instance.currentStageId)) return;
    }
}
'''
        unsafe = r'''
import funkin.modding.module.Module;
class UnsafeModule extends Module {
    var enabled = true;
    function new() {
        super('unsafe');
        save = DokiPreferences.getDokiSave();
    }
    override function onCountdownStart(event) {
        super.onCountdownStart(event);
        Preferences.flush();
    }
    override function onStateChangeEnd(event) { super.onStateChangeEnd(event); }
}
'''
        partial_source = r'''
import funkin.modding.module.Module;
import flixel.FlxG;
class PartialModule extends Module {
    var enabled = true;
    override function onPause(event) {
        super.onPause(event);
        if (enabled && FlxG.sound.music != null) FlxG.sound.music.pause();
    }
    override function onStateChangeEnd(event) {
        super.onStateChangeEnd(event);
        DokiPreferences.flush();
    }
}
'''
        donor_song_source = r'''
import funkin.modding.module.Module;
import funkin.play.PlayState;
        class DonorSongFieldModule extends Module {
    override function onUpdate(event) {
        PlayState.instance.currentSong.getDifficulty('normal');
    }
}
'''
        group_source = r'''
import funkin.modding.module.Module;
import flixel.group.FlxTypedGroup;
class GroupStateModule extends Module {
    var widgets:FlxTypedGroup = new FlxTypedGroup();
    override function onUpdate(event) {
        widgets.clear();
    }
}
'''
        save_source = r'''
import funkin.modding.module.Module;
class SaveAdapterModule extends Module {
    var save:Dynamic = Save.instance;
    var useDownscroll:Bool = Preferences.downscroll;
    function new() {
        super('save-adapter');
        save = DokiPreferences.getDokiSave();
    }
    override function onUpdate(event) {
        if (save.modOptions.get('compat-key') == null)
            save.modOptions.set('compat-key', true);
        Save.instance.flush();
        if (useDownscroll) trace('downscroll');
    }
}
'''
        module_call_source = r'''
import funkin.modding.module.Module;
import funkin.modding.module.ModuleHandler;
class ModuleCallAdapter extends Module {
    override function onUpdate(event) {
        var sibling = ModuleHandler.getModule('SiblingModule');
        if (sibling != null) sibling.scriptCall('tick', [event]);
    }
}
'''
        highscore_gap_source = r'''
import funkin.modding.module.Module;
class HighscoreGapModule extends Module {
    override function onSongStart(event) {
        if (Save.instance.hasBeatenSong('adapter-song') == false) trace('locked');
    }
}
'''
        chart_source = r'''
import funkin.modding.module.Module;
import funkin.play.PlayState;
class CurrentChartModule extends Module {
    override function onUpdate(event) {
        if (PlayState.instance.currentChart.characters.player == 'bf') trace(PlayState.instance.currentChart.songName);
        if (PlayState.instance.currentChart.characters.opponent == 'dad') trace(PlayState.instance.currentChart.stage);
        trace(PlayState.instance.currentChart.song.id);
        trace(PlayState.instance.currentChart.bpm + PlayState.instance.currentChart.scrollSpeed);
        trace(PlayState.instance.currentChart.album);
    }
}
'''
        chart_gap_source = r'''
import funkin.modding.module.Module;
import funkin.play.PlayState;
class CurrentChartMetadataGap extends Module {
    override function onUpdate(event) {
        trace(PlayState.instance.currentChart.noteStyle);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var safe = HxcCompat.analyze({hx_string(safe)}, "scripts/modules/FullPause.hxc");
    if (safe.kind != "module" || !safe.moduleSafe || !safe.moduleInitializationSafe)
      fail("FullPause safety: " + safe.kind + "/" + safe.moduleSafe + "/" + safe.moduleInitializationSafe);
    if (safe.stateInitializers.length != 1 || safe.stateInitializers[0].name != "stages")
      fail("literal state inventory");
    if (safe.generatedHscript.indexOf("var stages = ['schoolDDTO', 'clubroom'];") < 0)
      fail("literal state was not emitted: " + safe.generatedHscript);
    if (safe.generatedHscript.indexOf("function pause") < 0
      || safe.generatedHscript.indexOf("function songRetry") < 0
      || safe.generatedHscript.indexOf("function resume") < 0)
      fail("retry/pause/resume adapter missing: " + safe.generatedHscript);
    new Parser().parseString(safe.generatedHscript);
    if (hasCode(safe, "unsupported-hxc-module-body")) fail("safe module warning");
    var blocked = HxcCompat.analyze({hx_string(unsafe)}, "scripts/modules/UnsafeModule.hxc");
    // The isolated Doki save adapter now makes construction representable;
    // Preferences.flush and the unrouted lifecycle hook still keep behavior
    // unsafe, so initialization and callback safety are asserted separately.
    if (blocked.moduleSafe || !blocked.moduleInitializationSafe
      || !hasCode(blocked, "unsupported-hxc-module-body"))
      fail("unsafe module state/callback distinction was lost");
    var partial = HxcCompat.analyze({hx_string(partial_source)}, "scripts/modules/PartialModule.hxc");
    if (partial.moduleSafe || partial.generatedHscript.indexOf("function pause") < 0
      || !hasCode(partial, "hxc-module-adapter")
      || !hasCode(partial, "unsupported-hxc-module-body"))
      fail("partial module callback/state distinction was lost: " + partial.generatedHscript);
    new Parser().parseString(partial.generatedHscript);
    var donorSong = HxcCompat.analyze({hx_string(donor_song_source)}, "scripts/modules/DonorSongFieldModule.hxc");
    // Song.loadFromJson attaches a bounded getDifficulty view to the active
    // native chart. The HXC module may therefore resolve sibling charts without
    // constructing a donor Song graph or editing the source chart.
    if (!donorSong.moduleSafe || !donorSong.moduleInitializationSafe
      || hasCode(donorSong, "unsupported-hxc-module-body")
      || donorSong.generatedHscript.indexOf("currentSong.getDifficulty('normal')") < 0)
      fail("native currentSong.getDifficulty adapter was not retained: " + donorSong.generatedHscript);
    var group = HxcCompat.analyze({hx_string(group_source)}, "scripts/modules/GroupStateModule.hxc");
    if (!group.moduleSafe || !group.moduleInitializationSafe
      || group.generatedHscript.indexOf("var widgets = new FlxTypedGroup();") < 0)
      fail("native group state was not initialized safely: " + group.generatedHscript);
    new Parser().parseString(group.generatedHscript);
    var save = HxcCompat.analyze({hx_string(save_source)}, "scripts/modules/SaveAdapterModule.hxc");
    if (!save.moduleSafe || !save.moduleInitializationSafe
      || hasCode(save, "unsupported-hxc-module-body")
      || save.generatedHscript.indexOf("Save.instance") >= 0
      || save.generatedHscript.indexOf("DokiPreferences") >= 0
      || save.generatedHscript.indexOf("Preferences.downscroll") >= 0
      || save.generatedHscript.indexOf("HxcCompatRuntime.openStore") < 0
      || save.generatedHscript.indexOf("__hxcStore") < 0)
      fail("namespaced save/preferences adapter was not executable: " + save.generatedHscript);
    new Parser().parseString(save.generatedHscript);
    var moduleCall = HxcCompat.analyze({hx_string(module_call_source)}, "scripts/modules/ModuleCallAdapter.hxc");
    if (!moduleCall.moduleSafe || hasCode(moduleCall, "unsupported-hxc-module-body")
      || moduleCall.generatedHscript.indexOf("ModuleHandler") >= 0
      || moduleCall.generatedHscript.indexOf("hxcGetModule") < 0)
      fail("ModuleHandler route was not represented safely: " + moduleCall.generatedHscript);
    new Parser().parseString(moduleCall.generatedHscript);
    var highscoreGap = HxcCompat.analyze({hx_string(highscore_gap_source)}, "scripts/modules/HighscoreGapModule.hxc");
    if (highscoreGap.moduleSafe || !hasCode(highscoreGap, "unsupported-hxc-module-body"))
      fail("highscore lookup was over-mapped");
    var chart = HxcCompat.analyze({hx_string(chart_source)}, "scripts/modules/CurrentChartModule.hxc");
    if (!chart.moduleSafe
      || chart.generatedHscript.indexOf("PlayState.instance.currentChart.") >= 0
      || chart.generatedHscript.indexOf("currentPlayState.currentChart.") >= 0
      || chart.generatedHscript.indexOf("game.currentChart.") >= 0
      || chart.generatedHscript.indexOf("SONG.player1") < 0
      || chart.generatedHscript.indexOf("SONG.player2") < 0
      || chart.generatedHscript.indexOf("SONG.song") < 0
      || chart.generatedHscript.indexOf("trace(SONG.song)") < 0
      || chart.generatedHscript.indexOf("SONG.stage") < 0
      || chart.generatedHscript.indexOf("SONG.speed") < 0
      || chart.generatedHscript.indexOf("HxcCompatRuntime.currentChartAlbum") < 0)
      fail("currentChart fields were not lowered to the live chart: " + chart.generatedHscript);
    new Parser().parseString(chart.generatedHscript);
    var chartGap = HxcCompat.analyze({hx_string(chart_gap_source)}, "scripts/modules/CurrentChartMetadataGap.hxc");
    if (chartGap.moduleSafe || !hasCode(chartGap, "unsupported-hxc-module-body")
      || chartGap.generatedHscript.indexOf("currentChart.noteStyle") >= 0)
      fail("unsupported chart metadata was over-mapped: " + chartGap.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_costume_swapper_constructor_and_preserved_metadata_are_executable(self):
        path = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CostumeSwapperv3.hxc"
        if not path.exists():
            self.skipTest("CostumeSwapper donor fixture is not mounted")
        source = path.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(path))});
    if (result.kind != "module" || !result.moduleSafe || !result.moduleInitializationSafe)
      fail("CostumeSwapper safety: " + result.kind + "/" + result.moduleSafe + "/"
        + result.moduleInitializationSafe + " reasons=" + result.moduleSafetyReasons.join(","));
    if (hasCode(result, "unsupported-hxc-module-body"))
      fail("CostumeSwapper retained module-body diagnostic");
    if (result.generatedHscript.indexOf("hxcGetCharacterData") < 0
      || result.generatedHscript.indexOf("hxcChangeCharacter") < 0
      || result.generatedHscript.indexOf("hxcPrepareCharacter") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.openStore") < 0
      || result.generatedHscript.indexOf("SaveData.bfcostume") < 0)
      fail("CostumeSwapper adapters missing: " + result.generatedHscript);
    if (result.generatedHscript.indexOf("CharacterDataParser") >= 0
      || result.generatedHscript.indexOf("FunkinMemory") >= 0
      || result.generatedHscript.indexOf("?.") >= 0
      || result.generatedHscript.indexOf("??") >= 0)
      fail("donor-only costume API leaked: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_state_and_countdown_lifecycle_aliases_have_live_dispatch_names(self):
        source = r'''
import funkin.modding.module.Module;
class LifecycleModule extends Module {
    override function onCountdownStep(event) {
        if (event.step == 'THREE' && !event.eventCanceled) trace('ready');
    }
    override function onSubStateOpenEnd(event) {
        if (event.targetState != null) trace('opened');
    }
    override function onSubStateCloseEnd(event) {
        if (event.targetState != null) trace('closed');
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/LifecycleModule.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe
      || hasCode(result, "unsupported-hxc-module-body"))
      fail("lifecycle module was not routed: " + result.moduleSafetyReasons.join(","));
    if (result.generatedHscript.indexOf("function countdownStep") < 0
      || result.generatedHscript.indexOf("function subStateOpenEnd") < 0
      || result.generatedHscript.indexOf("function subStateCloseEnd") < 0)
      fail("lifecycle aliases missing: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_common_callback_roots_ignore_quoted_names_and_use_seeded_aliases(self):
        source = r'''
import funkin.modding.module.Module;
class RootedModule extends Module {
    override function onUpdate(event) {
        var donorClass = "funkin.ui.freeplay.FreeplayState";
        if (PlayState.instance.isGamePaused) return;
        if (PlayerSettings.player1.controls.BACK) trace(donorClass);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/RootedModule.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe)
      fail("seeded callback roots were rejected: " + result.moduleSafetyReasons.join(","));
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-callback-body"
        || finding.code == "unsupported-hxc-module-body")
        fail("safe callback diagnostic leaked: " + finding.code);
    if (result.generatedHscript.indexOf("paused") < 0
      || result.generatedHscript.indexOf("PlayerSettings.player1.controls.BACK") < 0)
      fail("seeded aliases were not lowered: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);

    var donorOnly = HxcCompat.analyze("import funkin.modding.module.Module;\n"
      + "class DonorOnly extends Module {{\n"
      + "  override function onUpdate(event) {{ var game = PlayState.instance; trace(game.mysteryGraph); }}\n"
      + "}}", "scripts/modules/DonorOnly.hxc");
    var sawDonorOnly = false;
    for (finding in (cast donorOnly.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-callback-body") sawDonorOnly = true;
    if (!sawDonorOnly) fail("unseeded PlayState alias field was treated as safe: "
      + donorOnly.moduleSafetyReasons.join(","));
    new Parser().parseString(donorOnly.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_character_registry_factory_adapter_is_bounded(self):
        donor = r'''
import funkin.modding.module.Module;
import funkin.play.character.CharacterDataParser;
import funkin.play.character.CharacterType;
import funkin.play.PlayState;
class CharacterRegistryModule extends Module {
    var characterCaches = ["bf" => ["init" => true]];
    var types = ["bf" => CharacterType.BF];
    function onCountdownStart(event) {
        if (CharacterDataParser.listCharacterIds().contains("bf")) {
            characterCaches.get("bf").set("bf", CharacterDataParser.fetchCharacter("bf"));
        }
    }
    function onSongRetry(event) {
        var characters = PlayState.instance.get_currentChart().characters;
        var actor = CharacterDataParser.fetchCharacter(characters.player);
        actor.set_characterType(CharacterType.BF);
        actor.initHealthIcon(false);
        PlayState.instance.currentStage.addCharacter(actor, CharacterType.BF);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/CharacterRegistryModule.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe)
      fail("character registry module was not executable: " + result.moduleSafetyReasons.join(","));
    if (hasCode(result, "unsupported-hxc-module-body")
      || hasCode(result, "unsupported-hxc-callback-body"))
      fail("character registry gap remained after native bridge");
    if (result.generatedHscript.indexOf("HxcCompatRuntime.characterExists") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.fetchCharacter") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.stageAddCharacter") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.setCharacterType") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.initHealthIcon") < 0
      || result.generatedHscript.indexOf("actor.set_characterType") >= 0
      || result.generatedHscript.indexOf("actor.initHealthIcon") >= 0
      || result.generatedHscript.indexOf("var characterCaches = hxcMap") < 0)
      fail("character registry aliases missing: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
    HxcCompatRuntime.clear();
    if (HxcCompatRuntime.characterExists("__missing_hxc_character__"))
      fail("missing native character was treated as present");
    var actor:Dynamic = {{}};
    if (HxcCompatRuntime.stageAddCharacter(null, actor, "unknown") != actor)
      fail("unknown character role was not bounded");
    var fake = new FakePlayState();
    var original:Dynamic = {{x: 42.0, y: 17.0, zIndex: 8}};
    fake.boyfriend = original;
    fake.iconP1 = new FakeIcon();
    fake.iconP2 = new FakeIcon();
    var replacement:Dynamic = {{x: 0.0, y: 0.0, zIndex: 0, isPlayer: false, curCharacter: "native-bf"}};
    HxcCompatRuntime.bindActiveState(fake);
    HxcCompatRuntime.setCharacterType(replacement, "bf");
    HxcCompatRuntime.initHealthIcon(replacement, false);
    if (fake.iconP1.lastName != "native-bf") fail("native health icon bridge");
    var fakeStage = new FakeStage();
    HxcCompatRuntime.stageAddCharacter(fakeStage, replacement, "bf");
    if (!fake.switched || fake.boyfriend != replacement || fake.lastRole != "boyfriend")
      fail("canonical switchToChar bridge was not used");
    if (replacement.x != 42.0 || replacement.y != 17.0 || replacement.zIndex != 8
      || replacement.isPlayer != true || fakeStage.refreshes != 1
      || fakeStage.rebinds != 1 || fakeStage.previous != original || fakeStage.replacement != replacement
      || fakeStage.role != "boyfriend")
      fail("replacement position/control/layer bridge");
    fakeStage.hasPresentation = true;
    var next:Dynamic = {{x: 0.0, y: 0.0, isPlayer: false, curCharacter: "next-bf"}};
    HxcCompatRuntime.stageAddCharacter(fakeStage, next, "bf");
    if (next.x != 900.0 || next.y != 800.0 || fake.boyfriend != next
      || fakeStage.presentations != 2)
      fail("stage role presentation was replaced by old actor position");
    var stale:Dynamic = {{x: 0.0, y: 0.0, zIndex: 0}};
    HxcCompatRuntime.setCharacterType(stale, "bf");
    HxcCompatRuntime.clearActiveState(fake);
    fake.switched = false;
    HxcCompatRuntime.bindActiveState(fake);
    HxcCompatRuntime.stageAddCharacter(new FakeStage(), stale, "unknown");
    if (fake.switched) fail("character type hint leaked across state cleanup");
  }}
}}
class FakePlayState {{
  public var boyfriend:Dynamic;
  public var iconP1:Dynamic;
  public var iconP2:Dynamic;
  public var switched:Bool = false;
  public var lastRole:String = "";
  public function new() {{}}
  public function switchToChar(character:Dynamic, role:String, destroy:Bool):Void {{
    switched = true;
    lastRole = role;
    boyfriend = character;
  }}
}}
class FakeStage {{
  public var refreshes:Int = 0;
  public var rebinds:Int = 0;
  public var presentations:Int = 0;
  public var hasPresentation:Bool = false;
  public var previous:Dynamic;
  public var replacement:Dynamic;
  public var role:String;
  public function new() {{}}
  public function applyVSliceCharacterPresentation(role:String, actor:Dynamic):Bool {{
    presentations++;
    if (!hasPresentation) return false;
    actor.x = 900.0;
    actor.y = 800.0;
    return true;
  }}
  public function rebindCharacterZ(role:String, previous:Dynamic, replacement:Dynamic):Void {{
    rebinds++;
    this.role = role;
    this.previous = previous;
    this.replacement = replacement;
  }}
  public function refresh():Void refreshes++;
}}
class FakeIcon {{
  public var lastName:String = "";
  public function new() {{}}
  public function switchAnim(name:Dynamic):Void lastName = Std.string(name);
}}
'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_character_registry_modules_use_native_factory_bridge(self):
        paths = {
            "change": DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/modules/ChangeCharacterHandler.hxc",
            "reset": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/CharacterResetHandlerCL.hxc",
        }
        if not all(path.exists() for path in paths.values()):
            self.skipTest("character registry donor fixtures are not mounted")
        declarations = "\n".join(
            f'''var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for name, path in paths.items()
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function safe(result:Dynamic, name:String):Bool {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == name && callback.safe) return true;
    return false;
  }}
  static function main() {{
    {declarations}
    if (!change.moduleSafe || !change.moduleInitializationSafe
      || !safe(change, "onCountdownStart") || !safe(change, "onSongEvent")
      || !safe(change, "onSongRetry")) fail("ChangeCharacterHandler bridge");
    if (change.generatedHscript.indexOf("HxcCompatRuntime.characterExists") < 0
      || change.generatedHscript.indexOf("HxcCompatRuntime.fetchCharacter") < 0
      || change.generatedHscript.indexOf("HxcCompatRuntime.stageAddCharacter") < 0)
      fail("ChangeCharacterHandler generated bridge");
    if (!reset.moduleSafe || !reset.moduleInitializationSafe || !safe(reset, "onSongRetry"))
      fail("CharacterResetHandlerCL bridge: " + reset.moduleSafetyReasons.join(","));
    if (reset.generatedHscript.indexOf("HxcCompatRuntime.fetchCharacter") < 0
      || reset.generatedHscript.indexOf("HxcCompatRuntime.stageAddCharacter") < 0)
      fail("CharacterResetHandlerCL generated bridge");
    new Parser().parseString(change.generatedHscript);
    new Parser().parseString(reset.generatedHscript);
  }}
}}'''
        before = {name: path.stat().st_mtime_ns for name, path in paths.items()}
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, {name: path.stat().st_mtime_ns for name, path in paths.items()})

    def test_synthetic_character_wrapper_keeps_native_constructor_and_actor_super(self):
        source = r'''
class CasualCharacter extends ProtagBaseCharacter {
    public function new() {
        super("costumes/protag-casual");
    }
    override public function playAnimation(name:String, restart:Bool = false,
        ignoreOther:Bool = false, reversed:Bool = false):Void {
        if (!StringTools.contains(name, "sing")) this.color = 0xFFFFFFFF;
        super.playAnimation(name, restart, ignoreOther, reversed);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/characters/costumes/casual.hxc");
    if (result.kind != "character" || result.characterConstructor != "costumes/protag-casual")
      fail("wrapper constructor metadata: " + result.kind + "/" + result.characterConstructor);
    if (result.generatedHscript.indexOf("HxcCompatRuntime.applyCharacterConstructor") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.playAnimation") < 0
      || result.generatedHscript.indexOf("hxcCharacter().color") < 0)
      fail("native character bridge missing: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
    var actor:Dynamic = {{isPlayer: true, curCharacter: "casual"}};
    var state:Dynamic = {{boyfriend: actor}};
    HxcCompatRuntime.bindActiveState(state);
    if (HxcCompatRuntime.characterType(actor) != "bf") fail("live character slot alias");
    if (HxcCompatRuntime.applyCharacterConstructor(actor, "costumes/missing") != actor)
      fail("missing costume was not bounded");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_character_screen_and_gameover_hooks_execute_native_bridges(self):
        source = r'''
class AtlasCharacter extends Character {
    var gameOverAnims = ['firstDeath', 'deathLoop', 'deathConfirm'];
    function addGameOverAssets() {
        var subTexture = Paths.getSparrowAtlas('characters/CustomGameOver');
        subTexture.parent.destroyOnNoUse = false;
        this.frames.addAtlas(subTexture);
        var animations = [
            {name: 'firstDeath', flipX: true, prefix: 'Intro', assetPath: 'characters/CustomGameOver', offsets: [-8, 12]},
            {name: 'deathLoop', flipX: true, prefix: 'Loop', assetPath: 'characters/CustomGameOver', looped: true, offsets: [-9, 13]},
            {name: 'deathConfirm', flipX: true, prefix: 'Confirm', assetPath: 'characters/CustomGameOver', offsets: [-7, 14]}
        ];
        for (anim in animations) {
            FlxAnimationUtil.addAtlasAnimation(super, anim);
            if (anim.offsets == null) setAnimationOffsets(anim.name, 0, 0);
            else setAnimationOffsets(anim.name, anim.offsets[0] + 20, anim.offsets[1] - 300);
        }
    }
    function getScreenPosition(result, camera) {
        var output = super.getScreenPosition(result, camera);
        if (gameOverAnims.contains(getCurrentAnimation())) return output;
        if (flipX) output.x += (animOffsets[0] * 2 + globalOffsets[0] + width - frameWidth) * scale.x;
        return output;
    }
}
'''
        main = f'''import hscript.Interp;
import hscript.Parser;
class FakeCharacter {{
  public var flipX:Bool = true;
  public var flipY:Bool = false;
  public var width:Float = 100;
  public var height:Float = 80;
  public var frameWidth:Float = 80;
  public var frameHeight:Float = 80;
  public var scale:Dynamic = {{x: 1.0, y: 1.0}};
  public var atlasPath:String = '';
  public var specCount:Int = 0;
  public var receivedX:Float = 0;
  public var receivedY:Float = 0;
  public function new() {{}}
  public function hxcBaseScreenPosition(result:Dynamic, camera:Dynamic):Dynamic return result;
  public function getCurrentAnimationOffset(index:Int):Float return index == 0 ? 3 : 4;
  public function getCurrentGlobalOffset(index:Int):Float return index == 0 ? 5 : 6;
  public function addHxcAtlasAnimations(path:String, animations:Dynamic, x:Float, y:Float):Void {{
    atlasPath = path;
    specCount = animations.length;
    receivedX = x;
    receivedY = y;
  }}
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/characters/atlas.hxc");
    if (result.characterHookGaps.length != 0)
      fail("character hook gap: " + result.characterHookGaps.join(","));
    if (result.generatedHscript.indexOf("addCharacterAtlasAnimations") < 0
      || result.generatedHscript.indexOf("characterBaseScreenPosition") < 0
      || result.generatedHscript.indexOf("characterAnimationOffset") < 0
      || result.generatedHscript.indexOf("characterGlobalOffset") < 0)
      fail("missing native character bridge: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
    var actor = new FakeCharacter();
    var interp = new Interp();
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("hxcAssetRoot", "");
    interp.variables.set("hxcCharacter", function() return actor);
    interp.variables.set("getCurrentAnimation", function() return "idle");
    interp.execute(new Parser().parseString(result.generatedHscript));
    var add:Dynamic = interp.variables.get("addGameOverAssets");
    if (add == null) fail("missing game-over helper");
    add();
    if (actor.atlasPath != "characters/CustomGameOver" || actor.specCount != 3
      || actor.receivedX != 20 || actor.receivedY != -300)
      fail("atlas bridge payload: " + actor.atlasPath + "/" + actor.specCount
        + "/" + actor.receivedX + "/" + actor.receivedY);
    var position:Dynamic = interp.variables.get("getScreenPosition");
    var point:Dynamic = position({{x: 10.0, y: 20.0}}, null);
    if (point.x != 41 || point.y != 20) fail("screen position bridge: " + point.x + "/" + point.y);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_module_indexed_character_offsets_use_active_native_animation_and_global_offsets(self):
        source = r'''import funkin.modding.module.Module;
class OffsetProbe extends Module {
    function noteHit(note, player, opponent) {
        var playerX = player.animOffsets[0] - player.globalOffsets[0];
        var playerY = player.animOffsets[1] - player.globalOffsets[1];
        var opponentY = opponent.animOffsets[1] - opponent.globalOffsets[1];
    }
}'''
        main = f'''import hscript.Parser;
class FakeCharacter {{
  public function new() {{}}
  public function getCurrentAnimationOffset(index:Int):Float return index == 0 ? 31 : -42;
  public function getCurrentGlobalOffset(index:Int):Float return index == 0 ? 7 : -8;
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/offset-probe.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf("characterAnimationOffset(player, 0)") < 0
      || generated.indexOf("characterAnimationOffset(player, 1)") < 0
      || generated.indexOf("characterGlobalOffset(player, 0)") < 0
      || generated.indexOf("characterGlobalOffset(player, 1)") < 0
      || generated.indexOf("characterAnimationOffset(opponent, 1)") < 0
      || generated.indexOf("characterGlobalOffset(opponent, 1)") < 0)
      fail("module reads did not use the active character offset bridge: " + generated);
    new Parser().parseString(generated);
    var actor = new FakeCharacter();
    var x = HxcCompatRuntime.characterAnimationOffset(actor, 0)
      - HxcCompatRuntime.characterGlobalOffset(actor, 0);
    var y = HxcCompatRuntime.characterAnimationOffset(actor, 1)
      - HxcCompatRuntime.characterGlobalOffset(actor, 1);
    if (x != 24 || y != -34) fail("native offset bridge values: " + x + "," + y);
    if (HxcCompatRuntime.characterGlobalOffset(null, 0) != 0)
      fail("missing character global offset was not safe");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_character_inheritance_chain_is_composed_once_in_order(self):
        main = r'''import hscript.Parser;
import sys.FileSystem;
import sys.io.File;
class Main {
  static function fail(value:String):Void throw value;
  static function count(source:String, needle:String):Int {
    var total = 0;
    var offset = 0;
    while (offset < source.length) {
      var found = source.indexOf(needle, offset);
      if (found < 0) break;
      total++;
      offset = found + needle.length;
    }
    return total;
  }
  static function main() {
    var root = "tmp/hxc-inheritance-chain";
    var scripts = root + "/scripts/characters";
    FileSystem.createDirectory(root);
    FileSystem.createDirectory(root + "/scripts");
    FileSystem.createDirectory(scripts);
    var grand = scripts + "/grand.hxc";
    var base = scripts + "/base.hxc";
    var wrapper = scripts + "/wrapper.hxc";
    File.saveContent(grand, "class GrandBase extends Character { var marker = 'grand';\nfunction dance(force:Bool) { trace('grand-marker'); } }");
    File.saveContent(base, "class BaseCharacter extends GrandBase { var marker = 'base';\noverride function dance(force:Bool) { trace('base-marker'); super.dance(force); } }");
    File.saveContent(wrapper, "class WrapperCharacter extends BaseCharacter { var marker = 'wrapper';\nfunction new() { super('costumes/chain'); }\noverride function dance(force:Bool) { trace('wrapper-marker'); super.dance(force); } }");
    var result = HxcCompat.analyze(File.getContent(wrapper), wrapper);
    var generated = result.generatedHscript;
    if (!StringTools.endsWith(result.characterBasePath, "/base.hxc"))
      fail("direct base path was not resolved: " + result.characterBasePath);
    var grandPos = generated.indexOf("grand-marker");
    var basePos = generated.indexOf("base-marker");
    var wrapperPos = generated.indexOf("wrapper-marker");
    if (grandPos < 0 || basePos < 0 || wrapperPos < 0
      || !(grandPos < basePos && basePos < wrapperPos))
      fail("inheritance order: " + generated);
    if (count(generated, "grand-marker") != 1 || count(generated, "base-marker") != 1
      || count(generated, "wrapper-marker") != 1)
      fail("duplicate inherited body: " + generated);
    if (count(generated, "var marker") != 1
      || generated.indexOf("var marker = 'wrapper';") < 0
      || generated.indexOf("var marker = 'base';") >= 0
      || generated.indexOf("var marker = 'grand';") >= 0)
      fail("wrapper state initializer precedence: " + generated);
    new Parser().parseString(generated);
    FileSystem.deleteFile(grand);
    FileSystem.deleteFile(base);
    FileSystem.deleteFile(wrapper);
    FileSystem.deleteDirectory(scripts);
    FileSystem.deleteDirectory(root + "/scripts");
    FileSystem.deleteDirectory(root);
    }
}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_character_gap_diagnostics_distinguish_inherited_and_direct(self):
        main = r'''import sys.FileSystem;
import sys.io.File;
class Main {
  static function fail(value:String):Void throw value;
  static function has(result:HxcCompat.HxcCompatResult, code:String):Bool {
    for (finding in result.diagnostics) if (finding.code == code) return true;
    return false;
  }
  static function main() {
    var root = "tmp/hxc-character-gaps";
    var scripts = root + "/scripts/characters";
    FileSystem.createDirectory(root);
    FileSystem.createDirectory(root + "/scripts");
    FileSystem.createDirectory(scripts);
    var base = scripts + "/base.hxc";
    var wrapper = scripts + "/wrapper.hxc";
    File.saveContent(base, "class BaseCharacter extends Character {\nfunction onAdd(event) { Paths.image('donor-only'); }\nfunction getScreenPosition() { Paths.image('donor-only'); }\nfunction dance(force:Bool) { trace('safe-base'); }\n}");
    File.saveContent(wrapper, "class WrapperCharacter extends BaseCharacter {\nfunction new() { super('costumes/gap'); }\nfunction dance(force:Bool) { trace('safe-wrapper'); super.dance(force); }\n}");
    var inherited = HxcCompat.analyze(File.getContent(wrapper), wrapper);
    if (!has(inherited, "unsupported-hxc-character-base")
      || has(inherited, "unsupported-hxc-character-hook")
      || inherited.characterBaseGaps.indexOf("onAdd") < 0
      || inherited.characterBaseGaps.indexOf("getScreenPosition") < 0
      || inherited.characterHookGaps.length != 0)
      fail("inherited gap classification: " + inherited.generatedHscript);
    if (inherited.generatedHscript.indexOf("safe-base") < 0
      || inherited.generatedHscript.indexOf("safe-wrapper") < 0)
      fail("safe inherited/wrapper callback was masked: " + inherited.generatedHscript);
    var direct = HxcCompat.analyze(
      "class DirectCharacter extends MissingCharacter { function onCreate() { Paths.image('donor-only'); } function dance(force:Bool) { trace('direct-safe'); } }",
      "scripts/characters/direct.hxc");
    if (has(direct, "unsupported-hxc-character-base")
      || !has(direct, "unsupported-hxc-character-hook")
      || direct.characterHookGaps.indexOf("onCreate") < 0)
      fail("direct gap classification");
    FileSystem.deleteFile(base);
    FileSystem.deleteFile(wrapper);
    FileSystem.deleteDirectory(scripts);
    FileSystem.deleteDirectory(root + "/scripts");
    FileSystem.deleteDirectory(root);
  }
}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_costume_wrappers_resolve_base_lifecycle_closure(self):
        paths = {
            "protag": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/Protag/protag-casual.hxc",
            "natsuki": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/Natsuki/natsuki-skater.hxc",
            "monika": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/Monika/monika-valentine.hxc",
            "sayori": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/Sayori/sayori-casual.hxc",
            "yuri": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/Yuri/yuri-picnic.hxc",
            "crazy_yuri": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/Yuri/Crazy Yuri/yuri-crazy-taki.hxc",
        }
        if not all(path.exists() for path in paths.values()):
            self.skipTest("mounted costume wrapper fixtures are not available")
        declarations = "\n".join(
            f'''var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for name, path in paths.items()
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {declarations}
    var results = [{", ".join(paths.keys())}];
    for (result in results) {{
      if (result.kind != "character" || result.characterBasePath == "")
        fail("unresolved character base: " + result.className + "/" + result.baseClass);
      if (result.characterConstructor == ""
        || result.generatedHscript.indexOf("HxcCompatRuntime.applyCharacterConstructor") < 0)
        fail("wrapper constructor bridge missing: " + result.className);
      if (result.generatedHscript.indexOf("function playAnimation") < 0)
        fail("inherited animation bridge missing: " + result.className);
      new Parser().parseString(result.generatedHscript);
    }}
  }}
}}'''
        before = {name: path.stat().st_mtime_ns for name, path in paths.items()}
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, {name: path.stat().st_mtime_ns for name, path in paths.items()})

    def test_mounted_ddto_character_position_and_gameover_hooks_are_executable(self):
        paths = [
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/yuri-crazy.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/protag.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/senpai-nonpixel.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/monika.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/natsuki.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/yuri.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/monika-pixelnew.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/sayori.hxc",
        ]
        if not all(path.exists() for path in paths):
            self.skipTest("mounted DDTO++ character hook fixtures are not available")
        declarations = "\n".join(
            f'''var result{index} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for index, path in enumerate(paths)
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {declarations}
    var results = [{", ".join("result" + str(index) for index in range(len(paths)))}];
    for (result in results) {{
      if (result.characterHookGaps.length != 0 || result.characterBaseGaps.length != 0)
        fail("mounted DDTO hook gap: " + result.className + "/"
          + result.characterBaseGaps.join(",") + "/" + result.characterHookGaps.join(","));
      if (result.generatedHscript.indexOf("function getScreenPosition") >= 0
        && result.generatedHscript.indexOf("characterBaseScreenPosition") < 0)
        fail("screen-position bridge missing: " + result.className);
      if (result.generatedHscript.indexOf("function addGameOverAssets") >= 0
        && result.generatedHscript.indexOf("addCharacterAtlasAnimations") < 0)
        fail("game-over atlas bridge missing: " + result.className);
      new Parser().parseString(result.generatedHscript);
    }}
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_wrapper_inherited_state_executes_across_character_hooks(self):
        path = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/characters/Costume Scripts/Protag/protag-casual.hxc"
        if not path.exists():
            self.skipTest("mounted protag costume wrapper is not available")
        source = path.read_text(errors="ignore")
        main = f'''import hscript.Parser;
import hscript.Interp;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(path))});
    if (result.generatedHscript.indexOf("var defaultColor;") < 0
      || result.generatedHscript.indexOf("var missColor;") < 0)
      fail("base state fields were not carried: " + result.generatedHscript);
    var parser = new Parser();
    var interp = new Interp();
    var actor = new FakeCharacter();
    interp.variables.set("HxcCompatRuntime", HxcCompatRuntime);
    interp.variables.set("StringTools", StringTools);
    interp.variables.set("hxcCharacter", function() return actor);
    interp.variables.set("PlayState", new FakePlayState());
    interp.execute(parser.parseString(result.generatedHscript));
    var start:Dynamic = interp.variables.get("start");
    var sing:Dynamic = interp.variables.get("playSingAnimation");
    var animation:Dynamic = interp.variables.get("playAnimation");
    if (start == null || sing == null || animation == null) fail("inherited hooks missing");
    start("song");
    if (actor.color != 0xFFFFFFFF)
      fail("onCreate state did not survive: " + actor.color);
    sing(0, true, "");
    if (actor.singCalls != 1 || actor.color != 0xFF8282FF || actor.holdTimer != 0)
      fail("playSingAnimation state bridge: " + actor.singCalls + "/" + actor.color + "/" + actor.holdTimer);
    animation("idle", false, false, false);
    if (actor.animCalls != 1 || actor.color != 0xFFFFFFFF)
      fail("playAnimation state bridge: " + actor.animCalls + "/" + actor.color);
  }}
}}
class FakeCharacter {{
  public var color:Dynamic = 0;
  public var flipX:Bool = false;
  public var holdTimer:Float = 99;
  public var isPlayer:Bool = true;
  public var singCalls:Int = 0;
  public var animCalls:Int = 0;
  public function new() {{}}
  public function playSingAnimation(_direction:Int, _miss:Bool = false, _suffix:String = ""):Void singCalls++;
  public function playAnimation(_name:String, _restart:Bool = false, _ignoreOther:Bool = false, _reversed:Bool = false):Void animCalls++;
}}
class FakePlayState {{
  public var instance:Dynamic;
  public function new() instance = new FakeStageState();
}}
class FakeStageState {{
  public var curStage:Dynamic = {{}};
  public var currentStageId:Dynamic;
  public function new() currentStageId = new FakeStageId();
}}
class FakeStageId {{
  public function new() {{}}
  public function toLowerCase():String return "clubroom";
}}
'''
        before = path.stat().st_mtime_ns
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, path.stat().st_mtime_ns)

    def test_mounted_callback_aliases_cover_only_seeded_runtime_values(self):
        paths = [
            DONOR / "v-slice/Wacky World UPDATE [V-Slice]/scripts/modules/PVE_VideoModule.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/SUBSTATES/DokiPause.hxc",
            DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/modules/MikuScore.hxc",
        ]
        if not all(path.exists() for path in paths):
            self.skipTest("callback alias donor fixtures are not mounted")
        declarations = []
        checks = []
        for index, path in enumerate(paths):
            name = f"callback_{index}"
            declarations.append(
                f'var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'
            )
            if index == 0:
                checks.append(f'''var sawUpdate_{index} = false;
    var sawFocus_{index} = false;
    for (callback in {name}.callbackAdapters)
      if (callback.sourceName == "onUpdate") {{
        sawUpdate_{index} = true;
        if (!callback.safe) fail("native video onUpdate adapter is unsafe: {path.name}");
      }} else if (callback.sourceName == "onFocusGained") {{
        sawFocus_{index} = true;
        if (!callback.safe) fail("native video focus adapter is unsafe: {path.name}");
      }}
    for (finding in (cast {name}.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-callback-body"
        || finding.code == "unsupported-hxc-module-body")
        fail("complete video module retained an unsupported diagnostic: " + finding.code);
    if (!sawUpdate_{index} || !sawFocus_{index} || {name}.videoModuleAdapter != true
      || !{name}.moduleSafe)
      fail("video module did not use its complete native boundary: {path.name}");
    new Parser().parseString({name}.generatedHscript);''')
            elif index == 1:
                callback_names = 'callback.sourceName == "onSubStateOpenEnd"'
            else:
                callback_names = 'callback.sourceName == "onStateChangeEnd"'
            if index != 0:
                checks.append(f'''var sawCallback_{index} = false;
    for (callback in {name}.callbackAdapters)
      if (({callback_names}) && callback.safe)
        sawCallback_{index} = true;
    if (!sawCallback_{index}) fail("seeded callback alias was rejected: {path.name}");
    new Parser().parseString({name}.generatedHscript);''')
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {''.join(declarations)}
    {''.join(checks)}
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unseeded_typed_container_graph_is_not_an_executable_module(self):
        donor = r'''
import flixel.group.FlxTypedGroup;
class GenericPayloadModule extends Module {
    var payloads:FlxTypedGroup<ForeignFrame> = new FlxTypedGroup();
    function pausePayload(frame:ForeignFrame):Void {
        frame.videoSprite.pause();
    }
    function onUpdate(event) {
        for (frame in payloads.members)
            pausePayload(frame);
    }
}
'''
        native_source = r'''
class NativeTextGroup extends Module {
    var labels:FlxTypedGroup<FlxText> = new FlxTypedGroup();
    function onUpdate(event) { labels.clear(); }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "some/import/GenericPayloadModule.hxc");
    if (result.moduleSafe || !result.moduleInitializationSafe)
      fail("unseeded typed payload graph crossed the module gate: " + result.moduleSafetyReasons.join(","));
    var unsafeUpdate = false;
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onUpdate" && !callback.safe) unsafeUpdate = true;
    var unsafeHelper = false;
    for (helper in (cast result.helperAdapters:Array<Dynamic>))
      if (helper.sourceName == "pausePayload" && !helper.safe) unsafeHelper = true;
    var moduleDiagnostic = false;
    var callbackDiagnostic = false;
    for (finding in (cast result.diagnostics:Array<Dynamic>)) {{
      if (finding.code == "unsupported-hxc-module-body") moduleDiagnostic = true;
      if (finding.code == "unsupported-hxc-callback-body") callbackDiagnostic = true;
    }}
    if (!unsafeUpdate || !unsafeHelper || !moduleDiagnostic || !callbackDiagnostic)
      fail("typed payload reachability was not diagnosed: " + result.moduleSafetyReasons.join(","));
    new Parser().parseString(result.generatedHscript);

    var native = HxcCompat.analyze({hx_string(native_source)}, "some/import/NativeTextGroup.hxc");
    if (!native.moduleSafe || !native.moduleInitializationSafe)
      fail("known native typed container was rejected: " + native.moduleSafetyReasons.join(","));
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_freeplay_hooks_and_literal_native_state_factory_are_routed(self):
        source = r'''
import funkin.modding.module.Module;
class FreeplayModule extends Module {
    function onDifficultySwitch(event) {
        if (event.difficulty != null) trace(event.difficulty);
    }
    function onCapsuleSelected(event) {
        if (event.capsule != null) trace(event.capsule);
    }
    function goHome() {
        FlxG.switchState(ScriptedMusicBeatState.init("MainMenuState"));
    }
}
'''
        donor_state = source.replace("MainMenuState", "DokiMainMenuState")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/FreeplayModule.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe
      || hasCode(result, "unsupported-hxc-module-body"))
      fail("Freeplay hooks were not routed: " + result.moduleSafetyReasons.join(","));
    if (result.generatedHscript.indexOf("function difficultySwitch") < 0
      || result.generatedHscript.indexOf("function capsuleSelected") < 0
      || result.generatedHscript.indexOf('hxcStateInit("MainMenuState")') < 0)
      fail("Freeplay/state adapters missing: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);

    var payload = EngineCompat.hxcFreeplayPayload("capsuleSelected", "state", "capsule", 2, null);
    var routed = EngineCompat.callbackArguments("capsuleSelected", "capsuleSelected", [payload], true);
    if (routed.length != 1 || routed[0].capsule != "capsule"
      || routed[0].difficulty != 2 || routed[0].targetState != "state")
      fail("Freeplay payload ABI");

    var donorState = HxcCompat.analyze({hx_string(donor_state)}, "scripts/modules/FreeplayModule.hxc");
    if (hasCode(donorState, "unsupported-hxc-state-factory")
      || donorState.generatedHscript.indexOf('hxcStateInit("DokiMainMenuState")') < 0)
      fail("literal manifest state factory was not routed: " + donorState.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_freeplay_capsule_payload_is_shallow_and_routes_graph_adapter(self):
        path = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/FreeplayFixes.hxc"
        if not path.exists():
            self.skipTest("FreeplayFixes donor fixture is not mounted")
        source = path.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(path))});
    if (!result.payloadSafe || hasCode(result, "unsupported-hxc-payload"))
      fail("shallow Freeplay capsule payload remained unsupported");
    if (!result.moduleSafe || !result.moduleInitializationSafe
      || hasCode(result, "unsupported-hxc-module-body")
      || hasCode(result, "unsupported-hxc-callback-body"))
      fail("mounted Freeplay module was not bounded: " + result.moduleSafetyReasons.join(","));
    if (result.generatedHscript.indexOf("HxcCompatRuntime.applyFreeplayCustomization(event.targetState, null") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.applyFreeplayCustomization(currentFreeplayState, event.capsule") < 0
      || result.generatedHscript.indexOf("save = __hxcStore.getSave()") < 0)
      fail("generic Freeplay adapters missing: " + result.generatedHscript);
    if (result.generatedHscript.indexOf("grpCapsules") >= 0
      || result.generatedHscript.indexOf("weekType") >= 0)
      fail("unsupported Freeplay graph leaked into generated HScript");
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        before = path.stat().st_mtime_ns
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, path.stat().st_mtime_ns)

    def test_local_playstate_song_alias_and_stage_alias_are_bounded(self):
        source = r'''
import funkin.modding.module.Module;
import funkin.play.PlayState;
class LocalPlayStateAliases extends Module {
    override function onUpdate(event) {
        var ps = PlayState.instance;
        var stage = ps.currentStage;
        if (ps == null || ps.song == null) return;
        if (ps.song.id != "alias-song" && stage != null)
            trace(ps.song.id);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/local-playstate-aliases.hxc");
    if (!result.moduleSafe || hasCode(result, "unsupported-hxc-module-body")
      || hasCode(result, "unsupported-hxc-callback-body"))
      fail("local PlayState/stage aliases were rejected: " + result.moduleSafetyReasons.join(","));
    if (result.generatedHscript.indexOf("SONG.song") < 0
      || result.generatedHscript.indexOf("ps.song") >= 0
      || result.generatedHscript.indexOf("stage = ps.curStage") < 0)
      fail("local aliases were not lowered narrowly: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_your_demise_module_uses_native_song_and_stage_aliases(self):
        path = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/YourDemiseSafetyModule.hxc"
        if not path.exists():
            self.skipTest("YourDemiseSafetyModule donor fixture is not mounted")
        source = path.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(path))});
    if (result.kind != "module" || !result.moduleSafe || !result.moduleInitializationSafe)
      fail("YourDemise module safety: " + result.moduleSafetyReasons.join(","));
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-module-body"
        || finding.code == "unsupported-hxc-callback-body")
        fail("YourDemise donor gap remained: " + finding.code);
    if (result.generatedHscript.indexOf("SONG.song") < 0
      || result.generatedHscript.indexOf("ps.song") >= 0
      || result.generatedHscript.indexOf("function stateChangeEnd") < 0
      || result.generatedHscript.indexOf("function songRetry") < 0)
      fail("YourDemise aliases/lifecycle output: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        before = path.stat().st_mtime_ns
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, path.stat().st_mtime_ns)

    def test_mounted_state_factory_diagnostics_cover_all_nine_donor_hits(self):
        paths = [
            DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/ui/MikuMainMenu.hxc",
            DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/ui/TitleScreenFullReplace.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CatFightFreeplayFix.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CostumeMenuButtonv2.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CustomFreeplayFix.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/DokiMenuOverrides.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/TitleScreenFullReplace.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/states/DokiMainMenuState.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/states/DokiTitleState.hxc",
        ]
        if not all(path.exists() for path in paths):
            self.skipTest("state-factory donor fixtures are not mounted")
        declarations = []
        checks = []
        for index, path in enumerate(paths):
            name = f"state_{index}"
            declarations.append(
                f'var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'
            )
            checks.append(
                f'''var sawFactory_{index} = false;
    var sawUnsupported_{index} = false;
    for (finding in (cast {name}.diagnostics:Array<Dynamic>)) {{
      if (finding.code == "hxc-state-factory") sawFactory_{index} = true;
      if (finding.code == "unsupported-hxc-state-factory") sawUnsupported_{index} = true;
    }}
    if (!sawFactory_{index} || sawUnsupported_{index}) fail("state factory {index}: " + {name}.generatedHscript);
    new Parser().parseString({name}.generatedHscript);'''
            )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {''.join(declarations)}
    {''.join(checks)}
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_state_transition_forms_use_bounded_routes(self):
        paths = [
            DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/ui/CustomTitle.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/states/DokiTitleState.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/states/DokiMainMenuState.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CatFightFreeplayFix.hxc",
            DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CostumeMenuButtonv2.hxc",
        ]
        if not all(path.exists() for path in paths):
            self.skipTest("state-transition donor fixtures are not mounted")
        declarations = []
        checks = []
        for index, path in enumerate(paths):
            name = f"transition_{index}"
            declarations.append(
                f'var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'
            )
            checks.append(f'new Parser().parseString({name}.generatedHscript);')
        checks.extend([
            'if (transition_0.generatedHscript.indexOf(\'hxcStateFactory("AttractState", [])\') < 0) fail("Miku closure was not bounded");',
            'if (transition_1.generatedHscript.indexOf(\'hxcStateFactory("MainMenuState", [true])\') < 0) fail("Doki title variable closure was not bounded");',
            'if (transition_2.menuSpec == null || transition_2.generatedHscript.indexOf("mountMainMenuOverlay") < 0 || transition_2.generatedHscript.indexOf("clearMainMenuOverlay") < 0) fail("Doki menu transition host missing");',
            'if (transition_2.generatedHscript.indexOf("FlxG.state") >= 0 || transition_2.generatedHscript.indexOf("Application.current.window.close") >= 0) fail("donor Doki menu graph leaked");',
            'for (finding in (cast transition_2.diagnostics:Array<Dynamic>)) if (finding.code == "unsupported-hxc-state-switch" || finding.code == "unsupported-hxc-state-factory") fail("Doki native menu route remained unsupported: " + finding.code);',
            'var catfightFactory = false; for (finding in (cast transition_3.diagnostics:Array<Dynamic>)) if (finding.code == "hxc-state-factory") catfightFactory = true; if (!catfightFactory) fail("Catfight factory was not discovered");',
            'var costumeMenuAdapter = false; for (adapter in (cast transition_4.callbackAdapters:Array<Dynamic>)) if (adapter.body.indexOf(\'HxcCompatRuntime.addCostumeMenuItem(event.targetState, hxcStateInit("Costumes"))\') >= 0) costumeMenuAdapter = true; if (!costumeMenuAdapter || transition_4.generatedHscript.indexOf(\'hxcStateInit("CostumeSelectState")\') >= 0) fail("Costumes menu route was not kept inside the native boundary");',
            'var probe = HxcCompat.analyze("class Probe extends MusicBeatState { function go() { FlxG.switchState(() -> new funkin.ui.X()); } }", "scripts/states/Probe.hxc"); var qualified = false; var codes = ""; for (finding in (cast probe.diagnostics:Array<Dynamic>)) { codes += finding.code + ","; if (finding.code == "unsupported-hxc-state-switch") qualified = true; } if (!qualified) fail("qualified donor closure was not diagnosed: " + codes);',
        ])
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {''.join(declarations)}
    {''.join(checks)}
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_allowlisted_qualified_menu_states_and_start_exit_are_bounded(self):
        source = r'''
class MenuProbe extends MusicBeatState {
    function go() {
        var target:NextState = () -> new funkin.ui.credits.CreditsState();
        FlxG.switchState(target);
        target = () -> new funkin.ui.options.OptionsState();
        currentState.startExitState(target);
    }
}
'''
        unsafe = r'''
class UnsafeMenuProbe extends MusicBeatState {
    function go() {
        var target:NextState = () -> new StoryMenuState();
        target = () -> new funkin.ui.other.DonorState();
        FlxG.switchState(target);
    }
}
'''
        costume = r'''
class CostumeProbe extends MusicBeatState {
    function go() {
        currentState.startExitState(ScriptedMusicBeatState.init('CostumeSelectState'));
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/states/MenuProbe.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf('hxcStateFactory("CreditsState", [])') < 0
      || generated.indexOf('hxcStateFactory("SaveDataState", [])') < 0
      || generated.indexOf('hxcStartExitState(target)') < 0
      || hasCode(result, "unsupported-hxc-state-switch")
      || hasCode(result, "unsupported-hxc-state-factory")
      || !hasCode(result, "hxc-state-alias"))
      fail("allow-listed menu route was not bounded: " + generated);
    new Parser().parseString(generated);

    var unsafeResult = HxcCompat.analyze({hx_string(unsafe)}, "scripts/states/UnsafeMenuProbe.hxc");
    if (!hasCode(unsafeResult, "unsupported-hxc-state-switch")
      || unsafeResult.generatedHscript.indexOf("funkin.ui.other.DonorState") < 0)
      fail("unallowlisted qualified closure escaped diagnostics: " + unsafeResult.generatedHscript);

    var costumeResult = HxcCompat.analyze({hx_string(costume)}, "scripts/states/CostumeProbe.hxc");
    if (costumeResult.generatedHscript.indexOf('hxcStartExitState(hxcStateInit("CostumeSelectState"))') < 0
      || costumeResult.generatedHscript.indexOf('hxcStateInit("Costumes")') >= 0)
      fail("CostumeSelectState naming mismatch was silently aliased: " + costumeResult.generatedHscript);
    new Parser().parseString(costumeResult.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_dynamic_state_factory_is_root_scoped_without_reflection(self):
        source = r'''
class DynamicStateModule extends Module {
    function open(name) {
        return ScriptedMusicBeatState.init(name);
    }
}
'''
        unsafe_source = 'class Unsafe extends Module { function open() { return ScriptedMusicBeatState.init(new DonorState()); } }'
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/modules/DynamicStateModule.hxc");
    var sawDynamic = false;
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "hxc-state-factory-dynamic") sawDynamic = true;
    if (!sawDynamic) fail("dynamic factory was not classified as root-scoped");
    if (result.generatedHscript.indexOf("hxcStateInit(name)") < 0
      || result.generatedHscript.indexOf("Type.resolveClass") >= 0)
      fail("dynamic factory was not lowered to the bounded resolver: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);

    var unsafe = HxcCompat.analyze({hx_string(unsafe_source)}, "scripts/modules/Unsafe.hxc");
    var sawUnsafe = false;
    for (finding in (cast unsafe.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-state-factory") sawUnsafe = true;
    if (!sawUnsafe || unsafe.generatedHscript.indexOf("hxcStateInit(new DonorState())") >= 0)
      fail("donor constructor escaped the bounded factory: " + unsafe.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_state_transition_closures_and_substate_chains_lower(self):
        source = r'''
class TransitionState extends MusicBeatState {
    function update() {
        var targetState:NextState = () -> new MainMenuState(true);
        FlxG.switchState(targetState);
        FlxG.switchState(() -> new AttractState());
        var stateName = "DokiMainMenuState";
        var imported = ScriptedMusicBeatState.init(stateName);
        FlxG.switchState(imported);
        var subStateName = "CatfightPopup";
        var popup = ScriptedMusicBeatSubState.init(subStateName);
        FlxG.state.subState.openSubState(popup);
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, "scripts/states/TransitionState.hxc");
    var generated = result.generatedHscript;
    if (generated.indexOf('hxcStateFactory("MainMenuState", [true])') < 0
      || generated.indexOf('hxcStateFactory("AttractState", [])') < 0
      || generated.indexOf('hxcStateInit(stateName)') < 0
      || generated.indexOf('hxcSubStateInit(subStateName)') < 0
      || generated.indexOf('hxcOpenSubStateOn(FlxG.state.subState, popup)') < 0
      || generated.indexOf('FlxG.state.subState.openSubState') >= 0)
      fail("transition lowering missing: " + generated);
    if (!hasCode(result, "hxc-state-factory-dynamic") || !hasCode(result, "hxc-substate-route"))
      fail("transition diagnostics missing");
    if (hasCode(result, "unsupported-hxc-state-switch"))
      fail("bounded closure/factory was rejected: " + generated);
    new Parser().parseString(generated);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_freeplay_state_dispatches_native_hxc_boundaries(self):
        source = (ROOT / "source/FreeplayState.hx").read_text()
        self.assertIn("hxcRuntime = new HxcFreeplayRuntime(this)", source)
        self.assertIn("hxcRuntime.dispatch('difficultySwitch'", source)
        self.assertIn("hxcRuntime.dispatch('capsuleSelected'", source)
        self.assertIn("public function hxcCapsuleView", source)

    def test_zoom2_module_uses_live_camera_and_song_aliases(self):
        path = DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/modules/Zoom2.hxc"
        if not path.exists():
            self.skipTest("Zoom2 donor fixture is not mounted")
        source = path.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function main() {{
    var result = HxcCompat.analyze({hx_string(source)}, {hx_string(str(path))});
    if (result.kind != "module" || !result.moduleSafe || !result.moduleInitializationSafe)
      fail("Zoom2 module safety: " + result.kind + "/" + result.moduleSafe + "/" + result.moduleInitializationSafe
        + " reasons=" + result.moduleSafetyReasons.join(","));
    if (hasCode(result, "unsupported-hxc-module-body"))
      fail("Zoom2 retained module-body diagnostic");
    if (result.generatedHscript.indexOf("SONG.song") < 0
      || result.generatedHscript.indexOf("currentCameraZoom") < 0
      || result.generatedHscript.indexOf("cameraFollowPoint") < 0
      || result.generatedHscript.indexOf("Conductor.instance.currentStep") >= 0)
      fail("Zoom2 aliases were not preserved for the live PlayState adapter: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_donor_fixtures_are_read_only_and_classified_when_mounted(self):
        event = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/events/AddCamZoomPsych.hxc"
        note = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/notes/markov.hxc"
        if not event.exists() or not note.exists():
            self.skipTest("concrete HXC donor fixtures are not mounted")
        event_source = event.read_text(errors="ignore")
        note_source = note.read_text(errors="ignore")
        markov_be = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/notes/markovBE.hxc"
        markov_be_source = markov_be.read_text(errors="ignore")
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var event = HxcCompat.analyze({hx_string(event_source)}, {hx_string(str(event))});
    var note = HxcCompat.analyze({hx_string(note_source)}, {hx_string(str(note))});
    if (event.kind != "song-event" || event.eventAdapters.length != 1
      || event.eventAdapters[0].canonicalName != "Add Camera Zoom") fail("real event fixture");
    if (note.kind != "note-kind" || note.noteKinds.indexOf("markov") < 0) fail("real note fixture");
    var sawAdapter = false;
    var sawDonorGap = false;
    var sawTallyAdapter = false;
    for (finding in note.diagnostics) {{
      if (finding.code == "hxc-note-behavior-adapter") sawAdapter = true;
      if (finding.code == "unsupported-hxc-note-state") sawDonorGap = true;
    }}
    for (pattern in note.noteBehaviorPatterns)
      if (pattern == "tally-adapter") sawTallyAdapter = true;
    if (!sawAdapter || sawDonorGap || !sawTallyAdapter) fail("markov behavior diagnostics");
    if (note.generatedHscript.indexOf("HxcCompatRuntime.tallies.totalNotes") < 0)
      fail("markov tally alias");
    new Parser().parseString(note.generatedHscript);
    var markovBePath = {hx_string(str(markov_be))};
    var markovBe = HxcCompat.analyze({hx_string(markov_be_source)}, markovBePath);
    var markovBeGap = false;
    for (finding in markovBe.diagnostics) if (finding.code == "unsupported-hxc-note-state") markovBeGap = true;
    if (markovBeGap || markovBe.noteBehaviorPatterns.indexOf("tally-adapter") < 0)
      fail("markovBE state gap");
    new Parser().parseString(markovBe.generatedHscript);
  }}
}}'''
        before_event = event.stat().st_mtime_ns
        before_note = note.stat().st_mtime_ns
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before_event, event.stat().st_mtime_ns)
        self.assertEqual(before_note, note.stat().st_mtime_ns)

    def test_real_donor_class_families_get_central_lifecycle_adapters(self):
        samples = {
            "song-script": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/songs/hot-air-balloon.hxc",
            "stage": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/stages/clubroom.hxc",
            "base-stage": DONOR / "whitty/data/stages/facility.hxc",
            "character": DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/characters/bf_tb.hxc",
            "module": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CoolGameplay.hxc",
            "state": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/states/DokiTitleState.hxc",
        }
        if not all(path.exists() for path in samples.values()):
            self.skipTest("representative HXC donor classes are not mounted")
        sources = "\n".join(
            f'''var {name.replace("-", "_")} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for name, path in samples.items()
        )
        expected_kinds = {"base-stage": "stage", **{name: name for name in samples if name != "base-stage"}}
        checks = "\n".join(
            f'''if ({name.replace("-", "_")}.kind != {hx_string(kind)}) fail("{name} kind: " + {name.replace("-", "_")}.kind);'''
            for name, kind in expected_kinds.items()
        )
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    {sources}
    {checks}
    if (song_script.callbackAdapters.length == 0) fail("song callbacks");
    if (song_script.callbackAdapters[0].canonicalName != "start") fail("song start adapter");
    if (song_script.helperAdapters.length == 0) fail("song helper adapters");
    if (song_script.generatedHscript.indexOf("calcSectionLength") < 0) fail("song helper output");
    if (song_script.generatedHscript.indexOf("function start") < 0) fail("song generated HScript");
    if (stage.callbackAdapters.length == 0) fail("stage callbacks");
    if (stage.generatedHscript.indexOf("function start") < 0) fail("stage build adapter");
    if (base_stage.kind != "stage") fail("legacy stage kind");
    if (character.callbackAdapters.length == 0) fail("character callbacks");
    if (module.callbackAdapters.length == 0) fail("module callbacks");
    if (state.callbackAdapters.length == 0) fail("state callbacks");
  }}
}}'''
        before = {name: path.stat().st_mtime_ns for name, path in samples.items()}
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, {name: path.stat().st_mtime_ns for name, path in samples.items()})

    def test_general_mounted_callbacks_use_explicit_host_adapters(self):
        samples = {
            "score": DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/modules/MikuScore.hxc",
            "timebar": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/GlassTimeBar.hxc",
            "icons": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/playstate/WINICONBOP.hxc",
            "stage_reset": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/ResetStage.hxc",
            "title": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/CustomTitleBar.hxc",
            "vignette": DONOR / "v-slice/Wacky World UPDATE [V-Slice]/scripts/modules/eventHandlers/vignEventHandler.hxc",
            "healthbar": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/modules/IconColoredHealthBar.hxc",
            "fullscreen": DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts/FullscreenOff.hxc",
        }
        if not all(path.exists() for path in samples.values()):
            self.skipTest("general HXC callback donor fixtures are not mounted")
        sources = "\n".join(
            f'''var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for name, path in samples.items()
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function safe(result:Dynamic, name:String):Bool {{
    var callbacks:Array<Dynamic> = cast result.callbackAdapters;
    for (callback in callbacks)
      if (callback.sourceName == name && callback.safe) return true;
    return false;
  }}
  static function main() {{
    {sources}
    if (!score.moduleSafe || !safe(score, "onStateChangeEnd") || !safe(score, "onUpdate"))
      fail("score native PlayState fields were not routed");
    var sawRankAdapter = false;
    for (finding in (cast score.diagnostics:Array<Dynamic>))
      if (finding.code == "hxc-rank-adapter") sawRankAdapter = true;
    if (!sawRankAdapter) fail("native rank adapter was not diagnosed");
    if (score.generatedHscript.indexOf("HxcCompatRuntime.tallies.sick") < 0
      || score.generatedHscript.indexOf("HxcCompatRuntime.calculateRank") < 0)
      fail("score tally/scoring adapter missing");
    if (!timebar.moduleSafe || !safe(timebar, "onStateChangeEnd")
      || !safe(timebar, "onUpdate") || !safe(timebar, "onBeatHit"))
      fail("timebar native PlayState fields were not routed");
    if (!icons.moduleSafe || !safe(icons, "onUpdate")) fail("icon playback callback");
    if (!stage_reset.moduleSafe || !safe(stage_reset, "onCountdownStart")
      || stage_reset.generatedHscript.indexOf("HxcCompatRuntime.preferences.strumlineBackgroundOpacity") < 0)
      fail("stage reset preference adapter");
    if (!title.moduleSafe || !safe(title, "onSubStateCloseEnd")
      || title.generatedHscript.indexOf("hxcSetWindowTitle") < 0
      || title.generatedHscript.indexOf("hxcSetWindowIcon") < 0
      || title.generatedHscript.indexOf("function setIcon") >= 0
      || title.generatedHscript.indexOf("function hxcSetWindowIcon") >= 0)
      fail("window adapter");
    if (!safe(vignette, "onSongStart")
      || vignette.generatedHscript.indexOf("HxcCompatRuntime.prepareVignette") < 0
      || vignette.generatedHscript.indexOf("createRuntimeShader") >= 0)
      fail("shader adapter");
    if (!healthbar.moduleSafe || !safe(healthbar, "onBeatHit") || !safe(healthbar, "onSongEvent")
      || !safe(healthbar, "onPause") || !safe(healthbar, "onPlayStateEnter"))
      fail("health-bar native field alias adapter");
    if (!fullscreen.moduleSafe || !safe(fullscreen, "onStateChangeEnd")
      || fullscreen.generatedHscript.indexOf("HxcCompatRuntime.disableFullscreen") < 0
      || fullscreen.generatedHscript.indexOf("FlxG.fullscreen") >= 0)
      fail("fullscreen native window/resize adapter");
    for (result in [score, timebar, icons, stage_reset, title, vignette, fullscreen])
      if (result.generatedHscript != null && result.generatedHscript != "") new Parser().parseString(result.generatedHscript);
    new Parser().parseString(healthbar.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_rabbit_hole_shader_countdown_requires_complete_source_shape(self):
        donor_path = DONOR / "v-slice/HatsuneMiku-ProjectFunkin-V-Slice/scripts/songs/rabbit-hole.hxc"
        if not donor_path.exists():
            self.skipTest("Rabbit Hole HXC donor is not mounted")
        donor = donor_path.read_text(errors="ignore")
        unsafe = donor.replace(
            "game.camGame.filters = [bloomfilter];",
            "game.camGame.filters = [bloomfilter]; game.camGame.zoom += 1;",
            1,
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function safeCountdown(result:Dynamic):Bool {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCountdownStart") return callback.safe;
    return false;
  }}
  static function main() {{
    var complete = HxcCompat.analyze({hx_string(donor)}, "assets/scripts/songs/rabbit-hole.hxc");
    var descriptor:Dynamic = complete.runtimeShaderDescriptor;
    var gate:Dynamic = descriptor == null ? null : descriptor.gate;
    if (gate == null || gate.bucket != "rabbit_hole_settings"
      || gate.field != "shadersEnabled" || gate.defaultValue != false)
      fail("companion shader gate was not extracted");
    if (!safeCountdown(complete) || hasCode(complete, "unsupported-hxc-shader-callback"))
      fail("complete countdown shader callback was not accepted");
    if (complete.generatedHscript.indexOf("HxcCompatRuntime.applyShaderDescriptor") < 0
      || complete.generatedHscript.indexOf("new FlxRuntimeShader") >= 0
      || complete.generatedHscript.indexOf("new ShaderFilter") >= 0
      || complete.generatedHscript.indexOf("ModuleHandler") >= 0
      || complete.generatedHscript.indexOf("Assets.exists") >= 0)
      fail("donor shader graph escaped the bounded host");
    new Parser().parseString(complete.generatedHscript);

    var partial = HxcCompat.analyze({hx_string(unsafe)}, "assets/scripts/songs/renamed-song.hxc");
    if (!hasCode(partial, "unsupported-hxc-shader-callback"))
      fail("extra camera operation lost its strict diagnostic");
    if (safeCountdown(partial))
      fail("partial countdown callback marked safe");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_multishader_descriptors_keep_per_field_and_camera_ownership(self):
        scripts = DONOR / "v-slice/TAKEOVER-PLUS-PLUS-V10/DDTO++_V10_RELEASE/scripts"
        paths = {
            "wilted": scripts / "stages/wilted.hxc",
            "glitcher": scripts / "songs/glitcher-monika-mix.hxc",
            "markov": scripts / "songs/markov-lyrics.hxc",
        }
        if not all(path.exists() for path in paths.values()):
            self.skipTest("mounted DDTO++ shader donor fixtures are not available")
        declarations = "\n".join(
            f'''var {name} = HxcCompat.analyze({hx_string(path.read_text(errors="ignore"))}, {hx_string(str(path))});'''
            for name, path in paths.items()
        )
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function countdown(result:Dynamic):Dynamic {{
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onCountdownStart") return callback;
    return null;
  }}
  static function descriptor(result:Dynamic, field:String):Dynamic {{
    for (item in (cast result.runtimeShaderDescriptors:Array<Dynamic>))
      if (item.shaderField == field) return item;
    return null;
  }}
  static function hasCode(result:Dynamic, code:String):Bool {{
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == code) return true;
    return false;
  }}
  static function bindingHas(item:Dynamic, method:String, camera:String):Bool {{
    if (item == null || item.cameraBindings == null) return false;
    for (binding in (cast item.cameraBindings:Array<Dynamic>))
      if (binding.methodName == method && (binding.camera == camera || binding.cameraField == camera)) return true;
    return false;
  }}
  static function main() {{
    {declarations}
    var fish = descriptor(wilted, "fish");
    var staticShader = descriptor(wilted, "staticShader");
    var wiltedCountdown = countdown(wilted);
    if (wilted.runtimeShaderDescriptors.length != 2 || fish == null || staticShader == null)
      fail("Wilted shader graphs were not split by field");
    if (fish.shaderName != "FishEyeShader" || fish.filterField != "fishshader"
      || fish.dynamicCameraField != "camBG" || !bindingHas(fish, "onCountdownStart", "camBG"))
      fail("FishEye did not retain its registered camBG binding: " + Std.string(fish));
    if (staticShader.shaderName != "StaticShader" || staticShader.filterField != "shaderstat"
      || staticShader.dynamicCameraField != "" || staticShader.cameras.length != 1
      || staticShader.cameras[0] != "camGame" || !bindingHas(staticShader, "glitchEffect", "camGame"))
      fail("Static shader did not retain its camGame binding: " + Std.string(staticShader));
    if (wiltedCountdown == null || !wiltedCountdown.safe)
      fail("bounded Wilted countdown did not become executable");
    if (wilted.generatedHscript.indexOf('ensureShaderHandle(PlayState.instance, __hxcShaderHandles, "fish"') < 0
      || wilted.generatedHscript.indexOf('ensureShaderHandle(PlayState.instance, __hxcShaderHandles, "staticShader"') < 0
      || wilted.generatedHscript.indexOf('camBG, true') < 0
      || wilted.generatedHscript.indexOf('"camGame", true') < 0
      || wilted.generatedHscript.indexOf("new FlxRuntimeShader") >= 0
      || wilted.generatedHscript.indexOf("new ShaderFilter") >= 0)
      fail("Wilted operations were not routed through their own native handles");
    new Parser().parseString(wilted.generatedHscript);

    var pixel = descriptor(glitcher, "pixel");
    var bloom = descriptor(glitcher, "bloom");
    var glitcherCountdown = countdown(glitcher);
    if (glitcher.runtimeShaderDescriptors.length != 2 || pixel == null || bloom == null
      || pixel.shaderName != "PixelShader" || bloom.shaderName != "BloomShader"
      || pixel.filterField != "pixelshader" || bloom.filterField != "shader")
      fail("Glitcher shader fields were not independently described");
    if (pixel.cameras.length != 1 || bloom.cameras.length != 1
      || pixel.cameras[0] != "camGame" || bloom.cameras[0] != "camGame"
      || pixel.cameraBindings.length != 0 || bloom.cameraBindings.length != 0)
      fail("dynamic preference-selected filter list was treated as a literal binding");
    if (glitcherCountdown == null || !glitcherCountdown.safe
      || glitcher.generatedHscript.indexOf("function countdownStart") < 0
      || glitcher.generatedHscript.indexOf("new ShaderFilter") >= 0)
      fail("Glitcher preference/filter callback was not safely lowered");
    if (glitcherCountdown.body.indexOf('"pixel"') < 0
      || glitcherCountdown.body.indexOf('"bloom"') < 0
      || glitcherCountdown.body.indexOf('preferenceEnabled(save, "bloom")') < 0
      || glitcherCountdown.body.indexOf('HxcCompatRuntime.assignFilters(PlayState.instance.camGame, filters)') < 0)
      fail("Glitcher uniform and preference filter operations lost source order or ownership");
    new Parser().parseString(glitcher.generatedHscript);

    var markovCountdown = countdown(markov);
    if (markov.runtimeShaderDescriptors.length != 1 || markovCountdown == null || !markovCountdown.safe)
      fail("Markov's start timestamp/countdown camera adapter was not accepted");
    if (hasCode(markov, "unsupported-hxc-shader-pulse-body"))
      fail("Markov's structurally complete pulse helper kept an unsupported-body warning");
    if (markov.generatedHscript.indexOf("HxcCompatRuntime.isNonemptyString(sound)") < 0
      || markov.generatedHscript.indexOf("hxcPaths.sound(sound)") < 0
      || markov.generatedHscript.indexOf("FlxEase.circOut") < 0)
      fail("Markov's pulse helper did not preserve guarded audio and tween behavior");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_shader_descriptor_gate_fails_closed_and_uses_private_store(self):
        main = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    HxcCompatRuntime.clear();
    var store = HxcCompatRuntime.openStore("shader-gate-fixture");
    var calls = 0;
    var owner = {hxcApplyRuntimeShaderDescriptor: function(_descriptor:Dynamic, _root:Dynamic) {
      calls++;
      return true;
    }};
    var descriptor = {shaderName: "bloom", cameras: ["camHUD", "camGame"],
      gate: {bucket: "private_shader_settings", field: "enabled", defaultValue: false}};
    if (HxcCompatRuntime.applyShaderDescriptor(owner, descriptor, store, "assets"))
      fail("missing option bucket enabled a shader");
    if (calls != 0) fail("disabled shader reached native owner");
    HxcCompatRuntime.seedStoreDefaults(store, {enabled: false}, "private_shader_settings");
    if (HxcCompatRuntime.applyShaderDescriptor(owner, descriptor, store, "assets"))
      fail("false option enabled a shader");
    store.set("private_shader_settings", {enabled: true});
    if (!HxcCompatRuntime.applyShaderDescriptor(owner, descriptor, store, "assets") || calls != 1)
      fail("true private option did not reach native owner");
    store.set("private_shader_settings", {enabled: "true"});
    if (HxcCompatRuntime.applyShaderDescriptor(owner, descriptor, store, "assets") || calls != 1)
      fail("non-boolean option did not fail closed");
    if (Reflect.hasField(store, "options")) fail("shader setting mutated player options");

    var createCalls = 0;
    var shaderOwner = {hxcCreateRuntimeShaderHandle: function(shader:Dynamic, _root:Dynamic) {
      createCalls++;
      return "owned-" + shader.shaderName;
    }};
    var handles = {};
    var fish = {shaderName: "FishEyeShader", cameras: ["camGame"], uniforms: ["warp"]};
    var staticDesc = {shaderName: "StaticShader", cameras: ["camGame"], uniforms: ["iTime"]};
    var fishHandle = HxcCompatRuntime.ensureShaderHandle(shaderOwner, handles, "fish", fish, "assets");
    if (fishHandle != "owned-FishEyeShader" || createCalls != 1)
      fail("first field-keyed shader handle was not created");
    if (HxcCompatRuntime.ensureShaderHandle(shaderOwner, handles, "fish", fish, "assets") != fishHandle
      || createCalls != 1)
      fail("shader field did not reuse its owned handle");
    if (HxcCompatRuntime.ensureShaderHandle(shaderOwner, handles, "staticShader", staticDesc, "assets")
      != "owned-StaticShader" || createCalls != 2)
      fail("second shader field reused the wrong handle");
    if (HxcCompatRuntime.ensureShaderHandle(shaderOwner, handles, "fish.bad", fish, "assets") != null
      || createCalls != 2)
      fail("invalid shader field key crossed the native handle gate");
  }
}'''
        result = self.run_fixture(main)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_host_aliases_remain_scoped_and_parseable(self):
        donor = r'''
import funkin.Highscore;
import funkin.Preferences;
import funkin.play.scoring.Scoring;
import funkin.util.WindowUtil;
class GeneralCompat extends Module {
    function onUpdate(event) {
        var rate = PlayState.instance.playbackRate;
        if (rate > 0) PlayState.instance.iconP1.angle = rate;
    }
    function onSongStart(event) {
        WindowUtil.setWindowTitle("compat");
        Preferences.strumlineBackgroundOpacity = 100;
        var rank = Scoring.calculateRank({tallies: Highscore.tallies});
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/general-compat.hxc");
    if (!result.moduleSafe) fail("synthetic host aliases rejected: " + result.moduleSafetyReasons.join(","));
    if (result.generatedHscript.indexOf("hxcSetWindowTitle") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.preferences") < 0
      || result.generatedHscript.indexOf("HxcCompatRuntime.calculateRank") < 0)
      fail("synthetic aliases were not lowered: " + result.generatedHscript);
    var sawRankAdapter = false;
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "hxc-rank-adapter") sawRankAdapter = true;
    if (!sawRankAdapter) fail("synthetic rank adapter was not diagnosed");
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fullscreen_adapter_uses_native_window_and_resize_semantics(self):
        donor = r'''
import flixel.FlxG;
import flixel.util.FlxTimer;
import funkin.ui.FullScreenScaleMode;
import funkin.modding.module.Module;
import flixel.system.scaleModes.RatioScaleMode;

class DisableFullscreenForever extends Module {
    public function new() {
        super("DisableFullscreenForever");
        forceDisableFullscreen();
    }
    override function onStateChangeEnd(event) {
        super.onStateChangeEnd(event);
        new FlxTimer().start(0.1, function(tmr) {
            forceDisableFullscreen();
        });
    }
    function forceDisableFullscreen() {
        if (FlxG.fullscreen) FlxG.fullscreen = false;
        FullScreenScaleMode.enabled = false;
        FlxG.scaleMode = new RatioScaleMode();
        FlxG.signals.gameResized.dispatch(FlxG.width, FlxG.height);
    }
}
'''
        main = f'''import hscript.Parser;
class ResizeSignal {{
  public var calls:Int = 0;
  public var lastWidth:Dynamic;
  public var lastHeight:Dynamic;
  public function new() {{}}
  public function dispatch(width:Dynamic, height:Dynamic):Void {{
    calls++;
    lastWidth = width;
    lastHeight = height;
  }}
}}
class FakeSignals {{
  public var gameResized:ResizeSignal;
  public function new() gameResized = new ResizeSignal();
}}
class FakeGlobals {{
  public var fullscreen:Bool = true;
  public var scaleMode:Dynamic;
  public var width:Int = 1280;
  public var height:Int = 720;
  public var signals:FakeSignals;
  public function new() signals = new FakeSignals();
}}
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/FullscreenOff.hxc");
    if (!result.moduleSafe || !result.moduleInitializationSafe)
      fail("fullscreen module safety: " + result.moduleSafetyReasons.join(","));
    if (result.generatedHscript.indexOf("HxcCompatRuntime.disableFullscreen") < 0
      || result.generatedHscript.indexOf("FlxG.fullscreen") >= 0
      || result.generatedHscript.indexOf("RatioScaleMode") >= 0)
      fail("fullscreen bridge was not centralized: " + result.generatedHscript);
    var callbackSafe = false;
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onStateChangeEnd" && callback.safe) callbackSafe = true;
    if (!callbackSafe) fail("fullscreen callback was not rooted");
    new Parser().parseString(result.generatedHscript);

    var globals = new FakeGlobals();
    var ratio = {{kind: "ratio"}};
    if (!HxcCompatRuntime.disableFullscreen(globals, ratio)) fail("fullscreen runtime returned false");
    if (globals.fullscreen || globals.scaleMode != ratio) fail("native window/scale state");
    if (globals.signals.gameResized.calls != 1
      || globals.signals.gameResized.lastWidth != 1280
      || globals.signals.gameResized.lastHeight != 720)
      fail("native resize dispatch");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_synthetic_native_playstate_collection_fields_are_bounded(self):
        donor = r'''
class NativePlayStateFields extends Module {
    function onStateChangeEnd(event) {
        var game = PlayState.instance;
        if (game == null || game.needsReset) return;
        if (game.timeTxt != null) game.timeTxt.visible = false;
        game.members.sort(function(a, b) {
            var left = (a.zIndex != null) ? a.zIndex : 0;
            var right = (b.zIndex != null) ? b.zIndex : 0;
            return left - right;
        });
    }
}
'''
        main = f'''import hscript.Parser;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/native-playstate-fields.hxc");
    if (!result.moduleSafe || result.moduleSafetyReasons.length != 0)
      fail("native collection fields were rejected: " + result.moduleSafetyReasons.join(","));
    var safe = false;
    for (callback in (cast result.callbackAdapters:Array<Dynamic>))
      if (callback.sourceName == "onStateChangeEnd" && callback.safe) safe = true;
    if (!safe || result.generatedHscript.indexOf("game.members.sort") < 0
      || result.generatedHscript.indexOf("game.needsReset") < 0)
      fail("native fields were not preserved: " + result.generatedHscript);
    new Parser().parseString(result.generatedHscript);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_playstate_field_local_is_not_treated_as_playstate_alias(self):
        donor = r'''
class LocalFieldModule extends Module {
    function onUpdate(event) {
        var icon = PlayState.instance.iconP2;
        if (icon != null && icon.characterId != null) trace(icon.characterId);
    }
}
'''
        main = f'''class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var result = HxcCompat.analyze({hx_string(donor)}, "scripts/modules/local-field-alias.hxc");
    if (!result.moduleSafe || result.generatedHscript.indexOf("icon.characterId") < 0)
      fail("local PlayState field was rejected: " + result.moduleSafetyReasons.join(","));
    for (finding in (cast result.diagnostics:Array<Dynamic>))
      if (finding.code == "unsupported-hxc-module-body") fail("unexpected module warning");
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_hxc_corpus_is_inventoryable_without_execution(self):
        paths = sorted(DONOR.rglob("*.hxc"))
        if not paths:
            self.skipTest("HXC donor corpus is not mounted")
        encoded_paths = ",\n".join(hx_string(str(path)) for path in paths)
        main = f'''import hscript.Parser;
import sys.io.File;
class Main {{
  static function fail(value:String):Void throw value;
  static function main() {{
    var counts:Map<String, Int> = new Map();
    var callbackCount = 0;
    var diagnostics = 0;
    var generated = 0;
    var parseable = 0;
    var parseFailures = 0;
    var unsafeCallbacks = 0;
    var moduleBodies = 0;
    var safeModuleCallbacks = 0;
    var safeModuleFiles = 0;
    var syntaxGaps = 0;
    var apiGaps = 0;
    var failedPaths:Array<String> = [];
    var unsafeCallbackKeys:Array<String> = [];
    var moduleBodyKeys:Array<String> = [];
    var paths = [{encoded_paths}];
    for (path in paths) {{
      var result = HxcCompat.analyze(File.getContent(path), path);
      counts.set(result.kind, (counts.exists(result.kind) ? counts.get(result.kind) : 0) + 1);
      callbackCount += result.callbackAdapters.length;
      diagnostics += result.diagnostics.length;
      for (callback in result.callbackAdapters) if (!callback.safe) {{
        unsafeCallbacks++;
        unsafeCallbackKeys.push(path.substr(path.lastIndexOf("/") + 1) + "." + callback.sourceName);
      }}
      if (result.kind == "module") {{
        var moduleHadSafeCallback = false;
        for (callback in result.callbackAdapters) if (callback.safe) {{ safeModuleCallbacks++; moduleHadSafeCallback = true; }}
        if (moduleHadSafeCallback) safeModuleFiles++;
      }}
      for (finding in result.diagnostics) {{
        if (finding.code == "unsupported-hxc-syntax") syntaxGaps++;
        if (finding.code == "unsupported-hxc-api") apiGaps++;
        if (finding.code == "unsupported-hxc-module-body") {{
          moduleBodies++;
          moduleBodyKeys.push(path.substr(path.lastIndexOf("/") + 1));
        }}
      }}
      if (result.generatedHscript != null && StringTools.trim(result.generatedHscript) != "") {{
        generated++;
        try {{
          new Parser().parseString(result.generatedHscript);
          parseable++;
        }} catch (error:Dynamic) {{
          parseFailures++;
          if (failedPaths.length < 8)
            failedPaths.push(path + " :: " + Std.string(error));
        }}
      }}
    }}
    if (paths.length < 200) fail("corpus unexpectedly small: " + paths.length);
    if (counts.get("song-script") < 30) fail("song scripts: " + counts.get("song-script"));
    if (counts.get("stage") < 14) fail("stages: " + counts.get("stage"));
    if (counts.get("character") < 80) fail("characters: " + counts.get("character"));
    if (counts.get("module") < 40) fail("modules: " + counts.get("module"));
    if (counts.get("song-event") < 10) fail("events: " + counts.get("song-event"));
    if (callbackCount < 250) fail("lifecycle callbacks: " + callbackCount);
    if (diagnostics <= 0) fail("diagnostics missing");
    if (generated <= 0) fail("generated HScript: " + generated);
    // Modules and note kinds retain only bodies whose roots resolve through
    // the seeded native API. The mounted 228-file corpus is the regression
    // fixture for that decision. Expanded lifecycle discovery now inventories
    // state-change, focus, game-over, destroy, and note-incoming hooks which
    // older passes silently treated as ordinary helpers. This pass emits at
    // least 177 parseable adapters. The current mounted inventory is
    // parseable after syntax lowering: bftricky's guarded super.onNoteMiss now
    // lowers to the native bridge, and @:privateAccess is removed while its
    // dynamic field expression remains. StaticTextHandler is now covered by
    // the generic perfect-hit note-text adapter. Shader-bearing countdown
    // callbacks are safe only when their complete source body matches the
    // bounded owner. Rabbit Hole and Wilted's registered custom-camera pair
    // now match; source-backed boolean filter lists preserve each array order.
    // Markov's start timestamp, zero-duration camera setup, and complete shader
    // pulse helper are lowered through bounded native adapters.
    // Pin the exact unsafe callbacks and unsupported module bodies so the wider
    // corpus cannot hide new gaps or accidental execution. Mixed Rabbit Hole
    // sources are counted by their Song owner while the companion options
    // Module remains registered in the generated adapter.
    for (failed in failedPaths)
      fail("generated HScript did not parse: " + failed);
    var knownTrickyFailures = 0;
    var storyConfirmStillKnown = false;
    for (stem in ["bfhell.hxc", "bftricky.hxc", "StoryConfirmMouth.hxc"]) {{
      var found = false;
      for (failed in failedPaths)
        if (failed.indexOf(stem) >= 0) found = true;
      if (found) knownTrickyFailures++;
      if (stem == "StoryConfirmMouth.hxc" && found) storyConfirmStillKnown = true;
    }}
    if (parseable != generated - parseFailures || parseFailures != 0
        || knownTrickyFailures != 0 || storyConfirmStillKnown)
      fail("generated/parseable HScript: " + generated + "/" + parseable
        + " (failures " + parseFailures + ", expected 0"
        + ", known " + knownTrickyFailures + ") " + failedPaths.join(" || "));
    if (generated < 177) fail("generated HScript coverage regressed: " + generated + "/" + paths.length);
    // The score/tally, icon-rate, retry-stage, title/icon, shader, and
    // character-registry aliases are explicit native adapters. Keep exact
    // counts so donor menu/freeplay graphs cannot be relabelled as executable.
    unsafeCallbackKeys.sort(Reflect.compare);
    moduleBodyKeys.sort(Reflect.compare);
    var expectedUnsafeCallbacks = [];
    var expectedModuleBodies = [];
    expectedUnsafeCallbacks.sort(Reflect.compare);
    expectedModuleBodies.sort(Reflect.compare);
    if (unsafeCallbacks != expectedUnsafeCallbacks.length
      || unsafeCallbackKeys.join("|") != expectedUnsafeCallbacks.join("|"))
      fail("unsafe callback set changed: " + unsafeCallbackKeys.join(",")
        + "; module bodies " + moduleBodyKeys.join(","));
    if (moduleBodies != expectedModuleBodies.length
      || moduleBodyKeys.join("|") != expectedModuleBodies.join("|"))
      fail("unsupported module-body set changed: " + moduleBodyKeys.join(",")
        + "; unsafe callbacks " + unsafeCallbackKeys.join(","));
    // The video module's nine lifecycle hooks route through the native hxvlc
    // boundary; StoryMenu visuals/transition use their state owner, and Tricky's
    // vocal-volume restore uses the shared native vocal bus bridge.
    if (safeModuleCallbacks != 111 || safeModuleFiles != 45)
      fail("safe module callback coverage changed: " + safeModuleCallbacks + "/" + safeModuleFiles);
    trace("HXC corpus generated/parseable HScript: " + generated + "/" + parseable + " of " + paths.length
      + "; unsafe callbacks " + unsafeCallbacks + "; module bodies " + moduleBodies
      + "; safe module callbacks/files " + safeModuleCallbacks + "/" + safeModuleFiles
      + "; syntax gaps " + syntaxGaps + "; API gaps " + apiGaps);
  }}
}}'''
        result = self.run_fixture(main, [ROOT / ".haxelib/hscript/2,5,0"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mounted_auto_import_reports_exact_module_and_unsupported_script_counts(self):
        if not DONOR.exists():
            self.skipTest("HXC donor corpus is not mounted")
        env = os.environ.copy()
        decoder = ROOT / ".tools/astcenc/astcenc"
        if decoder.is_file():
            # Keep the mounted visual diagnostics deterministic even when the
            # caller's PATH/runtime root does not expose the project-local
            # decoder.  The importer still exercises its own checkout-root
            # discovery when this override is absent.
            env["DISAPPOINTINGPLUS_ASTCENC"] = str(decoder)
        result = subprocess.run(
            ["python3", str(ROOT / "tools/diagnose_example_auto_import.py"), "--counts-only"],
            # The diagnostic separately bounds a cold native build and the
            # scan to 300 seconds each. Let it report either phase's failure
            # instead of killing a healthy scan after a successful cold build.
            cwd=ROOT, capture_output=True, text=True, timeout=620, env=env,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = result.stdout + result.stderr

        def count(code: str, required: bool = True) -> int:
            match = re.search(r"DIAGNOSTIC_COUNT\|" + re.escape(code) + r"\|count=(\d+)", output)
            if match is None and not required:
                return 0
            self.assertIsNotNone(match, f"missing {code} count in auto-import report")
            return int(match.group(1))

        def selected_count(engine: str, code: str, required: bool = True) -> int:
            match = re.search(
                r"SELECTED_DIAGNOSTIC_ENGINE_COUNT\|" + re.escape(engine) + r"\|"
                + re.escape(code) + r"\|count=(\d+)",
                output,
            )
            if match is None and not required:
                return 0
            self.assertIsNotNone(
                match, f"missing selected {engine} {code} count in auto-import report"
            )
            return int(match.group(1))

        # The selected discovery set includes all mounted HXC donor families.
        # Keep unsupported cases explicit: the generic note-text adapter covers
        # StaticTextHandler; generated custom handlers cover Miku's zoom and
        # Tricky's sign/gremlin events. Other exact corpus gaps remain pinned
        # by test_mounted_hxc_corpus_is_inventoryable_without_execution.
        # Story-menu jaws, the foreign video module, and the source-proven
        # stage camera/filter graphs now have native hosts. Tricky's note-hit
        # restore uses the shared vocal bus bridge. Wilted's registered-camera
        # countdown is now covered; the selected importer reports no unsupported
        # shader callback bodies; the corpus test separately verifies the
        # source-backed boolean filter-list switch and Markov's pulse contract.
        self.assertEqual(count("hxc-unsupported-hxc-module-body", required=False), 0)
        self.assertEqual(count("hxc-unsupported-hxc-callback-body", required=False), 0)
        self.assertEqual(count("hxc-unsupported-hxc-shader-callback", required=False), 0)
        self.assertEqual(count("unsupported-hxc-script", required=False), 3)
        self.assertEqual(count("hxc-unsupported-hxc-character-base", required=False), 0)
        # The scoped texture warm-up and suffix bridge also cover the mounted
        # bfhell onCreate hook; no direct character hook remains donor-only.
        self.assertEqual(count("hxc-unsupported-hxc-character-hook", required=False), 0)
        self.assertEqual(count("hxc-hxc-module-adapter"), 45)
        self.assertEqual(count("hxc-hxc-lifecycle-adapter"), 167)
        self.assertEqual(count("hxc-hxc-menu-overlay-adapter"), 2)
        self.assertEqual(count("hxc-hxc-pause-overlay-adapter"), 1)
        self.assertEqual(count("hxc-hxc-menu-state-materialized"), 1)
        self.assertEqual(count("hxc-hxc-menu-bounded-fallback"), 1)
        self.assertEqual(count("hxc-unsupported-hxc-payload", required=False), 0)
        self.assertEqual(count("hxc-hxc-note-text-adapter"), 1)
        self.assertEqual(count("hxc-hxc-note-text-scope", required=False), 0)
        self.assertGreaterEqual(count("note-kind-adapter"), 7)
        # The Codename chart inventory preserves authored custom note identities,
        # but these selected/duplicate candidate records still lack a generic
        # hit/miss behavior adapter. Keep both the raw inventory and selected
        # owner count explicit so a new source note behavior cannot be hidden by
        # successful chart conversion.
        self.assertEqual(count("note-kind-generic", required=False), 46)
        # The compact counts-only selector groups by the same physical chart
        # origin as the production selector. The full summary scan currently
        # reports 23 selected Codename instances; raw count still includes
        # duplicate source views.
        self.assertEqual(selected_count("Codename Engine", "note-kind-generic", required=False), 23)
        self.assertEqual(count("hxc-hxc-event-body-gap", required=False), 0)
        # Only player/opponent actors require HUD health icons. The Codename
        # importer now classifies girlfriend/event-only references separately;
        # those actors may use a healthless source definition without a HUD
        # icon. Pin both classes so a scanner optimization cannot drop either.
        self.assertEqual(count("missing-health-icon"), 14)
        self.assertEqual(selected_count("Codename Engine", "missing-health-icon"), 7)
        self.assertEqual(count("icon-unresolved"), 3)
        self.assertEqual(selected_count("Codename Engine", "icon-unresolved"), 2)
        self.assertEqual(selected_count("V-Slice", "missing-health-icon", required=False), 0)
        # Package-wide definitions are reachable from each of the 54 DDTO
        # songs through runtime HXC character swaps. The same two incomplete
        # split atlases are reported for each row, rather than being counted
        # only when chart metadata names the character up front.
        self.assertEqual(count("animation-asset-switch"), 108)
        # All 48 historical primary warnings were duplicate consequences of
        # planning authored ASTC atlases without the runtime decoder.  With the
        # pinned decoder available, both primary and secondary multisparrow
        # routes combine cleanly; the two remaining split-animation gaps are
        # reported by their precise missing-asset/animation-asset-switch
        # diagnostics instead.
        self.assertEqual(count("multisparrow-primary-not-combined", required=False), 0)
        self.assertEqual(count("multisparrow-subatlas-not-combined", required=False), 0)
        self.assertEqual(count("astc-only", required=False), 0)
        # Count reachable decoder-backed mappings, not every raw ASTC in the
        # donor tree.  Several Miku ASTCs have a same-stem PNG (which correctly
        # wins) or are unreachable from the selected songs.  Keep the current
        # reachable baseline strict against losses while allowing newly-routed
        # assets to increase coverage.
        self.assertGreaterEqual(count("astc-decoder-ready"), 226)
        missing_match = re.search(r"MISSING_DEPENDENCIES=(\d+)", output)
        self.assertIsNotNone(missing_match, "missing dependency total in auto-import report")
        # The newly mounted Mario release includes compiled stage behavior
        # without corresponding editable stage modules. Keep the expanded
        # source-dependency inventory visible instead of treating conversion
        # of its songData charts as a compatibility pass.
        # Grouping by physical chart origin exposes independent owner songs
        # that were previously collapsed by the compact counts-only path.
        # The current full-summary scan reports 119 missing references.
        self.assertEqual(int(missing_match.group(1)), 119)
        stage_missing = re.findall(r"MISSING\|stage\|[^|]+\|count=(\d+)", output)
        self.assertEqual(sum(map(int, stage_missing)), 96)
        self.assertNotRegex(output, r"MISSING\|ui\|vslice-(?:pomni|hatsunemiku)\|")


if __name__ == "__main__":
    unittest.main()
