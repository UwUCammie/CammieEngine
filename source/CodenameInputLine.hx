package;

import flixel.util.FlxSignal.FlxTypedSignal;

/** Input ownership for one authored Codename strumline. This is not a full
 * StrumLine: notes, strums, and input dispatch stay with PlayState.
 * Keep one instance per source index so scripts can mutate cpu/controls and
 * retain a stable line identity while its actor bindings change. */
@:keep
class CodenameInputLine<T> {
	/** Donor StrumLine.ID and the source chart index begin with the same value. */
	public var ID:Int;
	/** Authored identity stays fixed even when a script changes donor ID. */
	public var lineIndex(default, null):Int;
	public var lineType(default, null):Null<Int>;
	/** Indexed source slots are engine-owned. Keep their null entries so notes
	 * continue to target the authored occurrence rather than a compacted list. */
	public var actorSlots:Array<Null<T>> = [];
	/** Codename scripts receive only materialized characters. This stable array
	 * is compact even when the indexed source slots contain unresolved actors. */
	@:keep public var characters(get, set):Array<T>;
	var scriptCharacters:Array<T> = [];
	var scriptCharacterSlots:Array<Int> = [];
	var scriptCharacterSnapshot:Array<T> = [];
	/** Chart-authored line presentation fields. The original source values stay
	 * available to scripts; layout code interprets them only at the native edge. */
	@:keep public var keyCount:Int = 4;
	@:keep public var strumLinePos:Dynamic = 0.5;
	@:keep public var strumPos:Dynamic = [0, 50];
	@:keep public var strumScale:Dynamic = 1;
	@:keep public var strumSpacing:Dynamic = 1;
	/** Hidden source lines still own notes and callbacks. This setter only
	 * controls their receptor group; note lifecycle stays active in PlayState. */
	@:keep @:isVar public var visible(get, set):Bool;
	var sourceVisible:Bool = true;
	function get_visible():Bool return sourceVisible;
	function set_visible(value:Bool):Bool {
		sourceVisible = value;
		if (!released && setNativeVisibility != null) setNativeVisibility(value);
		return value;
	}
	/** Live native receptors for this authored line. The resolver returns the
	 * actual player/opponent group member array; lines with no native lane have
	 * no receptor view. */
	@:keep public var members(get, never):Dynamic;
	function get_members():Dynamic
		return released || resolveMembers == null ? null : resolveMembers(lineIndex);
	/** Live native notes for this authored line, including future chart notes. */
	@:keep public var notes(get, never):CodenameStrumlineNoteCollection;
	function get_notes():CodenameStrumlineNoteCollection {
		if (sourceNotes == null)
			sourceNotes = new CodenameStrumlineNoteCollection(lineIndex, resolveNotes, resolveSongPosition);
		return sourceNotes;
	}
	/** Codename StrumLine itself is iterable over its live receptors. */
	@:keep public function iterator():Iterator<Dynamic> {
		var receptors:Dynamic = members;
		return Std.isOfType(receptors, Array)
			? (cast receptors:Array<Dynamic>).iterator() : ([]:Array<Dynamic>).iterator();
	}
	/** Match FlxTypedGroup.forEachAlive for the live receptor members. */
	@:keep public function forEachAlive(func:Dynamic, ?recurse:Bool = false):Void {
		var receptors:Dynamic = members;
		if (func == null || !Std.isOfType(receptors, Array)) return;
		for (receptor in (cast receptors:Array<Dynamic>)) {
			if (!isAliveMember(receptor)) continue;
			if (recurse) forEachAliveSubgroup(receptor, func, recurse);
			Reflect.callMethod(null, func, [receptor]);
		}
	}

	static function isAliveMember(member:Dynamic):Bool
		return member != null && Reflect.field(member, 'exists') == true
			&& Reflect.field(member, 'alive') == true;

