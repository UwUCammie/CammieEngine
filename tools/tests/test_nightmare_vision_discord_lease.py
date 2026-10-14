"""Nightmare Vision script presence goes through the shared owner lease."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''
import Discord.DiscordClient;
import Discord.DiscordPresenceSnapshot;
import SourceDiscordPresenceLease;

/** Stands in for the shared daemon: two independently versioned parts. */
class FakeDaemon {
 public var presence:Dynamic = {details:'engine menu'};
 public var hasPresence:Bool = true;
 public var clientId:String = 'engine-id';
 public var presenceRevision:Int = 1;
 public var identityRevision:Int = 1;
 public function new() {}
 public function snapshot():DiscordPresenceSnapshot return {presence:presence, hasPresence:hasPresence,
  explicitlyCleared:!hasPresence, clientId:clientId, presenceRevision:presenceRevision, identityRevision:identityRevision};
 public function driver():SourceDiscordPresenceLeaseDriver return {
  snapshot:snapshot,
  setClientId:function(value) { if (value != clientId) { clientId = value; identityRevision++; } return snapshot(); },
  publish:function(value) { presence = value; hasPresence = true; presenceRevision++; return snapshot(); },
  clear:function() { presence = null; hasPresence = false; presenceRevision++; return snapshot(); },
  restorePresence:function(revision, saved) {
   if (revision != presenceRevision) return false;
   presence = saved.presence; hasPresence = saved.hasPresence; presenceRevision++; return true;
  },
  restoreClientId:function(revision, value) {
   if (revision != identityRevision) return false;
   clientId = value; identityRevision++; return true;
  }
 };
}

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function throwsReleased(run:Void->Void):Bool {
  try run() catch (error:Dynamic) return Std.string(error).indexOf('Released imported owner') >= 0;
  return false;
 }

 static function main():Void {
  // One timestamp rule for every Psych-family facade.
  var timed = SourceDiscordPresenceLease.sourcePresence('d', 's', 'small', true, 5000, 'large', 'text', 20000);
  check(timed.startTimestamp == 20 && timed.endTimestamp == 25, 'an end time is a duration counted from the start');
  var untimed = SourceDiscordPresenceLease.sourcePresence('d', null, null, false, 5000, 'large', 'text', 20000);
  check(untimed.startTimestamp == 0 && untimed.endTimestamp == 5, 'no start means the duration counts from zero');
  var open = SourceDiscordPresenceLease.sourcePresence('d', null, null, true, null, 'large', 'text', 20000);
  check(open.startTimestamp == 20 && open.endTimestamp == 0, 'a missing end stays unset');
  check(timed.details == 'd' && timed.state == 's' && timed.smallImageKey == 'small'
   && timed.largeImageKey == 'large' && timed.largeImageText == 'text', 'presence fields were moved around');

  // Both facades publish the same times for the same call.
  var psychDaemon = new FakeDaemon();
  var psych = new PsychDiscordClient(new SourceDiscordPresenceLease(psychDaemon.driver()));
  var daemon = new FakeDaemon();
  var lease = new SourceDiscordPresenceLease(daemon.driver());
  var facade = NightmareVisionDiscordClient.leased(lease);
  psych.changePresence('Playing', 'Song', 'small', false, 90000, 'cover');
  facade.changePresence('Playing', 'Song', 'small', false, 90000, 'cover');
  check(daemon.presence.startTimestamp == psychDaemon.presence.startTimestamp
   && daemon.presence.endTimestamp == psychDaemon.presence.endTimestamp && daemon.presence.endTimestamp == 90,
   'the two facades disagree about timestamps');
  check(daemon.presence.smallImageKey == 'small' && daemon.presence.largeImageKey == 'cover'
   && daemon.presence.state == 'Song', 'image keys or state were dropped');
  check(daemon.presence.details == 'Cammie Engine | Playing' && daemon.presence.largeImageText == 'Cammie Engine',
   'engine branding of the presence changed');
  facade.changePresence('Timed', null, null, true, 1000);
  check(daemon.presence.startTimestamp > 0 && daemon.presence.endTimestamp - daemon.presence.startTimestamp <= 1
   && daemon.presence.endTimestamp >= daemon.presence.startTimestamp && daemon.presence.largeImageKey == 'icon',
   'a live start time or the default image was lost');

  // The client id goes through the lease as well.
  check(facade.rpcId == 'engine-id', 'rpcId does not read the shared identity');
  facade.rpcId = 'mod-id';
  check(daemon.clientId == 'mod-id' && facade.rpcId == 'mod-id', 'rpcId does not write the shared identity');
  facade.rpcId = null;
  check(daemon.clientId == 'mod-id', 'a null rpcId changed the identity');

  // Leaving the owner puts back what the engine had.
  lease.release();
  check(daemon.clientId == 'engine-id', 'the engine client id was not restored');
  check(daemon.hasPresence && daemon.presence.details == 'engine menu', 'the engine presence was not restored');
  check(throwsReleased(function() facade.changePresence('late')) && throwsReleased(function() facade.rpcId = 'late')
   && throwsReleased(function() return facade.rpcId), 'a released facade kept working');
  check(daemon.clientId == 'engine-id' && daemon.presence.details == 'engine menu', 'a released facade still wrote');

  // Something else wrote after the owner did: release leaves it alone.
  var busy = new FakeDaemon();
  var busyLease = new SourceDiscordPresenceLease(busy.driver());
  var busyFacade = NightmareVisionDiscordClient.leased(busyLease);
  busyFacade.rpcId = 'mod-id';
  busyFacade.changePresence('Playing');
  busy.presence = {details:'engine results'}; busy.presenceRevision++;
  busy.clientId = 'other-id'; busy.identityRevision++;
  busyLease.release();
  check(busy.presence.details == 'engine results', 'release overwrote a later presence');
  check(busy.clientId == 'other-id', 'release overwrote a later client id');

  // An owner guard retires a facade without touching the lease.
  var alive = true;
  var guardedLease = new SourceDiscordPresenceLease(new FakeDaemon().driver());
  var guarded = NightmareVisionDiscordClient.leased(guardedLease, function() return alive);
  guarded.changePresence('ok');
  alive = false;
  check(throwsReleased(function() guarded.changePresence('late')) && !guardedLease.isReleased(),
   'the owner guard did not retire only its facade');

  // Owner facades share one lease over the real service and hand it back.
  var engineId = DiscordClient.getClientId();
  DiscordClient.publishPresenceAndGetSnapshot({details:'engine menu'});
  var first = NightmareVisionDiscordClient.forOwner('assets/imported_mods/owner-a');
  var second = NightmareVisionDiscordClient.forOwner('assets\\imported_mods\\owner-a/');
  first.rpcId = 'owner-a-id';
  second.changePresence('Playing', 'Song');
  check(second.rpcId == 'owner-a-id' && DiscordClient.getClientId() == 'owner-a-id', 'owner facades do not share state');
  check(DiscordClient.getRequestedSnapshot().presence.details == 'Cammie Engine | Playing', 'owner presence was not published');
  NightmareVisionDiscordClient.releaseOwner('assets/imported_mods/owner-a');
  check(DiscordClient.getClientId() == 'owner-a-id', 'keeping the same owner released its lease');
  var other = NightmareVisionDiscordClient.forOwner('assets/imported_mods/owner-b');
  check(DiscordClient.getClientId() == engineId, 'switching owner did not restore the engine client id');
  check(DiscordClient.getRequestedSnapshot().presence.details == 'engine menu', 'switching owner did not restore the engine presence');
  other.changePresence('Other');
  check(throwsReleased(function() first.changePresence('stale')), 'a replaced owner kept publishing');
  NightmareVisionDiscordClient.releaseOwner();
  check(DiscordClient.getRequestedSnapshot().presence.details == 'engine menu', 'leaving every owner did not restore the engine presence');
  NightmareVisionDiscordClient.releaseOwner();

  // A facade that outlives its released owner must not take a new lease.
  check(throwsReleased(function() other.changePresence('late')) && throwsReleased(function() other.rpcId = 'late-id')
   && throwsReleased(function() return other.rpcId), 'a released owner facade kept working');
  check(DiscordClient.getClientId() == engineId
   && DiscordClient.getRequestedSnapshot().presence.details == 'engine menu', 'a released owner facade still wrote');

  // Released before it ever wrote anything: still retired, and nothing to restore.
  var idle = NightmareVisionDiscordClient.forOwner('assets/imported_mods/owner-c');
  NightmareVisionDiscordClient.releaseOwner();
  check(throwsReleased(function() idle.rpcId = 'idle-id') && DiscordClient.getClientId() == engineId,
   'a facade released before its first write came back');

  // The same owner coming back gets a working facade and a fresh lease.
  var again = NightmareVisionDiscordClient.forOwner('assets/imported_mods/owner-c');
  again.rpcId = 'owner-c-id';
  check(DiscordClient.getClientId() == 'owner-c-id' && throwsReleased(function() idle.changePresence('stale')),
   'a returning owner was mixed up with its retired facade');
  NightmareVisionDiscordClient.releaseOwner('assets/imported_mods/owner-c');
  check(again.rpcId == 'owner-c-id', 'keeping the current owner retired its facade');
  NightmareVisionDiscordClient.releaseOwner();
  check(DiscordClient.getClientId() == engineId, 'the returning owner did not hand the client id back');
 }
}
'''


class NightmareVisionDiscordLeaseTest(unittest.TestCase):
    def test_script_presence_and_client_id_are_restored_through_the_shared_lease(self):
        with tempfile.TemporaryDirectory(prefix='nmv-discord-lease-', dir=ROOT / 'tmp') as folder:
            scratch = FixturePath(folder)
            (scratch / 'Main.hx').write_text(FIXTURE, encoding='utf-8', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(scratch), '--main', 'Main', '--interp'],
                cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gameplay_scripts_get_the_leased_facade(self):
        source = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
        self.assertIn('NightmareVisionDiscordClient.forOwner(paths.root)', source)
        self.assertIn('NightmareVisionDiscordClient.releaseOwner(root);', source)
        entry = (ROOT / 'source/ImportedMenuEntry.hx').read_text(encoding='utf-8')
        self.assertIn('NightmareVisionDiscordClient.releaseOwner();', entry)


if __name__ == '__main__':
    unittest.main()
