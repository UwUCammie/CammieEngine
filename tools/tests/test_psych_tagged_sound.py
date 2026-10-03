"""Psych tagged sounds keep fade/stop targets within one PlayState."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    start = source.index("\tfunction " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError(name)


class PsychTaggedSoundTest(unittest.TestCase):
    def test_tagged_playback_fade_stop_and_song_isolation(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        for binding in ("compatSoundFadeOut", "compatSoundFadeIn", "compatStopSound"):
            self.assertIn("interp.variables.set('" + {
                "compatSoundFadeOut": "soundFadeOut",
                "compatSoundFadeIn": "soundFadeIn", "compatStopSound": "stopSound",
            }[binding] + "', " + binding + ");", source)
        self.assertIn("interp.variables.set('playSound', function(path:Dynamic", source)
        self.assertIn("compatPlaySoundForOwner(psychScriptOwner, path, volume, tag, looped)", source)
        self.assertIn("psychTaggedSounds.clear();", source)
        methods = "\n".join(method(source, name) for name in (
            "compatPlaySound", "compatTaggedSound", "compatSoundFadeOut",
            "compatSoundFadeIn", "compatStopSound"))
        fixture = r'''class FlxSound {
 public var exists=true;
 public var stopped=false;
 public var fadeDuration:Float=-1;
 public var fadeTarget:Float=-1;
 public function new() {}
 public function fadeOut(duration:Float,to:Float):FlxSound {
  fadeDuration=duration;fadeTarget=to;return this;
 }
 public function fadeIn(duration:Float,from:Float,to:Float):FlxSound {
  fadeDuration=duration;fadeTarget=to;return this;
 }
 public function stop():Void stopped=true;
}
class Main {
 var psychTaggedSounds:Map<String,FlxSound>=new Map();
 static var latest:FlxSound;
 function new() {}
 function compatSoundPath(path:String,preferSounds:Bool):String return 'owner/'+path;
 static function hscriptSafePlay(path:String,volume:Float,looped:Bool):FlxSound {
  latest=new FlxSound();return latest;
 }
''' + methods + r'''
 static function main():Void {
  var first=new Main();
  var sound=first.compatPlaySound('rumble',1,'rumb');
  if(sound==null || first.compatTaggedSound('rumb')!=sound) throw 'tag lost';
  first.compatSoundFadeOut('rumb',4,0.25);
  if(sound.fadeDuration!=4 || sound.fadeTarget!=0.25) throw 'fade out lost';
  first.compatSoundFadeIn('rumb',2,0.2,0.8);
  if(sound.fadeDuration!=2 || sound.fadeTarget!=0.8) throw 'fade in lost';
  var second=new Main();
  if(second.compatTaggedSound('rumb')!=null) throw 'tag leaked between songs';
  first.compatStopSound('rumb');
  if(!sound.stopped || first.compatTaggedSound('rumb')!=null) throw 'stop failed';
  first.compatPlaySound('plain',1,true);
  if(first.compatTaggedSound('plain')!=null) throw 'legacy loop flag became a tag';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", work,
                                     "--run", "Main"], cwd=ROOT, capture_output=True,
                                    text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
