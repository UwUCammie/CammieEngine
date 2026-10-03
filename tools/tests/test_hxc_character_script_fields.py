"""Execute shared actor-scoped HXC scriptGet/scriptSet routing."""
from haxe_test_support import HAXE_COMMAND
from pathlib import Path
from haxe_test_support import FixturePath as Path
import subprocess
import tempfile
import unittest

from tools.tests.test_psych_character_scope import extract_method

ROOT = Path(__file__).resolve().parents[2]


class HxcCharacterScriptFieldTest(unittest.TestCase):
    def test_creation_hook_reads_and_writes_pending_actor_fields(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\t\tvar bindCharacterStart =')
        end = source.index('\t\tvar startSucceeded =', start)
        creation_binding = source[start:end]
        self.assertLess(source.index('hscriptStates.set(usehaxe,interp);'), start)
        self.assertIn('registerHxcCharacterScope(usehaxe, path + filename, characterRole)', creation_binding)
        methods = '\n'.join(extract_method(source, marker) for marker in (
            'function registerHxcCharacterScope(', 'function hxcCharacterForScope(',
            'function hxcCharacterScopeIsActive(', 'public function hxcCharacterScriptField(',
            'function hxcCharacterRole(', 'function hxcCharacterForRole('))
        fixture = r'''using StringTools;
class Character {
 public var curCharacter:String; public var frames:Dynamic = {};
 public function new(id:String) curCharacter=id;
}
class Interp {public var variables:Map<String,Dynamic>=new Map(); public function new() {}}
class HxcScriptDiscovery {
 public static function characterId(path:String):String return 'pending';
 public static function normalizeToken(name:String):String return name;
}
class Main {
 var hxcCharacterScopeNames:Map<String,String>=new Map();
 var hxcCharacterScopeRoles:Map<String,Array<String>>=new Map();
 var hscriptStates:Map<String,Interp>=new Map();
 var boyfriend:Character; var gf:Character; var dad:Character;
 var hxcGameOverCharacter:Character;
 var hxcCharacterCallbackActor:Character;
 var hxcCharacterCallbackRole:String='';
 function new() {}
 function hxcCharacterRolesForPath(path:String):Array<String> return ['boyfriend'];
''' + methods + r'''
 function run() {
  boyfriend=new Character('old');
  var characterOverride=new Character('pending');
  var characterRole='boyfriend'; var isHxcSource=true;
  var usehaxe='pending-scope'; var path='scripts/characters/'; var filename='wrapper.hxc';
  var interp=new Interp(); interp.variables.set('suffix','initial');
  hscriptStates.set(usehaxe,interp);
''' + creation_binding + r'''
  // Execute the field API in the same creation window as the source hook.
  if(hxcCharacterScriptField(characterOverride,'suffix')!='initial') throw 'creation read lost';
  hxcCharacterScriptField(characterOverride,'suffix',true,'created');
  if(interp.variables.get('suffix')!='created') throw 'creation write lost';
  if(hxcCharacterScriptField(boyfriend,'suffix')!=null) throw 'creation field crossed actor';
  hxcCharacterCallbackActor=previousStartActor; hxcCharacterCallbackRole=previousStartRole;
  if(hxcCharacterScriptField(characterOverride,'suffix')!=null) throw 'pending binding leaked';
  boyfriend=characterOverride;
  if(hxcCharacterScriptField(boyfriend,'suffix')!='created') throw 'installed actor lost creation state';
 }
 static function main() new Main().run();
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            (Path(work) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', work, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_live_actor_fields_exclude_closed_foreign_and_inactive_scopes(self):
        source = (ROOT / 'source/PlayState.hx').read_text()
        start = source.index('\tpublic function hxcCharacterScriptField(')
        end = source.index('\n\t/** Query the live actor', start)
        method = source[start:end]
        actor = (ROOT / 'source/Character.hx').read_text()
        self.assertIn('public function scriptGet(name:String)', actor)
        self.assertIn('public function scriptSet(name:String, value:Dynamic)', actor)
        self.assertIn('hxcCharacterScriptField(this, name, true, value)', actor)
        fixture = r'''class Character { public function new() {} }
class Interp {
 public var variables:Map<String,Dynamic> = new Map();
 public function new(value:String) {variables.set('suffix',value);}
}
class Main {
 var hxcCharacterScopeNames:Map<String,String> = new Map();
 var hscriptStates:Map<String,Interp> = new Map();
 var owners:Map<String,Array<Character>> = new Map();
 var active:Map<String,Bool> = new Map();
 function new() {}
 function hxcCharacterScopeIsActive(scope:String):Bool return active.get(scope) == true;
 function hxcCharacterForScope(scope:String):Array<Character> return owners.get(scope);
 function add(scope:String, actor:Character, value:String, live:Bool=true):Interp {
  var interp = new Interp(value);
  hxcCharacterScopeNames.set(scope,'id'); hscriptStates.set(scope,interp);
  owners.set(scope,[actor]); active.set(scope,live); return interp;
 }
''' + method + r'''
 static function main() {
  var state=new Main(); var player=new Character(); var opponent=new Character();
  var closed=state.add('a-closed',player,'closed'); closed.variables.set('__compatClosed',true);
  var inactive=state.add('b-old',player,'old',false);
  var foreign=state.add('c-opponent',opponent,'opponent');
  var live=state.add('d-player',player,'plain');
  if(state.hxcCharacterScriptField(player,'suffix')!='plain') throw 'wrong read owner';
  if(state.hxcCharacterScriptField(player,'missing')!=null) throw 'missing field invented';
  state.hxcCharacterScriptField(player,'suffix',true,'-costume');
  if(live.variables.get('suffix')!='-costume' || closed.variables.get('suffix')!='closed'
   || inactive.variables.get('suffix')!='old' || foreign.variables.get('suffix')!='opponent')
   throw 'write crossed script ownership';
  state.active.set('d-player',false);
  if(state.hxcCharacterScriptField(player,'suffix')!=null) throw 'stale scope after swap';
  if(state.hxcCharacterScriptField(null,'suffix')!=null) throw 'null actor read';
 }
}'''
        with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as work:
            (Path(work) / 'Main.hx').write_text(fixture, newline='\n')
            result = subprocess.run([*HAXE_COMMAND, '-cp', work, '--run', 'Main'],
                                    cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
