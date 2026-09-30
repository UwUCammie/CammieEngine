"""Exercise the production Character input lease without a game launch."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def method(source, name):
    marker = ("\t@:keep public function " if name == "lockCodenameAnimationForInput"
              else "\tpublic function " if name == "codenameBeatHit"
              else "\tfunction ") + name + "("
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for at in range(brace, len(source)):
        depth += (source[at] == "{") - (source[at] == "}")
        if depth == 0:
            return source[start:at + 1]
    raise AssertionError(name)


class CodenameCharacterInputLockTest(unittest.TestCase):
    def test_held_input_lease_only_blocks_one_update_and_next_beat(self):
        source = (ROOT / "source/Character.hx").read_text()
        methods = "\n".join(method(source, name) for name in (
            "lockCodenameAnimationForInput", "codenameBeatHit", "codenameUpdateAfterSuper"))
        fixture = '''class Character {
 public var codenameLiveDefinition:Dynamic={};
 public var characterDestroyed=false;
 public var stunned=false; var codenameStunnedTime:Float=0;
 public var lastAnimContext:Dynamic='LOCK';
 public var codenameAnimationLock=false;
 public var danceOnBeat=true;
 public var skipNegativeBeats=false;
 public var beatInterval=1;
 public var beatOffset=0;
 public var dances=0;
 public var updates=0;
 public var codenameRuntime:Dynamic;
 public function new() {
  var self=this;
  codenameRuntime={call:function(name:String,_args:Array<Dynamic>):Bool {
   if(name=='update') self.updates++;
   return true;
  }};
 }
 function codenameAdvanceLoop():Void {}
 function codenameTryDance():Void dances++;
''' + methods + '''
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var actor=new Character();
  // Ordinary script playback and a finished animation's loop successor do
  // not grant an input lease. They cannot suppress the next beat dance.
  actor.codenameBeatHit(0);
  check(actor.dances==1 && !actor.codenameAnimationLock,
   'ordinary playback state unexpectedly blocked beat');
  actor.lockCodenameAnimationForInput();
  check(actor.codenameAnimationLock,'held input did not grant lease');
  actor.codenameBeatHit(1);
  check(actor.dances==1 && actor.codenameAnimationLock,
   'beat consumed input lease or danced during held input');
  @:privateAccess actor.codenameUpdateAfterSuper(0.1);
  check(actor.dances==1 && actor.updates==1 && !actor.codenameAnimationLock,
   'update did not preserve and then clear one-frame input lease');
  actor.codenameBeatHit(2);
  check(actor.dances==2,'cleared lease still suppressed beat');
  actor.lastAnimContext='DANCE';
  actor.lockCodenameAnimationForInput();
  check(!actor.codenameAnimationLock,'DANCE context acquired input lease');
  actor.lastAnimContext='LOCK';
  actor.codenameLiveDefinition=null;
  actor.lockCodenameAnimationForInput();
  check(!actor.codenameAnimationLock,'native actor acquired Codename input lease');
  actor.codenameLiveDefinition={};
  actor.characterDestroyed=true;
  actor.lockCodenameAnimationForInput();
  check(!actor.codenameAnimationLock,'destroyed actor acquired input lease');
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture)
            result = subprocess.run([
                str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                "-cp", work, "--run", "Main"], cwd=ROOT,
                capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
