package;

import haxe.Json;
import haxe.io.Path;

typedef CodenameScriptPlanData = {
	var version:Int;
	var song:String;
	var stages:Dynamic;
}

typedef CodenameNoteTypePlanData = {
	var version:Int;
	var song:String;
	var difficulties:Dynamic;
}

/** Destination-only identities needed to select Codename companions. */
class CodenameScriptPlan {
	public static inline var FILE_NAME = '__cammie_compat_scripts.json';
	/** Separate file so an older stage plan, including user edits, stays byte-identical. */
	public static inline var CAMERA_FILE_NAME = '__cammie_compat_camera.json';
	/** Separate selected-chart note type table; existing native charts stay untouched. */
	public static inline var NOTE_TYPES_FILE_NAME = '__cammie_compat_note_types.json';
	public static inline var VERSION = 1;

	public static function metadataPath(root:String, song:String):String {
		if (root == null || root == '' || !CodenameScriptDiscovery.safeName(song))
			return '';
		return Path.join([root, 'songs', song, FILE_NAME]);
	}

	public static function cameraMetadataPath(root:String, song:String):String {
		if (root == null || root == '' || !CodenameScriptDiscovery.safeName(song))
			return '';
		return Path.join([root, 'songs', song, CAMERA_FILE_NAME]);
	}

	public static function noteTypesMetadataPath(root:String, song:String):String {
		if (root == null || root == '' || !CodenameScriptDiscovery.safeName(song))
			return '';
		return Path.join([root, 'songs', song, NOTE_TYPES_FILE_NAME]);
	}

	/** Per-difficulty authored note tables used when an imported chart predates
	 * the inline codenameNoteTypes field. Type order and duplicate names are kept. */
	public static function createNoteTypes(song:String, difficulties:Dynamic):CodenameNoteTypePlanData {
		if (!CodenameScriptDiscovery.safeName(song) || difficulties == null
			|| !Reflect.isObject(difficulties) || Std.isOfType(difficulties, Array))
			throw 'Invalid Codename note type plan';
		var safeDifficulties:Dynamic = {};
		for (difficulty in Reflect.fields(difficulties)) {
			if (!CodenameScriptDiscovery.safeName(difficulty)) continue;
			var authored:Dynamic = Reflect.field(difficulties, difficulty);
			if (!Std.isOfType(authored, Array)) continue;
			var copy:Array<Dynamic> = [];
			for (kind in (cast authored:Array<Dynamic>))
				if (Std.isOfType(kind, String)) copy.push(kind);
			Reflect.setField(safeDifficulties, difficulty, copy);
		}
		return {version:VERSION, song:song, difficulties:safeDifficulties};
	}

	public static function stringifyNoteTypes(plan:CodenameNoteTypePlanData):String {
		if (plan == null) throw 'Missing Codename note type plan';
		return Json.stringify(createNoteTypes(plan.song, plan.difficulties));
	}

	public static function parseNoteTypes(raw:String):CodenameNoteTypePlanData {
		if (raw == null || raw == '') throw 'Missing Codename note type plan';
		var data:Dynamic = Json.parse(raw);
		if (data == null || !Std.isOfType(Reflect.field(data, 'version'), Int)
			|| Reflect.field(data, 'version') != VERSION
			|| !Std.isOfType(Reflect.field(data, 'song'), String)
			|| !CodenameScriptDiscovery.safeName(Reflect.field(data, 'song')))
			throw 'Invalid Codename note type plan';
		var difficulties:Dynamic = Reflect.field(data, 'difficulties');
		if (difficulties == null || !Reflect.isObject(difficulties) || Std.isOfType(difficulties, Array))
			throw 'Invalid Codename note type difficulty map';
		for (difficulty in Reflect.fields(difficulties)) {
			var types:Dynamic = Reflect.field(difficulties, difficulty);
			if (!CodenameScriptDiscovery.safeName(difficulty) || !Std.isOfType(types, Array))
				throw 'Invalid Codename note type entry';
			for (kind in (cast types:Array<Dynamic>))
				if (!Std.isOfType(kind, String)) throw 'Invalid Codename note type name';
		}
		return {version:VERSION, song:Reflect.field(data, 'song'), difficulties:difficulties};
	}

	public static function selectedNoteTypes(plan:CodenameNoteTypePlanData,
		difficulty:String):Array<Dynamic> {
		if (plan == null || !CodenameScriptDiscovery.safeName(difficulty)) return [];
		var types:Dynamic = Reflect.field(plan.difficulties, difficulty);
		return Std.isOfType(types, Array) ? (cast types:Array<Dynamic>).copy() : [];
	}

	static function cameraNumber(value:Dynamic):Float {
		if (!(Std.isOfType(value, Int) || Std.isOfType(value, Float)) || !Math.isFinite(value))
			throw 'Invalid Codename camera number';
		return value;
	}

