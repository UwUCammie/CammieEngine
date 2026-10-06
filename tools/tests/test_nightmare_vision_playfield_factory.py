"""Exercise the owner-local Nightmare Vision PlayField constructor through real Iris."""
import subprocess
import tempfile
import unittest

from haxe_test_support import HAXE_COMMAND, FixturePath as Path
from tools.haxe_flixel_math_stubs import write_flixel_point_stub


ROOT = Path(__file__).resolve().parents[2]
MAIN = r'''
import crowplexus.hscript.Parser;

class TestPlayState {
	public var name:String;
	public var created:Array<Dynamic> = [];
	public var playFields:Array<Dynamic> = [];

	public function new(name:String) this.name = name;

	public function createNightmareVisionSourceField(args:Array<Dynamic>):Dynamic {
		var field:Dynamic = {owner: name, args: args.copy(), attached: false};
		created.push(field);
		return field;
	}
}

class Main {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;

	static function main():Void {
		check(Type.resolveClass('PlayField') == PlayField,
			'fixture must expose a colliding native PlayField class');
		var parser = new Parser();
		var interpA = new NightmareVisionScriptInterp();
		var hostA = new TestPlayState('A');
		var currentA:TestPlayState = hostA;
		NightmareVisionPlayFieldBindings.install(interpA, 'A',
			function(owner:String):Dynamic return owner == 'A' ? currentA : null);

		var viewA = interpA.variables.get('PlayField');
		check(viewA != null
			&& viewA == interpA.importBindings.get('funkin.objects.note.PlayField'),
			'bare and source import must share one owner-local class identity');
		interpA.execute(parser.parseString(
			'bare = new PlayField(10, 20, 7); qualified = new funkin.objects.note.PlayField(30, 40);'));
		var bare:Dynamic = interpA.variables.get('bare');
		var qualified:Dynamic = interpA.variables.get('qualified');
		check(bare.owner == 'A' && qualified.owner == 'A',
			'both constructor spellings must resolve through the owning host');
		check(bare.args.length == 3 && bare.args[0] == 10 && bare.args[1] == 20 && bare.args[2] == 7,
			'the binding must pass explicit arguments without rewriting them');
		check(qualified.args.length == 2 && qualified.args[0] == 30 && qualified.args[1] == 40,
			'the binding must leave omitted source defaults to the host constructor');
		check(hostA.created.length == 2 && hostA.playFields.length == 0
			&& bare.attached == false && qualified.attached == false,
			'constructor must make fields available without implicitly adding them to playFields');

		var localType:Dynamic = {};
		interpA.bindConstructorFactory(localType,
			function(args:Array<Dynamic>):Dynamic return {owner: 'local', args: args.copy()}, null);
		interpA.variables.set('localType', localType);
		interpA.execute(parser.parseString(
			'{ var PlayField = localType; localField = new PlayField("local"); } '
			+ 'afterLocal = new PlayField(50, 60);'));
		check(interpA.variables.get('localField').owner == 'local',
			'a script-local class binding must shadow the seeded constructor');
		check(interpA.variables.get('afterLocal').owner == 'A',
			'local constructor shadow must end with its lexical block');

		// The binding resolves the current owner on each construction instead of
		// retaining the PlayState that happened to be active at installation.
		var replacementA = new TestPlayState('A-replacement');
		currentA = replacementA;
		interpA.execute(parser.parseString('replacement = new PlayField(70, 80);'));
		check(replacementA.created.length == 1 && replacementA.created[0].owner == 'A-replacement',
			'construction should re-resolve the current owner host');

		var interpB = new NightmareVisionScriptInterp();
		var hostB = new TestPlayState('B');
		NightmareVisionPlayFieldBindings.install(interpB, 'B',
			function(owner:String):Dynamic return owner == 'B' ? hostB : null);
		check(interpB.variables.get('PlayField') != viewA,
			'different interpreters must have distinct class identities');
		interpB.execute(parser.parseString(
			'otherBare = new PlayField(1, 2); otherQualified = new funkin.objects.note.PlayField(3, 4);'));
		check(interpB.variables.get('otherBare').owner == 'B'
			&& interpB.variables.get('otherQualified').owner == 'B'
			&& hostB.created.length == 2,
			'interpreter B must use only its own PlayState host');

		var missing = new NightmareVisionScriptInterp();
		NightmareVisionPlayFieldBindings.install(missing, 'ended-scene',
			function(_owner:String):Dynamic return null);
		var errorMessage = '';
		try {
			missing.execute(parser.parseString('field = new PlayField(0, 0);'));
		} catch (error:Dynamic) {
			errorMessage = Std.string(error);
		}
		check(errorMessage.indexOf('No active PlayState for owner: ended-scene') >= 0,
			'stale owner closure should fail with a scene-specific diagnostic');

		// Removing the owner-local seed leaves ordinary compiled Haxe lookup intact.
		interpA.variables.remove('PlayField');
		interpA.importBindings.remove('funkin.objects.note.PlayField');
		interpA.unbindConstructorFactory(viewA);
		interpA.execute(parser.parseString('nativeField = new PlayField("native");'));
		check(Std.isOfType(interpA.variables.get('nativeField'), PlayField),
			'unbound lookup must still construct the colliding native Haxe class');

		interpA.release();
		interpB.release();
		missing.release();
		trace('NV_PLAYFIELD_FACTORY_OK');
	}
}
'''

