package;

using StringTools;

import StoryMenuState.StorySongsJson;
import FreeplayState.JsonMetadata;
import flixel.math.FlxMath;
import DifficultyIcons.DiffInfo;
import haxe.io.Path;
#if sys
import sys.FileSystem;
#end
typedef CoolCategory = {
    var name:String;
    var songs:Array<JsonMetadata>;
}
typedef SourceDifficultyRules = {
	var selectable:Array<String>;
	var unsupported:Array<String>;
}
class DifficultyManager {
    static var diffJson:Dynamic;
    public static var supportedDiff:Map<String,Array<Int>> = [];
    public static var weeksSupported:Map<Int, Array<Int>> = [];

	public static function init() {
		supportedDiff = [];
		weeksSupported = [];
		diffJson = CoolUtil.parseJson(FNFAssets.getJson("assets/images/custom_difficulties/difficulties"));
        var fpJson:Array<CoolCategory> = cast FreeplayRegistry.getJson();
		// addSongSupport discovers authored suffixes for each song before it
		// builds the support map. Use the same path for startup and late imports.
        for (cat in fpJson) {
            for (song in cat.songs) {
                addSongSupport(song.name);
            }
        }
        var weekJson:StorySongsJson = CoolUtil.parseJson(FNFAssets.getText('assets/data/storySonglist.json'));
        var week = 0;
        for (weekThing in weekJson.weeks) {
            var weekSongs = weekThing.songs;
			var supThingies:Array<Int> = [];
			var thingsInWeek:Array<Int> = [];
			for (i in 0...weekSongs.length) {
                if (supportedDiff.get(weekSongs[i].toLowerCase()) != null)
				    thingsInWeek = thingsInWeek.concat(supportedDiff.get(weekSongs[i].toLowerCase()));
			}
			for (diff in 0...diffJson.difficulties.length) {
				var count = 0;
				for (thing in thingsInWeek) {
					if (diff == thing)
						count++;
				}
				if (count < weekSongs.length) {
					// do nothing, it isn't supported
				} else {
					supThingies.push(diff);
				}
			}
			// postfix means we get the value before it is incremented!
			weeksSupported.set(week++, supThingies);
        }
    }

	public static function addSongSupport(song:String) {
		if (song == null || StringTools.trim(song) == '')
			return;
		if (supportedDiff == null)
			supportedDiff = [];
		var key = StringTools.trim(song).toLowerCase();
		// Imports can finish after init() has scanned Freeplay. Discover any new
		// authored suffix before building support for the newly registered song.
		var sourceRules:SourceDifficultyRules = null;
		#if sys
		sourceRules = readAndDiscoverSongDifficulties(key);
		#end
		if (sourceRules == null)
			sourceRules = readSourceDifficultyRules(key);
		supportedDiff.set(key, []);
		if (diffJson == null || diffJson.difficulties == null)
			return;
		for (diff in 0...diffJson.difficulties.length) {
			var difficultyName = Std.string(Reflect.field(diffJson.difficulties[diff], 'name'));
			if (FNFAssets.exists('assets/data/${key}/${key + getDiffEnding(diff)}.json')
				&& NightmareVisionDifficultyCompat.allows(sourceRules.selectable, difficultyName)
				&& (sourceRules.unsupported == null
					|| !NightmareVisionDifficultyCompat.allows(sourceRules.unsupported, difficultyName))) {
				// : )
				supportedDiff.get(key).push(diff);
			}
		}
	}

	/** NMV imports retain extra charts for source-script access, but only the
	 * source owner's declared menu difficulties belong in Freeplay. */
	static function readSourceDifficultyRules(song:String):SourceDifficultyRules {
		if (song == null || StringTools.trim(song) == '')
			return {selectable: null, unsupported: null};
		var path = 'assets/data/' + song.toLowerCase() + '/importProvenance.json';
		if (!FNFAssets.exists(path))
			return {selectable: null, unsupported: null};
		try {
			var metadata:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
			if (metadata == null || Reflect.field(metadata, 'sourceEngine') != ImportEngine.NIGHTMARE_VISION)
				return {selectable: null, unsupported: null};
			return {
				selectable: sourceDifficultyNames(Reflect.field(metadata, 'sourceSelectableDifficulties')),
				unsupported: sourceDifficultyNames(Reflect.field(metadata, 'sourceUnsupportedDifficulties'))
			};
		} catch (_:Dynamic) {
			return {selectable: null, unsupported: null};
		}
	}

