"""Installed addon dependencies require committed, unique, exact-dialect provenance."""
from pathlib import Path
import os
import hashlib
import json
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND

ROOT=Path(__file__).resolve().parents[2]


class ImportInstalledDependencyRootsTest(unittest.TestCase):
    def provider(self, install, label, *, engine='Psych Engine', relative='base', complete=True, stage=True, actors=True):
        record_id=hashlib.sha256(label.encode()).hexdigest()
        snapshot=hashlib.sha256(('snapshot-'+label).encode()).hexdigest()
        retained=install/'import-cache/sources'/snapshot/'content/base'
        owner=install/'assets/imported_mods'/label
        for root in [retained,owner]:
            (root/'characters').mkdir(parents=True)
            (root/'stages').mkdir()
            if actors:
                for name in ['unique-player','unique-opponent']:
                    (root/'characters'/f'{name}.json').write_text('{"image":"actor","animations":[]}')
            (root/'stages/room.json').write_text('{"defaultZoom":1}')
            if stage: (root/'stages/room.lua').write_text('function onCreate() end')
        snapshot_root=install/'import-cache/sources'/snapshot
        (snapshot_root/'receipt.json').write_text(json.dumps({'snapshotSchemaVersion':2,'snapshotId':snapshot,'incompleteReasons':[] if complete else ['incomplete']}))
        state=install/'import-cache/state'/hashlib.sha256(('retained-import:'+record_id).encode()).hexdigest()
        (state/'transactions/txn-fixture').mkdir(parents=True)
        record={'id':record_id,'source':f'sources/{snapshot}/content','snapshotId':snapshot,'roots':[{'relative':relative,'engine':engine,'namespace':label}]}
        manifest={'schemaVersion':1,'owner':'retained-import:'+record_id,'transactionId':'txn-fixture','revision':{'importRecord':record}}
        text=json.dumps(manifest)
        (state/'manifest.json').write_text(text)
        (state/'transactions/txn-fixture/receipt.json').write_text(json.dumps({'status':'applied','owner':manifest['owner'],'transactionId':'txn-fixture','manifestSha256':hashlib.sha256(text.encode()).hexdigest()}))
        pointers=install/'import-cache/records'
        pointers.mkdir(parents=True,exist_ok=True)
        (pointers/f'{record_id}.json').write_text(json.dumps({'id':record_id}))
        return retained,owner,state

    def run_haxe(self, folder, body, args):
        (folder/'Main.hx').write_text('class Main {static function main(){\n'+body+'\n}}')
        helper=(ROOT/'source/CompatCanonicalPath.hx').read_text()
        if os.name=='nt':
            helper=helper.replace('var result = FileSystem.fullPath(path);','var result = CanonicalWindowsTestPath.resolve(path);')
            (folder/'CanonicalWindowsTestPath.hx').write_text('class CanonicalWindowsTestPath {public static function resolve(path:String):String {var p=new sys.io.Process("python",["-c","import os,sys; print(os.path.realpath(sys.argv[1]))",path]);var value=StringTools.trim(p.stdout.readAll().toString());var code=p.exitCode();p.close();if(code!=0)throw "canonical path probe failed";return value;}}')
        (folder/'CompatCanonicalPath.hx').write_text(helper)

        # Identity seam only; the resolver, record/receipt validation and staged
        # filesystem modules are the actual production classes.
        (folder/'CompatScriptManifest.hx').write_text('class CompatScriptManifest {public static function destinationRoot(s:String,e:String):String return "assets/imported_mods/current";}')
        result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(folder),'--run','Main',*map(str,args)],
            cwd=ROOT,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_unique_provider_and_rejection_contracts(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            scratch=Path(temp)
            names=['unique','ambiguous','traversal','incomplete','stage-json-only','wrong-engine','missing-actor','current-owner']
            for name in names:
                install=scratch/name
                (install/'addon').mkdir(parents=True)
                self.provider(install,'provider',relative='../base' if name=='traversal' else 'base',
                    complete=name!='incomplete',stage=name!='stage-json-only',
                    engine='Nightmare Vision' if name=='wrong-engine' else 'Psych Engine',actors=name!='missing-actor')
                if name=='ambiguous': self.provider(install,'second-provider')
                if name=='current-owner': self.provider(install,'current')
            self.run_haxe(scratch,r'''
var parent=Sys.args()[0];
var chart:Dynamic={song:{player1:"unique-player",player2:"unique-opponent",gfVersion:"gf",stage:"room"}};
for(name in ["unique","ambiguous","traversal","incomplete","stage-json-only","wrong-engine","missing-actor","current-owner"]){
 Sys.setCwd(parent+"/"+name);
 var result=ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart);
 if(name=="unique" || name=="current-owner") {
  if(result.providers.length!=1 || result.providers[0].owner!="assets/imported_mods/provider") throw "unique provider/current-owner isolation failed";
 } else if(result.providers.length!=0) throw "unsafe dependency chosen: "+name;
 if(name=="ambiguous" && result.diagnostics.length==0) throw "ambiguity omitted diagnostic";
}
Sys.setCwd(parent+"/unique");
var bounded = @:privateAccess new ImportInstalledDependencyRoots();
@:privateAccess bounded.metadataRemaining=1;
var exhausted = @:privateAccess bounded.scan(Sys.getCwd()+"/addon","Psych Engine",chart);
if(exhausted.providers.length!=0 || exhausted.diagnostics.length!=1 || exhausted.diagnostics[0].indexOf("installed-dependency-limit")<0) throw "metadata exhaustion guessed a provider";
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",{player1:"bf",player2:"dad",stage:"room"}).providers.length!=0) throw "builtin cast inferred provider";
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Nightmare Vision",chart).providers.length!=0) throw "Psych provider leaked into NV";
var owner=ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers[0];
if(ImportInstalledDependencyRoots.resolve(owner.root,"Psych Engine",chart).providers.length!=0) throw "source owner chose itself";
sys.FileSystem.createDirectory("addon/stages");sys.io.File.saveContent("addon/stages/room.lua","function onCreate() end");
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=0) throw "complete addon adopted base";
''',[scratch])

    def test_record_limit_cannot_choose_early_match(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            scratch=Path(temp);install=scratch/'install'
            (install/'addon').mkdir(parents=True)
            self.provider(install,'provider')
            for index in range(256):
                name=hashlib.sha256(('extra-'+str(index)).encode()).hexdigest()+'.json'
                (install/'import-cache/records'/name).write_text('{}')
            self.run_haxe(scratch,r'''
Sys.setCwd(Sys.args()[0]);
var result=ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",{player1:"unique-player",stage:"room"});
if(result.providers.length!=0 || result.diagnostics.length!=1 || result.diagnostics[0].indexOf("installed-dependency-limit")<0) throw "truncated scan chose early match";
''',[install])

    def test_nv_exact_dialect_and_third_role(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            scratch=Path(temp)
            install=scratch/'install'
            (install/'addon').mkdir(parents=True)
            retained,owner,_=self.provider(install,'provider',engine='Nightmare Vision')
            for root in [retained,owner]:
                (root/'data/stages/room').mkdir(parents=True)
                (root/'data/stages/room/script.hx').write_text('function create() {}')
            self.run_haxe(scratch,r'''
Sys.setCwd(Sys.args()[0]);
var chart:Dynamic={player1:"unique-player",player2:"unique-opponent",stage:"room"};
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Nightmare Vision",chart).providers.length!=1) throw "NV provider missing";
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=0) throw "NV provider crossed dialect";
chart.player3="unique-girlfriend";
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Nightmare Vision",chart).providers.length!=0) throw "third role ignored";
chart.gfVersion="gf";
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Nightmare Vision",chart).providers.length!=1) throw "obsolete NV third-role alias displaced gfVersion";
''',[install])

    def test_staged_owner_reads_and_commit_integrity(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            scratch=Path(temp)
            install=scratch/'install'
            (install/'addon').mkdir(parents=True)
            retained,owner,state=self.provider(install,'provider')
            self.run_haxe(scratch,r'''
Sys.setCwd(Sys.args()[0]);
var chart:Dynamic={player1:"unique-player",player2:"unique-opponent",stage:"room"};
var context=ImportIO.begin(Sys.getCwd(),Sys.args()[1]);
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=1) throw "worker view missed committed base";
ImportFile.saveContent("assets/imported_mods/provider/stages/room.lua", "");
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=0) throw "resolver ignored staged stage removal";
ImportIO.end();
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=1) throw "worker changed installed base";
''',[install,install/'import-cache/staging/test'])
            (state/'manifest.json').write_text((state/'manifest.json').read_text()+' ')
            self.run_haxe(scratch,r'''
Sys.setCwd(Sys.args()[0]);
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",{player1:"unique-player",stage:"room"}).providers.length!=0) throw "uncommitted manifest accepted";
''',[install])

    @unittest.skipUnless(os.name=='nt','Windows junction contract')
    def test_junction_owner_is_rejected_in_direct_and_staged_views(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            scratch=Path(temp);install=scratch/'install'
            (install/'addon').mkdir(parents=True)
            _,owner,_=self.provider(install,'provider')
            target=scratch/'external';owner.rename(target)
            quote=lambda value: "'"+str(value).replace("'","''")+"'"
            setup=subprocess.run(['powershell','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(owner)+' -Target '+quote(target)+' | Out-Null'],capture_output=True,text=True,timeout=20)
            self.assertEqual(setup.returncode,0,setup.stdout+setup.stderr)
            self.run_haxe(scratch,r'''
Sys.setCwd(Sys.args()[0]);
var chart:Dynamic={player1:"unique-player",stage:"room"};
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=0) throw "junction owner accepted";
ImportIO.begin(Sys.getCwd(),Sys.args()[1]);
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=0) throw "worker junction owner accepted";
ImportIO.end();
''',[install,install/'import-cache/staging/test'])

    def test_symlink_owner_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            scratch=Path(temp)
            install=scratch/'install'
            (install/'addon').mkdir(parents=True)
            retained,owner,_=self.provider(install,'provider')
            target=scratch/'external'
            owner.rename(target)
            try:
                owner.symlink_to(target,target_is_directory=True)
            except OSError as error:
                if getattr(error,'winerror',None)==1314: self.skipTest('Windows symlink privilege unavailable')
                raise
            self.run_haxe(scratch,r'''
Sys.setCwd(Sys.args()[0]);
var chart:Dynamic={player1:"unique-player",stage:"room"};
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=0) throw "symlink installed owner accepted";
ImportIO.begin(Sys.getCwd(),Sys.args()[1]);
if(ImportInstalledDependencyRoots.resolve(Sys.getCwd()+"/addon","Psych Engine",chart).providers.length!=0) throw "staged view accepted symlink owner";
ImportIO.end();
''',[install,install/'import-cache/staging/test'])

    def test_real_completed_record_read_only(self):
        install=ROOT/'tmp/addon-native/CammieEngine-windows-x64'
        addon=ROOT.parent/'fnf_example_mods/psych/Ugh Moment'
        if not (install/'import-cache/records').is_dir() or not addon.is_dir(): self.skipTest('private completed install fixture unavailable')
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as temp:
            self.run_haxe(Path(temp),r'''
Sys.setCwd(Sys.args()[0]);
var chart=haxe.Json.parse(sys.io.File.getContent(Sys.args()[1]+"/data/ugh/ugh.json"));
var result=ImportInstalledDependencyRoots.resolve(Sys.args()[1],"Psych Engine",chart);
if(result.providers.length!=1 || result.providers[0].owner.indexOf("assets/imported_mods/")!=0) throw "completed retained installed base was not resolved: "+result.diagnostics.join(";");
''',[install,addon])


if __name__=='__main__': unittest.main()
