"""Pin the shared, owner-scoped importer availability rules used by Freeplay."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath, haxe_command
from test_source_event_preparation import extract_method


ROOT = FixturePath(__file__).resolve().parents[2]


class FreeplaySongAvailabilityTest(unittest.TestCase):
    def test_owner_chart_and_provisional_decisions(self):
        if not (ROOT / '.tools/haxe/haxe.exe').is_file() and not (ROOT / '.tools/haxe/haxe').is_file():
            self.skipTest('portable Haxe interpreter is unavailable')

        main = r'''import ImportRefreshAvailabilitySnapshot.ImportRefreshAvailabilitySnapshot;
import ImportRefreshAvailabilitySnapshot.ImportRefreshPendingSong;
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main():Void {
  check(!FreeplaySongAvailability.songListNeedsRegistryRefresh(false,4,7,7),
   'a same-generation selected category list can be retained');
  check(FreeplaySongAvailability.songListNeedsRegistryRefresh(false,4,7,8),
   'a list selected before a background handoff must reload when Freeplay is recreated');
  check(FreeplaySongAvailability.songListNeedsRegistryRefresh(false,0,8,8),
   'an explicitly cleared category list must repopulate from the registry');
  check(FreeplaySongAvailability.songListNeedsRegistryRefresh(true,4,8,8),
   'direct imported-package Freeplay must reselect from its owner registry');
  var owner='assets/imported_mods/alpha';
  var other='assets/imported_mods/beta';
  var empty:ImportRefreshAvailabilitySnapshot={revision:1,inspectionPending:true,
   pendingOwnerRoots:[],handoffPendingOwnerRoots:[],committedOwnerRoots:[],
   pendingTouchedPaths:[],pendingSongs:[]};
  check(FreeplaySongAvailability.ownerReadiness(empty,'').ready,
   'base-game owner must stay available during receipt inspection');
  check(FreeplaySongAvailability.canPresentPendingSongs('Imported',false),
   'provisional rows must be visible in the canonical Imported category');
  check(FreeplaySongAvailability.canPresentPendingSongs('All',false)
   && FreeplaySongAvailability.canPresentPendingSongs('',false),
   'provisional rows remain visible in unscoped master lists');
  check(!FreeplaySongAvailability.canPresentPendingSongs('Base Game',false),
   'provisional rows must not leak into unrelated authored categories');
  check(FreeplaySongAvailability.canPresentPendingSongs('Base Game',true),
   'explicit package Freeplay remains owner-scoped');
#if windows
  check(FreeplaySongAvailability.normalizePath('A/B')=='a/b',
   'Windows path comparisons should be case-insensitive');
#else
  check(FreeplaySongAvailability.normalizePath('A/B')=='A/B',
   'case-sensitive targets must preserve path case');
#end
  var unknown=FreeplaySongAvailability.ownerReadiness(empty,owner);
  check(!unknown.ready && unknown.state=='checking',
   'unknown imported owner must wait for first receipt inspection');

  var snapshot:ImportRefreshAvailabilitySnapshot={revision:2,inspectionPending:false,
   pendingOwnerRoots:[owner],handoffPendingOwnerRoots:[],committedOwnerRoots:[owner,other],
   pendingTouchedPaths:['assets/data/shared/shared-hard.json','assets/data/shared/events.json'],
   pendingSongs:[]};
  var pending=FreeplaySongAvailability.ownerReadiness(snapshot,'assets\\imported_mods\\alpha');
  check(!pending.ready && pending.state=='pending' && pending.reason.indexOf('recovery')>=0,
   'path spelling must normalize and a reserved package must have an explicit pending reason');
  check(FreeplaySongAvailability.ownerReadiness(snapshot,other).ready,
   'an unrelated committed package remains playable while another owner refreshes');
  check(FreeplaySongAvailability.songReadiness(snapshot,other,true).ready,
   'unrelated committed song with a chart remains playable');
  var missing=FreeplaySongAvailability.songReadiness(snapshot,other,false);
  check(!missing.ready && missing.state=='missing-chart',
   'a committed owner with no selected chart must remain unavailable');
  var overlap=FreeplaySongAvailability.songReadiness(snapshot,other,true,'assets/data/shared');
  check(!overlap.ready && overlap.state=='overlap',
   'shared output touching a song data directory must block that song');
  check(!FreeplaySongAvailability.touchesPath(snapshot,'assets/data/share'),
   'a sibling prefix must not count as a touched song directory');
  var provisional=FreeplaySongAvailability.songReadiness(snapshot,other,true,null,true);
  check(!provisional.ready && provisional.state=='provisional'
   && provisional.reason.indexOf('until the package is committed')>=0,
   'provisional scan rows must stay visibly unplayable');

  snapshot.handoffPendingOwnerRoots=[owner];
  snapshot.pendingOwnerRoots=[];
  var handoff=FreeplaySongAvailability.ownerReadiness(snapshot,owner);
  check(!handoff.ready && handoff.state=='handoff',
   'a published package remains unavailable until main-thread handoff finishes');
  snapshot.handoffPendingOwnerRoots=[];
  check(FreeplaySongAvailability.ownerReadiness(snapshot,owner).ready,
   'a safely completed or failed refresh releases the reservation');
  check(!FreeplaySongAvailability.ownerReadiness(null,owner).ready,
   'an absent snapshot cannot prove an imported package ready');
  snapshot.pendingOwnerRoots=[other];
  check(!FreeplaySongAvailability.ownerReadiness(snapshot,'assets/imported_mods/unknown').ready,
   'an unchecked owner must stay locked during another queued refresh');
  check(FreeplaySongAvailability.ownerReadiness(snapshot,owner).ready,
   'a checked owner stays playable while another package refreshes');
  snapshot.pendingOwnerRoots=[];
  snapshot.inspectionPending=true;
  check(!FreeplaySongAvailability.ownerReadiness(snapshot,owner).ready,
   'old committed receipts cannot bypass a new inspection');
  snapshot.committedOwnerRoots=[];
  check(!FreeplaySongAvailability.ownerReadiness(snapshot,owner).ready,
   'unvalidated import owners remain gated during inspection');
  snapshot.inspectionPending=false;
  check(FreeplaySongAvailability.ownerReadiness(snapshot,owner).ready,
   'legacy unmanaged owner falls back after inspection completes');

  snapshot.pendingOwnerRoots=[other];
  snapshot.refreshInProgress=true;
  check(!FreeplaySongAvailability.ownerReadiness(snapshot,owner).ready,
   'unmanaged imports stay locked while active refresh work remains');
  snapshot.refreshInProgress=false;
  check(FreeplaySongAvailability.ownerReadiness(snapshot,owner).ready,
   'a stopped unrelated failure must not permanently gate a legacy import');
  check(!FreeplaySongAvailability.ownerReadiness(snapshot,other).ready,
   'the failed owner remains reserved when its work has stopped');
  check(!FreeplaySongAvailability.songReadiness(snapshot,owner,false).ready,
   'stopped work must not make a missing chart playable');
  check(!FreeplaySongAvailability.songReadiness(snapshot,owner,true,'assets/data/shared').ready,
   'stopped work must preserve chart output overlap locks');
  snapshot.pendingOwnerRoots=[];

  var candidate:ImportRefreshPendingSong={key:'pending:one',name:'Chart',ownerRoot:owner,
   sourceRoot:'retained/source',sourceFolder:'Source Chart',destinationFolder:'Chart'};
  check(FreeplaySongAvailability.matchesInstalledDestination(candidate,owner,'Chart'),
   'authoritative destination should match the installed row within its owner');
#if windows
  check(FreeplaySongAvailability.matchesInstalledDestination(candidate,owner,'chart'),
   'Windows destination folder matching should ignore case');
  check(FreeplaySongAvailability.matchesInstalledSource(candidate,owner,'source chart'),
   'Windows source folder matching should ignore case');
#else
  check(!FreeplaySongAvailability.matchesInstalledDestination(candidate,owner,'chart'),
   'case-sensitive targets must not collapse distinct destination folder names');
  check(!FreeplaySongAvailability.matchesInstalledSource(candidate,owner,'source chart'),
   'case-sensitive targets must not collapse distinct source folder names');
#end
  check(!FreeplaySongAvailability.matchesInstalledDestination(candidate,other,'Chart'),
   'same destination under another owner is a legitimate homonym');
  check(FreeplaySongAvailability.matchesInstalledSource(candidate,owner,'Source Chart'),
   'source folder may dedupe only within the exact owner');
  check(!FreeplaySongAvailability.matchesInstalledSource(candidate,other,'Source Chart'),
   'source folder under another owner must remain a separate candidate');
  var sameDisplayDifferentFolder:ImportRefreshPendingSong={key:'pending:two',name:'Chart',
   ownerRoot:owner,sourceRoot:'retained/source',sourceFolder:'Different Folder'};
  check(!FreeplaySongAvailability.matchesInstalledSource(sameDisplayDifferentFolder,owner,'Source Chart'),
   'display name alone must not hide a distinct source folder');

  var touched=[' assets\\data\\shared\\one.json ', 'assets/data/shared-extra/a.json',
   'assets/data/shared/two.json', 'assets/data/shared/two.json', '', null];
  var index=new ImportRefreshAvailabilitySnapshot.ImportRefreshPathIndex(touched);
  snapshot.pendingTouchedPaths=touched.copy();snapshot.pendingPathIndex=null;
  var queries=['assets/data/shared','assets/data/share','assets/data/shared/one.json',
   'assets/data/shared/one.json/child','assets/data/shared-extra','assets/data','',null];
  for (i in 0...200) {
   touched.push('assets/data/song'+i+'/chart.json');
   queries.push('assets/data/song'+i);queries.push('assets/data/song'+i+'-sibling');
  }
  check(!index.touches('assets/data/song0'),'index detaches constructor input');
  snapshot.pendingTouchedPaths=touched.copy();index=new ImportRefreshAvailabilitySnapshot.ImportRefreshPathIndex(touched);
  for(scope in queries) {
   snapshot.pendingPathIndex=null;var linear=FreeplaySongAvailability.touchesPath(snapshot,scope);
   snapshot.pendingPathIndex=index;
   check(FreeplaySongAvailability.touchesPath(snapshot,scope)==linear,'indexed overlap matches linear: '+scope);
  }
  check(index.touches('assets/data/shared'),'sibling sort order cannot hide descendants');
  // Case folding and trimming can reorder an otherwise sorted input array.
  var variants=[['Z/last/file', 'a/first/file'],[' a/middle/file ', 'A/first/file','z/end/file'],
   ['root/file','root/file','root/file/child','root-extra/file'],
   ['unicode/\u00c9/file','unicode/\u00e9/file','unicode/\u03a9/file']];
  for(paths in variants) {
   for(reverse in [false,true]) {
    if(reverse)paths.reverse();
    snapshot.pendingTouchedPaths=paths;
    var orderedIndex=new ImportRefreshAvailabilitySnapshot.ImportRefreshPathIndex(paths);
    var scopes=['Z','z','a','A','a/first','a/middle','root','root-extra','root/file',
     'root/file/child','root/file/child/missing','unicode/\u00c9','unicode/\u00e9','unicode/\u03a9'];
    for(scope in scopes) {
     snapshot.pendingPathIndex=null;var expected=FreeplaySongAvailability.touchesPath(snapshot,scope);
     snapshot.pendingPathIndex=orderedIndex;
     check(FreeplaySongAvailability.touchesPath(snapshot,scope)==expected,'normalized input order: '+scope);
    }
   }
  }
  check(!new ImportRefreshAvailabilitySnapshot.ImportRefreshPathIndex(null).touches('anything'),
   'absent input has no overlaps');
  var newer=new ImportRefreshAvailabilitySnapshot.ImportRefreshPathIndex(['assets/data/replacement/a.json']);
  check(index.touches('assets/data/shared')&&!newer.touches('assets/data/shared')&&newer.touches('assets/data/replacement'),
   'a later revision does not mutate an old index');

  Sys.println('freeplay-song-availability-ok');
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            temp_path = FixturePath(temp)
            (temp_path / 'Main.hx').write_text(main, newline='\n')
            for windows in [False, True]:
                result = subprocess.run(
                    [*haxe_command(windows=windows), '-cp', str(ROOT / 'source'), '-cp', str(temp_path),
                     '-main', 'Main', '--interp'],
                    cwd=ROOT, capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('freeplay-song-availability-ok', result.stdout)

    def test_freeplay_uses_revisioned_snapshot_and_rechecks_interactions(self):
        source = (ROOT / 'source/FreeplayState.hx').read_text()
        self.assertIn('ImportRefreshManager.availabilityRevision()', source)
        self.assertIn('ImportRefreshManager.availabilitySnapshot()', source)
        self.assertIn('currentSongListGeneration', source)
        self.assertIn('songListNeedsRegistryRefresh(', source)
        self.assertIn('ImportRefreshManager.requestAvailabilityRecheck();', source)
        self.assertIn('FreeplaySongAvailability.ownerReadiness(', source)
        self.assertIn('FreeplaySongAvailability.songReadiness(', source)
        self.assertNotIn('if (ImportRefreshManager.browseTick().busy) { super.update(elapsed); return; }', source)
        for marker in [
            'function hxcLaunchCurrentSelection()',
            'function startPreview()',
            'if (accepted)',
        ]:
            self.assertIn(marker, source)
        self.assertIn('availabilityAllowsSelection(', source)
        self.assertIn('pendingKey', source)
        self.assertIn('rowAvailabilityReason', source)
        self.assertIn('hxcCapsuleView(index)', source)
        self.assertIn('returnFromEmptySongList();', source)
        self.assertIn('changeSelection(0, true);', source)
        self.assertIn('if (infoPanel == null)', source)
        self.assertIn('FreeplaySongAvailability.canPresentPendingSongs(curCategory, directOwnerRoot != \'\')', source)

    def test_interaction_snapshot_is_reconciled_on_the_following_update(self):
        source = (ROOT / 'source/FreeplayState.hx').read_text(encoding='utf-8')
        refresh = extract_method(source, 'function refreshImportAvailability(')
        interaction = extract_method(source, 'function refreshAvailabilityForInteraction():Void')
        refresh = refresh.replace('function refreshImportAvailability(', 'public function refreshImportAvailability(', 1)
        interaction = interaction.replace('function refreshAvailabilityForInteraction()',
                                          'public function refreshAvailabilityForInteraction()', 1)
        main = r'''class ImportRefreshManager {
  public static var revision:Int = 1;
  public static var snapshot:Dynamic = {revision:1,pendingSongs:[]};
  public static function availabilityRevision():Int return revision;
  public static function availabilitySnapshot():Dynamic return snapshot;
}
class FreeplayHarness {
  var libraryOrderKey:String = "";
  public var importAvailability:Dynamic;
  public var importAvailabilityRevision:Int = -1;
  public var importAvailabilityAppliedRevision:Int = -1;
  public var songs:Array<Dynamic> = [{isProvisional:false,pendingKey:'',availabilityRevision:-1,chartRevision:-1}];
  public var rowSongIndices:Array<Int> = [0];
  public var grpSongs:Dynamic = {};
  public var curSelected:Int = 0;
  public var previewSound:Dynamic;
  public var reconciles:Int = 0;
  public var rendered:Int = 0;
  public var renderedRevision:Int = -1;
  public function new() {}
  function reconcilePendingSongs():Bool { reconciles++; return false; }
  function rebuildVisibleRows():Void {}
  function rebuildIconQueue():Void {}
  function updateRenderedRowAvailability(index:Int):Void {
    rendered++;
    renderedRevision = importAvailabilityRevision;
  }
  function availabilityAllowsSelection(index:Int):Bool return true;
  function stopPreviewSound():Void {}
  function returnFromEmptySongList():Void {}
  function indexForPendingKey(key:String):Int return -1;
  function changeSelection(amount:Int, force:Bool=false):Void {}
''' + refresh + '\n' + interaction + r'''
}
class Main {
  static function check(value:Bool,message:String):Void if(!value) throw message;
  static function main():Void {
    var state=new FreeplayHarness();
    check(state.refreshImportAvailability(true),'initial snapshot was not applied');
    check(state.importAvailabilityRevision==1 && state.importAvailabilityAppliedRevision==1
      && state.renderedRevision==1,'initial UI revision was not reconciled');
    var reconcilesBefore=state.reconciles;
    var renderedBefore=state.rendered;
    ImportRefreshManager.revision=2;
    ImportRefreshManager.snapshot={revision:2,pendingSongs:[{key:'pending:new'}]};
    state.refreshAvailabilityForInteraction();
    check(state.importAvailabilityRevision==2 && state.importAvailabilityAppliedRevision==1,
      'interaction should consume the new snapshot without claiming the UI applied it');
    check(state.reconciles==reconcilesBefore && state.rendered==renderedBefore,
      'interaction path mutated or rebuilt the song rows');
    check(state.refreshImportAvailability(false),
      'next browse update skipped a snapshot already consumed by an interaction');
    check(state.reconciles==reconcilesBefore+1 && state.rendered==renderedBefore+1
      && state.renderedRevision==2 && state.importAvailabilityAppliedRevision==2,
      'pending rows or rendered availability were not reconciled to the consumed revision');
  }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
            work = FixturePath(directory)
            (work / 'Main.hx').write_text(main, encoding='utf-8', newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, '-cp', str(work), '-main', 'Main', '--interp'],
                cwd=work, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_import_back_detaches_manual_import_but_stops_scan(self):
        source = (ROOT / 'source/ImportSettingsState.hx').read_text()
        self.assertIn('if (backPressed && importJob != null)', source)
        self.assertIn('detachImportAndLeave();', source)
        self.assertIn('if (backPressed && scanJob != null)', source)
        self.assertIn('if (!hasCancelableWorker())', source)
        self.assertIn('importJob = null;', source)
        self.assertIn('ImportRefreshManager owns', source)
        self.assertIn('Back hides this screen; Cancel requests a safe stop.', source)


if __name__ == '__main__':
    unittest.main()
