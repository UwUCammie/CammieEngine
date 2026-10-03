package;

import flixel.math.FlxPoint.FlxCallbackPoint;
import flixel.math.FlxPoint;

/** Psych FlxSpriteGroup view for a host that stores actors directly in state. */
class PsychBaseStageActorGroupCompat {
	final stageHost:Dynamic;
	final role:String;
	final groupMembers:Array<Dynamic> = [];
	final removedMembers:Array<Dynamic> = [];
	final scrollFactorValue:FlxCallbackPoint;
	var groupVisible:Bool = true;
	var groupCameras:Array<Dynamic>;
	var hasGroupCameras:Bool = false;
	var hasGroupScrollFactor:Bool = false;
	var groupZIndex:Int = 0;
	var hasGroupZIndex:Bool = false;
	var initializingScrollFactor:Bool = true;
	var sceneObjectResolver:Dynamic->Bool->Dynamic;
	var sceneAdd:Dynamic->Dynamic;
	var sceneInsert:Int->Dynamic->Dynamic;
	var sceneRemove:Dynamic->Bool->Dynamic;

	public function new(stageHost:Dynamic, role:String) {
		this.stageHost = stageHost;
		this.role = role;
		var current = actor();
		if (current != null) {
			groupMembers.push(current);
			var cameras:Dynamic = Reflect.getProperty(current, 'cameras');
			if (cameras != null) {
				groupCameras = cast cameras;
				hasGroupCameras = true;
			}
		}
		scrollFactorValue = new FlxCallbackPoint(function(point:FlxPoint):Void {
			if (initializingScrollFactor) {
				for (member in groupMembers) copyPoint(member, 'scrollFactor', point);
			} else {
				hasGroupScrollFactor = true;
				// A real group-wide mutation reaches cached members too. Materialize
				// them here so their per-character authored factors can be overridden
				// only by an explicit group write.
				for (member in members) copyPoint(member, 'scrollFactor', point);
			}
		});
		var scroll:Dynamic = current == null ? null : Reflect.getProperty(current, 'scrollFactor');
		scrollFactorValue.set(pointAxis(scroll, 'x', 1), pointAxis(scroll, 'y', 1));
		initializingScrollFactor = false;
	}

	/** Bind owner-scope script-object unwrapping and direct PlayState membership. */
	public function attachSceneBridge(resolve:Dynamic->Bool->Dynamic,
		add:Dynamic->Dynamic, insert:Int->Dynamic->Dynamic,
		remove:Dynamic->Bool->Dynamic):Void {
		if (sceneObjectResolver != null && sceneObjectResolver != resolve)
			throw '[psych-stage] ' + groupName() + ' scene bridge cannot change owners';
		sceneObjectResolver = resolve;
		sceneAdd = add;
		sceneInsert = insert;
		sceneRemove = remove;
	}

	public var x(get, set):Float;
	function get_x():Float return coordinate('x');
	function set_x(value:Float):Float return setCoordinate('x', value);

	public var y(get, set):Float;
	function get_y():Float return coordinate('y');
	function set_y(value:Float):Float return setCoordinate('y', value);

	public var members(get, never):Array<Dynamic>;
	function get_members():Array<Dynamic> {
		var current = actor();
		if (current != null) addLocalMember(current);
		for (member in additionalMembers()) addLocalMember(member);
		return groupMembers;
	}
	public var length(get, never):Int;
	function get_length():Int return members.length;
	public function iterator():Iterator<Dynamic> return members.iterator();

	/** Existing and future members receive the same camera assignment. */
	public var cameras(get, set):Array<Dynamic>;
	function get_cameras():Array<Dynamic> {
		if (hasGroupCameras) return groupCameras;
		var current = actor();
		return current == null ? null : Reflect.getProperty(current, 'cameras');
	}
	function set_cameras(value:Array<Dynamic>):Array<Dynamic> {
		groupCameras = value;
		hasGroupCameras = true;
		var sync = Reflect.field(stageHost, 'setPsychStageGroupCameras');
		if (Reflect.isFunction(sync)) Reflect.callMethod(stageHost, sync, [role, value]);
		for (member in members) setProperty(member, 'cameras', value);
		return value;
	}
	public var camera(get, set):Dynamic;
	function get_camera():Dynamic {
		var value = cameras;
		return value == null || value.length == 0 ? null : value[0];
	}
	function set_camera(value:Dynamic):Dynamic {
		cameras = value == null ? null : [value];
		return value;
	}

	public var visible(get, set):Bool;
	function get_visible():Bool return groupVisible;
	function set_visible(value:Bool):Bool {
		if (groupVisible != value)
			for (member in members) setProperty(member, 'visible', value);
		groupVisible = value;
		return value;
	}

