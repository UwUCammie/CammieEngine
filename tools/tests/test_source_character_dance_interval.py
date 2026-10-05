"""Execute reflected source cadence and the real automatic beat gate."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


class SourceCharacterDanceIntervalTest(unittest.TestCase):
    def test_nv_character_reflective_beat_callback_matches_pinned_character_bopper(self):
        character = (ROOT / 'source/Character.hx').read_text(encoding='utf-8')
        callback = method(character, '@:keep public function onBeatHit(')
        donor = ROOT.parent / 'fnf_sources/NightmareVision/source/funkin/objects'
        donor_character = (donor / 'Character.hx').read_text(encoding='utf-8')
        donor_bopper = (donor / 'Bopper.hx').read_text(encoding='utf-8')
        donor_callback = method(donor_character, 'override function onBeatHit(').replace('override function', 'override public function', 1)
        donor_base = method(donor_bopper, 'public function onBeatHit(')
        fixture = '''using StringTools;
class Bopper {
 public var danceEveryNumBeats:Int=2;
 public var name:String='idle';
 public var dances:Int=0;
 public function new() {}
 public function isAnimNull():Bool return name==null;
 public function dance():Void dances++;
 @@DONOR_BASE@@
}
class DonorCharacter extends Bopper {
 public var stunned:Bool=false;public var holding:Bool=false;
 public function new() {super();}
 public function getAnimName():String return name;
 @@DONOR_CALLBACK@@
}
class Character {
 public var sourceDanceNightmare:Bool=true;
 public var nightmareVisionCharacterData:Dynamic=null;
 public var codenameLiveDefinition:Dynamic=null;
 public var characterDestroyed:Bool=false;
 public var animation:Dynamic={};
 public var stunned:Bool=false;public var holding:Bool=false;
 public var debugMode:Bool=false;public var specialAnim:Bool=false;
 public var danceEveryNumBeats:Int=2;
 public var name:String='idle';public var dances:Int=0;
 public function new() {}
 public function getAnimName():String return name;
 public function dance():Void dances++;
 @@CALLBACK@@
}
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function invoke(actor:Character,beat:Int):Void {
  var fn=Reflect.field(actor,'onBeatHit');
  check(fn!=null,'NV Character callback retained for reflective scripts');
  Reflect.callMethod(actor,fn,[beat]);
 }
 static function main():Void {
  for(interval in [1,2,3,4]) for(beat in -4...13)
   for(name in ['idle','danceLeft','singLEFT','singUP-hold','hey'])
    for(stunned in [false,true]) for(holding in [false,true]) {
     var actor=new Character();actor.danceEveryNumBeats=interval;
     actor.name=name;actor.stunned=stunned;actor.holding=holding;
     var donor=new DonorCharacter();donor.danceEveryNumBeats=interval;
     donor.name=name;donor.stunned=stunned;donor.holding=holding;
     invoke(actor,beat);donor.onBeatHit(beat);
     check(actor.dances==donor.dances,'callback differs from pinned Character/Bopper cadence');
    }
  var actor=new Character();actor.danceEveryNumBeats=3;
  invoke(actor,2);check(actor.dances==0,'off-cadence stage actor danced');
  invoke(actor,3);check(actor.dances==1,'stage actor did not dance on cadence');
  for(interval in [0,-1]) {actor.danceEveryNumBeats=interval;invoke(actor,0);}
  check(actor.dances==1,'nonpositive source cadence safety changed');
  actor.danceEveryNumBeats=1;actor.name=null;invoke(actor,1);
  actor.name='idle';actor.specialAnim=true;invoke(actor,1);
  actor.specialAnim=false;actor.debugMode=true;invoke(actor,1);
  actor.debugMode=false;actor.characterDestroyed=true;invoke(actor,1);
  actor.characterDestroyed=false;actor.animation=null;invoke(actor,1);
  check(actor.dances==1,'invalid/special/debug/destroyed actor danced');
  actor.animation={};actor.sourceDanceNightmare=false;invoke(actor,1);
  check(actor.dances==1,'native/Psych cadence changed by NV callback');
  actor.nightmareVisionCharacterData={};invoke(actor,1);
  check(actor.dances==2,'loaded NV actor must accept callback');
  actor.codenameLiveDefinition={};invoke(actor,1);
  check(actor.dances==2,'Codename-owned actor reached NV beat callback');
 }
}'''.replace('@@CALLBACK@@', callback).replace('@@DONOR_CALLBACK@@', donor_callback).replace('@@DONOR_BASE@@', donor_base)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '-dce', 'full', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_source_defaults_pair_changes_and_live_reflected_interval(self):
        character = (ROOT / 'source/Character.hx').read_text(encoding='utf-8')
        play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        methods = '\n'.join(method(character, marker) for marker in (
            '@:keep public function recalculateDanceIdle()',
        ))
        getters = character[character.index('\tfunction get_danceEveryNumBeats()'):
                            character.index('\t@:keep public var danceIdle:')]
        gate = method(play, 'function characterDanceDue(')
        self.assertIn("Reflect.field(definition, 'dance_every'), 2", character)
        self.assertIn('if (sourceDanceNightmare && nightmareVisionCharacterData == null)', character)
        fixture = '''class Animations {
 public var names:Array<String> = [];
 public function new() {}
 public function exists(name:String):Bool return names.indexOf(name) >= 0;
}
class Character {
 public var danceEvery:Int = 1;
 public var danceEveryNumBeats(get,set):Int;
 public var danceIdle:Bool = false;
 public var idleSuffix:String = '';
 public var sourceDanceNightmare:Bool = false;
 public var settingSourceDanceUp:Bool = true;
 public var codenameLiveDefinition:Dynamic = null;
 public var animation:Animations = new Animations();
 public function new() {}
 @@GETTERS@@
 @@METHODS@@
}
class Main {
 @@GATE@@
 public function new() {}
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  var host = new Main();
  var psych = new Character();
  psych.recalculateDanceIdle();
  check(psych.danceEveryNumBeats == 2, 'Psych idle default');
  psych.animation.names = ['danceLeft', 'danceRight'];
  psych.recalculateDanceIdle();
  check(psych.danceIdle && psych.danceEveryNumBeats == 1, 'Psych changed pair cadence');
  psych.danceEveryNumBeats = 4;
  check(psych.danceEvery == 4 && !host.characterDanceDue(psych, 2)
   && host.characterDanceDue(psych, 4), 'live script cadence did not reach beat gate');
  psych.idleSuffix = '-alt';
  psych.recalculateDanceIdle();
  check(!psych.danceIdle && psych.danceEveryNumBeats == 8, 'Psych changed idle cadence');
  var pair = new Character();
  pair.animation.names = ['danceLeft', 'danceRight'];
  pair.recalculateDanceIdle();
  check(pair.danceEveryNumBeats == 1, 'Psych initial pair default');
  var nv = new Character();
  nv.sourceDanceNightmare = true;
  nv.danceEveryNumBeats = 3;
  nv.animation.names = ['danceLeft', 'danceRight'];
  nv.recalculateDanceIdle();
  check(nv.danceIdle && nv.danceEveryNumBeats == 3, 'NV JSON cadence changed for pair');
  nv.animation.names = [];
  nv.recalculateDanceIdle();
  check(nv.danceEveryNumBeats == 3, 'NV pair change rewrote cadence');
  for (interval in [0, -1]) {
   nv.danceEveryNumBeats = interval;
   check(!host.characterDanceDue(nv, 0), 'nonpositive cadence must disable automatic dance');
  }
  nv.danceEvery = 1;
  check(nv.danceEveryNumBeats == 1 && host.characterDanceDue(nv, 1), 'host/source aliases diverged');
 }
}'''.replace('@@GETTERS@@', getters).replace('@@METHODS@@', methods).replace('@@GATE@@', gate)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture, encoding='utf-8', newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