	/** Flixel groups use type 2; sprite groups use type 4 and recurse through
	 * their inner group. Those are FlxBasic.GROUP and SPRITEGROUP respectively. */
	static function forEachAliveSubgroup(member:Dynamic, func:Dynamic, recurse:Bool):Void {
		var kind:Dynamic = Reflect.field(member, 'flixelType');
		if (kind != 2 && kind != 4) return;
		var group:Dynamic = kind == 4 ? Reflect.field(member, 'group') : member;
		if (group == null) return;
		var visit:Dynamic = Reflect.field(group, 'forEachAlive');
		if (visit != null && Reflect.isFunction(visit))
			Reflect.callMethod(group, visit, [func, recurse]);
	}
	/** Same one-argument listener API used by donor StrumLine.onHit/onMiss. */
	public var onHit:FlxTypedSignal<Dynamic->Void> = new FlxTypedSignal<Dynamic->Void>();
	public var onMiss:FlxTypedSignal<Dynamic->Void> = new FlxTypedSignal<Dynamic->Void>();
	public var cpu:Bool;
	public var controls:Dynamic;
	/** Codename StrumLine animation state. The authored line suffix applies to
	 * note hits only when the note did not specify its own suffix. */
	public var animSuffix:String = '';
	public var defaultAnimSuffix:String = '-alt';
	public var altAnim(get, set):Bool;
	function get_altAnim():Bool return animSuffix == defaultAnimSuffix;
	function set_altAnim(enabled:Bool):Bool {
		animSuffix = enabled ? defaultAnimSuffix : '';
		return enabled;
	}
	public function noteAnimSuffix(authored:Null<String>):String
		return authored == null ? animSuffix : authored;
	/** Donor StrumLine.ghostTapping is an optional per-line override. */
	@:isVar public var ghostTapping(get, set):Null<Bool> = null;
	function get_ghostTapping():Null<Bool>
		return this.ghostTapping != null ? this.ghostTapping
			: (defaultGhostTapping == null ? false : defaultGhostTapping());
	function set_ghostTapping(value:Null<Bool>):Null<Bool>
		return this.ghostTapping = value;
	/** Local demo/botplay suppresses native keyShit; it does not change the
	 * donor's initial cpu value or a script's later cpu mutation. */
	public var botplay:Bool;
	public var released(default, null):Bool = false;
	var resolveCharacters:Int->Array<Null<T>>;
	var resolveMembers:Int->Dynamic;
	var resolveNotes:Int->Array<Dynamic>;
	var resolveSongPosition:Void->Float;
	var sourceNotes:CodenameStrumlineNoteCollection;
	var setNativeVisibility:Bool->Void;
	var defaultGhostTapping:Void->Bool;

	function get_characters():Array<T> {
		// HScript can mutate this live Array without going through the setter.
		// Keep the public view dense even before the next actor-slot commit.
		var index = 0;
		while (index < scriptCharacters.length) {
			if (scriptCharacters[index] == null) scriptCharacters.splice(index, 1);
			else index++;
		}
		return scriptCharacters;
	}

	function set_characters(value:Array<T>):Array<T> {
		if (value == null) value = [];
		if (value != scriptCharacters) {
			scriptCharacters.resize(0);
			for (actor in value) if (actor != null) scriptCharacters.push(actor);
		}
		return scriptCharacters;
	}

	public function new(lineIndex:Int, lineType:Null<Int>, opponentMode:Bool,
		coopMode:Bool, botplay:Bool, soloControls:Dynamic,
		controlsP1:Dynamic, controlsP2:Dynamic,
		resolveCharacters:Int->Array<Null<T>>, ?defaultGhostTapping:Void->Bool,
		?resolveMembers:Int->Dynamic, ?sourceVisible:Bool = true,
		?sourceKeyCount:Int = 4, ?sourceStrumLinePos:Dynamic,
		?sourceStrumPos:Dynamic, ?sourceStrumScale:Dynamic,
		?sourceStrumSpacing:Dynamic, ?setNativeVisibility:Bool->Void,
		?sourceOnMiss:FlxTypedSignal<Dynamic->Void>,
		?resolveNotes:Int->Array<Dynamic>, ?resolveSongPosition:Void->Float) {
		if (lineIndex < 0 || (lineType != null && lineType < 0) || sourceKeyCount < 1
			|| resolveCharacters == null)
			throw 'Invalid Codename input line';
		this.ID = lineIndex;
		this.lineIndex = lineIndex;
		this.lineType = lineType;
		this.cpu = initialCpu(lineType, opponentMode, coopMode);
		this.botplay = botplay;
		this.resolveCharacters = resolveCharacters;
		this.resolveMembers = resolveMembers;
		this.resolveNotes = resolveNotes;
		this.resolveSongPosition = resolveSongPosition;
		this.keyCount = sourceKeyCount;
		this.strumLinePos = sourceStrumLinePos == null
			? CodenameStrumlineLayout.defaultLinePosition(lineType)
			: sourceStrumLinePos;
		this.strumPos = sourceStrumPos == null ? [0, 50] : copyStrumPos(sourceStrumPos);
		this.strumScale = sourceStrumScale == null ? 1 : sourceStrumScale;
		this.strumSpacing = sourceStrumSpacing == null ? 1 : sourceStrumSpacing;
		this.setNativeVisibility = setNativeVisibility;
		if (sourceOnMiss != null) this.onMiss = sourceOnMiss;
		this.visible = sourceVisible;
		this.defaultGhostTapping = defaultGhostTapping;
		this.controls = switch (initialControlsBank(lineType, opponentMode, coopMode)) {
			case 'p1': controlsP1;
			case 'p2': controlsP2;
			default: soloControls;
		};
		refreshActors();
	}

