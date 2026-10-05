"""Active Psych song companions inherit only their selected manifest owner."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_nv_multifield_routes import method
ROOT=Path(__file__).resolve().parents[2]

class PsychSongCompanionOwnerTest(unittest.TestCase):
    def test_real_owner_resolver_and_settings_validation(self):
        resolver=method((ROOT/'source/PlayState.hx').read_text(),'function compatPsychOwnerForScript(')
        fixture=r'''import sys.FileSystem;
class ImportEngine {public static var PSYCH='Psych Engine';}
class Main {
 var selected='assets/imported_mods/addon';var directory='assets/data/active';
 function getCompatScriptManifest():{roots:Array<{engine:String,path:String}>} return {roots:[{engine:ImportEngine.PSYCH,path:'assets/imported_mods/base'},{engine:ImportEngine.PSYCH,path:selected}]};
 function selectedPsychSkinRoot():String return selected;
 function currentSongDataFolder():String return directory;
 __RESOLVER__
 public function new(){}
 static function check(v:Bool,label:String):Void if(!v)throw label;
 static function main(){
 var h=new Main();var origin='assets/data/active/script.lua';
 check(h.compatPsychOwnerForScript(origin)==h.selected,'active native companion owner');
 check(h.compatPsychOwnerForScript(FileSystem.fullPath(origin))==h.selected,'absolute source origin');
 check(h.compatPsychOwnerForScript(origin.split('/').join('\\'))==h.selected,'backslash source origin');
 check(h.compatPsychOwnerForScript('assets/imported_mods/base/stages/stage.lua')=='assets/imported_mods/base','physical base stage owner wins');
 var provider='assets/imported_mods/provider/scripts/results.lua';
 check(PsychModSettingCompat.ownerForScriptRoots(provider,['assets/imported_mods/provider'])=='assets/imported_mods/provider','physical provider stays its owner');
 check(h.compatPsychOwnerForScript(provider)==null,'unlisted provider not claimed by selected addon');
 for(bad in ['assets/scripts/global.lua','assets/data/other/script.lua','assets/data/active-prefix/script.lua','assets/data/active/../active/script.lua','assets/data/active/./script.lua','assets/data/active/missing.lua','assets/data/active','assets/imported_mods/unrelated/scripts/source.lua'])
 check(h.compatPsychOwnerForScript(bad)==null,'rejected origin '+bad);
 check(PsychModSettingCompat.ownerForSongCompanion(origin,h.selected,'assets/data')==null,'data root not companion context');
 check(PsychModSettingCompat.ownerForSongCompanion(origin,h.selected,'assets/data/active/nested')==null,'only active top-level song directory context');
 check(PsychModSettingCompat.ownerForSongCompanion(origin,'assets/imported_mods/missing',h.directory)==null,'selected owner must exist');
 check(PsychModSettingCompat.ownerForSongCompanion(origin,'assets',h.directory)==null,'native root cannot be selected owner');
 var settings:Dynamic=PsychModSettingCompat.create(origin,h.selected,null,h.directory);
 check(Reflect.callMethod(null,settings,['value'])=='addon','companion reads selected owner settings');
 check(Reflect.callMethod(null,settings,['value','Base'])==null,'package arg cannot query base');
 var denied:Dynamic=PsychModSettingCompat.create(origin,h.selected);check(Reflect.callMethod(null,denied,['value'])==null,'explicit companion proof required');
 denied=PsychModSettingCompat.create('assets/data/other/script.lua',h.selected,null,h.directory);check(Reflect.callMethod(null,denied,['value'])==null,'settings cannot map another song');
 var direct:Dynamic=PsychModSettingCompat.create('assets/imported_mods/base/stages/stage.lua','assets/imported_mods/base',null,h.directory);
 check(Reflect.callMethod(null,direct,['value'])=='base','direct physical settings owner preserved');
 if(FileSystem.exists('assets/imported_mods/escaped-owner/data')) {
  var escaped:Dynamic=PsychModSettingCompat.create('assets/imported_mods/escaped-owner/stages/stage.lua','assets/imported_mods/escaped-owner');
  check(Reflect.callMethod(null,escaped,['value'])==null,'settings directory link escaped its imported owner');
 }
 __SYMLINK_CHECK__
 }
}'''.replace('__RESOLVER__',resolver)
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as directory:
            work=FixturePath(directory)
            for relative in ['assets/data/active/script.lua','assets/data/other/script.lua','assets/data/active-prefix/script.lua','assets/scripts/global.lua','assets/imported_mods/base/stages/stage.lua','assets/imported_mods/provider/scripts/results.lua','assets/imported_mods/unrelated/scripts/source.lua']:
                path=work/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('--fixture')
            for owner in ['base','addon']:
                path=work/'assets/imported_mods'/owner;path.mkdir(parents=True,exist_ok=True);(path/'data').mkdir(exist_ok=True)
                (path/'data/settings.json').write_text(json.dumps({'value':owner}))
                (path/'pack.json').write_text(json.dumps({'name':owner.title()}))
            escaped_owner=work/'assets/imported_mods/escaped-owner'
            (escaped_owner/'stages').mkdir(parents=True)
            (escaped_owner/'stages/stage.lua').write_text('--fixture')
            escaped_settings=work/'outside-owner-settings'
            escaped_settings.mkdir()
            (escaped_settings/'settings.json').write_text(json.dumps({'value':'outside'}))
            helper=(ROOT/'source/CompatCanonicalPath.hx').read_text()
            if os.name=='nt':
                # Eval fullPath is lexical on Windows. Supply the canonical OS
                # filesystem dependency; production C++ uses its final-target API.
                helper=helper.replace('var result = FileSystem.fullPath(path);','var result = CanonicalWindowsTestPath.resolve(path);')
                (work/'CanonicalWindowsTestPath.hx').write_text('class CanonicalWindowsTestPath {public static function resolve(path:String):String {var p=new sys.io.Process("python",["-c","import os,sys; print(os.path.realpath(sys.argv[1]))",path]);var value=StringTools.trim(p.stdout.readAll().toString());var code=p.exitCode();p.close();if(code!=0)throw "canonical path probe failed";return value;}}',newline='\n')
            (work/'CompatCanonicalPath.hx').write_text(helper,newline='\n')
            symlink_check=''
            try:
                (work/'assets/data/active/escape.lua').symlink_to(work/'assets/data/other/script.lua')
                symlink_check="check(h.compatPsychOwnerForScript('assets/data/active/escape.lua')==null,'file symlink escape');"
            except OSError:pass
            if os.name=='nt':
                for link,target in [(work/'assets/data/linked',work/'assets/data/other'),(work/'assets/imported_mods/linked',work/'assets/imported_mods/base')]:
                    quote=lambda value:"'"+str(value).replace("'","''")+"'"
                    setup=subprocess.run(['powershell','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(link)+' -Target '+quote(target)+' | Out-Null'],capture_output=True,text=True,timeout=20)
                    self.assertEqual(setup.returncode,0,setup.stdout+setup.stderr)
                quote=lambda value:"'"+str(value).replace("'","''")+"'"
                setup=subprocess.run(['powershell','-NoProfile','-Command','New-Item -ItemType Junction -Path '+quote(escaped_owner/'data')+' -Target '+quote(escaped_settings)+' | Out-Null'],capture_output=True,text=True,timeout=20)
                self.assertEqual(setup.returncode,0,setup.stdout+setup.stderr)
                symlink_check+="check(PsychModSettingCompat.ownerForSongCompanion('assets/data/linked/script.lua',h.selected,'assets/data/linked')==null,'directory junction redirects active song');"
                symlink_check+="check(PsychModSettingCompat.ownerForSongCompanion(origin,'assets/imported_mods/linked',h.directory)==null,'selected owner junction redirects pack');"
                symlink_check+="check(PsychModSettingCompat.ownerForScript('assets/imported_mods/linked/stages/stage.lua','assets/imported_mods/linked')==null,'direct script owner junction redirects pack');"
            else:
                try:
                    (escaped_owner/'data').symlink_to(escaped_settings,target_is_directory=True)
                except OSError:
                    pass
            (work/'Main.hx').write_text(fixture.replace('__SYMLINK_CHECK__',symlink_check),newline='\n')
            result=subprocess.run([*HAXE_COMMAND,'-cp',str(ROOT/'source'),'-cp',str(ROOT/'.haxelib/tjson/1,4,0'),'-cp',directory,'-main','Main','--interp'],cwd=directory,capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('CompatCanonicalPath.resolve(path)',(ROOT/'source/PsychModSettingCompat.hx').read_text())
        native=(ROOT/'source/CompatCanonicalPath.hx').read_text()
        self.assertIn('GetFinalPathNameByHandleW(handle',native)
        self.assertIn('FILE_FLAG_BACKUP_SEMANTICS',native)
        self.assertIn('CloseHandle(handle);',native)

if __name__=='__main__':unittest.main()
