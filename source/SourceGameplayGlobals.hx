package;

/** Plain values a gameplay host hands over. Keeping this a struct means the
 * globals can be built (and tested) without the live state. */
typedef SourceGameplayState = {
	var songName:String;
	var songPath:String;
	var songBpm:Float;
	var songSpeed:Float;
	var songLength:Float;
	var stage:String;
	var hasVocals:Bool;
	var storyMode:Bool;
	var difficulty:Int;
	var difficultyName:String;
	var week:String;
	var seenCutscene:Bool;
	var startedCountdown:Bool;
	var botPlay:Bool;
	var practice:Bool;
	var healthGainMult:Float;
	var healthLossMult:Float;
	var instakillOnMiss:Bool;
	var deaths:Int;
	/** The chart section the globals describe, or null before the chart exists. */
	var section:Dynamic;
	var curDecBeat:Float;
	var curDecStep:Float;
	var boyfriendX:Float;
	var boyfriendY:Float;
	var opponentX:Float;
	var opponentY:Float;
	var girlfriendX:Float;
	var girlfriendY:Float;
	/** Folder name of the import that owns the script, '' for base game content. */
	var modFolder:String;
}

/** The gameplay globals Psych style script engines hand to every script.
 * Psych Lua and Nightmare Vision HScript use the same names for the same
 * values, so both seeds read them from here instead of keeping two lists. */
@:keep
class SourceGameplayGlobals {
	/** Set on an interpreter that received the globals, so refreshes skip the rest. */
	public static inline var MARKER:String = '__sourceGameplayGlobals';

	public static function snapshot(state:SourceGameplayState):Map<String, Dynamic> {
		var values:Map<String, Dynamic> = [
			'bpm' => state.songBpm, 'scrollSpeed' => state.songSpeed, 'songLength' => state.songLength,
			'songName' => text(state.songName), 'songPath' => text(state.songPath),
			'loadedSongName' => text(state.songName), 'loadedSongPath' => text(state.songPath),
			'curStage' => text(state.stage), 'hasVocals' => state.hasVocals == true,
			'isStoryMode' => state.storyMode == true, 'seenCutscene' => state.seenCutscene == true,
			'startedCountdown' => state.startedCountdown == true,
			'difficulty' => state.difficulty, 'difficultyName' => text(state.difficultyName),
			'difficultyNameTranslation' => text(state.difficultyName),
			'difficultyPath' => difficultyPath(state.difficultyName),
			'week' => text(state.week), 'weekRaw' => weekIndex(state.week),
			'deaths' => state.deaths, 'botPlay' => state.botPlay == true, 'practice' => state.practice == true,
			'healthGainMult' => state.healthGainMult, 'healthLossMult' => state.healthLossMult,
			'instakillOnMiss' => state.instakillOnMiss == true,
			'curDecBeat' => state.curDecBeat, 'curDecStep' => state.curDecStep,
			'defaultBoyfriendX' => state.boyfriendX, 'defaultBoyfriendY' => state.boyfriendY,
			'defaultOpponentX' => state.opponentX, 'defaultOpponentY' => state.opponentY,
			'defaultGirlfriendX' => state.girlfriendX, 'defaultGirlfriendY' => state.girlfriendY,
			'modFolder' => text(state.modFolder), 'currentModDirectory' => text(state.modFolder),
			// Scripts assign these two to tune their own logging, so they only need to exist.
			'luaDebugMode' => false, 'luaDeprecatedWarnings' => true,
			// There is no per-player skin suffix here, so both resolve to the plain skin.
			'noteSkinPostfix' => '', 'splashSkinPostfix' => ''
		];
		for (name => value in section(state.section)) values.set(name, value);
		return values;
	}

	/** The entries that follow the chart section, for the per-section refresh. */
	public static function section(section:Dynamic):Map<String, Dynamic> {
		return [
			'mustHitSection' => flag(section, 'mustHitSection'),
			'altAnim' => flag(section, 'altAnim'),
			'gfSection' => flag(section, 'gfSection')
		];
	}

	/** Seed only the names the interpreter does not have yet, so a host that
	 * already exposes a live value under the same name keeps its own. */
	public static function seedMissing(variables:Map<String, Dynamic>, values:Map<String, Dynamic>):Void {
		if (variables == null || values == null) return;
		for (name => value in values) if (!variables.exists(name)) variables.set(name, value);
		variables.set(MARKER, true);
	}

	/** Update one global on an interpreter that was seeded from here. */
	public static function refresh(variables:Map<String, Dynamic>, name:String, value:Dynamic):Void {
		if (variables != null && variables.get(MARKER) == true) variables.set(name, value);
	}

	/** File suffix of a difficulty: '' for the default one, '-hard' style otherwise. */
	public static function difficultyPath(name:String):String {
		var lower = StringTools.trim(text(name)).toLowerCase();
		if (lower == '' || lower == 'normal') return '';
		return '-' + StringTools.replace(lower, ' ', '-');
	}

	/** Weeks are named here, but scripts expect an index. A numeric name keeps
	 * its number and anything else reads as the first week. */
	public static function weekIndex(week:String):Int {
		var parsed = week == null ? null : Std.parseInt(StringTools.trim(week));
		return parsed == null ? 0 : parsed;
	}

	/** Last folder of an import root, which is what scripts know as the mod folder. */
	public static function folderName(root:String):String {
		if (root == null) return '';
		var clean = StringTools.replace(root, '\\', '/');
		while (StringTools.endsWith(clean, '/')) clean = clean.substr(0, clean.length - 1);
		return clean.substr(clean.lastIndexOf('/') + 1);
	}

	static function flag(section:Dynamic, name:String):Bool
		return section != null && Reflect.field(section, name) == true;

	static function text(value:String):String return value == null ? '' : value;
}
