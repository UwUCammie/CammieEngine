"""Turn hooks fire once per section and Image Flash overlays cover any zoom.

Both were regressions found while porting modcharts: playerOneTurn/playerTwoTurn
were dispatched every frame (Hedgehog Stew piled camera zoom until the view was
unusable) and the Image Flash overlay was screen-sized, so it only covered the
screen at zoom == 1 (2k22's white flash vanished while defaultCamZoom was < 1).
"""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / '.tools/haxe/haxe'
SOURCE = ROOT / 'source/PlayState.hx'


def turn_dispatch_block(source):
    start = source.index('if (curSection != lastTurnSection)')
    end = source.index('if (!PlayState.SONG.notes[curSection].mustHitSection)', start)
    # Imported split stems and the compatibility Voices track now share this
    # centralized volume helper; the old direct FlxSound write was retired.
    end = source.index('\n', source.index('setVocalsVolume(1);', end)) + 1
    return source[start:end]


def fit_helper(source):
    start = source.index('function fitEventImageCover()')
    end = source.index('\n\t}\n', start) + len('\n\t}\n')
    return source[start:end].replace('function fitEventImageCover', 'public function fitEventImageCover')


class TurnHookDispatchTest(unittest.TestCase):
    def test_hooks_fire_once_per_section(self):
        block = turn_dispatch_block(SOURCE.read_text())
        fixture = 'class Note {\n\tpublic var mustHitSection:Bool;\n\tpublic function new(m:Bool) this.mustHitSection = m;\n}\n' + '''
class Song {
\tpublic var notes:Array<Note>;
\tpublic function new(notes:Array<Note>) this.notes = notes;
}
class PlayState {
\tpublic static var SONG:Song;
}
class RuntimeSmokeHarness {
\tpublic static function enabled():Bool return false;
}
class Vocals {
\tpublic var volume:Float = 0;
\tpublic function new() {}
}
class Probe {
\tpublic var curSection:Int = 0;
\tpublic var lastTurnSection:Int = -1;
\tpublic var smokeFirstBfFocusCaptured:Bool = false;
\tpublic var calls:Array<String> = [];
\tpublic var vocals:Vocals = new Vocals();
\tpublic function new() {}
\tinline function callAllHScript(name:String, args:Array<Dynamic>) calls.push(name);
\tinline function setVocalsVolume(value:Float) vocals.volume = value;
\tinline function runtimeSmokeCameraSnapshot(phase:String) {}
\tpublic function tick() {
''' + block + '''
\t}
\tstatic function main() {
\t\tvar sections = [false, false, true, true, true, false];
\t\tPlayState.SONG = new Song([for (m in sections) new Note(m)]);
\t\tvar p = new Probe();
\t\t// sit on each section for a few frames, then move on
\t\tfor (i in 0...sections.length) {
\t\t\tp.curSection = i;
\t\t\tp.tick(); p.tick(); p.tick();
\t\t}
\t\tvar expected = [for (m in sections) m ? "playerOneTurn" : "playerTwoTurn"];
\t\tif (p.calls.length != expected.length)
\t\t\tthrow 'expected one call per section, got ' + p.calls.length + ' (' + p.calls.join(",") + ')';
\t\tfor (i in 0...expected.length)
\t\t\tif (p.calls[i] != expected[i])
\t\t\t\tthrow 'section ' + i + ': expected ' + expected[i] + ' got ' + p.calls[i];
\t\t// staying on a section must not re-fire
\t\tp.tick(); p.tick();
\t\tif (p.calls.length != expected.length) throw 're-fired without a section change';
\t}
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Probe.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '--main', 'Probe', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class ImageFlashCoverTest(unittest.TestCase):
    def test_overlay_scales_with_camera_zoom(self):
        helper = fit_helper(SOURCE.read_text())
        fixture = '''
