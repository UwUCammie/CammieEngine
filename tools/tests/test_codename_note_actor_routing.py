"""Exercise the actual PlayState exact-line singer helper with small actors."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source: str, name: str) -> str:
    start = source.index('\tfunction ' + name + '(')
    brace = source.index('{', start)
    depth = 0
    for i in range(brace, len(source)):
        depth += (source[i] == '{') - (source[i] == '}')
        if depth == 0:
            return source[start:i + 1]
    raise AssertionError(name)


class CodenameNoteActorRoutingTest(unittest.TestCase):
    def test_bound_line_sings_each_live_actor_once_without_fallback(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        helper = method(source, 'singCodenameNoteActors')
        fixture = '''class Character {
 public var altNum:Int=-1; public var altAnim:String="old"; public var holdTimer:Float=7;
 public var calls:Array<String>=[];
 public function new() {}
 public function sing(direction:Int,miss:Bool=false,alt:Int=0):Void
  calls.push(direction+":"+miss+":"+alt);
}
class Note {
 public var codenameInputLine:CodenameInputLine<Character>=null;
 public function new(?line:CodenameInputLine<Character>) codenameInputLine=line;
}
class CodenameInputLine<T> {
 public var actorSlots:Array<Null<T>>;
 public var characters:Array<T>;
 public function new(actors:Array<Null<T>>) {
  actorSlots=actors;characters=[];
  for(actor in actors)if(actor!=null)characters.push(actor);
 }
}
class Main {
 public function new() {}
 public var fades:Array<Character>=[];
 function spawnCrossFade(actor:Character,note:Note):Void fades.push(actor);
''' + helper + '''
 static function check(ok:Bool, why:String):Void if(!ok) throw why;
 static function main():Void {
  var state=new Main();
  var native=new Note();
  check(!state.singCodenameNoteActors(native,2,false,1),"native note must use fallback");
  check(!state.singCodenameNoteActors(null,2,false,1),"null note must use fallback");
  var empty=new Note(new CodenameInputLine<Character>([]));
  check(state.singCodenameNoteActors(empty,2,false,1),"bound empty line must not fall back");
  var first=new Character(); var second=new Character(); var unrelated=new Character();
  var line=new CodenameInputLine<Character>([first,null,first,second]);
  var note=new Note(line);
  check(state.singCodenameNoteActors(note,3,false,2),"bound line not routed");
  check(first.calls.length==1 && second.calls.length==1 && unrelated.calls.length==0,
   "duplicate/null/unrelated actor routing");
  check(state.fades.length==2 && state.fades[0]==first && state.fades[1]==second,
   "source crossfade must target each attached actor once");
  check(first.calls[0]=="3:false:2" && second.calls[0]=="3:false:2",
   "direction, hit context or alt lost");
  check(first.altNum==2 && second.altNum==2 && first.altAnim=="-alt2"
   && second.altAnim=="-alt2" && first.holdTimer==0 && second.holdTimer==0,
   "per actor alt and hold state not updated");
  line.actorSlots=[second];line.characters=[second];
  check(state.singCodenameNoteActors(note,1,true),"current line actors not read");
  check(first.calls.length==1 && second.calls.length==2
   && second.calls[1]=="1:true:0" && second.altNum==0 && second.altAnim=="",
   "miss or current actor membership wrong");
  check(state.fades.length==2,"miss must not create a crossfade");
 }
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'Main.hx').write_text(fixture, newline='\n')
            command = [*HAXE_COMMAND, '-cp', tmp, '-main', 'Main', '--interp']
            result = subprocess.run(command, cwd=ROOT, env=os.environ.copy(), text=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout)

    def test_all_judgement_paths_call_the_exact_line_helper(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        miss = method(source, 'noteMiss')
        hit = method(source, 'goodNoteHit')
        self.assertEqual(miss.count('singCodenameNoteActors('), 2,
            'both authored note miss branches need exact-line singers')
        self.assertEqual(hit.count('singCodenameNoteActors('), 1)
        auto = source[source.index('if (!daNote.mustPress && daNote.wasGoodHit'):
                      source.index('var neg = downscroll ?', source.index('if (!daNote.mustPress && daNote.wasGoodHit'))]
        self.assertEqual(auto.count('singCodenameNoteActors('), 2,
            'opponent and BF autoplay need exact-line singers')
        helper = method(source, 'singCodenameNoteActors')
        for forbidden in ('combo +=', 'notes.remove', 'note.destroy', 'health +=', 'health -=',
                          'callAllHScript', 'callHxcNoteHScript'):
            self.assertNotIn(forbidden, helper,
                'per-actor singer helper must not duplicate one-note judgement effects')


if __name__ == '__main__':
    unittest.main()
