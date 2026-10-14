"""Tagged sound bookkeeping, exercised with stand-in sound handles."""
from haxe_test_support import HAXE_COMMAND, FixturePath as Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

FIXTURE = r'''class Handle {
 public var name:String;
 public var alive=true;
 public var disposed=0;
 public function new(name:String) this.name=name;
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main():Void {
  var registry=new TaggedSoundRegistry<Handle>(
   function(handle:Handle):Bool return handle.alive,
   function(handle:Handle):Void {handle.disposed++;handle.alive=false;});
  var music=new Handle('music');

  // two tags, one file: each tag keeps a handle of its own
  var a=new Handle('same-file');
  var b=new Handle('same-file');
  check(registry.put('a',a) && registry.put('b',b),'tags were refused');
  check(registry.get('a')==a && registry.get('b')==b && a!=b,'tags share a handle');
  check(registry.get(' a ')==a,'tags should ignore surrounding spaces');

  // a tag that is played again silences what it had
  var a2=new Handle('other-file');
  registry.put('a',a2);
  check(a.disposed==1 && registry.get('a')==a2 && b.disposed==0,
   'reusing a tag should release only that tag\'s previous handle');
  registry.put('a',a2);
  check(a2.disposed==0,'storing the same handle again must not release it');

  // the replaced handle ending late is nobody's business any more
  check(!registry.finished('a',a,false) && registry.get('a')==a2,
   'a stale handle finishing removed the tag it used to own');

  // a one-shot gives the tag up and is reported exactly once
  check(registry.finished('a',a2,false),'a finished one-shot was not reported');
  check(registry.get('a')==null,'a finished one-shot kept its tag');
  check(!registry.finished('a',a2,false),'a finished one-shot was reported twice');
  check(a2.disposed==0,'finishing must leave releasing the handle to the audio system');

  // a loop keeps its tag through every pass
  check(registry.finished('b',b,true) && registry.finished('b',b,true) && registry.get('b')==b,
   'a looping handle lost its tag');

  // the empty tag is the music only where the caller says so
  check(registry.resolve(null,true,music)==music && registry.resolve('  ',true,music)==music,
   'an empty tag should mean the music');
  check(registry.resolve('',false,music)==null,'an empty tag leaked the music to a strict caller');
  check(registry.resolve('b',true,music)==b,'a real tag should never resolve to the music');
  check(registry.resolve('nobody',true,music)==null,'an unknown tag resolved to something');
  check(!registry.put('',new Handle('x')) && !registry.put(true,new Handle('x')) && !registry.put('c',null),
   'empty tags, loop flags and missing handles must not be stored');
  check(TaggedSoundRegistry.key(7)=='7' && TaggedSoundRegistry.key(null)=='','tag keys');

  // a handle recycled elsewhere drops out on the next lookup
  b.alive=false;
  check(registry.get('b')==null && b.disposed==0,'a dead handle stayed addressable');

  // and a dead handle that still holds a tag is not touched when the tag is reused
  var gone=new Handle('gone');
  registry.put('reused',gone);
  gone.alive=false;
  var fresh=new Handle('fresh');
  registry.put('reused',fresh);
  check(gone.disposed==0 && registry.get('reused')==fresh,
   'reusing a tag released a handle the audio system had already taken back');
  registry.stop('reused');

  var c=new Handle('c');
  var d=new Handle('d');
  registry.put('c',c);
  registry.put('d',d);
  check(registry.stop('c') && c.disposed==1 && registry.get('c')==null,'stop should release and forget');
  check(!registry.stop('c') && !registry.stop(null),'stopping nothing should report nothing');
  registry.clear();
  check(d.disposed==1 && registry.get('d')==null,'clear should release every remaining handle');
 }
}'''


class TaggedSoundRegistryTest(unittest.TestCase):
    def test_tags_own_separate_handles_and_release_them_on_reuse_finish_and_stop(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(FIXTURE, newline='\n')
            (Path(work) / "TaggedSoundRegistry.hx").write_text(
                (ROOT / "source/TaggedSoundRegistry.hx").read_text(), newline='\n')
            result = subprocess.run([*HAXE_COMMAND, "-cp", work, "--run", "Main"], cwd=ROOT,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
