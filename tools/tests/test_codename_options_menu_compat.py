"""Exercise the shared Codename options menu's native settings adapter."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


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


class CodenameOptionsMenuCompatTest(unittest.TestCase):
    def test_imported_caller_route_is_retained_through_controls_and_exit(self):
        source = (ROOT / "source/CodenameOptionsMenuCompat.hx").read_text()
        self.assertIn("Std.isOfType(FlxG.state, CodenameImportedState)", source)
        self.assertIn("source.scriptPath", source)
        self.assertIn("categoryIndex, rowIndex, returnOwnerRoot, returnScriptPath", source)
        self.assertIn("CodenameModRuntime.stateInit(returnOwnerRoot, returnScriptPath)", source)

    def test_menu_row_motion_is_scaled_and_frame_rate_independent(self):
        source = (ROOT / "source/CodenameOptionsMenuCompat.hx").read_text(encoding="utf-8")
        self.assertIn("row.scale.set(ROW_SCALE, ROW_SCALE);", source)
        self.assertIn("static inline var ROW_SCALE:Float = 0.85;", source)
        self.assertIn("static inline var ROW_MOTION_RATE:Float = 2;", source)
        self.assertIn("Reflect.field(row, 'kind') == 'action'", source)
        self.assertIn("Reflect.field(row, 'field') == 'controls'", source)
        helper = extract_method(
            (ROOT / "source/CoolUtil.hx").read_text(encoding="utf-8"),
            "public static function timeAdjustedLerpAlpha",
        )
        update_motion = extract_method(source, "function updateRowMotion")
        fixture = f"""
