"""Character implementation discovery preserves live checks and skips irrelevant probes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath
from test_import_workflow import extract_method

ROOT = Path(__file__).resolve().parents[2]

class ImportCharacterProbesTest(unittest.TestCase):
    def test_candidate_kinds_and_live_files(self):
        method = extract_method((ROOT / "source/ImportWorkflow.hx").read_text(),
                                "static function characterImplementationFound(")
        fixture = r'''import haxe.io.Path;
using StringTools;
class CharacterProbeFixture {
 static var files:Map<String,Bool> = [];
 static var dirs:Map<String,Bool> = [];
 static var probes = 0;
 static function file(p:String):Bool { probes++; return files.exists(p); }
 static function directory(p:String):Bool return dirs.exists(p);
 METHOD
 static function check(p:String, expected:Bool) {
  var candidates = [p]; var before = candidates.copy();
  if (characterImplementationFound(candidates) != expected) throw "wrong result: " + p;
  if (candidates.length != 1 || candidates[0] != before[0]) throw "searched paths mutated";
 }
 static function main() {
  var ignored = [null,""," ","root/images/custom_chars/a/char.png",
   "root/images/custom_chars/a/char.xml","root/characters/a.xml",
   "root/characters/a.txt","root/characters/a.hxs","root/image.png"];
  for (p in ignored) {
   if (p != null) files.set(p,true);
   check(p,false);
  }
  if (probes != 0) throw "irrelevant candidates touched filesystem";
  var accepted = ["root/characters/a.png","root/characters/a/char.png",
   "ROOT\\CHARACTERS\\A.PNG","root/images/custom_chars/alias.hscript",
   "root/a.hxc","root/a/animation.json","root/a.json","root/a.jsonc","root/a.hscript"];
  for (p in accepted) {
   files = []; dirs = []; probes = 0;
   check(p,false);
   if (probes != 1) throw "eligible file did not receive live check";
   files.set(p,true);
   dirs.set(Path.directory(p),true); dirs.set(Path.withoutExtension(p),true);
   check(p,true);
   files.remove(p); check(p,false);
   files.set(p,true); check(p,true);
   if (probes != 4) throw "filesystem result was cached";
  }
  for (p in ["root/a.json","root/a.jsonc","root/a.hscript","root/a/animation.json"]) {
   files = []; dirs = []; files.set(p,true); check(p,false);
   dirs.set(Path.withoutExtension(p),true); check(p,true);
   dirs.remove(Path.withoutExtension(p)); check(p,false);
  }
  // A folder cannot satisfy the file requirement, and a bare sprite/atlas
  // stays invalid here even when both halves exist (registry checks are separate).
  files = []; dirs = []; dirs.set("root/a.hxc",true); check("root/a.hxc",false);
  files.set("root/images/custom_chars/a/char.png",true);
  files.set("root/images/custom_chars/a/char.xml",true);
  if (characterImplementationFound(["root/images/custom_chars/a/char.png",
   "root/images/custom_chars/a/char.xml"])) throw "bare atlas accepted";
 }
}
'''.replace("METHOD", method)
        with tempfile.TemporaryDirectory() as folder:
            (FixturePath(folder) / "CharacterProbeFixture.hx").write_text(fixture, newline="\n")
            result = subprocess.run([*HAXE_COMMAND,"-cp",folder,"--run","CharacterProbeFixture"],
                                    cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout + result.stderr)
