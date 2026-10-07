"""Focused ownership and daemon-state contracts for Psych Discord leases."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, TEST_TMP, FixturePath

ROOT = Path(__file__).resolve().parents[2]


FIXTURE = r'''
import Discord.DiscordClient;
import Discord.DiscordPresenceSnapshot;
import Discord.DiscordRpcLifecycle;
import SourceDiscordPresenceLease;

class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function details(snapshot:DiscordPresenceSnapshot):Dynamic
  return snapshot.hasPresence ? Reflect.field(snapshot.presence, 'details') : null;
 static function main():Void {
  var initial = DiscordClient.getRequestedSnapshot();
  check(initial.clientId == DiscordClient.NATIVE_CLIENT_ID && !initial.hasPresence,
   'the shared service exposes an initial detached snapshot before startup');

  var menu:Dynamic={details:'Cammie Engine | In the Menus', state:null,
   largeImageKey:'icon', largeImageText:'Cammie Engine'};
  var readyEvents:Array<String>=[];
  var readyLifecycle=new DiscordRpcLifecycle(initial.clientId,
   function(id)readyEvents.push('start:'+id),function(){},function(){},
   function(value)readyEvents.push('publish:'+Reflect.field(value,'details')),
   function()readyEvents.push('clear'));
  readyLifecycle.seedRequestedState(initial);
  var capturedReady=DiscordClient.captureReadyPresence(menu);
  readyLifecycle.seedRequestedPresence(capturedReady);
  readyLifecycle.initialize();
  readyLifecycle.onReady(menu);
  check(details(capturedReady)=='Cammie Engine | In the Menus'
   && capturedReady.presenceRevision>initial.presenceRevision
   && readyEvents.join('|')=='start:'+initial.clientId+'|publish:Cammie Engine | In the Menus',
   'a real ready fallback becomes the shared requested presence and daemon baseline');
  var readyLease=new SourceDiscordPresenceLease();
  readyLease.publish({details:'temporary-after-ready'});
  readyLease.release();
  check(details(DiscordClient.getRequestedSnapshot())=='Cammie Engine | In the Menus',
   'a lease created after SDK readiness restores the actual menu baseline');
  DiscordClient.clearPresenceAndGetSnapshot();
  initial=DiscordClient.getRequestedSnapshot();
  check(!initial.hasPresence && initial.explicitlyCleared,
   'the following lease cases begin from explicit absence');

  var lease = new SourceDiscordPresenceLease();
  lease.setClientId('psych-owner-id');
  var requested:Dynamic = {details:'leased', state:'gameplay', largeImageKey:'large',
   smallImageKey:'small', startTimestamp:12, nested:{mutable:true}};
  lease.publish(requested);
  Reflect.setField(requested, 'details', 'mutated-after-publish');
  Reflect.setField(Reflect.field(requested, 'nested'), 'mutable', false);
  var stored = DiscordClient.getRequestedSnapshot();
  check(stored.clientId == 'psych-owner-id' && stored.hasPresence && details(stored) == 'leased',
   'the lease retains pre-initialization identity and presence');
  check(!Reflect.hasField(stored.presence, 'nested'),
   'RPC marshalling copies only scalar rich-presence fields');
  Reflect.setField(stored.presence, 'details', 'mutated-snapshot');
  check(details(DiscordClient.getRequestedSnapshot()) == 'leased',
   'snapshot callers cannot mutate the retained request');
  var ownedPresenceRevision = stored.presenceRevision;
  lease.release();
  var restored = DiscordClient.getRequestedSnapshot();
  check(restored.clientId == initial.clientId && restored.identityRevision > initial.identityRevision,
   'lease release restores the identity while its revision is still owned');
  check(!restored.hasPresence && restored.explicitlyCleared
   && restored.presenceRevision > ownedPresenceRevision,
   'restoring an absent snapshot explicitly clears stale activity instead of inventing a menu default');

  var contested = new SourceDiscordPresenceLease();
  contested.setClientId('lease-id');
  contested.publish({details:'lease-presence'});
  DiscordClient.setClientId('external-id');
  DiscordClient.changePresence('external-presence', null);
  var external = DiscordClient.getRequestedSnapshot();
  contested.release();
  var afterContest = DiscordClient.getRequestedSnapshot();
  check(afterContest.clientId == external.clientId && details(afterContest) == 'Cammie Engine | external-presence',
   'external writes to either owned dimension survive lease release');

  var identityConflict = new SourceDiscordPresenceLease();
  var baseline = DiscordClient.getRequestedSnapshot();
  identityConflict.publish({details:'temporary-presence'});
  DiscordClient.setClientId('external-id-after-lease');
  identityConflict.release();
  var afterIdentityConflict = DiscordClient.getRequestedSnapshot();
  check(afterIdentityConflict.clientId == 'external-id-after-lease'
   && details(afterIdentityConflict) == details(baseline),
   'an external identity update survives while the still-owned presence restores independently');

  var presenceConflict = new SourceDiscordPresenceLease();
  presenceConflict.setClientId('temporary-owner-id');
  presenceConflict.publish({details:'temporary-presence-2'});
  DiscordClient.changePresence('external-presence-2', null);
  var externalPresence = DiscordClient.getRequestedSnapshot();
  presenceConflict.release();
  var afterPresenceConflict = DiscordClient.getRequestedSnapshot();
  check(afterPresenceConflict.clientId == 'external-id-after-lease'
   && details(afterPresenceConflict) == details(externalPresence),
   'an external presence update survives while the still-owned identity restores independently');

  var sameIdentityAssignment=new SourceDiscordPresenceLease();
  DiscordClient.setClientId('external-same-id');
  sameIdentityAssignment.setClientId('external-same-id');
  sameIdentityAssignment.release();
  check(DiscordClient.getClientId()=='external-same-id',
   'a no-op lease assignment does not adopt another owner’s identity revision');

  DiscordClient.clearPresenceAndGetSnapshot();
  var pendingLease=new SourceDiscordPresenceLease();
  pendingLease.publish({details:'pending-before-ready'});
  var pendingReady=DiscordClient.captureReadyPresence(menu);
  var pendingEvents:Array<String>=[];
  var pendingLifecycle=new DiscordRpcLifecycle('startup-id',function(id)pendingEvents.push('start:'+id),
   function(){},function(){},function(value)pendingEvents.push('publish:'+Reflect.field(value,'details')),
   function()pendingEvents.push('clear'));
  pendingLifecycle.seedRequestedPresence(pendingReady);
  pendingLifecycle.initialize();
  pendingLifecycle.onReady(menu);
  check(details(pendingReady)=='pending-before-ready'
   && pendingEvents.join('|')=='start:startup-id|publish:pending-before-ready',
   'ready replays a source presence queued before SDK readiness');
  pendingLease.release();

  var absent=DiscordClient.clearPresenceAndGetSnapshot();
  var revisionAtClear=absent.presenceRevision;
  var explicitlyAbsentReady=DiscordClient.captureReadyPresence(menu);
  var absentEvents:Array<String>=[];
  var absentLifecycle=new DiscordRpcLifecycle('id',function(id)absentEvents.push('start:'+id),
   function(){},function(){},function(value)absentEvents.push('publish:'+Reflect.field(value,'details')),
   function()absentEvents.push('clear'));
  absentLifecycle.seedRequestedPresence(explicitlyAbsentReady);
  absentLifecycle.initialize();
  absentLifecycle.onReady(menu);
  check(!explicitlyAbsentReady.hasPresence && explicitlyAbsentReady.explicitlyCleared
   && explicitlyAbsentReady.presenceRevision==revisionAtClear
   && absentEvents.join('|')=='start:id|clear',
   'ready after explicit clear remains absent and clears the daemon');

  var queuedIdentity=DiscordClient.setClientIdAndGetSnapshot('queued-id');
  var queuedEvents:Array<String>=[];
  var queuedLifecycle=new DiscordRpcLifecycle('startup-id',function(id)queuedEvents.push('start:'+id),
   function(){},function()queuedEvents.push('shutdown'),function(value)queuedEvents.push('publish'),
   function()queuedEvents.push('clear'));
  var startupState:DiscordPresenceSnapshot={presence:null,hasPresence:false,explicitlyCleared:true,
   clientId:'startup-id',presenceRevision:0,identityRevision:0};
  queuedLifecycle.seedRequestedState(startupState);
  queuedLifecycle.seedRequestedPresence(DiscordClient.captureReadyPresence(menu));
  queuedLifecycle.initialize();
  queuedLifecycle.onReady(menu);
  queuedLifecycle.dispatch({kind:'clientId',value:queuedIdentity.clientId});
  check(queuedEvents.join('|')=='start:startup-id|clear|shutdown|start:queued-id|clear',
   'ready-time presence seeding does not consume a queued identity restart');
 }
}
'''


class SourceDiscordPresenceLeaseTest(unittest.TestCase):
    def test_owner_snapshot_compare_restore_and_explicit_clear(self):
        if not (ROOT / ".tools/haxe/haxe.exe").is_file():
            self.skipTest("portable Haxe interpreter is unavailable")
        TEST_TMP.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="source-discord-lease-", dir=TEST_TMP) as folder:
            scratch = FixturePath(folder)
            (scratch / "Main.hx").write_text(FIXTURE, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
