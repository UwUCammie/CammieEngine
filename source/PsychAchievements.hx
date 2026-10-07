package;

import haxe.Exception;
import haxe.ds.StringMap;
import PsychAchievementInfo;
import PsychAchievementsHost.PsychAchievementSource;
import PsychAchievementsHost.PsychAchievementsHost;

using StringTools;

/** Owner-local implementation of Psych 1.0.4 `backend.Achievements`.
	The save adapter and all asset, mod-list, audio, diagnostic, clock, and popup
	operations are captured for one imported owner. */
@:keep
class PsychAchievements {
	static inline var MAP_MARKER:String = '__psychAchievementsMap__';
	static inline var UNLOCKED_FIELD:String = 'achievementsUnlocked';
	static inline var VARIABLES_FIELD:String = 'achievementsVariables';

	public var achievements:Map<String, PsychAchievementInfo> = new Map();
	public var variables:Map<String, Float> = new Map();
	public var achievementsUnlocked:Array<String> = [];

	final ownerRoot:String;
	var ownerSave:Dynamic;
	var host:PsychAchievementsHost;
	var firstLoad:Bool = true;
	var sortID:Int = 0;
	var originalLength:Int = -1;
	var lastUnlock:Int = -999;
	var released:Bool = false;

	public function new(ownerRoot:String, ownerSave:Dynamic,
		host:PsychAchievementsHost) {
		if (ownerSave == null || !Reflect.isFunction(Reflect.field(ownerSave, 'getField'))
			|| !Reflect.isFunction(Reflect.field(ownerSave, 'setField'))
			|| !Reflect.isFunction(Reflect.field(ownerSave, 'flush')))
			throw '[psych-achievements] Missing owner-scoped save data';
		validateHost(host);
		var normalizedOwner = normalizeOwnerKey(ownerRoot);
		var pathsOwner = normalizeOwnerKey(readPathsOwner(host.paths));
		if (normalizedOwner == '' || normalizedOwner != pathsOwner)
			throw '[psych-achievements] Captured Paths owner does not match the selected import';
		this.ownerRoot = normalizedOwner;
		this.ownerSave = ownerSave;
		this.host = host;
	}

	public function init():Void {
		ensureAlive();
		createAchievement('friday_night_play', {name:'Freaky on a Friday Night',
			description:'Play on a Friday... Night.', hidden:true});
		#if BASE_GAME_FILES
		createAchievement('week1_nomiss', {name:'She Calls Me Daddy Too', description:'Beat Week 1 on Hard with no Misses.'});
		createAchievement('week2_nomiss', {name:'No More Tricks', description:'Beat Week 2 on Hard with no Misses.'});
		createAchievement('week3_nomiss', {name:'Call Me The Hitman', description:'Beat Week 3 on Hard with no Misses.'});
		createAchievement('week4_nomiss', {name:'Lady Killer', description:'Beat Week 4 on Hard with no Misses.'});
		createAchievement('week5_nomiss', {name:'Missless Christmas', description:'Beat Week 5 on Hard with no Misses.'});
		createAchievement('week6_nomiss', {name:'Highscore!!', description:'Beat Week 6 on Hard with no Misses.'});
		createAchievement('week7_nomiss', {name:'God Effing Damn It!', description:'Beat Week 7 on Hard with no Misses.'});
		createAchievement('weekend1_nomiss', {name:'Just a Friendly Sparring', description:'Beat Weekend 1 on Hard with no Misses.'});
		#end
		createAchievement('ur_bad', {name:"What a Funkin' Disaster!",
			description:'Complete a Song with a rating lower than 20%.'});
		createAchievement('ur_good', {name:'Perfectionist',
			description:'Complete a Song with a rating of 100%.'});
		#if BASE_GAME_FILES
		createAchievement('roadkill_enthusiast', {name:'Roadkill Enthusiast',
			description:'Watch the Henchmen die 50 times.', maxScore:50, maxDecimals:0});
		#end
		createAchievement('oversinging', {name:'Oversinging Much...?',
			description:'Sing for 10 seconds without going back to Idle.'});
		createAchievement('hype', {name:'Hyperactive',
			description:'Finish a Song without going back to Idle.'});
		createAchievement('two_keys', {name:'Just the Two of Us',
			description:'Finish a Song pressing only two keys.'});
		createAchievement('toastie', {name:'Toaster Gamer',
			description:'Have you tried to run the game on a toaster?'});
		#if BASE_GAME_FILES
		createAchievement('debugger', {name:'Debugger',
			description:'Beat the "Test" Stage from the Chart Editor.', hidden:true});
		#end
		// The pinned Psych Project.xml always defines PSYCH_WATERMARKS. Keep this
		// source default even though the host engine does not compile that define.
		createAchievement('pessy_easter_egg', {name:'Engine Gal Pal',
			description:'Teehee, you found me~!', hidden:true});
		// The source counts IDs from the next slot and includes that slot in the
		// base boundary used by reloadList when it removes mod-owned entries.
		originalLength = sortID + 1;
	}

