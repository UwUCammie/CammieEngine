"""Native Change Character runs one role-parameterised body for every slot.

The fixture compiles the real switchCharacter with recording stubs and checks
the exact call trace for each role, layering mode and control flag. The traces
were recorded from the three-case version before it was folded into one body,
so the shared body has to keep every step and its order. The last two traces
were worked out by hand from that version: it re-read the role field after the
character's scripts ran, so an actor a script put in the role is the one the
rest of the swap places and announces.
"""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from test_psych_charting_handoff import method

ROOT = Path(__file__).resolve().parents[2]


def swap_methods(play: str) -> str:
	parts = [method(play, '\tfunction switchCharacter(charTo:String, charState:String)')]
	for marker in ('public function characterForRole(role:String)', 'static function characterGroupRole(role:String)',
			'function setCharacterForRole(role:String, actor:Character)',
			'function layerSwappedCharacter(role:String, actor:Character)',
			'function characterInSlot(slot:String)'):
		if marker in play:
			parts.append(method(play, marker))
	return '\n'.join(parts)


FIXTURE = r'''
class RuntimeSmokeHarness {
 public static function beginCharacterSwap():Float return 0;
 public static function markCharacterSwap(at:Float, name:String, role:String):Void State.log.push('smoke:' + name + ':' + role);
}
class PsychCharacterChangeEvent { public static function role(r:String):Int return 0; }
class Point { public var x:Float = 1; public var y:Float = 1; public function new() {}
 public function set(x:Float, y:Float):Void { this.x = x; this.y = y; State.log.push('scroll:' + x + ',' + y); } }
class Character {
 public var curCharacter:String; public var likeGf:Bool = false; public var alpha:Float = 1; public var visible:Bool = true;
 public var x:Float = 0; public var y:Float = 0; public var beingControlled:Bool = false; public var characterType:String = '';
 public var scrollFactor = new Point();
 public function new(name:String) curCharacter = name;
 public function destroy():Void State.log.push('destroy:' + curCharacter);
 public function setPosition(x:Float, y:Float):Void { this.x = x; this.y = y; State.log.push('setPosition:' + curCharacter + ':' + x + ',' + y); }
}
class Info { public var x:Float = 7; public var y:Float = 9; public var zIndex:Int; public function new(z:Int) zIndex = z; }
class Stage {
 public var gfInfo = new Info(0); public var presented:Map<String, Bool> = new Map(); public var z:Int = -69;
 public function new() {}
 public function applyVSliceCharacterPresentation(role:String, actor:Character):Bool {
  State.log.push('present:' + role + ':' + actor.curCharacter); return presented.get(role) == true; }
 public function rebindCodenameActor(a:Character, b:Character):Void State.log.push('rebindCodename:' + a.curCharacter + '>' + b.curCharacter);
 public function rebindCharacterZ(role:String, a:Character, b:Character):Void State.log.push('rebindZ:' + role + ':' + b.curCharacter);
 public function getInfo(role:String):Info return new Info(z);
 public function refresh():Void State.log.push('refresh');
}
class Actors { public function new() {}
 public function rebindBorrowed(a:Character, b:Character):Bool { State.log.push('borrowed:' + b.curCharacter); return true; } }
class State {
 public static var log:Array<String> = [];
 public var boyfriend:Character = new Character('bf'); public var dad:Character = new Character('dad'); public var gf:Character = new Character('gf');
 public var nightmareVisionScripts:Dynamic = null; public var sourceScoreOwner:Bool = false;
 public var opponentPlayer:Bool = false; public var demoMode:Bool = false; public var duoMode:Bool = false; public var soloMode:Bool = false;
 public var psychStageCharacterRoot:String = null; public var curStage:Stage = new Stage(); public var codenameActors:Actors = new Actors();
 public var iconRPC:String = ''; public var members:Array<Character> = [];
 public function new() { members = [gf, dad, boyfriend]; }
 function publishNightmareVisionCharacter(n:String, t:Int):Void log.push('nv');
 function forgetPsychRoleCharacter(a:Character):Void log.push('forget:' + (a == null ? 'null' : a.curCharacter));
 function detachIdlePsychRoleCharacter(s:String, n:String):Void log.push('detach:' + s + ':' + n);
 function compatClearCharacterTrail(a:Dynamic):Void log.push('clearTrail:' + a.curCharacter);
 function compatEnableCharacterTrail(a:Dynamic):Void log.push('enableTrail:' + a.curCharacter);
 function remove(a:Character, ?splice:Bool = false):Character { log.push('remove:' + a.curCharacter + ':' + splice); members.remove(a); return a; }
 function add(a:Character):Character { log.push('add:' + a.curCharacter); members.push(a); return a; }
 function insert(i:Int, a:Character):Character { log.push('insert:' + i + ':' + a.curCharacter); members.insert(i, a); return a; }
 function takeSwapCharacter(slot:String, name:String):Character { log.push('take:' + slot + ':' + name); var c = new Character(name); c.likeGf = name.indexOf('likegf') >= 0; return c; }
 public var loadReplace:String = null; public var addedReplace:String = null;
 function replaceRole(role:String, name:String):Void switch (role) {
  case 'dad': dad = new Character(name); case 'gf': gf = new Character(name); default: boyfriend = new Character(name); }
 function loadHxcCharacterCompat(name:String, role:String, a:Character):Void {
  log.push('hxc:' + name + ':' + role + ':' + a.characterType); if (loadReplace != null) replaceRole(role, loadReplace); }
 function stageCharacterOffset(a:Character, role:String):Array<Float> { log.push('offset:' + role); return [10, 20]; }
 function setAllHaxeVar(name:String, value:Dynamic):Void log.push('var:' + name + ':' + value.curCharacter);
 function callHxcCharacterAdded(a:Character, role:String):Void {
  log.push('hxcAdded:' + a.curCharacter + ':' + role); if (addedReplace != null) replaceRole(role, addedReplace); }
 function callAllHScript(name:String, args:Array<Dynamic>):Void log.push(name + ':' + args[0].curCharacter + ':' + args[1]);
 function rebindCodenameInputActor(a:Character, b:Character):Void log.push('rebindInput:' + b.curCharacter);
 function refreshCharacterHUD():Void log.push('hud');
 @@METHODS@@
 public function run(name:String, role:String):String {
  log = []; switchCharacter(name, role);
  var actor = role == 'other' ? null : characterForRole(role == 'player2' ? 'dad' : role == 'girlfriend' ? 'gf' : role == 'bf' ? 'boyfriend' : role);
  if (actor != null) log.push('final:' + actor.curCharacter + ':' + actor.characterType + ':' + actor.beingControlled + ':'
   + actor.alpha + ':' + actor.visible + ':' + actor.x + ',' + actor.y + ':' + actor.scrollFactor.x);
  log.push('members:' + [for (m in members) m.curCharacter].join(','));
  return log.join('|');
 }
}
class Main {
 static function main():Void {
  var out:Array<String> = [];
  for (role in ['boyfriend', 'bf', 'dad', 'player2', 'gf', 'girlfriend', 'other']) {
   var s = new State(); out.push(role + '=' + s.run('new-' + role, role));
   var slot = new State(); slot.sourceScoreOwner = true; slot.boyfriend.alpha = 0.5; slot.dad.visible = false; slot.gf.alpha = 0.25;
   slot.curStage.z = 3; out.push('slot-' + role + '=' + slot.run('new-' + role, role));
  }
  var likeDad = new State(); likeDad.dad.likeGf = true; out.push('bf-dad-likegf=' + likeDad.run('n', 'boyfriend'));
  var likeBf = new State(); likeBf.boyfriend.likeGf = true; out.push('dad-bf-likegf=' + likeBf.run('n', 'dad'));
  var root = new State(); root.psychStageCharacterRoot = 'stage'; out.push('dad-root-likegf=' + root.run('n-likegf', 'dad'));
  var opp = new State(); opp.opponentPlayer = true; out.push('bf-opponent=' + opp.run('n', 'boyfriend'));
  out.push('dad-opponent=' + opp.run('m', 'dad'));
  var demo = new State(); demo.demoMode = true; out.push('bf-demo=' + demo.run('n', 'boyfriend'));
  var duo = new State(); duo.duoMode = true; out.push('dad-duo=' + duo.run('n', 'dad'));
  var solo = new State(); solo.soloMode = true; out.push('dad-solo=' + solo.run('n', 'dad'));
  var shown = new State(); shown.curStage.presented.set('gf', true); out.push('gf-presented=' + shown.run('n', 'gf'));
  var bare = new State(); bare.curStage = null; out.push('bf-nostage=' + bare.run('n', 'boyfriend'));
  var loadSwap = new State(); loadSwap.loadReplace = 'script'; out.push('bf-load-replaces=' + loadSwap.run('n', 'boyfriend'));
  var addedSwap = new State(); addedSwap.addedReplace = 'late'; out.push('dad-added-replaces=' + addedSwap.run('n', 'dad'));
  Sys.println(out.join('\n'));
 }
}
'''


