"""Exercise the real Codename occurrence registry with lightweight actors."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CodenameActorRuntimeTest(unittest.TestCase):
    def test_order_identity_unresolved_and_ownership(self):
        fixture = r'''
class Actor {
 public var id:Int;
 public function new(id:Int) this.id=id;
}
class Main {
 static function check(ok:Bool, message:String):Void if (!ok) throw message;
 static function main():Void {
  var stage=CodenameStagePlacement.toData(CodenameStagePlacement.parse(
   '<stage><char name="same" x="10" spacingx="35" flip="false"/>'
   +'<dad flip="true"/><girlfriend/></stage>'));
  var entry:Dynamic={stagePlacement:stage, nativeCharacters:{}, lines:[
   {role:"player",type:1,position:null,characters:["same","same"]},
   {role:"opponent",type:0,position:null,characters:["same"]},
   {role:"gf",type:2,position:null,characters:["unknown"]},
   {role:"extra",type:3,position:null,characters:["same"]}]};
  Reflect.setField(entry.nativeCharacters,"same","native-same");
  Reflect.setField(entry.nativeCharacters,"unknown",null);
  var plan=new CodenameActorPlan(entry);
  var made=0; var destroyed:Array<Int>=[]; var placed:Array<String>=[];
  var runtime=new CodenameActorRuntime<Actor>(plan,
   function(_) return new Actor(++made),
   function(actor,record) placed.push(record.lineIndex+":"+record.occurrenceIndex+":"+actor.id),
   function(actor) destroyed.push(actor.id));
  var primary=new Actor(100);
  check(!runtime.bindPrimary("player","edited-name",primary),"edited primary must not alias");
  check(runtime.bindPrimary("player","native-same",primary),"exact primary alias");
  check(runtime.bindPrimary("player","native-same",primary),"idempotent alias");
  check(!runtime.bindPrimary("opponent","native-same",primary),"one actor cannot bind two records");
  check(!runtime.bindPrimary("gf","unknown",new Actor(101)),"null map cannot alias");
  runtime.materialize(); runtime.materialize();
  check(made==3 && runtime.bindings.length==4,
   "each resolved occurrence once: made="+made+" bound="+runtime.bindings.length
   +" diagnostics="+runtime.diagnostics.join(","));
  check(runtime.find(0,0).actor==primary && !runtime.find(0,0).owned,"borrowed primary");
  check(runtime.find(0,1).actor!=primary && runtime.find(0,1).actor!=runtime.find(1,0).actor,
   "repeated ID has distinct instances");
  check(runtime.find(2,0)==null && runtime.diagnostics[0]=="unresolved-character:2:0:unknown",
   "null map is explicit and uninstantiated");
  check(runtime.structuredDiagnostics.length==1
   && runtime.structuredDiagnostics[0].code=="unresolved-character"
   && runtime.structuredDiagnostics[0].lineIndex==2
   && runtime.structuredDiagnostics[0].occurrenceIndex==0
   && runtime.structuredDiagnostics[0].role=="gf"
   && runtime.structuredDiagnostics[0].lineType==2
   && runtime.structuredDiagnostics[0].authoredId=="unknown",
   "unresolved type-2 GF needs a structured authored-identity diagnostic");
  check(runtime.lineCharacters(2).length==1 && runtime.lineCharacters(2)[0]==null,
   "unresolved line retains occurrence slot");
  check(placed.join(",")=="0:0:100,0:1:1,1:0:2,3:0:3","source insertion order");
  var line=runtime.lineCharacters(0);
  check(line.length==2 && line[0]==primary && line[1]==runtime.find(0,1).actor,
   "line accessor order");
  line.pop(); check(runtime.lineCharacters(0).length==2,"accessor returns copy");
  var replacement=new Actor(200);
  check(runtime.rebindBorrowed(primary,replacement) && runtime.find(0,0).actor==replacement
   && runtime.lineCharacters(0)[0]==replacement,"native primary swap retains exact occurrence");
  check(!runtime.rebindBorrowed(replacement,runtime.find(0,1).actor),
   "borrowed actor cannot alias an owned occurrence");
  var scriptActor=new Actor(201);
  var retainedExtra=runtime.find(0,1).actor;
  check(runtime.removeActor(0,1) && runtime.lineCharacters(0)[1]==null
   && runtime.replaceActor(0,1,retainedExtra,true)
   && runtime.lineCharacters(0)[1]==retainedExtra,
   "script collection removal and reattachment lost its authored occurrence");
  check(runtime.replaceActor(0,0,scriptActor,true) && runtime.find(0,0).actor==scriptActor
   && runtime.lineCharacters(0)[0]==scriptActor,"source script actor replacement updates line identity");
  var restoredPrimary=new Actor(202);
  check(runtime.replaceActor(0,0,restoredPrimary,false)
   && runtime.rebindBorrowed(restoredPrimary,new Actor(203)),
   "source script may return the occurrence to a native primary");
  runtime.cleanup(); runtime.cleanup();
  check(destroyed.join(",")=="201,1,2,3" && runtime.bindings.length==0,
   "retired and active owned actors destroyed once; borrowed preserved");
  check(runtime.lineCharacters(0).length==2 && runtime.lineCharacters(0)[0]==null
   && !runtime.bindPrimary("player","native-same",primary),
   "released runtime cannot revive");
  var bad:Dynamic=haxe.Json.parse(haxe.Json.stringify(entry));
  bad.stagePlacement.unsupported=["dynamic-stage-placement"];
  var unsupported=new CodenameActorRuntime<Actor>(new CodenameActorPlan(bad),
   function(_) { made++; return new Actor(made); }, function(_,_) {}, function(_) {});
  check(unsupported.bindPrimary("player","native-same",primary),"primary identity remains known");
  var before=made; unsupported.materialize();
  check(made==before && unsupported.lineCharacters(0).length==2
   && unsupported.lineCharacters(0)[0]==primary && unsupported.lineCharacters(0)[1]==null
   && unsupported.diagnostics.indexOf("unsupported-placement:0:1")>=0,
   "unsupported placement skips extra construction without discarding primary identity");
  unsupported.cleanup();
  var failedDestroyed:Array<Int>=[];
  var failed=new CodenameActorRuntime<Actor>(plan,
   function(record) return new Actor(300+record.lineIndex*10+record.occurrenceIndex),
   function(_,record) if (record.lineIndex==0 && record.occurrenceIndex==1) throw "bad slot",
   function(actor) failedDestroyed.push(actor.id));
  check(failed.bindPrimary("player","native-same",primary),"failure fixture primary");
  failed.materialize();
  check(failed.find(0,1)==null && failed.lineCharacters(0)[1]==null
   && failedDestroyed.join(",")=="301"
   && failed.diagnostics[0]=="placement-failed:0:1:bad slot",
   "failed placement destroys the new instance and preserves its ordinal");
  check(failed.contains(primary) && !failed.contains(new Actor(999)),"actor membership");
  failed.cleanup();
  check(failedDestroyed.join(",")=="301,310,330","remaining owned actors destroyed once");
  var fallbackEntry:Dynamic={stagePlacement:stage,nativeCharacters:{unavailable:null},
   missingCharacters:["unavailable"],lines:[
    {role:"gf",type:2,position:null,characters:["unavailable"]}]};
  var fallbackPlan=new CodenameActorPlan(fallbackEntry,null,"native-fallback");
  var fallbackRuntime=new CodenameActorRuntime<Actor>(fallbackPlan,
   function(_) return new Actor(401),function(_,_) {},function(_) {});
  fallbackRuntime.materialize();
  var fallbackOccurrence=fallbackPlan.occurrences[0];
  check(fallbackOccurrence.authoredId=="unavailable"
   && fallbackOccurrence.nativeName=="native-fallback"
   && fallbackOccurrence.sourceFallbackId=="native-fallback"
   && fallbackRuntime.find(0,0)!=null && fallbackRuntime.diagnostics.length==0,
   "supported source fallback must construct while retaining authored identity");
 }
}
'''
        (ROOT / "tmp").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as work:
            folder = Path(work)
            (folder / "Main.hx").write_text(fixture)
            result = subprocess.run([
                str(ROOT / ".tools/haxe/haxe"), "-cp", str(ROOT / "source"),
                "-cp", str(folder), "--run", "Main"], cwd=ROOT,
                env={**os.environ, "TMPDIR": work}, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
