"""Real removal receipts, history preservation and cancellation contracts."""
from pathlib import Path
import subprocess
import json
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
from test_import_installed_ownership import FIXTURE
ROOT=Path(__file__).resolve().parents[2]
BODY=r'''  Sys.setCwd(root);
  write(root+"/assets/data/baseSongKeys.json",[]);
  if(mode=="unowned")File.saveContent(root+"/"+ownerRoot+"/local.txt","private local bytes");
  if(mode=="family3") {
   // The core cannot leave while members stay, so asking for it asks for the whole
   // family, and the members are reported as linked for a second confirmation.
   var corePlan=ImportRemovalTransaction.preview(root,["assets/imported_mods/core"],[]);
   check(corePlan.selectedOwners.length==1+corePlan.linkedOwners.length && corePlan.linkedOwners.indexOf(ownerRoot)>=0,
    "shared family core could be removed while a surviving member depends on it: "+corePlan.linkedOwners.join(",")+" / "+corePlan.blockers.join("; "));
   check(corePlan.linkedOwners.indexOf("assets/imported_mods/core")<0,"requested package reported as its own link");
   check(File.getContent(root+"/assets/imported_mods/core/__nmv_core/core.bin")=="shared core payload","blocked core preview changed bytes");
  }
  var plan=ImportRemovalTransaction.preview(root,[ownerRoot],[]);
  if(mode=="unowned") {check(plan.blockers.length>0,"unowned local file accepted");check(File.getContent(root+"/"+ownerRoot+"/local.txt")=="private local bytes","local file changed");return;}
  check(plan.blockers.length==0,"preview failed: "+plan.blockers.join("; "));
  File.saveContent(root+"/user-library.json","saved favorite and category");
  var before:Array<Dynamic>=[];
  function capture(path:String):Void {
   if(FS.isDirectory(path)){for(name in FS.readDirectory(path))capture(path+"/"+name);}
   else before.push({path:path.substr(root.length+1),sha256:ImportSourceSnapshot.sha256File(path,65536)});
  }
  for(path in ["assets","import-cache/state","import-cache/records"])capture(root+"/"+path);
  write(root+"/pre-removal-audit.json",before);
  if(mode=="edited")File.saveContent(root+"/"+ownerRoot+"/.cammie-owner.json","local edit");
  var cancelNow=false;
  var result=ImportRemovalTransaction.apply(root,plan,[],function()return mode=="cancel" || cancelNow,
   function(p) {
    if(mode=="cancel-prepare" && p.phase=="backing-up-removal")cancelNow=true;
    if(mode=="cleanup-pending" && p.phase=="removal-committed") {
     var transactions=root+"/import-cache/removal-state/transactions";
     var transaction=transactions+"/"+FS.readDirectory(transactions)[0];
     File.saveContent(transaction+"/retired/owner-0/modified.txt","changed private quarantine bytes");
    }
    if(mode=="crash-"+p.phase || mode=="partial-crash-"+p.phase)Sys.exit(33); if((mode=="rollback" || mode=="moved-rollback") && p.phase=="removal-scope-retired")throw "fixture rollback";});
  check(result.status==((mode=="cancel" || mode=="cancel-prepare")?"cancelled":mode=="cleanup-pending"?"cleanup-pending":(mode=="rollback" || mode=="moved-rollback" || mode=="edited")?"conflict":"applied"),"remove failed: "+result.status+" "+result.blockers.join("; "));
  check(File.getContent(root+"/user-library.json")=="saved favorite and category","history deleted");
  if(mode=="moved" || mode=="moved-rollback" || mode=="moved-unfinished") {
   // The install folder was moved or renamed after this removal. A committed or
   // rolled-back removal has nothing left to restore into the old folder, so its
   // history must not lock imports and removals on every later launch. The journal
   // bytes stay untouched: the receipt binds them.
   var transactions=root+"/import-cache/removal-state/transactions";
   if(mode=="moved-unfinished")for(name in FS.readDirectory(transactions))FS.deleteFile(transactions+"/"+name+"/receipt.json");
   Sys.setCwd(haxe.io.Path.directory(root));
   var renamed=root+"-moved";FS.rename(root,renamed);root=renamed;Sys.setCwd(root);
  }
  if(mode=="moved-unfinished") {
   // Without a receipt the journal could still restore files into the old folder.
   var held=ImportRemovalTransaction.recover(root);
   check(held.length==1 && held[0].indexOf("different install folder")>=0,"unfinished foreign removal was recovered: "+held.join("; "));
   check(!FS.exists(root+"/"+ownerRoot),"foreign unfinished removal restored files into this install");
   return;
  }
  if(mode!="cleanup-pending")check(ImportRemovalTransaction.recover(root).length==0,"recovery failed: "+ImportRemovalTransaction.recover(root).join("; "));
  if(mode=="moved" || mode=="moved-rollback")check(ImportRemovalTransaction.recover(root).length==0,"second launch recovery of a moved install failed");
  var installed=ImportRefreshTransaction.inspectRetainedManifests(root,root+"/import-cache/state",root+"/import-cache/records");
  check(installed.length==((mode=="cancel" || mode=="cancel-prepare" || mode=="rollback" || mode=="moved-rollback" || mode=="edited" || mode=="partial" || mode=="family" || mode=="family3")?1:0),"receipt retirement wrong");
  if(mode!="cancel" && mode!="edited")check(LibraryIdentityArchive.load(root).records.length==1,"identity archive lost");
  if(mode=="rollback") {
   // Removing the same package again after a rolled-back attempt must work, and the
   // next launch's recovery must not trip over the old attempt's journal.
   var retry=ImportRemovalTransaction.preview(root,[ownerRoot],[]);
   check(retry.blockers.length==0,"retry preview blocked: "+retry.blockers.join("; "));
   var second=ImportRemovalTransaction.apply(root,retry,[],function()return false,function(p){});
   check(second.status=="applied","retry removal failed: "+second.status+" "+second.blockers.join("; "));
   var relaunch=ImportRemovalTransaction.recover(root);
   check(relaunch.length==0,"recovery after a rolled-back attempt and a later removal failed: "+relaunch.join("; "));
   check(ImportRemovalTransaction.recover(root).length==0,"second launch recovery failed");
   check(ImportRefreshTransaction.inspectRetainedManifests(root,root+"/import-cache/state",root+"/import-cache/records").length==0,"retry left the package installed");
  }
  if(mode=="valid") {
   var donor=root+"/renamed-donor";write(donor+"/pack.json",{id:"alpha-package"});
   ImportSongOwnership.invalidateOwnerIdentityIndex();
   check(CompatScriptManifest.namespaceFor(donor,engine)=="alpha","explicit reinstall lost archived owner");
   var destination=ImportSongOwnership.planDestination("assets/data/song","song",donor,engine,"song");
   check(Reflect.field(destination,"folder")=="song" && Reflect.field(destination,"error")==null,"explicit reinstall lost chart identity");
   var reinstall=ImportRefreshTransaction.apply(root,stage,root+"/import-cache/state",owner,["assets"],outputs,{importRecord:record});
   check(reinstall.status=="applied","explicit reinstall failed");
   check(File.getContent(root+"/user-library.json")=="saved favorite and category","reinstall lost history");
  }
  if(mode=="partial" || mode=="family" || mode=="family3") {
   check(installed[0].revision.importRecord.roots.length==(mode=="family3"?2:1) && installed[0].revision.importRecord.roots[0].namespace=="beta","partial roots wrong");
   check(installed[0].revision.importRecord.removedSourceRoots.length==1,"source exclusion missing");
   check(File.getContent(root+"/assets/data/other/importProvenance.json").indexOf("beta")>=0,"survivor deleted");
   if(mode=="family3") {
    check(File.getContent(root+"/assets/imported_mods/core/__nmv_core/core.bin")=="shared core payload","member removal changed shared core");
    check(installed[0].revision.importRecord.packageFamilyCatalog.version==3 && installed[0].revision.importRecord.packageFamilyCatalog.members.length==1,"surviving family lost its v3 core declaration");
   }
  }
 }
}'''
PHASES=('backing-up-removal','removal-journal-prepared','removal-file-applied','removal-scope-retired','removal-scope-published','removal-marker-published','removal-committed')
RECOVERY=r'''  if(StringTools.startsWith(mode,"recover-")) {
   Sys.setCwd(root); var failures=ImportRemovalTransaction.recover(root);
   if(mode=="recover-blocked") {check(failures.length>0,"edited journal accepted");return;}
   check(failures.length==0,"fresh recovery failed: "+failures.join("; "));
   check(ImportRemovalTransaction.recover(root).length==0,"repeated recovery failed");
   var installed=ImportRefreshTransaction.inspectRetainedManifests(root,root+"/import-cache/state",root+"/import-cache/records");
   var partial=StringTools.startsWith(mode,"recover-partial-");
   var committed=StringTools.endsWith(mode,"removal-committed");
   check(installed.length==((partial || !committed)?1:0),"recovery receipt count wrong");
   if(partial)check(installed[0].revision.importRecord.roots.length==(committed?1:2),"partial recovery roots wrong");
   if(!committed) {
    var before:Array<Dynamic>=Json.parse(File.getContent(root+"/pre-removal-audit.json"));
    for(entry in before)check(FS.exists(root+"/"+entry.path) && ImportSourceSnapshot.sha256File(root+"/"+entry.path,65536)==entry.sha256,"recovery changed original bytes: "+entry.path);
   }
   check(File.getContent(root+"/user-library.json")=="saved favorite and category","recovery lost saved history");
   return;
  }
'''
class ImportRemovalTransactionTest(unittest.TestCase):
 def test_real_commit_and_cancel(self):
  fixture=FIXTURE.split('  var protectedRoots:Array<String>=[];')[0].replace('sourceIdentity:"fixture",sourceFingerprint:"fixture"','sourceIdentity:engine.toLowerCase()+"|id|alpha-package",sourceFingerprint:""')+BODY
  fixture=fixture.replace('  var ownerRoot=',RECOVERY+'  var ownerRoot=')
  with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
   work=Path(folder); (work/'Main.hx').write_text(fixture,encoding='utf-8')
   for mode in ('valid','cancel','cancel-prepare','cleanup-pending','edited','rollback','moved','moved-rollback','moved-unfinished','partial','family','family3','unowned', *['crash-'+phase for phase in PHASES], *['partial-crash-'+phase for phase in PHASES]):
    install=work/str(len(list(work.iterdir())));install.mkdir()
    current=fixture
    if mode in ('partial','family','family3') or mode.startswith('partial-crash-'):
     current=current.replace('roots:[{namespace:"alpha",engine:engine}]','roots:[{namespace:"alpha",engine:engine,relative:"alpha"},{namespace:"beta",engine:engine,relative:"beta"}]')
     current=current.replace('  var committed=ImportRefreshTransaction.apply',r'''  write(stage+"/other-provenance",{version:1,destinationFolder:"other",sourceFolder:"other",sourceEngine:engine,sourceOwner:"assets/imported_mods/beta",sourceIdentity:engine.toLowerCase()+"|id|beta-package",sourceFingerprint:""});
  write(stage+"/other-compat",{version:1,selectedRoot:"assets/imported_mods/beta",roots:[{path:"assets/imported_mods/beta",engine:engine}]});
  write(stage+"/other-marker",marker);
  outputs.push({path:"assets/data/other/importProvenance.json",stagedPath:"other-provenance"});
  outputs.push({path:"assets/data/other/compatScripts.json",stagedPath:"other-compat"});
  outputs.push({path:"assets/imported_mods/beta/.cammie-owner.json",stagedPath:"other-marker"});
  var committed=ImportRefreshTransaction.apply''')
    if mode in ('family','family3'):
     current=current.replace('var engine=ImportEngine.PSYCH','var engine=ImportEngine.NIGHTMARE_VISION')
     current=current.replace('  var committed=ImportRefreshTransaction.apply',r'''  Reflect.setField(record,"engines",[engine]);
  Reflect.setField(record,"packageFamilyCatalog",{version:2,engine:engine,snapshotId:snapshot,containerRelative:"",members:[{directory:"alpha",sourceRelative:"alpha",namespace:"alpha"},{directory:"beta",sourceRelative:"beta",namespace:"beta"}]});
  outputs.push({path:ownerRoot+"/scripts/main.lua",stagedPath:"marker"});
  outputs.push({path:"assets/imported_mods/beta/scripts/main.lua",stagedPath:"other-marker"});
  var committed=ImportRefreshTransaction.apply''')
    if mode=='family3':
     current=current.replace('  var committed=ImportRefreshTransaction.apply',r'''  record.roots.push({namespace:"core",engine:engine,relative:""});
  Reflect.setField(record,"packageFamilyCatalog",{version:3,engine:engine,snapshotId:snapshot,containerRelative:"content",members:[{directory:"alpha",sourceRelative:"content/alpha",namespace:"alpha"},{directory:"beta",sourceRelative:"content/beta",namespace:"beta"}],coreProvider:{rootRelative:"",namespace:"core",projectSha256:hash("project")}});
  record.roots[0].relative="content/alpha/assets";record.roots[1].relative="content/beta/assets";
  Reflect.setField(record,"sourceAssetProfiles",{version:1,snapshotId:snapshot,roots:[{rootRelative:"",engine:engine,namespace:"core",profile:{provenance:"receipt-bound",snapshotId:snapshot,sourceEngine:engine,rootRelative:"",namespace:"core",projectSha256:hash("project")}}]});
  write(stage+"/core-marker",marker);File.saveContent(stage+"/core-payload","shared core payload");write(stage+"/receiver-index",{version:1});
  outputs.push({path:"assets/imported_mods/core/.cammie-owner.json",stagedPath:"core-marker"});
  outputs.push({path:"assets/imported_mods/core/__nmv_core/core.bin",stagedPath:"core-payload"});
  for(namespace in ["alpha","beta"])outputs.push({path:"assets/imported_mods/"+namespace+"/"+SourceLimeAssetIdentity.sidecarRelativePath(engine,"core"),stagedPath:"receiver-index"});
  var otherCompat:Dynamic=Json.parse(File.getContent(stage+"/other-compat"));otherCompat.roots.push({path:"assets/imported_mods/core",engine:engine});write(stage+"/other-compat",otherCompat);
  var alphaCompat:Dynamic=Json.parse(File.getContent(stage+"/compat"));alphaCompat.roots.push({path:"assets/imported_mods/core",engine:engine});write(stage+"/compat",alphaCompat);
  var committed=ImportRefreshTransaction.apply''')
    (work/'Main.hx').write_text(current,encoding='utf-8')
    run=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main',mode,str(install)],cwd=work,text=True,capture_output=True,timeout=90)
    self.assertEqual(run.returncode,33 if 'crash-' in mode else 0,run.stdout+run.stderr)
    if 'crash-' in mode:
     phase=mode.split('crash-',1)[1]
     recovery_mode=('recover-partial-' if mode.startswith('partial-') else 'recover-')+phase
     recovered=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main',recovery_mode,str(install)],cwd=work,text=True,capture_output=True,timeout=90)
     self.assertEqual(recovered.returncode,0,recovered.stdout+recovered.stderr)

     # Existing shared transaction coverage exercises the same restoration
     # guard. The removal-specific recreated-path probe runs below separately.

     # Committed cleanup journals are cryptographically bound by the receipt.
     # Recovery of an edited journal must preserve every existing byte.
     if phase=='removal-committed':
      transaction=next((install/'import-cache/removal-state/transactions').iterdir())
      journal_path=sorted(transaction.glob('journal-*.json'))[-1]
      journal=json.loads(journal_path.read_text(encoding='utf-8'))
      journal['operations'][0]['beforeSha256']='0'*64
      journal_path.write_text(json.dumps(journal),encoding='utf-8')
      before={str(path.relative_to(install)):path.read_bytes() for path in install.rglob('*') if path.is_file()}
      blocked=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main','recover-blocked',str(install)],cwd=work,text=True,capture_output=True,timeout=90)
      self.assertEqual(blocked.returncode,0,blocked.stdout+blocked.stderr)
      after={str(path.relative_to(install)):path.read_bytes() for path in install.rglob('*') if path.is_file()}
      self.assertEqual(before,after)

    if mode=='cleanup-pending':
     transaction=next((install/'import-cache/removal-state/transactions').iterdir())
     changed=transaction/'retired/owner-0/modified.txt'
     self.assertTrue(changed.exists())
     before={str(path.relative_to(install)):path.read_bytes() for path in install.rglob('*') if path.is_file()}
     blocked=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main','recover-blocked',str(install)],cwd=work,text=True,capture_output=True,timeout=90)
     self.assertEqual(blocked.returncode,0,blocked.stdout+blocked.stderr)
     self.assertEqual(before,{str(path.relative_to(install)):path.read_bytes() for path in install.rglob('*') if path.is_file()})
     changed.unlink()  # This exact private fixture file was created above.
     recovered=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main','recover-removal-committed',str(install)],cwd=work,text=True,capture_output=True,timeout=90)
     self.assertEqual(recovered.returncode,0,recovered.stdout+recovered.stderr)

   current=fixture
   (work/'Main.hx').write_text(current,encoding='utf-8')
   install=work/'recreated';install.mkdir()
   crashed=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main','crash-removal-file-applied',str(install)],cwd=work,text=True,capture_output=True,timeout=90)
   self.assertEqual(crashed.returncode,33,crashed.stdout+crashed.stderr)
   transaction=next((install/'import-cache/removal-state/transactions').iterdir())
   journal=json.loads(sorted(transaction.glob('journal-*.json'))[-1].read_text(encoding='utf-8'))
   recreated=install/journal['operations'][0]['path'];recreated.write_text('new local bytes after interruption',encoding='utf-8')
   blocked=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main','recover-blocked',str(install)],cwd=work,text=True,capture_output=True,timeout=90)
   self.assertEqual(blocked.returncode,0,blocked.stdout+blocked.stderr)
   self.assertEqual(recreated.read_text(encoding='utf-8'),'new local bytes after interruption')
   recreated.unlink()  # Exact private fixture file created above.
   recovered=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','Main','recover-removal-file-applied',str(install)],cwd=work,text=True,capture_output=True,timeout=90)
   self.assertEqual(recovered.returncode,0,recovered.stdout+recovered.stderr)