	static function sourceDifficultyNames(raw:Dynamic):Array<String> {
		if (!Std.isOfType(raw, Array))
			return null;
		var result:Array<String> = [];
		for (value in (cast raw:Array<Dynamic>))
			if (value != null && StringTools.trim(Std.string(value)) != '')
				result.push(StringTools.trim(Std.string(value)).toLowerCase());
		return result.length == 0 ? null : result;
	}

	static function readSourceSelectableDifficulties(song:String):Array<String> {
		return readSourceDifficultyRules(song).selectable;
	}

	/** Imported NMV charts that fail the generic source-schema adapter remain
	 * on disk for inspection, but must not be offered as playable difficulties. */
	static function readSourceUnsupportedDifficulties(song:String):Array<String> {
		return readSourceDifficultyRules(song).unsupported;
	}

	/** Return a stable, never-null support list. Imports can finish after the
	 * title-time registry scan, and duplicate/repair imports may add a Freeplay
	 * entry without appearing in the current batch's newly-copied song list.
	 * Resolve that race lazily instead of calling Array.contains on null in a
	 * native build (which becomes a SIGSEGV). */
	public static function getSupportedDiffs(song:String):Array<Int> {
		if (song == null || StringTools.trim(song) == '')
			return [];
		if (supportedDiff == null)
			supportedDiff = [];
		var key = StringTools.trim(song).toLowerCase();
		var supported = supportedDiff.get(key);
		if (supported == null) {
			addSongSupport(key);
			supported = supportedDiff.get(key);
		}
		return supported == null ? [] : supported;
	}

	/** Return the donor difficulty suffix encoded in a native chart filename.
	 * The base `<song>.json` chart is the configured default and therefore has
	 * no new suffix. Sidecars are excluded so `events.json` can never become a
	 * selectable difficulty. */
	public static function difficultySuffixFromChartFile(song:String, file:String):String {
		if (song == null || file == null)
			return null;
		var key = StringTools.trim(song).toLowerCase();
		var name = Path.withoutDirectory(Path.normalize(file)).toLowerCase();
		if (name.endsWith('.jsonc'))
			name = name.substr(0, name.length - 6);
		else if (name.endsWith('.json'))
			name = name.substr(0, name.length - 5);
		else
			return null;
		if (name == key)
			return '';
		var prefix = key + '-';
		if (!name.startsWith(prefix))
			return null;
		var suffix = StringTools.trim(name.substr(prefix.length));
		if (suffix == '' || suffix == 'events' || suffix == 'metadata'
			|| suffix == 'manifest' || suffix == 'dialogue' || suffix == 'chartmeta')
			return null;
		return suffix;
	}

	#if sys
	static function discoverSongDifficulties(song:String):Void {
		readAndDiscoverSongDifficulties(song);
	}

