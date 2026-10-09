"""Opt-in scene evidence also captures cutscenes with an empty highway."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_runtime_note_render_readback import extract_method
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class SmokeSceneReadbackTest(unittest.TestCase):
    def test_empty_scene_requires_explicit_opt_in_and_respects_capture_time(self):
        source = (ROOT / 'source/RuntimeSmokeHarness.hx').read_text()
        marker = 'static function onNoteRenderReadbackRendered('
        start = source.index(marker)
        opening = source.index('{', start)
        depth, end = 1, opening + 1
        while depth:
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        method = source[start:end].replace('lime.graphics.RenderContext', 'Dynamic')
        method += '\n' + extract_method(source, 'static function noteRenderCandidate(')
        fixture = r'''
class FlxG { public static var state:Dynamic; }
class Conductor { public static var songPosition:Float = 62000; }
class PlayState {
 public var startedCountdown = true;
 public var notes = {members:new Array<Note>()};
 public function new() {}
}
class Note {
 public var exists = true; public var visible = true; public var active = true;
 public var alpha:Float = 1; public var isSustainNote = false;
 public var frames:Dynamic = {}; public function new() {}
 public function isOnScreen():Bool return true;
}
class Main {
 static var finished = false; static var playStateReady = true;
 static var songStartObserved = true; static var introRenderHeldAt:Float = -1;
 static var visitsStarted = 1;
 static var introRenderReadbackVisits:Map<Int,Bool> = new Map();
 static var noteRenderReadbackVisits:Map<Int,Bool> = new Map();
 static var settings = {sceneRenderReadback:false, noteRenderAfterMs:62000.0};
 static var captured:Array<Note> = [];
 static function config() return settings;
 static function nowMs():Float return 0;
 static function captureIntroRenderReadback(state:PlayState, visit:Int):Void throw 'unexpected intro';
 static function captureNoteRenderReadback(note:Note, visit:Int):Void captured.push(note);
''' + method + r'''
 static function main() {
  var state = new PlayState(); FlxG.state = state;
  onNoteRenderReadbackRendered(null);
  if (captured.length != 0) throw 'ordinary note evidence accepted empty highway';
  settings.sceneRenderReadback = true; Conductor.songPosition = 61999;
  onNoteRenderReadbackRendered(null);
  if (captured.length != 0) throw 'scene captured before requested time';
  Conductor.songPosition = 62000;
  onNoteRenderReadbackRendered(null);
  if (captured.length != 1 || captured[0] != null) throw 'empty scene was not captured';
  settings.sceneRenderReadback = false;
  var note = new Note(); state.notes.members.push(note);
  onNoteRenderReadbackRendered(null);
  if (captured.length != 2 || captured[1] != note) throw 'ordinary note evidence changed';
  finished = true; settings.sceneRenderReadback = true;
  onNoteRenderReadbackRendered(null);
  if (captured.length != 2) throw 'finished run captured again';
 }
}
'''
        with tempfile.TemporaryDirectory(dir=TEST_TMP, prefix='scene-readback-') as folder:
            work = FixturePath(folder)
            (work / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
