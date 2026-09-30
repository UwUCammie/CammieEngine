import hscript.Interp;
import flixel.FlxSprite;
import flixel.group.FlxGroup;
import flixel.group.FlxSpriteGroup;
import flixel.util.FlxSort;
import flixel.math.FlxPoint;
import haxe.Json;
import CodenameStagePlacement.CodenameStagePlacementData;

typedef CharacterInfo = {
	var x:Float;
	var y:Float;
	var camOffsetX:Int;
	var camOffsetY:Int;
	var scrollFactor:FlxPoint;
	var zIndex:Int;
	@:optional var camOffsetsAbsolute:Bool;
}

typedef VSliceStageCharacterPresentation = {
	var feetX:Float;
	var feetY:Float;
	var scaleX:Float;
	var scaleY:Float;
	var scrollX:Float;
	var scrollY:Float;
	var alpha:Float;
	var angle:Float;
	var cameraX:Int;
	var cameraY:Int;
}

class StageHelper extends FlxSpriteGroup {
	public var interp:Interp;
	public var name:String = 'stage';
	/** V-Slice Stage.id is the authored registry identity used by stage-change
	 * modules when deciding whether the chart's opening stage needs restoring. */
	public var id(get, never):String;
	function get_id():String return authoredName;
	/** Authored chart id retained when the native group uses a safe fallback. */
	public var authoredName:String = 'stage';
	/** Shared diagnostic emitted when the authored stage payload is absent. */
	public var fallbackDiagnostic:String = '';
	public var defaultZoom:Float = 1.05;
	/** NMV retains the complete authored StageFile for live script reads. */
	@:keep public var stageData:Dynamic;
	/** FPS Plus/BaseStage compatibility flag retained by imported stage scopes. */
	public var useStartPoints:Bool = false;

	public var bfInfo:CharacterInfo;
	public var dadInfo:CharacterInfo;
	public var gfInfo:CharacterInfo;

	public var elements:Map<String, Dynamic> = [];
	public var zIndexes:Map<FlxSprite, Int> = [];
	var vSliceCharacterPresentation:Map<String, VSliceStageCharacterPresentation> = [];
	var presentedCharacters:Map<Character, String> = [];
	/** Role actors hidden by the stage's authored entrance staging (reversible). */
	public var stagedOutActors:Map<String, Bool> = [];
	var highestZ:Int = 0;
	var extraCharacterIndex:Int = 0;
	public var functions:Map<String, Dynamic> = [];
	/** XML-order objects belong to the stage; actor bindings never do. */
	@:keep public var codenameOrderNodes:Array<{kind:String, ordinal:Int, key:String, sprite:FlxSprite}> = [];
	var codenameAnchors:Map<String, FlxSprite> = [];
	var codenameActorBindings:Array<{actor:FlxSprite, key:String}> = [];
	var codenamePlacement:Null<CodenameStagePlacementData> = null;
	/** Codename's Stage.characterPoses map is read by shared event and shader
	 * scripts. Publish the validated XML slot camera offsets under their source
	 * names so those scripts keep their authored character bindings. */
	@:keep public var characterPoses(default, null):Map<String, Dynamic> = [];

	/** Generated Codename stages publish their own XML placement before adding
	 * props or anchors. Legacy scripts leave this null for safe native fallback.
	 * Validate before replacing the current model so a bad stage script cannot
	 * leave partially installed placement behind. */
	@:keep public function setCodenamePlacement(data:Dynamic):Void {
		var value:Dynamic = Std.isOfType(data, String) ? Json.parse(cast data) : data;
		codenamePlacement = CodenameStagePlacement.fromData(value);
		characterPoses.clear();
		for (name in codenamePlacement.slots.keys()) {
			var slot = codenamePlacement.slots.get(name);
			characterPoses.set(name, {camxoffset:slot.cameraX, camyoffset:slot.cameraY});
		}
	}

	public function getCodenamePlacement():Null<CodenameStagePlacementData> {
		return codenamePlacement;
	}