	static function copyStrumPos(value:Dynamic):Dynamic {
		if (Std.isOfType(value, Array)) return (cast value:Array<Dynamic>).copy();
		return value;
	}

	/** Exact v1.0.1 PlayState constructor expression, including null types. */
	public static function initialCpu(lineType:Null<Int>, opponentMode:Bool,
		coopMode:Bool):Bool {
		return lineType == 2 || (!coopMode
			&& !((lineType == 1 && !opponentMode) || (lineType == 0 && opponentMode)));
	}

	/** Name the donor constructor's control-bank choice without freezing the
	 * chosen controls object; scripts may later replace `controls` directly. */
	public static function initialControlsBank(lineType:Null<Int>, opponentMode:Bool,
		coopMode:Bool):String {
		if (!coopMode) return 'solo';
		return ((lineType == 1) != opponentMode) ? 'p1' : 'p2';
	}

	public function canProcessInput():Bool
		return !released && !cpu && !botplay;

	/** Refresh the line's actor slots after a materialization or primary swap.
	 * This replaces the view array, never the stable line object. */
	public function refreshActors():Array<Null<T>> {
		if (released) return actorSlots;
		var current = resolveCharacters(lineIndex);
		actorSlots = current == null ? [] : current.copy();
		refreshScriptCharacters();
		return actorSlots;
	}

	/** Fold direct HScript Array edits back into their original source slots.
	 * Replacements at the same position retain that occurrence; removed or moved
	 * actors follow their prior source occurrence by identity when possible. */
	public function commitScriptCharacters():Bool {
		if (released) return false;
		var changed = scriptCharacters.length != scriptCharacterSnapshot.length;
		if (!changed) for (index in 0...scriptCharacters.length)
			if (scriptCharacters[index] != scriptCharacterSnapshot[index]) {
				changed = true;
				break;
			}
		if (!changed) return false;

		var nextSlots:Array<Int> = [];
		var used:Map<Int, Bool> = new Map();
		var matchedSnapshot:Array<Bool> = [];
		for (_ in scriptCharacterSnapshot) matchedSnapshot.push(false);
		for (index in 0...scriptCharacters.length) {
			var actor = scriptCharacters[index];
			var slot = -1;
			// Keep an unchanged actor attached to its authored occurrence even if
			// an earlier live actor was removed from the script-facing array.
			for (oldIndex in 0...scriptCharacterSnapshot.length)
				if (!matchedSnapshot[oldIndex] && scriptCharacterSnapshot[oldIndex] == actor) {
					var oldSlot = scriptCharacterSlots[oldIndex];
					if (!used.exists(oldSlot)) {
						slot = oldSlot;
						matchedSnapshot[oldIndex] = true;
						break;
					}
				}
			if (slot < 0 && index < scriptCharacterSlots.length
				&& !used.exists(scriptCharacterSlots[index]))
				slot = scriptCharacterSlots[index];
			if (slot < 0) {
				slot = actorSlots.length;
				actorSlots.push(null);
			}
			while (actorSlots.length <= slot) actorSlots.push(null);
			actorSlots[slot] = actor;
			used.set(slot, true);
			nextSlots.push(slot);
		}
		for (oldSlot in scriptCharacterSlots)
			if (!used.exists(oldSlot) && oldSlot < actorSlots.length) actorSlots[oldSlot] = null;
		scriptCharacterSlots = nextSlots;
		refreshScriptCharacters();
		return true;
	}

	/** Preserve both engine slots and the stable script array across a native
	 * primary swap, then reset the edit snapshot to the new actor reference. */
	public function rebindActor(previous:T, replacement:T):Void {
		if (released || previous == null || replacement == null) return;
		for (index in 0...actorSlots.length)
			if (actorSlots[index] == previous) actorSlots[index] = replacement;
		for (index in 0...scriptCharacters.length)
			if (scriptCharacters[index] == previous) scriptCharacters[index] = replacement;
		scriptCharacterSnapshot = scriptCharacters.copy();
	}

	function refreshScriptCharacters():Void {
		scriptCharacters.resize(0);
		scriptCharacterSlots.resize(0);
		for (index in 0...actorSlots.length) {
			var actor = actorSlots[index];
			if (actor == null) continue;
			scriptCharacters.push(actor);
			scriptCharacterSlots.push(index);
		}
		scriptCharacterSnapshot = scriptCharacters.copy();
	}

	public function release():Void {
		if (released) return;
		released = true;
		actorSlots = [];
		characters = [];
		onHit.removeAll();
		onMiss.removeAll();
		controls = null;
		resolveCharacters = null;
		resolveMembers = null;
		resolveNotes = null;
		resolveSongPosition = null;
		if (sourceNotes != null) sourceNotes.release();
		sourceNotes = null;
		setNativeVisibility = null;
		defaultGhostTapping = null;
	}
}