	public function get(name:String):PsychAchievementInfo {
		ensureAlive();
		return achievements.get(name);
	}

	public function exists(name:String):Bool {
		ensureAlive();
		return achievements.exists(name);
	}

	public function load():Void {
		ensureAlive();
		if (!firstLoad) return;
		if (originalLength < 0) init();

		var savedUnlocked = readField(UNLOCKED_FIELD);
		if (savedUnlocked != null) achievementsUnlocked = restoreUnlocked(savedUnlocked);
		var savedVariables = readField(VARIABLES_FIELD);
		if (savedVariables != null) variables = restoreFloatMap(savedVariables, VARIABLES_FIELD);
		firstLoad = false;
	}

	/** Writes the donor field names into this import's private save bucket. */
	public function save():Void {
		ensureAlive();
		writeField(UNLOCKED_FIELD, achievementsUnlocked);
		writeField(VARIABLES_FIELD, snapshotFloatMap(variables));
	}

	public function getScore(name:String):Float return scoreFunc(name, 'get');

	public function setScore(name:String, value:Float, saveIfNotUnlocked:Bool = true):Float
		return scoreFunc(name, 'set', value, saveIfNotUnlocked);

	public function addScore(name:String, value:Float = 1, saveIfNotUnlocked:Bool = true):Float
		return scoreFunc(name, 'add', value, saveIfNotUnlocked);

	function scoreFunc(name:String, operation:String, addOrSet:Float = 1,
		saveIfNotUnlocked:Bool = true):Float {
		ensureAlive();
		if (!variables.exists(name)) variables.set(name, 0);
		if (!achievements.exists(name)) return -1;

		var achievement = achievements.get(name);
		var maxScore:Float = achievement.maxScore == null ? 0 : achievement.maxScore;
		if (maxScore < 1)
			throw new Exception('Achievement has score disabled or is incorrectly configured: $name');
		if (achievementsUnlocked.contains(name)) return maxScore;

		var value = addOrSet;
		switch (operation) {
			case 'get': return variables.get(name);
			case 'add': value += variables.get(name);
			default:
		}

		if (value >= maxScore) {
			unlock(name);
			value = maxScore;
		}
		variables.set(name, value);
		save();
		if (saveIfNotUnlocked || value >= maxScore) flushOwner();
		return value;
	}

	public function unlock(name:String, autoStartPopup:Bool = true):String {
		ensureAlive();
		if (!achievements.exists(name)) {
			var error = 'Achievement "$name" does not exists!';
			host.report(error);
			throw new Exception(error);
		}
		if (isUnlocked(name)) return null;

		host.report('Completed achievement "$name"');
		achievementsUnlocked.push(name);
		var time = host.nowMillis();
		if (Math.abs(time - lastUnlock) >= 100) {
			host.playConfirmSound('confirmMenu', 0.5);
			lastUnlock = time;
		}
		save();
		flushOwner();
		if (autoStartPopup) startPopup(name);
		return name;
	}