	public function new(stageName:String = 'stage', ?stageInterp:Interp) {
		super();

		dadInfo = defaultInfo('dad');
		gfInfo = defaultInfo('gf');
		bfInfo = defaultInfo('bf');

		name = stageName == null || StringTools.trim(stageName) == '' ? 'stage' : stageName;
		authoredName = stageName == null ? name : stageName;
		if (stageInterp != null) interp = stageInterp;
	}

	/**
		Use the empty native stage group when a donor stage has no implementation.
		The authored id remains available through `currentStageId` and to import
		diagnostics; no donor sprite, script, or chart-specific substitute is
		invented here.
	*/
	public function applyNativeFallback(requested:String, diagnostic:String = ''):StageHelper {
		authoredName = requested == null || StringTools.trim(requested) == '' ? name : requested;
		name = 'stage';
		fallbackDiagnostic = diagnostic == null ? '' : diagnostic;
		interp = null;
		return this;
	}

	// Char Infos

	public static function defaultInfo(?char:String = 'dad') {
		var info:CharacterInfo = {x: 100, y: 100, camOffsetX: 0, camOffsetY: 0, scrollFactor: FlxPoint.get(1, 1), zIndex: -69};
		switch(char) {
			case 'bf':
				info.x = 770;
				info.y = 450;
			case 'gf':
				info.x = 400;
				info.y = 130;
		}
		return info;
	}

	public function setOffsets(char:String = 'dad', offx:Float = 0, offy:Float = 0, ?addition:Bool = true) {
		var info = getInfo(char);
		if (addition) {
			offx += info.x;
			offy += info.y;
		}
		info.x = offx;
		info.y = offy;
		return this;
	}

	/**
		Apply one BaseStage start-point operation to the native stage and the live
		actor occupying that slot.  Imported FPS Plus stages are loaded after the
		three standard characters have been created, so changing only the stored
		CharacterInfo would fix later swaps but leave the opening frame misplaced.
	*/
	public function applyStartOffset(char:String = 'dad', axis:String = 'x', value:Float = 0,
		?operation:String = 'add'):StageHelper {
		var info = getInfo(char);
		if (info == null || Math.isNaN(value))
			return this;
		var normalizedAxis = axis == null ? 'x' : StringTools.trim(axis).toLowerCase();
		var normalizedOperation = operation == null ? 'add' : StringTools.trim(operation).toLowerCase();
		var oldValue = normalizedAxis == 'y' ? info.y : info.x;
		var nextValue = switch (normalizedOperation) {
			case 'set' | '=': value;
			case 'subtract' | '-=': oldValue - value;
			default: oldValue + value;
		};
		if (normalizedAxis == 'y')
			info.y = nextValue;
		else
			info.x = nextValue;

		// Move the currently mounted actor by the same delta.  Character offsets
		// (playerOffsetX/enemyOffsetX/gfOffsetX) remain untouched and are applied
		// by PlayState when a later Change Character event constructs a replacement.
		if (PlayState.instance != null) {
			var actor:Character = switch (normalizeCharacterRole(char)) {
				case 'boyfriend': PlayState.instance.boyfriend;
				case 'gf': PlayState.instance.gf;
				default: PlayState.instance.dad;
			};
			if (actor != null) {
				var delta = nextValue - oldValue;
				if (normalizedAxis == 'y')
					actor.y += delta;
				else
					actor.x += delta;
			}
		}
		return this;
	}

