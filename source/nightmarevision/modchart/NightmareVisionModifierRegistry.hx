package nightmarevision.modchart;

/** Public metadata for one source ModManager modifier or submodifier. */
typedef NightmareVisionModifierDefinition = {
	var name:String;
	var parent:Null<String>;
	var order:Int;
	var noteModifier:Bool;
	var alwaysExecute:Bool;
	var registrationOrder:Int;
}

/**
	Pure value/registry layer for the supplied Nightmare Vision 0.6.4
	ModManager. Names, submod families, registration order, and initial values
	mirror ModManager.registerEssentialModifiers/registerDefaultModifiers.
	Scripted modifiers are intentionally not synthesized here.
*/
class NightmareVisionModifierRegistry {
	public static inline var FIRST:Int = -1000;
	public static inline var PRE_REVERSE:Int = -3;
	public static inline var REVERSE:Int = -2;
	public static inline var POST_REVERSE:Int = -1;
	public static inline var DEFAULT:Int = 0;
	public static inline var LAST:Int = 1000;

	public final keys:Int;
	public final players:Int;
	public var definitions(default, null):Array<NightmareVisionModifierDefinition> = [];
	public var families(default, null):Array<String> = [];

	var byName:Map<String, NightmareVisionModifierDefinition> = new Map();
	var children:Map<String, Array<String>> = new Map();
	var values:Map<String, Array<Float>> = new Map();
	var activeFamilyCache:Array<Array<String>> = [];
	var activeFamilyCacheRevision:Array<Int> = [];
	var activeFamilyRevision:Array<Int> = [];
	var nextOrder:Int = 0;
	var essentialsRegistered:Bool = false;
	var defaultsRegistered:Bool = false;

	public function new(keys:Int, players:Int = 2, registerBuiltins:Bool = true) {
		this.keys = keys < 1 ? 1 : keys;
		this.players = players < 1 ? 1 : players;
		for (_ in 0...this.players) {
			activeFamilyCache.push([]);
			activeFamilyCacheRevision.push(-1);
			activeFamilyRevision.push(0);
		}
		if (registerBuiltins) {
			registerEssentialModifiers();
			registerDefaultModifiers();
		}
	}

	/** Match PlayState's registration order: essential, then default modifiers. */
	public function registerEssentialModifiers():Void {
		if (essentialsRegistered) return;
		essentialsRegistered = true;
		addFamily('reverse', REVERSE, true, true, [
			'cross', 'split', 'alternate', 'reverseScroll', 'crossScroll', 'splitScroll', 'alternateScroll',
			'centered', 'unboundedReverse'
		].concat(indexed('reverse', '', keys)));
		addFamily('confusion', DEFAULT, true, true,
			['noteAngle', 'receptorAngle'].concat(indexed('note', 'Angle', keys))
				.concat(indexed('receptor', 'Angle', keys)).concat(indexed('confusion', '', keys)));
		addFamily('perspectiveDONTUSE', LAST + 100, true, true, []);
		addFamily('opponentSwap', DEFAULT, true, false, []);
	}

	public function registerDefaultModifiers():Void {
		if (defaultsRegistered) return;
		defaultsRegistered = true;
		addFamily('flip', DEFAULT, true, false, []);
		addFamily('invert', DEFAULT, true, false, []);
		addFamily('drunk', DEFAULT, true, false, [
			'drunkSpeed', 'drunkOffset', 'drunkPeriod', 'tipsy', 'tipsySpeed', 'tipsyOffset',
			'bumpy', 'bumpyOffset', 'bumpyPeriod', 'tipZ', 'tipZSpeed', 'tipZOffset',
			'drunkZ', 'drunkZSpeed', 'drunkZOffset', 'drunkZPeriod'
		]);
		addFamily('beat', DEFAULT, true, false, []);
		addFamily('stealth', DEFAULT, true, true, [
			'sustainSplashAlpha', 'noteSplashAlpha', 'noteAlpha', 'alpha', 'hidden', 'hiddenOffset',
			'sudden', 'suddenOffset', 'blink', 'randomVanish', 'dark', 'useStealthGlow',
			'stealthPastReceptors'
		].concat(indexed('sustainSplashAlpha', '', keys)).concat(indexed('noteSplashAlpha', '', keys))
			.concat(indexed('noteAlpha', '', keys)).concat(indexed('alpha', '', keys)).concat(indexed('dark', '', keys)));
		addFamily('receptorScroll', DEFAULT, true, false, []);

		var miniSubmods = [
			'squish', 'stretch', 'miniX', 'miniY', 'receptorScaleX', 'receptorScaleY',
			'noteScaleX', 'noteScaleY', 'noteSplashScaleX', 'noteSplashScaleY',
			'sustainSplashScaleX', 'sustainSplashScaleY'
		];
		for (i in 0...keys) {
			for (prefix in ['mini', 'squish', 'stretch', 'receptor', 'note', 'noteSplash', 'sustainSplash']) {
				if (prefix == 'squish' || prefix == 'stretch') miniSubmods.push(prefix + i);
				else if (prefix == 'mini') {
					miniSubmods.push(prefix + i + 'X');
					miniSubmods.push(prefix + i + 'Y');
				} else {
					miniSubmods.push(prefix + i + 'ScaleX');
					miniSubmods.push(prefix + i + 'ScaleY');
				}
			}
		}
		addFamily('mini', PRE_REVERSE, true, true, miniSubmods);

		var transformSubmods = ['transformY', 'transformZ', 'transformX-a', 'transformY-a', 'transformZ-a'];
		for (i in 0...keys) for (axis in ['X', 'Y', 'Z']) {
			transformSubmods.push('transform' + i + axis);
			transformSubmods.push('transform' + i + axis + '-a');
		}
		addFamily('transformX', LAST, true, false, transformSubmods);
		addFamily('infinite', DEFAULT, true, false, ['infiniteVisual', 'infiniteSpeed']);
		addFamily('boost', DEFAULT, true, false, ['brake', 'wave']);
		addFamily('xmod', DEFAULT, true, true, indexed('xmod', '', keys));
		addFamily('rotateX', LAST + 2, true, false, rotateSubmods('', keys));
		addFamily('centerrotateX', LAST + 2, true, false, rotateSubmods('center', keys));
		addFamily('localrotateX', POST_REVERSE, true, false, rotateSubmods('local', keys));
		addFamily('noteSpawnTime', DEFAULT, false, false, []);

		// Source ModManager.registerDefaultModifiers sets these after registration.
		setValue('noteSpawnTime', 2000);
		setValue('xmod', 1);
		for (i in 0...keys) setValue('xmod' + i, 1);
	}