class Graphic {
\tpublic var width:Float;
\tpublic var height:Float;
\tpublic function new(w:Float, h:Float) { width = w; height = h; }
}
class Point {
\tpublic var x:Float = 0;
\tpublic var y:Float = 0;
\tpublic function new() {}
\tpublic function set(x:Float, y:Float) { this.x = x; this.y = y; return this; }
}
class Sprite {
\tpublic var graphic:Graphic;
\tpublic var scale:Point = new Point();
\tpublic var x:Float = 0;
\tpublic var y:Float = 0;
\tpublic var width:Float = 0;
\tpublic var height:Float = 0;
\tpublic function new(w:Float, h:Float) graphic = new Graphic(w, h);
\tpublic function updateHitbox() { width = graphic.width * scale.x; height = graphic.height * scale.y; }
\tpublic function screenCenter() { x = (FlxG.width - width) / 2; y = (FlxG.height - height) / 2; }
}
class Cam {
\tpublic var zoom:Float = 1;
\tpublic function new() {}
}
class FlxG {
\tpublic static var camera:Cam = new Cam();
\tpublic static var width:Int = 1280;
\tpublic static var height:Int = 720;
}
class Probe {
\tpublic var eventImageSprite:Sprite;
\tpublic var camHUD:Cam = new Cam();
\tpublic function new(w:Float, h:Float) eventImageSprite = new Sprite(w, h);
''' + helper + '''
}
class Test {
\tstatic function main() {
\t\t// zoomed out: a plain screen-sized overlay only covered zoom == 1
\t\tvar p = new Probe(8, 8);
\t\tFlxG.camera.zoom = 0.5;
\t\tp.camHUD.zoom = 1;
\t\tp.fitEventImageCover();
\t\tif (p.eventImageSprite.width < FlxG.width / 0.5) throw 'flash not wide enough at zoom 0.5';
\t\tif (p.eventImageSprite.height < FlxG.height / 0.5) throw 'flash not tall enough at zoom 0.5';
\t\t// zoomed in: HUD is the limiting camera, still must cover it
\t\tFlxG.camera.zoom = 1.5;
\t\tp.fitEventImageCover();
\t\tif (p.eventImageSprite.width < FlxG.width) throw 'flash lost coverage when zoomed in';
\t\t// centred on screen
\t\tif (p.eventImageSprite.x > 0 || p.eventImageSprite.y > 0) throw 'flash not centred';
\t\tif (p.eventImageSprite.x + p.eventImageSprite.width < FlxG.width) throw 'flash off the right edge';
\t}
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'Test.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', tmp, '--main', 'Test', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CutsceneCleanupTest(unittest.TestCase):
    def test_cutscene_sprites_removed_at_countdown(self):
        source = SOURCE.read_text()
        start = source.index('public function startCountdown():Void {')
        end = source.index('enemyStrums.transIn();', start)
        block = source[start:end]
        self.assertIn('for (spr in cutsceneSprites)', block)
        self.assertIn("hscriptStates.remove('cutscene')", block)
        self.assertIn('if (usehaxe == \'cutscene\'', source)


class AtlasCacheLifecycleTest(unittest.TestCase):
    def test_cache_holds_a_reference_on_the_graphic(self):
        dynamic = (ROOT / 'source/DynamicSprite.hx').read_text()
        # a cached sheet must survive switchCharacter destroying its sprite
        self.assertIn('incrementUseCount()', dynamic)
        self.assertIn('decrementUseCount()', dynamic)
        self.assertIn('isDestroyed', dynamic)
        self.assertIn('ATLAS_CACHE_MAX', dynamic)

    def test_character_json_goes_through_the_cache(self):
        paths = (ROOT / 'source/Paths.hx').read_text()
        self.assertIn('DynamicAtlasFrames.fromTexturePackerJson(pngPath, jsonPath)', paths)

    def test_swap_targets_preloaded_at_load(self):
        source = SOURCE.read_text()
        self.assertIn('preloadSwapCharacters();', source)
        start = source.index('function preloadSwapCharacters()')
        # switchToChar is public because stage/HXC adapters use the native swap
        # path.  Keep the extraction tolerant of the old private spelling so this
        # regression test remains about the preload body, not visibility syntax.
        end = source.find('\tpublic function switchToChar(', start)
        if end < 0:
            end = source.index('\tfunction switchToChar(', start)
        body = source[start:end]
        self.assertIn("'Change Character'", body)
        self.assertIn('preload.txt', body)


class TerribleFateCharacterSwapTest(unittest.TestCase):
    def test_drowned_swaps_resolve_and_blank_slot_targets_player(self):
        import json
        registry_fixture = ROOT / 'assets/images/custom_chars/custom_chars.jsonc'
        base_fixture = ROOT / 'assets/images/custom_chars/bendrowned/char.png'
        chart_fixture = ROOT / 'assets/data/terrible-fate/events.json'
        if not registry_fixture.is_file() or not base_fixture.is_file() or not chart_fixture.is_file():
            self.skipTest(f'mounted Terrible Fate character/event fixtures unavailable: {registry_fixture}, {base_fixture}, {chart_fixture}')
        registry = json.loads(registry_fixture.read_text())
        for name in ('bfdrowned', 'drowned'):
            self.assertEqual(registry[name]['like'], 'bendrowned')
            self.assertEqual(registry[name]['icons'], 'bendrowned')
        self.assertTrue((ROOT / 'assets/images/custom_chars/bendrowned/char.png').is_file())
        self.assertTrue((ROOT / 'assets/images/custom_chars/bendrowned/char.xml').is_file())
        self.assertTrue((ROOT / 'assets/images/custom_chars/bendrowned.hscript').is_file())

        source = SOURCE.read_text()
        start = source.index("case 'Change Character':")
        end = source.index("case 'Hey!':", start)
        self.assertIn("case '' | '0' | 'bf' | 'boyfriend': 'bf';", source[start:end])

        events = json.loads(chart_fixture.read_text())
        rows = [row for section in events['song']['notes'] for row in section['sectionNotes']]
        swaps = {(row[3], row[4]) for row in rows if len(row) >= 5 and row[2] == 'Change Character'}
        self.assertIn(('', 'bfdrowned'), swaps)
        self.assertIn(('1', 'drowned'), swaps)


if __name__ == '__main__':
    unittest.main()
