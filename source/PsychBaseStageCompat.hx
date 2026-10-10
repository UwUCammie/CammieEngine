package;

import flixel.FlxBasic;
import hscript.ScriptClass;
import hscript.ScriptClassScope;

/** Minimal owner-side host contract for Psych's compiled BaseStage callbacks.
	The donor BaseStage source depends on native Character, Note, FlxBasic and
	PlayState types. HScript stage classes instead inherit this adapter; live
	state fields and scene operations are delegated through the selected owner
	context supplied by PsychCompiledStageRuntime; assets retain their owner scope.
*/
@:keep
class PsychBaseStageCompat extends FlxBasic {
	var stageHost:Dynamic;
	var ownerClassScope:ScriptClassScope;
	var context:SourceStageContext;
	final actorGroups:haxe.ds.ObjectMap<Dynamic, Map<String, PsychBaseStageActorGroupCompat>> = new haxe.ds.ObjectMap();
	var creatingBackground:Bool = true;
	var placement:PsychStagePlacement;

	public function new(?stageHost:Dynamic, ?context:SourceStageContext, register:Bool = false) {
		this.stageHost = stageHost;
		this.context = context;
		// Direct source construction uses ordinary scene insertion. Only the
		// selected compiled stage needs the host actor-order adaptation.
		if (register) creatingBackground = false;
		if (register && PsychStageConstruction.register(game, this) == null) {
			flixel.FlxG.log.error('Invalid state for the stage added!');
			destroy();
			return;
		}
		super();
		if (register) create();
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

	public function attachContext(value:SourceStageContext):Void context = value;

	public function attachPlacement(value:PsychStagePlacement):Void {
		if (placement != null && placement != value)
			throw '[psych-stage] Placement phase cannot change owners';
		placement = value;
	}

	public var game(get, never):Dynamic;
	function get_game():Dynamic return context == null ? stageHost : context.state();

	@:keep public var controls(get, never):Dynamic;
	function get_controls():Dynamic {
		var sourceControls = readField('psychControls');
		return sourceControls == null ? readField('controls') : sourceControls;
	}

	public var onPlayState(get, never):Bool;
	function get_onPlayState():Bool return context == null ? boolField('onPlayState', stageHost != null) : context.isPlay(context.state());

	public var paused(get, never):Bool;
	function get_paused():Bool return boolField('paused', false);

	public var songName(get, never):String;
	function get_songName():String {
		// Psych sets songName from the chart's SONG.song. This fork also has a
		// HUD FlxText named songName, which must never become the source stage id.
		var sourceName = readField('songName');
		if (Std.isOfType(sourceName, String)) return cast sourceName;
		var song = staticField('SONG');
		if (song == null) song = readField('SONG');
		var value = song == null ? null : Reflect.field(song, 'song');
		if (value == null) value = readField('curSong');
		return value == null ? '' : PsychSongNameCompat.format(Std.string(value));
	}

	public var isStoryMode(get, never):Bool;
	function get_isStoryMode():Bool return staticBoolField('isStoryMode', false);

	public var seenCutscene(get, never):Bool;
	function get_seenCutscene():Bool return staticBoolField(context == null ? 'watchedCutscene' : 'seenCutscene', false);

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
	function get_boyfriendGroup():Dynamic return actorGroup('bf', 'boyfriendGroup');

	public var dadGroup(get, never):Dynamic;
	function get_dadGroup():Dynamic return actorGroup('dad', 'dadGroup');

	public var gfGroup(get, never):Dynamic;
	function get_gfGroup():Dynamic return actorGroup('gf', 'gfGroup');

	function actorGroup(role:String, field:String):Dynamic {
		var host = game;
		var nativeGroup = readField(field);
		if (nativeGroup != null || host == null) return nativeGroup;
		var groups = actorGroups.get(host);
		if (groups == null) {groups = new Map();actorGroups.set(host, groups);}
		if (!groups.exists(role)) groups.set(role, new PsychBaseStageActorGroupCompat(host, role));
		return groups.get(role);
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
		return get_defaultCamZoom();
	}

	public var camFollow(get, never):Dynamic;
	function get_camFollow():Dynamic return readField('camFollow');

	public var curBeat:Int = 0;
	public var curDecBeat:Float = 0;
	public var curStep:Int = 0;
	public var curDecStep:Float = 0;
	public var curSection:Int = 0;

	public function create():Void {}
	public function createPost():Void {}
	override public function update(_elapsed:Float):Void {}
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
	override public function destroy():Void super.destroy();

	public function add(object:Dynamic):Dynamic {
		var nativeObject = sceneObject(object, true);
		// Psych constructs the stage before adding its character groups. This
		// engine constructs actors first, so preserve Psych's draw order by
		// inserting create() props ahead of the earliest actor. createPost() and
		// later callbacks append as authored; addBehind* uses explicit insert().
		var beforeActors = placement == null ? creatingBackground : placement.beforeActors(game);
		var actorIndex = beforeActors ? firstActorMemberIndex() : -1;
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
		var song:Dynamic = staticField('SONG');
		if (song == null && context == null) song = readField('SONG');
		if (song == null && context == null) song = readField('songData');
		if (song == null) return;
		var current:Dynamic = Reflect.field(song, 'gfVersion');
		if (current == null || current.length < 1) Reflect.setField(song, 'gfVersion', name);
	}

	public function getStageObject(name:String):Dynamic {
		var variables:Dynamic = readField('variables');
		return SourceScriptReflection.read(variables, name, true, function(registry, key) {
			var get = Reflect.field(registry, 'get');
			return Reflect.isFunction(get) ? Reflect.callMethod(registry, get, [key]) : null;
		});
	}

	public function setStartCallback(callback:Dynamic):Void {if (onPlayState) callPlay('setStartCallback', [callback]);}
	public function setEndCallback(callback:Dynamic):Void {if (onPlayState) callPlay('setEndCallback', [callback]);}
	public function startCountdown():Dynamic return onPlayState ? callPlay('startCountdown', []) : false;
	public function endSong():Dynamic return onPlayState ? callPlay('endSong', []) : false;
	public function moveCameraSection():Void {if (onPlayState) callPlay('moveCameraSection', []);}
	public function moveCamera(isDad:Bool):Void {if (onPlayState) callPlay('moveCamera', [isDad]);}

	function callPlay(name:String, args:Array<Dynamic>):Dynamic {
		return callTarget(context == null ? game : context.play(), name, args);
	}

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
		var host = game;
		if (host == null) return null;
		try return Reflect.getProperty(host, name) catch (_:Dynamic) return null;
	}

	function staticField(name:String):Dynamic {
		if (context != null) return context.staticValue(name);
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
		var host = game;
		if (host == null) return;
		try Reflect.setProperty(host, name, value) catch (_:Dynamic) {}
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

	function callHost(name:String, args:Array<Dynamic>):Dynamic return callTarget(game, name, args);

	function callTarget(host:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		if (host == null) return null;
		var callback:Dynamic = null;
		try callback = Reflect.field(host, name) catch (_:Dynamic) return null;
		if (!Reflect.isFunction(callback)) return null;
		try return Reflect.callMethod(host, callback, args) catch (error:Dynamic) {
			throw '[psych-stage] host ' + name + ' failed: ' + Std.string(error);
		}
	}
}
