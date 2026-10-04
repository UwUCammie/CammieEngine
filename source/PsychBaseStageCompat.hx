package;

import flixel.FlxBasic;
import hscript.ScriptClass;
import hscript.ScriptClassScope;

/** Minimal owner-side host contract for Psych's compiled BaseStage callbacks.
	The donor BaseStage source depends on native Character, Note, FlxBasic and
	PlayState types. HScript stage classes instead inherit this adapter; live
	state fields and scene operations are delegated through the selected owner
	host supplied by PsychCompiledStageRuntime.
*/
class PsychBaseStageCompat {
	var stageHost:Dynamic;
	var ownerClassScope:ScriptClassScope;
	var compatBoyfriendGroup:PsychBaseStageActorGroupCompat;
	var compatDadGroup:PsychBaseStageActorGroupCompat;
	var compatGfGroup:PsychBaseStageActorGroupCompat;
	var creatingBackground:Bool = true;

	public function new(?stageHost:Dynamic) {
		this.stageHost = stageHost;
	}

	public function attachHost(stageHost:Dynamic):Void {
		if (this.stageHost != null && this.stageHost != stageHost)
			throw '[psych-stage] BaseStage host cannot change owners';
		this.stageHost = stageHost;
	}

	public function attachScriptClassScope(scope:ScriptClassScope):Void {
		if (ownerClassScope != null && ownerClassScope != scope)
			throw '[psych-stage] BaseStage class scope cannot change owners';
		ownerClassScope = scope;
	}

	public var game(get, never):Dynamic;
	function get_game():Dynamic return stageHost;

	@:keep public var controls(get, never):Dynamic;
	function get_controls():Dynamic {
		var sourceControls = readField('psychControls');
		return sourceControls == null ? readField('controls') : sourceControls;
	}

	public var onPlayState(get, never):Bool;
	function get_onPlayState():Bool return boolField('onPlayState', stageHost != null);

	public var paused(get, never):Bool;
	function get_paused():Bool return boolField('paused', false);

	public var songName(get, never):String;
	function get_songName():String {
		// Psych sets songName from the chart's SONG.song. This fork also has a
		// HUD FlxText named songName, which must never become the source stage id.
		var song = staticField('SONG');
		if (song == null) song = readField('SONG');
		var value = song == null ? null : Reflect.field(song, 'song');
		if (value == null) value = readField('curSong');
		return value == null ? '' : PsychSongNameCompat.format(Std.string(value));
	}

	public var isStoryMode(get, never):Bool;
	function get_isStoryMode():Bool return staticBoolField('isStoryMode', false);

	public var seenCutscene(get, never):Bool;
	function get_seenCutscene():Bool return staticBoolField('watchedCutscene', false);

	public var inCutscene(get, set):Bool;
	function get_inCutscene():Bool return boolField('inCutscene', false);
	function set_inCutscene(value:Bool):Bool return writeBoolField('inCutscene', value);

	public var canPause(get, set):Bool;
	function get_canPause():Bool return boolField('canPause', true);
	function set_canPause(value:Bool):Bool return writeBoolField('canPause', value);

	public var members(get, never):Array<Dynamic>;
	function get_members():Array<Dynamic> {
		var value:Dynamic = readField('members');
		return Std.isOfType(value, Array) ? cast value : [];
	}

	public var boyfriend(get, never):Dynamic;
	function get_boyfriend():Dynamic return readField('boyfriend');

	public var dad(get, never):Dynamic;
	function get_dad():Dynamic return readField('dad');

	public var gf(get, never):Dynamic;
	function get_gf():Dynamic return readField('gf');

	public var boyfriendGroup(get, never):Dynamic;
	function get_boyfriendGroup():Dynamic {
		var nativeGroup = readField('boyfriendGroup');
		if (nativeGroup != null) return nativeGroup;
		if (compatBoyfriendGroup == null) compatBoyfriendGroup = new PsychBaseStageActorGroupCompat(stageHost, 'bf');
		return compatBoyfriendGroup;
	}

	public var dadGroup(get, never):Dynamic;
	function get_dadGroup():Dynamic {
		var nativeGroup = readField('dadGroup');
		if (nativeGroup != null) return nativeGroup;
		if (compatDadGroup == null) compatDadGroup = new PsychBaseStageActorGroupCompat(stageHost, 'dad');
		return compatDadGroup;
	}

	public var gfGroup(get, never):Dynamic;
	function get_gfGroup():Dynamic {
		var nativeGroup = readField('gfGroup');
		if (nativeGroup != null) return nativeGroup;
		if (compatGfGroup == null) compatGfGroup = new PsychBaseStageActorGroupCompat(stageHost, 'gf');
		return compatGfGroup;
	}

	public var unspawnNotes(get, never):Array<Dynamic>;
	function get_unspawnNotes():Array<Dynamic> {
		var value:Dynamic = readField('unspawnNotes');
		return Std.isOfType(value, Array) ? cast value : [];
	}

