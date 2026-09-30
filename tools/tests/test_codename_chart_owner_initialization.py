"""Direct chart launches initialize owner globals before authored note creation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.tests.test_codename_global_script_diagnostic_context import extract_method

ROOT = Path(__file__).resolve().parents[2]


class CodenameChartOwnerInitializationTest(unittest.TestCase):
    def test_owner_lifecycle_for_direct_repeat_foreign_and_failed_launches(self):
        source = (ROOT / 'source/CodenameModRuntime.hx').read_text()
        helper = extract_method(source, '\tpublic static function synchronizeChartOwner(')
        fixture = '''class Main {
 static var owner:String='';
 static var globalFailure:String='';
 static var calls:Array<String>=[];
 static function activeRoot():String return owner;
 static function isActiveOwner(root:String):Bool return owner==root;
 static function clearActiveOwner():Void { calls.push('destroy:'+owner); owner='';globalFailure=''; }
 static function activateChartOwner(root:String):Bool {
  calls.push('load:'+root);
  if(root=='missing') return false;
  owner=root;return true;
 }
''' + helper + '''
 static function main():Void {
  if(!synchronizeChartOwner('first')) throw 'initial selection';
  if(!synchronizeChartOwner('first')) throw 'repeat selection';
  if(calls.join(',')!='load:first') throw 'same owner reinitialized';
  if(!synchronizeChartOwner('second')) throw 'foreign selection';
  if(calls.join(',')!='load:first,destroy:first,load:second') throw 'foreign lifecycle';
  if(!synchronizeChartOwner(null) || activeRoot()!='') throw 'native retained owner';
  var count=calls.length;
  synchronizeChartOwner('');
  if(calls.length!=count) throw 'empty native session destroyed again';
  synchronizeChartOwner('third');
  if(synchronizeChartOwner('missing') || activeRoot()!='') throw 'failed selection leaked owner';
  if(calls[calls.length-2]!='destroy:third' || calls[calls.length-1]!='load:missing')
   throw 'failed selection order';
  synchronizeChartOwner('retry');
  globalFailure='constructor failed';
  count=calls.length;
  synchronizeChartOwner('retry');
  if(calls.length!=count+2 || calls[count]!='destroy:retry' || calls[count+1]!='load:retry')
   throw 'failed global constructor did not retry';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
            Path(folder, 'Main.hx').write_text(fixture)
            result = subprocess.run([str(ROOT / '.tools/haxe/haxe'), '-cp', folder,
                                     '--run', 'Main'], cwd=ROOT, capture_output=True,
                                    text=True, timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_create_initializes_before_character_and_note_scripts(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        create = extract_method(source, '\toverride public function create() {')
        activate = 'CodenameModRuntime.synchronizeChartOwner(codenameSelectedRoot());'
        self.assertEqual(create.count(activate), 1)
        self.assertLess(create.index('clearScriptOwnership();'), create.index(activate))
        self.assertLess(create.index(activate), create.index('gf = addCharacter('))
        self.assertLess(create.index(activate), create.index('generateSong('))


if __name__ == '__main__':
    unittest.main()