	public function setCamOffsets(char:String = 'dad', offx:Int = 0, offy:Int = 0, ?addition:Bool = true) {
		var info = getInfo(char);
		if (addition) {
			offx += info.camOffsetX;
			offy += info.camOffsetY;
		}
		info.camOffsetX = offx;
		info.camOffsetY = offy;
		// Imported stages author absolute camera offsets; classic charts use
		// additive ones on top of the character defaults.  Either way the
		// per-frame camera math reads Character.followCamX/Y, so apply the
		// stored value to the live actor here - this is the single instance
		// both the opening frame and later character swaps converge on.
		info.camOffsetsAbsolute = !addition;
		if (PlayState.instance != null) {
			var actor:Character = switch (normalizeCharacterRole(char)) {
				case 'boyfriend': PlayState.instance.boyfriend;
				case 'gf': PlayState.instance.gf;
				default: PlayState.instance.dad;
			};
			if (actor != null) {
				if (addition) {
					actor.followCamX += offx;
					actor.followCamY += offy;
				} else {
					// Donor composition: funkin adds the stage's authored camera
					// offsets on top of the character's own CharacterData
					// cameraOffsets (cameraFocusPoint = midpoint + char offsets +
					// stage offsets).  The stage script zeroes followCamX/Y first
					// to cancel the classic 150/-100 defaults, so reapply the
					// authored character offsets here.
					actor.followCamX = offx + actor.vSliceCamOffsetX;
					actor.followCamY = offy + actor.vSliceCamOffsetY;
					actor.camOffsetX = actor.followCamX;
					actor.camOffsetY = actor.followCamY;
					// The donor stage owns the framing: the classic per-branch
					// camera constants must not stack on top (PlayState camera
					// math checks this flag).
					actor.authoredCamOffsets = true;
					actor.cameraFocusPoint.set(actor.x + actor.width / 2 + actor.followCamX,
						actor.y + actor.height / 2 + actor.followCamY);
				}
			}
		}
		return this;
	}

	public function setScrollFactor(char:String = 'dad', scrollx:Float = 1, scrolly:Float = 1) {
		getInfo(char).scrollFactor.set(scrollx, scrolly);
		return this;
	}

	public function getInfo(char:String = 'dad') {
		switch(char) {
			case 'dad': return dadInfo;
			case 'bf' | 'boyfriend': return bfInfo;
			case 'gf': return gfInfo;
			default: return null;
		}
	}

	/** Return an independent stage-space position for a gameplay character slot. */
	public function getCharacterPosition(char:String = 'dad'):FlxPoint {
		var info = getInfo(char);
		return info == null ? FlxPoint.get() : FlxPoint.get(info.x, info.y);
	}

	public function getDadPosition():FlxPoint {
		return getCharacterPosition('dad');
	}

	public function getBoyfriendPosition():FlxPoint {
		return getCharacterPosition('bf');
	}

	public function getGirlfriendPosition():FlxPoint {
		return getCharacterPosition('gf');
	}

	/**
	 * Attach a character using the native three-slot owner when the role is a
	 * gameplay slot, or as a stage-owned spectator for OTHER.  The latter is
	 * intentionally small: it renders and participates in stage cleanup, but it
	 * does not pretend to be a second note lane or a replacement PlayState slot.
	 */
	public function addCharacter(character:Character, ?role:Dynamic):Character {
		if (character == null)
			return null;
		var normalized = normalizeCharacterRole(role);
		character.characterType = normalized;
		if (normalized == 'boyfriend' || normalized == 'dad' || normalized == 'gf') {
			if (PlayState.instance != null)
				PlayState.instance.switchToChar(character, normalized, false);
			return character;
		}

		character.isPlayer = false;
		var name = '__hxc_character_' + extraCharacterIndex++;
		elements.set(name, character);
		// FlxSprite/Character do not expose the donor engine's zIndex field.
		// Read it dynamically when an imported wrapper supplies one, otherwise
		// use the normal stage insertion order sentinel. This keeps stage sorting
		// engine-owned without making Character pretend to implement a foreign
		// display-list property.
		var authoredZ:Dynamic = null;
		try authoredZ = Reflect.field(character, 'zIndex') catch (_:Dynamic) {}
		var characterZ:Int = authoredZ == null ? -69 : Std.int(authoredZ);
		setZIndex(character, characterZ);
		if (PlayState.instance != null) {
			if (character.cameras == null || character.cameras.length == 0)
				character.cameras = [PlayState.instance.camGame];
			PlayState.instance.add(character);
		}
		return character;
	}

	static function normalizeCharacterRole(role:Dynamic):String {
		if (role == null)
			return 'other';
		var value = Std.string(role).toLowerCase();
		return switch (value) {
			case 'bf' | 'boyfriend' | 'player' | 'player1' | 'character.bf': 'boyfriend';
			case 'dad' | 'opponent' | 'player2' | 'character.dad': 'dad';
			case 'gf' | 'girlfriend' | 'player3' | 'character.gf': 'gf';
			default: 'other';
		};
	}

