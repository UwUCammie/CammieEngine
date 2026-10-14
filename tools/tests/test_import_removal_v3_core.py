"""Remove a member from a real captured and mapped v3 core family."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
from test_import_package_family_catalog import FIXTURE
ROOT=Path(__file__).resolve().parents[2]
CHECK=r'''    if(mode=="v3-removal") {
     var selected="assets/imported_mods/"+packageNamespaces[0];
     var survivor="assets/imported_mods/"+packageNamespaces[1];
     var core="assets/imported_mods/"+providerNamespace;
     // The shared core cannot go while members stay: asking for it widens to the
     // members, which are reported as linked so the UI asks about them separately.
     var corePreview=ImportRemovalTransaction.preview(install,[core],[]);
     if(corePreview.linkedOwners.indexOf(selected)<0 || corePreview.linkedOwners.indexOf(survivor)<0 || corePreview.linkedOwners.indexOf(core)>=0)
      throw "shared provider deletion did not take its members along: "+corePreview.linkedOwners.join(",")+" / "+corePreview.blockers.join("; ");
     var hashes:Map<String,String>=new Map();
     for(file in committed.files)if(StringTools.startsWith(file.path,survivor+"/"))hashes.set(file.path,ImportSourceSnapshot.sha256File(install+"/"+file.path,65536));
     var preview=ImportRemovalTransaction.preview(install,[selected],[]);
     if(preview.blockers.length>0)throw preview.blockers.join("; ");
     var removed=ImportRemovalTransaction.apply(install,preview,[]);
     if(removed.status!="applied")throw removed.status+": "+removed.blockers.join("; ");
     for(path in hashes.keys())if(ImportSourceSnapshot.sha256File(install+"/"+path,65536)!=hashes.get(path))throw "surviving mapped core changed: "+path;
     if(FileSystem.exists(install+"/"+selected))throw "removed member namespace remains";
     var next=ImportRefreshTransaction.inspectRetainedManifests(install,cache+"/state",cache+"/records")[0];
     if(next.packageFamilyCatalog.version!=3||next.packageFamilyCatalog.members.length!=1)throw "v3 survivor catalog invalid";
    }
'''
RECOVER=r'''   case "v3-removal-recover", "v3-remove-all":
    var failures=ImportRemovalTransaction.recover(install);
    if(failures.length>0)throw failures.join("; ");
    var manifest=ImportRefreshTransaction.inspectRetainedManifests(install,cache+"/state",cache+"/records")[0];
    var record=manifest.revision.importRecord;
    var roots=ImportPackageFamilyCatalog.sourceRoots(cache+"/sources/"+record.snapshotId,record);
    if(roots.length!=1||!StringTools.endsWith(roots[0],"/beta"))throw "fresh family publication enumerated removed alpha";
    var namespace=manifest.packageFamilyCatalog.members[0].namespace;
    if(File.getContent(install+"/assets/imported_mods/"+namespace+"/__nmv_core/images/core.png")!="provider core image")throw "fresh core bytes changed";
    if(mode=="v3-remove-all") {
     var snapshot=cache+"/sources/"+record.snapshotId;
     var selected=ImportRemovalPlan.manifestRoots(manifest);
     var preview=ImportRemovalTransaction.preview(install,selected,[]);
     if(preview.blockers.length>0)throw preview.blockers.join("; ");
     if(preview.candidateSnapshots.length!=1)throw "unreferenced snapshot not eligible for managed cleanup";
     var removed=ImportRemovalTransaction.apply(install,preview,[]);
     if(removed.status!="applied")throw removed.status+": "+removed.blockers.join("; ");
     if(FileSystem.exists(snapshot))throw "unreferenced managed snapshot remains";
     if(!FileSystem.exists(install+"/donors/v3-core-handoff-source/NightmareVision.exe"))throw "external donor source was removed";
     if(ImportRemovalTransaction.recover(install).length>0)throw "fully removed source cleanup recovery failed";
    }
    report({survivingRoots:roots,namespace:namespace});
'''
class ImportRemovalV3CoreTest(unittest.TestCase):
 def test_real_v3_core_survives_member_removal_and_restart(self):
  fixture=FIXTURE.replace('case "v3-core-handoff", "v3-container-only", "v3-legacy-runtime":',RECOVER+'case "v3-core-handoff", "v3-container-only", "v3-legacy-runtime", "v3-removal":')
  fixture=fixture.replace('    planned.record.packageFamilyCatalog=published;', '    planned.record.packageFamilyCatalog=published;\n    if(mode=="v3-removal")Reflect.setField(planned.record,"runtimeDependencyOwners",[]);')
  fixture=fixture.replace('    report({version:committed.packageFamilyCatalog.version',CHECK+'    report({version:committed.packageFamilyCatalog.version')
  with tempfile.TemporaryDirectory(dir=TEST_TMP) as temporary:
   work=Path(temporary);install=work/'i';install.mkdir()
   (work/'ImportPackageFamilyCatalogFixture.hx').write_text(fixture,encoding='utf-8')
   for mode in ('v3-removal','v3-removal-recover','v3-remove-all'):
    run=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(work),'--run','ImportPackageFamilyCatalogFixture',mode,str(install)],cwd=work,text=True,capture_output=True,timeout=120)
    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