	/** Supports Psych's `.scrollFactor.set(x, y)` group write. */
	public var scrollFactor(get, set):FlxCallbackPoint;
	function get_scrollFactor():FlxCallbackPoint return scrollFactorValue;
	function set_scrollFactor(value:FlxCallbackPoint):FlxCallbackPoint {
		if (value != null) scrollFactorValue.set(value.x, value.y);
		return scrollFactorValue;
	}

	/** Shared Psych/NMV parent layering for a flattened actor group. */
	public var zIndex(get, set):Int;
	function get_zIndex():Int return hasGroupZIndex ? groupZIndex : Std.int(HxcCompatRuntime.getZIndex(actor()));
	function set_zIndex(value:Int):Int {
		groupZIndex = value;
		hasGroupZIndex = true;
		for (member in members) HxcCompatRuntime.setZIndex(member, value);
		return value;
	}

	public function add(sprite:Dynamic):Dynamic return insert(members.length, sprite);

	public function insert(position:Int, sprite:Dynamic):Dynamic {
		if (sprite == null) return null;
		var nativeSprite = sceneObject(sprite, true);
		if (nativeSprite == null) return null;
		prepareChild(nativeSprite);
		var localPosition = Std.int(Math.max(0, Math.min(members.length, position)));
		var hostPosition = hostInsertionIndex(localPosition);
		if (hostMemberIndex(nativeSprite) < 0) {
			if (sceneInsert != null) sceneInsert(hostPosition, nativeSprite);
			else if (hostPosition >= hostMemberCount()) {
				if (sceneAdd != null) sceneAdd(nativeSprite); else callHost('add', [nativeSprite]);
			} else callHost('insert', [hostPosition, nativeSprite]);
		}
		removedMembers.remove(sprite);
		groupMembers.insert(localPosition, sprite);
		return sprite;
	}

	/** State/cache code owns destruction; removing from the facade only removes
	 * the flattened state membership, like removing a child from FlxSpriteGroup. */
	public function remove(sprite:Dynamic, splice:Bool = false):Dynamic {
		if (sprite == null) return null;
		var localPosition = groupMembers.indexOf(sprite);
		var nativeSprite = sceneObject(sprite, false);
		if (localPosition < 0 && nativeSprite != null)
			for (i in 0...groupMembers.length)
				if (sceneObject(groupMembers[i], false) == nativeSprite) { localPosition = i; break; }
		if (nativeSprite == null) return sprite;
		setProperty(nativeSprite, 'x', numberProperty(nativeSprite, 'x', 0) - x);
		setProperty(nativeSprite, 'y', numberProperty(nativeSprite, 'y', 0) - y);
		setProperty(nativeSprite, 'cameras', null);
		if (localPosition >= 0) {
			if (splice) groupMembers.splice(localPosition, 1); else groupMembers[localPosition] = null;
		}
		if (!removedMembers.contains(sprite)) removedMembers.push(sprite);
		if (sceneRemove != null) sceneRemove(nativeSprite, splice);
		else callHost('remove', [nativeSprite, splice]);
		return sprite;
	}

	public function clear():Void {
		for (member in members.copy()) if (member != null) remove(member, true);
		groupMembers.resize(0);
	}

	/** An engine-specific subclass can provide cached CharacterGroup members. */
	public function additionalMembers():Array<Dynamic> return [];

	public function actor():Dynamic {
		if (stageHost == null) return null;
		return Reflect.field(stageHost, actorField());
	}

	function addLocalMember(member:Dynamic):Void {
		if (member != null && !removedMembers.contains(member) && groupMembers.indexOf(member) < 0) {
			groupMembers.push(member);
			if (hasGroupCameras) setProperty(member, 'cameras', groupCameras);
			if (hasGroupZIndex) HxcCompatRuntime.setZIndex(member, groupZIndex);
			if (!groupVisible) setProperty(member, 'visible', false);
			if (hasGroupScrollFactor) copyPoint(member, 'scrollFactor', scrollFactorValue);
		}
	}

	function prepareChild(sprite:Dynamic):Void {
		setProperty(sprite, 'x', numberProperty(sprite, 'x', 0) + x);
		setProperty(sprite, 'y', numberProperty(sprite, 'y', 0) + y);
		if (!groupVisible) setProperty(sprite, 'visible', false);
		copyPoint(sprite, 'scrollFactor', scrollFactorValue);
		setProperty(sprite, 'cameras', cameras);
	}