	public function isUnlocked(name:String):Bool {
		ensureAlive();
		return achievementsUnlocked.indexOf(name) >= 0;
	}

	public var showingPopups(get, never):Bool;
	function get_showingPopups():Bool {
		ensureAlive();
		return host.showingPopups();
	}

	public function startPopup(achieve:String, endFunc:Void->Void = null):Void {
		ensureAlive();
		host.showPopup(achieve, get(achieve), endFunc);
	}

	public function getAchievementInfo(id:String):Null<PsychAchievementInfo> {
		ensureAlive();
		return achievements.get(id);
	}

	public function createAchievement(name:String, data:PsychAchievementInfo,
		?mod:String = null):Void {
		ensureAlive();
		if (data == null) throw '[psych-achievements] Cannot create an achievement from null data';
		Reflect.setField(data, 'ID', sortID);
		Reflect.setField(data, 'mod', mod);
		achievements.set(name, data);
		sortID++;
	}

	/** Reloads the ordered base and enabled-mod list supplied by the authenticated
		owner. It never reads or changes process-wide mod selection state. */
	public function reloadList():Void {
		ensureAlive();
		if (originalLength < 0) init();
		if ((sortID + 1) > originalLength) {
			var toRemove:Array<String> = [];
			for (key => value in achievements) if (value.mod != null) toRemove.push(key);
			for (key in toRemove) achievements.remove(key);
		}
		sortID = originalLength - 1;
		var sources = host.achievementSources();
		if (sources == null) throw '[psych-achievements] Owner achievement source list is unavailable';
		for (source in sources) {
			if (source == null || source.path == null || source.path == '') continue;
			loadAchievementJson(source);
		}
	}

	function loadAchievementJson(source:PsychAchievementSource):Null<Array<Dynamic>> {
		var result:Array<Dynamic> = null;
		try {
			var raw = host.readText(source.path);
			if (raw == null) return null;
			raw = raw.trim();
			if (raw.length > 0) result = cast tjson.TJSON.parse(raw);
			if (result != null) for (index in 0...result.length) {
				var achievement:Dynamic = result[index];
				if (achievement == null) {
					host.report(sourceLabel(source) + ' - Achievement #${index + 1} is invalid.');
					continue;
				}
				var key:Dynamic = Reflect.field(achievement, 'save');
				if (key == null || !Std.isOfType(key, String) || (cast key:String).trim().length < 1) {
					var displayName = Reflect.field(achievement, 'name');
					var err = 'Error on Achievement: ' + (displayName == null ? 'null' : Std.string(displayName));
					host.report(err + ' - Missing valid "save" value.');
					continue;
				}
				key = (cast key:String).trim();
				if (achievements.exists(key)) continue;
				createAchievement(cast key, cast achievement, source.mod);
			}
		} catch (error:Dynamic) {
			host.report(sourceLabel(source) + ' - Error loading achievements.json: ' + Std.string(error));
		}
		return result;
	}

	public function release():Void {
		if (released) return;
		released = true;
		ownerSave = null;
		host = null;
		achievements = new Map();
		variables = new Map();
		achievementsUnlocked = [];
	}

	function snapshotFloatMap(values:Map<String, Float>):Dynamic {
		var keys:Array<String> = [];
		for (key in values.keys()) keys.push(key);
		keys.sort(Reflect.compare);
		var entries:Array<Dynamic> = [];
		for (key in keys) entries.push([key, values.get(key)]);
		return {__psychAchievementsMap__:true, entries:entries};
	}