	// Elements

	/** Stage is a compatibility owner, not a member of the PlayState display
	 * list. Forward donor `stage.add(sprite)` to the live state once so the
	 * sprite receives draw/update callbacks and stage-swap cleanup. */
	override public function add(sprite:FlxSprite):FlxSprite {
		if (sprite == null)
			return null;
		if (members.indexOf(sprite) < 0)
			super.add(sprite);
		if (PlayState.instance != null && PlayState.instance.curStage == this)
			PlayState.instance.attachStageMember(sprite);
		return sprite;
	}

	override public function remove(sprite:FlxSprite, splice:Bool = false):FlxSprite {
		if (sprite == null || members.indexOf(sprite) < 0)
			return sprite;
		if (PlayState.instance != null && PlayState.instance.curStage == this)
			PlayState.instance.detachStageMember(sprite);
		// FlxSpriteGroup.remove clears cameras. Donor scripts may temporarily
		// remove and re-add a HUD prop, so keep its explicit target intact.
		var explicitCameras:Array<flixel.FlxCamera> = null;
		@:privateAccess explicitCameras = sprite._cameras;
		var removed = super.remove(sprite, splice);
		if (explicitCameras != null)
			sprite.cameras = explicitCameras;
		return removed;
	}

	/** A distinct invisible anchor is retained for every authored slot node.
	 * Repeated keys select the last anchor without removing earlier nodes. */
	@:keep public function addCodenameAnchor(key:String, ordinal:Int):FlxSprite {
		if (key == null || ordinal < 0) throw 'Invalid Codename stage anchor';
		var anchor = new FlxSprite();
		anchor.visible = false;
		anchor.active = false;
		add(anchor);
		codenameOrderNodes.push({kind:'anchor', ordinal:ordinal, key:key, sprite:anchor});
		codenameAnchors.set(key, anchor);
		return anchor;
	}

	/** Called in XML order, independently of duplicate donor prop names. */
	@:keep public function addCodenameProp(sprite:FlxSprite, ordinal:Int):Void {
		if (sprite == null || ordinal < 0) throw 'Invalid Codename stage prop';
		add(sprite);
		codenameOrderNodes.push({kind:'prop', ordinal:ordinal, key:Std.string(ordinal), sprite:sprite});
	}

	function insertCodenameActor(actor:FlxSprite, key:String):Void {
		var state = PlayState.instance;
		if (actor == null || state == null || state.curStage != this) return;
		var anchor = codenameAnchors.get(key);
		if (actor == anchor) return;
		if (state.members.indexOf(actor) >= 0) state.remove(actor, true);
		var index = anchor == null ? -1 : state.members.indexOf(anchor);
		if (index < 0) state.add(actor);
		else state.insert(index, actor);
	}

	/** Actors remain PlayState-owned. Unknown slots append, as in the donor. */
	@:keep public function placeCodenameActor(actor:FlxSprite, slotKey:String):Void {
		if (actor == null || slotKey == null) return;
		var existing = false;
		for (binding in codenameActorBindings) if (binding.actor == actor) {
			binding.key = slotKey;
			existing = true;
			break;
		}
		if (!existing) codenameActorBindings.push({actor:actor, key:slotKey});
		insertCodenameActor(actor, slotKey);
	}

	/** Native character swaps can also re-add other roles. Restore all bound
	 * occurrences in their original order after replacing the changed actor. */
	public function rebindCodenameActor(previous:FlxSprite, replacement:FlxSprite):Void {
		if (previous == null || replacement == null) return;
		var found = false;
		for (binding in codenameActorBindings) if (binding.actor == previous) {
			binding.actor = replacement;
			found = true;
		}
		if (found) for (binding in codenameActorBindings)
			insertCodenameActor(binding.actor, binding.key);
	}

	public function addElement(name:String, element:Dynamic, ?zIndex:Int) {
		elements.set(name, element);

		if ((element is FlxGroup)) {
			element.forEach(function(piece) {
				this.add(piece);
				setZIndex(piece, resolvePropZ(piece, zIndex));
			});
		} else {
			this.add(element);
			setZIndex(element, resolvePropZ(element, zIndex));
		}
	}