	public var camGame(get, never):Dynamic;
	function get_camGame():Dynamic return readField('camGame');

	public var camHUD(get, never):Dynamic;
	function get_camHUD():Dynamic return readField('camHUD');

	public var camOther(get, never):Dynamic;
	function get_camOther():Dynamic return readField('camOther');

	public var defaultCamZoom(get, set):Float;
	function get_defaultCamZoom():Float return floatField('defaultCamZoom', 1.05);
	function set_defaultCamZoom(value:Float):Float {
		writeField('defaultCamZoom', value);
		return value;
	}

	public var camFollow(get, never):Dynamic;
	function get_camFollow():Dynamic return readField('camFollow');

	public var curBeat(get, never):Int;
	function get_curBeat():Int return intField('curBeat', 0);

	public var curDecBeat(get, never):Float;
	function get_curDecBeat():Float return floatField('curDecBeat', 0);

	public var curStep(get, never):Int;
	function get_curStep():Int return intField('curStep', 0);

	public var curDecStep(get, never):Float;
	function get_curDecStep():Float return floatField('curDecStep', 0);

	public var curSection(get, never):Int;
	function get_curSection():Int {
		// Psych refreshes section ownership before its stage callbacks. This fork
		// updates PlayState.curSection later in stepHit(), so query its pure
		// section calculation when the host exposes one without mutating state.
		var section = callHost('getSection', []);
		return Std.isOfType(section, Int) ? cast section : intField('curSection', 0);
	}

	public function create():Void {}
	public function createPost():Void {}
	public function update(_elapsed:Float):Void {}
	public function countdownTick(_count:Dynamic, _num:Int):Void {}
	public function startSong():Void {}
	public function beatHit():Void {}
	public function stepHit():Void {}
	public function sectionHit():Void {}
	// Psych BaseStage defaults these lifecycle callbacks to no-op. Delegating
	// back into the PlayState host here would recursively re-enter the callback.
	public function openSubState(_subState:Dynamic):Void {}
	public function closeSubState():Void {}
	public function eventCalled(_eventName:String, _value1:String, _value2:String,
		_flValue1:Null<Float>, _flValue2:Null<Float>, _strumTime:Float):Void {}
	public function eventPushed(_event:Dynamic):Void {}
	public function eventPushedUnique(_event:Dynamic):Void {}
	public function goodNoteHit(_note:Dynamic):Void {}
	public function opponentNoteHit(_note:Dynamic):Void {}
	public function noteMiss(_note:Dynamic):Void {}
	public function noteMissPress(_direction:Int):Void {}
	public function destroy():Void {}

	public function add(object:Dynamic):Dynamic {
		var nativeObject = sceneObject(object, true);
		// Psych constructs the stage before adding its character groups. This
		// engine constructs actors first, so preserve Psych's draw order by
		// inserting create() props ahead of the earliest actor. createPost() and
		// later callbacks append as authored; addBehind* uses explicit insert().
		var actorIndex = creatingBackground ? firstActorMemberIndex() : -1;
		var result = actorIndex < 0 ? callHost('add', [nativeObject])
			: callHost('insert', [actorIndex, nativeObject]);
		return nativeObject == object ? result : object;
	}

	public function beginPostCreate():Void creatingBackground = false;

	function firstActorMemberIndex():Int {
		var first = -1;
		for (role in ['gf', 'dad', 'bf']) {
			var groupField = role == 'gf' ? 'gfGroup' : role == 'bf' ? 'boyfriendGroup' : 'dadGroup';
			var actorField = role == 'gf' ? 'gf' : role == 'bf' ? 'boyfriend' : 'dad';
			var group = readField(groupField);
			var actor = group != null ? sceneObject(group, false) : sceneObject(readField(actorField), false);
			var index = actor == null ? -1 : members.indexOf(actor);
			if (index >= 0 && (first < 0 || index < first)) first = index;
		}
		return first;
	}
	public function remove(object:Dynamic, splice:Bool = false):Dynamic {
		var nativeObject = sceneObject(object, false);
		var result = callHost('remove', [nativeObject, splice]);
		return nativeObject == object ? result : object;
	}
	public function insert(position:Int, object:Dynamic):Dynamic {
		var nativeObject = sceneObject(object, true);
		var result = callHost('insert', [position, nativeObject]);
		return nativeObject == object ? result : object;
	}

	function sceneObject(value:Dynamic, adding:Bool):Dynamic {
		// The host stores actors directly, so this compatibility group is a
		// coordinate/member view rather than a native FlxBasic. Resolve it before
		// asking PlayState's FlxTypedGroup to add, remove, or insert the object.
		if (Std.isOfType(value, PsychBaseStageActorGroupCompat))
			return (cast value:PsychBaseStageActorGroupCompat).actor();
		return ownerClassScope == null ? unwrapSceneObject(value)
			: ownerClassScope.nativeFlixelSceneObject(value, adding);
	}

