"""Psych tagged sounds: one sound per tag, replacement, fades, stop and onSoundFinished."""
from haxe_test_support import HAXE_COMMAND

from pathlib import Path
from haxe_test_support import FixturePath as Path
import re
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    match = re.search(r"^\t(?:override |public |static |private )*function " + re.escape(name) + r"\(", source, re.M)
    if match is None:
        raise AssertionError(name)
    start = match.start()
    brace = source.index("{", start)
    depth = 0
    for pos in range(brace, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError(name)


FIXTURE_HEAD = r'''class Sound { public function new() {} }
class FlxSound {
 public var exists=true;
 public var stops=0;
 public var plays=0;
 public var volume:Float=1;
 public var looped=false;
 public var source:Dynamic;
 public var fadeDuration:Float=-1;
 public var fadeTarget:Float=-1;
 public var onComplete:Void->Void;
 public function new() {}
 public function fadeOut(duration:Float,to:Float):FlxSound {
  fadeDuration=duration;fadeTarget=to;return this;
 }
 public function fadeIn(duration:Float,from:Float,to:Float):FlxSound {
  fadeDuration=duration;fadeTarget=to;return this;
 }
 public function play():FlxSound {plays++;return this;}
 // an autoDestroy sound goes back to the pool when it is stopped
 public function stop():Void {stops++;exists=false;onComplete=null;}
 // what the audio backend does when playback reaches the end
 public function reachEnd():Void {
  if(onComplete!=null) onComplete();
  if(!looped) {exists=false;onComplete=null;}
 }
}
class SoundFrontEnd {
 public var music:FlxSound=new FlxSound();
 public var loads:Array<FlxSound>=[];
 public var autoDestroyLoads=0;
 public function new() {}
 public function load(embedded:Dynamic,volume:Float,looped:Bool,group:Dynamic,autoDestroy:Bool):FlxSound {
  var sound=new FlxSound();
  sound.source=embedded;sound.volume=volume;sound.looped=looped;
  if(autoDestroy) autoDestroyLoads++;
  loads.push(sound);
  return sound;
 }
}
class FlxG { public static var sound:SoundFrontEnd=new SoundFrontEnd(); }
class Main {
 var taggedSounds:TaggedSoundRegistry<FlxSound>=new TaggedSoundRegistry<FlxSound>(
  function(sound:FlxSound):Bool return sound.exists,
  function(sound:FlxSound):Void sound.stop());
 static var pooledPlays:Array<Dynamic>=[];
 static var decoded:Map<String,Sound>=new Map();
 static var hscriptSoundCache:Map<String,Sound>=new Map();
 var finished:Array<String>=[];
 function new() {}
 function compatSoundPath(path:String,preferSounds:Bool):String return 'owner/'+path;
 static function resolveHscriptSoundPath(path:String):String
  return path.indexOf('missing')>=0 ? null : path+'.ogg';
 static function preloadHscriptSound(path:String):Bool {
  if(!hscriptSoundCache.exists(path)) hscriptSoundCache.set(path,new Sound());
  return true;
 }
 static function hscriptSafePlay(path:Dynamic,volume:Float,looped:Bool):FlxSound {
  pooledPlays.push(path);
  return new FlxSound();
 }
 function callAllHScript(name:String,args:Array<Dynamic>):Void finished.push(name+':'+args.join(','));
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
'''

FIXTURE_MAIN = r'''
 static function main():Void {
  var first=new Main();
  var sound=first.compatPlaySound('rumble',0.5,'rumb');
  check(sound!=null && first.compatTaggedSound('rumb')==sound,'tag lost');
  check(sound.plays==1 && sound.volume==0.5 && FlxG.sound.autoDestroyLoads==1,
   'a tagged sound should be loaded as its own self-releasing sound and started');
  check(pooledPlays.length==0,'a tagged play went through the shared per-file sound');
  first.compatSoundFadeOut('rumb',4,0.25);
  check(sound.fadeDuration==4 && sound.fadeTarget==0.25,'fade out lost');
  first.compatSoundFadeIn('rumb',2,0.2,0.8);
  check(sound.fadeDuration==2 && sound.fadeTarget==0.8,'fade in lost');
  var second=new Main();
  check(second.compatTaggedSound('rumb')==null,'tag leaked between songs');

  // two tags on one file must not share a sound
  var other=first.compatPlaySound('rumble',1,'other');
  check(other!=sound,'two tags on the same file got one sound object');
  check(other.source==sound.source,'the same file was decoded twice');
  first.compatStopSound('other');
  check(other.stops==1 && sound.stops==0 && first.compatTaggedSound('rumb')==sound,
   'stopping one tag reached the other tag on the same file');

  // playing a tag again replaces what it had
  var replacement=first.compatPlaySound('thud',1,'rumb');
  check(replacement!=sound && sound.stops==1 && first.compatTaggedSound('rumb')==replacement,
   'replaying a tag left the previous sound running');
  check(first.finished.length==0,'a replaced sound reported that it finished');

  // reaching the end tells scripts once and frees the tag
  replacement.reachEnd();
  check(first.finished.join('|')=='onSoundFinished:rumb','completion callback: '+first.finished.join('|'));
  check(first.compatTaggedSound('rumb')==null,'a finished one-shot kept its tag');

  // a looping sound reports each pass and keeps its tag
  var loop=first.compatPlaySound('hum',1,'hum',true);
  check(loop.looped,'the loop argument was dropped');
  loop.reachEnd();
  loop.reachEnd();
  check(first.finished.length==3 && first.compatTaggedSound('hum')==loop,
   'a looping sound lost its tag or its completion callback');
  first.compatStopSound('hum');
  check(loop.stops==1 && first.compatTaggedSound('hum')==null,'stop failed');

  // untagged plays stay on the shared per-file sound, with its repeat guard
  first.compatPlaySound('plain',1,true);
  first.compatPlaySound('plain',1);
  first.compatPlaySound('plain',1,'  ');
  check(pooledPlays.length==3 && first.compatTaggedSound('plain')==null,
   'untagged plays should use the shared sound and never become a tag');

  var embedded=new Sound();
  var embeddedPlayback=first.compatPlaySound(embedded,0.5,'embedded');
  check(embeddedPlayback.source==embedded && first.compatTaggedSound('embedded')==embeddedPlayback,
   'decoded sound identity/tag lost through string coercion');
  check(first.compatPlaySound('missing',1,'gone')==null && first.compatTaggedSound('gone')==null,
   'a missing file registered a tag');

  // an empty tag means the music for stop and fades, as it does for pause
  var music=FlxG.sound.music;
  first.compatSoundFadeOut(null,3,0.1);
  check(music.fadeDuration==3 && music.fadeTarget==0.1,'an empty tag should fade the music out');
  first.compatSoundFadeIn('',1,0,0.6);
  check(music.fadeDuration==1 && music.fadeTarget==0.6,'an empty tag should fade the music in');
  check(first.soundForTag('')==null && first.soundForTag('',true)==music,
   'the empty tag rule should be the caller\'s choice');
  first.compatStopSound(null);
  check(music.stops==1,'an empty tag should stop the music');
 }
}'''


class PsychTaggedSoundTest(unittest.TestCase):
    def test_bindings_route_through_the_base_tagged_sound_functions(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        for name, binding in (("soundFadeOut", "compatSoundFadeOut"), ("soundFadeIn", "compatSoundFadeIn"),
                              ("stopSound", "compatStopSound")):
            self.assertIn("interp.variables.set('" + name + "', " + binding + ");", source)
        self.assertIn("interp.variables.set('playSound', function(path:Dynamic", source)
        self.assertIn("compatPlaySoundForOwner(psychScriptOwner, path, volume, tag, looped)", source)
        self.assertIn("taggedSounds.clear();", method(source, "destroy"))
        self.assertIn("playTaggedSound(", method(source, "compatPlaySound"))
        self.assertNotIn("hscriptSafePlay", method(source, "compatPlaySound"))
        bindings = (ROOT / "source/PsychSourceBindings.hx").read_text()
        self.assertIn("return host.soundForTag(tag, emptyMeansMusic);", bindings)
        for helper in ("soundAction", "soundNumber", "setSoundNumber"):
            self.assertNotIn("FlxG.sound.music", method(bindings, helper),
                             helper + " should not carry its own tag-or-music rule")

    def test_each_tag_owns_its_sound_and_reports_completion(self):
        source = (ROOT / "source/PlayState.hx").read_text()
        methods = "\n".join(method(source, name).replace("public function", "function") for name in (
            "newTaggedSound", "playTaggedSound", "soundForTag", "stopTaggedSound",
            "compatPlaySound", "compatSoundFinished", "compatTaggedSound", "compatSoundFadeOut",
            "compatSoundFadeIn", "compatStopSound"))
        fixture = FIXTURE_HEAD + methods + FIXTURE_MAIN
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture, newline='\n')
            (Path(work) / "TaggedSoundRegistry.hx").write_text(
                (ROOT / "source/TaggedSoundRegistry.hx").read_text(), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", work,
                                     "--run", "Main"], cwd=ROOT, capture_output=True,
                                    text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