	/**
		Scripts that layer a prop through `addSprite(prop, BEHIND_ALL)` (positional
		insert before the actors) then register it here with no zIndex. Passing
		that null straight into setZIndex used to hit the -69 sentinel, which
		auto-assigned `highestZ + 10` and lifted the freshly-layered background
		above the un-z-indexed actors in PlayState's state-level refresh() sort.
		When the caller omits the zIndex, keep the engine z the sprite already has
		(HxcCompatRuntime.getZIndex consults the native field, the compat side
		table, and this stage's own map); the sentinel only auto-assigns when a
		caller passes -69 on purpose.
	*/
	function resolvePropZ(element:Dynamic, ?zIndex:Null<Int>):Null<Int> {
		if (zIndex != null)
			return zIndex;
		var existing:Dynamic = null;
		try existing = HxcCompatRuntime.getZIndex(element) catch (_:Dynamic) {}
		return existing == null ? null : Std.int(existing);
	}

	public function getElement(name:String) {
		return elements.get(name);
	}

	/**
	 * V-Slice/HXC Stage aliases.  Imported stage scripts use these accessors to
	 * reach the live gameplay characters and named props; keep the lookup on
	 * the stage object so both `stage.getDad()` and the unqualified PlayState
	 * compatibility functions resolve the same objects.
	 */
	public function getDad():Character {
		return PlayState.instance == null ? null : PlayState.instance.dad;
	}

	public function getBoyfriend():Character {
		return PlayState.instance == null ? null : PlayState.instance.boyfriend;
	}

	public function getGirlfriend():Character {
		return PlayState.instance == null ? null : PlayState.instance.gf;
	}

	public function getOpponent():Character {
		return getDad();
	}

	public function getNamedProp(name:String):Dynamic {
		var element = getElement(name);
		if (element != null) return element;
		// Older selected V-Slice scripts register their proven generated props
		// in this stage's element map at load time. Resolve only an unambiguous
		// generated identifier belonging to this stage instance.
		var legacy = VSliceStageCompat.legacyGeneratedProp(name, elements);
		return Std.isOfType(legacy, FlxSprite) ? legacy : null;
	}

	public function removeElement(name:String, ?destroy:Bool = true) {
		var element = getElement(name);

		if (element != null) {
			elements.remove(name);
			if ((element is FlxGroup))
				(cast element:FlxGroup).forEach(function(piece) remove(cast piece));
			else
				remove(cast element);
			if (destroy) element.destroy();
		}
	}

	// Z Index

	public function getZIndex(element:String) {
		return zIndexes.get(getElement(element));
	}

	/** Read the z-order for a live sprite without requiring a donor element name. */
	public function getZIndexForElement(element:Dynamic):Null<Int> {
		if (element == null)
			return null;
		return zIndexes.get(cast element);
	}

	/**
		Persist one actor's authored stage zIndex (same lifecycle as
		setOffsets): it must survive character swaps, and it must land in the
		engine's z sources for both the stage's own sort and PlayState's
		state-level refresh().  HScript writes like `dad.zIndex = 300` cannot
		see a physical field (flixel sprites carry none), so scripts route
		through here.
	*/
	public function setCharacterZ(char:String = 'dad', z:Int = 0) {
		var info = getInfo(char);
		if (info != null)
			info.zIndex = z;
		var actor:FlxSprite = switch (normalizeCharacterRole(char)) {
			case 'boyfriend': PlayState.instance == null ? null : PlayState.instance.boyfriend;
			case 'gf': PlayState.instance == null ? null : PlayState.instance.gf;
			case 'dad': PlayState.instance == null ? null : PlayState.instance.dad;
			default: null;
		};
		if (actor != null)
			setZIndex(actor, z);
		return this;
	}

