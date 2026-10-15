"""A custom V-Slice SongEvent can read its own kind through `id`.

SongEvent stores the name given to its constructor in `id`; custom events
scan the chart with `data.eventKind != id`. The adapter left `id` unbound, so
those callbacks threw EUnknownVariable(id).
"""
import json
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path

ROOT = Path(__file__).resolve().parents[2]

DONOR = r'''import funkin.play.event.SongEvent;
import funkin.play.PlayState;

class SwapSongEvent extends SongEvent {
    var seen:Int = 0;
    public function new() { super("Swap", {processOldEvents: true}); }
    override public function onSongLoaded(event) {
        for (data in PlayState.instance.currentChart.events)
            if (data != null && data.eventKind == id) seen++;
    }
}
'''

OWN_FIELD = r'''import funkin.play.event.SongEvent;

class LabelSongEvent extends SongEvent {
    var id:String = "custom-label";
    public function new() { super("Label"); }
    override public function onSongLoaded(event) { trace(id); }
}
'''

ROUTED = r'''import funkin.play.event.SongEvent;

class PlayAnimationSongEvent extends SongEvent {
    public function new() { super("PlayAnimation"); }
    override public function onSongLoaded(event) { trace(id); }
}
'''

MAIN = '''class Main {
  static function fail(value:String):Void throw value;
  static function main() {
    var generated = HxcCompat.analyze(%s, "scripts/events/Swap.hxc").generatedHscript;
    var declared = generated.indexOf('var id = "Swap";');
    if (declared < 0) fail("event kind not bound to id: " + generated);
    var used = generated.indexOf("== id");
    if (used < 0 || used < declared) fail("id is not declared before the callback reads it: " + generated);
    var own = HxcCompat.analyze(%s, "scripts/events/Label.hxc").generatedHscript;
    var ours = own.indexOf('var id = "Label";');
    var theirs = own.indexOf("custom-label");
    if (ours >= 0 && theirs >= 0 && ours > theirs) fail("the donor's own id field was overridden: " + own);
    var routed = HxcCompat.analyze(%s, "scripts/events/PlayAnimation.hxc");
    if (routed.customEventKind != null && routed.customEventKind != "") fail("fixture should route to a native event");
    if (routed.generatedHscript.indexOf('var id = "PlayAnimation";') < 0)
      fail("a natively routed event lost its id: " + routed.generatedHscript);
    Sys.println("event-id-ok");
  }
}
'''


class HxcSongEventIdTest(unittest.TestCase):
    def test_custom_song_event_binds_its_kind_as_id(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            (Path(folder) / 'Main.hx').write_text(MAIN % (json.dumps(DONOR), json.dumps(OWN_FIELD), json.dumps(ROUTED)), newline=chr(10))
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', folder,
                '-main', 'Main', '--interp'], cwd=ROOT, capture_output=True, text=True, timeout=600)
        self.assertEqual(result.returncode, 0, result.stdout[-3000:] + result.stderr[-3000:])
        self.assertIn('event-id-ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
