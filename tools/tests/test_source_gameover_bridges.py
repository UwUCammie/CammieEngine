"""Execute owner GameOver setting and audio bridges with observable Paths boundaries."""
from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath as Path
import subprocess
import tempfile
import unittest
from test_psych_gameover_class_compat import extract_method

ROOT = Path(__file__).resolve().parents[2]


class SourceGameOverBridgesTest(unittest.TestCase):
    def test_live_names_preserve_dialect_provider_nulls_and_owner_isolation(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = [extract_method(source, marker).replace('@:keep ', '', 1) for marker in (
            'function sourceGameOverSettingKey',
            '@:keep public function sourceGameOverPsychPaths',
            '@:keep public function sourceGameOverSoundPath',
            '@:keep public function sourceGameOverSound(',
            'public function psychGameOverCharacterName',
            'public function psychGameOverDeathDelay',
        )]
        fixture = r'''
import openfl.media.Sound;
class FNFAssets {
 public static var available:Map<String, Bool> = [];
 public static function exists(path:String):Bool return available.exists(path);
 public static function getSound(path:String):Sound return new Sound(path);
}
class PsychOwnerPaths {
 public static var calls:Array<String> = [];
 public static var libraries:Array<String> = [];
 public static function create(root:String, ?library:String):Dynamic {
  libraries.push(root + ':' + library);
  return {
  sound:function(name:String):String { calls.push(root + ':sound:' + name); return root + '/sounds/' + name + '.ogg'; },
  music:function(name:String):String { calls.push(root + ':music:' + name); return root + '/music/' + name + '.ogg'; }
  };
 }
}
class NVPaths {
 public var root:String;
 public var calls:Array<String> = [];
 public function new(root:String) this.root = root;
 public function findFileWithExts(key:String, exts:Array<String>):String {
  calls.push('path:' + key + ':' + exts.join(','));
  return root + '/' + key + '.' + exts[0];
 }
 public function sound(name:String):Sound { calls.push('sound:' + name); return new Sound(root + ':sound:' + name); }
 public function music(name:String):Sound { calls.push('music:' + name); return new Sound(root + ':music:' + name); }
}
class Host {
 public var sourceGameOverSettings:SourceGameOverSettings;
 public var sourceScoreNightmare:Bool;
 public var nightmareVisionPaths:NVPaths;
 var root:String;
 var psychStageLibrary:String = 'shared-stage';
 var psychGameOverOverrides:Map<String, String> = [];
 var psychGameOverDeathDelaySeconds:Float = 0;
 public function new(root:String, nv:Bool) {
  this.root = root;
  sourceScoreNightmare = nv;
  nightmareVisionPaths = new NVPaths(root);
  sourceGameOverSettings = new SourceGameOverSettings(nv ? 2 : 1, {});
 }
 function selectedPsychSkinRoot():String return root;
__METHODS__
}
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var psych = new Host('owner-one', false);
  check(psych.psychGameOverCharacterName() == 'bf-dead', 'source defaults were absent without a class write');
  psych.sourceGameOverSettings.characterName = 'folder/death';
  check(psych.psychGameOverCharacterName() == 'folder/death', 'authored character subfolder was rejected');
  psych.sourceGameOverSettings.deathDelay = -1;
  check(psych.psychGameOverDeathDelay() == -1, 'donor negative delay was normalized');
  psych.sourceGameOverSettings.deathSoundName = '  loss  ';
  var soundPath = 'owner-one/sounds/  loss  .ogg';
  FNFAssets.available.set(soundPath, true);
  check(psych.sourceGameOverSound('deathSoundName', true).label == soundPath, 'sound key was trimmed or wrong provider used');
  check(PsychOwnerPaths.libraries[0] == 'owner-one:shared-stage', 'Psych stage library was lost for game-over assets');
  psych.sourceGameOverSettings.loopSoundName = 'loop';
  FNFAssets.available.set('owner-one/music/loop.ogg', true);
  check(psych.sourceGameOverSound('loopSoundName', false).label == 'owner-one/music/loop.ogg', 'loop used sounds folder');
  psych.sourceGameOverSettings.endSoundName = null;
  check(psych.sourceGameOverSound('endSoundName', false).label == 'flixel/sounds/beep', 'Psych missing/null name did not preserve source beep fallback');
  check(PsychOwnerPaths.calls.indexOf('owner-one:music:null') >= 0, 'Psych null name was skipped as NV policy');
  var nv = new Host('owner-two', true);
  nv.sourceGameOverSettings.deathSoundName = null;
  check(nv.sourceGameOverSound('deathSoundName', true) == null && nv.nightmareVisionPaths.calls.length == 0,
   'NV null initial sound did not skip Paths');
  nv.sourceGameOverSettings.loopSoundName = '';
  check(nv.sourceGameOverSound('loopSoundName', false).label == 'owner-two:music:'
   && nv.nightmareVisionPaths.calls[0] == 'music:', 'NV empty string became a default or native fallback');
  nv.sourceGameOverSettings.deathSoundName = 'loss';
  check(nv.sourceGameOverSoundPath('deathSoundName', true) == 'owner-two/sounds/loss.ogg'
   && nv.nightmareVisionPaths.calls[1] == 'path:sounds/loss:ogg,wav', 'NV extension/provider contract');
  check(nv.psychGameOverDeathDelay() == 0, 'Psych delay leaked into NV');
  var rejectedNVPaths = false;
  try nv.sourceGameOverPsychPaths() catch (_:Dynamic) rejectedNVPaths = true;
  check(rejectedNVPaths, 'Psych asset context accepted an NV owner');
  check(psych.sourceGameOverSettings.loopSoundName == 'loop', 'NV state leaked into Psych owner');
  nv.sourceGameOverSettings = null;
  check(nv.sourceGameOverSound('loopSoundName', false) == null && nv.sourceGameOverSoundPath('loopSoundName', false) == null,
   'disposed source sound route read stale owner data');
 }
}
'''.replace('__METHODS__', '\n'.join(methods))
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='source-gameover-bridges-', dir=TEST_TMP) as folder:
            path = Path(folder)
            (path / 'openfl/media').mkdir(parents=True)
            (path / 'flixel/system').mkdir(parents=True)
            (path / 'openfl/media/Sound.hx').write_text('package openfl.media; class Sound { public var label:String; public function new(label:String) this.label = label; }', newline='\n')
            (path / 'flixel/system/FlxAssets.hx').write_text("package flixel.system; class FlxAssets { public static function getSound(key:String):openfl.media.Sound return new openfl.media.Sound(key); }", newline='\n')
            (path / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(path), '-main', 'Main', '--interp'],
                                    cwd=ROOT, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