	static function cameraPoint(value:Dynamic):Dynamic {
		if (value == null || Std.isOfType(value, Array)) throw 'Invalid Codename camera offset';
		return {cameraX:cameraNumber(Reflect.field(value, 'cameraX')),
			cameraY:cameraNumber(Reflect.field(value, 'cameraY'))};
	}

	static function cameraOptionalNumber(value:Dynamic):Null<Float> {
		return value == null ? null : cameraNumber(value);
	}

	static function cameraObject(value:Dynamic):Bool {
		return value != null && Type.typeof(value) == TObject;
	}

	/** The indices in `lines` are authored strumline indices, including lines
	 * whose notes cannot fit the native lanes. `visible` is the strumline flag;
	 * runtime actor visibility is checked separately. Camera offsets are named
	 * independently from stage/character sprite positions. `playerOffsets` is
	 * the nullable XML isPlayer hint, separate from the actor's camera role.
	 * `nativeCharacters` is optional for old metadata; when present, every
	 * authored line ID has an exact key. Null values mean a known unresolved
	 * actor, never an invitation to use a global registry fallback. */
	public static function createCamera(song:String, difficulties:Dynamic):Dynamic {
		if (!CodenameScriptDiscovery.safeName(song) || StringTools.trim(song) == ''
			|| !cameraObject(difficulties))
			throw 'Invalid Codename camera plan';
		var safeDifficulties:Dynamic = {};
		var difficultyNames = Reflect.fields(difficulties);
		for (difficulty in difficultyNames) {
			if (!CodenameScriptDiscovery.safeName(difficulty) || StringTools.trim(difficulty) == '')
				throw 'Invalid Codename camera difficulty';
			var entry:Dynamic = Reflect.field(difficulties, difficulty);
			if (!cameraObject(entry)) throw 'Invalid Codename camera difficulty entry';
			var stage:Dynamic = Reflect.field(entry, 'stage');
			var nativeStage:Dynamic = Reflect.field(entry, 'nativeStage');
			var lines:Dynamic = Reflect.field(entry, 'lines');
			var characters:Dynamic = Reflect.field(entry, 'characters');
			var nativeCharacters:Dynamic = Reflect.field(entry, 'nativeCharacters');
			var stageOffsets:Dynamic = Reflect.field(entry, 'stageOffsets');
			var stageStartCamera:Dynamic = Reflect.field(entry, 'stageStartCamera');
			var stagePlacement:Dynamic = Reflect.field(entry, 'stagePlacement');
			var missing:Dynamic = Reflect.field(entry, 'missingCharacters');
			var known:Dynamic = Reflect.field(entry, 'stageOffsetsKnown');
			if (!Std.isOfType(stage, String) || !CodenameScriptDiscovery.safeName(cast stage)
				|| (nativeStage != null && (!Std.isOfType(nativeStage, String)
					|| !CodenameScriptDiscovery.safeName(cast nativeStage)))
				|| !Std.isOfType(lines, Array)
				|| !cameraObject(characters) || !cameraObject(stageOffsets)
				|| !Std.isOfType(missing, Array) || !Std.isOfType(known, Bool))
				throw 'Invalid Codename camera difficulty';
			var safeLines:Array<Dynamic> = [];
			for (line in (cast lines:Array<Dynamic>)) {
				if (line == null) {
					safeLines.push(null);
					continue;
				}
				var role:Dynamic = Reflect.field(line, 'role');
				var type:Dynamic = Reflect.field(line, 'type');
				var position:Dynamic = Reflect.field(line, 'position');
				var visible:Dynamic = Reflect.field(line, 'visible');
				var ids:Dynamic = Reflect.field(line, 'characters');
				if (['opponent', 'player', 'gf', 'extra'].indexOf(role) < 0
					|| (type != null && (!Std.isOfType(type, Int) || type < 0))
					|| (position != null && !Std.isOfType(position, String))
					|| !Std.isOfType(visible, Bool) || !Std.isOfType(ids, Array)
					)
					throw 'Invalid Codename camera strumline';
				var keyCountValue = cameraLineNumber(Reflect.field(line, 'keyCount'), 4);
				var keyCount = !Math.isFinite(keyCountValue) || keyCountValue < 1
					|| keyCountValue != Math.floor(keyCountValue) ? 4 : Std.int(keyCountValue);
				var linePosDefault = CodenameStrumlineLayout.defaultLinePosition(type);
				var linePos = cameraLineNumber(Reflect.field(line, 'strumLinePos'), linePosDefault);
				if (!Math.isFinite(linePos)) linePos = linePosDefault;
				var strumScale = cameraLineNumber(Reflect.field(line, 'strumScale'), 1);
				if (!Math.isFinite(strumScale) || strumScale <= 0) strumScale = 1;
				var strumSpacing = cameraLineNumber(Reflect.field(line, 'strumSpacing'), 1);
				if (!Math.isFinite(strumSpacing) || strumSpacing <= 0) strumSpacing = 1;
				var strumPos:Array<Float> = [0, 50];
				var rawStrumPos:Dynamic = Reflect.field(line, 'strumPos');
				if (Std.isOfType(rawStrumPos, Array)) {
					var authoredPos:Array<Dynamic> = cast rawStrumPos;
					if (authoredPos.length >= 2) {
						var posX = cameraLineNumber(authoredPos[0], Math.NaN);
						var posY = cameraLineNumber(authoredPos[1], Math.NaN);
						if (Math.isFinite(posX) && Math.isFinite(posY)) strumPos = [posX, posY];
					}
				}
				var safeIds:Array<String> = [];
				for (id in (cast ids:Array<Dynamic>)) {
					if (!Std.isOfType(id, String) || !CodenameScriptDiscovery.safeRelativeName(cast id)
						|| StringTools.trim(cast id) == '') throw 'Invalid Codename camera character id';
					safeIds.push(cast id);
				}
				safeLines.push({role:role, type:type, position:position, visible:visible,
					characters:safeIds, keyCount:keyCount, strumLinePos:linePos,
					strumPos:strumPos, strumScale:strumScale, strumSpacing:strumSpacing});
			}
			var safeCharacters:Dynamic = {};
			var charIds = Reflect.fields(characters);
			for (id in charIds) {
				if (!CodenameScriptDiscovery.safeRelativeName(id) || StringTools.trim(id) == '')
					throw 'Invalid Codename camera character id';
				var offset = Reflect.field(characters, id);
				if (!cameraObject(offset)) throw 'Invalid Codename character camera offset';
				var centered:Dynamic = Reflect.field(offset, 'centeredCamera');
				var playerOffsets:Dynamic = Reflect.field(offset, 'playerOffsets');
				if (centered != null && !Std.isOfType(centered, Bool))
					throw 'Invalid Codename centered camera override';
				if (playerOffsets != null && !Std.isOfType(playerOffsets, Bool))
					throw 'Invalid Codename playerOffsets override';
				Reflect.setField(safeCharacters, id, {globalX:cameraNumber(Reflect.field(offset, 'globalX')),
					globalY:cameraNumber(Reflect.field(offset, 'globalY')),
					cameraX:cameraNumber(Reflect.field(offset, 'cameraX')),
					cameraY:cameraNumber(Reflect.field(offset, 'cameraY')),
					centeredCamera:centered, playerOffsets:playerOffsets});
			}
			var safeMissing:Array<String> = [];
			for (id in (cast missing:Array<Dynamic>)) {
				if (!Std.isOfType(id, String) || !CodenameScriptDiscovery.safeRelativeName(cast id)
					|| StringTools.trim(cast id) == '') throw 'Invalid missing Codename camera character';
				if (safeMissing.indexOf(cast id) < 0) safeMissing.push(cast id);
			}
			for (line in safeLines) if (line != null) for (id in (cast Reflect.field(line, 'characters'):Array<String>))
				if (!Reflect.hasField(safeCharacters, id) && safeMissing.indexOf(id) < 0)
					throw 'Codename camera character has no offset or missing diagnostic: ' + id;
			var safeNativeCharacters:Dynamic = null;
			if (nativeCharacters != null) {
				if (!cameraObject(nativeCharacters)) throw 'Invalid Codename native character map';
				safeNativeCharacters = {};
				for (id in Reflect.fields(nativeCharacters)) {
					if (!CodenameScriptDiscovery.safeRelativeName(id) || StringTools.trim(id) == '')
						throw 'Invalid Codename authored character id';
					var mapped:Dynamic = Reflect.field(nativeCharacters, id);
					if (mapped != null && (!Std.isOfType(mapped, String)
						|| !CodenameScriptDiscovery.safeName(cast mapped)
						|| StringTools.trim(cast mapped) == ''))
						throw 'Invalid Codename native character name';
					Reflect.setField(safeNativeCharacters, id, mapped);
				}
				for (line in safeLines) if (line != null) for (id in (cast Reflect.field(line, 'characters'):Array<String>))
					if (!Reflect.hasField(safeNativeCharacters, id))
						throw 'Missing Codename native character mapping: ' + id;
			}
			var safeStageOffsets:Dynamic = {};
			for (role in Reflect.fields(stageOffsets)) {
				if (['dad', 'bf', 'gf'].indexOf(role) < 0) throw 'Invalid Codename stage camera role';
				Reflect.setField(safeStageOffsets, role, cameraPoint(Reflect.field(stageOffsets, role)));
			}
			if (stageStartCamera != null && !cameraObject(stageStartCamera))
				throw 'Invalid Codename stage start camera';
			var safeStartCamera = {x:stageStartCamera == null ? null : cameraOptionalNumber(Reflect.field(stageStartCamera, 'x')),
				y:stageStartCamera == null ? null : cameraOptionalNumber(Reflect.field(stageStartCamera, 'y'))};
			// Older sidecars have no full placement model. Keep that gap explicit;
			// role camera offsets cannot reconstruct named slots or occurrences.
			var safePlacement = stagePlacement == null ? null
				: CodenameStagePlacement.toData(CodenameStagePlacement.fromData(stagePlacement));
			Reflect.setField(safeDifficulties, difficulty, {stage:stage, nativeStage:nativeStage,
				lines:safeLines,
				characters:safeCharacters, stageOffsets:safeStageOffsets,
				missingCharacters:safeMissing, stageOffsetsKnown:known,
				stageStartCamera:safeStartCamera, stagePlacement:safePlacement,
				nativeCharacters:safeNativeCharacters});
		}
		return {version:VERSION, song:song, difficulties:safeDifficulties};
	}

