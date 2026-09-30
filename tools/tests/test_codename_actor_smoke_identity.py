"""Native smoke actor tokens must identify instances even across state reuse."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ActorSmokeIdentityTest(unittest.TestCase):
    def test_real_snapshot_keeps_instance_identity_across_states(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\tfunction runtimeSmokeActorSummary(')
        end = source.index('\n\tfunction reapplyCodenameActors(', start)
        method = source[start:end]
        fixture = r'''
class Character {
 public var runtimeSmokeActorToken:Int=0;
 public var curCharacter="repeated";
 public var x:Float=10; public var y:Float=20; public var alpha:Float=0.75;
 public var scale={x:1.5,y:0.8};
 public function new() {}
}
class Main {
 static var nextRuntimeSmokeActorToken:Int=1;
 var codenameActors:{bindings:Array<{actor:Character,owned:Bool,occurrence:{lineIndex:Int,occurrenceIndex:Int,authoredId:String}}>} ;
 var members:Array<Character>;
 public function new(actors:Array<Character>) {
  members=actors.copy();
  codenameActors={bindings:[for(i in 0...actors.length)
   {actor:actors[i],owned:i>0,occurrence:{lineIndex:0,occurrenceIndex:i,authoredId:"repeated"}}]};
 }
 __METHOD__
 static function main() {
  var first=new Character(); var second=new Character();
  var a=new Main([first,second]); var snap=a.runtimeSmokeActorSummary();
  if(snap.owned!=1 || snap.borrowed!=1 || snap.actors.length!=2) throw "counts";
  if(snap.actors[0].token==snap.actors[1].token) throw "duplicate IDs collapsed";
  var again=a.runtimeSmokeActorSummary();
  if(again.actors[1].token!=snap.actors[1].token) throw "unstable token";
  var b=new Main([first,new Character()]); var next=b.runtimeSmokeActorSummary();
  if(next.actors[0].token!=snap.actors[0].token) throw "reused object escaped detection";
  if(next.actors[1].token==snap.actors[1].token) throw "new object reused token";
  if(next.actors[1].displayIndex!=1 || next.actors[1].occurrenceIndex!=1
   || next.actors[1].scaleX!=1.5 || next.actors[1].alpha!=0.75) throw "snapshot";
  b.codenameActors=null;
  if(b.runtimeSmokeActorSummary().actors.length!=0) throw "missing registry";
 }
}
'''.replace('__METHOD__', method)
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
            Path(tmp, 'Main.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', tmp,
                                     '-main', 'Main', '--interp'],
                                    capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