class CoolUtil {{
{helper}
}}
class FakeText {{ public var y:Float; public function new(y:Float) this.y = y; }}
class FakeGroup {{ public var members:Array<FakeText>; public function new(row:FakeText) members = [row]; }}
class CodenameOptionsMenuCompat {{
    static inline var ROW_MOTION_RATE:Float = 2;
    var rowMotionTargetYs:Array<Float> = [118];
    var rowMotionActive:Bool = true;
    var rowGroup:FakeGroup;
    public function new() rowGroup = new FakeGroup(new FakeText(132.1));
{update_motion}
    public function advance(elapsed:Float):Void updateRowMotion(elapsed);
    public function rowY():Float return rowGroup.members[0].y;
}}
class MenuRowMotionMain {{
    static function runAtRate(fps:Int, duration:Float):Float {{
        var menu = new CodenameOptionsMenuCompat();
        for (_ in 0...Std.int(fps * duration)) menu.advance(1.0 / fps);
        return menu.rowY();
    }}
    static function main() {{
        var expected = runAtRate(60, 0.05);
        for (fps in [60, 480, 1440, 5000]) {{
            var actual = runAtRate(fps, 0.05);
            if (Math.abs(actual - expected) > 1e-8)
                throw 'selection motion changed at ' + fps + ' fps';
        }}
        var twiceRate = 132.1 + (118 - 132.1) * CoolUtil.timeAdjustedLerpAlpha(0.16, 0.05 * 2);
        if (Math.abs(expected - twiceRate) > 1e-8)
            throw 'selection motion did not use the configured 2x rate';
    }}
}}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            path = Path(directory) / "MenuRowMotionMain.hx"
            path.write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "MenuRowMotionMain", "--interp"],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_model_navigation_values_and_private_settings_copy(self):
        model = (ROOT / "source/CodenameOptionsMenuModel.hx").read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "CodenameOptionsMenuModel.hx").write_text(model, newline='\n')
            (base / "OptionsCategories.hx").write_text(
                (ROOT / "source/OptionsCategories.hx").read_text(), newline='\n')
            (base / "CodenameOptionsQualityCompat.hx").write_text(
                (ROOT / "source/CodenameOptionsQualityCompat.hx").read_text()
            , newline='\n')
            (base / "OptionsHandler.hx").write_text("""class OptionsHandler {
 public static inline var MAX_FPS_CAP:Int=2147483647;
 public static inline var DYNAMIC_SCROLL_SPEED_MAX:Float=10;
 public static inline var DYNAMIC_SCROLL_SPEED_STEP:Float=0.5;
 public static function sanitizeOffset(value:Dynamic):Float {
  var offset:Float=value; return Math.floor(offset*10+0.5)/10;
 }
}
""", newline='\n')
            (base / "Main.hx").write_text(r'''class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function row(category:String, label:String):Dynamic {
  for (item in CodenameOptionsMenuModel.rows(category))
   if (item.label == label) return item;
  return null;
 }
 static function main():Void {
  var categories = CodenameOptionsMenuModel.categories();
  check(categories.join(",") == "Gameplay,Controls & Timing,Graphics & Performance,Audio,Interface,Compatibility",
   "Codename options categories or source order changed");
  var controlsAction = row("Controls & Timing", "Controls...");
  check(controlsAction != null && controlsAction.kind == "action"
   && CodenameOptionsMenuModel.valueText({}, controlsAction) == ""
   && row("Controls", "Controls...") != null,
   "Controls action row or legacy category alias was not preserved");
  check(CodenameOptionsMenuModel.rows("Compatibility").length > 0,
   "Compatibility did not expose existing engine compatibility settings");
  var sharedFields=["offset", "controls", "showTimings", "fpsCap", "unlimitedFPS",
   "showFPS", "showMemory", "showNoteSplashes", "useCharColor", "lyricsEnabled", "zoomCamera",
   "normalizeSongAudio", "ignoreUnlocks", "emuOsuLifts", "useKadeHealth", "fastSceneTransitions"];
  for(field in sharedFields) {
   var occurrences=0;
   for(category in categories) for(item in CodenameOptionsMenuModel.rows(category))
    if(item.field==field) {
     occurrences++;
     check(OptionsCategories.sectionFor(field)==category,"shared option changed sections: "+field);
    }
   check(occurrences==1,"shared option duplicated or missing: "+field);
  }
  var native:Dynamic = {
   downscroll:false, midscroll:false, useCustomInput:true, naughtyness:true,
   volumeMusic:1.0, volumeSFX:1.0, useCharColor:true, scrollSpeed:1.0,
   normalizeSongAudio:false, dynamicScrollSpeed:0.0, offset:0.0, showSongPos:true, showTimings:true,
   showNoteSplashes:true, camNotes:false, zoomCamera:true, flashingLights:true,
           antialiasing:true, gameplayShaders:true, vignetteEffects:true, lyricsEnabled:true,
   week6PixelPerfect:true, quality:CodenameOptionsQualityCompat.HIGH,
   fpsCap:60, autoPause:true, lowMemoryMode:false, showFPS:false, showMemory:false,
   alwaysDoCutscenes:false, skipVictoryScreen:false, fastSceneTransitions:false,
   ignoreUnlocks:false, emuOsuLifts:false, useKadeHealth:false, unrelatedSaveField:"preserve"
  };
  var work = CodenameOptionsMenuModel.copyOptions(native);
  var legacyHealth = row("Compatibility", "Use Kade Health");
  check(CodenameOptionsMenuModel.adjust(work, legacyHealth, 1)
   && work.useKadeHealth && !native.useKadeHealth,
   "compatibility setting did not toggle only the private options copy");
  var downscroll = row("Gameplay", "Downscroll");
  check(CodenameOptionsMenuModel.adjust(work, downscroll, 1), "toggle did not change");
  check(work.downscroll == true && native.downscroll == false,
   "options editing mutated the cached settings before menu exit");
  var normalize = row("Audio", "Normalize Song Audio");
  check(normalize != null && normalize.field == "normalizeSongAudio"
   && CodenameOptionsMenuModel.valueText(work, normalize) == "Off",
   "Codename normalize-song-audio row did not read the saved toggle");
  check(CodenameOptionsMenuModel.adjust(work, normalize, 1)
   && work.normalizeSongAudio == true && native.normalizeSongAudio == false
   && CodenameOptionsMenuModel.valueText(work, normalize) == "On",
   "Codename normalize-song-audio row did not toggle the private options copy");
  var scroll = row("Gameplay", "Scroll Speed");
  check(CodenameOptionsMenuModel.adjust(work, scroll, 1) && work.scrollSpeed == 1.1,
   "scroll speed did not step by its native menu increment");
  for (i in 0...120) CodenameOptionsMenuModel.adjust(work, scroll, 1);
  check(work.scrollSpeed == 10.0, "scroll speed did not clamp to the native maximum");
  check(!CodenameOptionsMenuModel.adjust(work, scroll, 0),
   "numeric setting changed without a left/right input");
  var naughty = row("Gameplay", "Naughtyness");
  check(CodenameOptionsMenuModel.adjust(work, naughty, 1) && work.naughtyness == false,
   "Codename naughtyness preference was not editable");
  var musicVolume = row("Audio", "Music Volume");
  var sfxVolume = row("Audio", "SFX Volume");
  check(CodenameOptionsMenuModel.adjust(work, musicVolume, -1) && work.volumeMusic == 0.9
   && CodenameOptionsMenuModel.adjust(work, sfxVolume, -1) && work.volumeSFX == 0.9,
   "music and SFX group volumes did not use bounded tenth steps");
  var charHealth = row("Appearance", "Color Health Bar");
  check(CodenameOptionsMenuModel.adjust(work, charHealth, -1) && work.useCharColor == false,
   "Codename colorHealthBar did not map to the existing native character-color setting");
  var pixelPerfect = row("Appearance", "Pixel Perfect Effect");
  check(CodenameOptionsMenuModel.adjust(work, pixelPerfect, 1)
   && work.week6PixelPerfect == false && native.week6PixelPerfect == true,
   "week6PixelPerfect did not edit the private settings copy");
  var quality = row("Appearance", "Quality");
  var antialiasing = row("Appearance", "Antialiasing");
  var lowMemory = row("Appearance", "Low Memory Mode");
  var shaders = row("Appearance", "Gameplay Shaders");
  check(CodenameOptionsMenuModel.valueText(work, quality) == "HIGH"
   && !CodenameOptionsMenuModel.adjust(work, antialiasing, 1),
   "HIGH quality did not display or lock its derived advanced settings");
  check(CodenameOptionsMenuModel.adjust(work, quality, -1)
   && work.quality == CodenameOptionsQualityCompat.LOW && !work.antialiasing
   && work.lowMemoryMode && !work.gameplayShaders,
   "LOW quality did not apply Codename's exact option triple");
  check(!CodenameOptionsMenuModel.adjust(work, shaders, 1),
   "LOW quality did not lock its derived shader field");
  check(CodenameOptionsMenuModel.adjust(work, quality, 1)
   && work.quality == CodenameOptionsQualityCompat.HIGH && work.antialiasing
   && !work.lowMemoryMode && work.gameplayShaders,
   "HIGH quality did not restore Codename's exact option triple");
  check(CodenameOptionsMenuModel.adjust(work, quality, 1)
   && work.quality == CodenameOptionsQualityCompat.CUSTOM
   && work.antialiasing && !work.lowMemoryMode && work.gameplayShaders
   && !CodenameOptionsQualityCompat.isLocked(work, "antialiasing"),
   "CUSTOM transition did not preserve values or unlock its advanced fields");
  check(CodenameOptionsMenuModel.adjust(work, antialiasing, -1)
   && !work.antialiasing && native.antialiasing,
   "CUSTOM advanced settings did not edit only the private settings copy");
  var offset = row("Controls & Timing", "Note Offset");
  work.offset = 1.26;
  check(CodenameOptionsMenuModel.valueText(work, offset) == "1.3 ms",
   "note offset display did not round to the nearest tenth");
  work.offset = 0;
  check(CodenameOptionsMenuModel.adjust(work, offset, -1) && work.offset == -0.1,
   "note offset did not preserve negative sub-millisecond adjustment");
  check(CodenameOptionsMenuModel.adjust(work, offset, 1, true) && work.offset == 19.9,
   "Shift offset adjustment did not add exactly 20 ms while preserving the fraction");
  check(CodenameOptionsMenuModel.adjust(work, offset, -1, true) && work.offset == -0.1,
   "Shift offset adjustment did not subtract exactly 20 ms");
  work.offset = 995.1;
  check(CodenameOptionsMenuModel.adjust(work, offset, 1, true) && work.offset == 1000,
   "Shift offset adjustment did not clamp to the upper limit");
  work.offset = -995.1;
  check(CodenameOptionsMenuModel.adjust(work, offset, -1, true) && work.offset == -1000,
   "Shift offset adjustment did not clamp to the lower limit");
  check(CodenameOptionsMenuModel.adjust(work, scroll, -1, true) && work.scrollSpeed == 9.9,
   "Shift offset shortcut changed the increment for another numeric option");
  var fps = row("Graphics & Performance", "FPS Cap");
  check(fps.min == 1 && fps.step == 1 && fps.max == OptionsHandler.MAX_FPS_CAP && fps.integral,
   "FPS option did not expose the full positive integer range");
  check(row("Miscellaneous", "FPS Cap") != null
   && row("Miscellaneous", "Always Show Cutscenes") != null,
   "legacy Miscellaneous alias lost previously exposed rows");
  for (i in 0...500) CodenameOptionsMenuModel.adjust(work, fps, 1);
  check(work.fpsCap == 560 && CodenameOptionsMenuModel.valueText(work, fps) == "560 FPS",
   "FPS option did not step by one above the old 480 cap or show its units");
  check(CodenameOptionsMenuModel.adjust(work, fps, 1, true) && work.fpsCap == 580
   && CodenameOptionsMenuModel.adjust(work, fps, -1, true) && work.fpsCap == 560,
   "Shift FPS adjustment did not step by exactly 20");
  work.fpsCap = OptionsHandler.MAX_FPS_CAP;
  check(!CodenameOptionsMenuModel.adjust(work, fps, 1, true)
   && work.fpsCap == OptionsHandler.MAX_FPS_CAP,
   "FPS cap upper boundary overflowed the native Int range");
  var fastTransitions = row("Interface", "Fast Scene Transitions");
  check(fastTransitions != null && !work.fastSceneTransitions
   && CodenameOptionsMenuModel.adjust(work, fastTransitions, 1)
   && work.fastSceneTransitions && !native.fastSceneTransitions,
   "fast scene transitions did not edit the isolated interface preference");
  check(work.unrelatedSaveField == "preserve" && native.fpsCap == 60,
   "editing supported settings overwrote unrelated or persisted settings");
  check(CodenameOptionsMenuModel.valueText(work, downscroll) == "On",
   "toggle value was not rendered in source-like on/off form");
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "Main", "--interp"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_xml_checkboxes_use_isolated_owner_fields(self):
        helper = (ROOT / "source/CodenameOwnerOptionsCompat.hx").read_text()
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "CodenameOwnerOptionsCompat.hx").write_text(helper, newline='\n')
            (base / "CodenameScriptDiscovery.hx").write_text("""class CodenameScriptDiscovery {
 public static function resolveScopedRelative(root:String, relative:String):String return null;
}
""", newline='\n')
            (base / "CodenamePaths.hx").write_text("""class CodenamePaths {
 public function new(root:String) {}
 public function getFolderContent(path:String, addPath:Bool=false):Array<String> return [];
}
""", newline='\n')
            (base / "FNFAssets.hx").write_text("""class FNFAssets {
 public static function getText(path:String):String return "";
}
""", newline='\n')
            (base / "Main.hx").write_text(r'''class FakeOwnerSave {
 public var values:Map<String,Dynamic> = new Map();
 public var writes:Int=0;
 public function new() {}
 public function getField(name:String):Dynamic return values.get(name);
 public function setField(name:String,value:Dynamic):Dynamic {writes++;values.set(name,value);return value;}
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var parsed=CodenameOwnerOptionsCompat.parse(
   '<menu name="Package Options" desc="Adjust package features">'
   + '<checkbox id="mechanics" name="Enable Mechanics" />'
   + '<checkbox id="modCharts" name="Enable Modcharts" />'
   + '</menu>', 'data/config/options.xml');
  check(parsed.menus.length==1 && parsed.menus[0].name=='Package Options'
   && parsed.menus[0].options.length==2,
   'owner menu or checkbox rows did not parse from Codename XML');
  var mechanics=parsed.menus[0].options[0];
  check(mechanics.id=='mechanics' && mechanics.label=='Enable Mechanics',
   'source option id/label was not retained');
  var ownerA=new FakeOwnerSave(); var ownerB=new FakeOwnerSave();
  ownerA.setField('mechanics',true); ownerB.setField('mechanics',true);
  check(CodenameOwnerOptionsCompat.value(ownerA,mechanics),
   'selected-owner value did not read its private preference');
  check(CodenameOwnerOptionsCompat.toggle(ownerA,mechanics)
   && !CodenameOwnerOptionsCompat.value(ownerA,mechanics)
   && CodenameOwnerOptionsCompat.value(ownerB,mechanics),
   'editing one imported owner changed another owner preference');
  check(!CodenameOwnerOptionsCompat.toggle(ownerA,{kind:'number',id:'unsupported'}),
   'unsupported XML option type was silently treated as a checkbox');
  var unsupported=CodenameOwnerOptionsCompat.parse(
   '<menu name="Extra"><number id="count" name="Count" min="0" max="5" /></menu>',
   'data/config/options/extra.xml');
  check(unsupported.menus.length==0 && unsupported.diagnostics.length==1
   && unsupported.diagnostics[0].indexOf('Unsupported XML option type "number"')>=0,
   'unimplemented XML option type did not produce a concrete diagnostic');
  var reserved=CodenameOwnerOptionsCompat.parse(
   '<menu name="Unsafe"><checkbox id="codenameImportedModData" name="Replace save root" /></menu>',
   'data/config/options/unsafe.xml');
  check(reserved.menus.length==0 && reserved.diagnostics.length==1
   && reserved.diagnostics[0].indexOf('unsupported owner save id')>=0,
   'reserved owner-save field was exposed to an XML checkbox');
  check(!CodenameOwnerOptionsCompat.toggle(ownerA,{kind:'checkbox',id:'__proto__'}),
   'reserved checkbox id could be toggled through the adapter');
 }
}''', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", directory, "-main", "Main", "--interp"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hscript_exit_closure_remains_callable_after_owner_facade_release(self):
        fixture = r'''import hscript.Interp;
