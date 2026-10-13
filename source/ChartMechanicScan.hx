package;

typedef NoteScriptHazard = {
	/** The note is authored to be skipped (it may be missed without penalty). */
	var avoid:Bool;
	/** Hitting it takes the player's input away until they recover. */
	var inputLock:Bool;
	var damage:Bool;
	var lethal:Bool;
}

typedef ChartScriptText = {
	var text:String;
	var lua:Bool;
}

typedef ChartAnalysisContext = {
	/** Lower-case canonical note type to what its script does. */
	@:optional var noteHazards:Map<String, NoteScriptHazard>;
	/** ChartMechanicScan.modchart result, zero when no playfield scripting was found. */
	@:optional var modchart:Float;
}

/** Read-only inspection of donor script text. Nothing is executed, and no mod,
 * song or note type is recognized by name: only the shape of the code counts.
 * Results are estimates and are reported as such. */
class ChartMechanicScan {
	public static inline var MAX_SCRIPT_BYTES:Int = 262144;
	public static inline var MAX_SONG_SCRIPTS:Int = 24;
	public static var SCRIPT_EXTENSIONS(default, never):Array<String> = ['hx', 'hxs', 'hxc', 'hscript', 'lua'];

	/** Lower-case source without comments. `--` only opens a comment in Lua. */
	public static function clean(text:String, lua:Bool):String {
		if (text == null) return '';
		var source = text.toLowerCase();
		var out = new StringBuf(); var i = 0; var length = source.length;
		while (i < length) {
			var c = source.charAt(i); var next = i + 1 < length ? source.charAt(i + 1) : '';
			if (!lua && c == '/' && next == '*') {
				var end = source.indexOf('*/', i + 2); i = end < 0 ? length : end + 2; out.add(' '); continue;
			}
			if (lua && c == '-' && next == '-') {
				if (source.substr(i + 2, 2) == '[[') { var end = source.indexOf(']]', i + 4); i = end < 0 ? length : end + 2; }
				else { var end = source.indexOf('\n', i); i = end < 0 ? length : end; }
				out.add(' '); continue;
			}
			if (!lua && c == '/' && next == '/') { var end = source.indexOf('\n', i); i = end < 0 ? length : end; continue; }
			out.add(c); i++;
		}
		return out.toString();
	}

	static function count(pattern:EReg, text:String):Int {
		var total = 0; var at = 0;
		while (at < text.length && pattern.matchSub(text, at)) {
			var found = pattern.matchedPos(); total++;
			at = found.pos + (found.len > 0 ? found.len : 1);
		}
		return total;
	}