	function hostInsertionIndex(groupIndex:Int):Int {
		var list = members;
		if (groupIndex < list.length) {
			var before = hostMemberIndex(sceneObject(list[groupIndex], false));
			if (before >= 0) return before;
		}
		var previous = groupIndex > 0 && groupIndex <= list.length
			? sceneObject(list[groupIndex - 1], false) : actor();
		var previousIndex = hostMemberIndex(previous);
		return previousIndex < 0 ? hostMemberCount() : previousIndex + 1;
	}

	function hostMemberIndex(value:Dynamic):Int {
		var list:Dynamic = stageHost == null ? null : Reflect.getProperty(stageHost, 'members');
		return Std.isOfType(list, Array) ? (cast list:Array<Dynamic>).indexOf(value) : -1;
	}
	function hostMemberCount():Int {
		var list:Dynamic = stageHost == null ? null : Reflect.getProperty(stageHost, 'members');
		return Std.isOfType(list, Array) ? (cast list:Array<Dynamic>).length : 0;
	}

	function sceneObject(value:Dynamic, adding:Bool):Dynamic {
		if (sceneObjectResolver != null) return sceneObjectResolver(value, adding);
		return value;
	}

	function callHost(name:String, args:Array<Dynamic>):Dynamic {
		var callback:Dynamic = stageHost == null ? null : Reflect.field(stageHost, name);
		return Reflect.isFunction(callback) ? Reflect.callMethod(stageHost, callback, args) : null;
	}

	function copyPoint(object:Dynamic, field:String, value:FlxPoint):Void {
		if (object == null || value == null) return;
		var point:Dynamic = Reflect.getProperty(object, field);
		if (point == null) return;
		var copy = Reflect.field(point, 'copyFrom');
		if (Reflect.isFunction(copy)) Reflect.callMethod(point, copy, [value]);
		else {
			var set = Reflect.field(point, 'set');
			if (Reflect.isFunction(set)) Reflect.callMethod(point, set, [value.x, value.y]);
		}
	}

	function coordinate(axis:String):Float {
		var value = Reflect.getProperty(positionInfo(), axis);
		if (!Std.isOfType(value, Int) && !Std.isOfType(value, Float))
			throw '[psych-stage] ' + groupName() + '.' + axis + ' has no numeric stage placement anchor';
		return cast value;
	}

	function setCoordinate(axis:String, value:Float):Float {
		if (!Math.isFinite(value)) throw '[psych-stage] ' + groupName() + '.' + axis + ' must be finite';
		var info = positionInfo();
		var current = Reflect.getProperty(info, axis);
		if (!Std.isOfType(current, Int) && !Std.isOfType(current, Float))
			throw '[psych-stage] ' + groupName() + '.' + axis + ' has no numeric stage placement anchor';
		var delta = value - (cast current:Float);
		var liveActor = actor();
		if (liveActor != null) setProperty(liveActor, axis, numberProperty(liveActor, axis, 0) + delta);
		for (member in members) if (member != null && member != liveActor)
			setProperty(member, axis, numberProperty(member, axis, 0) + delta);
		Reflect.setProperty(info, axis, value);
		var sync = Reflect.field(stageHost, 'syncPsychStageGroupAnchor');
		if (Reflect.isFunction(sync)) Reflect.callMethod(stageHost, sync, [role, axis, value]);
		return value;
	}

	function positionInfo():Dynamic {
		if (stageHost == null) throw '[psych-stage] ' + groupName() + ' cannot resolve its host stage placement';
		var stage = Reflect.field(stageHost, 'curStage');
		var info:Dynamic = null;
		if (stage != null) {
			info = Reflect.field(stage, infoField());
			if (info == null) {
				var getInfo = Reflect.field(stage, 'getInfo');
				if (Reflect.isFunction(getInfo)) info = Reflect.callMethod(stage, getInfo, [role]);
			}
		}
		if (info == null) throw '[psych-stage] ' + groupName() + ' cannot resolve curStage.' + infoField();
		return info;
	}

	static function setProperty(object:Dynamic, field:String, value:Dynamic):Void {
		if (object != null) Reflect.setProperty(object, field, value);
	}
	static function numberProperty(object:Dynamic, field:String, fallback:Float):Float {
		var value = object == null ? null : Reflect.getProperty(object, field);
		return Std.isOfType(value, Int) || Std.isOfType(value, Float) ? cast value : fallback;
	}
	static function pointAxis(point:Dynamic, axis:String, fallback:Float):Float return numberProperty(point, axis, fallback);

	function actorField():String return role == 'bf' ? 'boyfriend' : role == 'dad' ? 'dad' : 'gf';
	function infoField():String return role == 'bf' ? 'bfInfo' : role == 'dad' ? 'dadInfo' : 'gfInfo';
	function groupName():String return role == 'bf' ? 'boyfriendGroup' : role == 'dad' ? 'dadGroup' : 'gfGroup';
}