import hscript.Parser;
class FlxGFacade {
 public var stateSwitch:Dynamic;
 public var switched:Array<Dynamic>=[];
 public function new() {}
 public function switchState(target:Dynamic):Bool {
  if(stateSwitch!=null) return stateSwitch(target);
  switched.push(target); return true;
 }
 public function release():Void stateSwitch=null;
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var facade=new FlxGFacade();
  facade.stateSwitch=function(target:Dynamic):Bool {facade.switched.push('owner-switch');return true;};
  var interp=new Interp();
  interp.variables.set('FlxG',facade);
  interp.variables.set('PlayState',PlayState);
  interp.execute(new Parser().parseString(
   'function makeExit(){return function(_) {FlxG.switchState(new PlayState());};}'));
  var makeExit:Dynamic=interp.variables.get('makeExit');
  var callback:Dynamic=makeExit();
  facade.release();
  Reflect.callMethod(null,callback,[{}]);
  check(facade.switched.length==1 && Std.isOfType(facade.switched[0],PlayState),
   'a retained source exit closure could not use the released facade fallback');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            base = Path(directory)
            (base / "Main.hx").write_text(fixture, newline='\n')
            (base / "PlayState.hx").write_text("class PlayState { public function new() {} }\n", newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / ".haxelib/hscript/2,5,0"),
                 "-cp", directory, "-main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        facade = (ROOT / "source/CodenameFlxGFacade.hx").read_text()
        self.assertIn("stateSwitch = null;", facade)
        self.assertIn("FlxG.switchState(cast target);", facade)
        self.assertIn("if (onStateSwitchAccepted != null) onStateSwitchAccepted(target);", facade)

