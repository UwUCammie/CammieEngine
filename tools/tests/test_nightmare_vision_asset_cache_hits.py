"""Nightmare Vision lookup memo and cached graphic hits keep their results."""
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


MAIN = r"""
class Main {
 static function check(value:Bool, message:String):Void if (!value) throw message;
 static function rejected(call:Void->Dynamic):Bool {
  try call() catch (_:Dynamic) return true;
  return false;
 }
 static function main() {
  var root='assets/imported_mods/memo';
  var mod=root+'/images/late.png';
  var core=root+'/__nmv_core/images/late.png';
  var paths=new NightmareVisionPaths(root);
  check(paths.getPath('images/late.png',null,true)==core,'a missing mod file resolves to core');
  sys.io.File.saveContent(mod,'late');
  check(paths.getPath('images/late.png',null,true)==core,'a repeated lookup was not remembered');
  check(paths.getPath('late.png','images',true)==core,'parent folder spelling missed the same lookup');
  check(paths.getPath('images/late.png',null,false)==core,'core-only lookup changed');
  ImportRefreshManager.generation++;
  check(paths.getPath('images/late.png',null,true)==mod,'an import refresh kept a remembered lookup');
  sys.FileSystem.deleteFile(mod);
  check(paths.getPath('images/late.png',null,true)==mod,'a remembered mod path was not reused');
  paths.setCurrentLevel('week1');
  check(paths.getPath('images/late.png',null,true)==core,'a level change kept a remembered lookup');
  sys.io.File.saveContent(mod,'late');
  check(paths.getPath('images/late.png',null,true)==core,'the level lookup was not remembered');
  Sys.sleep(2.2);
  check(paths.getPath('images/late.png',null,true)==mod,'a remembered lookup outlived its lifetime');

  check(paths.scopeAssetPath(root+'/images/late.png')==mod,'owner scope changed');
  check(paths.scopeAssetPath(root+'/images/late.png')==mod,'remembered owner scope changed');
  check(paths.scopeAssetPath('assets/imported_mods/other/images/late.png')==null,'foreign path was scoped');
  check(paths.scopeAssetPath('assets/imported_mods/other/images/late.png')==null,'a foreign miss was remembered as a hit');
  check(paths.scopeAssetPath(null)==null,'a null path was scoped');
  check(rejected(()->paths.getPath('../escape.txt',null,true)),'traversal was accepted');
  check(rejected(()->paths.getPath('../escape.txt',null,true)),'a rejected lookup was remembered');

  var dev=new NightmareVisionPaths(root,null,{inDevMode:true});
  check(dev.getPath('images/late.png',null,true)==mod,'dev mode lookup changed');
  sys.FileSystem.deleteFile(mod);
  check(dev.getPath('images/late.png',null,true)==core,'dev mode remembered a lookup');
  paths.releaseOwnerAssets();
  check(paths.getPath('images/late.png',null,true)==core,'owner release kept remembered lookups');

  var image=root+'/images/hit.png';
  var assets=new NightmareVisionFunkinAssets(paths);
  var first=assets.getGraphicUnsafe(image);
  check(first!=null && assets.cache.currentTrackedGraphics.get(image)==first,'graphic was not tracked');
  for (_ in 0...20) check(assets.getGraphicUnsafe(image)==first,'a cached graphic hit returned another object');
  check(assets.cache.localTrackedAssets.length==1,'repeated hits grew the state-local list');
  first.bitmap=null;
  check(assets.getGraphicUnsafe(image)==first,'a destroyed entry left the original cache path');
  sys.FileSystem.deleteFile(image);
  check(assets.getGraphicUnsafe(image)==null,'a destroyed entry for a deleted file skipped the disk checks');
  check(assets.getGraphicUnsafe(root+'/images')==null,'a directory was returned as a graphic');
  check(assets.getGraphicUnsafe('assets/imported_mods/other/images/hit.png')==null,'a foreign graphic was returned');

  var cache=assets.cache;
  cache.localTrackedAssets.push(root+'/data/manual.txt');
  cache.currentTrackedTexts.set(root+'/data/manual.txt','manual');
  cache.currentTrackedTexts.set(root+'/data/cold.txt','cold');
  cache.trackLocal(root+'/data/manual.txt');
  check(cache.localTrackedAssets.length==2,'a direct list edit was tracked twice');
  cache.clearUnusedMemory();
  check(cache.currentTrackedTexts.exists(root+'/data/manual.txt') && !cache.currentTrackedTexts.exists(root+'/data/cold.txt'),
   'clearUnusedMemory did not follow the state-local list');
 }
}
"""


