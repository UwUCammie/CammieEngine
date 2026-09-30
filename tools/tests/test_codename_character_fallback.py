"""Pin Codename's owner-scoped DEFAULT_CHARACTER runtime fallback."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HAXE = ROOT / ".tools/haxe/haxe"


class CodenameCharacterFallbackTest(unittest.TestCase):
    def test_configured_default_and_owner_isolation(self):
        fixture = r'''
class Main {
 static function main():Void {
  var files:Map<String,String> = new Map();
  var put = function(owner:String, path:String, value:String):Void
   files.set(owner+":"+path,value);
  var resolve = function(owner:String, path:String):Null<String>
   return files.exists(owner+":"+path) ? path : null;
  var read = function(owner:String, path:String):String {
   var value=files.get(owner+":"+path);
   if(value==null) throw "owner file missing: "+owner+":"+path;
   return value;
  };
  var dark="<character name=\"dark\"/>";
  var custom="<character sprite=\"owner-custom\"/>";
  var bf="<character sprite=\"owner-bf\"/>";
  put("one","data/config/modpack.ini","[Flags]\nDEFAULT_CHARACTER=custom\n");
  put("one","data/characters/custom.xml",custom);
  put("two","data/config/modpack.ini","[Flags]\nDEFAULT_CHARACTER=bf\n");
  put("two","data/characters/bf.xml",bf);
  put("two","data/characters/dark.xml",dark);
  put("isolated","data/config/modpack.ini","[Flags]\nDEFAULT_CHARACTER=custom\n");
  put("foreign","data/characters/custom.xml",custom);
  var fromOne=CodenameCharacterFallback.resolve("one","pico-dark",resolve,read);
  if(fromOne==null || !fromOne.usedFallback || !fromOne.configuredFallback
    || fromOne.definitionId!="custom" || fromOne.xmlText!=custom
    || fromOne.requestedId!="pico-dark") throw "configured owner fallback "+haxe.Json.stringify(fromOne);
  var exact=CodenameCharacterFallback.resolve("two","dark",resolve,read);
  if(exact==null || exact.usedFallback || exact.definitionId!="dark" || exact.xmlText!=dark)
   throw "exact owner XML must win";
  var unavailable=CodenameCharacterFallback.resolve("isolated","gf-dark",resolve,read);
  if(unavailable==null || unavailable.definitionId!=null || unavailable.usedFallback
    || unavailable.diagnostic==null) throw "fallback borrowed from another owner";
  put("three","data/characters/bf.xml",bf);
  var engineDefault=CodenameCharacterFallback.resolve("three","gf-dark",resolve,read);
  if(engineDefault==null || !engineDefault.usedFallback || engineDefault.configuredFallback
    || engineDefault.definitionId!="bf") throw "engine default bf not used";
  put("four","data/config/modpack.ini","[Flags]\nDEFAULT_CHARACTER=../foreign\n");
  put("four","data/characters/bf.xml",bf);
  var unsafe=CodenameCharacterFallback.resolve("four","missing",resolve,read);
  if(unsafe==null || unsafe.definitionId!=null || !unsafe.configuredFallback
    || unsafe.diagnostic==null) throw "unsafe override silently replaced";
 }
}
'''
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as folder:
            work = Path(folder)
            (work / "Main.hx").write_text(fixture)
            result = subprocess.run([str(HAXE), "-cp", str(ROOT / "source"), "-cp", str(work),
                                     "--run", "Main"], cwd=ROOT,
                                    env={**os.environ, "TMPDIR": str(work)},
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
