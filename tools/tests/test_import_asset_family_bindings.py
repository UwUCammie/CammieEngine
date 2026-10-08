"""Exercise the real manager routing after a validated NV family catalog."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND


ROOT = Path(__file__).resolve().parents[2]


class ImportAssetFamilyBindingsTest(unittest.TestCase):
    def test_provider_keeps_ordinary_index_and_receivers_use_exact_handoff(self):
        source = (ROOT / "source/ImportRefreshManager.hx").read_text(encoding="utf-8")
        start = source.index("\tstatic function buildAssetIndexBindings(")
        end = source.index("\n\t/** Replace the small set", start)
        method = source[start:end].replace("static function", "public static function", 1)
        fixture = r'''package;
typedef ImportRefreshPackageFamilyCatalog = {
 var version:Int;
 var members:Array<Dynamic>;
 var coreProvider:Dynamic;
}
class ImportWorkScheduler { public static function cooperate():Void {} }
class ImportRevision { public static function normalizeEngine(value:String):String return value; }
class SourceLimeAssetIdentity {
 public static inline var SIDECAR_DIR:String=".cammie-asset-identities";
 public static function sidecarRelativePath(engine:String,scope:String):String
  return SIDECAR_DIR+"/"+engine+"-"+scope+".json";
}
class ImportRefreshTransaction {
 // Catalog validation has its own real retained-transaction coverage. This
 // seam supplies its accepted value to isolate the manager's routing logic.
 public static function validatePackageFamilyCatalog(value:Dynamic,record:Dynamic):Dynamic {
  if(value.rejected==true) throw "invalid catalog";
  return value;
 }
}
class BindingBuilder {
 static function normalizeInstallRelative(value:String):String return value;
__METHOD__
}
class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function profile(namespace:String,relative:String,sha:String,snapshot:String):Dynamic {
  return {namespace:namespace,engine:"Nightmare Vision",rootRelative:relative,
   profile:{namespace:namespace,sourceEngine:"Nightmare Vision",rootRelative:relative,
    projectSha256:sha,snapshotId:snapshot,provenance:"receipt-bound"}};
 }
 static function main():Void {
  var snapshot=StringTools.lpad("","0",64);
  var providerSha=StringTools.lpad("","1",64);
  var memberSha=StringTools.lpad("","2",64);
  var receiver="assets/imported_mods/receiver";
  var provider="assets/imported_mods/provider";
  var family:Dynamic={version:3,members:[{namespace:"receiver",sourceRelative:"content/alpha"}],
   coreProvider:{namespace:"provider",rootRelative:"",projectSha256:providerSha}};
  var record:Dynamic={schemaVersion:1,snapshotId:snapshot,packageFamilyCatalog:family,
   sourceAssetProfiles:{roots:[profile("provider","",providerSha,snapshot),
    profile("receiver","content/alpha",memberSha,snapshot)]}};
  var files:Array<Dynamic>=[];
  for(root in [provider,receiver]) for(scope in ["package","core"])
   files.push({owner:"selection",path:root+"/"+SourceLimeAssetIdentity.sidecarRelativePath("Nightmare Vision",scope),
    sha256:StringTools.lpad("","3",64)});
  var manifest:Dynamic={owner:"selection",transactionId:"transaction",files:files,
   revision:{importRecord:record}};
  var bindings=BindingBuilder.buildAssetIndexBindings(manifest,[provider,receiver]);
  var own=bindings.get(provider+"/Nightmare Vision/core");
  check(own!=null&&own.handoff==null&&own.namespace=="provider"
   &&own.rootRelative==""&&own.projectSha256==providerSha,
   "v3 receiver handoff suppressed or relabeled the provider's ordinary core index");
  var borrowed=bindings.get(receiver+"/Nightmare Vision/core");
  check(borrowed!=null&&borrowed.owner==receiver&&borrowed.namespace=="receiver"
   &&borrowed.rootRelative==""&&borrowed.projectSha256==providerSha,
   "receiver core is not keyed to its exact owner and provider profile");
  check(borrowed.handoff!=null&&borrowed.handoff.providerNamespace=="provider"
   &&borrowed.handoff.receiverNamespace=="receiver"
   &&borrowed.handoff.receiverRootRelative=="content/alpha",
   "receiver handoff edge was lost");
  var packageBinding=bindings.get(receiver+"/Nightmare Vision/package");
  check(packageBinding!=null&&packageBinding.handoff==null&&packageBinding.projectSha256==memberSha,
   "receiver package index incorrectly uses the provider profile");
  family.rejected=true;
  check(!BindingBuilder.buildAssetIndexBindings(manifest,[provider,receiver]).iterator().hasNext(),
   "a rejected v3 catalog fell back to ordinary bindings");
 }
}
'''.replace("__METHOD__", method)
        with tempfile.TemporaryDirectory(prefix="family-index-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            (work / "Main.hx").write_text(fixture, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(work), "--run", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