NATIVE_PLAYFIELD = r'''
class PlayField {
	public var name:String;
	public function new(name:String) this.name = name;
}
'''


class NightmareVisionPlayFieldFactoryTest(unittest.TestCase):
	def test_real_iris_uses_owner_local_unattached_playfield_factory(self):
		if not (ROOT / '.tools/haxe/haxe').is_file():
			self.skipTest('portable Haxe interpreter is unavailable')
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
			work = Path(directory)
			write_flixel_point_stub(work)
			(work / 'Main.hx').write_text(MAIN, newline='\n')
			(work / 'PlayField.hx').write_text(NATIVE_PLAYFIELD, newline='\n')
			result = subprocess.run(
				[
					*HAXE_COMMAND,
					'-cp', str(ROOT / 'source'),
					'-cp', str(ROOT / '.haxelib/hscript-iris/1,1,3'),
					'-cp', str(work),
					'--run', 'Main',
				],
				cwd=ROOT,
				capture_output=True,
				text=True,
				timeout=60,
			)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
		self.assertIn('NV_PLAYFIELD_FACTORY_OK', result.stdout)



def extract_method(source: str, marker: str) -> str:
	start = source.index(marker)
	brace = source.index("{", start)
	depth = 0
	for index in range(brace, len(source)):
		if source[index] == "{":
			depth += 1
		elif source[index] == "}":
			depth -= 1
			if depth == 0:
				return source[start:index + 1]
	raise AssertionError(f"unterminated method: {marker}")


