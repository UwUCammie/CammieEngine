"""Durable library identities preserve favorites and destinations across reinstall."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, TEST_TMP
from test_import_installed_ownership import FIXTURE as OWNERSHIP_FIXTURE
ROOT = Path(__file__).resolve().parents[2]

ARCHIVE_BODY = r'''  Sys.setCwd(root);
  var source=root+"/renamed-source";FS.createDirectory(source);
  write(source+"/pack.json",{id:"alpha-package",name:"Alpha"});
  write(root+"/assets/data/baseSongKeys.json",[]);
  function expectFailure(work:Void->Void):Void {
   var failed=false;try work() catch(_:Dynamic)failed=true;check(failed,"unsafe archive accepted: "+mode);
  }
  var before=File.getContent(root+"/assets/data/song/importProvenance.json");
  if(mode=="cancel") {
   expectFailure(function(){LibraryIdentityArchive.prepare(root,[ownerRoot],[],function()return true);});
   check(!FS.exists(root+"/"+LibraryIdentityArchive.DATA),"cancel wrote history");return;
  }
  var archive=LibraryIdentityArchive.prepare(root,[ownerRoot],[]);
  check(archive.records.length==1,"archive omitted validated identity");
  check(File.getContent(root+"/assets/data/song/importProvenance.json")==before,"archive changed donor output");
  check(archive.ownerFor(engine,engine.toLowerCase()+"|id|alpha-package","")==ownerRoot,"owner reservation missing");
  check(archive.destinationFor(engine,engine.toLowerCase()+"|id|alpha-package","","song")=="song","destination reservation missing");
  check(archive.ownerFor(engine,engine.toLowerCase()+"|id|other-package","")==null,"unrelated package merged");
  if(mode=="edited") {
   File.saveContent(root+"/"+LibraryIdentityArchive.DATA,archive.encode()+" ");
   expectFailure(function(){LibraryIdentityArchive.load(root);});return;
  }
  if(mode=="missing-receipt") {
   FS.deleteFile(root+"/import-cache/library-history/state/"+hash("library-history-identities")+"/manifest.json");
   expectFailure(function(){LibraryIdentityArchive.load(root);});return;
  }
  if(mode=="ambiguity") {
   var duplicate=archive.records[0];duplicate.ownerRoot="assets/imported_mods/other";duplicate.folder="other-song";
   var ambiguous=new LibraryIdentityArchive(archive.records.concat([duplicate]));
   expectFailure(function(){ambiguous.ownerFor(engine,engine.toLowerCase()+"|id|alpha-package","");});return;
  }
  if(mode=="invalid-path") {
   var record=archive.records[0];record.folder="../escape";
   expectFailure(function(){new LibraryIdentityArchive([record]);});return;
  }
  var library=new UserLibraryData();var key=UserLibraryData.chartKey(ownerRoot,"song");
  library.setFavorite(key,true);library.setLastDifficulty(key,"hard");
  var category=library.createCategory("Favorites");library.setMembership(category,ownerRoot,true);
  File.saveContent(root+"/user-library.json",library.encode());
  // Model only the removal of this fixture's explicitly managed outputs.
  for(output in outputs)FS.deleteFile(root+"/"+output.path);
  FS.deleteDirectory(root+"/assets/data/song");FS.deleteDirectory(root+"/"+ownerRoot);
  if(mode=="occupied")FS.createDirectory(root+"/"+ownerRoot);
  ImportSongOwnership.invalidateOwnerIdentityIndex();
  if(mode=="occupied") {
   expectFailure(function(){CompatScriptManifest.namespaceFor(source,engine);});return;
  }
  var namespace=CompatScriptManifest.namespaceFor(source,engine);
  check(namespace=="alpha","reinstall changed archived owner");
  var plan=ImportSongOwnership.planDestination("assets/data/song","song",source,engine,"song");
  check(Reflect.field(plan,"error")==null && Reflect.field(plan,"folder")=="song","reinstall changed chart destination");
  var restored=UserLibraryData.decode(File.getContent(root+"/user-library.json"));
  var restoredKey=UserLibraryData.chartKey("assets/imported_mods/"+namespace,"song");
  check(restored.isFavorite(restoredKey) && restored.lastDifficulty(restoredKey)=="hard"
   && restored.hasMod(category,ownerRoot),"reinstall lost saved library records");
  var reloaded=LibraryIdentityArchive.load(root);
  check(reloaded.encode()==archive.encode(),"fresh history read changed reservations");
  // Names alone cannot claim history, unlike explicit authored IDs.
  var named=archive.records[0];named.sourceIdentity=engine.toLowerCase()+"|package-name|alpha";
  named.sourceFingerprint="0123456789abcdef0123456789abcdef";
  var weak=new LibraryIdentityArchive([named]);
  check(weak.ownerFor(engine,named.sourceIdentity,"")==null,"label alone claimed an owner");
  check(weak.ownerFor(engine,named.sourceIdentity,named.sourceFingerprint)==ownerRoot,"fingerprinted match lost");
  Sys.println("archive contract passed: "+mode);
 }
}'''

class LibraryIdentityArchiveTest(unittest.TestCase):
    def test_durable_archive_and_reinstall_contracts(self):
        fixture = OWNERSHIP_FIXTURE.split('  var protectedRoots:Array<String>=[];')[0]
        fixture = fixture.replace('sourceIdentity:"fixture",sourceFingerprint:"fixture"',
                                  'sourceIdentity:engine.toLowerCase()+"|id|alpha-package",sourceFingerprint:""')
        fixture += ARCHIVE_BODY
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as folder:
            work=Path(folder)
            (work/'Main.hx').write_text(fixture,encoding='utf-8')
            for mode in ('valid','qualified','cancel','edited','missing-receipt','ambiguity','invalid-path','occupied'):
                with self.subTest(mode=mode):
                    current = fixture
                    if mode == 'qualified':
                        current = current.replace('destinationFolder:"song"', 'destinationFolder:"song--archived"')
                        current = current.replace('assets/data/song', 'assets/data/song--archived')
                        current = current.replace('=="song"', '=="song--archived"')
                    (work/'Main.hx').write_text(current,encoding='utf-8')
                    install=work/mode;install.mkdir()
                    result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/tjson/1,4,0'),
                                           '-cp',str(work),'--run','Main',mode,str(install)],
                                          cwd=work,text=True,capture_output=True,timeout=60)
                    self.assertEqual(result.returncode,0,result.stdout+result.stderr)
