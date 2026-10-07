"""Actual family Paths/FunkinAssets with the existing explicit rendering stubs."""
import ast
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


def asset_stubs():
    tree = ast.parse((ROOT / "tools/tests/test_nightmare_vision_source_asset_adapters.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "stubs" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("Shared asset adapter fixture stubs unavailable")


class NvPackageFamilyPathsTest(unittest.TestCase):
    def test_selected_paths_and_borrowed_keys_share_authorized_family(self):
        main = r"""
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function main() {
  var a='assets/imported_mods/alpha';
  var b='assets/imported_mods/beta';
  var session=new NightmareVisionModFamilySession('alpha',a,[{directory:'alpha',root:a},{directory:'beta',root:b}]);
  var mods=new NightmareVisionModsContext(a,'alpha',session);
  var paths=new NightmareVisionPaths(a,null,null,'alpha');
  paths.bindModFamily(mods);
  var assets=new NightmareVisionFunkinAssets(paths);
  var old=paths.image('marker');
  check(paths.getPath('data/shared.txt',null,true)==a+'/data/shared.txt','initial provider');
  mods.currentModDirectory='beta';
  check(paths.root==a,'immutable lease anchor');
  check(paths.getPath('data/shared.txt',null,true)==b+'/data/shared.txt','selected provider');
  check(paths.getCorePath('data/shared.txt')==b+'/__nmv_core/data/shared.txt','selected core');
  check(paths.getTextFromFile('data/shared.txt')=='beta','selected text');
  check(paths.mods('alpha/data/shared.txt')==a+'/data/shared.txt','explicit original directory');
  check(paths.mods('beta/data/shared.txt')==b+'/data/shared.txt','explicit sibling directory');
  check(paths.modFolders('data/shared.txt')==b+'/data/shared.txt','selected direct mod path');
  check(paths.scopeAssetPath('content/alpha/data/shared.txt')==a+'/data/shared.txt','borrowed alias');
  check(paths.scopeAssetPath('content/beta/data/shared.txt')==b+'/data/shared.txt','sibling alias');
  check(paths.getModFolder(b+'/images/marker.png')=='beta','sibling identity');
  check(paths.getModFolder(sys.FileSystem.absolutePath(b+'/images/marker.png'))=='beta','absolute discovery identity');
  check(paths.getModFolder(sys.FileSystem.absolutePath(a+'/images/marker.png'))=='alpha','absolute old identity');
  check(paths.getModFolder(sys.FileSystem.absolutePath('assets/imported_mods/unrelated/images/marker.png'))=='','absolute unrelated identity');
  check(paths.scopeAssetPath('assets/imported_mods/unrelated/data/shared.txt')==null,'unrelated root');
  check(paths.scopeAssetPath('content/unrelated/data/shared.txt')==null,'unrelated alias');
  check(paths.scopeAssetPath(b+'/../unrelated/data/shared.txt')==null,'traversal');
  check(assets.getContent(a+'/data/shared.txt')=='alpha','old borrowed provider still readable');
  var fresh=paths.image('marker');
  check(fresh!=old,'same-name graphics retain distinct identities');
  check(assets.cache.currentTrackedGraphics.exists(a+'/images/marker.png'),'old graphic retained');
  check(assets.cache.currentTrackedGraphics.exists(b+'/images/marker.png'),'new graphic retained');
  check(paths.resolveScript('events/ping').path==b+'/events/ping.hx','selected script lookup');
  check(paths.resolveScript(a+'/events/ping').path==a+'/events/ping.hx','explicit original script');
  check(paths.resolveScript(b+'/events/ping').path==b+'/events/ping.hx','explicit sibling script');
  var rejected=false;try mods.currentModDirectory='unrelated' catch(e:Dynamic) rejected=true;
  check(rejected && mods.currentModDirectory=='beta','failed selection preserves current provider');
  mods.pushGlobalMods();
  check(mods.globalMods.join(',')=='alpha','enabled global members');
  check(paths.getTextFromFile('data/global-only.txt')=='global-alpha','global fallback');
  check(paths.getTextFromFile('data/shared.txt')=='beta','selected package precedes globals for lookup');
  var listing=paths.listAllFilesInDirectory('data');
  check(listing.indexOf(b+'/__nmv_core/data/shared.txt')<listing.indexOf(a+'/data/shared.txt'),'core-first listing');
  check(listing.indexOf(a+'/data/shared.txt')<listing.indexOf(b+'/data/shared.txt'),'globals precede selected listing');
  mods.globalMods=[];
  mods.currentModDirectory=null;
  check(paths.getPath('data/shared.txt',null,true)==a+'/__nmv_core/data/shared.txt','null selection uses core only');
  rejected=false;try paths.modFolders('data/shared.txt') catch(e:Dynamic) rejected=true;
  check(rejected,'null selection must not keep old package implicitly');
  mods.currentModDirectory='beta';
  paths.releaseOwnerAssets();
  var oldRemovals=0;var newRemovals=0;
  for(g in flixel.FlxG.bitmap.removed){if(g==old)oldRemovals++;if(g==fresh)newRemovals++;}
  check(oldRemovals==1 && newRemovals==1,'each family graphic released once');
  mods.release();
  rejected=false;try paths.getPath('data/shared.txt',null,true) catch(e:Dynamic) rejected=true;
  check(rejected,'released family cannot resolve more IO');
  var missing=new NightmareVisionPaths(a);
  missing.bindModFamily(new NightmareVisionModsContext(a));
  check(missing.getModFolder(a+'/images/marker.png')=='alpha','missing-label singleton basename');
  check(missing.getModFolder(sys.FileSystem.absolutePath(a+'/images/marker.png'))=='alpha','absolute singleton identity');
 }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work=FixturePath(directory)
            for name, content in asset_stubs().items():
                path=work/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding="utf-8")
            for label in ("alpha","beta","unrelated"):
                for name,content in {"data/shared.txt":label,"__nmv_core/data/shared.txt":"core","images/marker.png":"image",'events/ping.hx':'function ping() {}','meta.json':'{"global":'+('true' if label=='alpha' else 'false')+'}'}.items():
                    path=work/"assets/imported_mods"/label/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding="utf-8")
            (work/"assets/imported_mods/alpha/data/global-only.txt").write_text("global-alpha",encoding="utf-8")
            (work/"Main.hx").write_text(main,encoding="utf-8")
            result=subprocess.run([*HAXE_COMMAND,"-cp",str(ROOT/"source"),"-cp",str(work),"--main","Main","--interp"],cwd=work,capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_host_binds_the_same_context_before_source_scripts(self):
        host=(ROOT/"source/PlayState.hx").read_text(encoding="utf-8")
        self.assertIn("ImportPackageFamilyCatalog.forOwner(root)",host)
        self.assertIn("? entry.path : entry == null",host)
        self.assertIn("paths.getModFolder(entryPath, 'scripts')",host)
        self.assertIn("nightmareVisionPaths.bindModFamily(nightmareVisionActiveMods)",host)
        self.assertLess(host.index("nightmareVisionPaths.bindModFamily(nightmareVisionActiveMods)"),host.index("sourceSession.mountPlugins()"))
        session=(ROOT/"source/NightmareVisionStateSession.hx").read_text(encoding="utf-8")
        self.assertIn("PlayState.seedNightmareVisionCommon(interp, paths, prefs, runtime, mods, difficulty",session)