	/** Read owner rules once while scanning a song, then share them with the
	 * support-map builder. This remains per-call so completed imports are fresh. */
	static function readAndDiscoverSongDifficulties(song:String):SourceDifficultyRules {
		var directory = Path.join(['assets', 'data', song]);
		if (!FileSystem.exists(directory) || !FileSystem.isDirectory(directory))
			return null;
		var entries:Array<String>;
		try {
			entries = FileSystem.readDirectory(directory);
		} catch (_:Dynamic) {
			return null;
		}
		if (entries == null)
			return null;
		entries.sort(function(a:String, b:String):Int return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		var sourceRules = readSourceDifficultyRules(song);
		for (entry in entries) {
			var suffix = difficultySuffixFromChartFile(song, entry);
			if (suffix != null && suffix != ''
				&& NightmareVisionDifficultyCompat.allows(sourceRules.selectable, suffix)
				&& (sourceRules.unsupported == null
					|| !NightmareVisionDifficultyCompat.allows(sourceRules.unsupported, suffix)))
				ensureDifficultyDefinition(suffix);
		}
		return sourceRules;
	}
	#end

	static function ensureDifficultyDefinition(name:String):Int {
		if (diffJson == null || diffJson.difficulties == null || name == null)
			return -1;
		var clean = StringTools.trim(name).toLowerCase();
		if (clean == '')
			return -1;
		var difficulties:Array<Dynamic> = cast diffJson.difficulties;
		for (index in 0...difficulties.length) {
			var difficulty = difficulties[index];
			if (difficulty != null && difficulty.name != null
				&& Std.string(difficulty.name).toLowerCase() == clean)
				return index;
		}
		// Reuse the ordinary HARD icon when a foreign engine does not provide an
		// icon definition. The name and filename suffix remain exact.
		difficulties.push({offset: 20, anim: 'HARD', name: clean});
		return difficulties.length - 1;
	}

    public static function changeDifficulty(diff:Int, ?change:Int=0):DiffInfo {
        // we can do it directly because Ints are saved by value : )
		if (diffJson == null || diffJson.difficulties == null || diffJson.difficulties.length == 0)
			return {difficulty: 0, text: ''};
        diff += change;
        diff = FlxMath.wrap(diff, 0, Std.int(diffJson.difficulties.length - 1));
        return {difficulty: diff, text: diffJson.difficulties[diff].name.toUpperCase()};
    }

    // sans : ) meaning without, this omits any bad difficulties
	public static function changeDifficultySans(diff:Int, ?change:Int=0, ?song:String="tutorial"):DiffInfo {
		var foundSomething = false;
		var giveUpNum = 0;
		var giveUpResult = changeDifficulty(diff, change);
		var supported = getSupportedDiffs(song);
		if (supported.length == 0)
			return giveUpResult;
		var ignoreIfExists = change == 0;
        if (change == 0)
            change = 1;
        while (giveUpNum < diffJson.difficulties.length && !foundSomething) {
			if (supported.contains(diff) && ignoreIfExists)
				return giveUpResult;
            var sus = changeDifficulty(diff, change);
            diff = sus.difficulty;
            
			if (supported.contains(diff))
				return sus;
            giveUpNum++;
        }
        return giveUpResult;
    }

    public static function changeDiffStorySans(diff:Int, ?change:Int = 0, ?week:Int=0) {
		var foundSomething = false;
		var giveUpNum = 0;
		var giveUpResult = changeDifficulty(diff, change);
		var ignoreIfExists = change == 0;
		if (change == 0)
			change = 1;
		if (weeksSupported == null)
			return giveUpResult;
		var daSupport = weeksSupported.get(week);
		if (daSupport == null || daSupport.length == 0)
			return giveUpResult;
		while (giveUpNum < diffJson.difficulties.length && !foundSomething) {
			if (daSupport.contains(diff) && ignoreIfExists)
				return giveUpResult;
			var sus = changeDifficulty(diff, change);
			diff = sus.difficulty;

			if (daSupport.contains(diff))
				return sus;
			giveUpNum++;
		}
		return giveUpResult;
    }

    public static function getDiffName(diff:Int):String {
		return diffJson.difficulties[diff].name.toUpperCase();
    }

    public static function getDiffNum(diffName:String):Int {
        for (diff in 0...diffJson.difficulties.length) {
            if (diffJson.difficulties[diff].name.toLowerCase() == diffName.toLowerCase())
                return diff;
        }
        return 0;
    }

    public static function getDefaultForDiff(diff:Int):String {
        var daDefault;
        if (diffJson.difficulties[diff].defaults != null)
            daDefault = diffJson.difficulties[diff].defaults;
        else
            daDefault = '';
        return daDefault;
    }

    public static function getDefaultFromName(diffName:String) {
        var diff = getDiffNum(diffName);
        return getDefaultForDiff(diff);
    }

    // Song metadata fallback needs to consider sibling charts too. Keep the
    // configured order here so web builds (which cannot enumerate the data
    // directory) get the same candidates as native builds.
    public static function getDifficultyNames():Array<String> {
        var names:Array<String> = [];
        if (diffJson == null || diffJson.difficulties == null)
            return names;
        var difficulties:Array<Dynamic> = cast diffJson.difficulties;
        for (difficulty in difficulties) {
            if (difficulty != null && difficulty.name != null)
                names.push(difficulty.name);
        }
        return names;
    }

    public static function getDiffEnding(diff:Int):String {
        var ending = "";
        if (diff != diffJson.defaultDiff)
            ending = "-" + diffJson.difficulties[diff].name;
        return ending;
    }

    // get a valid difficulty
	public static function getValidDiff(diff:Int, song:String):Int {
		var daThing = getSupportedDiffs(song);
		if (daThing.length == 0)
			return changeDifficulty(diff).difficulty;
        // if the diff is there, no problem
        if (daThing.contains(diff))
            return diff;
        // otherwise if the default diff is there prefer that
        if (daThing.contains(diffJson.defaultDiff))
            return diffJson.defaultDiff;
        // otherwise prefer the hardest difficulty : )
		return daThing[daThing.length - 1];
    }

    public static function getDefaultDiff():Int {
        return diffJson.defaultDiff;
    }
}
