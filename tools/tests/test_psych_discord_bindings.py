"""Psych 1.0.4 callback and source class bindings against the shared lease."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath

ROOT = Path(__file__).resolve().parents[2]
HAXSCRIPT = ROOT / ".haxelib/hscript/2,5,0"

SCRIPT_INTERP_STUB = r'''package;
import hscript.Interp;
class NightmareVisionScriptInterp extends Interp {
 public var importBindings:Map<String,Dynamic>=[];
 var scope:SourceNativeClassScope;
 public function new() {super();scope=new SourceNativeClassScope();scope.installReflectionBindings();}
 public function bindImport(name:String,type:Dynamic):Void importBindings.set(name,type);
 public function sourceClassScope():SourceNativeClassScope return scope;
}'''

FIXTURE = r'''
import Discord.DiscordClient;
import PsychDiscordClient;
import PsychDiscordBindings;
import SourceDiscordPresenceLease;
import SourceNativeClassScope;

class Main {
 static function check(value:Bool,message:String):Void if(!value)throw message;
 static function invoke(interp:hscript.Interp,name:String,args:Array<Dynamic>):Dynamic
  return Reflect.callMethod(null,interp.variables.get(name),args);
 static function main():Void {
  var lease=new SourceDiscordPresenceLease();
  var alive=true;
  var facade=new PsychDiscordClient(lease,function()return alive);
  var lua=new hscript.Interp();
  PsychDiscordBindings.installLua(lua,facade);
  invoke(lua,'changeDiscordPresence',[]);
  var menu=DiscordClient.getRequestedSnapshot();
  check(Reflect.field(menu.presence,'details')=='In the Menus'
   && Reflect.field(menu.presence,'state')==null,
   'Lua callback preserves the donor plain menu default');
  check(Reflect.field(menu.presence,'smallImageKey')==null
   && Reflect.field(menu.presence,'largeImageKey')=='icon'
   && Reflect.field(menu.presence,'largeImageText')=='Engine Version: 1.0.4',
   'Psych image dimensions and version text match the donor');
  check(Reflect.field(menu.presence,'startTimestamp')==0
   && Reflect.field(menu.presence,'endTimestamp')==0,
   'missing timestamp arguments remain zero');

  invoke(lua,'changeDiscordClientID',['configured-psych-id']);
  var before=Std.int(Date.now().getTime()/1000);
  invoke(lua,'changeDiscordPresence',['Song: Test','Playing','small-icon',true,90.0,'large-icon']);
  var playing=DiscordClient.getRequestedSnapshot();
  var start:Int=Reflect.field(playing.presence,'startTimestamp');
  var finish:Int=Reflect.field(playing.presence,'endTimestamp');
  check(playing.clientId=='configured-psych-id'
   && Reflect.field(playing.presence,'details')=='Song: Test'
   && Reflect.field(playing.presence,'state')=='Playing',
   'presence details are forwarded without engine-brand prefixes');
  check(Reflect.field(playing.presence,'smallImageKey')=='small-icon'
   && Reflect.field(playing.presence,'largeImageKey')=='large-icon'
   && Reflect.field(playing.presence,'largeImageText')=='Engine Version: 1.0.4',
   'the third and sixth callback arguments retain donor small/large meaning');
  check(start>=before && finish-start>=0 && finish-start<=1,
   'timestamp starts at callback time and donor adds endTimestamp as raw milliseconds');
  invoke(lua,'changeDiscordClientID',[null]);
  check(DiscordClient.getClientId()==PsychDiscordClient.DEFAULT_CLIENT_ID,
   'nil client ID restores Psych’s pinned default');

  var interp=new NightmareVisionScriptInterp();
  PsychDiscordBindings.install(interp,facade);
  var type=interp.importBindings.get('backend.DiscordClient');
  var scope=interp.sourceClassScope();
  check(type==PsychDiscordClient && scope.resolveClass('backend.DiscordClient')==type
   && scope.resolveClass('DiscordClient')==type,
   'both source class names resolve to one real facade token');
  var setter=scope.read(type,'clientID');
  check(setter==PsychDiscordClient.DEFAULT_CLIENT_ID,
   'source static clientID reads from the owner lease');
  scope.write(type,'clientID','class-assigned-id');
  check(DiscordClient.getClientId()=='class-assigned-id',
   'source static clientID writes through to the shared daemon');
  var classPresence:Dynamic=scope.read(type,'changePresence');
  Reflect.callMethod(null,classPresence,[]);
  check(Reflect.field(DiscordClient.getRequestedSnapshot().presence,'details')=='In the Menus',
   'backend.DiscordClient.changePresence uses the donor no-argument defaults');
  var fields:Array<String>=cast Reflect.callMethod(null,scope.read(Reflect,'fields'),[type]);
  check(fields.indexOf('changePresence')>=0 && fields.indexOf('clientID')>=0,
   'source reflection discovers virtual backend static fields');

  var secondFacade=new PsychDiscordClient(lease);
  facade.release();
  var blocked=false;
  try Reflect.callMethod(null,classPresence,['blocked',null]) catch(_:Dynamic) blocked=true;
  check(blocked && !lease.isReleased(),
   'retiring one provider closes its guard without releasing the shared session lease');
  secondFacade.changePresence('still-live',null);
  check(Reflect.field(DiscordClient.getRequestedSnapshot().presence,'details')=='still-live',
   'a second provider using the same lease remains active');
  secondFacade.release();
  lease.release();

  var guarded=new PsychDiscordClient(new SourceDiscordPresenceLease(),function()return alive);
  alive=false;
  var ownerBlocked=false;
  try guarded.changePresence() catch(_:Dynamic) ownerBlocked=true;
  check(ownerBlocked,'owner departure blocks facade methods even before facade release');
 }
}
'''


class PsychDiscordBindingsTest(unittest.TestCase):
    def test_lua_callbacks_and_haxe_static_class_share_owner_facade(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="psych-discord-bindings-", dir=TEST_TMP) as folder:
            scratch = FixturePath(folder)
            (scratch / "NightmareVisionScriptInterp.hx").write_text(SCRIPT_INTERP_STUB,
                encoding="utf-8", newline="\n")
            (scratch / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(HAXSCRIPT),
                 "-cp", str(scratch), "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_contract_keeps_source_callbacks_and_single_owner_lease_wiring(self):
        services = (ROOT / "source/PsychStandardServices.hx").read_text(encoding="utf-8")
        self.assertIn("new SourceDiscordPresenceLease()", services)
        self.assertIn("new PsychDiscordClient(rpc, function() return !owner.released)", services)
        self.assertIn("PsychDiscordBindings.installLua(interp, owner.discord)", services)
        self.assertIn("PsychDiscordBindings.install(evaluator, owner.discord)", services)
        self.assertIn("PsychDiscordBindings.installScope(scope, owner.discord)", services)
        source = (ROOT / "source/PsychDiscordBindings.hx").read_text(encoding="utf-8")
        self.assertIn("changeDiscordPresence", source)
        self.assertIn("changeDiscordClientID", source)
        self.assertIn("backend.DiscordClient", source)
        self.assertIn("DEFAULT_CLIENT_ID:String = '863222024192262205'", (ROOT / "source/PsychDiscordClient.hx").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