	public function isRegistered(name:String):Bool return name != null && byName.exists(name);

	public function definition(name:String):Null<NightmareVisionModifierDefinition>
		return name == null ? null : byName.get(name);

	public function value(name:String, player:Int):Float {
		var row = requireValues(name);
		checkPlayer(player);
		return row[player];
	}

	public function percent(name:String, player:Int):Float return value(name, player) * 100;

	public function setValue(name:String, value:Float, player:Int = -1):Void {
		var row = requireValues(name);
		if (player == -1) {
			for (index in 0...players) setPlayerValue(row, index, value);
		} else {
			checkPlayer(player);
			setPlayerValue(row, player, value);
		}
	}

	public function setPercent(name:String, value:Float, player:Int = -1):Void
		setValue(name, value * 0.01, player);

	public function getSubmodValue(parent:String, name:String, player:Int):Float {
		var list = children.get(parent);
		if (list == null || list.indexOf(name) < 0) return 0;
		return value(name, player);
	}

	public function setSubmodValue(parent:String, name:String, value:Float, player:Int):Void {
		var list = children.get(parent);
		if (list == null || list.indexOf(name) < 0)
			throw 'Nightmare Vision modifier ' + parent + ' has no registered submodifier ' + name;
		setValue(name, value, player);
	}

	/** Active family roots in source order; child submods do not add a second pass.
	 * The returned per-player array is cached and must be treated as read-only. */
	public function activeFamilies(player:Int):Array<String> {
		checkPlayer(player);
		if (activeFamilyCacheRevision[player] == activeFamilyRevision[player])
			return activeFamilyCache[player];

		var active:Array<NightmareVisionModifierDefinition> = [];
		for (name in families) {
			var def = byName.get(name);
			// ModManager.updateObject/getPos look up only notemodRegister. A misc
			// value such as noteSpawnTime stays registered but is not a note pass.
			if (!def.noteModifier) continue;
			var enabled = def.alwaysExecute || value(name, player) != 0;
			var subs = children.get(name);
			if (!enabled && subs != null) for (sub in subs)
				if (value(sub, player) != 0) {
					enabled = true;
					break;
				}
			if (enabled) active.push(def);
		}
		active.sort(function(a, b) {
			if (a.order < b.order) return -1;
			if (a.order > b.order) return 1;
			return a.registrationOrder - b.registrationOrder;
		});
		var result = [for (def in active) def.name];
		activeFamilyCache[player] = result;
		activeFamilyCacheRevision[player] = activeFamilyRevision[player];
		return result;
	}

	function setPlayerValue(row:Array<Float>, player:Int, value:Float):Void {
		var previous = row[player];
		if (previous == value) return;
		row[player] = value;
		// The active root list depends only on whether each root/submodifier is
		// zero. Tweens that change one active value on every render frame do not
		// need to rebuild and sort the same family list for every live note.
		if ((previous == 0) != (value == 0))
			activeFamilyRevision[player]++;
	}

	function addFamily(name:String, order:Int, noteModifier:Bool, alwaysExecute:Bool, submods:Array<String>):Void {
		if (byName.exists(name)) return;
		families.push(name);
		addDefinition(name, null, order, noteModifier, alwaysExecute);
		children.set(name, []);
		for (submod in submods) {
			if (byName.exists(submod)) continue;
			children.get(name).push(submod);
			addDefinition(submod, name, LAST, noteModifier, false);
		}
		for (player in 0...players)
			activeFamilyRevision[player]++;
	}

	function addDefinition(name:String, parent:Null<String>, order:Int, noteModifier:Bool, alwaysExecute:Bool):Void {
		var def:NightmareVisionModifierDefinition = {
			name:name, parent:parent, order:order, noteModifier:noteModifier,
			alwaysExecute:alwaysExecute, registrationOrder:nextOrder++
		};
		byName.set(name, def);
		definitions.push(def);
		values.set(name, [for (_ in 0...players) 0.0]);
	}

	function requireValues(name:String):Array<Float> {
		var row = name == null ? null : values.get(name);
		if (row == null)
			throw 'Nightmare Vision scripted or unknown modifier is unsupported: ' + Std.string(name);
		return row;
	}

	function checkPlayer(player:Int):Void {
		if (player < 0 || player >= players)
			throw 'Nightmare Vision modifier player index out of range: ' + player;
	}

	static function indexed(prefix:String, suffix:String, count:Int):Array<String> {
		return [for (i in 0...count) prefix + i + suffix];
	}

	static function rotateSubmods(prefix:String, count:Int):Array<String> {
		var result = [prefix + 'rotateY', prefix + 'rotateZ'];
		for (i in 0...count) for (axis in ['X', 'Y', 'Z']) result.push(prefix + 'rotate' + i + axis);
		return result;
	}
}