	public function addBehindGF(object:Dynamic):Dynamic return insert(groupMemberIndex('gf'), object);
	public function addBehindBF(object:Dynamic):Dynamic return insert(groupMemberIndex('bf'), object);
	public function addBehindDad(object:Dynamic):Dynamic return insert(groupMemberIndex('dad'), object);

	function groupMemberIndex(role:String):Int {
		var groupField = role == 'gf' ? 'gfGroup' : role == 'bf' ? 'boyfriendGroup' : 'dadGroup';
		var nativeGroup = readField(groupField);
		if (nativeGroup != null) return members.indexOf(sceneObject(nativeGroup, false));
		var actorField = role == 'gf' ? 'gf' : role == 'bf' ? 'boyfriend' : 'dad';
		var actor = sceneObject(readField(actorField), false);
		if (actor == null)
			throw '[psych-stage] cannot place an object behind ' + groupField + ': no native group or live actor is available';
		return members.indexOf(actor);
	}

	public function setDefaultGF(name:String):Void {
		if (callHost('setDefaultGF', [name]) != null) return;
		var song:Dynamic = readField('SONG');
		if (song == null) song = staticField('SONG');
		if (song == null) song = readField('songData');
		if (song == null || Reflect.field(song, 'gfVersion') != null) return;
		Reflect.setField(song, 'gfVersion', name);
	}

	public function getStageObject(name:String):Dynamic {
		var direct = callHost('getStageObject', [name]);
		if (direct != null) return direct;
		var variables:Dynamic = readField('variables');
		if (variables != null && Reflect.isFunction(Reflect.field(variables, 'get')))
			return Reflect.callMethod(variables, Reflect.field(variables, 'get'), [name]);
		return null;
	}

	public function setStartCallback(callback:Dynamic):Void callHost('setStartCallback', [callback]);
	public function setEndCallback(callback:Dynamic):Void callHost('setEndCallback', [callback]);
	public function startCountdown():Dynamic return callHost('startCountdown', []);
	public function endSong():Dynamic return callHost('endSong', []);
	public function moveCameraSection():Void callHost('moveCameraSection', []);
	public function moveCamera(isDad:Bool):Void callHost('moveCamera', [isDad]);

	/** HScript-ex classes compose their native superclass in `superClass`; they
	 * are not themselves FlxBasic instances. Unwrap only those script proxies at
	 * the native scene insertion boundary so Flixel groups receive the actual
	 * sprite/object while the stage retains its owner-scoped proxy reference. */
	static function unwrapSceneObject(value:Dynamic):Dynamic {
		var current = value;
		var seen:Array<Dynamic> = [];
		while (current != null && Std.isOfType(current, ScriptClass)) {
			if (seen.indexOf(current) >= 0)
				throw '[psych-stage] cyclic HScript scene-object superclass chain';
			seen.push(current);
			current = (cast current:ScriptClass).superClass;
		}
		if (value != null && Std.isOfType(value, ScriptClass) && !Std.isOfType(current, FlxBasic))
			throw '[psych-stage] HScript scene object does not wrap a native FlxBasic';
		return current;
	}

	function readField(name:String):Dynamic {
		if (stageHost == null) return null;
		try return Reflect.getProperty(stageHost, name) catch (_:Dynamic) return null;
	}

	function staticField(name:String):Dynamic {
		if (stageHost == null) return null;
		try {
			var owner = Type.getClass(stageHost);
			return owner == null ? null : Reflect.field(owner, name);
		} catch (_:Dynamic) {
			return null;
		}
	}

	function staticBoolField(name:String, fallback:Bool):Bool {
		var value = staticField(name);
		return Std.isOfType(value, Bool) ? cast value : fallback;
	}

	function writeField(name:String, value:Dynamic):Void {
		if (stageHost == null) return;
		try Reflect.setProperty(stageHost, name, value) catch (_:Dynamic) {}
	}

	function boolField(name:String, fallback:Bool):Bool {
		var value = readField(name);
		return Std.isOfType(value, Bool) ? cast value : fallback;
	}

	function writeBoolField(name:String, value:Bool):Bool {
		writeField(name, value);
		return value;
	}

	function intField(name:String, fallback:Int):Int {
		var value = readField(name);
		return Std.isOfType(value, Int) ? cast value : fallback;
	}

	function floatField(name:String, fallback:Float):Float {
		var value = readField(name);
		return Std.isOfType(value, Int) || Std.isOfType(value, Float) ? cast value : fallback;
	}

	function callHost(name:String, args:Array<Dynamic>):Dynamic {
		if (stageHost == null) return null;
		var callback:Dynamic = null;
		try callback = Reflect.field(stageHost, name) catch (_:Dynamic) return null;
		if (!Reflect.isFunction(callback)) return null;
		try return Reflect.callMethod(stageHost, callback, args) catch (error:Dynamic) {
			throw '[psych-stage] host ' + name + ' failed: ' + Std.string(error);
		}
	}
}