	static function cameraLineNumber(value:Dynamic, fallback:Float):Float {
		var number = if (Std.isOfType(value, Int) || Std.isOfType(value, Float))
			(cast value:Float) else if (Std.isOfType(value, String))
			Std.parseFloat(StringTools.trim(cast value)) else Math.NaN;
		return Math.isFinite(number) ? number : fallback;
	}

	public static function stringifyCamera(plan:Dynamic):String {
		return Json.stringify(createCamera(Reflect.field(plan, 'song'), Reflect.field(plan, 'difficulties')));
	}

	public static function parseCamera(raw:String):Dynamic {
		if (raw == null || raw == '') throw 'Missing Codename camera plan';
		var data:Dynamic = Json.parse(raw);
		if (!cameraObject(data) || !Std.isOfType(Reflect.field(data, 'version'), Int)
			|| Reflect.field(data, 'version') != VERSION)
			throw 'Invalid Codename camera plan version';
		return createCamera(Reflect.field(data, 'song'), Reflect.field(data, 'difficulties'));
	}

	public static function selectedCamera(plan:Dynamic, difficulty:String):Dynamic {
		if (plan == null || !CodenameScriptDiscovery.safeName(difficulty)) return null;
		return Reflect.field(Reflect.field(plan, 'difficulties'), difficulty);
	}

