"""Asset candidate deduplication remains ordered and avoids quadratic normalization."""
from pathlib import Path
import subprocess,tempfile,unittest
from haxe_test_support import HAXE_COMMAND,FixturePath
from test_import_workflow import extract_method
ROOT=Path(__file__).resolve().parents[2]
class ImportAssetCandidateDedupeTest(unittest.TestCase):
    def test_candidate_order_and_normalization_cost(self):
        source=(ROOT/"source/ImportWorkflow.hx").read_text()
        candidate=extract_method(source,"static function scriptCandidatesForToken(")
        self.assertNotIn("uniquePush(result,",candidate)
        legacy=candidate.replace("scriptCandidatesForToken(","legacyCandidates(",1).replace(
            "var resultKeys:Map<String, Bool> = new Map();", "").replace(
            "uniquePushKeyed(result, resultKeys,", "uniquePush(result,")
        methods="\n".join(extract_method(source,m) for m in ("static function uniquePush(","static function uniquePushKeyed("))
        fixture=r'''import haxe.io.Path;
using StringTools;
class EngineCompat {public static function resolveLegacyAssetPath(p:String):String return p;}
class AssetCandidatesFixture {
 static var normalizations=0;
 static function pathKey(p:String):String { normalizations++; return Path.normalize(p.replace("\\","/")).toLowerCase(); }
 static function caseInsensitivePath(p:String):String return p;
 static function canonicalLegacyCharacter(p:String):String return p=="boyfriend" ? "bf" : p;
 METHODS
 CANDIDATE
 LEGACY
 static function main() {
  var roots=[for(i in 0...8) "C:/mods/owner"+i]; roots.push(roots[0]); roots.push("C:/mods/OWNER0");
  var cases=[{ref:"sky",token:"image"},{ref:"boyfriend",token:"healthicon"},
   {ref:"assets/sounds/noise",token:"Paths.sound"},{ref:"sprite.png",token:"fromSpriteSheetPacker"},
   {ref:"C:/mods/absolute.png",token:"loadGraphic"},{ref:"//server/share/image.png",token:"image"},
   {ref:"",token:"image"},{ref:"./folder/../sky",token:"image"}];
  for(c in cases) {
   normalizations=0; var old=legacyCandidates(roots,"C:/mods/owner0/stages/stage.hscript",c.ref,c.token);
   var oldCount=normalizations; normalizations=0;
   var current=scriptCandidatesForToken(roots,"C:/mods/owner0/stages/stage.hscript",c.ref,c.token);
   var newCount=normalizations;
   if(haxe.Json.stringify(old)!=haxe.Json.stringify(current)) throw "candidate order/spelling changed: "+c.ref;
   if(old.length>30 && newCount*10>=oldCount) throw "normalization still grows quadratically";
   if(current.length>0 && current[0].indexOf("OWNER0")>=0) throw "later case variant replaced first spelling";
  }
  var a=scriptCandidatesForToken(["C:/owner-a"],"C:/stage.hscript","sky","image");
  var b=scriptCandidatesForToken(["C:/owner-b"],"C:/stage.hscript","sky","image");
  if(b.join("|").indexOf("owner-a")>=0 || a.join("|").indexOf("owner-b")>=0) throw "candidate sets leaked owners";
  if(scriptCandidatesForToken(roots,"C:/stage.hscript","sky","image").length==0) throw "previous lookup suppressed candidates";
 }
}
'''.replace("METHODS",methods).replace("CANDIDATE",candidate).replace("LEGACY",legacy)
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder)/"AssetCandidatesFixture.hx").write_text(fixture,newline="\n")
            result=subprocess.run([*HAXE_COMMAND,"-cp",folder,"--run","AssetCandidatesFixture"],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
