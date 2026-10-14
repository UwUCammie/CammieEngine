"""Psych 0.7 HScript reaches PlayState members through `game` that this engine
keeps elsewhere: triggerEvent, the character groups, Flixel 5's camera
setFilters, and the mod's own rating and combo images.
"""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
ROOT = Path(__file__).resolve().parents[2]


def source(name):
    return (ROOT / 'source' / name).read_text(encoding='utf-8').replace('\r\n', '\n')


class PsychHscriptGameSurfaceTest(unittest.TestCase):
    def test_game_trigger_event_fires_the_chart_event(self):
        play = source('PlayState.hx')
        # Psych's fourth argument is a strum time, so it must not become value 3.
        self.assertIn('@:keep public function triggerEvent(eventName:String, value1:Dynamic, value2:Dynamic, ?strumTime:Dynamic):Void\n\t\ttriggerEventNote(eventName, value1, value2);', play)

    def test_game_character_groups_are_live_views_for_psych_scripts(self):
        play = source('PlayState.hx')
        start = play.index("interp.variables.set('variables', psychScriptVariables);")
        block = play[start:start + 1600]
        # Plain Psych HScript evaluates through the bridge's interpreter.
        self.assertIn('Std.isOfType(interp, SourceIrisBridge)\n\t\t\t\t? (cast interp:SourceIrisBridge).evaluator', block)
        for name, role in (('boyfriendGroup', 'bf'), ('dadGroup', 'dad'), ('gfGroup', 'gf')):
            self.assertIn("sourceInterp.bindLiveValue('%s', function() return characterGroupForRole('%s')," % (name, role), block)
        # Nightmare Vision's real groups still win inside characterGroupForRole.
        self.assertIn("var nightmare:Dynamic = key == 'dad' ? dadGroup : key == 'gf' ? gfGroup : boyfriendGroup;\n\t\tif (nightmare != null) return nightmare;", play)

    def test_group_anchor_before_the_stage_is_built(self):
        group = source('PsychBaseStageActorGroupCompat.hx')
        self.assertIn("var early = Reflect.field(stageHost, 'earlyStageAnchor');\n\t\t\tif (Reflect.isFunction(early)) info = Reflect.callMethod(stageHost, early, [role]);", group)
        play = source('PlayState.hx')
        self.assertIn('@:keep public function earlyStageAnchor(role:String):Dynamic {\n\t\tif (curStage != null) return curStage.getInfo(role);', play)
        self.assertIn("var point = meta == null ? null : key == 'bf' ? meta.boyfriend : key == 'dad' ? meta.opponent : meta.girlfriend;", play)

    def test_early_anchor_reads_the_stage_file_points(self):
        # The same parse the anchor uses: Psych stage files name the roles
        # boyfriend, opponent and girlfriend.
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            (Path(temp) / 'Main.hx').write_text(r"""
class Main {
	static function check(ok:Bool, m:String) { if (!ok) throw m; }
	static function main() {
		var meta = SourceStageMetadata.parse(haxe.Json.parse('{"boyfriend":[1270,100],"girlfriend":[400,130],"opponent":[310,85]}'));
		check(meta.opponent[0] == 310 && meta.opponent[1] == 85, 'opponent anchor');
		check(meta.boyfriend[0] == 1270 && meta.girlfriend[1] == 130, 'other anchors');
	}
}""", encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_raw_camera_set_filters(self):
        interp = source('NightmareVisionScriptInterp.hx')
        # Same effect as the camera view's helper: filters set, enabled when present.
        self.assertIn("if (field == 'setFilters' && isFlixelCamera(object) && Reflect.field(object, field) == null) {\n\t\t\tvar filters:Dynamic = args.length > 0 ? args[0] : null;\n\t\t\tReflect.setProperty(object, 'filters', filters);\n\t\t\tReflect.setProperty(object, 'filtersEnabled', filters != null);", interp)
        camera = source('PsychFlxCameraCompat.hx')
        self.assertIn('public function setFilters(value:Array<BitmapFilter>):Void {\n\t\tnativeCamera.filters = value;\n\t\tnativeCamera.filtersEnabled = value != null;', camera)

    def test_camera_detection_walks_the_class_chain_by_name(self):
        # Headless tools build the interpreter without Flixel, so the check must
        # not name the Flixel type; a camera subclass still counts.
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            folder = Path(temp)
            (folder / 'flixel').mkdir()
            (folder / 'flixel' / 'FlxCamera.hx').write_text('package flixel;\nclass FlxCamera { public function new() {} }\n', encoding='utf-8')
            (folder / 'Main.hx').write_text(r"""
class GameCamera extends flixel.FlxCamera {}
class Main {
	static function check(ok:Bool, m:String) { if (!ok) throw m; }
	static function main() {
		var method = Reflect.field(NightmareVisionScriptInterp, 'isFlixelCamera');
		inline function camera(value:Dynamic):Bool return Reflect.callMethod(NightmareVisionScriptInterp, method, [value]);
		check(camera(new flixel.FlxCamera()) && camera(new GameCamera()), 'camera not recognised');
		check(!camera(null) && !camera({filters: []}) && !camera('camOther'), 'non-camera accepted');
	}
}""", encoding='utf-8')
            source_text = (ROOT / 'source' / 'NightmareVisionScriptInterp.hx').read_text(encoding='utf-8')
            start = source_text.index('\tstatic function isFlixelCamera(object:Dynamic):Bool {')
            end = source_text.index('\n\t}\n', start) + 4
            (folder / 'NightmareVisionScriptInterp.hx').write_text('class NightmareVisionScriptInterp {\n' + source_text[start:end].replace('\r\n', '\n') + '}\n', encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', temp, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_psych_owner_rating_and_combo_images(self):
        play = source('PlayState.hx')
        self.assertIn("Reflect.callMethod(paths, Reflect.field(paths, '__sourceOwnedPath'), ['images/' + image + '.png']);", play)
        self.assertIn("var owned = psychOwnerPopupImage('num' + numeral);\n\t\tif (owned != null) return owned;", play)
        self.assertIn('var ownerRatingImage = psychOwnerPopupImage(daRating);\n\t\tif (ownerRatingImage != null) {', play)
        # Pixel art lives in Psych's pixelUI folder, and Nightmare Vision HUDs draw their own.
        self.assertIn("if (nightmareVisionScripts != null || name == null || name == '') return null;", play)
        self.assertIn("var image = pixelUI ? 'pixelUI/' + name + '-pixel' : name;", play)


if __name__ == '__main__':
    unittest.main()
