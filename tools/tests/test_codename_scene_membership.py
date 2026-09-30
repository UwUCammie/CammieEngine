"""Execute the shared borrowed-node membership journal with real Haxe."""

from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameSceneMembershipTest(unittest.TestCase):
    def test_overlapping_scopes_and_neighbor_restore(self):
        fixture = '''class Node {
 public var name:String; public var destroyed=false;
 public function new(name:String) this.name=name;
 public function destroy():Void destroyed=true;
}
class Main {
 static function names(nodes:Array<Node>):String return [for (node in nodes) node.name].join(",");
 static function check(nodes:Array<Node>, expected:String):Void
   if (names(nodes)!=expected) throw expected+" != "+names(nodes);
 static function main():Void {
   var a=new Node("a"), b=new Node("b"), c=new Node("c"), x=new Node("x"), d=new Node("d");
   var members=[a,b,c];
   var detaches=0;
   var journal=new CodenameSceneMembership<Node>(
     function() return members,
     function(node) { detaches++; members.remove(node); },
     function(index,node) { members.insert(index,node); });
   var first={}, second={};
   journal.place(first,b,null); check(members,"a,c");
   journal.place(first,b,2); check(members,"a,c,b");
   var beforeDuplicate=detaches;
   journal.place(first,b,0); check(members,"a,c,b");
   if(detaches!=beforeDuplicate) throw "duplicate insert moved an existing member";
   for (_ in 0...10000) journal.place(first,b,2);
   @:privateAccess if (journal.nodes[0].actions.length!=1) throw "unbounded owner history";
   journal.release(first); check(members,"a,b,c");
   journal.place(first,b,null); check(members,"a,c");
   journal.place(second,b,0); check(members,"b,a,c");
   var before=detaches;
   journal.release(first); check(members,"b,a,c");
   if(detaches!=before) throw "earlier owner clobbered later placement";
   journal.release(second); check(members,"a,b,c");
   journal.place(first,b,null); check(members,"a,c");
   journal.place(second,b,0); check(members,"b,a,c");
   journal.release(second); check(members,"a,c");
   members.insert(1,x); check(members,"a,x,c");
   journal.release(first); check(members,"a,x,b,c");
   journal.place(first,d,1); check(members,"a,d,x,b,c");
   journal.release(first); check(members,"a,x,b,c");
   journal.release(first); check(members,"a,x,b,c");
   if (b.destroyed || d.destroyed || x.destroyed) throw "borrowed node destroyed";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            (Path(work) / "Main.hx").write_text(fixture)
            result = subprocess.run(
                [str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                 "-cp", work, "--run", "Main"], cwd=ROOT, text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
