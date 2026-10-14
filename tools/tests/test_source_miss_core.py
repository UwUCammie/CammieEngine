"""The shared source miss core: instakill and the historical health mode.

Psych, modern Nightmare Vision and the historical Nightmare Vision flows all
end a run through killOnSourceMiss, and the historical flows take their health
from the same helpers as the other two. The fixture runs the real helpers and
compares them with the inline code each caller used to carry.
"""
from pathlib import Path
import subprocess, tempfile, unittest
from haxe_test_support import HAXE_COMMAND
from test_psych_camera_alias import extract_method

ROOT = Path(__file__).resolve().parents[2]


class SourceMissCoreTest(unittest.TestCase):
	def setUp(self):
		self.play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8').replace('\r\n', '\n')

	def run_fixture(self, body):
		methods = '\n'.join(extract_method(self.play, 'function ' + name + '(') for name in (
			'applySourceMissHealth', 'applySourceHitHealth', 'killOnSourceMiss'))
		fixture = r'''
class Field {public var playerControls=true;public function new(){}}
class Note {public var missHealth:Null<Float>=null;public var hitHealth:Null<Float>=null;public var isSustainNote=false;public function new(){}}
class Main {
 var health=1.;var healthLoss=1.;var healthGain=1.;var healthLossMultiplier=1.;var healthGainMultiplier=1.;
 var pressMissDamage:Null<Float>=null;var holdSubdivisions=1;var guitarHeroSustains=false;var sourceScoreNightmare=true;
 var instakillOnMiss=false;var log:Array<String>=[];var field=new Field();var fieldAsked=0;
 function new(){}
 function nightmareVisionFieldForNote(n:Note):Field {fieldAsked++;return field;}
 function setSourceVocalVolume(role:String,v:Float)log.push(role+':'+v);
 function doDeathCheck(force:Bool)log.push('death:'+force);
 METHODS
 static function check(ok:Bool,why:String)if(!ok)throw why;
 static function main(){
BODY
 }
}
'''.replace('METHODS', methods).replace('BODY', body)
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
			(Path(folder) / 'Main.hx').write_text(fixture, newline='\n')
			(Path(folder) / 'SourceHealthDelta.hx').write_text(
				(ROOT / 'source/SourceHealthDelta.hx').read_text(encoding='utf-8'), newline='\n')
			result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--run', 'Main'], cwd=ROOT,
									capture_output=True, text=True, timeout=60)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

	def test_instakill_mutes_then_dies_once(self):
		self.run_fixture(r'''
  var s=new Main();s.killOnSourceMiss(true);
  check(s.log.length==0,'no instakill means nothing happens');
  s.instakillOnMiss=true;s.killOnSourceMiss(true);
  check(s.log.join(',')=='player:0,opponent:0,death:true','Psych silences both tracks before the death check');
  s=new Main();s.instakillOnMiss=true;s.killOnSourceMiss(false);
  check(s.log.join(',')=='player:0,death:true','Nightmare Vision silences only the player track');
''')

	def test_historical_health_matches_the_old_inline_formulas(self):
		self.run_fixture(r'''
  for(loss in [0.,0.5,1.,2.5])for(gain in [0.,1.,3.])for(authored in [null,0.,0.04,0.3])for(sustain in [false,true])
  for(multiplier in [1.,0.5,4.])for(subdivisions in [1,4])for(press in [false,true]){
   var s=new Main();s.healthLoss=loss;s.healthGain=gain;s.healthLossMultiplier=multiplier;s.healthGainMultiplier=multiplier;
   s.holdSubdivisions=subdivisions;s.pressMissDamage=0.4;s.field.playerControls=false;
   var n=new Note();n.missHealth=authored;n.hitHealth=authored;n.isSustainNote=sustain;
   s.health=1;s.applySourceMissHealth(press?null:n,true,true,true);
   var expected=1.;expected-=press?SourceHealthDelta.pressMiss(loss):SourceHealthDelta.miss(true,authored,loss);
   check(s.health==expected,'historical miss health '+loss+' '+authored+' '+press);
   s.health=1;s.applySourceHitHealth(n,true,true);
   expected=1.;expected+=SourceHealthDelta.hit(true,authored,gain);
   check(s.health==expected,'historical hit health '+gain+' '+authored);
   check(s.fieldAsked==0,'historical hit health ignores the modern field gate');
   s.health=1;s.applySourceMissHealth(n,true,false,true);
   check(s.health==1,'no reaction means no health change');
  }
  var s=new Main();s.healthLossMultiplier=2;var n=new Note();n.missHealth=0.1;
  s.applySourceMissHealth(n,true,true);
  check(Math.abs(s.health-0.8)<1e-9,'the modern mode still applies the native modifier');
''')

	def test_callers_use_the_shared_core(self):
		miss = extract_method(self.play, 'function sourceNoteMiss(')
		self.assertIn('killOnSourceMiss(true);', miss)
		self.assertIn('if (instakillOnMiss) killOnSourceMiss(false);', miss)
		self.assertEqual(miss.count('doDeathCheck('), 0)
		legacy = (ROOT / 'source/NightmareVisionLegacyMissFlow.hx').read_text(encoding='utf-8')
		self.assertEqual(legacy.count('state.killOnSourceMiss(false);'), 2)
		self.assertEqual(legacy.count('state.applySourceMissHealth('), 2)
		self.assertNotIn('SourceHealthDelta', legacy)


if __name__ == '__main__':
	unittest.main()
