"""The shared Discord daemon owns source-requested application identities."""

from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath


ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools" / "haxe" / "haxe"


class SourceDiscordIdentityTest(unittest.TestCase):
    def test_lifecycle_order_presence_replay_restore_and_facade_callbacks(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe interpreter is unavailable")

        fixture = r'''
import Discord.DiscordClient;
import Discord.DiscordRpcCommand;
import Discord.DiscordRpcLifecycle;
import NightmareVisionDiscordClient;

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function last(values:Array<String>, count:Int):Array<String>
  return values.slice(values.length - count);
 static function drain(service:DiscordRpcLifecycle, queue:Array<DiscordRpcCommand>):Void {
  while (queue.length > 0) service.dispatch(queue.shift());
 }

 static function main():Void {
  check(DiscordClient.getClientId() == DiscordClient.NATIVE_CLIENT_ID,
   'native client identity is the shared service default');
  DiscordClient.setClientId('temporary-id');
  check(DiscordClient.getClientId() == 'temporary-id',
   'requested identity is observable before daemon startup');
  DiscordClient.setClientId(DiscordClient.NATIVE_CLIENT_ID);

  var events:Array<String> = [];
  var service = new DiscordRpcLifecycle(DiscordClient.NATIVE_CLIENT_ID,
   function(id:String) events.push('start:' + id),
   function() events.push('process'),
   function() events.push('shutdown'),
   function(presence:Dynamic) events.push('presence:' + Reflect.field(presence, 'details')));
  service.initialize();
  service.onReady({details: 'menu'});
  var queue:Array<DiscordRpcCommand> = [];
  queue.push({kind: 'presence', value: {details: 'playing'}});
  drain(service, queue);
  var beforeSameId = events.length;
  queue.push({kind: 'clientId', value: DiscordClient.NATIVE_CLIENT_ID});
  drain(service, queue);
  check(events.length == beforeSameId,
   'setting the active identity is a no-op');

  queue.push({kind: 'clientId', value: 'nightmare-vision-id'});
  drain(service, queue);
  check(last(events, 3).join('|') == 'shutdown|start:nightmare-vision-id|presence:playing',
   'identity change shuts down, starts the new client, then restores presence');
  service.onReady({details: 'menu-after-reconnect'});
  check(events[events.length - 1] == 'presence:playing',
   'ready callback retains the latest gameplay presence');

  queue.push({kind: 'clientId', value: DiscordClient.NATIVE_CLIENT_ID});
  drain(service, queue);
  check(last(events, 3).join('|') == 'shutdown|start:' + DiscordClient.NATIVE_CLIENT_ID + '|presence:playing',
   'restoring native identity uses the same ordered restart and replay');
  var shutdownAck = false;
  queue.push({kind: 'shutdown', value: null, complete: function() {
   shutdownAck = true;
   events.push('shutdown-ack');
  }});
  drain(service, queue);
  var beforeInactive = events.length;
  check(shutdownAck && last(events, 2).join('|') == 'shutdown|shutdown-ack',
   'shutdown completion callback runs after the SDK shutdown callback');
  service.process();
  queue.push({kind: 'clientId', value: 'pending-while-closed'});
  drain(service, queue);
  check(events.length == beforeInactive && events[events.length - 1] == 'shutdown-ack',
   'closed service does not process or restart until initialize is requested');
  queue.push({kind: 'initialize', value: 'pending-while-closed'});
  drain(service, queue);
  check(events[events.length - 1] == 'start:pending-while-closed',
   'initialize starts with the latest requested identity');

  var sharedId = DiscordClient.NATIVE_CLIENT_ID;
  var facadeEvents:Array<String> = [];
  var facade = new NightmareVisionDiscordClient(
   function(details, state, smallImageKey, hasStartTimestamp, endTimestamp, largeImageKey)
    facadeEvents.push('publish:' + details + ':' + largeImageKey),
   function() return sharedId,
   function(value:String) { sharedId = value; facadeEvents.push('identity:' + value); });
  check(facade.NMV_ID == '1252033037680513115',
   'source scripts can read the pinned Nightmare Vision application ID');
  check(facade.rpcId == DiscordClient.NATIVE_CLIENT_ID,
   'facade getter reads the shared native service identity');
  facade.rpcId = 'configured-mod-id';
  check(sharedId == 'configured-mod-id' && facade.rpcId == sharedId,
   'facade setter writes through to the shared service callback');
  facade.changePresence('In the Menus', null, 'small', false, null, 'large');
  check(facadeEvents.join('|') == 'identity:configured-mod-id|publish:In the Menus:large',
   'source presence publishes through the existing facade callback');

  var localFacade = new NightmareVisionDiscordClient(function(_, _, _, _, _, _) {});
  check(localFacade.rpcId == localFacade.NMV_ID,
   'standalone facade defaults to the source client ID');
  localFacade.rpcId = 'local-mod-id';
  check(localFacade.rpcId == 'local-mod-id',
   'standalone facade retains a locally assigned identity');
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="source-discord-identity-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_native_daemon_serializes_rpc_and_skips_native_smoke_startup(self):
        source = (ROOT / "source/Discord.hx").read_text(encoding="utf-8")
        self.assertIn("RuntimeSmokeHarness.enabled()", source)
        self.assertIn("rpcCommands.add({kind: 'clientId', value: value})", source)
        self.assertIn("rpcCommands.add({kind: 'presence', value: presence})", source)
        self.assertIn("rpcLifecycle.process();", source)
        self.assertIn("rpcLifecycle.dispatch(command);", source)
        self.assertIn("case 'clientId': setClientId(cast command.value)", source)
        self.assertIn("case 'presence': setPresence(command.value)", source)
        self.assertIn("case 'shutdown': shutdown()", source)
        self.assertIn("rpcLifecycle.onReady(fallback)", source)
        self.assertIn("rpcLifecycle.seedRequestedPresence(snapshot)", source)
        self.assertIn("captureReadyPresence(fallback)", source)
        self.assertIn("public static function getClientId():String", source)
        self.assertIn("public static function setClientId(value:String):Void", source)

    def test_native_branch_typechecks_with_fake_discord_driver(self):
        if not HAXE.is_file():
            self.skipTest("portable Haxe compiler is unavailable")

        discord_stub = r'''package discord_rpc;
typedef DiscordStartOptions = {
 var clientID:String;
 @:optional var onReady:Void->Void;
 @:optional var onDisconnected:Int->String->Void;
 @:optional var onError:Int->String->Void;
}
typedef DiscordPresenceOptions = {
 @:optional var details:String;
 @:optional var state:Null<String>;
 @:optional var startTimestamp:Int;
 @:optional var endTimestamp:Int;
 @:optional var largeImageKey:String;
 @:optional var largeImageText:String;
 @:optional var smallImageKey:Null<String>;
}
class DiscordRpc {
 public static function start(options:DiscordStartOptions):Void {}
 public static function process():Void {}
 public static function presence(options:DiscordPresenceOptions):Void {}
 public static function shutdown():Void {}
}
'''
        smoke_stub = r'''class RuntimeSmokeHarness {
 public static function enabled():Bool return false;
}
'''
        main = r'''import Discord.DiscordClient;
class Main {
 static function main():Void {
  DiscordClient.setClientId('test-client');
  DiscordClient.initialize();
  DiscordClient.changePresenceWithImages('test', null, null, false, null, 'icon');
  DiscordClient.shutdown();
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="source-discord-cpp-", dir=ROOT / "tmp") as folder:
            scratch = FixturePath(folder)
            (scratch / "discord_rpc").mkdir(parents=True)
            (scratch / "discord_rpc/DiscordRpc.hx").write_text(discord_stub, encoding="utf-8", newline="\n")
            (scratch / "RuntimeSmokeHarness.hx").write_text(smoke_stub, encoding="utf-8", newline="\n")
            (scratch / "Main.hx").write_text(main, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "-cpp", str(scratch / "cpp"), "--no-output", "--main", "Main"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