	/** Keep the role's authored depth when PlayState replaces its actor. */
	public function rebindCharacterZ(role:String, previous:Dynamic, replacement:Dynamic):Void {
		if (previous != replacement && Std.isOfType(previous, FlxSprite)) {
			zIndexes.remove(cast previous);
			if (Std.isOfType(previous, Character))
				presentedCharacters.remove(cast previous);
		}
		var info = getInfo(role);
		if (info != null && info.zIndex != -69 && Std.isOfType(replacement, FlxSprite))
			setZIndex(cast replacement, info.zIndex);
	}

	/** Retain raw StageDataCharacter values, independently of the actor mounted
	 * while the stage script runs. Fresh actors need their own base scale/hitbox. */
	public function setVSliceCharacterPresentation(role:String, feetX:Float, feetY:Float,
		scaleX:Float = 1, scaleY:Float = 1, scrollX:Float = 1, scrollY:Float = 1,
		alpha:Float = 1, angle:Float = 0, cameraX:Int = 0, cameraY:Int = 0):Void {
		var normalized = normalizeCharacterRole(role);
		if (normalized != 'boyfriend' && normalized != 'dad' && normalized != 'gf')
			return;
		vSliceCharacterPresentation.set(normalized, {
			feetX: feetX, feetY: feetY, scaleX: scaleX, scaleY: scaleY,
			scrollX: scrollX, scrollY: scrollY, alpha: alpha, angle: angle,
			cameraX: cameraX, cameraY: cameraY
		});
	}

	/** Reapply the donor Stage.addCharacter operation to a newly fetched actor. */
	public function applyVSliceCharacterPresentation(role:String, actor:Character):Bool {
		if (actor == null)
			return false;
		var normalized = normalizeCharacterRole(role);
		var data = vSliceCharacterPresentation.get(normalized);
		if (data == null)
			return false;
		if (presentedCharacters.get(actor) == normalized)
			return true;
		actor.scale.set(actor.stageBaseScaleX * data.scaleX, actor.stageBaseScaleY * data.scaleY);
		actor.updateHitbox();
		actor.flipX = normalized == 'boyfriend' ? !actor.stageBaseFlipX : actor.stageBaseFlipX;
		var globalX:Float = switch (normalized) {
			case 'boyfriend': actor.playerOffsetX;
			case 'gf': actor.gfOffsetX;
			default: actor.enemyOffsetX;
		};
		var globalY:Float = switch (normalized) {
			case 'boyfriend': actor.playerOffsetY;
			case 'gf': actor.gfOffsetY;
			default: actor.enemyOffsetY;
		};
		actor.x = data.feetX - actor.width / 2 + globalX;
		actor.y = data.feetY - actor.height + globalY;
		actor.scrollFactor.set(data.scrollX, data.scrollY);
		actor.alpha = data.alpha;
		actor.angle = data.angle;
		actor.followCamX = data.cameraX + actor.vSliceCamOffsetX;
		actor.followCamY = data.cameraY + actor.vSliceCamOffsetY;
		actor.camOffsetX = actor.followCamX;
		actor.camOffsetY = actor.followCamY;
		actor.authoredCamOffsets = true;
		actor.syncHxcPosition();
		actor.cameraFocusPoint.set(actor.x + actor.width / 2 + actor.followCamX,
			actor.y + actor.height / 2 + actor.followCamY);
		var outgoing:Array<Character> = [];
		for (previous in presentedCharacters.keys())
			if (previous != actor && presentedCharacters.get(previous) == normalized)
				outgoing.push(previous);
		for (previous in outgoing) {
			presentedCharacters.remove(previous);
			zIndexes.remove(previous);
		}
		presentedCharacters.set(actor, normalized);
		return true;
	}

	public function setZIndex(element:Dynamic, zIndex:Int = -69) {
		if ((element is String)) element = getElement(element);

		if (zIndex == -69) zIndex = highestZ + 10;

		zIndexes.set(element, zIndex);
		if (zIndex > highestZ) highestZ = zIndex;
	}

