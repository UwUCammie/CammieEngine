package;

using StringTools;

/** Owner-scoped GameOverSubstate settings shared by Psych and Nightmare Vision. */
class SourceGameOverSettings {
	public static inline var PSYCH:Int = 1;
	public static inline var NIGHTMARE:Int = 2;

	public final mode:Int;
	final chart:Dynamic;

	public var characterName:Null<String>;
	public var deathSoundName:Null<String>;
	public var loopSoundName:Null<String>;
	public var endSoundName:Null<String>;
	public var deathDelay:Float = 0;

	public function new(mode:Int, chart:Dynamic) {
		if (mode != PSYCH && mode != NIGHTMARE)
			throw '[source-gameover] unsupported source mode ' + mode;
		this.mode = mode;
		this.chart = chart;
		resetVariables();
	}

	/** Restore donor defaults and, for Psych, apply nonblank chart overrides. */
	public function resetVariables():Void {
		characterName = 'bf-dead';
		deathSoundName = 'fnf_loss_sfx';
		loopSoundName = 'gameOver';
		endSoundName = 'gameOverEnd';
		deathDelay = 0;

		if (mode != PSYCH) return;
		characterName = psychChartValue('gameOverChar', characterName);
		deathSoundName = psychChartValue('gameOverSound', deathSoundName);
		loopSoundName = psychChartValue('gameOverLoop', loopSoundName);
		endSoundName = psychChartValue('gameOverEnd', endSoundName);
	}

	/** Apply Nightmare Vision character metadata using donor null-coalescing semantics. */
	public function applyCharacter(character:Dynamic):Void {
		if (mode != NIGHTMARE || character == null) return;
		var name = nullableStringField(character, 'gameoverCharacter');
		var death = nullableStringField(character, 'gameoverInitialDeathSound');
		var loop = nullableStringField(character, 'gameoverLoopDeathSound');
		var ending = nullableStringField(character, 'gameoverConfirmDeathSound');
		if (name != null) characterName = name;
		if (death != null) deathSoundName = death;
		if (loop != null) loopSoundName = loop;
		if (ending != null) endSoundName = ending;
	}

	/** Read a donor-named static setting for an owner-bound class facade. */
	public function read(key:String):Dynamic {
		return switch (key) {
			case 'characterName': characterName;
			case 'deathSoundName': deathSoundName;
			case 'loopSoundName': loopSoundName;
			case 'endSoundName': endSoundName;
			case 'deathDelay' if (mode == PSYCH): deathDelay;
			case 'deathDelay': throw '[source-gameover] deathDelay is Psych-only';
			default: throw '[source-gameover] unknown setting ' + key;
		};
	}

	/** Write a donor-named static setting for an owner-bound class facade. */
	public function write(key:String, value:Dynamic):Dynamic {
		switch (key) {
			case 'characterName': characterName = stringValue(key, value);
			case 'deathSoundName': deathSoundName = stringValue(key, value);
			case 'loopSoundName': loopSoundName = stringValue(key, value);
			case 'endSoundName': endSoundName = stringValue(key, value);
			case 'deathDelay':
				if (mode != PSYCH) throw '[source-gameover] deathDelay is Psych-only';
				deathDelay = floatValue(key, value);
			default: throw '[source-gameover] unknown setting ' + key;
		}
		return read(key);
	}

	function psychChartValue(field:String, fallback:String):String {
		var value:Dynamic = chart == null ? null : Reflect.field(chart, field);
		if (value == null || !Std.isOfType(value, String)) return fallback;
		var candidate:String = cast value;
		// Psych checks trim() only for emptiness and retains the authored string.
		return candidate.trim().length == 0 ? fallback : candidate;
	}

	static function nullableStringField(owner:Dynamic, field:String):Null<String> {
		var value:Dynamic = Reflect.getProperty(owner, field);
		return value == null || !Std.isOfType(value, String) ? null : cast value;
	}

	static function stringValue(key:String, value:Dynamic):Null<String> {
		if (value == null) return null;
		if (!Std.isOfType(value, String))
			throw '[source-gameover] ' + key + ' must be a string or null';
		return cast value;
	}

	static function floatValue(key:String, value:Dynamic):Float {
		if (value == null || (!Std.isOfType(value, Int) && !Std.isOfType(value, Float)))
			throw '[source-gameover] ' + key + ' must be a number';
		// Psych stores a Float and its death path only tests `deathDelay > 0`.
		// Preserve signed and non-finite Float values; the host applies that same
		// strict-positive gate before starting its timer.
		return cast value;
	}
}
