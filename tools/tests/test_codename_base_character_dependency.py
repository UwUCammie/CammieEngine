"""Pin the owner-scoped Codename installation-character dependency."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameBaseCharacterDependencyTest(unittest.TestCase):
    def test_hl17_plan_and_private_materialization(self):
        donor = Path("/run/media/cammie/External Storage/FNF-Example-Mods/codename/hl17_v3")
        if not (donor / "assets/data/characters/bf.xml").is_file():
            self.skipTest("mounted HL17 example installation is unavailable")
        fixture = r'''
class Main {
 static function main():Void {
  var install=Sys.args()[0]+"/assets";
  var selected=Sys.args()[0]+"/mods/HL17";
  var owner="assets/imported_mods/hl17-install-dry-run";
  var plan=CodenameBaseCharacterDependency.plan(install,"bf");
  if(plan.diagnostic!=null) throw "HL17 base character plan failed: "+plan.diagnostic;
  var expected=["data/characters/bf.xml","images/characters/bf.png","images/characters/bf.xml"];
  var actual:Array<String>=[];
  for(file in plan.files) actual.push(file.destinationRelative);
  actual.sort(Reflect.compare); expected.sort(Reflect.compare);
  if(actual.join("|")!=expected.join("|"))
   throw "unexpected HL17 dependency file set: "+actual.join("|");
  var result=CodenameBaseCharacterDependency.materialize(install,selected,owner,"bf");
  if(result.failed || result.copied!=3) throw "HL17 private materialization failed: "+haxe.Json.stringify(result);
  var resolved=CodenameBaseCharacterDependency.resolveImported(owner,"bf");
  if(resolved==null || resolved.xmlText.indexOf("BF NOTE LEFT0")<0
    || resolved.assetFiles.length!=3) throw "HL17 private receipt did not resolve";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            owner_dir = work / "assets/imported_mods/hl17-install-dry-run"
            owner_dir.mkdir(parents=True)
            preserved = {
                owner_dir / "existing.marker": b"keep this owner file",
                owner_dir / "data/characters/locally-owned.xml": b"<character/>",
            }
            for path, contents in preserved.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(contents)
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main", str(donor)],
                cwd=work,
                env={**os.environ, "TMPDIR": str(work)},
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for path, contents in preserved.items():
                self.assertEqual(path.read_bytes(), contents, str(path))
            copied = owner_dir / "compat-engine-base"
            self.assertEqual(
                sorted(str(path.relative_to(copied)) for path in copied.rglob("*") if path.is_file()),
                [
                    "character-dependency.json",
                    "data/characters/bf.xml",
                    "images/characters/bf.png",
                    "images/characters/bf.xml",
                ],
            )

    def test_materialization_resolution_isolation_and_local_precedence(self):
        fixture = r'''
class Main {
 static function mkdir(path:String):Void {
  if (sys.FileSystem.exists(path)) return;
  var parent=haxe.io.Path.directory(path);
  if(parent!=null && parent!="" && parent!=path) mkdir(parent);
  if(!sys.FileSystem.exists(path)) sys.FileSystem.createDirectory(path);
 }
 static function put(path:String, contents:String):Void {
  mkdir(haxe.io.Path.directory(path)); sys.io.File.saveContent(path,contents);
 }
 static function main():Void {
  var base=Sys.args()[0];
  var install=base+"/install/assets";
  var selected=base+"/install/mods/Selected";
  var owner="assets/imported_mods/selected-owner";
  put(install+"/data/characters/bf.xml","<character sprite=\"base-bf\" icon=\"base\"/>");
  put(install+"/images/characters/base-bf.png","sprite bytes");
  put(install+"/images/characters/base-bf.xml","<TextureAtlas/>");
  mkdir(selected);
  var result=CodenameBaseCharacterDependency.materialize(install,selected,owner,"bf");
  if(result.failed || result.copied!=3 || result.skipped!=0)
   throw "new dependency copy failed: "+haxe.Json.stringify(result);
  var resolved=CodenameBaseCharacterDependency.resolveImported(owner,"bf");
  if(resolved==null || resolved.definitionId!="bf" || resolved.assetRoot!=owner+"/compat-engine-base"
    || resolved.xmlText.indexOf("base-bf")<0 || resolved.assetFiles.length!=3)
   throw "receipt resolution failed";
  var again=CodenameBaseCharacterDependency.materialize(install,selected,owner,"bf");
  if(again.failed || again.copied!=0 || again.skipped!=1) throw "valid receipt should be idempotent";
  var ownerResolve=function(root:String,relative:String):Null<String>
   return CodenameScriptDiscovery.resolveScopedRelative(root,relative);
  var ownerRead=function(root:String,relative:String):String
   return sys.io.File.getContent(root+"/"+relative);
  var dependency=function(root:String,id:String):Null<CodenameBaseCharacterDependency.CodenameBaseCharacterDependencyResolution>
   return CodenameBaseCharacterDependency.resolveImported(root,id);
  var sourceFallback=CodenameCharacterFallback.resolve(owner,"bf",ownerResolve,ownerRead,dependency);
  if(sourceFallback==null || !sourceFallback.usedFallback || sourceFallback.definitionId!="bf"
    || sourceFallback.assetRoot!=owner+"/compat-engine-base")
   throw "missing id equal to DEFAULT_CHARACTER must use trusted dependency";
  var darkFallback=CodenameCharacterFallback.resolve(owner,"dark",ownerResolve,ownerRead,dependency);
  if(darkFallback==null || !darkFallback.usedFallback || darkFallback.definitionId!="bf")
   throw "missing custom character should use selected owner's dependency";
  if(CodenameBaseCharacterDependency.resolveImported("assets/imported_mods/sibling","bf")!=null)
   throw "dependency leaked to a sibling owner";
  put(owner+"/data/characters/bf.xml","<character sprite=\"owner-bf\"/>");
  put(owner+"/images/characters/owner-bf.png","owner sprite");
  var localFallback=CodenameCharacterFallback.resolve(owner,"dark",ownerResolve,ownerRead,dependency);
  if(localFallback==null || !localFallback.usedFallback || localFallback.xmlText.indexOf("owner-bf")<0
    || localFallback.assetRoot!=owner) throw "selected-owner fallback XML must precede installation dependency";
  var localRequest=CodenameCharacterFallback.resolve(owner,"bf",ownerResolve,ownerRead,dependency);
  if(localRequest==null || localRequest.usedFallback || localRequest.xmlText.indexOf("owner-bf")<0)
   throw "selected-owner exact XML must precede dependency";
  var collisionOwner="assets/imported_mods/collision-owner";
  put(collisionOwner+"/compat-engine-base/images/characters/base-bf.png","user bytes");
  var collision=CodenameBaseCharacterDependency.materialize(install,selected,collisionOwner,"bf");
  if(!collision.failed || sys.io.File.getContent(collisionOwner+"/compat-engine-base/images/characters/base-bf.png")!="user bytes")
   throw "unreceipted collision must fail without overwrite";
  var existingOwner=base+"/install/mods/HasDefault";
  put(existingOwner+"/data/characters/bf.xml","<character/>");
  var localImport=CodenameBaseCharacterDependency.materialize(install,existingOwner,
    "assets/imported_mods/local-owner","bf");
  if(localImport.failed || localImport.copied!=0 || localImport.skipped!=1)
   throw "owner-local DEFAULT_CHARACTER must not copy engine-base data";
  mkdir(base+"/outside");
  var symlink=CodenameBaseCharacterDependency.materialize(install,selected,
    "assets/imported_mods/linked-owner","bf");
  if(!symlink.failed) throw "symlink owner root must be rejected";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "outside").mkdir()
            (work / "assets" / "imported_mods").mkdir(parents=True)
            os.symlink(work / "outside", work / "assets" / "imported_mods" / "linked-owner")
            (work / "Main.hx").write_text(fixture, newline='\n')
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(work), "--run", "Main", str(work)],
                cwd=work,
                env={**os.environ, "TMPDIR": str(work)},
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
