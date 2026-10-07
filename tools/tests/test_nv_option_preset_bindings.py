"""The actual preset shares option state and reads its script's live modFolder."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from haxe_test_support import HAXE_COMMAND, FixturePath

ROOT = Path(__file__).resolve().parents[2]


class NvOptionPresetBindingsTest(unittest.TestCase):
    def test_two_presets_share_values_with_live_script_admission(self):
        files = {
            'flixel/input/keyboard/FlxKey.hx': '''package flixel.input.keyboard;
class FlxKey {public static var toStringMap:Map<Int,String>=[]; public static var fromStringMap:Map<String,Int>=[];}''',
            'CodenameFlxKeyFacade.hx': 'class CodenameFlxKeyFacade {public static function snapshot():Dynamic return {};}',
            'NightmareVisionSourceRandom.hx': 'class NightmareVisionSourceRandom {}',
            'Main.hx': r'''
class Preset {
 public var variables:Map<String,Dynamic>=[];
 public var imports:Map<String,Dynamic>=[];
 public var ownerSave:Dynamic;
 public function new(script:Dynamic) variables.set('script',script);
 public function bindImport(name:String,value:Dynamic):Void imports.set(name,value);
}
class Main {
 static function check(ok:Bool,message:String):Void if(!ok) throw message;
 static function main() {
  var a='assets/imported_mods/alpha', b='assets/imported_mods/beta';
  var data:Map<String,Dynamic>=[];
  function save(root:String):Dynamic return {ownerKey:root,getField:function(name:String):Dynamic return data.get(root),
   setField:function(name:String,value:Dynamic):Dynamic {data.set(root,value);return value;},flush:function():Void {}};
  var backend=new NightmareVisionSourceOptions(a,save(a));
  backend.bindFamily(function(label) return label=='alpha'?a:label=='beta'?b:null,save,function() return []);
  backend.init('alpha');
  var script:Dynamic={modFolder:'alpha'};
  var first=new Preset(script), second=new Preset({modFolder:'alpha'});
  NightmareVisionSourceBindings.bindOwner(first,a,'alpha',null,backend);
  NightmareVisionSourceBindings.bindOwner(second,a,'alpha',null,backend);
  var create:Dynamic=first.variables.get('newOption');
  create('first','bool',true);
  var api:NightmareVisionModOptionsFacade=cast second.imports.get('funkin.data.ModOptions');
  check(api.getValue('first')==true,'shared source table across presets');
  api.setValue('first',false);
  var read:Dynamic=first.variables.get('getOption');
  check(read('first')==false,'source value changes are live');
  script.modFolder='beta';
  create('not-admitted','bool',true);
  check(api.get('not-admitted')==null,'newOption reads captured script live modFolder');
  backend.init('beta');
  create('second','bool',true);
  check(api.currentMod=='beta' && api.getValue('second')==true,'same facade follows selected table');
  var rejected=false;
  try api.currentMod='foreign' catch(error:Dynamic) rejected=true;
  check(rejected && api.currentMod=='beta','foreign source namespace rejected');
 }
}''',
        }
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as temp:
            folder = FixturePath(temp)
            for name, content in files.items():
                target = folder / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8')
            result = subprocess.run([*HAXE_COMMAND, '-cp', str(ROOT / 'source'), '-cp', str(folder),
                                     '--interp', '-main', 'Main'], cwd=temp, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
