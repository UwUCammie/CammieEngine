"""Fresh-process regeneration of a partitioned retained import."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
from test_import_installed_ownership import FIXTURE
from test_import_refresh_manager import STUBS
ROOT=Path(__file__).resolve().parents[2]
MAIN=r'''  Sys.setCwd(root);
  var state=root+"/import-cache/state";
  if(mode=="refresh") {
   var manifest=ImportRefreshTransaction.inspectRetainedManifests(root,state,root+"/import-cache/records")[0];
   var record=manifest.revision.importRecord;
   var source=root+"/import-cache/"+record.source;
   ImportWorkflow.overrideRoots=[{root:source+"/alpha",engine:ImportEngine.PSYCH},{root:source+"/beta",engine:ImportEngine.PSYCH}];
   ImportWorkflow.overrideRootRelatives=["alpha","beta"];
   ImportWorkflow.manualSongs=cast [{name:"song",sourceRelative:"alpha",engine:ImportEngine.PSYCH,missing:[]},{name:"other",sourceRelative:"beta",engine:ImportEngine.PSYCH,missing:[]}];
   var scanned=ImportWorkflow.scanNow(source,ImportEngine.PSYCH);
   var filtered=ImportRefreshManager.filterRemovedSourceRoots(scanned,source,record);
   check(filtered.detectedRoots.length==1 && filtered.songs.length==1 && filtered.songs[0].name=="other","removed root rescanned");
   var converted:Array<String>=[];
   var result=ImportRefreshManager.refreshNow(root,record,function(source,scan,names) {
    for(song in scan.songs) {
     converted.push(song.name);
     ImportFile.saveContent("assets/data/other/importProvenance.json",File.getContent(source+"/beta/provenance.json"));
     ImportFile.saveContent("assets/data/other/compatScripts.json",File.getContent(source+"/beta/compat.json"));
     ImportFile.saveContent("assets/imported_mods/beta/.cammie-owner.json",File.getContent(source+"/beta/marker.json"));
    }
    return {found:scan.songs.length,imported:scan.songs.length,importedSongs:converted,skipped:0,failed:0,copiedAssets:0,skippedAssets:0,errors:[]};
   },function()return false,function(p){});
   check(result.failed==0 && converted.join(",")=="other","refresh resurrected alpha");
   check(!FS.exists(root+"/assets/data/song/importProvenance.json") && !FS.exists(root+"/assets/imported_mods/alpha"),"refresh restored removed assets");
   check(File.getContent(root+"/user-library.json")=="saved history","refresh lost history");
   return;
  }
'''
SETUP=r'''  var donor=root+"/donor";
  write(donor+"/alpha/pack.json",{id:"alpha-package"});
  write(donor+"/beta/pack.json",{id:"beta-package"});
  write(donor+"/beta/provenance.json",{version:1,destinationFolder:"other",sourceFolder:"other",sourceEngine:engine,sourceOwner:"assets/imported_mods/beta",sourceIdentity:engine.toLowerCase()+"|id|beta-package",sourceFingerprint:""});
  write(donor+"/beta/compat.json",{version:1,selectedRoot:"assets/imported_mods/beta",roots:[{path:"assets/imported_mods/beta",engine:engine}]});
  write(donor+"/beta/marker.json",marker);
  var captured=ImportSourceSnapshot.capture(donor,root+"/import-cache/sources",engine,"0.0.9");
  check(captured.complete,"source capture failed");
  var snapshot=captured.snapshotId;
'''
TAIL=r'''  write(root+"/assets/data/baseSongKeys.json",[]);
  write(stage+"/other-provenance",Json.parse(File.getContent(donor+"/beta/provenance.json")));
  write(stage+"/other-compat",Json.parse(File.getContent(donor+"/beta/compat.json")));
  write(stage+"/other-marker",marker);
  outputs.push({path:"assets/data/other/importProvenance.json",stagedPath:"other-provenance"});
  outputs.push({path:"assets/data/other/compatScripts.json",stagedPath:"other-compat"});
  outputs.push({path:"assets/imported_mods/beta/.cammie-owner.json",stagedPath:"other-marker"});
  Reflect.setField(record,"type",engine);Reflect.setField(record,"engines",[engine]);
  Reflect.setField(record,"revisions",[ImportRevision.current(engine,"0.0.9")]);
'''
class ImportRemovalRefreshTest(unittest.TestCase):
 def run_fixture(self,tail,modes=('remove','refresh')):
  fixture=FIXTURE.split('  var protectedRoots:Array<String>=[];')[0]
  fixture=fixture.replace('class Main {','@:access(ImportRefreshManager) class Main {')
  fixture=fixture.replace('  var ownerRoot=',MAIN+'  var ownerRoot=')
  fixture=fixture.replace('sourceIdentity:"fixture",sourceFingerprint:"fixture"','sourceIdentity:engine.toLowerCase()+"|id|alpha-package",sourceFingerprint:""')
  fixture=fixture.replace('  var snapshot=hash("snapshot");',SETUP)
  fixture=fixture.replace('roots:[{namespace:"alpha",engine:engine}]','roots:[{namespace:"alpha",engine:engine,relative:"alpha"},{namespace:"beta",engine:engine,relative:"beta"}]')
  fixture=fixture.replace('  var committed=',TAIL+'  var committed=')
  fixture+=tail
  with tempfile.TemporaryDirectory(dir=TEST_TMP) as temporary:
   work=Path(temporary);install=work/'i';install.mkdir()
   (work/'ImportRefreshManagerFixture.hx').write_text('class ImportRefreshManagerFixture {public static var currentInstall:String="";public static function convertRetainedSource(source:String,scan:ImportWorkflow.ImportScanResult,names:Map<String,String>):ModuleFunctions.SongImportBatchResult return null;}',encoding='utf-8')
   for name,text in STUBS.items():
    target=work/name;target.parent.mkdir(parents=True,exist_ok=True)
    if name=='CompatScriptManifest.hx':
     text=text.replace(' public static inline var FILE_NAME', ' public static inline var VERSION:Int=1;\n public static function normalize(data:CompatScriptManifestData):CompatScriptManifestData return data;\n public static inline var FILE_NAME')
    target.write_text(text,encoding='utf-8')
   (work/'Main.hx').write_text(fixture,encoding='utf-8')
   for mode in modes:
    run=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main',mode,str(install)],cwd=work,text=True,capture_output=True,timeout=90)
    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
 def test_committed_partition_survives_fresh_process_regeneration(self):
  self.run_fixture(r'''  File.saveContent(root+"/user-library.json","saved history");
  var preview=ImportRemovalTransaction.preview(root,[ownerRoot],[]);
  check(preview.blockers.length==0,preview.blockers.join("; "));
  ImportRefreshManager.checked=true;
  var lease=ImportRefreshManager.tryAcquireRuntimeOwnerLease([ownerRoot]);
  check(lease!="","active owner lease denied without writer");
  check(ImportRefreshManager.reserveForRemoval(preview)=="","active owner could be removed");
  check(ImportRefreshManager.tryAcquireRuntimeOwnerLease([ownerRoot,"unsafe/root"])=="","mixed invalid roots were silently dropped");
  ImportRefreshManager.releaseRuntimeOwnerLease(lease);
  var reservation=ImportRefreshManager.reserveForRemoval(preview);
  check(reservation!="","unleased owner removal reservation failed");
  check(ImportRefreshManager.tryAcquireRuntimeOwnerLease([ownerRoot])=="","writer allowed source code lease");
  var handoffs=ModuleFunctions.handoffCalls;var invalidToken=false;
  try ImportRefreshManager.finishRemovalReservation("invalid",[],true) catch(_:Dynamic)invalidToken=true;
  check(invalidToken && ModuleFunctions.handoffCalls==handoffs,"invalid token touched foreground caches");
  ImportRefreshManager.finishRemovalReservation(reservation,[],false);
  ImportRefreshManager.dependentRootsByOwner.set("assets/imported_mods/provider",["assets/imported_mods/beta"]);
  var betaLease=ImportRefreshManager.tryAcquireRuntimeOwnerLease(["assets/imported_mods/beta"]);
  check(betaLease!="" && ImportRefreshManager.removalActiveOwners().indexOf("assets/imported_mods/provider")>=0,"provider closure missing from atomic lease");
  var blockedRefresh=false;
  try ImportRefreshManager.refreshNow(root,record,function(source,scan,names)return null,function()return false,function(p){}) catch(_:Dynamic)blockedRefresh=true;
  check(blockedRefresh,"active aggregate owner refresh was allowed");
  ImportRefreshManager.queue=[record];ImportRefreshManager.startNext();
  check(ImportRefreshManager.queue.length==1 && !ImportRefreshManager.active,"queued writer bypassed source lease");
  ImportRefreshManager.queue=[];ImportRefreshManager.releaseRuntimeOwnerLease(betaLease);
  ImportRefreshManager.dependentRootsByOwner=new Map();
  var removed=ImportRemovalTransaction.apply(root,preview,[]);
  check(removed.status=="applied",removed.status+": "+removed.blockers.join("; "));
 }
}''')
 def test_idle_refresh_gate_does_not_block_removal(self):
  """An import that cannot be refreshed is held out of use, yet the player must be able to remove it."""
  self.run_fixture(r'''  File.saveContent(root+"/user-library.json","saved history");
  var preview=ImportRemovalTransaction.preview(root,[ownerRoot],[]);
  check(preview.blockers.length==0,preview.blockers.join("; "));
  ImportRefreshManager.checked=true;
  ImportRefreshManager.mutex.acquire();
  var hold=ImportRefreshManager.reserveLocked("refresh:held","retained-import:held",[ownerRoot],null,false);
  hold.recoveryBlocked=true;
  ImportRefreshManager.mutex.release();
  check(ImportRefreshManager.removalActiveOwners().indexOf(ownerRoot)>=0,"a recovery hold must count as active");
  check(ImportRefreshManager.reserveForRemoval(preview)=="","a recovery hold must block removal");
  ImportRefreshManager.markIdleGate("refresh:held");
  check(ImportRefreshManager.removalActiveOwners().indexOf(ownerRoot)<0,"an idle gate must not count as active");
  check(ImportRefreshManager.tryAcquireRuntimeOwnerLease([ownerRoot])=="","an idle gate must still keep the package out of use");
  var again=ImportRemovalTransaction.preview(root,[ownerRoot],[],ImportRefreshManager.removalActiveOwners());
  check(again.blockers.length==0,again.blockers.join("; "));
  var token=ImportRefreshManager.reserveForRemoval(again);
  check(token!="","an idle gate blocked the removal reservation");
  var removed=ImportRemovalTransaction.apply(root,again,[]);
  check(removed.status=="applied",removed.status+": "+removed.blockers.join("; "));
  ImportRefreshManager.finishRemovalReservation(token,removed.affectedOwners,true);
  check(!ImportRefreshManager.reservations.exists("refresh:held"),"the hold of the removed import survived");
  check(ImportRefreshManager.reserveRemovalRecovery()!="","recovery must be possible once the hold is gone");
 }
}''',modes=('remove',))

 def test_a_failed_refresh_leaves_an_idle_gate_not_a_busy_hold(self):
  source=(ROOT/'source/ImportRefreshManager.hx').read_text(encoding='utf-8')
  # A stored failure for an outdated import marks the hold idle once no recovery is owed.
  start=source.index('var unrefreshable = false;')
  failure=source[start:source.index('ImportRefreshFailure.message(knownFailure', start)]
  self.assertIn('unrefreshable = true;', failure)
  self.assertIn('if (unrefreshable && recoveryPaths.length == 0) markIdleGate("refresh:" + id);', source)
  # A live failure whose rollback verified clean does the same; one with conflicts stays busy.
  settle=source[source.index('static function settleFailedReservation'):]
  settle=settle[:settle.index('static function refreshFailurePath')]
  self.assertIn('if (conflicts.length == 0) reservation.idleGate = true;', settle)
  # Only idle gates are ignored by the removal checks, and a retry of the receipt pass resets the flag.
  self.assertIn('for (reservation in reservations) if (!reservation.idleGate) return true;', source)
  self.assertIn('reservation.idleGate = false;', source)
