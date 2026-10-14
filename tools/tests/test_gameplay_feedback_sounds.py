"""Hit and miss sounds: one route for every family, owner files first, cached per song."""

from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath
from test_source_miss_lifecycle import extract_method


ROOT = Path(__file__).resolve().parents[2]


HOST = r'''
class Note {
 public var isSustainNote:Bool = false;
 public var hitsoundDisabled:Bool = false;
 public var hitsound:String = 'hitsound';
 public var hitsoundForce:Bool = false;
 public var ownVolume:Float = 1;
 public var preference:Float = 0;
 // Mirrors Note.hitsoundVolume: the source preference, else the forced own volume.
 public var hitsoundVolume(get, never):Float;
 function get_hitsoundVolume():Float return Note_sourceHitsoundVolume(preference, hitsoundForce, ownVolume);
 static function Note_sourceHitsoundVolume(preference:Float, force:Bool, own:Float):Float {
  if (preference > 0) return preference;
  return force ? own : 0.0;
 }
 public function new() {}
}
class Sound { public var path:String; public function new(p) path=p; }
class Options { public var hitSounds:Bool = false; public function new() {} }
class OptionsHandler { public static var options:Options = new Options(); }
class TitleState { public static var soundExt:String = '.ogg'; }
class FakeSound {
 public var plays:Array<String> = [];
 public function new() {}
 public function play(sound:Sound, volume:Float):Void plays.push(sound.path + '@' + volume);
}
class FakeRandom {
 public var next:Int = 2;
 public var calls:Array<String> = [];
 public function new() {}
 public function int(min:Int, max:Int):Int {calls.push('int'); return next;}
 public function float(min:Float, max:Float):Float {calls.push('float'); return min;}
}
class FlxG {
 public static var sound:FakeSound = new FakeSound();
 public static var random:FakeRandom = new FakeRandom();
}
class FNFAssets {
 public static var decodes:Array<String> = [];
 public static function precacheSound(path:String):Sound {decodes.push(path); return new Sound(path);}
}
class PlayState {
 public var owned:Map<String, String> = [];
 public var ownerThrows:Bool = false;
 public var hitSoundResolved:Bool = false;
 public var hitSoundAsset:Sound = null;
 public function new() {}
 function feedbackOwnerSoundPath(name:String):Null<String> {
  if (ownerThrows) throw 'owner lookup failed';
  return owned.get(name);
 }
 __METHODS__
}
'''


class GameplayFeedbackSoundsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.play = (ROOT / "source/PlayState.hx").read_text(encoding="utf-8")

    def run_haxe(self, body: str, host: bool = False) -> None:
        files = {}
        if host:
            methods = "\n".join(
                extract_method(self.play, marker).replace(marker, "public " + marker, 1)
                for marker in ("function playNoteHitSound(", "function playMissSound(", "function feedbackSound(")
            ) + "\n var feedbackSounds:Map<String, Sound> = new Map();"
            files["PlayState.hx"] = HOST.replace("__METHODS__", methods)
        files["Main.hx"] = ("import PlayState;\n" if host else "") + \
            "class Main {\n static function check(v:Bool, m:String):Void if (!v) throw m;\n" + body + "\n}\n"
        with tempfile.TemporaryDirectory(prefix="feedback-sounds-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            for name, text in files.items():
                (scratch / name).write_text(text, encoding="utf-8", newline="\n")
            (scratch / "GameplayFeedbackSounds.hx").write_text(
                (ROOT / "source/GameplayFeedbackSounds.hx").read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(scratch), "--main", "Main", "--interp"],
                cwd=ROOT, env={**os.environ, "TMPDIR": str(ROOT / "tmp")},
                capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_owner_file_wins_and_engine_file_is_the_fallback(self):
        self.run_haxe(r'''
 static function main():Void {
  var owner = function(name:String):Null<String> return name == 'missnote2' ? 'mods/a/sounds/missnote2.ogg' : null;
  check(GameplayFeedbackSounds.resolve('missnote2', owner, 'assets/sounds/missnote2.ogg') == 'mods/a/sounds/missnote2.ogg',
   'an owner copy of the sound is used');
  check(GameplayFeedbackSounds.resolve('missnote1', owner, 'assets/sounds/missnote1.ogg') == 'assets/sounds/missnote1.ogg',
   'a sound the owner does not ship falls back to the engine file');
  check(GameplayFeedbackSounds.resolve('hitsound', null, 'native') == 'native', 'no owner means the engine file');
  var broken = function(name:String):Null<String> throw 'unavailable';
  check(GameplayFeedbackSounds.resolve('hitsound', broken, 'native') == 'native', 'a failing owner lookup falls back');
  check(GameplayFeedbackSounds.nativePath('hitsound', '.ogg') == 'assets/sounds/hitSound.ogg',
   'the engine hit sound keeps its own spelling');
  check(GameplayFeedbackSounds.nativePath('cancelMenu', '.ogg') == 'assets/sounds/cancelMenu.ogg',
   'other names map into the engine sounds folder');
  check(GameplayFeedbackSounds.missName(1) == 'missnote1' && GameplayFeedbackSounds.missName(3) == 'missnote3',
   'miss sounds are numbered');
  check(GameplayFeedbackSounds.missName(4) == 'missnote4', 'a number past the stock three still names its file');
  for (bad in [null, '', '  ', '../secret', 'a/../../b', '/abs', 'C:/x', 'a//b'])
   check(GameplayFeedbackSounds.safeName(bad, 'hitsound') == 'hitsound', 'unsafe name refused: ' + bad);
  check(GameplayFeedbackSounds.safeName(' extra/click ', 'hitsound') == 'extra/click', 'plain sub folders are kept');
 }
''')

    def test_hit_volume_follows_the_source_preference_then_the_engine_switch(self):
        self.run_haxe(r'''
 static function main():Void {
  check(GameplayFeedbackSounds.hitVolume(0.4, false) == 0.4, 'a source volume plays as set');
  check(GameplayFeedbackSounds.hitVolume(0.4, true) == 0.4, 'the source volume wins over the engine switch');
  check(GameplayFeedbackSounds.hitVolume(0, true) == 1, 'the engine switch alone plays at full volume');
  check(GameplayFeedbackSounds.hitVolume(0, false) == 0, 'nothing turned on stays silent');
  check(GameplayFeedbackSounds.hitVolume(Math.NaN, false) == 0, 'a broken volume stays silent');
 }
''')

    def test_shared_hit_route_plays_the_note_sound_once_decoded(self):
        self.run_haxe(r'''
 static function main():Void {
  var host = new PlayState();
  var note = new Note();
  host.playNoteHitSound(note);
  check(FlxG.sound.plays.length == 0, 'no preference, no force and the switch off plays nothing');

  note.preference = 0.5;
  host.playNoteHitSound(note);
  check(FlxG.sound.plays.join(',') == 'assets/sounds/hitSound.ogg@0.5', 'the source preference sets the volume');

  var sustain = new Note(); sustain.preference = 1; sustain.isSustainNote = true;
  host.playNoteHitSound(sustain);
  var disabled = new Note(); disabled.preference = 1; disabled.hitsoundDisabled = true;
  host.playNoteHitSound(disabled);
  check(FlxG.sound.plays.length == 1, 'sustain pieces and disabled notes stay quiet');

  var forced = new Note(); forced.hitsoundForce = true; forced.ownVolume = 0.3; forced.hitsound = 'cancelMenu';
  host.owned.set('cancelMenu', 'mods/a/sounds/cancelMenu.ogg');
  host.playNoteHitSound(forced);
  check(FlxG.sound.plays[1] == 'mods/a/sounds/cancelMenu.ogg@0.3',
   'a forced note plays its own sound from the owner at its own volume');

  OptionsHandler.options.hitSounds = true;
  host.playNoteHitSound(new Note());
  check(FlxG.sound.plays[2] == 'assets/sounds/hitSound.ogg@1', 'the engine switch plays the hit at full volume');
  OptionsHandler.options.hitSounds = false;

  var traversal = new Note(); traversal.preference = 1; traversal.hitsound = '../../secret';
  host.playNoteHitSound(traversal);
  check(FlxG.sound.plays[3] == 'assets/sounds/hitSound.ogg@1', 'a path escaping the sounds folder falls back to the hit sound');
  check(FNFAssets.decodes.join(',') == 'assets/sounds/hitSound.ogg,mods/a/sounds/cancelMenu.ogg',
   'each sound is decoded once per song: ' + FNFAssets.decodes.join(','));

  var preloaded = new PlayState();
  preloaded.hitSoundResolved = true;
  preloaded.hitSoundAsset = new Sound('preloaded');
  var plain = new Note(); plain.preference = 1;
  preloaded.playNoteHitSound(plain);
  check(FlxG.sound.plays[4] == 'preloaded@1' && FNFAssets.decodes.length == 2,
   'the hit sound preloaded with the song is reused');
 }
''', host=True)

    def test_shared_miss_route_keeps_random_order_and_owner_files(self):
        self.run_haxe(r'''
 static function main():Void {
  var host = new PlayState();
  host.owned.set('missnote2', 'mods/a/sounds/missnote2.ogg');
  host.playMissSound();
  FlxG.random.next = 1;
  host.playMissSound();
  host.ownerThrows = true;
  FlxG.random.next = 3;
  host.playMissSound();
  check(FlxG.random.calls.join(',') == 'int,float,int,float,int,float', 'random pick then random volume, every time');
  check(FlxG.sound.plays.join(',') == 'mods/a/sounds/missnote2.ogg@0.1,assets/sounds/missnote1.ogg@0.1,assets/sounds/missnote3.ogg@0.1',
   'owner miss sound first, engine file otherwise: ' + FlxG.sound.plays.join(','));
 }
''', host=True)

    def test_every_family_uses_the_shared_routes(self):
        play = self.play
        self.assertNotIn("FlxG.sound.play('assets/sounds/missnote'", play)
        self.assertNotIn("soundRandom('missnote'", play)
        self.assertNotIn("playHitSound();", play)
        self.assertNotIn("nightmareVisionPaths.sound('hitsound')", play)
        good = extract_method(play, "function goodNoteHit(")
        self.assertIn("if (psychHitSound && playerOne) playNoteHitSound(note);", good)
        self.assertLess(good.index("if (psychHitSound && playerOne) playNoteHitSound(note);"),
                        good.index("dispatchHitCausesMiss(note, playerOne)"),
                        "Psych plays the hit sound before a hazard turns into a miss")
        self.assertIn("if (!psychHitSound) playNoteHitSound(note);", good)
        self.assertIn("if (field.playerControls) playNoteHitSound(note);",
                      extract_method(play, "function handleNightmareVisionFieldHit("))
        self.assertIn("playNoteHitSound(note);", extract_method(play, "function playNightmareVisionLegacyHitSound("))
        self.assertIn("playMissSound();", extract_method(play, "function playHistoricalNightmareMissSound("))
        self.assertEqual(extract_method(play, "function sourceNoteMiss(").count("playMissSound();"), 2)
        self.assertIn("this.playMissSound();", extract_method(play, "function noteMissCore("))
        owner = extract_method(play, "function feedbackOwnerSoundPath(")
        self.assertIn("nightmareVisionPaths.findFileWithExts('sounds/' + name, ['ogg', 'wav'])", owner)
        self.assertIn("PsychOwnerPaths.create(owner, psychStageLibrary)", owner)


if __name__ == "__main__":
    unittest.main()