    def test_state_commits_only_on_exit_and_preserves_active_owner_route(self):
        adapter = (ROOT / "source/CodenameOptionsMenuCompat.hx").read_text()
        self.assertIn("CodenameOptionsMenuModel.copyOptions(OptionsHandler.options)", adapter)
        self.assertIn("OptionsHandler.options = cast workingOptions;", adapter)
        self.assertIn("if (!optionsDirty || workingOptions == null) return;", adapter)
        self.assertIn("LoadingState.loadAndSwitchState(new MainMenuState());", adapter)
        self.assertNotIn("CodenameModRuntime.clearActiveOwner", adapter)
        self.assertIn("for (oldRow in rowGroup.members)", adapter)
        self.assertIn("oldRow.destroy();", adapter)
        self.assertIn("@:keep public function exit():Void", adapter)
        self.assertIn("new ControlsState(returnState)", adapter)
        self.assertIn("Reflect.callMethod(null, onExitCallback, [this]);", adapter)
        self.assertIn("if (hasExited) return;", adapter)
        self.assertIn("CodenameOwnerOptionsCompat.load(owner)", adapter)
        self.assertIn("CodenameOwnerSaveData(owner)", adapter)
        self.assertIn("CodenameOwnerOptionsCompat.toggle(ownerOptionsSave, option)", adapter)
        self.assertIn("maps and persists quality and ", adapter)
        self.assertIn("pixel-camera effects from imported scripts remain unverified", adapter)
        self.assertIn("engine-wide shader and memory effects remain unverified", adapter)
        self.assertIn("Developer/config surfaces", adapter)
        controls = (ROOT / "source/ControlsState.hx").read_text()
        self.assertIn("public function new(?returnState:FlxState)", controls)
        self.assertIn("returnState == null ? new SaveDataState() : returnState", controls)


if __name__ == "__main__":
    unittest.main()
