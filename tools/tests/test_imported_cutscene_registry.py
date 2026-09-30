"""A Modding Plus cutscene loads only from its selected chart owner."""

from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ImportedCutsceneRegistryTest(unittest.TestCase):
    def test_selected_owner_collision_and_missing_source_fail_closed(self):
        fixture = r'''import haxe.Json;
class Main {
 static var files:Map<String,String> = new Map();
 static function exists(path:String):Bool return files.exists(path);
 static function read(path:String):String return files.get(path);
 static function parse(source:String):Dynamic return Json.parse(source);
 static function eq(actual:Dynamic, wanted:Dynamic):Void
   if (actual != wanted) throw Std.string(actual) + " != " + Std.string(wanted);
 static function main():Void {
   var own = "assets/imported_mods/owner-a";
   var foreign = "assets/imported_mods/owner-b";
   var manifest = "assets/data/slaughter/compatScripts.json";
   files.set(manifest, Json.stringify({version:1,selectedRoot:own,roots:[
     {engine:"Modding Plus",path:own},{engine:"Modding Plus",path:foreign}]}));
   files.set(own + "/images/custom_cutscenes/cutscenes.json",
     '{"monster":"owned-monster"}');
   files.set(own + "/images/custom_cutscenes/owned-monster.hscript", "owned");
   files.set(foreign + "/images/custom_cutscenes/cutscenes.json",
     '{"monster":"foreign-monster"}');
   files.set("assets/images/custom_cutscenes/cutscenes.json",'{"monster":"global-monster"}');
   var result:Dynamic = ImportedCutsceneRegistry.resolve("slaughter", "MONSTER", exists, read, parse);
   eq(result.script,"owned-monster");
   eq(result.directory,own + "/images/custom_cutscenes/");
   eq(result.unavailable,false);
   files.remove(own + "/images/custom_cutscenes/owned-monster.hscript");
   result = ImportedCutsceneRegistry.resolve("slaughter", "monster", exists, read, parse);
   eq(result.unavailable,true);
   eq(result.reason,"script-unavailable");
   files.remove(own + "/images/custom_cutscenes/cutscenes.json");
   result = ImportedCutsceneRegistry.resolve("slaughter", "monster", exists, read, parse);
   eq(result.reason,"registry-unavailable");
   if (ImportedCutsceneRegistry.resolve("../slaughter", "monster", exists, read, parse) != null)
     throw "unsafe storage folder accepted";
   if (ImportedCutsceneRegistry.resolve("slaughter", "../monster", exists, read, parse) != null)
     throw "unsafe cutscene key accepted";
   files.set(manifest, Json.stringify({version:1,selectedRoot:own,roots:[
     {engine:"Psych Engine",path:own}]}));
   if (ImportedCutsceneRegistry.resolve("slaughter", "monster", exists, read, parse) != null)
     throw "foreign engine entered Modding Plus cutscene lookup";
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as directory:
            work = Path(directory)
            (work / "Main.hx").write_text(fixture)
            for name in ("ImportedCutsceneRegistry", "CompatScriptManifest", "ImportSongOwnership", "ImportEngine"):
                (work / f"{name}.hx").write_text((ROOT / "source" / f"{name}.hx").read_text())
            process = subprocess.run([str(ROOT / ".tools/haxe/haxe"), "-cp", str(work),
                                      "--run", "Main"], cwd=ROOT, text=True,
                                     capture_output=True, timeout=45)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