class NightmareVisionAssetCacheHitsTest(unittest.TestCase):
    def test_lookup_memo_and_graphic_hits(self):
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = FixturePath(directory)
            for name, content in asset_stubs().items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            owner = work / "assets/imported_mods/memo"
            for name in ("__nmv_core/images/late.png", "images/hit.png", "data/manual.txt"):
                path = owner / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture", encoding="utf-8")
            (work / "Main.hx").write_text(MAIN, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_lookup_memo_follows_family_selection_and_global_mods(self):
        # Every step runs well inside the memo lifetime, so only the explicit
        # selection and global mod checks can make these lookups change.
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
  check(paths.getPath('data/shared.txt',null,true)==a+'/data/shared.txt','initial selection');
  mods.currentModDirectory='beta';
  check(paths.getPath('data/shared.txt',null,true)==b+'/data/shared.txt','a selection change kept a remembered lookup');
  check(paths.getPath('data/global-only.txt',null,true)==b+'/__nmv_core/data/global-only.txt','global-only file before globals');
  mods.pushGlobalMods();
  check(mods.globalMods.join(',')=='alpha','global fixture');
  check(paths.getPath('data/global-only.txt',null,true)==a+'/data/global-only.txt','enabling a global mod kept a remembered lookup');
  mods.globalMods=[];
  check(paths.getPath('data/global-only.txt',null,true)==b+'/__nmv_core/data/global-only.txt','replacing the global list kept a remembered lookup');
  mods.globalMods.push('alpha');
  check(paths.getPath('data/global-only.txt',null,true)==a+'/data/global-only.txt','editing the global list in place kept a remembered lookup');
  mods.currentModDirectory='alpha';
  check(paths.getPath('data/shared.txt',null,true)==a+'/data/shared.txt','switching back kept a remembered lookup');
  mods.release();
  var rejected=0;
  for (_ in 0...2) try paths.getPath('data/shared.txt',null,true) catch(e:Dynamic) rejected++;
  check(rejected==2,'a released family resolved from remembered lookups');
 }
}
"""
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = FixturePath(directory)
            for name, content in asset_stubs().items():
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            for label in ("alpha", "beta"):
                files = {
                    "data/shared.txt": label,
                    "__nmv_core/data/shared.txt": "core",
                    "meta.json": '{"global":' + ("true" if label == "alpha" else "false") + "}",
                }
                for name, content in files.items():
                    path = work / "assets/imported_mods" / label / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(content, encoding="utf-8")
            (work / "assets/imported_mods/alpha/data/global-only.txt").write_text("global", encoding="utf-8")
            (work / "Main.hx").write_text(main, encoding="utf-8")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--main", "Main", "--interp"],
                cwd=work, capture_output=True, text=True, timeout=60,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_graphic_hit_checks_the_tracked_cache_before_disk(self):
        source = (ROOT / "source/NightmareVisionFunkinAssets.hx").read_text(encoding="utf-8")
        start = source.index("public function getGraphicUnsafe(")
        body = source[start:source.index("\n\t}", start)]
        self.assertLess(body.index("cache.currentTrackedGraphics.get(selected)"), body.index("!exists(selected)"))
        self.assertEqual(body.count("resolve("), 1)


if __name__ == "__main__":
    unittest.main()
