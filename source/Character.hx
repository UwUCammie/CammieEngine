package;

import hscript.Expr;
import flixel.tweens.FlxTween;
import flixel.util.FlxTimer;
import flixel.group.FlxGroup;
import flixel.math.FlxAngle;
import flixel.math.FlxAngle;
import flixel.math.FlxMath;
import flixel.math.FlxPoint;
import flixel.math.FlxRect;
import flixel.math.FlxMatrix;
import flixel.FlxCamera;
import hscript.Interp;
import hscript.ParserEx;
import haxe.xml.Parser;
import hscript.InterpEx;
import flixel.util.FlxColor;
import flixel.FlxSprite;
import flixel.animation.FlxBaseAnimation;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.graphics.frames.FlxFramesCollection;
import animate.FlxAnimateFrames;
import flash.display.BitmapData;
import lime.utils.Assets;
import flixel.FlxG;
import lime.system.System;
import lime.app.Application;
import flixel.sound.FlxSound;
import openfl.utils.AssetType;
import flixel.util.FlxSignal;
import Song.SwagSong;
#if sys
import sys.io.File;
import sys.FileSystem;
import haxe.io.Path;
import openfl.utils.ByteArray;
#end
import haxe.Json;
import tjson.TJSON;
import haxe.format.JsonParser;
import FNFAssets.Extensions;
using StringTools;
enum abstract EpicLevel(Int) from Int to Int {
	var Level_NotAHoe = 0;
	var Level_Boogie = 1;
	var Level_Sadness = 2;
	var Level_Sing = 3;

	@:op(A > B) static function gt(a:EpicLevel, b:EpicLevel):Bool;
	@:op(A >= B) static function gte(a:EpicLevel, b:EpicLevel):Bool;
	@:op(A == B) static function equals(a:EpicLevel, b:EpicLevel):Bool;
	@:op(A != B) static function nequals(a:EpicLevel, b:EpicLevel):Bool;
	@:op(A < B) static function lt(a:EpicLevel, b:EpicLevel):Bool;
	@:op(A <= B) static function lte(a:EpicLevel, b:EpicLevel):Bool;
}
typedef TCharacterRefJson = {
	var like:String;
	var icons:Array<Int>;
	var ?colors:Array<String>;
}
typedef CharacterProgramCacheEntry = {
	var source:String;
	var program:Expr;
}
class Character extends DisSprite implements CodenameCharacterAccess {
	public var codenameRuntime:CodenameCharacterRuntime;
	public var codenameGamePostCreated:Bool = false;
	public var codenameLiveDefinition:Dynamic;
	// Node-time XML playback needs the donor script path before the completed
	// visual definition exists. Keep this partial state private to construction.
	var codenameVisualBuilding:Bool = false;
	var codenameBuildingAnimations:Array<Dynamic> = null;
	@:keep public var codenameSourceId:String;
	@:keep public var xml:CodenameXmlAccess;
	@:keep public var globalOffset:FlxPoint = FlxPoint.get();
	@:keep public var cameraOffset:FlxPoint = FlxPoint.get();
	/** Nightmare Vision's directional singing-camera distance in world pixels. */
	@:keep public var camDisplacement:Float = 20;
	@:keep public var frameOffset:FlxPoint = FlxPoint.get();
	@:keep public var frameOffsetAngle:Null<Float> = null;
	@:keep public var extraOffset:FlxPoint = FlxPoint.get();
	@:keep public var ghostDraw:Bool = false;
	@:keep public var playerOffsets:Bool = false;
	@:keep public var holdTime:Float = 4;
	@:keep public var beatInterval:Int = 2;
	@:keep public var beatOffset:Int = 0;
	@:keep public var danceOnBeat:Bool = true;
	@:keep public var skipNegativeBeats:Bool = false;
	@:keep public var lastAnimContext:Dynamic;
	@:keep public var lastHit:Float = 0;
	@:keep public var icon:String = 'face';
	@:keep public var iconColor:Null<Int>;
	@:keep public var gameOverCharacter:String = 'bf-dead';
	@:keep public var extra:Map<String, Dynamic> = new Map();
	var codenameAnimationContext:Dynamic;
	var codenameAnimationLock:Bool = false;
	var codenameBaseFlipped:Bool = false;
	var codenameReverseDrawProcedure:Bool = false;
	var codenamePendingForce:Null<Bool>;
	var codenameHasPendingForce:Bool = false;
	var characterDestroyed:Bool = false;

	static var characterProgramCache:Map<String, CharacterProgramCacheEntry> = new Map();
	static var characterProgramCacheOrder:Array<String> = [];
	static inline var CHARACTER_PROGRAM_CACHE_MAX:Int = 64;

	/** Parse character scripts once per unchanged source. Character swaps still
		create fresh interpreters and run init for each actor; only the immutable
		HScript syntax tree is reused. Keep a small LRU so browsing many imported
		characters cannot retain an unbounded number of programs. */
	static function cachedCharacterProgram(key:String, source:String):Expr {
		var cacheKey = key == null ? '' : StringTools.trim(key);
		var content = source == null ? '' : source;
		if (cacheKey == '')
			return new hscript.Parser().parseString(content);

		var cached = characterProgramCache.get(cacheKey);
		if (cached != null && cached.source == content) {
			characterProgramCacheOrder.remove(cacheKey);
			characterProgramCacheOrder.push(cacheKey);
			return cached.program;
		}

		var program = new hscript.Parser().parseString(content);
		characterProgramCache.set(cacheKey, {source: content, program: program});
		characterProgramCacheOrder.remove(cacheKey);
		characterProgramCacheOrder.push(cacheKey);
		while (characterProgramCacheOrder.length > CHARACTER_PROGRAM_CACHE_MAX) {
			var expired = characterProgramCacheOrder.shift();
			characterProgramCache.remove(expired);
		}
		return program;
	}

	public var animOffsets:Map<String, Array<Dynamic>>;
	public var camOffsets:Map<String, Array<Dynamic>>;
	public var debugMode:Bool = false;

	public var deathSound = 'fnf_loss_sfx.ogg';
	public var gameoverMusic = 'gameOver.ogg';
	public var gameoverMusicEnd = 'gameOverEnd.ogg';
	/** V-Slice character death-camera metadata.  These remain zero/default for
	 * native and legacy characters, so the existing game-over framing is
	 * unchanged unless an imported definition explicitly authors them. */
	public var deathCameraOffsetX:Float = 0;
	public var deathCameraOffsetY:Float = 0;
	public var deathCameraZoom:Float = 0;

	public var isPlayer:Bool = false;
	/** Assigned only by the multi-visit runtime smoke probe. Keeping the token
	 * on the instance detects accidental reuse without retaining old sprites. */
	@:allow(PlayState) var runtimeSmokeActorToken:Int = 0;
	/**
	 * V-Slice character geometry aliases.  HXC character/song scripts use these
	 * FlxPoint members as part of the common Character ABI.  Keeping the points
	 * on the native actor lets imported callbacks use the same operations without
	 * a chart-specific rewrite or a null dynamic field.
	 */
	public var characterOrigin:FlxPoint;
	public var cameraFocusPoint:FlxPoint;
	public var originalPosition:FlxPoint;
	/** Character definition scale before any stage applies its own multiplier. */
	public var stageBaseScaleX:Float = 1;
	public var stageBaseScaleY:Float = 1;
	public var stageBaseFlipX:Bool = false;
	/**
	 * Native storage for the donor role value.  The gameplay fork does not use
	 * an enum-backed CharacterType, so this remains Dynamic: imported scripts
	 * use both the named BF/DAD/GF values and the donor's OTHER/spectator value.
	 */
	public var characterType:Dynamic = 'dad';
	/**
	 * Donor characters can opt out of a host-side exclusion preference.  The
	 * native engine has no separate exclusion pass, but retaining the flag is
	 * safe and lets generic character code make the same decision when one is
	 * present.
	 */
	// Some mounted HXC revisions assign the donor's empty-list sentinel here,
	// while others use a boolean. Keep the metadata Dynamic so either spelling
	// is safe; this fork has no separate exclusion pass to coerce it.
	public var ignoreExclusionPref:Dynamic = false;
	public var noFlip:Bool = false;
	/** V-Slice's `no-gf`/`nogf` ids use the native GF slot for camera and
	 * stage bookkeeping, but keep the actor fully hidden instead of falling
	 * back to Dad when the donor has no girlfriend definition. */
	public var isHiddenCharacter:Bool = false;
	public var requestedCharacter:String = '';
	/** Authored id and the concrete visual selected by Song's shared resolver
	 * intentionally remain separate (for example miku -> mikuv2). */
	public var resolvedCharacter:String = '';
	public var resolvedImplementation:String = '';
	public var resolvedAssetRoot:String = '';
	/** Source CharacterData's HUD icon identity. Nightmare Vision stores this as
	 * `healthicon`; other character formats keep the established character-id
	 * fallback so HealthIcon continues using its existing owner-aware resolver. */
	@:keep public var healthIcon(get, never):String;
	function get_healthIcon():String
		return nightmareVisionHealthIcon == null ? curCharacter : nightmareVisionHealthIcon;
	/** NMV scripts use this packed color for character-owned health displays. */
	@:keep public var healthColour(get, set):FlxColor;
	var nightmareVisionHealthColour:Null<FlxColor> = null;
	/** Mutable source-compatible RGB triplet. Keep it behind accessors so the
	 * Psych Lua property bridge can continue using its icon-aware fallback. */
	@:keep public var healthColorArray(get, set):Array<Int>;
	var nightmareVisionHealthColorArray:Array<Int> = [255, 0, 0];
	@:keep function get_healthColorArray():Array<Int> {
		return nightmareVisionHealthColorArray;
	}
	@:keep function set_healthColorArray(value:Array<Int>):Array<Int> {
		nightmareVisionHealthColorArray = value;
		return value;
	}
	@:keep function get_healthColour():FlxColor {
		if (nightmareVisionHealthColour != null)
			return nightmareVisionHealthColour;
		var fallback:FlxColor = isPlayer ? playerColor : enemyColor;
		var authored:Dynamic = nightmareVisionCharacterData == null ? null
			: Reflect.field(nightmareVisionCharacterData, 'healthbar_colour');
		if (authored == null)
			return fallback;
		if (Std.isOfType(authored, String)) {
			var parsed = FlxColor.fromString(Std.string(authored));
			return parsed == null ? fallback : parsed;
		}
		var numeric = Std.parseFloat(Std.string(authored));
		return !Math.isFinite(numeric) ? fallback : cast Std.int(numeric);
	}
	@:keep function set_healthColour(value:FlxColor):FlxColor {
		nightmareVisionHealthColour = value;
		return value;
	}

