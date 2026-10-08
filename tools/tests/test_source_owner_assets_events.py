"""Owner-local Lime and OpenFL Assets event bridges use pinned event classes."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path


ROOT = Path(__file__).resolve().parents[2]
LIME = ROOT / ".haxelib/lime/8,3,2/src"
OPENFL = ROOT / ".haxelib/openfl/9,5,2/src"


class SourceOwnerAssetsEventsTest(unittest.TestCase):
    def test_owner_event_sharing_listener_routing_and_release(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file():
            self.skipTest("portable Haxe is unavailable")

        files = {
            "SourceOwnerAssetContext.hx": r'''package;
class SourceOwnerAssetContext {
 public var ownerRoot:String;public var engine:String;public var scope:String;
 public function new(ownerRoot:String,engine:String,scope:String){this.ownerRoot=ownerRoot;this.engine=engine;this.scope=scope;}
}''',
            "SourceOwnerAssetsEventsFixture.hx": r'''package;
import lime.app.Event;
import lime.utils.AssetLibrary;
import lime.utils.Assets as HostLimeAssets;
import openfl.events.Event as OpenFlEvent;
class SourceOwnerAssetsEventsFixture {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function main():Void {
  var contextA=new SourceOwnerAssetContext("owner-A","Nightmare Vision","composite");
  var contextACopy=new SourceOwnerAssetContext("owner-A","Nightmare Vision","composite");
  var contextB=new SourceOwnerAssetContext("owner-B","Nightmare Vision","composite");
  var a=SourceOwnerAssetsEvents.forContext(contextA);
  var aAgain=SourceOwnerAssetsEvents.forContext(contextACopy);
  var b=SourceOwnerAssetsEvents.forContext(contextB);
  check(a==aAgain&&a!=b,"event provider was not shared exactly by owner context");
  check(a.limeOnChange!=HostLimeAssets.onChange,
   "owner Lime event reused the process-global event object");

  var limeCalls=0;
  var openCalls=0;
  var customCalls=0;
  var ownerLimeListener=function():Void limeCalls++;
  var openListener=function(_event:OpenFlEvent):Void openCalls++;
  var customListener=function(_event:OpenFlEvent):Void customCalls++;
  a.addOnChange(ownerLimeListener);
  var localLibrary=new AssetLibrary();
  a.watchLibrary(localLibrary);
  a.watchLibrary(localLibrary);
  localLibrary.onChange.dispatch();
  check(limeCalls==1,"one local library change did not dispatch once to Lime listeners");

  a.addEventListener(OpenFlEvent.CHANGE,openListener);
  check(a.hasEventListener(OpenFlEvent.CHANGE)&&a.willTrigger(OpenFlEvent.CHANGE),
   "OpenFL owner dispatcher did not report its listener");
  a.limeOnChange.dispatch();
  check(openCalls==1&&limeCalls==2,"OpenFL CHANGE was not bridged from the owner Lime event");
  check(!b.hasEventListener(OpenFlEvent.CHANGE),"another owner inherited the OpenFL listener");
  a.addEventListener("fixture",customListener);
  check(a.dispatchEvent(new OpenFlEvent("fixture"))&&customCalls==1,
   "owner OpenFL dispatchEvent did not dispatch its event");
  a.removeEventListener(OpenFlEvent.CHANGE,openListener);
  a.removeEventListener("fixture",customListener);
  check(!a.hasEventListener(OpenFlEvent.CHANGE)&&!a.willTrigger("fixture"),
   "OpenFL listener removal did not update hasEventListener/willTrigger");

  a.unwatchLibrary(localLibrary);
  localLibrary.onChange.dispatch();
  check(limeCalls==2,"unwatchLibrary left a callback attached to the owner library");
  a.removeOnChange(ownerLimeListener);
  check(!a.hasOnChange(ownerLimeListener),"removeOnChange retained a source callback");
  var releaseLibrary=new AssetLibrary();
  a.watchLibrary(releaseLibrary);
  check(releaseLibrary.onChange.__listeners.length==1,
   "owner-local library did not receive exactly one listener");
  var releasedLibraryCalls=0;
  a.addOnChange(function():Void releasedLibraryCalls++);
  var bCalls=0;
  b.addOnChange(function():Void bCalls++);
  SourceOwnerAssetsEvents.releaseOwner("owner-A");
  releaseLibrary.onChange.dispatch();
  check(releaseLibrary.onChange.__listeners.length==0
   &&limeCalls==2&&openCalls==1&&releasedLibraryCalls==0,
   "released owner retained listeners or callbacks from its library");
  b.limeOnChange.dispatch();
  check(bCalls==1&&b.hasOnChange(null)==false,"owner release affected another owner event provider");
  var replacement=SourceOwnerAssetsEvents.forContext(contextA);
  check(replacement!=a,"retired event provider was returned again");
  var releasedDispatchRejected=false;
  try a.addEventListener("after-release",customListener) catch (_:Dynamic) releasedDispatchRejected=true;
  check(releasedDispatchRejected,"retired proxy accepted a new owner listener");
  SourceOwnerAssetsEvents.releaseOwner("owner-A");
  SourceOwnerAssetsEvents.releaseOwner("owner-B");
 }
}''',
        }

        with tempfile.TemporaryDirectory(prefix="source-owner-events-", dir=ROOT / "tmp") as scratch:
            work = Path(scratch)
            for name, content in files.items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="\n")
            env = os.environ.copy()
            env["HAXELIB_PATH"] = str(ROOT / ".haxelib")
            env["NEKOPATH"] = str(ROOT / ".tools/neko")
            env["PATH"] = os.pathsep.join(
                [str(ROOT / ".tools/haxe"), str(ROOT / ".tools/neko"), env.get("PATH", "")]
            )
            result = subprocess.run(
                [*HAXE_COMMAND, "-D", "lime=8.3.2", "-D", "openfl=9.5.2",
                 "-D", "lime-native", "-D", "openfl-native", "-D", "desktop", "-D", "windows",
                 "-cp", str(LIME), "-cp", str(OPENFL),
                 "-cp", str(ROOT / "source"), "-cp", scratch, "--run",
                 "SourceOwnerAssetsEventsFixture"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