	/**
		Record a role actor as staged out by the stage's authored hide (Kade
		source stages emit `dad.visible = false` when the opponent's entrance is
		staged by the song's own cutscene).  Stays reversible: the song script's
		cutscene handback calls restoreStagedActors() so the entrance machinery
		owns the re-entrance instead of the hide being permanent.
	*/
	public function stageOutActor(char:String = 'dad') {
		var role = normalizeCharacterRole(char);
		var actor:FlxSprite = switch (role) {
			case 'boyfriend': PlayState.instance == null ? null : PlayState.instance.boyfriend;
			case 'gf': PlayState.instance == null ? null : PlayState.instance.gf;
			case 'dad': PlayState.instance == null ? null : PlayState.instance.dad;
			default: null;
		};
		if (actor == null)
			return this;
		stagedOutActors.set(role, actor.visible);
		actor.visible = false;
		return this;
	}

	/** Bring back every actor a staged hide removed (song cutscene handback). */
	public function restoreStagedActors() {
		if (stagedOutActors == null || !stagedOutActors.iterator().hasNext())
			return this;
		for (role in stagedOutActors.keys()) {
			var actor:FlxSprite = switch (role) {
				case 'boyfriend': PlayState.instance == null ? null : PlayState.instance.boyfriend;
				case 'gf': PlayState.instance == null ? null : PlayState.instance.gf;
				case 'dad': PlayState.instance == null ? null : PlayState.instance.dad;
				default: null;
			};
			if (actor != null)
				actor.visible = true;
		}
		stagedOutActors.clear();
		return this;
	}

	function sortByZIndex(order:Int, Obj1:FlxSprite, Obj2:FlxSprite):Int {
		return FlxSort.byValues(order, zIndexes.get(Obj1), zIndexes.get(Obj2));
	}

	public function refresh() {
		sort(sortByZIndex, FlxSort.ASCENDING);
		if (PlayState.instance != null && PlayState.instance.curStage == this)
			PlayState.instance.refresh();
	}

	// Functions

	public function addFunction(name:String, afunction:Dynamic) {
		functions.set(name, afunction);
	}

	public function getFunction(name:String) {
		return functions.get(name);
	}

	public function doFunction(name:String) {
		var method = getFunction(name);
		return method();
	}

	// Sprite Group Stuff

	/** Remove registered stage elements. Runtime stage swaps detach the objects
	 * first and destroy them from PlayState, so they can request `false` here to
	 * avoid a second destroy while normal callers retain the old behavior. */
	public function clearStage(?destroyElements:Bool = true):Void {
		var handledOrderNodes:Array<FlxSprite> = [];
		for (element in elements) {
			if ((element is FlxGroup))
				(cast element:FlxGroup).forEach(function(piece) {
					handledOrderNodes.push(cast piece);
					remove(cast piece);
				});
			else {
				handledOrderNodes.push(cast element);
				remove(cast element);
			}
			if (destroyElements && element != null)
				element.destroy();
		}
		// A donor can call stage.add(sprite) without registering an element.
		// Detach those direct members too, including their state ownership.
		for (sprite in members.copy()) {
			if (sprite == null)
				continue;
			handledOrderNodes.push(sprite);
			remove(sprite, true);
			if (destroyElements)
				sprite.destroy();
		}
		// A removed XML node may have no element name and no current group
		// membership. Its order record still owns it until this stage ends.
		for (node in codenameOrderNodes) {
			var sprite = node.sprite;
			if (sprite == null || handledOrderNodes.indexOf(sprite) >= 0) continue;
			handledOrderNodes.push(sprite);
			if (PlayState.instance != null && PlayState.instance.curStage == this)
				PlayState.instance.detachStageMember(sprite);
			if (destroyElements) sprite.destroy();
		}
		group.clear();
		elements.clear();
		functions.clear();
		codenameOrderNodes.resize(0);
		codenameAnchors.clear();
		codenameActorBindings.resize(0);
		codenamePlacement = null;
		characterPoses.clear();
		presentedCharacters.clear();
		vSliceCharacterPresentation.clear();
	}

	/*override function destroy():Void {
		clearStage();

		super.destroy();
	}*/

	override function preAdd(sprite:FlxSprite):Void {
		sprite.x += x;
		sprite.y += y;
		sprite.alpha *= alpha;
		@:privateAccess if (sprite._cameras == null && _cameras != null)
			sprite.cameras = _cameras;

		if (clipRect != null)
			clipRectTransform(sprite, clipRect);
	}
}
