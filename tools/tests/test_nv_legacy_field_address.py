"""Compare nonmutating gameplay field resolution with real NV chart correction."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class NvLegacyFieldAddressTest(unittest.TestCase):
    def test_matches_chart_api_correction_for_legacy_and_absolute_banks(self):
        play = (ROOT / 'source/PlayState.hx').read_text()
        self.assertIn('? ChartNoteOwnership.nightmareVisionAddress(SONG.format,', play)
        self.assertIn('if (nightmareVisionScripts != null) gottaHitNote = chartAddress.playfieldIndex == 0;', play)
        self.assertIn('? chartAddress.playerControlled : ChartNoteOwnership.playerControlOverride(SONG.format, chartAddress);', play)
        fixture = r'''
class Main {
 static function check(ok:Bool,message:String) {if(!ok)throw message;}
 static function main() {
  var api=new NightmareVisionChartApi(function(path:String):String return null,
   function(song:String,difficulty:Int):String return null);
  for(keys in [1,4,6]) for(count in [1,2,3,5]) for(mustHit in [false,true])
   for(format in [null,'','legacy','psych_v1_convert','nmv2','psych_v1']) for(explicitNull in [false,true]) {
    var rows:Array<Array<Dynamic>>=[];
    for(lane in 0...(keys*(count+1))) rows.push([1000,lane,0,'']);
    var raw:Dynamic={keys:keys,lanes:count,notes:[{mustHitSection:mustHit,sectionNotes:rows}]};
    if(format!=null||explicitNull)Reflect.setField(raw,'format',format);
    var before=haxe.Json.stringify(raw);
    var corrected:Dynamic=api.fromData({song:haxe.Json.parse(before)});
    var convertedRows:Array<Array<Dynamic>>=corrected.notes[0].sectionNotes;
    for(lane in 0...rows.length) {
     var actual=ChartNoteOwnership.nightmareVisionAddress(format,lane,mustHit,keys);
     var correctedLane=Std.int(convertedRows[lane][1]);
     var expected=ChartNoteOwnership.address(corrected.format,correctedLane,mustHit,keys);
     check(actual.playfieldIndex==expected.playfieldIndex,'legacy/absolute field mismatch '+format+':'+lane);
     check(actual.direction==expected.direction,'local direction mismatch');
     check(actual.playerControlled==(expected.playfieldIndex!=1),'NV source owner policy');
     check(actual.autoPlay==(expected.playfieldIndex!=0),'NV source autoplay policy');
     check((actual.playfieldIndex>=0 && actual.playfieldIndex<count)==(expected.playfieldIndex<count),'source admission guard');
    }
    check(haxe.Json.stringify(raw)==before,'address query mutated retained source chart');
   }
  var event=ChartNoteOwnership.nightmareVisionAddress(null,-1,false,4);
  check(event.playfieldIndex==-1&&!event.playerControlled&&!event.autoPlay,'legacy event not playable');
  check(ChartNoteOwnership.nightmareVisionAddress(null,8,false,4).playfieldIndex==2,'third field preserved');
  // Existing shared callers retain their old binary ownership contracts.
  check(ChartNoteOwnership.address(null,8,false,4).playfieldIndex==1,'native legacy route remains binary');
  check(ChartNoteOwnership.mustPress('psych_v1_convert',0,false,4),'Psych conversion route unchanged');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', directory,
                                     '-main', 'Main', '--interp'], capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
