package;

/** Coordinate and member view for a Psych character FlxSpriteGroup when the
 * host engine stores the actor directly instead of in a Psych group. The
 * anchor comes from StageHelper's role placement, not the character's offset
 * sprite coordinates. Moving the view moves both the placement anchor and its
 * live actor by the same delta, matching a translated parent group.
 */
class PsychBaseStageActorGroupCompat {
	final stageHost:Dynamic;
	final role:String;

	public function new(stageHost:Dynamic, role:String) {
		this.stageHost = stageHost;
		this.role = role;
	}

	public var x(get, set):Float;
	function get_x():Float return coordinate('x');
	function set_x(value:Float):Float return setCoordinate('x', value);

	public var y(get, set):Float;
	function get_y():Float return coordinate('y');
	function set_y(value:Float):Float return setCoordinate('y', value);

	/** Psych stage classes commonly iterate this group to access its character.
	 * The host has one live actor per role; returning it here preserves that read
	 * contract while keeping the native state as the owner of the actor.
	 */
	public var members(get, never):Array<Dynamic>;
	function get_members():Array<Dynamic> {
		var value = actor();
		return value == null ? [] : [value];
	}

	public function iterator():Iterator<Dynamic> return members.iterator();

	public function actor():Dynamic {
		if (stageHost == null) return null;
		return Reflect.field(stageHost, actorField());
	}

	function coordinate(axis:String):Float {
		var value = Reflect.getProperty(positionInfo(), axis);
		if (!Std.isOfType(value, Int) && !Std.isOfType(value, Float))
			throw '[psych-stage] ' + groupName() + '.' + axis + ' has no numeric stage placement anchor';
		return cast value;
	}

	function setCoordinate(axis:String, value:Float):Float {
		if (!Math.isFinite(value))
			throw '[psych-stage] ' + groupName() + '.' + axis + ' must be finite';
		var info = positionInfo();
		var current = Reflect.getProperty(info, axis);
		if (!Std.isOfType(current, Int) && !Std.isOfType(current, Float))
			throw '[psych-stage] ' + groupName() + '.' + axis + ' has no numeric stage placement anchor';
		var delta = value - (cast current:Float);
		var liveActor = actor();
		var actorCurrent:Dynamic = null;
		if (liveActor != null) {
			actorCurrent = Reflect.getProperty(liveActor, axis);
			if (!Std.isOfType(actorCurrent, Int) && !Std.isOfType(actorCurrent, Float))
				throw '[psych-stage] cannot translate ' + groupName() + ': live actor has no numeric ' + axis;
		}

		// Psych character sprites are children of their start-position groups.
		// Keep their local/imported character offsets by applying only the group
		// movement delta to the direct host actor.
		if (liveActor != null)
			Reflect.setProperty(liveActor, axis, (cast actorCurrent:Float) + delta);
		Reflect.setProperty(info, axis, value);
		// Character swaps use a separate host placement array. Keep that source
		// anchor in step when a compiled Psych stage moves a character group.
		var sync = Reflect.field(stageHost, 'syncPsychStageGroupAnchor');
		if (Reflect.isFunction(sync))
			Reflect.callMethod(stageHost, sync, [role, axis, value]);
		return value;
	}

	function positionInfo():Dynamic {
		if (stageHost == null)
			throw '[psych-stage] ' + groupName() + ' cannot resolve its host stage placement';
		var stage = Reflect.field(stageHost, 'curStage');
		var info:Dynamic = null;
		if (stage != null) {
			info = Reflect.field(stage, infoField());
			if (info == null) {
				var getInfo = Reflect.field(stage, 'getInfo');
				if (Reflect.isFunction(getInfo))
					info = Reflect.callMethod(stage, getInfo, [role]);
			}
		}
		if (info == null)
			throw '[psych-stage] ' + groupName() + ' cannot resolve curStage.' + infoField();
		return info;
	}

	function actorField():String return role == 'bf' ? 'boyfriend' : role == 'dad' ? 'dad' : 'gf';
	function infoField():String return role == 'bf' ? 'bfInfo' : role == 'dad' ? 'dadInfo' : 'gfInfo';
	function groupName():String return role == 'bf' ? 'boyfriendGroup' : role == 'dad' ? 'dadGroup' : 'gfGroup';
}