HOST_CONSTRUCTOR_FIXTURE = r'''
class Note {
	public static inline var NOTE_AMOUNT:Int = 4;
}

class NightmareVisionNoteSkin {
	public static var created:Int = 0;
	public var paths:Dynamic;
	public var name:String;
	public var keys:Int;
	public var ID:Int;

	public function new(paths:Dynamic, name:String, keys:Int=4, id:Int=0) {
		this.paths = paths;
		this.name = name;
		this.keys = keys;
		this.ID = id;
		created++;
	}
}

class Strumline {
	public static var nextID:Int = 100;
	public var ID:Int;
	public var x:Float;
	public var y:Float;
	public var uiType:String;
	public var members:Array<Dynamic> = [];
	public var generationCalls:Int = 0;
	public var clearCalls:Int = 0;

	public function new(x:Float, y:Float, uiType:String) {
		ID = nextID++;
		this.x = x;
		this.y = y;
		this.uiType = uiType;
	}

	public function generateReceptors(count:Int):Void {
		generationCalls++;
		for (_ in 0...count) members.push({});
	}

	public function clearReceptors():Void {
		clearCalls++;
		members.resize(0);
	}
}

class NightmareVisionPlayFieldView {
	public var ID:Int;
	public var strumline:Strumline;
	public var owner:Dynamic;
	public var baseX:Float = 0;
	public var baseY:Float = 0;
	public var keyCount(default, set):Int = 4;
	public var isPlayer:Bool = false;
	public var playerControls:Bool = false;
	public var autoPlayed:Bool = false;
	public var player:Int = 0;
	public var playAnims:Bool = true;
	public var showRatings:Bool = false;
	public var noteSplashes:Bool = false;
	public var quants:Bool = false;
	public var holdDropLeniency:Float = 1 / 3;
	public var _skin:NightmareVisionNoteSkin;
	public var hooks:Dynamic;

	public var members(get, never):Array<Dynamic>;

	public function new(id:Int, defaultAuto:Void->Bool) {
		ID = id;
		autoPlayed = defaultAuto();
		player = id;
		isPlayer = id != 1;
		playerControls = id != 1;
	}

	function get_members():Array<Dynamic> return strumline == null ? [] : strumline.members;

	function set_keyCount(value:Int):Int {
		keyCount = value;
		if (members.length > 0) generateReceptors();
		return value;
	}

	public function bindNativeLifecycle(hooks:Dynamic):Void this.hooks = hooks;

	public function generateReceptors():Void {
		var callback = Reflect.field(hooks, 'generateReceptors');
		if (callback == null) throw 'missing generate hook';
		Reflect.callMethod(hooks, callback, [this]);
	}
}

class FakeCollection {
	public var members:Array<Dynamic> = [];
	public function new() {}
}

class FakePlayState {
	public var nightmareVisionPaths:Dynamic;
	public var nightmareVisionPrefs:Dynamic;
	public var SONG:Dynamic;
	public var nightmareVisionOwnedStrumlines:Array<Strumline> = [];
	public var nightmareVisionOwnedFields:Array<NightmareVisionPlayFieldView> = [];
	public var playFields:FakeCollection = new FakeCollection();
	public var generationCalls:Int = 0;
	public var clearCalls:Int = 0;

	public function new(paths:Dynamic, quants:Bool, song:Dynamic) {
		nightmareVisionPaths = paths;
		nightmareVisionPrefs = {view: {quants: quants}};
		SONG = song;
	}

 function nightmareVisionSourceSkinRegistry():Dynamic return {noteskins:[]};
 function initializeNightmareVisionFieldSplashes(field:NightmareVisionPlayFieldView):Void {}
	function bindNightmareVisionPlayFieldLifecycle(field:NightmareVisionPlayFieldView):Void {
		nightmareVisionOwnedFields.push(field);
		var host = this;
		field.bindNativeLifecycle({
			generateReceptors: function(changed:NightmareVisionPlayFieldView):Void
				host.nightmareVisionGenerateFieldReceptors(changed)
		});
	}

	function nightmareVisionGenerateFieldReceptors(field:NightmareVisionPlayFieldView):Void {
		generationCalls++;
		field.strumline.generateReceptors(field.keyCount);
	}

	function nightmareVisionClearFieldReceptors(field:NightmareVisionPlayFieldView):Void {
		clearCalls++;
		field.strumline.clearReceptors();
	}

	__SOURCE_CONSTRUCTOR__
}

class Main {
	static function check(ok:Bool, message:String):Void if (!ok) throw message;

	static function expectError(action:Void->Void, expected:String, message:String):Void {
		var actual = '';
		try action() catch (error:Dynamic) actual = Std.string(error);
		check(actual.indexOf(expected) >= 0, message + ': ' + actual);
	}

	static function main():Void {
		var paths:Dynamic = {root: 'owner-assets'};
		var defaults = new FakePlayState(paths, false, null);
		var defaultField = defaults.createNightmareVisionSourceField([12.5, 34.25]);
		check(defaultField.baseX == 12.5 && defaultField.baseY == 34.25,
			'x/y constructor arguments must seed the source base position');
		check(defaultField.keyCount == 4 && defaultField.owner == null
			&& !defaultField.isPlayer && !defaultField.autoPlayed
			&& !defaultField.playerControls && defaultField.player == 0,
			'source constructor defaults must be preserved');
		check(defaultField._skin != null && defaultField._skin.name == 'default'
			&& defaultField._skin.paths == paths && defaultField._skin.keys == 4 && defaultField._skin.ID == 0,
			'default skin must be created with the active owner paths');
		check(defaultField.strumline.x == 12.5 && defaultField.strumline.y == 34.25
			&& defaultField.strumline.uiType == 'normal',
			'constructor must create an owner-positioned line with the normal fallback UI');
		check(defaultField.ID == defaultField.strumline.ID && defaultField.ID != defaultField.player,
			'field ID must follow the native line ID rather than the source player index');
		check(defaults.clearCalls == 1 && defaults.generationCalls == 0
			&& defaultField.members.length == 0 && defaultField.strumline.generationCalls == 0,
			'new fields must retain an empty receptor bank until explicit generation');
		check(defaults.nightmareVisionOwnedFields.length == 1
			&& defaults.nightmareVisionOwnedFields[0] == defaultField
			&& defaults.nightmareVisionOwnedStrumlines.length == 1
			&& defaults.nightmareVisionOwnedStrumlines[0] == defaultField.strumline
			&& defaults.playFields.members.length == 0,
			'host must retain the unattached field and line without publishing the field');

		var owner:Dynamic = {name: 'bf'};
		var derived = defaults.createNightmareVisionSourceField([1, 2, 4, owner, true]);
		check(derived.owner == owner && derived.isPlayer && derived.playerControls
			&& !derived.autoPlayed && derived.player == 0,
			'playerControls should default to isPlayer while other omitted flags keep donor defaults');

		var customSong:Dynamic = {uiType: 'pixel'};
		var overrides = new FakePlayState(paths, false, customSong);
		var injectedSkin = new NightmareVisionNoteSkin({root: 'injected'}, 'injected-skin');
		var skinsBeforeInjection = NightmareVisionNoteSkin.created;
		var explicitOwner:Dynamic = {name: 'custom-owner'};
		var overridden = overrides.createNightmareVisionSourceField([
			50.5, 60.25, 3, explicitOwner, true, true, false, 2, 'ignored-skin-name', injectedSkin
		]);
		check(overridden.baseX == 50.5 && overridden.baseY == 60.25 && overridden.keyCount == 3
			&& overridden.owner == explicitOwner && overridden.isPlayer && overridden.autoPlayed
			&& !overridden.playerControls && overridden.player == 2,
			'provided source constructor arguments must override their defaults');
		check(overridden._skin == injectedSkin && NightmareVisionNoteSkin.created == skinsBeforeInjection
			&& overridden.strumline.uiType == 'pixel',
			'injected skin identity must win without loading a replacement skin');
		check(overridden.ID == overridden.strumline.ID && overridden.ID != overridden.player,
			'field identity must remain the receptor-line ID when player is overridden');
		check(overridden.members.length == 0 && overridden.strumline.generationCalls == 0
			&& overrides.playFields.members.length == 0,
			'construction must leave the custom field ungenerated and unattached');
		overridden.generateReceptors();
		check(overrides.generationCalls == 1 && overridden.strumline.generationCalls == 1
			&& overridden.members.length == 3,
			'explicit field generation must populate exactly the requested receptor count');
		check(overrides.nightmareVisionOwnedFields.length == 1
			&& overrides.nightmareVisionOwnedFields[0] == overridden
			&& overrides.nightmareVisionOwnedStrumlines.length == 1
			&& overrides.nightmareVisionOwnedStrumlines[0] == overridden.strumline
			&& overrides.playFields.members.length == 0,
			'owner must retain generated-but-never-added field and line objects');

		var badSkinHost = new FakePlayState(paths, false, null);
		expectError(function() badSkinHost.createNightmareVisionSourceField([
			0, 0, 4, null, false, false, null, 0, 'default', {name: 'not-a-skin'}
		]), 'Injected skin requires a source NoteSkin adapter',
			'invalid injected skin must produce the source adapter diagnostic');
		check(badSkinHost.nightmareVisionOwnedFields.length == 0
			&& badSkinHost.nightmareVisionOwnedStrumlines.length == 0,
			'bad skin input must fail before allocating host-owned objects');

		var quantHost = new FakePlayState(paths, true, null);
		var quantField = quantHost.createNightmareVisionSourceField([0, 0]);
		check(quantField.quants,
			'field constructor must seed source quant mode from the owner preferences');
		check(quantHost.nightmareVisionOwnedFields.length == 1
			&& quantHost.nightmareVisionOwnedFields[0] == quantField
			&& quantHost.nightmareVisionOwnedStrumlines.length == 1,
			'enabled quant mode must retain its normal owner-owned field resources');

		var tooWideHost = new FakePlayState(paths, false, null);
		expectError(function() tooWideHost.createNightmareVisionSourceField([0, 0, 5]),
			'exceeds host layout limit 4',
			'field constructor must enforce the four-lane host limit');
		check(tooWideHost.nightmareVisionOwnedFields.length == 0
			&& tooWideHost.nightmareVisionOwnedStrumlines.length == 0,
			'over-limit layouts must fail before creating field resources');

		trace('NV_PLAYFIELD_HOST_CONSTRUCTOR_OK');
	}
}
'''


class NightmareVisionPlayFieldHostConstructorTest(unittest.TestCase):
	def test_extracted_host_constructor_uses_real_argument_parser_and_keeps_fields_unattached(self):
		if not (ROOT / '.tools/haxe/haxe').is_file():
			self.skipTest('portable Haxe interpreter is unavailable')
		play_state = (ROOT / 'source/PlayState.hx').read_text(encoding='utf-8')
		constructor = extract_method(play_state,
			'@:keep public function createNightmareVisionSourceField(')
		fixture = HOST_CONSTRUCTOR_FIXTURE.replace('__SOURCE_CONSTRUCTOR__', constructor)
		with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as directory:
			work = Path(directory)
			(work / 'Main.hx').write_text(fixture, newline='\n')
			result = subprocess.run(
				[
					*HAXE_COMMAND,
					'-cp', str(ROOT / 'source'),
					'-cp', str(work),
					'--run', 'Main',
				],
				cwd=ROOT,
				capture_output=True,
				text=True,
				timeout=60,
			)
		self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
		self.assertIn('NV_PLAYFIELD_HOST_CONSTRUCTOR_OK', result.stdout)




if __name__ == '__main__':
	unittest.main()
