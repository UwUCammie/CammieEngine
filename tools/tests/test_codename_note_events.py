"""Compile the production note-event models and verify donor recycling semantics."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameNoteEventsTest(unittest.TestCase):
    def test_mutable_fields_aliases_cancellation_and_recycle(self):
        fixture = r'''
class Main {
 static function check(ok:Bool,label:String):Void if(!ok) throw label;
 static function main():Void {
  var note=new Note(), a=new Character(1), b=new Character(2), icon=new HealthIcon();
  var hit=new CodenameNoteHitEvent(false,true,true,null,true,true,note,[a,b],true,
   'mine','-alt','game/score/','',2,350,0.9,0.023,'sick',true,0.5,true,0.7,true,null,icon);
  check(hit.character==a&&hit.characters.length==2&&hit.forceAnim==null
   &&hit.clipSustain,'hit constructor order, nullable force, or sustain clipping default');
  hit.character=b;
  check(hit.characters.length==1&&hit.characters[0]==b,'hit character setter');
  hit.preventAnim();hit.preventDeletion();hit.forceDeletion();hit.preventVocalsUnmute();
  hit.preventCamZooming();hit.preventLastSustainHit();hit.preventSustainClip();
  hit.preventStrumGlow();hit.cancel(false);
  check(hit.animCancelled&&hit.deleteNote&&!hit.unmuteVocals&&!hit.enableCamZooming
   &&!hit.autoHitLastSustain&&!hit.clipSustain&&hit.strumGlowCancelled&&hit.stopsPropagation(),
   'hit helper effects');
  hit.data={prior:true};
  hit.recycle(false,false,false,null,false,false,note,[a],false,null,'','','',1,0,null,0,
   'bad',false,0.5,true,0.7,true,true,icon);
  check(!hit.cancelled&&!hit.stopsPropagation()&&!hit.animCancelled&&hit.deleteNote
   &&hit.unmuteVocals&&hit.enableCamZooming&&hit.autoHitLastSustain
   &&hit.clipSustain&&!hit.strumGlowCancelled&&hit.data.prior==null&&hit.character==a,
   'hit recycle did not reset base and hidden state');
  var miss=new CodenameNoteMissEvent(note,-10,1,true,-0.0475,'miss.ogg',0.15,
   false,true,'sad',true,null,'miss',[a,b],1,'mine',3,0);
  check(miss.character==a&&miss.healthGain==-0.0475&&miss.forceAnim==null,
   'miss constructor order');
  miss.character=b;check(miss.characters.length==1&&miss.character==b,'miss character setter');
  miss.preventMissSound();miss.preventResetCombo();miss.preventStunned();
  miss.preventAnim();miss.preventDeletion();miss.preventVocalsMute();miss.cancel(false);
  check(!miss.playMissSound&&!miss.resetCombo&&!miss.stunned&&miss.animCancelled
   &&!miss.deleteNote&&!miss.muteVocals&&miss.stopsPropagation(),
   'miss helper effects');
  miss.recycle(note,-1,2,true,-0.04,'other',0.1,true,false,'sad',false,true,
   '',[a],0,null,0,null);
  check(!miss.cancelled&&!miss.stopsPropagation()&&miss.playMissSound&&miss.resetCombo
   &&miss.stunned&&!miss.animCancelled&&miss.deleteNote&&miss.muteVocals
   &&miss.ghostMiss&&miss.character==a,'miss recycle did not reset state');
  Sys.println('note events ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            for name, body in {
                'Character': 'public var id:Int; public function new(id:Int) this.id=id;',
                'Note': 'public function new() {}',
                'HealthIcon': 'public function new() {}',
            }.items():
                (Path(folder) / (name + '.hx')).write_text('class ' + name + ' {' + body + '}')
            for name in ('CodenameGameEvent', 'CodenameNoteHitEvent', 'CodenameNoteMissEvent'):
                (Path(folder) / (name + '.hx')).write_text(
                    (ROOT / 'source' / (name + '.hx')).read_text()
                )
            (Path(folder) / 'Main.hx').write_text(fixture)
            result = subprocess.run(
                [str(ROOT / '.tools/haxe/haxe'), '-cp', folder, '-main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('note events ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
