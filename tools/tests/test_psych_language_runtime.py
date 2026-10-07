"""Behavior of the owner-scoped Psych Language parser and lookup service."""
import subprocess
import tempfile
import unittest

from haxe_test_support import FixturePath as Path, HAXE_COMMAND, TEST_TMP

ROOT = Path(__file__).resolve().parents[2]


class PsychLanguageRuntimeTest(unittest.TestCase):
    def test_language_parser_lookup_reload_alphabet_and_owner_guards(self):
        fixture = r'''
import PsychLanguageRuntime.PsychLanguageHost;

class OwnerPrefs {
 public var data:Dynamic;
 public var defaultData:Dynamic;
 public function new(language:String,defaultLanguage:String) {
  data={language:language};defaultData={language:defaultLanguage};
 }
}
class Hooks {
 public var active:Bool=true;
 public var lines:Map<String,Array<String>>=new Map();
 public var loads:Array<String>=[];
 public var languages:Array<String>=[];
 public var reports:Array<String>=[];
 public function new() {}
 public function host():PsychLanguageHost return {
  ownerActive:function():Bool return active,
  mergedLines:function(language:String):Array<String> {
   languages.push(language);
   var source=lines.get(language);
   return source==null?[]:source.copy();
  },
  loadAlphabetData:function(path:String):Void loads.push(path),
  report:function(message:String):Void reports.push(message)
 };
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function expectThrow(fn:Void->Void,fragment:String):Void {
  var caught=false;
  try fn() catch(error:Dynamic) caught=Std.string(error).indexOf(fragment)>=0;
  check(caught,'expected exception containing '+fragment);
 }
 static function main():Void {
  var hookA=new Hooks();
  var hookB=new Hooks();
  var prefsA=new OwnerPrefs('fr-CA','en-US');
  var prefsB=new OwnerPrefs('en-US','en-US');
  hookA.lines.set('fr-CA',[
   'Français',
   'greeting: "Base {1}"',
   'same: "base"',
   'punctuation_test: "normalized"',
   'missing_quotes: no quote',
   'short',
   '// ignored comment',
   'images/alphabet: "images/base-alphabet.png"'
  ].concat([
   'same: "mod"',
   'greeting: "Salut {1}, {2}!"',
   'images/alphabet: "images/mod-alphabet.png"',
   'escaped: "first'+String.fromCharCode(92)+'nsecond"'
  ]));
  hookB.lines.set('en-US',['English','greeting: "Other owner"']);

  var runtimeA=new PsychLanguageRuntime('assets/imported_mods/language-a',prefsA,hookA.host());
  var runtimeB=new PsychLanguageRuntime('assets/imported_mods/language-b',prefsB,hookB.host());
  check(runtimeA.defaultLangName=='English (US)',
   'the source default language display name must be retained');
  runtimeA.reloadPhrases();
  runtimeB.reloadPhrases();
  check(runtimeA.getPhrase('same')=='mod'
   && runtimeA.getPhrase('greeting',null,['Rin','two'])=='Salut Rin, two!'
   && runtimeA.getPhrase('punctuation test!?')=='normalized',
   'ordered phrase rows, key normalization and dynamic placeholder substitution must match the donor');
  check(runtimeA.getPhrase('unknown','fallback')=='fallback'
   && runtimeA.getPhrase('unknown')=='unknown',
   'missing phrases use the supplied default, then the original key');
  check(runtimeA.getFileTranslation(' IMAGES/ALPHABET ')=='images/mod-alphabet.png'
   && runtimeA.getFileTranslation('missing/path')=='missing/path',
   'file translation uses trimmed lowercase lookup and leaves misses unchanged');
  check(runtimeA.getPhrase('escaped')=='first\nsecond'
   && hookA.loads.join(',')=='mod-alphabet',
   'escaped newline decoding and translated alphabet path stripping must match source reload');
  check(hookA.languages.join(',')=='fr-CA'
   && hookB.languages.join(',')=='en-US'
   && runtimeB.getPhrase('greeting')=='Other owner'
   && runtimeA.getPhrase('greeting',null,['Rin','two'])=='Salut Rin, two!',
   'same callback names and language keys remain isolated by owner');

  var callsBefore=hookA.languages.length;
  runtimeA.getPhrase('same');
  check(hookA.languages.length==callsBefore,
   'lookups must reuse the parsed owner table instead of probing source registries');
  runtimeA.reloadPhrases();
  check(hookA.languages.length==callsBefore+1 && hookA.loads.length==2,
   'an explicit donor reload rereads the owner-selected language and reloads alphabet data');

  hookA.lines.set('fr-CA',['Français','// no phrase entries','abc','bad: no quotes']);
  runtimeA.reloadPhrases();
  check(prefsA.data.language=='en-US' && runtimeA.getPhrase('same')=='same'
   && hookA.loads[hookA.loads.length-1]=='alphabet',
   'an empty phrase table resets only the owner preference and still runs the alphabet side effect');

  hookA.active=false;
  expectThrow(function() runtimeA.getPhrase('same'),'released');
  expectThrow(function() runtimeA.reloadPhrases(),'released');
  runtimeA.release();runtimeB.release();
  expectThrow(function() runtimeA.getFileTranslation('x'),'released');
  expectThrow(function() runtimeA.defaultLangName,'released');
  expectThrow(function() runtimeB.phrases,'released');

  var invalidHost=false;
  try new PsychLanguageRuntime('assets/imported_mods/invalid',prefsB,null)
  catch(error:Dynamic) invalidHost=Std.string(error).indexOf('complete owner language host')>=0;
  check(invalidHost,'the runtime must reject missing host callbacks instead of installing no-ops');
 }
}
'''
        with tempfile.TemporaryDirectory(prefix="psych-language-runtime-", dir=TEST_TMP) as scratch:
            scratch = Path(scratch)
            (scratch / "Main.hx").write_text(fixture, encoding="utf-8", newline="\n")
            result = subprocess.run(
                [*HAXE_COMMAND, "-cp", str(ROOT / "source"), "-cp", str(scratch),
                 "--main", "Main", "--interp"],
                cwd=ROOT, capture_output=True, text=True, timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