	/** Classify one note type script. Null when it changes nothing a player must react to. */
	public static function noteHazard(text:String, lua:Bool):Null<NoteScriptHazard> {
		var source = clean(text, lua);
		if (source == '') return null;
		// A note that counts as a miss when hit is both skippable and harmful.
		var hitMiss = ~/\bhitcausesmiss\b['"]?\s*[,=:]\s*true/.match(source);
		var avoid = hitMiss || ~/\b(ignorenote|canmiss)\b['"]?\s*[,=:]\s*true/.match(source);
		var inputLock = ~/\b(incontrol|inputenabled|inputsenabled|caninput|keysenabled|controlsenabled|allowinput|inputallowed|canpress)\b['"]?\s*[,=:]\s*false/.match(source)
			|| ~/\b(stunned|inputlocked|inputlock|lockinput|blockinput|disableinput|freezeinput|(is)?frozen)\b['"]?\s*[,=:]\s*true/.match(source);
		var lethal = ~/\bhealth\b['"]?\s*[,=:]\s*(0(\.0*)?|-\s*\d[\d.]*)\s*[;,)\r\n]/.match(source) || ~/\b(instakill|dodeathcheck\s*\(\s*true)/.match(source);
		var damage = ~/\bhealth\b\s*-=/.match(source) || ~/\bhealth\b['"]?\s*,\s*[^,;)\r\n]*\bhealth\b['"]?\s*\)?\s*-/.match(source)
			|| ~/\baddhealth\s*\(\s*-/.match(source) || ~/\bhealth\b\s*=\s*[^;\r\n]*\bhealth\b\s*-/.match(source)
			|| ~/\bhithealth\b['"]?\s*[,=:]\s*-/.match(source) || hitMiss;
		if (!avoid && !inputLock && !lethal && !damage) return null;
		return {avoid:avoid, inputLock:inputLock, damage:damage, lethal:lethal};
	}

	// Modifier vocabulary by what it does to reading. Digits (per-column or
	// per-player variants) are removed before the lookup.
	static var families:Map<String, String> = [
		'reverse' => 'flow', 'unboundedreverse' => 'flow', 'flip' => 'flow', 'invert' => 'flow', 'opponentswap' => 'flow',
		'receptorscroll' => 'flow', 'centered' => 'flow', 'split' => 'flow', 'cross' => 'flow', 'alternate' => 'flow',
		'centerrotatex' => 'flow', 'centerrotatey' => 'flow', 'centerrotatez' => 'flow', 'localrotatex' => 'flow',
		'localrotatey' => 'flow', 'localrotatez' => 'flow', 'rotatex' => 'flow', 'rotatey' => 'flow', 'rotatez' => 'flow',
		'stealth' => 'sight', 'sudden' => 'sight', 'hidden' => 'sight', 'dark' => 'sight', 'blink' => 'sight', 'vanish' => 'sight',
		'alpha' => 'sight', 'suddenoffset' => 'sight', 'hiddenoffset' => 'sight',
		'drunk' => 'path', 'tipsy' => 'path', 'tandrunk' => 'path', 'tantipsy' => 'path', 'wave' => 'path', 'bumpy' => 'path',
		'zigzag' => 'path', 'sawtooth' => 'path', 'square' => 'path', 'tornado' => 'path', 'beat' => 'path', 'bounce' => 'path',
		'digital' => 'path', 'parabola' => 'path', 'confusion' => 'path', 'dizzy' => 'path', 'twirl' => 'path', 'roll' => 'path',
		'drift' => 'path', 'boomerang' => 'path', 'tipsyoffset' => 'path', 'drunkoffset' => 'path',
		'transformx' => 'layout', 'transformy' => 'layout', 'transformz' => 'layout', 'movex' => 'layout', 'movey' => 'layout',
		'movez' => 'layout', 'mini' => 'layout', 'tiny' => 'layout', 'squish' => 'layout', 'stretch' => 'layout', 'zoom' => 'layout',
		'boost' => 'speed', 'brake' => 'speed', 'xmod' => 'speed', 'cmod' => 'speed', 'speedmod' => 'speed', 'infinite' => 'speed',
		'notespawntime' => 'speed', 'scrollspeed' => 'speed',
	];
	static var weights:Map<String, Float> = ['flow' => 1.0, 'sight' => 0.8, 'speed' => 0.6, 'path' => 0.5, 'strums' => 0.6, 'layout' => 0.3, 'hud' => 0.4];

	/** Estimate how much scripted playfield movement a song has, from zero up.
	 * Each kind of effect counts once, growing slowly with how often it is used,
	 * so a long script cannot outweigh the variety of what it does. */
	public static function modchart(scripts:Array<ChartScriptText>, ?eventsText:String):Float {
		var uses:Map<String, Int> = [];
		function add(family:String, amount:Int):Void if (amount > 0) uses.set(family, (uses.exists(family) ? uses.get(family) : 0) + amount);
		// Patterns are built once per call, never shared: imports scan on a worker.
		var driver = ~/modmanager|modchart|modifier|setmod|startmod|queueease|queueset|setpercent/;
		var literal = ~/[(,]\s*['"]([a-z][a-z0-9_\-]*)['"]/; var variant = ~/[0-9_]|-a$/g;
		var tweens = ~/\bnotetween(x|y|angle|alpha|direction)\s*\(/;
		var groups = ~/setpropertyfromgroup\s*\(\s*['"](playerstrums|opponentstrums|strumlinenotes)['"]/;
		var members = ~/\b(playerstrums|opponentstrums|cpustrums|strumlinenotes)\b[^;\r\n]{0,80}\.(x|y|angle|alpha|direction|downscroll)\s*[+\-*]?=[^=]/;
		var hud = ~/\bcamhud\.(angle|x|y)\b/;
		if (scripts != null) for (script in scripts) {
			if (script == null || script.text == null) continue;
			var source = clean(script.text, script.lua);
			// Modifier names are ordinary words, so only a script that drives a
			// modifier system has its quoted arguments read as modifiers.
			if (driver.match(source)) {
				var at = 0;
				while (at < source.length && literal.matchSub(source, at)) {
					var found = literal.matchedPos(); at = found.pos + found.len;
					var name = variant.replace(literal.matched(1), '');
					if (families.exists(name)) add(families.get(name), 1);
				}
			}
			// Direct strum and HUD movement needs no modifier system.
			add('strums', count(tweens, source)); add('strums', count(groups, source)); add('strums', count(members, source));
			add('hud', count(hud, source));
		}
		if (eventsText != null) add('speed', count(~/"change scroll speed"/, eventsText.toLowerCase()));
		var total = 0.0;
		for (family in uses.keys())
			total += weights.get(family) * (1 + Math.min(1, Math.log(uses.get(family)) / Math.log(2) / 4));
		return Math.min(4, total * 0.6);
	}

	public static function modchartLabel(value:Float):String return value < 1 ? 'light' : value < 2.5 ? 'moderate' : 'heavy';

	/** Whether a file name is a script this scan reads. */
	public static function isScript(name:String):Bool {
		if (name == null) return false;
		var dot = name.lastIndexOf('.');
		return dot > 0 && SCRIPT_EXTENSIONS.indexOf(name.substr(dot + 1).toLowerCase()) >= 0;
	}
	public static function isLua(name:String):Bool return name != null && StringTools.endsWith(name.toLowerCase(), '.lua');

	/** Folders, relative to an imported owner, that hold one script per note type. */
	public static function noteScriptFolders():Array<String>
		return ['data/notetypes', 'custom_notetypes', 'notetypes', 'scripts/notetypes', 'data/custom_notetypes'];
	/** Folders, relative to an imported owner, whose scripts run with one song. */
	public static function songScriptFolders(folder:String):Array<String>
		return ['songs/' + folder, 'songs/' + folder + '/scripts', 'data/' + folder, 'data/' + folder + '/scripts', 'data/songs/' + folder];

	/** Receipt-derived owner roots are confined to one imported package folder. */
	public static function safeOwner(value:Dynamic):Null<String> {
		if (!Std.isOfType(value, String)) return null;
		var clean = StringTools.replace(StringTools.trim(cast value), '\\', '/');
		var parts = clean.split('/');
		if (parts.length != 3 || parts[0] != 'assets' || parts[1] != 'imported_mods' || !safeName(parts[2])) return null;
		return clean;
	}
	public static function safeName(value:Dynamic):Bool {
		if (!Std.isOfType(value, String)) return false;
		var name:String = cast value;
		return name != '' && name != '.' && name.indexOf('..') < 0 && name.indexOf('/') < 0
			&& name.indexOf('\\') < 0 && name.indexOf(':') < 0 && name.indexOf(String.fromCharCode(0)) < 0;
	}
}