	static function restoreFloatMap(value:Dynamic, field:String):Map<String, Float> {
		var result:Map<String, Float> = new Map();
		if (Std.isOfType(value, StringMap)) {
			var input:StringMap<Dynamic> = cast value;
			for (key in input.keys()) result.set(key, asFloat(input.get(key), field, key));
			return result;
		}
		if (Type.typeof(value) != TObject)
			throw '[psych-achievements] Malformed owner map: ' + field;
		var entries:Dynamic = Reflect.field(value, MAP_MARKER) == true ? Reflect.field(value, 'entries') : null;
		if (Reflect.field(value, MAP_MARKER) == true) {
			if (!Std.isOfType(entries, Array)) throw '[psych-achievements] Malformed owner map entries: ' + field;
			for (entry in (cast entries:Array<Dynamic>)) {
				if (!Std.isOfType(entry, Array) || (cast entry:Array<Dynamic>).length != 2
					|| !Std.isOfType((cast entry:Array<Dynamic>)[0], String))
					throw '[psych-achievements] Malformed owner map entry: ' + field;
				var key:String = (cast entry:Array<Dynamic>)[0];
				result.set(key, asFloat((cast entry:Array<Dynamic>)[1], field, key));
			}
		} else for (key in Reflect.fields(value))
			result.set(key, asFloat(Reflect.field(value, key), field, key));
		return result;
	}

	static function restoreUnlocked(value:Dynamic):Array<String> {
		if (!Std.isOfType(value, Array))
			throw '[psych-achievements] Malformed owner unlock list';
		var result:Array<String> = [];
		for (entry in (cast value:Array<Dynamic>)) {
			if (!Std.isOfType(entry, String)) throw '[psych-achievements] Malformed owner unlock entry';
			result.push(cast entry);
		}
		return result;
	}

	static function asFloat(value:Dynamic, field:String, key:String):Float {
		switch (Type.typeof(value)) {
			case TInt: return cast value;
			case TFloat: return cast value;
			default: throw '[psych-achievements] Invalid score in ' + field + ': ' + key;
		}
	}

	function readField(field:String):Dynamic {
		var method:Dynamic = Reflect.field(ownerSave, 'getField');
		return Reflect.callMethod(ownerSave, method, [field]);
	}

	function writeField(field:String, value:Dynamic):Void {
		var method:Dynamic = Reflect.field(ownerSave, 'setField');
		Reflect.callMethod(ownerSave, method, [field, value]);
	}

	function flushOwner():Void {
		var method:Dynamic = Reflect.field(ownerSave, 'flush');
		Reflect.callMethod(ownerSave, method, []);
	}

	function ensureAlive():Void {
		if (released) throw '[psych-achievements] This owner achievement service has been released';
		if (host == null || !host.ownerActive())
			throw '[psych-achievements] This owner achievement service is inactive';
	}

	static function validateHost(host:PsychAchievementsHost):Void {
		if (host == null || host.paths == null || !Reflect.isFunction(host.ownerActive)
			|| !Reflect.isFunction(host.achievementSources) || !Reflect.isFunction(host.readText)
			|| !Reflect.isFunction(host.report) || !Reflect.isFunction(host.playConfirmSound)
			|| !Reflect.isFunction(host.nowMillis) || !Reflect.isFunction(host.showingPopups)
			|| !Reflect.isFunction(host.showPopup))
			throw '[psych-achievements] Missing a required owner-captured service callback';
	}

	static function readPathsOwner(paths:Dynamic):String {
		var getter = Reflect.field(paths, '__sourceOwnerRoot');
		if (!Reflect.isFunction(getter)) throw '[psych-achievements] Expected captured Psych Paths';
		return Std.string(Reflect.callMethod(paths, getter, []));
	}

	static function normalizeOwnerKey(value:String):String {
		if (value == null) return '';
		var normalized = haxe.io.Path.normalize(value.replace('\\', '/'));
		while (normalized.endsWith('/')) normalized = normalized.substr(0, normalized.length - 1);
		return normalized;
	}

	function sourceLabel(source:PsychAchievementSource):String {
		return 'Mod name: ' + (source.mod == null || source.mod == '' ? 'None' : source.mod);
	}
}
