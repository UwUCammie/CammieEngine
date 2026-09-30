from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SodarEventsTest(unittest.TestCase):
    def test_companion_effects_and_singer_switches(self):
        fixtures = [
            ROOT / 'assets/data/sodar-fallout/sodar-fallout-hard.json',
            ROOT / 'assets/data/sodar-fallout/events.json',
        ]
        if not all(path.is_file() for path in fixtures):
            self.skipTest('mounted SODAR chart/event fixtures unavailable: ' + ', '.join(str(path) for path in fixtures))
        source = (ROOT / 'source/PlayState.hx').read_text()
        singer = source[source.index('\tpublic var gfSinging:'):source.index('\n\tfunction fireSongEvent')]
        cases = source[source.index("\t\t\tcase 'GF Sing':"):source.index("\t\t\tcase 'Add Camera Zoom':")]
        fixture = '''class Character {public var visible=false;public function new(){}}
class EventTest {
 public function new(){}
 var dad=new Character();var gf=new Character();
''' + singer + '''
 function fire(name:String){switch(name){
''' + cases + '''
 default:
 }}
 static function main(){
  var chart=haxe.Json.parse(sys.io.File.getContent('assets/data/sodar-fallout/sodar-fallout-hard.json')).song;
  var companion=haxe.Json.parse(sys.io.File.getContent('assets/data/sodar-fallout/events.json')).song;
  var events=SongEvents.collect(chart.events,companion.events);
  var counts=new Map<String,Int>();var previous=-1.0;
  var state=new EventTest();var switches=0;
  for(e in events){
   if(e.time<previous)throw 'Events out of order';previous=e.time;
   counts.set(e.name,counts.exists(e.name)?counts.get(e.name)+1:1);
   state.fire(e.name);
   if(e.name=='GF Sing'){switches++;if(e.time!=63950||state.getOpponentSinger()!=state.gf||!state.gf.visible)throw 'GF must take over';}
   if(e.name=='Dad Sing'){switches++;if(e.time!=92950||state.getOpponentSinger()!=state.dad)throw 'Dad must resume';}
  }
  if(switches!=2||counts.get('Screen Shake')!=45||counts.get('Red Flash Camera')!=18||counts.get('Add Camera Zoom')!=131)throw 'Missing choreography';
  if(SongEvents.collect(companion.events,companion.events).length!=events.length-2)throw 'Duplicated external events';
  var distinct=SongEvents.collect([[0,[['test','a',''],['test','b','']]]],null);
  if(distinct.length!=2)throw 'Distinct simultaneous events lost';
 }
}
'''
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'EventTest.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder, '-cp', str(ROOT / 'source'), '-main', 'EventTest', '--interp'], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
