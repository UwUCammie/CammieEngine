"""Verify Nightmare Vision note alpha survives renderer snapshots and misses."""
from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
FLIXEL = ROOT / ".haxelib/flixel/6,1,2"


FIXTURE = r'''
import nightmarevision.modchart.NightmareVisionModifierRegistry;
import nightmarevision.modchart.NightmareVisionModchartContext;
import nightmarevision.modchart.NightmareVisionModchartTransform;
import nightmarevision.modchart.NightmareVisionModchartRenderer;

class Main {
  static function fail(message:String):Void throw message;
  static function check(value:Bool, message:String):Void if (!value) fail(message);
  static function near(actual:Float, expected:Float, message:String):Void
    if (Math.isNaN(actual) || Math.abs(actual - expected) > 0.0001)
      fail(message + ': expected ' + expected + ', got ' + actual);

  static function sprite(?alphaMod:Float):Dynamic {
    var value:Dynamic = {
      x:0.0, y:0.0, width:50.0, height:100.0, frameWidth:50.0, frameHeight:100.0,
      scale:{x:1.0, y:1.0}, active:true, noteData:0, strumTime:900.0,
      multSpeed:1.0, isSustainNote:false, wasGoodHit:false
    };
    if (alphaMod != null) Reflect.setField(value, 'alphaMod', alphaMod);
    return value;
  }

  static function main():Void {
    var context = new NightmareVisionModchartContext(800, 600, 4, 112, 0, 0, 1, 500, false, false);
    var registry = new NightmareVisionModifierRegistry(4, 2, false);
    var renderer = new NightmareVisionModchartRenderer(new NightmareVisionModchartTransform(registry));

    for (initial in [0.3, 0.09]) {
      var note = sprite(initial);
      renderer.configureNote(note);
      for (_ in 0...5) {
        var visual = renderer.updateNote(context, note, 0, 0, 0, 0, 0, 0);
        near(visual.alphaMod, initial, 'note snapshot lost source alphaMod');
        near(note.alphaMod, initial, 'render update changed the source-owned alphaMod');
      }
    }

    var nativeNote = sprite();
    renderer.configureNote(nativeNote);
    for (_ in 0...3) {
      near(renderer.updateNote(context, nativeNote, 0, 0, 0, 0, 0, 0).alphaMod, 1,
        'native note without source alphaMod should use 1');
      check(!Reflect.hasField(nativeNote, 'alphaMod'),
        'renderer should not add a source alpha field to native notes');
    }

    var receptor = sprite(0.2);
    renderer.configureReceptor(receptor);
    near(renderer.updateReceptor(context, receptor, 0).alphaMod, 1,
      'receptor should keep default alphaMod regardless of a similarly named field');
    var splash = sprite(0.1);
    renderer.configureSplash(splash);
    near(renderer.updateSplash(context, splash, 'noteSplash', 0, 0).alphaMod, 1,
      'splash should keep default alphaMod regardless of a similarly named field');

    // The modifier result belongs to the snapshot/visual state, not back on the
    // source note. Repeated frames must never compound a computed result into
    // the persistent miss fade.
    var activeRegistry = new NightmareVisionModifierRegistry(4);
    activeRegistry.setSubmodValue('stealth', 'alpha', 0.4, 0);
    var activeRenderer = new NightmareVisionModchartRenderer(
      new NightmareVisionModchartTransform(activeRegistry));
    for (initial in [0.3, 0.09]) {
      var faded = sprite(initial);
      activeRenderer.configureNote(faded);
      var expectedVisualAlpha = (1 - 0.4);
      for (_ in 0...5) {
        var result = activeRenderer.updateNote(context, faded, 0, 0, 0, 0, 0, 0);
        near(result.alphaMod, expectedVisualAlpha, 'active stealth result was not retained in visual state');
        near(faded.alphaMod, initial, 'active modifier wrote computed alpha back to source note');
      }
    }
  }
}
'''


class SourceMissAlphaTest(unittest.TestCase):
    def test_note_exports_writable_source_alpha_and_renderer_preserves_it(self):
        note_source = (ROOT / "source/Note.hx").read_text(encoding="utf-8")
        self.assertIn("@:keep public var alphaMod:Float = 1;", note_source)

        if not FLIXEL.is_dir():
            self.skipTest("pinned Flixel 6.1.2 sources are unavailable")
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(FLIXEL),
                 "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
