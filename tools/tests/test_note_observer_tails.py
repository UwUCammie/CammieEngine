"""Shared hit and miss tails: observer order, GF reaction, combo and vocal muting."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_miss_lifecycle import extract_method


ROOT = Path(__file__).resolve().parents[2]

MARKERS = (
    "function notifyNoteHitObservers(",
    "function notifyNoteSingObservers(",
    "function notifyNoteMissObservers(",
    "function dispatchNightmareVisionNoteMiss(",
    "function markNightmareVisionTailMissed(",
    "function reactGirlfriendToComboBreak(",
    "function registerComboHit(",
    "function muteMissedVocals(",
)

HOST = r'''
class Piece { public var alive:Bool = true; public var tooLate:Bool = false; public function new() {} }
class Tail { public var missed:Bool = false; public var notes:Array<Piece> = []; public function new() {} }
class Note {
 public var y:Float = 0;
 public var noteHit:String = null;
 public var noteStrum:String = null;
 public var noteType:String = 'Default';
 public var nightmareVisionTailState:Tail = null;
 public function new() {}
}
class Actor { public var y:Float = 100; public function new() {} }
class Character {
 public var name:String;
 public var log:Array<String>;
 public var animations:Array<String> = ['sad'];
 public var specialAnim:Bool = false;
 public function new(n, l) {name = n; log = l;}
 public function hasAnimation(n:String):Bool return animations.indexOf(n) >= 0;
 public function playAnim(n:String, force:Bool = false):Void log.push(name + ':' + n + ':' + force);
 public function playAnimForDuration(n:String, d:Float, force:Bool = false):Void log.push(name + ':' + n + ':for' + d);
}
class Tracks {
 public var roles:Array<String>;
 public var log:Array<String>;
 public function new(r, l) {roles = r; log = l;}
 public function setRoleVolume(role:String, volume:Float, fallbackShared:Bool = false):Bool {
  var selected = role;
  if (roles.indexOf(selected) < 0 && fallbackShared && roles.indexOf('shared') >= 0) selected = 'shared';
  if (roles.indexOf(selected) < 0) return false;
  log.push('role:' + selected + ':' + volume);
  return true;
 }
}
class Voice { public var volume:Float = 1; public function new() {} }
class NightmareVisionScriptGroup { public static inline var STOP_FUNC:String = 'stop'; }
class NightmareVisionNoteTypeRuntime { public static function noteTypeOf(n:Note):String return n.noteType; }
class NoteTypes {
 public var log:Array<String>; public var result:String = 'go';
 public function new(l) log = l;
 public function noteMiss(n:Note, id:Int):String {log.push('type-miss:' + id); return result;}
}
class Scripts {
 public var log:Array<String>;
 public function new(l) log = l;
 public function call(name:String, args:Array<Dynamic>, ignore:Bool, filter:Array<String>):Dynamic {
  log.push('nv:' + name + ':' + args[1] + ':' + filter[0]); return null;
 }
}
class PlayState {
 public var log:Array<String> = [];
 public var downscroll:Bool = false;
 public var actor:Actor = new Actor();
 public var gf:Character;
 public var combo:Int = 0;
 public var performanceMaxCombo:Int = 0;
 public var vocalTracks:Tracks = null;
 public var vocals:Voice = null;
 public var nightmareVisionNoteTypes:NoteTypes;
 public var nightmareVisionScripts:Scripts;
 public function new() {gf = new Character('gf', log); nightmareVisionNoteTypes = new NoteTypes(log); nightmareVisionScripts = new Scripts(log);}
 function callAllHScript(name:String, args:Array<Dynamic>, ?skipHxc:Bool = false, ?returnValues:Array<Dynamic>,
  ?hxcArgs:Array<Dynamic>, ?skipPsych:Bool = false, ?skipLua:Bool = false):Void
  log.push('all:' + name + ':' + args.length + ':' + skipHxc + ':' + skipPsych + ':' + skipLua);
 function callHscript(name:String, args:Array<Dynamic>, family:String):Bool {log.push('one:' + name); return true;}
 function callCutsceneOpponentSing():Void log.push('cutscene');
 function getHaxeActor(id:String):Dynamic return actor;
 function setAllHaxeVar(name:String, value:Dynamic):Void log.push('global:' + name + '=' + value);
 function setVocalsVolume(volume:Float):Void log.push('all-vocals:' + volume);
 __METHODS__
}
'''


class NoteObserverTailsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def run_haxe(self, body: str) -> None:
        methods = "\n".join(
            extract_method(self.play, marker).replace(marker, "public " + marker, 1) for marker in MARKERS
        )
        with tempfile.TemporaryDirectory(prefix="note-observer-tails-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "PlayState.hx").write_text(HOST.replace("__METHODS__", methods), encoding="utf-8", newline="\n")
            (scratch / "Main.hx").write_text(
                "import PlayState;\nclass Main {\n static function check(v:Bool, m:String):Void if (!v) throw m;\n"
                + body + "\n}\n", encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "--main", "Main", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hit_observers_keep_order_and_fire_hooks_once(self):
        self.run_haxe(r'''
 static function main():Void {
  var host = new PlayState();
  var note = new Note(); note.noteHit = 'hitHook'; note.noteStrum = 'strumHook'; note.y = 50;
  host.notifyNoteHitObservers(note, true, true, null, true, false, false);
  check(host.log.join('|') == 'all:noteHit:4:true:true:false|all:goodNoteHit:2:true:true:false|one:hitHook|one:strumHook',
   'Psych-style player hit order: ' + host.log.join('|'));
  check(note.noteStrum == null, 'the strum hook is cleared after firing');
  host.log.resize(0);
  host.notifyNoteHitObservers(note, true, true, null, true, false, false);
  check(host.log.indexOf('one:strumHook') < 0, 'a cleared strum hook does not fire twice');

  var opponent = new PlayState();
  var other = new Note(); other.y = 150;
  other.noteStrum = 'late';
  opponent.notifyNoteHitObservers(other, false, false, null, false, true, true);
  check(opponent.log.join('|') == 'all:noteHit:4:true:false:true|all:opponentNoteHit:2:true:false:true|all:playerTwoSing:0:false:false:false|cutscene',
   'opponent hit with sing hooks: ' + opponent.log.join('|'));
  check(other.noteStrum == 'late', 'a note still below the receptor keeps its strum hook');

  var player = new PlayState();
  player.notifyNoteSingObservers(true);
  check(player.log.join('|') == 'all:playerOneSing:0:false:false:false', 'player sing hook skips the cutscene release');
 }
''')

    def test_miss_tail_marks_hold_and_dispatches_once(self):
        self.run_haxe(r'''
 static function main():Void {
  var host = new PlayState();
  var note = new Note(); note.noteType = 'Hurt';
  note.nightmareVisionTailState = new Tail();
  var live = new Piece(), dead = new Piece(); dead.alive = false;
  note.nightmareVisionTailState.notes = [live, null, dead];
  host.markNightmareVisionTailMissed(note, true);
  check(note.nightmareVisionTailState.missed && live.tooLate && !dead.tooLate, 'live-only marking skips dead pieces');
  host.markNightmareVisionTailMissed(note, false);
  check(dead.tooLate, 'full marking reaches every piece');
  host.markNightmareVisionTailMissed(new Note(), true);

  host.dispatchNightmareVisionNoteMiss(note, 2);
  check(host.log.join('|') == 'type-miss:2|nv:noteMiss:2:Hurt', 'note type then script hook: ' + host.log.join('|'));
  host.log.resize(0);
  host.nightmareVisionNoteTypes.result = NightmareVisionScriptGroup.STOP_FUNC;
  host.dispatchNightmareVisionNoteMiss(note, 0);
  check(host.log.join('|') == 'type-miss:0', 'a stopping note type keeps the script hook quiet');
  host.nightmareVisionNoteTypes = null;
  host.dispatchNightmareVisionNoteMiss(note, 0);

  host.log.resize(0);
  host.notifyNoteMissObservers(note, false, 1, null, true);
  check(host.log.join('|') == 'all:noteMiss:4:true:true:false|all:opponentNoteMiss:1:true:true:false',
   'opponent miss hooks: ' + host.log.join('|'));
  host.log.resize(0);
  host.notifyNoteMissObservers(null, true, 1, null, false);
  check(host.log.join('|') == 'all:noteMiss:4:true:false:false', 'player miss sends only the generic hook');
 }
''')

    def test_gf_reaction_combo_and_vocal_mute_rules(self):
        self.run_haxe(r'''
 static function main():Void {
  var host = new PlayState();
  host.reactGirlfriendToComboBreak(5, null, false);
  check(host.log.length == 0, 'a combo of five is not worth a reaction');
  host.reactGirlfriendToComboBreak(6, host.gf, false);
  check(host.log.length == 0, 'GF does not react to her own miss');
  host.reactGirlfriendToComboBreak(6, null, false);
  check(host.log.join('|') == 'gf:sad:true' && host.gf.specialAnim, 'Psych holds the pose as a special animation');
  host.log.resize(0); host.gf.specialAnim = false;
  host.reactGirlfriendToComboBreak(9, null, true);
  check(host.log.join('|') == 'gf:sad:for1' && !host.gf.specialAnim, 'Nightmare Vision plays it for a second');
  host.log.resize(0); host.gf.animations = [];
  host.reactGirlfriendToComboBreak(9, null, true);
  host.gf = null;
  host.reactGirlfriendToComboBreak(9, null, false);
  check(host.log.length == 0, 'no sad animation or no GF means no reaction');

  var counter = new PlayState();
  counter.combo = 9998;
  counter.registerComboHit();
  counter.registerComboHit(false);
  check(counter.combo == 9999 && counter.performanceMaxCombo == 9999, 'the combo caps at 9999');
  check(counter.log.join('|') == 'global:combo=9999', 'only a publishing hit updates the script global');

  var split = new PlayState(); split.vocalTracks = new Tracks(['player', 'opponent'], split.log);
  split.muteMissedVocals(true);
  split.muteMissedVocals(false);
  check(split.log.join('|') == 'role:player:0|role:opponent:0', 'split stems mute only the side that missed');
  var combined = new PlayState(); combined.vocalTracks = new Tracks(['shared'], combined.log);
  combined.muteMissedVocals(true);
  check(combined.log.join('|') == 'role:shared:0', 'one combined track still goes quiet');
  var odd = new PlayState(); odd.vocalTracks = new Tracks(['extra'], odd.log);
  odd.muteMissedVocals(true);
  check(odd.log.join('|') == 'all-vocals:0', 'stems with no matching side fall back to muting everything');
  var single = new PlayState();
  single.muteMissedVocals(true);
  check(single.log.join('|') == 'all-vocals:0', 'songs without stem tracks use the old mute');
 }
''')

    def test_hit_and_miss_routes_share_the_tails(self):
        play = self.play
        good = extract_method(play, "function goodNoteHit(")
        finish = extract_method(play, "function finishGoodNoteHit(")
        external = extract_method(play, "function finishNightmareVisionExternalHit(")
        sing = extract_method(play, "function notifyNoteSingObservers(")
        observers = extract_method(play, "function notifyNoteHitObservers(")
        for body in (good, finish, external):
            self.assertNotIn("playerOneSing", body)
            self.assertNotIn("note.noteStrum", body)
        self.assertEqual(sing.count("'playerOneSing'"), 1)
        self.assertIn("notifyNoteSingObservers(playerOne);", good)
        self.assertIn("notifyNoteHitObservers(note, playerOne, goodhit, hxcHitEvent, psychSource, false, false);", finish)
        self.assertIn("notifyNoteHitObservers(note, observerPlayer, note.wasGoodHit, hxcEvent, false,", external)
        self.assertIn("if (singHooks) notifyNoteSingObservers(playerOne);", observers)
        source_miss = extract_method(play, "function sourceNoteMiss(")
        core = extract_method(play, "function noteMissCore(")
        self.assertIn("notifyNoteMissObservers(note, playerOne, direction, hxcMissEvent, true);", source_miss)
        self.assertIn("notifyNoteMissObservers(note, playerOne, direction, hxcMissEvent, false);", core)
        for body in (source_miss, core):
            self.assertNotIn("nightmareVisionTailState.missed = true", body)
            self.assertNotIn("nightmareVisionNoteTypes.noteMiss(", body)
        self.assertIn("reactGirlfriendToComboBreak(previousCombo, sourceMissPerformer(note, actingOn), false);", source_miss)
        self.assertIn("reactGirlfriendToComboBreak(combo, null, true);", source_miss)
        self.assertNotIn("combo = Std.int(Math.min(9999, combo + 1))",
                         play.replace(extract_method(play, "function registerComboHit("), ""))
        self.assertIn("muteMissedVocals(daNote.mustPress);", play)
        legacy_miss = (ROOT / "source/NightmareVisionLegacyMissFlow.hx").read_text(encoding="utf-8")
        legacy_hit = (ROOT / "source/NightmareVisionLegacyHitFlow.hx").read_text(encoding="utf-8")
        for direct in ("state.songScore +=", "state.totalPlayed +=", "PlayState.misses +="):
            self.assertNotIn(direct, legacy_miss)
        self.assertEqual(legacy_miss.count("state.applySourceMiss("), 2)
        self.assertIn("state.registerComboHit();", legacy_hit)
        self.assertIn("state.applySourceHitHealth(note, true, true);", legacy_hit)
        self.assertNotIn("state.health", legacy_hit)
        self.assertNotIn("state.health", legacy_miss)
        self.assertNotIn("state.doDeathCheck", legacy_miss)


if __name__ == "__main__":
    unittest.main()