	static function nightmareVisionColorArrayFromPacked(value:FlxColor):Array<Int> {
		var packed:Int = cast value;
		return [(packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF];
	}

	/** Load both source health-color forms while retaining the authored mutable
	 * array reference. The array triplet has precedence over the packed color. */
	function loadNightmareVisionHealthColors(definition:Dynamic):Void {
		nightmareVisionCharacterData = definition;
		nightmareVisionHealthColour = null;
		var authored:Dynamic = definition == null ? null : Reflect.field(definition, 'healthbar_colors');
		if (Std.isOfType(authored, Array)) {
			var components:Array<Dynamic> = cast authored;
			if (components.length > 2) {
				healthColorArray = cast authored;
				nightmareVisionHealthColour = FlxColor.fromRGB(
					Std.int(nightmareVisionNumber(components[0], 0)),
					Std.int(nightmareVisionNumber(components[1], 0)),
					Std.int(nightmareVisionNumber(components[2], 0)));
				return;
			}
		}
		healthColorArray = nightmareVisionColorArrayFromPacked(healthColour);
	}

	static function nightmareVisionHealthIconFromDefinition(definition:Dynamic):Null<String> {
		if (definition == null) return null;
		var authored:Dynamic = Reflect.field(definition, 'healthicon');
		if (authored == null) return 'face';
		if (Std.isOfType(authored, String)) return cast authored;
		trace('[nightmare-vision-character-data] healthicon must be a string; using template face icon');
		return 'face';
	}
	/** Psych Lua reads this to reuse the actor's currently selected atlas. */
	public var imageFile:String = '';

	public var curCharacter:String = 'bf';
	public var altAnim:String = "";
	public var altNum:Int = 0;
	public var enemyOffsetX:Int = 0;
	public var enemyOffsetY:Int = 0;
	public var playerOffsetX:Int = 0;
	public var playerOffsetY:Int = 0;
	public var gfOffsetX:Int = 0;
	public var gfOffsetY:Int = 0;
	/** V-Slice CharacterData offsets used by Bopper's animation screen shift.
	 * Keep them distinct from native role placement offsets, which stage scripts
	 * and character repositioning may change after the atlas is imported. */
	public var vSliceGlobalOffsetX:Float = 0;
	public var vSliceGlobalOffsetY:Float = 0;
	public var vSliceGlobalOffsetsAuthored:Bool = false;
	public var camOffsetX:Int = 0;
	public var camOffsetY:Int = 0;
	public var followCamX:Int = 150;
	public var followCamY:Int = -100;
	/** Character-script camera values after this actor's own init hook.  The
	 * Psych camera bridge uses later edits as offsets from this native baseline,
	 * so built-in fallback scripts do not leak their legacy framing into Psych. */
	public var psychInitialFollowCamX:Int = 150;
	public var psychInitialFollowCamY:Int = -100;
	/** Raw Psych CharacterFile camera metadata for Lua/HScript property access.
	 * PlayState applies the authored role sign when computing the camera target. */
	public var cameraPosition:Array<Float> = [0, 0];
	/** Raw authored Psych/Nightmare Vision character start position for scripts.
	 * This remains metadata only; stage placement applies it through the engine's
	 * existing position resolver, so reading it here must not move the actor. */
	@:keep public var positionArray:Array<Float> = [0, 0];
	/** Authored V-Slice CharacterData cameraOffsets, kept separate from the
	 * classic follow defaults.  Imported stages zero followCamX/Y (classic
	 * 150/-100 has no donor meaning) and StageHelper.setCamOffsets recomposes
	 * the focus as stage offsets + these authored offsets. */
	public var vSliceCamOffsetX:Int = 0;
	public var vSliceCamOffsetY:Int = 0;
	/** An imported stage authored this actor's camera offsets absolutely, so
	 * the classic per-branch camera constants (bfCamOffset/dadCamOffset and
	 * the per-animation nudges) must not stack on top of them. */
	public var authoredCamOffsets:Bool = false;
	/** Literal FPS Plus CharacterInfo metadata retained by the HXC bridge. */
	public var hxcInfoApplied:Bool = false;
	public var hxcIconName:String = '';
	public var hxcSpritePath:String = '';
	public var hxcFrameLoadType:String = '';
	public var hxcExtraData:Map<String, Array<Dynamic>> = new Map<String, Array<Dynamic>>();
	// suffix for the idle anim ('-alt' via Alt Idle Animation events); dance()
	// uses <idle><suffix> when that anim exists, else plain 'idle'
	public var idleSuffix:String = '';
	public var midpointX:Int = 0;
	public var midpointY:Int = 0;
	public var holdTimer:Float = 0;
	/** Number of beats between automatic V-Slice/character idle dances.  A
	 * non-positive value disables the automatic beat dance; explicit sing/event
	 * animation calls remain unaffected. */
	public var danceEvery:Int = 1;
	/** Psych-compatible runtime switch for suppressing dance() calls.  Stage
	 * scripts may change it while explicit sing/playAnim calls stay available. */
	public var skipDance:Bool = false;
	/**
	 * V-Slice character metadata which is not part of the old registry schema.
	 *
	 * DDTO++ and other V-Slice conversions use these fields to select a
	 * costume at runtime.  Keep the original names as aliases as well as the
	 * namespaced copies: translated HXC/Lua code can ask the active Character
	 * for the same metadata without parsing a donor JSON file from disk.
	 */
	public var vSliceCostumes:String = '';
	public var vSliceCostumeList:Array<Dynamic> = [];
	public var vSliceDoesLoop:Bool = false;
	public var costumes:String = '';
	public var costumelist:Array<Dynamic> = [];
	public var doesLoop:Bool = false;
	/** Animation-asset registrations used by V-Slice definitions whose
	 * animations are split across multiple Sparrow/image files. */
	var vSliceAnimationAssets:Map<String, Dynamic> = new Map<String, Dynamic>();
	var vSliceAnimationFrames:Map<String, FlxFramesCollection> = new Map<String, FlxFramesCollection>();
	var vSliceBaseFrames:FlxFramesCollection;
	var vSliceActiveAnimationAsset:String = '';
	var vSliceBrokenAssetWarned:Bool = false;
	public var animationNotes:Array<Dynamic> = [];
	public var singPriority:Array<String> = [];
	public var noDanceAnims:Array<String> = ['cheer', 'fawn', 'sad'];
	public var like:String = "bf";
	public var beNormal:Bool = true;
	/**
	 * Color used by default for enemy, when not in duo mode or oppnt play.
	 */
	public var enemyColor:FlxColor = 0xFFFF0000;
	/**
	 * Color used by default for enemy in duo mode and oppnt play.
	 */
	public var opponentColor:FlxColor = 0xFFE7C53C;
	/**
	 * Color used by player while not in duo mode or oppnt play.
	 */
	public var playerColor:FlxColor = 0xFF66FF33;
	/**
	 * Color used by player when poisoned in fragile funkin.
	 */
	public var poisonColor:FlxColor = 0xFFA22CD1;
	/**
	 * Color used by enemy when poisoned in fragile funkin. 
	 */
	public var poisonColorEnemy:FlxColor = 0xFFEA2FFF;
	/**
	 * Color used by player in duo mode or oppnt play.
	 */
	public var bfColor:FlxColor = 0xFF149DFF;
	/**
	 * Set by ported character hscripts to tint their crossfade afterimages.
	 * A null value keeps the character's current tint.
	 */
	public var crossFadeColor:Null<FlxColor> = null;
	// sits on speakers, replaces gf
	public var likeGf:Bool = false;
	// uses animation notes
	public var hasGun:Bool = false;
	@:isVar public var stunned(get, set):Bool = false;
	var codenameStunnedTime:Float = 0;
	public var beingControlled:Bool = false;
	/**
	 * how many animations our current gf supports. 
	 * acts like a level meter, 0 means we aren't gf,
	 * 1 means we support the least animations (i think pixel-gf)
	 * 2 means we support the middle amount of animations (i think gf-tankmen)
	 * 3 means we support the full amount of animations (regular gf)
	 * you can have an epic level lower than your actual animations, 
	 * but the game will be safe and act like you don't have one.
	 */
	public var gfEpicLevel:EpicLevel = Level_NotAHoe;
	// like bf, is playable
	public var likeBf:Bool = false;
	public var isDie:Bool = false;
	/**
		V-Slice donor spelling of `isDie`. Imported scripts (CountdownGF's
		countdown idle freeze, DDTO's game-over swap) read and write
		`character.isDead`; the shared alias keeps that ABI on the native
		Character instead of per-script rewrites. Setting it also gates native
		dancing, matching V-Slice's onDanceHit `isDead` early-out which imported
		modules rely on.
	*/
	public var isDead(get, set):Bool;
	function get_isDead():Bool
		return isDie;
	function set_isDead(value:Bool):Bool {
		isDie = value;
		return value;
	}
	public var isPixel:Bool = false;
	private var interp:Interp;
	private var hxcFinishedAnimation:String = '';
	/** Parsed owner-local Nightmare Vision definition used by native atlas playback. */
	var nightmareVisionCharacterData:Dynamic = null;
	/** Owner-local source healthicon retained even if the character atlas falls back. */
	var nightmareVisionHealthIcon:Null<String> = null;
	/** Source Character's no-argument animation-finish callback signal. */
	public var onAnimationFinish:FlxSignal;
	/** Deduplicated diagnostics exposed to import screens/tests and mirrored in
	 * the native trace.  A missing visual must identify its dependency instead
	 * of appearing only as a silent Dad fallback. */
	public static var resolutionDiagnostics:Array<String> = [];
	public static function reportResolution(resolution:Dynamic):Void {
		if (resolution == null || resolution.complete == true)
			return;
		// CharacterInfo HXC companions are materialized immediately after the
		// native actor is constructed.  Their authored id is intentionally absent
		// from custom_chars, so defer this diagnostic only when PlayState has
		// proved that a selected manifest-owned definition has a complete atlas.
		// An HXC script without both media files remains a real dependency error.
		if (PlayState.instance != null && resolution.requested != null
			&& PlayState.instance.hasPendingHxcCharacterVisual(Std.string(resolution.requested)))
			return;
		var code = resolution.diagnosticCode == null || StringTools.trim(Std.string(resolution.diagnosticCode)) == ''
			? 'character-resolution-failed' : Std.string(resolution.diagnosticCode);
		var requested = resolution.requested == null ? '' : Std.string(resolution.requested);
		var detail = resolution.diagnostic == null ? '' : Std.string(resolution.diagnostic);
		var message = code + '|' + requested + '|' + detail;
		if (resolutionDiagnostics.indexOf(message) < 0) {
			resolutionDiagnostics.push(message);
			trace('[character-resolution] ' + message);
		}
		// Keep the resolver's precise reason, then add one shared runtime
		// dependency record with origin/search/impact fields.  The Dad
		// interpreter below is only an emergency visual implementation; the
		// authored id remains in `charName` and is never reported as resolved.
		var plan = EngineCompat.planVisualFallback('character', requested,
			'runtime chart character id',
			EngineCompat.visualDependencySearchPaths('character', requested),
			'character visual falls back to Dad; note lanes, timing, and score gameplay continue',
			'unresolved-source-dependency');
		EngineCompat.reportVisualFallback(plan);
	}
	public static function animationName(character:Character):String {
		return character != null && character.animation != null && character.animation.curAnim != null ? character.animation.curAnim.name : '';
	}
	/**
	 * V-Slice/HXC character aliases.  The native fork keeps animation state in
	 * FlxAnimationController and named offsets in `animOffsets`; exposing the
	 * donor method names here lets translated character/stage callbacks share
	 * one implementation instead of carrying chart-specific rewrites.
	 */
	/** Source-shaped pooled offset for the currently playing singing animation. */
	@:keep public function getSingDisplacement():FlxPoint {
		return switch (Character.animationName(this).substr(4).split('-')[0].toLowerCase()) {
			case 'left': FlxPoint.weak(-camDisplacement, 0);
			case 'down': FlxPoint.weak(0, camDisplacement);
			case 'up': FlxPoint.weak(0, -camDisplacement);
			case 'right': FlxPoint.weak(camDisplacement, 0);
			default: FlxPoint.weak();
		};
	}

	public function getCurrentAnimation():String {
		return Character.animationName(this);
	}
	@:keep public function getAnimName():String return animation.curAnim == null ? null : animation.curAnim.name;
	@:keep public function isAnimFinished():Bool return animation.curAnim == null || animation.curAnim.finished;

	public function setAnimationOffsets(name:String, x:Float = 0, y:Float = 0):Void {
		addOffset(name, x, y);
	}

	public function hasAnimation(name:String):Bool {
		return name != null && animation != null && animation.exists(name);
	}
	/** Psych's source field is initialized from these exact animations, then
	 * remains writable by scripts. A live default also sees late-added frames. */
	var explicitHasMissAnimations:Null<Bool> = null;
	@:keep public var hasMissAnimations(get, set):Bool;
	@:keep function get_hasMissAnimations():Bool {
		if (explicitHasMissAnimations != null) return explicitHasMissAnimations == true;
		return hasAnimation('singLEFTmiss') || hasAnimation('singDOWNmiss')
			|| hasAnimation('singUPmiss') || hasAnimation('singRIGHTmiss');
	}
	@:keep function set_hasMissAnimations(value:Bool):Bool {
		explicitHasMissAnimations = value;
		return value;
	}

	public function isSinging():Bool {
		return Character.animationName(this).startsWith('sing');
	}

	/** Shared HXC alias used by character dance/animation overrides. */
	public function isAnimationFinished():Bool {
		return animation != null && animation.curAnim != null && animation.curAnim.finished;
	}

	/** Restore the actor to the donor's recorded starting position. */
	public function resetPosition(?_force:Bool = false):Void {
		if (originalPosition == null)
			originalPosition = FlxPoint.get(x, y);
		setPosition(originalPosition.x, originalPosition.y);
	}

	/** Capture the native placement as the donor-visible starting position. */
	public function syncHxcPosition():Void {
		if (originalPosition == null)
			originalPosition = FlxPoint.get();
		originalPosition.set(x, y);
	}

	/** Return the native Bopper-equivalent base without re-entering HXC hooks. */
	public function hxcBaseScreenPosition(?result:FlxPoint, ?camera:FlxCamera):FlxPoint {
		return applyVSliceScreenOffset(super.getScreenPosition(result, camera));
	}

	function applyVSliceScreenOffset(output:FlxPoint):FlxPoint {
		if (vSliceBaseFrames != null) {
			// Bopper offsets its rendered position, leaving FlxSprite.offset's
			// scaled hitbox alignment intact. CharacterData's global offsets are
			// separate from native role placement and repositioning fields.
			output.x -= VSliceCharacterGeometry.screenShift(getCurrentAnimationOffset(0), vSliceGlobalOffsetX, scale.x);
			output.y -= VSliceCharacterGeometry.screenShift(getCurrentAnimationOffset(1), vSliceGlobalOffsetY, scale.y);
		}
		return output;
	}

	/**
		Preserve the native screen coordinate calculation, then let an active HXC
		character companion apply its authored visual offset convention.
	*/
	override public function getScreenPosition(?result:FlxPoint, ?camera:FlxCamera):FlxPoint {
		var output = hxcBaseScreenPosition(result, camera);
		if (PlayState.instance != null) {
			var routed = PlayState.instance.dispatchHxcCharacterScreenPosition(this, output, camera);
			if (routed != null)
				output = routed;
		}
		return output;
	}

	/** The pinned Codename Flixel fork translates frameOffset before sprite
	 * scale, angle, and skew. FlxAnimate uses this for draw and bounds. */
	override function prepareDrawMatrix(matrix:FlxMatrix, camera:FlxCamera):Void {
		if (codenameLiveDefinition != null) {
			if (frameOffsetAngle != null && frameOffsetAngle != angle) {
				var radians = (frameOffsetAngle - angle) * FlxAngle.TO_RAD;
				var cosine = Math.cos(radians);
				var sine = Math.sin(radians);
				matrix.rotateWithTrig(cosine, -sine);
				matrix.translate(-frameOffset.x, -frameOffset.y);
				matrix.rotateWithTrig(cosine, sine);
			} else matrix.translate(-frameOffset.x, -frameOffset.y);
		}
		super.prepareDrawMatrix(matrix, camera);
	}

	override public function isSimpleRender(?camera:FlxCamera):Bool {
		return codenameLiveDefinition != null ? false : super.isSimpleRender(camera);
	}

	/** Active animation offset for the donor `animOffsets[0/1]` convention. */
	public function getCurrentAnimationOffset(index:Int):Float {
		var offsets = animOffsets == null ? null : animOffsets.get(getCurrentAnimation());
		if (offsets == null || index < 0 || index >= offsets.length || offsets[index] == null)
			return 0;
		var value = Std.parseFloat(Std.string(offsets[index]));
		return Math.isNaN(value) ? 0 : value;
	}

	/** Active V-Slice CharacterData offset for the donor `globalOffsets[0/1]`
	 * convention. */
	public function getCurrentGlobalOffset(index:Int):Float {
		if (index == 0)
			return vSliceGlobalOffsetX;
		if (index == 1)
			return vSliceGlobalOffsetY;
		return 0;
	}

	/** Older generated V-Slice scripts stored CharacterData.offsets only in
	 * the role offset fields. Snapshot those values after init, before a stage
	 * can change placement, so existing imports retain their authored render
	 * offsets without rewriting their files. */
	function captureLegacyVSliceGlobalOffsets():Void {
		if (vSliceBaseFrames == null || vSliceGlobalOffsetsAuthored)
			return;
		vSliceGlobalOffsetX = playerOffsetX;
		vSliceGlobalOffsetY = playerOffsetY;
	}

	/**
		Load a literal Sparrow animation bundle emitted by the HXC compatibility
		adapter. The function accepts data only: it never executes a donor utility
		class and keeps all frame/animation ownership on the native Character.
	*/
	public function addHxcAtlasAnimations(assetPath:String, animations:Array<Dynamic>,
		offsetX:Float = 0, offsetY:Float = 0, ?assetRoot:String = ''):Void {
		if (animations == null)
			return;
		var loaded:Map<String, Bool> = new Map<String, Bool>();
		if (assetPath != null && StringTools.trim(assetPath) != '')
			loaded.set(StringTools.trim(assetPath), loadHxcAtlas(assetPath, assetRoot));
		for (spec in animations) {
			if (spec == null)
				continue;
			var path = Reflect.field(spec, 'assetPath');
			var resolvedPath = path == null || StringTools.trim(Std.string(path)) == ''
				? assetPath : StringTools.trim(Std.string(path));
			if (resolvedPath != null && resolvedPath != '' && !loaded.exists(resolvedPath))
				loaded.set(resolvedPath, loadHxcAtlas(resolvedPath, assetRoot));
			var name = Reflect.field(spec, 'name');
			var prefix = Reflect.field(spec, 'prefix');
			if (name == null || prefix == null)
				continue;
			var animationName = Std.string(name);
			var animationPrefix = Std.string(prefix);
			if (animationName == '' || animationPrefix == '')
				continue;
			var fps = Reflect.field(spec, 'fps');
			var frameRate = fps == null ? 24 : Std.parseFloat(Std.string(fps));
			if (Math.isNaN(frameRate) || frameRate <= 0)
				frameRate = 24;
			var looped = Reflect.field(spec, 'looped');
			if (looped == null)
				looped = Reflect.field(spec, 'loop');
			var flipAnimationX = Reflect.field(spec, 'flipX') == true;
			var flipAnimationY = Reflect.field(spec, 'flipY') == true;
			var kind = Reflect.field(spec, 'kind');
			var indices:Dynamic = Reflect.field(spec, 'indices');
			if (kind == 'indices' && indices != null && Std.isOfType(indices, Array))
				animation.addByIndices(animationName, animationPrefix, cast indices, '', frameRate,
					looped == true);
			else
				animation.addByPrefix(animationName, animationPrefix, frameRate, looped == true,
					flipAnimationX, flipAnimationY);
			var offsets:Dynamic = Reflect.field(spec, 'offsets');
			var x = offsetX;
			var y = offsetY;
			if (offsets != null && Std.isOfType(offsets, Array)) {
				var values:Array<Dynamic> = cast offsets;
				if (values.length > 0 && values[0] != null)
					x += Std.parseFloat(Std.string(values[0]));
				if (values.length > 1 && values[1] != null)
					y += Std.parseFloat(Std.string(values[1]));
			}
			setAnimationOffsets(animationName, x, y);
		}
	}

	function loadHxcAtlas(assetPath:String, ?assetRoot:String = ''):Bool {
		if (assetPath == null || StringTools.trim(assetPath) == '')
			return false;
		try {
			var atlas:Dynamic;
			if (assetRoot != null && StringTools.trim(assetRoot) != '') {
				// Imported HXC assets stay inside the manifest root.  Do not fall
				// back to global Paths here: a missing donor atlas must be a safe
				// no-op rather than a cross-root lookup.
				atlas = HxcStateAssetScope.sparrowAtlas(assetRoot, assetPath, null,
					'HXC character atlas');
			} else {
				atlas = DynamicSprite.DynamicAtlasFrames.fromSparrow(
					Paths.image(assetPath), Paths.file('images/' + assetPath + '.xml'));
			}
			if (atlas == null)
				return false;
			if (frames == null)
				frames = atlas;
			else if (Std.isOfType(frames, FlxAtlasFrames))
				(cast frames:FlxAtlasFrames).addAtlas(atlas);
			else
				frames = atlas;
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** HXC's animation call includes an ignoreOther flag which this fork does
	 * not need; retaining the parameter keeps donor callbacks source-compatible. */
	/** V-Slice character script variables belong to this actor's live companion. */
	@:keep public function scriptGet(name:String):Dynamic
		return PlayState.instance == null ? null : PlayState.instance.hxcCharacterScriptField(this, name);

	@:keep public function scriptSet(name:String, value:Dynamic):Void {
		if (PlayState.instance != null)
			PlayState.instance.hxcCharacterScriptField(this, name, true, value);
	}

	/** Source character identity stays independent of the import's storage root. */
	@:keep public var characterId(get, never):String;
	@:keep function get_characterId():String return curCharacter;

	/** Return-valued V-Slice character hook, queried by the native game-over host. */
	@:keep public function getDeathQuote():Null<String>
		return PlayState.instance == null ? null : PlayState.instance.hxcCharacterDeathQuote(this);

	public function playAnimation(name:String, restart:Bool = false, ignoreOther:Bool = false,
		reversed:Bool = false):Void {
		playAnim(name, restart, reversed);
	}

	/** HXC's `playSingAnimation` accepts a suffix such as `alt`; map it to the
	 * fork's `singLEFT-alt`/`singRIGHT-alt` animation naming convention. */
	@:keep public function playSingAnimation(direction:Int, miss:Bool = false, ?suffix:String = ''):Void {
		var baseName = switch (direction % 4) {
			case 0: 'singLEFT';
			case 1: 'singDOWN';
			case 2: 'singUP';
			case 3: 'singRIGHT';
			default: '';
		};
		var cleanSuffix = suffix == null ? '' : StringTools.trim(suffix);
		var candidate = baseName + (miss ? 'miss' : '')
			+ (cleanSuffix == '' ? '' : '-' + cleanSuffix);
		if (candidate != '' && animation != null && animation.exists(candidate))
			playAnim(candidate, true);
		else
			sing(direction, miss);
	}

	/** Common donor helper used by imported game-over character scripts. */
	public function getDataFlipX():Bool {
		return flipX;
	}

	/** Remember the frames created by a generated V-Slice character script.
	 * Alternate animation assets are loaded lazily and this collection is the
	 * canonical frame set to restore when the next animation uses the primary
	 * atlas. */
	public function rememberVSliceBaseFrames():Void {
		vSliceBaseFrames = frames;
		vSliceActiveAnimationAsset = '';
	}

	/**
	 * Register one animation's source atlas.  An empty png path means that the
	 * animation belongs to the primary atlas; non-empty paths are loaded on
	 * demand.  Rebuilding only the animation being played keeps all foreign
	 * prefixes/indices intact when V-Slice switches between its authored atlases.
	 */
	public function registerVSliceAnimationAsset(name:String, pngPath:String, ?xmlPath:String,
		?prefix:String, ?indices:Array<Int>, ?fps:Float = 24, ?loop:Bool = false,
		?txtPath:String = ''):Void {
		if (name == null || StringTools.trim(name) == '')
			return;
		var key = name.toLowerCase();
		vSliceAnimationAssets.set(key, {
				png: pngPath == null ? '' : pngPath,
				xml: xmlPath == null ? '' : xmlPath,
				txt: txtPath == null ? '' : txtPath,
				prefix: prefix == null ? '' : prefix,
			indices: indices == null ? [] : indices.copy(),
			fps: fps == null || fps <= 0 ? 24 : fps,
			loop: loop == true
		});
	}

	function loadVSliceAnimationFrames(spec:Dynamic, key:String):FlxFramesCollection {
		if (spec == null)
			return vSliceBaseFrames;
		if (vSliceAnimationFrames.exists(key))
			return vSliceAnimationFrames.get(key);
		var png = Std.string(Reflect.field(spec, 'png'));
		var xml = Std.string(Reflect.field(spec, 'xml'));
		var txt = Std.string(Reflect.field(spec, 'txt'));
		if (png == null || StringTools.trim(png) == '')
			return vSliceBaseFrames;
		var loaded:FlxFramesCollection = null;
		try {
			if (xml != null && StringTools.trim(xml) != '')
				loaded = FlxAtlasFrames.fromSparrow(png, xml);
			else if (txt != null && StringTools.trim(txt) != '')
				loaded = DynamicSprite.DynamicAtlasFrames.fromSpriteSheetPacker(png, txt);
			else {
				var sprite = new FlxSprite();
				sprite.loadGraphic(png);
				loaded = sprite.frames;
				sprite.destroy();
			}
		} catch (_:Dynamic) {
			loaded = null;
		}
		if (loaded != null)
			vSliceAnimationFrames.set(key, loaded);
		return loaded == null ? vSliceBaseFrames : loaded;
	}

	function applyVSliceAnimationAsset(name:String):Void {
		if (name == null)
			return;
		var key = name.toLowerCase();
		var spec:Dynamic = vSliceAnimationAssets.exists(key) ? vSliceAnimationAssets.get(key) : null;
		var targetFrames = loadVSliceAnimationFrames(spec, key);
		if (targetFrames == null)
			return;
		// A swapped-in character can outlive the collection captured as its base
		// (the old instance is destroyed on Change Character). Assigning an
		// unusable collection trips a null-frame deref inside flixel's setter,
		// so keep the current visual and say so once instead of crashing
		// mid-song.
		if (targetFrames.numFrames <= 0 || targetFrames.getByIndex(0) == null) {
			if (!vSliceBrokenAssetWarned) {
				vSliceBrokenAssetWarned = true;
				trace('[vslice-anim-asset] ' + requestedCharacter + ': animation "' + name
					+ '" target atlas has no usable frames; keeping the current sheet');
			}
			return;
		}
		var targetAsset = spec == null ? '' : Std.string(Reflect.field(spec, 'png'));
		if (targetAsset == null)
			targetAsset = '';
		if (frames != targetFrames || vSliceActiveAnimationAsset != targetAsset) {
			frames = targetFrames;
			vSliceActiveAnimationAsset = targetAsset;
			// FlxAnimation stores frame indices from the collection active when it
			// was added. Re-add this one animation after switching collections so
			// a foreign atlas cannot inherit stale indices from the main atlas.
			animation.remove(name);
			var prefix = spec == null ? '' : Std.string(Reflect.field(spec, 'prefix'));
			var indices:Dynamic = spec == null ? [] : Reflect.field(spec, 'indices');
			var fps:Float = spec == null ? 24 : Std.parseFloat(Std.string(Reflect.field(spec, 'fps')));
			if (Math.isNaN(fps) || fps <= 0)
				fps = 24;
			var loop = spec != null && Reflect.field(spec, 'loop') == true;
			if (indices != null && Std.isOfType(indices, Array) && (cast indices:Array<Int>).length > 0)
				animation.addByIndices(name, prefix, cast indices, '', fps, loop);
			else if (prefix != '')
				animation.addByPrefix(name, prefix, fps, loop);
		}
	}

	public function usesPixelAssets():Bool {
		return isPixel || (interp != null && interp.variables.exists("isPixel") && interp.variables.get("isPixel") == true);
	}

	public static function isNoGirlfriend(character:String):Bool {
		if (character == null)
			return false;
		var value = StringTools.replace(StringTools.replace(character.trim(), '_', '-'), ' ', '');
		return value.toLowerCase() == 'no-gf' || value.toLowerCase() == 'nogf';
	}

	function set_stunned(value:Bool):Bool {
		codenameStunnedTime = 0;
		return stunned = value;
	}
	function get_stunned():Bool {
		if (codenameLiveDefinition != null) return stunned;
		if (OptionsHandler.options.useMissStun)
			return stunned;
		return false;
	}
	function callInterp(func_name:String, args:Array<Dynamic>) {
		if (interp == null) return;
		if (!interp.variables.exists(func_name)) return;
		var method = interp.variables.get(func_name);
		switch (args.length) {
			case 0:
				method();
			case 1:
				method(args[0]);
			case 2:
				method(args[0], args[1]);
			case 4:
				method(args[0], args[1], args[2], args[3]);
		}
	}

	/** Construct a Nightmare Vision character directly from its source JSON. */
	function loadNightmareVisionCharacterVisual(definition:Dynamic, imageRoot:String, ownerRoot:String):Bool {
		#if sys
		if (definition == null || imageRoot == null || StringTools.trim(imageRoot) == ''
			|| ownerRoot == null || StringTools.trim(ownerRoot) == '')
			return false;
		try {
			var ownerImages = ownerRoot + '/images/';
			var coreImages = ownerRoot + '/__nmv_core/images/';
			var ownerPaths = new NightmareVisionPaths(ownerRoot);
			var atlasRoots = imageRoot.split(',');
			var atlases:Array<FlxAtlasFrames> = [];
			var animateAtlas = false;
			for (authoredRoot in atlasRoots) {
				var atlasRoot = StringTools.trim(authoredRoot);
				var atlasKey:String;
				var checkOwner:Bool;
				if (StringTools.startsWith(atlasRoot, ownerImages)) {
					atlasKey = atlasRoot.substr(ownerImages.length);
					checkOwner = true;
				} else if (StringTools.startsWith(atlasRoot, coreImages)) {
					atlasKey = atlasRoot.substr(coreImages.length);
					checkOwner = false;
				} else
					return false;

				var atlas = ownerPaths.getTextureAtlas(atlasKey, null, true, checkOwner);
				if (atlas == null)
					return false;
				var hasAnimateManifest = FileSystem.exists(atlasRoot + '/Animation.json');
				var hasSparrowFiles = FileSystem.exists(atlasRoot + '.png')
					&& FileSystem.exists(atlasRoot + '.xml');
				if (!hasAnimateManifest && !hasSparrowFiles)
					return false;
				animateAtlas = animateAtlas || hasAnimateManifest;
				atlases.push(atlas);
			}
			if (atlases.length == 0)
				return false;
			frames = atlases.length == 1 ? atlases[0] : FlxAnimateFrames.combineAtlas(atlases);
			if (frames == null)
				return false;

			var authoredAnimations:Dynamic = Reflect.field(definition, 'animations');
			if (!Std.isOfType(authoredAnimations, Array))
				return false;
			var loadedAnimations = 0;
			for (spec in (cast authoredAnimations:Array<Dynamic>)) {
				if (spec == null)
					continue;
				var rawAnimationName = Reflect.field(spec, 'anim');
				var rawPrefix = Reflect.field(spec, 'name');
				var animationName = rawAnimationName == null ? '' : StringTools.trim(Std.string(rawAnimationName));
				var prefix = rawPrefix == null ? '' : StringTools.trim(Std.string(rawPrefix));
				if (animationName == '')
					continue;
				var fps = nightmareVisionNumber(Reflect.field(spec, 'fps'), 24);
				if (fps <= 0)
					fps = 24;
				var loop = Reflect.field(spec, 'loop') == true;
				var indices:Array<Int> = [];
				var rawIndices:Dynamic = Reflect.field(spec, 'indices');
				if (Std.isOfType(rawIndices, Array))
					for (rawIndex in (cast rawIndices:Array<Dynamic>)) {
						var index = nightmareVisionNumber(rawIndex, Math.NaN);
						if (!Math.isNaN(index))
							indices.push(Std.int(index));
					}

				if (animateAtlas) {
					if (prefix == '')
						continue;
					var flipAnimationX:Dynamic = Reflect.field(spec, 'flipX');
					var flipAnimationY:Dynamic = Reflect.field(spec, 'flipY');
					var registered = false;
					var findFrameLabels = Reflect.field(animation, 'findFrameLabelIndices');
					var frameLabels:Dynamic = findFrameLabels == null ? null
						: Reflect.callMethod(animation, findFrameLabels, [prefix]);
					if (Std.isOfType(frameLabels, Array) && (cast frameLabels:Array<Int>).length > 0) {
						var addByFrameLabel = Reflect.field(animation, indices.length > 0
							? 'addByFrameLabelIndices' : 'addByFrameLabel');
						if (addByFrameLabel != null) {
							var labelArgs:Array<Dynamic> = indices.length > 0
								? [animationName, prefix, indices, fps, loop, flipAnimationX, flipAnimationY]
								: [animationName, prefix, fps, loop, flipAnimationX, flipAnimationY];
							Reflect.callMethod(animation, addByFrameLabel, labelArgs);
							registered = animation.exists(animationName);
						}
					}
					// Nightmare Vision's Animate API treats `name` as a frame-label
					// prefix first, then as a nested symbol name.
					if (!registered && indices.length > 0) {
						var addBySymbolIndices = Reflect.field(animation, 'addBySymbolIndices');
						if (addBySymbolIndices != null)
							Reflect.callMethod(animation, addBySymbolIndices,
								[animationName, prefix, indices, fps, loop, flipAnimationX, flipAnimationY]);
					} else if (!registered) {
						var addBySymbol = Reflect.field(animation, 'addBySymbol');
						if (addBySymbol != null)
							Reflect.callMethod(animation, addBySymbol,
								[animationName, prefix, fps, loop, flipAnimationX, flipAnimationY]);
					}
					if (!animation.exists(animationName))
						continue;
				} else if (indices.length > 0 && prefix == '')
					animation.add(animationName, indices, fps, loop);
				else if (indices.length > 0)
					animation.addByIndices(animationName, prefix, indices, '', fps, loop);
				else if (prefix != '')
					animation.addByPrefix(animationName, prefix, fps, loop);
				else
					continue;

				if (!animation.exists(animationName))
					continue;
				loadedAnimations++;
				var offsets:Array<Float> = nightmareVisionPair(Reflect.field(spec, 'offsets'));
				animOffsets.set(animationName, [offsets[0], offsets[1]]);
				var cameraOffset:Dynamic = Reflect.field(spec, 'cameraOffset');
				if (cameraOffset != null) {
					var camera:Array<Float> = nightmareVisionPair(cameraOffset);
					camOffsets.set(animationName, [camera[0], camera[1]]);
				}
			}
			if (loadedAnimations == 0)
				return false;

			var authoredScale = nightmareVisionNumber(Reflect.field(definition, 'scale'), 1);
			if (authoredScale > 0 && authoredScale != 1) {
				scale.set(authoredScale, authoredScale);
				updateHitbox();
			}
			flipX = PsychCharacterOrientation.flipX(Reflect.field(definition, 'flip_x') == true, isPlayer);
			antialiasing = Reflect.field(definition, 'no_antialiasing') != true;
			this.cameraPosition = nightmareVisionPair(Reflect.field(definition, 'camera_position'));
			var singDuration = nightmareVisionNumber(Reflect.field(definition, 'sing_duration'), holdTime);
			if (singDuration > 0)
				holdTime = singDuration;
			var danceEvery = nightmareVisionNumber(Reflect.field(definition, 'dance_every'), beatInterval);
			if (danceEvery >= 0) {
				this.danceEvery = Std.int(danceEvery);
				beatInterval = this.danceEvery;
			}
			var position:Array<Float> = nightmareVisionPair(Reflect.field(definition, 'position'));
			positionArray = [position[0], position[1]];
			enemyOffsetX = playerOffsetX = gfOffsetX = Std.int(Math.round(position[0]));
			enemyOffsetY = playerOffsetY = gfOffsetY = Std.int(Math.round(position[1]));
			loadNightmareVisionHealthColors(definition);
			return true;
		} catch (error:Dynamic) {
			trace('[nightmare-vision-character-init-error] ' + curCharacter + ': ' + Std.string(error));
			return false;
		}
		#else
		return false;
		#end
	}

	static function nightmareVisionNumber(value:Dynamic, fallback:Float):Float {
		if (value == null)
			return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? fallback : parsed;
	}

	static function nightmareVisionPair(value:Dynamic):Array<Float> {
		if (!Std.isOfType(value, Array) || (cast value:Array<Dynamic>).length < 2)
			return [0, 0];
		var pair:Array<Dynamic> = cast value;
		return [nightmareVisionNumber(pair[0], 0), nightmareVisionNumber(pair[1], 0)];
	}

	/** Read only the selected Psych owner's authored position metadata.  The
	 * stage-position resolver separately applies native/base fallbacks when it
	 * computes placement; scripts see the source pair (or the neutral default). */
	static function psychCharacterPositionArray(id:String, scopedRoot:String):Array<Float> {
		var name = id == null ? '' : StringTools.trim(id);
		if (name == '' || !~/^[A-Za-z0-9_-]+$/.match(name)
			|| scopedRoot == null || StringTools.trim(scopedRoot) == '')
			return [0, 0];
		for (folder in ['characters', 'shared/characters']) {
			var path = scopedRoot + '/' + folder + '/' + name + '.json';
			if (!FNFAssets.exists(path))
				continue;
			try {
				var definition:Dynamic = CoolUtil.parseJson(FNFAssets.getText(path));
				var authored = PsychCharacterPosition.point(Reflect.field(definition, 'position'));
				if (authored != null)
					return authored;
			} catch (_:Dynamic) {}
		}
		return [0, 0];
	}

	public function new(x:Float, y:Float, ?character:String = "bf", ?isPlayer:Bool = false, ?codename:CodenameCharacterConstruction) {
		animOffsets = new Map<String, Array<Dynamic>>();
		camOffsets = new Map<String, Array<Dynamic>>();
		super(x, y);
		onAnimationFinish = new FlxSignal();
		animation.onFinish.add(function(_animationName:String):Void onAnimationFinish.dispatch());
		markDeathConstructionStage('base');
		characterOrigin = FlxPoint.get();
		cameraFocusPoint = FlxPoint.get(x + followCamX, y + followCamY);
		originalPosition = FlxPoint.get(x, y);

		curCharacter = character;
		this.isPlayer = isPlayer;
		healthColorArray = nightmareVisionColorArrayFromPacked(healthColour);
		characterType = isPlayer ? 'bf' : 'dad';
		requestedCharacter = codename == null
			? (curCharacter == null ? '' : curCharacter.trim()) : codename.authoredId;
		var hiddenGirlfriend = Character.isNoGirlfriend(curCharacter);
		if (hiddenGirlfriend)
			curCharacter = 'gf';

		var tex:FlxAtlasFrames; // might be useful for sprite preloading, keep for now
		antialiasing = true;

		curCharacter = curCharacter.trim();
		trace(curCharacter);
		if (StringTools.endsWith(curCharacter, "-dead")) {
			isDie = true;
			curCharacter = curCharacter.substr(0, curCharacter.length - 5);
		}
		markDeathConstructionStage('identity');
		// Codename separates the actor's stage-slot flip (`isPlayer`) from the
		// character definition's `playerOffsets` convention. Only read this
		// adapter metadata while its selected Codename owner is active.
		var codenameCharacterMeta:Dynamic = null;
		if (PlayState.instance != null && FlxG.state == PlayState.instance && PlayState.SONG != null) {
			var codenameRoot = Song.characterRootForSong(Song.storageFolder(PlayState.SONG),
				ImportEngine.CODENAME);
			if (codenameRoot != '') {
				var codenameRow = Song.characterVisualRegistryEntryInManifest(curCharacter, codenameRoot);
				if (codenameRow != null)
					codenameCharacterMeta = Reflect.field(codenameRow, 'codenameCharacter');
				if (codenameCharacterMeta != null && (codename == null || codename.nativeName != curCharacter))
					flipX = Reflect.field(codenameCharacterMeta, 'flipX') == true;
			}
		}
		var nightmareVisionOwnerRoot = '';
		var nightmareVisionOwnedCharacter:Dynamic = null;
		if (PlayState.instance != null && FlxG.state == PlayState.instance && PlayState.SONG != null) {
			nightmareVisionOwnerRoot = Song.characterRootForSong(Song.storageFolder(PlayState.SONG),
				ImportEngine.NIGHTMARE_VISION);
			if (nightmareVisionOwnerRoot != '')
				nightmareVisionOwnedCharacter = NightmareVisionCharacterData.load(nightmareVisionOwnerRoot, curCharacter);
		}
		var nightmareVisionCharacterOwned = nightmareVisionOwnerRoot != ''
			&& nightmareVisionOwnedCharacter != null;
		if (nightmareVisionCharacterOwned)
			nightmareVisionHealthIcon = nightmareVisionHealthIconFromDefinition(nightmareVisionOwnedCharacter);
		var psychCameraRoot = Song.currentPsychCharacterRoot();
		positionArray = psychCharacterPositionArray(curCharacter, psychCameraRoot);
		// Psych keeps direction animation names and their named offsets authored
		// on the character. Its JSON is preserved under the selected song owner,
		// so existing imports can use Psych's slot flip without re-importing.
		var psychAuthoredFlipX:Null<Bool> = PsychCharacterOrientation.authoredFlipX(curCharacter,
			psychCameraRoot, function(path:String):Null<String> return FNFAssets.exists(path) ? FNFAssets.getText(path) : null);
		cameraPosition = psychCameraRoot == null || StringTools.trim(psychCameraRoot) == '' ? [0, 0]
			: PsychCharacterPosition.characterCameraPosition(curCharacter, psychCameraRoot);
		// Keep the authored id on the Character even when the resolver chooses a
		// complete sibling/alias visual.  Only the interpreter's asset root is
		// substituted; mutating curCharacter here loses chart identity and made
		// incomplete Popipo-style aliases look like an ordinary Dad chart.
		var visualResolution:Dynamic = Song.resolveCharacterVisualForCurrentSong(curCharacter);
		markDeathConstructionStage('visual-resolution');
		if (nightmareVisionCharacterOwned) {
			var nightmareVisionImageRoot = NightmareVisionCharacterData.imageRoot(nightmareVisionOwnerRoot,
				nightmareVisionOwnedCharacter);
			if (nightmareVisionImageRoot != null) {
				if (loadNightmareVisionCharacterVisual(nightmareVisionOwnedCharacter, nightmareVisionImageRoot,
					nightmareVisionOwnerRoot)) {
					resolvedCharacter = curCharacter;
					resolvedImplementation = curCharacter;
					resolvedAssetRoot = nightmareVisionImageRoot;
				} else if (visualResolution != null) {
					visualResolution.complete = false;
					visualResolution.diagnosticCode = 'nightmare-vision-character-atlas-load-failed';
					visualResolution.diagnostic = 'Nightmare Vision character "' + curCharacter
						+ '" definition loaded, but its atlas animations could not be initialized.';
				}
			}
		}
		if (visualResolution.complete) {
			resolvedCharacter = visualResolution.selectedRegistryName == null
				? curCharacter : Std.string(visualResolution.selectedRegistryName);
			resolvedImplementation = visualResolution.implementationName == null
				? '' : Std.string(visualResolution.implementationName);
			resolvedAssetRoot = visualResolution.assetRootPath == null
				? '' : Std.string(visualResolution.assetRootPath);
		}
		trace(curCharacter);
		var isError:Bool = false;
		if (codename != null && codename.nativeName == curCharacter) {
			try {
				if (codename.usedSourceFallback)
					trace('[codename-character-source-fallback] Requested "' + codename.authoredId
						+ '" uses Codename DEFAULT_CHARACTER "' + codename.sourceDefinitionId + '"'
						+ (codename.configuredSourceFallback ? ' from owner flags' : ' (engine default)')
						+ '; authored identity is preserved.');
				CodenameCharacterVisual.initializeSourceDefaults(this);
				codenameSourceId = codename.authoredId;
				xml = new CodenameXmlAccess(Xml.parse(codename.xmlText).firstElement());
				codenameRuntime = codename.createRuntime(this);
				codenameVisualBuilding = true;
				codenameBuildingAnimations = [];
				codenameRuntime.call('create', []);
				var event = new CodenameCharacterEvent();
				event.character = this;
				event.xml = xml;
				codenameRuntime.event('onCharacterXMLParsed', event);
				xml = event.xml;
				var builtCodenameDefinition = CodenameCharacterVisual.build(this, codename.authoredId,
					xml.x, new CodenamePaths(codename.root, codename.assetRoot,
						codename.fallbackAssetFiles), function(node:Xml):Void {
						var event = new CodenameCharacterEvent();
						event.character = this;
						event.node = new CodenameXmlAccess(node);
						event.name = node.nodeName;
						codenameRuntime.event('onCharacterNodeParsed', event);
					}, function(name:String, forced:Bool):Void {
						codenamePlayAnim(name, forced, null);
					}, codenameBuildingAnimations, codename.sourceDefinitionId);
				codenameVisualBuilding = false;
				codenameBuildingAnimations = null;
				codenameLiveDefinition = builtCodenameDefinition;
				for (message in (cast codenameLiveDefinition.diagnostics:Array<String>))
					trace('[codename-character-visual] ' + codename.authoredId + ': ' + message);
				for (key in Reflect.fields(codenameLiveDefinition.extra))
					extra.set(key, Reflect.field(codenameLiveDefinition.extra, key));
				if (codenameLiveDefinition.interval == null
					&& animation.exists('danceLeft') && animation.exists('danceRight')) beatInterval = 1;
				cameraPosition = [cameraOffset.x, cameraOffset.y];
				codenameCharacterMeta = {playerOffsets:playerOffsets};
			} catch (error:Dynamic) {
				trace('[codename-character-construction] ' + codename.authoredId + ': ' + Std.string(error));
				codenameVisualBuilding = false;
				codenameBuildingAnimations = null;
				if (codenameRuntime != null) codenameRuntime.destroy();
				codenameRuntime = null;
				codenameLiveDefinition = null;
			}
		}
		// Source-backed Codename definitions are constructed after the merged
		// registry lookup. Report a missing character only if both paths failed.
		if (!visualResolution.complete && !isDie && codenameLiveDefinition == null)
			Character.reportResolution(visualResolution);
		if (codenameLiveDefinition == null && !nightmareVisionCharacterOwned) {
			markDeathConstructionStage('before-character-interpreter');
			interp = Character.getAnimInterp(curCharacter);
			markDeathConstructionStage('after-character-interpreter');
		}
		// An imported character script may reference media the donor never
		// shipped. Its failure must degrade to whatever visual already loaded -
		// flixel's empty-frame fallback covers drawing - instead of ending the
		// whole song during create().
		markDeathConstructionStage('before-script-init');
		try callInterp("init", [this]) catch (error:Dynamic)
			trace('[hxc-character-init-error] ' + requestedCharacter + ': ' + Std.string(error));
		markDeathConstructionStage('after-script-init');
		markDeathConstructionStage('before-legacy-offsets');
		captureLegacyVSliceGlobalOffsets();
		markDeathConstructionStage('after-legacy-offsets');
		if (psychAuthoredFlipX != null)
			flipX = PsychCharacterOrientation.flipX(psychAuthoredFlipX, isPlayer);
		// Older Psych imports placed a generated visual in the global character
		// folder but retained the donor's JSON under the selected owner. Repair
		// only an exact generated-script match before dance() sets its authored
		// animation offset; otherwise the camera uses an unscaled midpoint.
		if (PsychCharacterDanceCompat.needsOwnedLegacyHitbox(curCharacter, psychCameraRoot,
			visualResolution == null || visualResolution.implementationPath == null
				? '' : Std.string(visualResolution.implementationPath),
			scale.x, scale.y, frameWidth, frameHeight, width, height,
			function(path:String):Null<String> return FNFAssets.exists(path) ? FNFAssets.getText(path) : null))
			updateHitbox();
		markDeathConstructionStage('before-codename-orientation');
		applyCodenameCharacterOrientation(codenameCharacterMeta);
		markDeathConstructionStage('after-codename-orientation');
		if (codenameLiveDefinition != null) codenameBaseFlipped = flipX;
		stageBaseScaleX = scale.x;
		stageBaseScaleY = scale.y;
		stageBaseFlipX = flipX;
		var graphicKey = graphic == null ? null : graphic.key;
		markDeathConstructionStage('before-image-resolution');
		imageFile = PsychCharacterImage.resolve(graphicKey, resolvedAssetRoot);
		markDeathConstructionStage('after-image-resolution');
		markDeathConstructionStage('before-dance');
		dance();
		markDeathConstructionStage('after-dance');
		// Donor BaseCharacter resets to its dance pose before sizing the hitbox.
		// Imported V-Slice adapters may have sized an atlas's first (sing) frame
		// during init, so measure the idle pose before Stage anchors its feet.
		if (vSliceBaseFrames != null) updateHitbox();

		if (codenameCharacterMeta == null && psychAuthoredFlipX == null
			&& !nightmareVisionCharacterOwned && isPlayer && !noFlip) {
			flipX = !flipX;
			// Doesn't flip for BF, since his are already in the right place???
			// V-Slice keeps its authored direction names and changes only the slot flip.
			if (!likeBf && vSliceBaseFrames == null && !isDie) {
				var getFrames = function(name:String):Array<Int> {
					var anim = animation.getByName(name);
					return anim == null ? null : anim.frames;
				};
				var setFrames = function(name:String, frames:Array<Int>):Void {
					var anim = animation.getByName(name);
					if (anim != null) anim.frames = frames;
				};
				// Keep authored offsets with the source animation when its direction
				// frame list is reassigned for the player-facing slot.
				CharacterAnimationOrientation.swapAll(animation.getNameList(), getFrames, setFrames, animOffsets);
			}
		}
		if (hiddenGirlfriend) {
			isHiddenCharacter = true;
			visible = false;
			alpha = 0;
			canSing = false;
		}
		// Character scripts have finished their init/dance setup at this point.
		// Later stage/song callbacks may still move followCamX/Y; the Psych
		// compatibility path keeps those later edits as a delta from this value.
		if (codenameLiveDefinition != null) {
			codenameRuntime.call('postCreate', []);
			stageBaseScaleX = scale.x;
			stageBaseScaleY = scale.y;
			stageBaseFlipX = flipX;
			cameraPosition = [cameraOffset.x, cameraOffset.y];
		}
		psychInitialFollowCamX = followCamX;
		psychInitialFollowCamY = followCamY;
		markDeathConstructionStage('complete');
	}
	function applyCodenameCharacterOrientation(codenameCharacterMeta:Dynamic):Void {
		if (codenameCharacterMeta == null) return;
		var playerOffsets = Reflect.field(codenameCharacterMeta, 'playerOffsets') == true;
		// GameOverSubstate constructs imported death actors through the legacy
		// character-script path, so owner metadata can exist without a live
		// Codename XML definition. In that case use the animations actually
		// installed by the generated script instead of dereferencing a missing
		// definition or skipping Codename's slot orientation.
		var authoredAnimationNames:Array<String> = animation.getNameList();
		if (codenameLiveDefinition != null) {
			var codenameAnimations:Array<Dynamic> = cast Reflect.field(codenameLiveDefinition, 'animations');
			if (codenameAnimations != null) {
				authoredAnimationNames = [];
				for (entry in codenameAnimations) {
					var animationName:Dynamic = Reflect.field(entry, 'name');
					if (animationName != null) authoredAnimationNames.push(cast animationName);
				}
			}
		}
		flipX = CodenameCharacterOrientation.apply(isPlayer, playerOffsets, flipX,
			authoredAnimationNames,
			function(name:String):Array<Int> {
				var anim = animation.getByName(name);
				return anim == null ? null : anim.frames;
			},
			function(name:String, frames:Array<Int>):Void {
				var anim = animation.getByName(name);
				if (anim != null) anim.frames = frames;
			}, animOffsets);
	}
	/** Smoke-only breadcrumbs delimit imported death-actor construction, whose
	 * native failures cannot be caught by the Haxe fallback in GameOverSubstate. */
	private function markDeathConstructionStage(stage:String):Void {
		if (isDie && RuntimeSmokeHarness.enabled())
			RuntimeSmokeHarness.markStep('character-death-construction:' + stage);
	}
	public static function characterExists(character:String):Bool {
		if (isNoGirlfriend(character))
			return true;
		var resolution:Dynamic = Song.resolveCharacterVisualForCurrentSong(character);
		if (!resolution.complete && PlayState.instance != null
			&& PlayState.instance.hasPendingHxcCharacterVisual(character))
			return true;
		if (!resolution.complete)
			Character.reportResolution(resolution);
		return resolution.complete;
	}
	/**
		Return the preserved V-Slice character metadata through the native
		registry.  HXC modules use this instead of opening donor JSON paths; the
		result is a detached object containing only data fields that the engine
		already imports.  Legacy characters simply return null or an empty costume
		list.
	*/
	public static function hxcCharacterData(character:String):Dynamic {
		if (character == null || StringTools.trim(character) == '')
			return null;
		var requested = StringTools.trim(character);
		var lookup = isNoGirlfriend(requested) ? 'gf' : requested;
		try {
			var resolution:Dynamic = Song.resolveCharacterVisualForCurrentSong(lookup);
			var entry:Dynamic = Song.characterVisualRegistryEntryForCurrentSong(lookup);
			if (entry == null)
				return null;
			var implementation:Dynamic = null;
			if (resolution != null && resolution.complete == true && resolution.implementationPath != null) {
				var implementationPath:String = Std.string(resolution.implementationPath);
				var lowerPath = implementationPath.toLowerCase();
				if (lowerPath.endsWith('.json') || lowerPath.endsWith('.jsonc'))
					implementation = CoolUtil.parseJson(FNFAssets.getText(implementationPath));
			}
			var result:Dynamic = {};
			var costumes:Dynamic = Reflect.field(entry, 'vSliceCostumes');
			if (costumes == null)
				costumes = Reflect.field(entry, 'costumes');
			if (costumes == null && implementation != null)
				costumes = Reflect.field(implementation, 'costumes');
			var costumeList:Dynamic = Reflect.field(entry, 'vSliceCostumeList');
			if (costumeList == null)
				costumeList = Reflect.field(entry, 'costumelist');
			if (costumeList == null && implementation != null)
				costumeList = Reflect.field(implementation, 'costumelist');
			if (!Std.isOfType(costumeList, Array))
				costumeList = [];
			var doesLoop:Dynamic = Reflect.field(entry, 'vSliceDoesLoop');
			if (doesLoop == null)
				doesLoop = Reflect.field(entry, 'doesLoop');
			if (doesLoop == null && implementation != null)
				doesLoop = Reflect.field(implementation, 'doesLoop');
			Reflect.setField(result, 'name', requested);
			Reflect.setField(result, 'costumes', costumes);
			Reflect.setField(result, 'costumelist', costumeList);
			Reflect.setField(result, 'doesLoop', doesLoop == true);
			return result;
		} catch (error:Dynamic) {
			trace('HXC character metadata lookup failed for ' + requested + ': ' + Std.string(error));
			return null;
		}
	}
	public function sing(direction:Int, ?miss:Bool=false, ?alt:Int=0) {
		if (!canSing || specialAnim) return;
		var directName:String = switch (direction % 4) {
			case 0:
				"singLEFT";
			case 1:
				"singDOWN";
			case 2:
				"singUP";
			case 3:
				"singRIGHT";
			default:
				"";
		}
		var missName:String = "";
		var missSupported:Bool = false;
		var missAltSupported:Bool = false;
		if (miss) {
			missName = "miss";
			if (animation.getByName(directName + missName) != null)
				missSupported = true;
			if (alt > 0) {
				if (alt == 1 && animation.getByName(directName + missName + '-alt') != null)
					missAltSupported = true;
				else if (alt > 1 && animation.getByName(directName + missName + "-alt" + alt) != null)
					missAltSupported = true;
			}
			if (missSupported && (alt == 0 || missAltSupported))
				directName += missName;
		} 
		if (alt > 0 && (!miss || missAltSupported)) {
			if (alt == 1 && animation.getByName(directName + '-alt') != null)
				directName += "-alt";
			else if (alt > 1 && animation.getByName(directName + "-alt" + alt) != null)
				directName += "-alt" + alt;
		}
		// if we have to miss, but miss isn't supported...
		if (miss && !(missSupported)) {
			// first, we don't want to be using alt, which is already handled.
			// second, we don't want no animation to be played, which again is handled.
			// third, we want character to turn purple, which is handled here.
			color = 0xCFAFFF;
		} else if (color == 0xCFAFFF) {
			color = FlxColor.WHITE;
		}
		if (alt > 0) {
			if (alt == 1 && animation.getByName(directName + '-alt') != null)
				directName += "-alt";
			else if (alt > 1 &&  animation.getByName(directName + "-alt" + alt) != null)
				directName += "-alt" + alt;
		}
		callInterp("sing", [direction, miss, alt, this]);
		if (codenameLiveDefinition != null) codenamePlayAnim(directName, true, miss ? 'MISS' : 'SING');
		else playAnim(directName, true);
		if (PlayState.instance != null)
			PlayState.instance.dispatchHxcCharacterMethod(this, 'playSingAnimation',
				[direction, miss, alt > 0 ? (alt == 1 ? 'alt' : 'alt' + alt) : '']);
	}
	override function update(elapsed:Float) {
		if (codenameLiveDefinition != null) {
			super.update(elapsed);
			codenameUpdateAfterSuper(elapsed);
			return;
		}
		updateNightmareVisionAnimationTimer(elapsed);
		if (heyTimer > 0) {
			var rate = PlayState.instance == null ? 1 : PlayState.instance.playbackRate;
			heyTimer -= elapsed * rate;
			if (heyTimer <= 0) {
				heyTimer = 0;
				var activeName = animationName(this);
				if (specialAnim && (activeName == 'hey' || activeName == 'cheer')) {
					specialAnim = false;
					dance();
				}
			}
		}
		if (specialAnim && heyTimer <= 0 && animation.curAnim != null && animation.curAnim.finished) {
			specialAnim = false;
			// Nightmare Vision returns to the normal dance as soon as a
			// one-shot special animation completes, even between beats.
			if (nightmareVisionCharacterData != null) dance();
		}
		var currentAnim = animationName(this);
		if (animation.curAnim != null && animation.curAnim.finished) {
			if (hxcFinishedAnimation != currentAnim) {
				hxcFinishedAnimation = currentAnim;
				if (PlayState.instance != null)
					PlayState.instance.dispatchHxcCharacterMethod(this, 'onAnimationFinished', [currentAnim]);
			}
		} else {
			hxcFinishedAnimation = '';
		}
		//curCharacter = curCharacter.trim();
		//var charJson:Dynamic = Json.parse(Assets.getText('assets/images/custom_chars/custom_chars.json'));
		//var animJson = File.getContent("assets/images/custom_chars/"+Reflect.field(charJson,curCharacter).like+".json");
		if (beingControlled) {
			if (!debugMode) {
				if (currentAnim.startsWith('sing') || singPriority.contains(currentAnim))
					holdTimer += elapsed;
				else
					holdTimer = 0;

				if (currentAnim.endsWith('miss') && animation.curAnim.finished && beNormal) {
					playAnim('idle', true, false, 10);
					trace("idle after miss");
				}

				if (currentAnim == 'firstDeath' && animation.curAnim.finished)
					playAnim('deathLoop');
			}
		}
		if (!beingControlled) {
			if (currentAnim.startsWith('sing') || singPriority.contains(currentAnim))
				holdTimer += elapsed;

			var dadVar:Float = nightmareVisionCharacterData == null ? 4
				: nightmareVisionNumber(Reflect.field(nightmareVisionCharacterData, 'sing_duration'), 4);
			if (interp != null)
				dadVar = interp.variables.get("dadVar");
			if (holdTimer >= Conductor.stepCrochet * dadVar * 0.001) {
				dance();
				holdTimer = 0;
			}
		}
		if (0 < animationNotes.length && Conductor.songPosition > animationNotes[0][0]) {
			if (hasGun) {
				var idkWhatThisISLol = 1;
				if (2 <= animationNotes[0][1]) {
					idkWhatThisISLol = 3;				
				}

				idkWhatThisISLol += FlxG.random.int(0, 1);
				playAnim("shoot" + idkWhatThisISLol, true);
				animationNotes.shift();
			} else {
				sing(Std.int(animationNotes[0][1] % 4));
				animationNotes.shift();
			}
		}
		if (animation.curAnim != null && animation.curAnim.name == 'hairFall' && animation.curAnim.finished)
			playAnim('danceRight');

		if (animation.curAnim != null && animation.exists(animation.curAnim.name + '-hold') && animation.curAnim.finished)
			playAnim(animation.curAnim.name + '-hold');
		
		callInterp("update", [elapsed, this]);
		super.update(elapsed);
	}
	function updateNightmareVisionAnimationTimer(elapsed:Float):Void {
		if (nightmareVisionCharacterData == null || debugMode || animTimer <= 0
			|| animation == null || animation.curAnim == null
			|| StringTools.endsWith(animation.curAnim.name, '-return')) return;
		animTimer -= elapsed;
		if (animTimer <= 0) {
			animTimer = 0;
			dance(forceDance);
		}
	}
	function codenameUpdateAfterSuper(elapsed:Float):Void {
		codenameAdvanceLoop();
		codenameRuntime.call('update', [elapsed]);
		if (stunned) {
			codenameStunnedTime += elapsed;
			if (codenameStunnedTime > 5 / 60) stunned = false;
		}
		if (!codenameAnimationLock && lastAnimContext != 'DANCE') codenameTryDance();
		codenameAnimationLock = false;
	}
	function codenameAdvanceLoop():Void {
		if (debugMode || (animation.curAnim != null && !animation.curAnim.finished)) return;
		var successor = animation.name + '-loop';
		if (animation.exists(successor)) codenamePlayAnim(successor, null, lastAnimContext);
	}

	private var danced:Bool = false;
	@:keep public var canSing:Bool = true;
	/** Nightmare Vision note-miss timer and source Bopper forced-dance setting. */
	@:keep public var animTimer:Float = 0;
	@:keep public var forceDance:Bool = false;
	/** Nightmare Vision's source Bopper/FunkinSprite animation lock. */
	@:keep public var canPlayAnimations:Bool = true;
	@:keep public var specialAnim:Bool = false;
	@:keep public var heyTimer:Float = 0;
	var forcedAnimationTimer:FlxTimer = new FlxTimer();
	/** Match Nightmare Vision's timed play helper; the optional forced mode
	 * holds every later animation request until this actor's timer completes. */
	@:keep public function playAnimForDuration(animToPlay:String, duration:Float = 0.6,
		forced:Bool = false):Void {
		if (forced) canPlayAnimations = true;
		playAnim(animToPlay, true);
		if (forced) canPlayAnimations = false;
		forcedAnimationTimer.start(duration, function(_:FlxTimer):Void {
			if (forced) canPlayAnimations = true;
		});
	}
	@:keep public function specialPlayAnim(name:String, force:Bool = false, reversed:Bool = false, frame:Int = 0):Void {
		playAnim(name, force, reversed, frame);
		specialAnim = true;
	}
	/** Source Bopper dance gate reuses the shared animation suppression flag. */
	@:keep public var canDance(get, set):Bool;
	function get_canDance():Bool return !skipDance;
	function set_canDance(value:Bool):Bool {
		skipDance = !value;
		return value;
	}
	public function dance(forced:Bool = false) {
		if (skipDance) return;
		if (nightmareVisionCharacterData != null && specialAnim) return;
		// A script can retain an actor after its visual is destroyed or fails to
		// resolve. The next beat must not dereference its animation controller.
		if (animation == null) return;
		if (codenameLiveDefinition != null || codenameVisualBuilding) {
			if (debugMode) return;
			var event = new CodenameCharacterEvent();
			event.danced = danced;
			codenameRuntime.event('onDance', event);
			if (event.cancelled) return;
			var name = 'idle';
			if (animation.exists('danceLeft') && animation.exists('danceRight')) {
				danced = !danced;
				name = danced ? 'danceLeft' : 'danceRight';
			}
			codenamePlayAnim(name + idleSuffix, null, 'DANCE');
			return;
		}
		if (nightmareVisionCharacterData != null) {
			var left = 'danceLeft' + idleSuffix;
			var right = 'danceRight' + idleSuffix;
			if (animation.exists(left) && animation.exists(right)) {
				danced = !danced;
				playAnim(danced ? right : left, forced);
			} else if (animation.exists('idle' + idleSuffix))
				playAnim('idle' + idleSuffix, forced);
			else if (animation.exists('idle'))
				playAnim('idle', forced);
			return;
		}
		if (!specialAnim && !debugMode && beNormal && !isDie && (animation.curAnim == null || !noDanceAnims.contains(animation.curAnim.name) || animation.curAnim.finished)) {
			if (interp != null)
				callInterp("dance", [this]);
			else {
				// 'Alt Idle Animation' events set this ('-alt' etc.) - fall
				// back to plain idle when the suffixed anim doesn't exist
				var idleName = 'idle' + idleSuffix;
				playAnim(idleSuffix != '' && animation.getByName(idleName) != null ? idleName : 'idle');
			}

			if (color == 0xCFAFFF)
				color = FlxColor.WHITE;
		}
		// V-Slice character companions may add dance-side effects (for example
		// costume-specific overlays or animation bookkeeping). Keep this actor
		// local just like play/sing dispatch; the native idle decision above still
		// provides a safe fallback when a donor override is unavailable.
		if (PlayState.instance != null)
			PlayState.instance.dispatchHxcCharacterMethod(this, 'dance', [false]);
	}

	/** Match the source Bopper animation playback controls on native actors. */
	@:keep public function pauseAnim():Void animation.pause();
	@:keep public function resumeAnim():Void animation.resume();

	public function playAnim(AnimName:String, Force:Bool = false, Reversed:Bool = false, Frame:Int = 0):Void {
		if (!canPlayAnimations) return;
		var codenameContext:Dynamic = null;
		var codenamePlayback = false;
		if (codenameLiveDefinition != null || codenameVisualBuilding) {
			var requestedForce:Null<Bool> = codenameHasPendingForce ? codenamePendingForce : Force;
			// Consume before callbacks: a script may request another animation here.
			codenameHasPendingForce = false;
			var event = new CodenameCharacterEvent();
			event.animName = AnimName; event.force = requestedForce; event.reverse = Reversed;
			event.startingFrame = Frame; event.context = codenameAnimationContext;
			codenameRuntime.event('onPlayAnim', event);
			if (event.cancelled) return;
			AnimName = event.animName; Reversed = event.reverse;
			codenameContext = event.context;
			// Donor Character updates the sing timestamp after FunkinSprite
			// returns, including a name rejected by the animation lookup.
			if (AnimName == null || (!debugMode && !animation.exists(AnimName))) {
				codenameApplyGlobalOffset();
				if (codenameContext == 'SING' || codenameContext == 'MISS') lastHit = Conductor.songPosition;
				return;
			}
			if (event.force == null) {
				Force = false;
				var knownAnimations:Array<Dynamic> = codenameVisualBuilding
					? codenameBuildingAnimations : cast codenameLiveDefinition.animations;
				// XML animDatas is a map: a later node with the same name wins,
				// but its value is not installed until its own LOOP play returns.
				var index = knownAnimations.length;
				while (index > 0) {
					index--;
					var data = knownAnimations[index];
					if (data.name == AnimName) { Force = data.forced == true; break; }
				}
			} else Force = event.force;
			Frame = event.startingFrame;
			codenamePlayback = true;
		}
		applyVSliceAnimationAsset(AnimName);
		animation.play(AnimName, Force, Reversed, Frame);
		if (codenamePlayback) {
			var data = animOffsets.get(AnimName);
			frameOffset.set(data == null ? 0 : data[0], data == null ? 0 : data[1]);
			codenameApplyGlobalOffset();
			lastAnimContext = codenameContext;
			if (codenameContext == 'SING' || codenameContext == 'MISS') lastHit = Conductor.songPosition;
			if (animation.curAnim == null) return;
		}
		var animName = "";
		if (animation.curAnim == null) {
			// P A N I K
			if (isDie)
				animName = "firstDeath";
			else
				animName = "idle";
			trace("OH SHIT OH FUCK");
		} else {
			// kalm
			animName = animation.curAnim.name;
		}
		// The V-Slice donor applies animation offsets in getScreenPosition,
		// leaving the base offset written by updateHitbox() intact. Legacy and
		// Psych characters retain this fork's original FlxSprite.offset path.
		if (vSliceBaseFrames == null && !codenamePlayback) {
			if (animOffsets.exists(animName)) {
				var daOffset = animOffsets.get(animName);
				offset.set(daOffset[0], daOffset[1]);
			} else
				offset.set(0, 0);
		}
		// Imported V-Slice character companions can override playAnimation. The
		// native animation still runs first, then the matching actor-local HXC
		// scope applies its additional behavior (colour/death overlays/etc.). A
		// PlayState-owned recursion guard keeps a translated super/play call from
		// dispatching the same companion forever.
		if (PlayState.instance != null)
			PlayState.instance.dispatchHxcCharacterMethod(this, 'playAnimation',
				[AnimName, Force, false, Reversed]);
		// should spooky be on this?
		if (likeGf) {
			if (AnimName == 'singLEFT') {
				danced = true;
			} else if (AnimName == 'singRIGHT') {
				danced = false;
			}

			if (AnimName == 'singUP' || AnimName == 'singDOWN') {
				danced = !danced;
			}
		}
	}
	function codenameApplyGlobalOffset():Void {
		offset.set(globalOffset.x * (isPlayer != playerOffsets ? 1 : -1), -globalOffset.y);
	}
	@:keep public function codenamePlayAnim(name:String, ?force:Null<Bool>, context:Dynamic = null,
		reverse:Bool = false, frame:Int = 0):Void {
		var previous = codenameAnimationContext;
		var previousForce = codenamePendingForce;
		var hadPreviousForce = codenameHasPendingForce;
		codenameAnimationContext = context;
		codenamePendingForce = force;
		codenameHasPendingForce = true;
		try playAnim(name, force == true, reverse, frame) catch (error:Dynamic) {
			codenameAnimationContext = previous;
			codenamePendingForce = previousForce;
			codenameHasPendingForce = hadPreviousForce;
			throw error;
		}
		codenameAnimationContext = previous;
		codenamePendingForce = previousForce;
		codenameHasPendingForce = hadPreviousForce;
	}

	@:keep public var codenameSingAnims:Array<String> = ['singLEFT', 'singDOWN', 'singUP', 'singRIGHT'];
	@:keep public function codenameGetSingAnim(direction:Int, suffix:String = ''):String {
		return codenameSingAnims[direction % codenameSingAnims.length] + suffix;
	}
	@:keep public function codenamePlaySingAnim(direction:Int, suffix:String = '', context:Dynamic = 'SING',
		?force:Null<Bool>, reversed:Bool = false, frame:Int = 0):Void {
		var event = new CodenameDirectionAnimEvent(codenameGetSingAnim(direction, suffix),
			direction, suffix, context, reversed, frame, force);
		if (codenameRuntime != null) codenameRuntime.event('onPlaySingAnim', event);
		if (event.cancelled) return;
		codenamePlaySingAnimUnsafe(event.direction, animation.exists(event.animName) ? event.suffix : '',
			event.context, event.force, event.reversed, event.frame);
	}
	@:keep public function codenamePlaySingAnimUnsafe(direction:Int, suffix:String = '', context:Dynamic = 'SING',
		force:Bool = true, reversed:Bool = false, frame:Int = 0):Void {
		var event = new CodenameDirectionAnimEvent(codenameGetSingAnim(direction, suffix),
			direction, suffix, context, reversed, frame, force);
		if (codenameRuntime != null) codenameRuntime.event('playSingAnimUnsafe', event);
		if (event.cancelled) return;
		codenamePlayAnim(event.animName, event.force, event.context, event.reversed, event.frame);
	}

	@:keep public function codenameTryDance():Void {
		var event = new CodenameCharacterEvent();
		codenameRuntime.event('onTryDance', event);
		if (event.cancelled) return;
		switch (lastAnimContext) {
			case 'SING' | 'MISS':
				if (lastHit + Conductor.stepCrochet * holdTime < Conductor.songPosition) dance();
			case 'DANCE': dance();
			case 'LOCK': if (animation.curAnim == null) dance();
			default: if (animation.curAnim == null || animation.curAnim.finished) dance();
		}
	}

	/** Donor StrumLine grants this lease only for accepted held input on the
	 * actor's controlled line. Character.update clears it after the next frame. */
	@:keep public function lockCodenameAnimationForInput():Void {
		if (codenameLiveDefinition != null && !characterDestroyed
			&& lastAnimContext != 'DANCE') codenameAnimationLock = true;
	}

	public function codenameBeatHit(beat:Int):Void {
		codenameRuntime.call('beatHit', [beat]);
		if (skipNegativeBeats && beat < 0) return;
		if (danceOnBeat && beatInterval > 0 && (beat + beatOffset) % beatInterval == 0 && !codenameAnimationLock)
			codenameTryDance();
	}

	@:keep public function getCameraPosition():FlxPoint {
		var midpoint = getMidpoint();
		var event = new CodenameCharacterEvent();
		event.x = midpoint.x + (isPlayer ? -100 : 150) + globalOffset.x + cameraOffset.x;
		event.y = midpoint.y - 100 + globalOffset.y + cameraOffset.y;
		if (codenameRuntime != null) codenameRuntime.event('onGetCamPos', event);
		midpoint.put();
		return FlxPoint.get(event.x, event.y);
	}

	@:keep public function isFlippedOffsets():Bool {
		return codenameLiveDefinition != null && !debugMode
			&& (isPlayer != playerOffsets) != (flipX != codenameBaseFlipped);
	}

	override public function getScreenBounds(?newRect:FlxRect, ?camera:FlxCamera):FlxRect {
		if (!codenameReverseDrawProcedure) return super.getScreenBounds(newRect, camera);
		scale.x *= -1;
		try {
			var bounds = super.getScreenBounds(newRect, camera);
			scale.x *= -1;
			return bounds;
		} catch (error:Dynamic) {
			scale.x *= -1;
			throw error;
		}
	}

	function codenameRestoreDraw(moved:Bool, reversed:Bool):Void {
		if (reversed) {
			flipX = !flipX;
			scale.x *= -1;
			codenameReverseDrawProcedure = false;
		}
		if (moved) {
			x -= extraOffset.x;
			y -= extraOffset.y;
		}
	}

	override public function draw():Void {
		if (codenameLiveDefinition == null) { super.draw(); return; }
		var smokeProfileAt = RuntimeSmokeHarness.profileEnabled() ? haxe.Timer.stamp() : 0.0;
		var event = new CodenameCharacterEvent();
		if (codenameRuntime != null) codenameRuntime.event('draw', event);
		if (smokeProfileAt > 0) {
			var now = haxe.Timer.stamp();
			RuntimeSmokeHarness.profileSection('codename-character-pre-draw', now - smokeProfileAt);
			smokeProfileAt = now;
		}
		var moved = !ghostDraw;
		if (moved) { x += extraOffset.x; y += extraOffset.y; }
		var reversed = isFlippedOffsets();
		if (reversed) {
			codenameReverseDrawProcedure = true;
			flipX = !flipX;
			scale.x *= -1;
		}
		try super.draw() catch (error:Dynamic) {
			codenameRestoreDraw(moved, reversed);
			throw error;
		}
		codenameRestoreDraw(moved, reversed);
		if (codenameRuntime != null) codenameRuntime.event('postDraw', event);
		if (smokeProfileAt > 0)
			RuntimeSmokeHarness.profileSection('codename-character-draw-rest', haxe.Timer.stamp() - smokeProfileAt);
	}

	override public function destroy():Void {
		if (characterDestroyed) return;
		characterDestroyed = true;
		forcedAnimationTimer.cancel();
		forcedAnimationTimer.destroy();
		if (onAnimationFinish != null) {
			onAnimationFinish.removeAll();
			onAnimationFinish.destroy();
		}
		if (codenameRuntime != null) codenameRuntime.destroy();
		codenameRuntime = null;
		globalOffset.put(); cameraOffset.put(); frameOffset.put(); extraOffset.put();
		super.destroy();
	}

	public function loadMappedAnims(?song:SwagSong, ?char:String) {
		// todo, make better
		// wish granted (again)
		if (animationNotes != [])
			animationNotes = [];

		var mappedAnims = null;
		if (song != null)
			mappedAnims = song.notes;
		else {
			var songFolder = Song.storageFolder(PlayState.SONG);
			if (songFolder != '' && FileSystem.exists('assets/data/' + songFolder + '/' + curCharacter + '.json'))
				mappedAnims = Song.loadFromJson(curCharacter, songFolder).notes;
		}

		if (mappedAnims != null) {
			var noteAmount = 4;
			if (song != null && song.preferredNoteAmount != null)
				noteAmount = song.preferredNoteAmount;

			for (anim in mappedAnims) {
				for (note in anim.sectionNotes) {
					var rootNote = note[1] % (noteAmount*2);
					if ((char == 'bf' && ((rootNote <= noteAmount-1 && anim.mustHitSection) || (rootNote > noteAmount-1 && rootNote <= noteAmount*2-1 && !anim.mustHitSection))) 
						|| (char == 'dad' && ((rootNote <= noteAmount-1 && !anim.mustHitSection) || (rootNote > noteAmount-1 && rootNote <= noteAmount*2-1 && anim.mustHitSection)))
						|| char == null) //dude what the funk is this
					animationNotes.push(note);
				}
			} 
			animationNotes.sort(sortAnims);
			trace('mapped anims');
		} else {
			trace('mapped anims failed to load');
		}
	}
	function sortAnims(a, b) {
		var aThing = a[0];
		var bThing = b[0];
		return aThing < bThing ? -1 : 1;
	}
	public function addOffset(name:String, x:Float = 0, y:Float = 0, ?plrX:Float, ?plrY:Float) {
		if (plrX == null) plrX = x;
		if (plrY == null) plrY = y;

		if (isPlayer) // quality of life function for adding offsets for both the player and opponent's sides
			animOffsets[name] = [plrX, plrY];
		else
			animOffsets[name] = [x, y];
	}
	public function addCamOffset(name:String, camX:Float = 0, camY:Float = 0) {
		camOffsets[name] = [camX, camY];
	}
	public static function getAnimInterp(char:String):Interp {
		var interp = PluginManager.createSimpleInterp();
		var requested = char == null ? '' : StringTools.trim(char);
		var lookup = isNoGirlfriend(requested) ? 'gf' : requested;
		var resolution:Dynamic = Song.resolveCharacterVisualForCurrentSong(lookup);
		if (!resolution.complete) {
			Character.reportResolution(resolution);
			// Keep the authored charName below, but use a known-safe native visual
			// only for the emergency interpreter bootstrap. The diagnostic above is
			// the observable result; this fallback is not allowed to masquerade as
			// a successful character resolution.
			var dadResolution:Dynamic = Song.resolveCharacterVisualForCurrentSong('dad');
			if (dadResolution.complete)
				resolution = dadResolution;
		}
		var charJson:Dynamic = {};
		var program:Expr = null;
		var assetRoot = 'assets/images/custom_chars/' + lookup;
		if (resolution != null && resolution.complete == true) {
			if (resolution.assetRootPath != null && StringTools.trim(Std.string(resolution.assetRootPath)) != '')
				assetRoot = Std.string(resolution.assetRootPath);
			var implementationPath:String = resolution.implementationPath == null
				? '' : Std.string(resolution.implementationPath);
			var lowerPath = implementationPath.toLowerCase();
			if (implementationPath != '' && (lowerPath.endsWith('.hscript') || lowerPath.endsWith('.hxs'))) {
				var scriptSource = FNFAssets.getText(implementationPath);
				if (scriptSource != null)
					program = cachedCharacterProgram('character:' + implementationPath,
						EngineCompat.rewriteLegacyAssetPaths(scriptSource));
			} else if (implementationPath != '') {
				var jsonSource = FNFAssets.getText(implementationPath);
				if (jsonSource != null)
					charJson = CoolUtil.parseJson(jsonSource);
			}
		}
		if (program == null) {
			var jsonProgram = FNFAssets.getText('assets/images/custom_chars/jsonbased.hscript');
			program = cachedCharacterProgram('character:assets/images/custom_chars/jsonbased.hscript', jsonProgram);
		}
		if (!assetRoot.endsWith('/'))
			assetRoot += '/';
		interp.variables.set("charJson", charJson);
		interp.variables.set("hscriptPath", assetRoot);
		interp.variables.set("PlayState", PlayState);
		interp.variables.set("getUV", function(variabull:String) {
			if (PlayState.universalVar.exists(variabull))
				return PlayState.universalVar.get(variabull);
			else
				return null;
		});

		interp.variables.set("updateUV", function(variabull:String, veryable:Dynamic) {
			PlayState.universalVar[variabull] = veryable;
		});
		// This remains the authored id, even when the resolver selected a sibling
		// implementation and/or an alias asset root.
		interp.variables.set("charName", requested);
		interp.variables.set("Level_NotAHoe", Level_NotAHoe);
		interp.variables.set("Level_Boogie", Level_Boogie);
		interp.variables.set("Level_Sadness", Level_Sadness);
		interp.variables.set("Level_Sing", Level_Sing);
		interp.variables.set("portraitOffset", [0, 0]);
		interp.variables.set("dadVar", 4.0);
		interp.variables.set("isPixel", false);
		interp.variables.set("colors", [FlxColor.CYAN]);
		if (program != null)
			try interp.execute(program) catch (error:Dynamic)
				trace('[hxc-character-script-error] ' + requested + ': ' + Std.string(error));
		trace(interp);
		return interp;
	}
}
