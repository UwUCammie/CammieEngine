"""Decoded Psych sounds retain identity across host playback and precache."""
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_tagged_sound import method

ROOT = Path(__file__).resolve().parents[2]


class PsychOwnerAudioBridgeTest(unittest.TestCase):
    def test_decoded_sound_music_and_precache_avoid_path_coercion(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(source, name) for name in (
            'compatPlaySoundForOwner', 'compatPlayMusicForOwner', 'compatPlayMusic',
            'compatPrecacheSoundForOwner', 'compatPrecacheMusicForOwner'))
        fixture = r'''using StringTools;
class Sound { public function new() {} }
class FlxSound { public function new() {} }
class FNFAssets {
 public static function exists(path:String):Bool throw 'decoded sound coerced into filesystem lookup';
 public static function getSound(path:String):Sound throw 'unexpected repeat decode';
}
class MusicDriver {
 public var played:Dynamic;
 public var looped:Bool;
 public var volume:Float;
 public function new() {}
 public function playMusic(sound:Dynamic,volume:Float,looped:Bool):Void {
  played=sound;this.volume=volume;this.looped=looped;
 }
}
class FlxG { public static var sound=new MusicDriver(); }
class Main {
 var decoded=new Sound();
 var latest:Dynamic;
 var fallbackCalls=0;
 function new() {}
 function compatPsychOwnerFallbackAllowed(owner:String,path:String):Bool return path!='blocked';
 function compatPsychAssetKey(path:String,ext:String):String return path;
 function compatPsychPathCall(owner:String,method:String,args:Array<Dynamic>):Dynamic return decoded;
 function compatPsychNativeSoundPath(path:String,prefer:Bool):String {fallbackCalls++;return null;}
 function compatSoundPath(path:Dynamic):String {fallbackCalls++;return null;}
 function compatPlaySound(path:Dynamic,volume:Float,tag:Dynamic,looped:Bool):FlxSound {
  latest=path;return new FlxSound();
 }
 function compatPrecacheSound(path:String):Void {}
 function compatPrecacheMusic(path:String):Void {}
''' + methods + r'''
 static function main():Void {
  var host=new Main();
  host.compatPrecacheSoundForOwner('owner','tone');
  host.compatPrecacheMusicForOwner('owner','theme');
  if(host.compatPlaySoundForOwner('owner','tone',0.7,'tag',true)==null
    ||host.latest!=host.decoded) throw 'owner Sound identity not preserved';
  host.compatPlayMusicForOwner('owner','theme',0.4,true);
  if(FlxG.sound.played!=host.decoded || FlxG.sound.volume!=0.4 ||!FlxG.sound.looped)
   throw 'owner music playback lost identity/parameters';
  if(host.fallbackCalls!=0) throw 'decoded owner audio fell through to native lookup';
  if(host.compatPlaySoundForOwner('owner','blocked')!=null) throw 'owner guard ignored';
  var supplied=new Sound();
  host.compatPlaySoundForOwner('owner',supplied,1,null,false);
  if(host.latest!=supplied) throw 'explicit Sound coerced';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            (Path(folder) / 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