def run_fixture(test, methods: str) -> str:
	with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as folder:
		Path(folder, 'Main.hx').write_text(FIXTURE.replace('@@METHODS@@', methods), encoding='utf-8', newline='\n')
		result = subprocess.run([*HAXE_COMMAND, '-cp', folder, '--main', 'Main', '--interp'],
				cwd=ROOT, capture_output=True, text=True, timeout=120)
	test.assertEqual(result.returncode, 0, result.stdout + result.stderr)
	return result.stdout.strip().replace('\r\n', '\n')


EXPECTED = '''boyfriend=forget:bf|detach:boyfriend:new-boyfriend|clearTrail:bf|remove:bf:false|destroy:bf|take:boyfriend:new-boyfriend|hxc:new-boyfriend:boyfriend:boyfriend|enableTrail:new-boyfriend|present:boyfriend:new-boyfriend|offset:boyfriend|remove:dad:false|add:new-boyfriend|add:dad|rebindCodename:bf>new-boyfriend|var:boyfriend:new-boyfriend|hxcAdded:new-boyfriend:boyfriend|onCharacterAdded:new-boyfriend:boyfriend|borrowed:new-boyfriend|rebindInput:new-boyfriend|rebindZ:boyfriend:new-boyfriend|hud|smoke:new-boyfriend:boyfriend|final:new-boyfriend:boyfriend:true:1:true:10,20:1|members:gf,new-boyfriend,dad
slot-boyfriend=forget:bf|detach:boyfriend:new-boyfriend|clearTrail:bf|remove:bf:true|destroy:bf|take:boyfriend:new-boyfriend|hxc:new-boyfriend:boyfriend:boyfriend|enableTrail:new-boyfriend|present:boyfriend:new-boyfriend|offset:boyfriend|insert:2:new-boyfriend|rebindCodename:bf>new-boyfriend|var:boyfriend:new-boyfriend|hxcAdded:new-boyfriend:boyfriend|onCharacterAdded:new-boyfriend:boyfriend|borrowed:new-boyfriend|rebindInput:new-boyfriend|rebindZ:boyfriend:new-boyfriend|refresh|hud|smoke:new-boyfriend:boyfriend|final:new-boyfriend:boyfriend:true:0.5:true:10,20:1|members:gf,dad,new-boyfriend
bf=forget:bf|detach:boyfriend:new-bf|clearTrail:bf|remove:bf:false|destroy:bf|take:boyfriend:new-bf|hxc:new-bf:boyfriend:boyfriend|enableTrail:new-bf|present:boyfriend:new-bf|offset:boyfriend|remove:dad:false|add:new-bf|add:dad|rebindCodename:bf>new-bf|var:boyfriend:new-bf|hxcAdded:new-bf:boyfriend|onCharacterAdded:new-bf:boyfriend|borrowed:new-bf|rebindInput:new-bf|rebindZ:boyfriend:new-bf|hud|smoke:new-bf:boyfriend|final:new-bf:boyfriend:true:1:true:10,20:1|members:gf,new-bf,dad
slot-bf=forget:bf|detach:boyfriend:new-bf|clearTrail:bf|remove:bf:true|destroy:bf|take:boyfriend:new-bf|hxc:new-bf:boyfriend:boyfriend|enableTrail:new-bf|present:boyfriend:new-bf|offset:boyfriend|insert:2:new-bf|rebindCodename:bf>new-bf|var:boyfriend:new-bf|hxcAdded:new-bf:boyfriend|onCharacterAdded:new-bf:boyfriend|borrowed:new-bf|rebindInput:new-bf|rebindZ:boyfriend:new-bf|refresh|hud|smoke:new-bf:boyfriend|final:new-bf:boyfriend:true:0.5:true:10,20:1|members:gf,dad,new-bf
dad=forget:dad|detach:dad:new-dad|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:new-dad|hxc:new-dad:dad:dad|enableTrail:new-dad|present:dad:new-dad|offset:dad|remove:bf:false|add:new-dad|add:bf|rebindCodename:dad>new-dad|var:dad:new-dad|hxcAdded:new-dad:dad|onCharacterAdded:new-dad:dad|borrowed:new-dad|rebindInput:new-dad|rebindZ:dad:new-dad|hud|smoke:new-dad:dad|final:new-dad:dad:false:1:true:10,20:1|members:gf,new-dad,bf
slot-dad=forget:dad|detach:dad:new-dad|clearTrail:dad|remove:dad:true|destroy:dad|take:dad:new-dad|hxc:new-dad:dad:dad|enableTrail:new-dad|present:dad:new-dad|offset:dad|insert:1:new-dad|rebindCodename:dad>new-dad|var:dad:new-dad|hxcAdded:new-dad:dad|onCharacterAdded:new-dad:dad|borrowed:new-dad|rebindInput:new-dad|rebindZ:dad:new-dad|refresh|hud|smoke:new-dad:dad|final:new-dad:dad:false:1:false:10,20:1|members:gf,new-dad,bf
player2=forget:dad|detach:dad:new-player2|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:new-player2|hxc:new-player2:dad:dad|enableTrail:new-player2|present:dad:new-player2|offset:dad|remove:bf:false|add:new-player2|add:bf|rebindCodename:dad>new-player2|var:dad:new-player2|hxcAdded:new-player2:dad|onCharacterAdded:new-player2:dad|borrowed:new-player2|rebindInput:new-player2|rebindZ:dad:new-player2|hud|smoke:new-player2:dad|final:new-player2:dad:false:1:true:10,20:1|members:gf,new-player2,bf
slot-player2=forget:dad|detach:dad:new-player2|clearTrail:dad|remove:dad:true|destroy:dad|take:dad:new-player2|hxc:new-player2:dad:dad|enableTrail:new-player2|present:dad:new-player2|offset:dad|insert:1:new-player2|rebindCodename:dad>new-player2|var:dad:new-player2|hxcAdded:new-player2:dad|onCharacterAdded:new-player2:dad|borrowed:new-player2|rebindInput:new-player2|rebindZ:dad:new-player2|refresh|hud|smoke:new-player2:dad|final:new-player2:dad:false:1:false:10,20:1|members:gf,new-player2,bf
gf=forget:gf|detach:gf:new-gf|clearTrail:gf|remove:gf:false|destroy:gf|take:gf:new-gf|hxc:new-gf:gf:gf|enableTrail:new-gf|scroll:0.95,0.95|present:gf:new-gf|offset:gf|remove:bf:false|remove:dad:false|add:new-gf|add:dad|add:bf|rebindCodename:gf>new-gf|var:gf:new-gf|hxcAdded:new-gf:gf|onCharacterAdded:new-gf:gf|borrowed:new-gf|rebindInput:new-gf|rebindZ:gf:new-gf|hud|smoke:new-gf:gf|final:new-gf:gf:false:1:true:10,20:0.95|members:new-gf,dad,bf
slot-gf=forget:gf|detach:gf:new-gf|clearTrail:gf|remove:gf:true|destroy:gf|take:gf:new-gf|hxc:new-gf:gf:gf|enableTrail:new-gf|scroll:0.95,0.95|present:gf:new-gf|offset:gf|insert:0:new-gf|rebindCodename:gf>new-gf|var:gf:new-gf|hxcAdded:new-gf:gf|onCharacterAdded:new-gf:gf|borrowed:new-gf|rebindInput:new-gf|rebindZ:gf:new-gf|refresh|hud|smoke:new-gf:gf|final:new-gf:gf:false:0.25:true:10,20:0.95|members:new-gf,dad,bf
girlfriend=forget:gf|detach:gf:new-girlfriend|clearTrail:gf|remove:gf:false|destroy:gf|take:gf:new-girlfriend|hxc:new-girlfriend:gf:gf|enableTrail:new-girlfriend|scroll:0.95,0.95|present:gf:new-girlfriend|offset:gf|remove:bf:false|remove:dad:false|add:new-girlfriend|add:dad|add:bf|rebindCodename:gf>new-girlfriend|var:gf:new-girlfriend|hxcAdded:new-girlfriend:gf|onCharacterAdded:new-girlfriend:gf|borrowed:new-girlfriend|rebindInput:new-girlfriend|rebindZ:gf:new-girlfriend|hud|smoke:new-girlfriend:gf|final:new-girlfriend:gf:false:1:true:10,20:0.95|members:new-girlfriend,dad,bf
slot-girlfriend=forget:gf|detach:gf:new-girlfriend|clearTrail:gf|remove:gf:true|destroy:gf|take:gf:new-girlfriend|hxc:new-girlfriend:gf:gf|enableTrail:new-girlfriend|scroll:0.95,0.95|present:gf:new-girlfriend|offset:gf|insert:0:new-girlfriend|rebindCodename:gf>new-girlfriend|var:gf:new-girlfriend|hxcAdded:new-girlfriend:gf|onCharacterAdded:new-girlfriend:gf|borrowed:new-girlfriend|rebindInput:new-girlfriend|rebindZ:gf:new-girlfriend|refresh|hud|smoke:new-girlfriend:gf|final:new-girlfriend:gf:false:0.25:true:10,20:0.95|members:new-girlfriend,dad,bf
other=forget:null|detach:other:new-other|hud|smoke:new-other:other|members:gf,dad,bf
slot-other=forget:null|detach:other:new-other|hud|smoke:new-other:other|members:gf,dad,bf
bf-dad-likegf=forget:bf|detach:boyfriend:n|clearTrail:bf|remove:bf:false|destroy:bf|take:boyfriend:n|hxc:n:boyfriend:boyfriend|enableTrail:n|present:boyfriend:n|offset:boyfriend|add:n|rebindCodename:bf>n|var:boyfriend:n|hxcAdded:n:boyfriend|onCharacterAdded:n:boyfriend|borrowed:n|rebindInput:n|rebindZ:boyfriend:n|hud|smoke:n:boyfriend|final:n:boyfriend:true:1:true:10,20:1|members:gf,dad,n
dad-bf-likegf=forget:dad|detach:dad:n|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:n|hxc:n:dad:dad|enableTrail:n|present:dad:n|offset:dad|add:n|rebindCodename:dad>n|var:dad:n|hxcAdded:n:dad|onCharacterAdded:n:dad|borrowed:n|rebindInput:n|rebindZ:dad:n|hud|smoke:n:dad|final:n:dad:false:1:true:10,20:1|members:gf,bf,n
dad-root-likegf=forget:dad|detach:dad:n-likegf|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:n-likegf|hxc:n-likegf:dad:dad|enableTrail:n-likegf|setPosition:n-likegf:7,9|present:dad:n-likegf|offset:dad|remove:bf:false|add:n-likegf|add:bf|rebindCodename:dad>n-likegf|var:dad:n-likegf|hxcAdded:n-likegf:dad|onCharacterAdded:n-likegf:dad|borrowed:n-likegf|rebindInput:n-likegf|rebindZ:dad:n-likegf|hud|smoke:n-likegf:dad|final:n-likegf:dad:false:1:true:17,29:1|members:gf,n-likegf,bf
bf-opponent=forget:bf|detach:boyfriend:n|clearTrail:bf|remove:bf:false|destroy:bf|take:boyfriend:n|hxc:n:boyfriend:boyfriend|enableTrail:n|present:boyfriend:n|offset:boyfriend|remove:dad:false|add:n|add:dad|rebindCodename:bf>n|var:boyfriend:n|hxcAdded:n:boyfriend|onCharacterAdded:n:boyfriend|borrowed:n|rebindInput:n|rebindZ:boyfriend:n|hud|smoke:n:boyfriend|final:n:boyfriend:false:1:true:10,20:1|members:gf,n,dad
dad-opponent=forget:dad|detach:dad:m|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:m|hxc:m:dad:dad|enableTrail:m|present:dad:m|offset:dad|remove:n:false|add:m|add:n|rebindCodename:dad>m|var:dad:m|hxcAdded:m:dad|onCharacterAdded:m:dad|borrowed:m|rebindInput:m|rebindZ:dad:m|hud|smoke:m:dad|final:m:dad:true:1:true:10,20:1|members:gf,m,n
bf-demo=forget:bf|detach:boyfriend:n|clearTrail:bf|remove:bf:false|destroy:bf|take:boyfriend:n|hxc:n:boyfriend:boyfriend|enableTrail:n|present:boyfriend:n|offset:boyfriend|remove:dad:false|add:n|add:dad|rebindCodename:bf>n|var:boyfriend:n|hxcAdded:n:boyfriend|onCharacterAdded:n:boyfriend|borrowed:n|rebindInput:n|rebindZ:boyfriend:n|hud|smoke:n:boyfriend|final:n:boyfriend:false:1:true:10,20:1|members:gf,n,dad
dad-duo=forget:dad|detach:dad:n|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:n|hxc:n:dad:dad|enableTrail:n|present:dad:n|offset:dad|remove:bf:false|add:n|add:bf|rebindCodename:dad>n|var:dad:n|hxcAdded:n:dad|onCharacterAdded:n:dad|borrowed:n|rebindInput:n|rebindZ:dad:n|hud|smoke:n:dad|final:n:dad:true:1:true:10,20:1|members:gf,n,bf
dad-solo=forget:dad|detach:dad:n|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:n|hxc:n:dad:dad|enableTrail:n|present:dad:n|offset:dad|remove:bf:false|add:n|add:bf|rebindCodename:dad>n|var:dad:n|hxcAdded:n:dad|onCharacterAdded:n:dad|borrowed:n|rebindInput:n|rebindZ:dad:n|hud|smoke:n:dad|final:n:dad:true:1:true:10,20:1|members:gf,n,bf
gf-presented=forget:gf|detach:gf:n|clearTrail:gf|remove:gf:false|destroy:gf|take:gf:n|hxc:n:gf:gf|enableTrail:n|scroll:0.95,0.95|present:gf:n|remove:bf:false|remove:dad:false|add:n|add:dad|add:bf|rebindCodename:gf>n|var:gf:n|hxcAdded:n:gf|onCharacterAdded:n:gf|borrowed:n|rebindInput:n|rebindZ:gf:n|hud|smoke:n:gf|final:n:gf:false:1:true:0,0:0.95|members:n,dad,bf
bf-nostage=forget:bf|detach:boyfriend:n|clearTrail:bf|remove:bf:false|destroy:bf|take:boyfriend:n|hxc:n:boyfriend:boyfriend|enableTrail:n|offset:boyfriend|remove:dad:false|add:n|add:dad|var:boyfriend:n|hxcAdded:n:boyfriend|onCharacterAdded:n:boyfriend|hud|smoke:n:boyfriend|final:n:boyfriend:true:1:true:10,20:1|members:gf,n,dad
bf-load-replaces=forget:bf|detach:boyfriend:n|clearTrail:bf|remove:bf:false|destroy:bf|take:boyfriend:n|hxc:n:boyfriend:boyfriend|enableTrail:script|present:boyfriend:script|offset:boyfriend|remove:dad:false|add:script|add:dad|rebindCodename:bf>script|var:boyfriend:script|hxcAdded:script:boyfriend|onCharacterAdded:script:boyfriend|borrowed:script|rebindInput:script|rebindZ:boyfriend:script|hud|smoke:n:boyfriend|final:script::true:1:true:10,20:1|members:gf,script,dad
dad-added-replaces=forget:dad|detach:dad:n|clearTrail:dad|remove:dad:false|destroy:dad|take:dad:n|hxc:n:dad:dad|enableTrail:n|present:dad:n|offset:dad|remove:bf:false|add:n|add:bf|rebindCodename:dad>n|var:dad:n|hxcAdded:n:dad|onCharacterAdded:late:dad|borrowed:late|rebindInput:late|rebindZ:dad:late|hud|smoke:n:dad|final:late::false:1:true:0,0:1|members:gf,n,bf'''


class SwitchCharacterRolesTest(unittest.TestCase):
	def test_one_body_reproduces_every_role_trace(self):
		play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
		actual = run_fixture(self, swap_methods(play))
		for want, got in zip(EXPECTED.split('\n'), actual.split('\n')):
			self.assertEqual(want, got)
		self.assertEqual(len(EXPECTED.split('\n')), len(actual.split('\n')))

	def test_switch_character_has_one_role_body(self):
		play = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
		swap = method(play, '\tfunction switchCharacter(charTo:String, charState:String)')
		self.assertEqual(swap.count('takeSwapCharacter('), 1)
		self.assertEqual(swap.count('.destroy();'), 1)
		self.assertEqual(swap.count("callAllHScript('onCharacterAdded'"), 1)
		self.assertEqual(swap.count('applyVSliceCharacterPresentation('), 1)


if __name__ == '__main__':
	unittest.main()
