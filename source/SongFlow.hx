package;

/** Which chart a load request ends up on. */
typedef SongLoadTarget = {
	/** Song name as the caller spelled it (or the current song). */
	var song:String;
	/** Chart file name without extension, lower case. */
	var chart:String;
	/** Difficulty index the chart belongs to. */
	var difficulty:Int;
}

/**
	Pure decisions behind restarting, leaving and loading songs, plus the
	countdown options scripts can change. Nothing here touches Flixel, so the
	pause menu, game over, Lua and HXC all get the same answers from PlayState
	and the rules can be checked without a running game.
**/
class SongFlow {
	public static inline var MENU_STORY:String = 'story';
	public static inline var MENU_FREEPLAY:String = 'freeplay';

	/** Leaving a song goes back to the menu the player came from. */
	public static function exitMenu(isStoryMode:Bool):String {
		return isStoryMode ? MENU_STORY : MENU_FREEPLAY;
	}

	/**
		Work out the chart for loadSong(name, difficulty).

		No name means the current song. The difficulty can be an index, a
		difficulty name, or missing / negative / unknown index, which all keep
		the difficulty being played. Any other text is taken as a chart file
		name, which is what older scripts passed here.
	**/
	public static function loadTarget(name:Null<String>, difficulty:Dynamic, currentSong:Null<String>,
			currentDifficulty:Int, difficultyNames:Array<String>, defaultDifficulty:Int):Null<SongLoadTarget> {
		var song = name == null ? '' : StringTools.trim(name);
		if (song == '')
			song = currentSong == null ? '' : StringTools.trim(currentSong);
		if (song == '')
			return null;
		var names = difficultyNames == null ? [] : difficultyNames;
		var current = validIndex(currentDifficulty, names) ? currentDifficulty : defaultDifficulty;
		var index = current;
		if (difficulty != null) {
			if (Std.isOfType(difficulty, Float)) {
				var number:Float = difficulty;
				if (Math.isFinite(number) && validIndex(Std.int(number), names))
					index = Std.int(number);
			} else if (Std.isOfType(difficulty, String)) {
				var text = StringTools.trim(cast difficulty);
				if (text != '') {
					var named = difficultyIndex(text, names);
					if (named >= 0)
						index = named;
					else if (isWholeNumber(text)) {
						var parsed = Std.parseInt(text);
						if (parsed != null && validIndex(parsed, names))
							index = parsed;
					} else
						return {song: song, chart: text.toLowerCase(), difficulty: current};
				}
			}
		}
		return {song: song, chart: chartName(song, index, names, defaultDifficulty), difficulty: index};
	}

	/**
		True when a load target is the chart being played: same song (as the
		caller spelled it, ignoring case), same difficulty and the chart file
		that difficulty uses. Loading it again is a retry of the song.
	**/
	public static function sameChart(target:Null<SongLoadTarget>, currentSong:Null<String>, currentDifficulty:Int,
			difficultyNames:Array<String>, defaultDifficulty:Int):Bool {
		if (target == null || currentSong == null)
			return false;
		var song = StringTools.trim(currentSong);
		if (song == '' || target.song.toLowerCase() != song.toLowerCase() || target.difficulty != currentDifficulty)
			return false;
		var names = difficultyNames == null ? [] : difficultyNames;
		return target.chart == chartName(song, currentDifficulty, names, defaultDifficulty);
	}

	/** The default difficulty is the plain `<song>.json`, the rest add `-<name>`. */
	public static function chartName(song:String, difficulty:Int, difficultyNames:Array<String>,
			defaultDifficulty:Int):String {
		var base = song.toLowerCase();
		if (difficulty == defaultDifficulty || !validIndex(difficulty, difficultyNames))
			return base;
		return base + '-' + difficultyNames[difficulty].toLowerCase();
	}

	static function validIndex(index:Int, names:Array<String>):Bool {
		return index >= 0 && index < names.length && names[index] != null;
	}

	static function difficultyIndex(text:String, names:Array<String>):Int {
		var wanted = text.toLowerCase();
		for (index in 0...names.length)
			if (names[index] != null && names[index].toLowerCase() == wanted)
				return index;
		return -1;
	}

	static function isWholeNumber(text:String):Bool {
		var start = StringTools.startsWith(text, '-') ? 1 : 0;
		if (text.length == start)
			return false;
		for (index in start...text.length) {
			var code = text.charCodeAt(index);
			if (code < '0'.code || code > '9'.code)
				return false;
		}
		return true;
	}

	/**
		Intro sound names to try for one countdown step, best first.

		A script suffix is tried before the UI pack's own one and is never
		stacked on top of it, so a script asking for '-pixel' on a pixel UI
		still looks for `intro3-pixel`. Muted countdowns need no sound at all.
	**/
	public static function introSoundNames(name:String, scriptSuffix:Null<String>, uiSuffix:Null<String>,
			soundsEnabled:Bool):Array<String> {
		if (!soundsEnabled)
			return [];
		var ui = uiSuffix == null ? '' : uiSuffix;
		var scripted = scriptSuffix == null ? '' : scriptSuffix;
		var names:Array<String> = [];
		if (scripted != '' && scripted != ui)
			names.push(name + scripted);
		names.push(name + ui);
		return names;
	}

	/** The reset key only kills the player when nothing has taken it away. */
	public static function resetKeyAllowed(canReset:Bool, duoMode:Bool, inCutscene:Bool, controlsLocked:Bool,
			resetDisabledByPreference:Bool):Bool {
		return canReset && !duoMode && !inCutscene && !controlsLocked && !resetDisabledByPreference;
	}

	/** Psych and Nightmare Vision drop every note whose strum time is within 350 ms after the given time. */
	public static inline var CLEAR_NOTES_LEAD:Float = 350;

	public static function clearNotesCutoff(time:Float):Float {
		return time + CLEAR_NOTES_LEAD;
	}

	/**
		Scripts swap the start or end step of a song for their own intro or
		ending and hand back to the game when they are done. The slot holds
		only a scripted step: assigning nothing, or the game's own step, puts
		the default back.
	**/
	public static function handoffSlot(value:Dynamic, native:Dynamic):Dynamic {
		if (value == null)
			return null;
		if (!Reflect.isFunction(value))
			throw 'Song start and end callbacks must be functions';
		return native != null && Reflect.compareMethods(value, native) ? null : value;
	}

	/** What a script reads back: its own step, or the game's when none is set. */
	public static function handoffCurrent(slot:Dynamic, native:Dynamic):Dynamic {
		return slot == null ? native : slot;
	}
}