	public static function create(song:String, stages:Dynamic):CodenameScriptPlanData {
		if (!CodenameScriptDiscovery.safeName(song)) throw 'Invalid Codename song id';
		var safeStages:Dynamic = {};
		if (stages != null)
			for (difficulty in Reflect.fields(stages)) {
				var stage:Dynamic = Reflect.field(stages, difficulty);
				if (CodenameScriptDiscovery.safeName(difficulty)
					&& Std.isOfType(stage, String) && CodenameScriptDiscovery.safeName(cast stage))
					Reflect.setField(safeStages, difficulty, stage);
			}
		return {version:VERSION, song:song, stages:safeStages};
	}

	public static function stringify(plan:CodenameScriptPlanData):String {
		return Json.stringify(create(plan.song, plan.stages));
	}

	/** Reject malformed or unsafe metadata, rather than resolving another song's scripts. */
	public static function parse(raw:String):CodenameScriptPlanData {
		if (raw == null || raw == '') throw 'Missing Codename script plan';
		var data:Dynamic = Json.parse(raw);
		if (data == null || !Std.isOfType(Reflect.field(data, 'version'), Int)
			|| Reflect.field(data, 'version') != VERSION
			|| !Std.isOfType(Reflect.field(data, 'song'), String)
			|| !CodenameScriptDiscovery.safeName(Reflect.field(data, 'song')))
			throw 'Invalid Codename script plan';
		var stages:Dynamic = Reflect.field(data, 'stages');
		if (stages == null || !Reflect.isObject(stages) || Std.isOfType(stages, Array))
			throw 'Invalid Codename stage map';
		for (difficulty in Reflect.fields(stages)) {
			var stage:Dynamic = Reflect.field(stages, difficulty);
			if (!CodenameScriptDiscovery.safeName(difficulty)
				|| !Std.isOfType(stage, String) || !CodenameScriptDiscovery.safeName(cast stage))
				throw 'Invalid Codename stage id';
		}
		return {version:VERSION, song:Reflect.field(data, 'song'), stages:stages};
	}

	public static function selectedStage(plan:CodenameScriptPlanData, difficulty:String):String {
		if (plan == null || !CodenameScriptDiscovery.safeName(difficulty)) return '';
		var stage:Dynamic = Reflect.field(plan.stages, difficulty);
		return Std.isOfType(stage, String) && CodenameScriptDiscovery.safeName(cast stage) ? cast stage : '';
	}
}
