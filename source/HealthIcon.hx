package;

import flixel.FlxSprite;
import lime.utils.Assets;
import lime.system.System;
import flash.display.BitmapData;
import lime.app.Future;
import flixel.graphics.frames.FlxAtlasFrames;
#if sys
import sys.io.File;
import haxe.io.Path;
import openfl.utils.ByteArray;

import sys.FileSystem;
#end
import flixel.math.FlxMath;
import flixel.util.FlxColor;
import hscript.Expr;
import hscript.Interp;
import hscript.ParserEx;
import haxe.xml.Parser;
import hscript.InterpEx;
import haxe.Json;
import haxe.format.JsonParser;
import tjson.TJSON;
using StringTools;
enum abstract IconState(Int) from Int to Int {
	var Normal;
	var Dying;
	var Poisoned;
	var Winning;
}
typedef IconData = {
	var json:Dynamic;
	var path:String;
	var assetRoot:String;
}
class HealthIcon extends FlxSprite {
	public var player:Bool = false;
	public var isAnimated = false;
	public var isNormal:Bool = false;
	/**
	 * V-Slice HealthIcon compatibility flag.  Donor song scripts use this to
	 * mark an icon that should retain the legacy HUD presentation.  Keep the
	 * state on the native icon even when the selected donor icon uses the
	 * neutral fallback graphic; consumers can still apply their normal layout
	 * rules without an invalid HScript field access.
	 */
	public var isLegacyStyle:Bool = false;
	/** V-Slice lets a song hold an authored icon animation until it restores
	 * automatic health and beat updates. */
	@:keep public var autoUpdate:Bool = true;
	@:keep public function getCurrentAnimation(?name:String):Dynamic {
		var current = animation == null || animation.curAnim == null
			? null : animation.curAnim.name;
		return name == null ? current : current == name;
	}
	@:keep public function playAnimation(name:String, restart:Bool = false):Void {
		if (name != null && animation != null && animation.exists(name))
			animation.play(name, restart);
	}
	/** Resting size used by the native bop. Imported V-Slice icon events can
	 * change it without fighting the per-frame return-to-150 animation. */
	public var bopBaseSize:Int = 150;
	/** Codename's scale callbacks are active only on its gameplay icons. */
	public var codenameBop:Bool = false;
	public var defaultScale:Float = 1;
	public dynamic function bump():Void {
		scale.set(defaultScale * 1.2, defaultScale * 1.2);
		updateHitbox();
	}
	public dynamic function updateBump():Void {
		var ratio = 1 - Math.pow(1 - 0.33, flixel.FlxG.elapsed * 60);
		scale.set(scale.x + (defaultScale - scale.x) * ratio,
			scale.y + (defaultScale - scale.y) * ratio);
		updateHitbox();
	}
	public var sprTracker:FlxSprite;
	public var healthColors:Array<FlxColor> = [];
	/** V-Slice/HXC Freeplay capsule alias for the native icon identity. */
	public var character(get, set):String;
	function get_character():String return curCharacter;
	function set_character(value:String):String {
		if (value != null && value != '' && value != curCharacter)
			switchAnim(value);
		return curCharacter;
	}
	var curCharacter:String = '';
	/** V-Slice HealthIcon character-loading alias used by imported HUD scripts. The
	 * selected character registry and icon owner are resolved by switchAnim. */
	@:keep public function loadCharacter(char:String):Dynamic return switchAnim(char);
	/** Psych changes the same owner-resolved icon only when its identifier changes. */
	@:keep public function changeIcon(char:String, allowGPU:Bool = true):Void {
		if (char != curCharacter) switchAnim(char);
	}
	public var iconState(default, set):IconState = Normal;
	private var interp:Interp;
	function set_iconState(x:IconState):IconState {
		if (isAnimated) {
			switch (x) {
				case Normal:
					animation.play('icon');
				case Dying:
					animation.play('dying');
				case Poisoned:
					animation.play('poisoned');
				case Winning:
					animation.play('winning');
			}
		} else {
			var maxPosition = iconPositionLimit();
			switch (x) {
				case Normal:
					animation.curAnim.curFrame = 0;
				case Dying:
					// short imported strips may not even have a losing cell
					animation.curAnim.curFrame = 1 <= maxPosition ? 1 : maxPosition;
				case Poisoned:
					// same deal it will go to dying which is good enough
					animation.curAnim.curFrame = 2 <= maxPosition ? 2 : maxPosition;
				case Winning:
					// we DO do it here here we want to make sure it isn't silly
					if (animation.curAnim.frames.length >= 4) {
						animation.curAnim.curFrame = 3 <= maxPosition ? 3 : maxPosition;
					} else {
						animation.curAnim.curFrame = 0;
					}
			}
		}
		return iconState = x;
	}

	/** Last valid slot inside the current 'icon' animation. A looped player
	 * animation set past its last slot wraps onto the wrong art (flixel
	 * re-enters the setter forever), so every state write clamps first. */
	function iconPositionLimit():Int {
		var anim = animation.curAnim;
		var count = anim == null ? 0 : anim.numFrames;
		return count <= 0 ? 0 : count - 1;
	}

	/**
	 * Fold a registry "icons" array onto the strip that actually loaded.
	 * Imported V-Slice strips often carry fewer 150x150 cells than the native
	 * four-state icon grid - a lone neutral icon, or neutral + losing - while
	 * the registry still asks for the native normal/losing/poisoned/winning
	 * indices. Entries pointing past the last loaded cell are remapped so
	 * flixel cannot drop or wrap them onto arbitrary cells: the winning slot
	 * falls back to the neutral cell, every other missing state takes the
	 * last available cell (the losing icon on a two-cell strip). Full-size
	 * native strips never have an out-of-range entry and keep the authored
	 * mapping untouched. Works on a copy: the registry json is cached
	 * statically and shared across icon reloads.
	 */
	function clampIconFrames(iconFrames:Array<Int>):Array<Int> {
		var available:Int = frames == null ? 0 : frames.numFrames;
		var mapped:Array<Int> = iconFrames == null ? [0, 0, 0, 0] : iconFrames.copy();
		if (available <= 0)
			return mapped;
		for (i in 0...mapped.length) {
			if (mapped[i] < 0 || mapped[i] >= available)
				mapped[i] = i == 3 ? 0 : available - 1;
		}
		return mapped;
	}

	static var charJson:Dynamic;
	static var iconJson:Dynamic;
	static var missingIconReference:String = '';
	var iconOwnerRoot:Null<String> = null;
	var iconOwnerEngine:String = '';
	var deferMissingIconDiagnostic:Bool = false;
	var deferredMissingIconDiagnostic:Dynamic = null;
	public function new(char:String = 'bf', isPlayer:Bool = false, ?isnormal:Bool = false, ?loadAsync:Bool = false,
		?ownerSong:String, ?deferMissingIconDiagnostic:Bool = false) {
		// freeplay builds hundreds of icons at once - parse the jsons once
		if (charJson == null)
			charJson = CoolUtil.parseJson(FNFAssets.getJson("assets/images/custom_chars/custom_chars"));
		if (iconJson == null)
			iconJson = CoolUtil.parseJson(FNFAssets.getJson("assets/images/custom_chars/icon_only_chars"));

		player = isPlayer;
		super();
		this.deferMissingIconDiagnostic = deferMissingIconDiagnostic;
		// Menu rows have their own song owner; they must not inherit an old
		// PlayState's scope or another row's same-named character/icon. Gameplay
		// HUD icons bind to the chart storage folder before HXC loadCharacter()
		// calls run, even though their legacy constructor omits ownerSong.
		iconOwnerRoot = ownerRootForIcon(ownerSong, isnormal);
		iconOwnerEngine = ownerEngineForIcon(ownerSong, isnormal);
		antialiasing = true;
		isNormal = isnormal;
		switchAnim(char, loadAsync);
		scrollFactor.set();
	}

	/** Resolve the chart's selected import owner for menu and gameplay icons. */
	static function characterOwnerRoot(ownerSong:String):String {
		if (ownerSong == null || StringTools.trim(ownerSong) == '')
			return '';
		var root = Song.characterRootForSong(ownerSong);
		if (root == null || root == '')
			root = Song.characterRootForSong(ownerSong, ImportEngine.V_SLICE);
		return root == null ? '' : root;
	}

	/** Keep a gameplay icon attached to its chart manifest; an unowned menu icon
	 * must never inherit a stale PlayState owner. */
	static function ownerRootForIcon(ownerSong:String, gameplayIcon:Bool):Null<String> {
		var selectedSong = ownerSong;
		if (selectedSong == null || StringTools.trim(selectedSong) == '') {
			if (!gameplayIcon || PlayState.SONG == null)
				return null;
			selectedSong = Song.storageFolder(PlayState.SONG);
		}
		return characterOwnerRoot(selectedSong);
	}

	/** Resolve the same chart/menu owner used by the icon root. */
	static function ownerEngineForIcon(ownerSong:String, gameplayIcon:Bool):String {
		var selectedSong = ownerSong;
		if (selectedSong == null || StringTools.trim(selectedSong) == '') {
			if (!gameplayIcon || PlayState.SONG == null)
				return '';
			selectedSong = Song.storageFolder(PlayState.SONG);
		}
		return Song.characterOwnerEngineForSong(selectedSong);
	}

	/** NMV characters store a logical healthicon separate from their character id. */
	static function nightmareVisionHealthIcon(char:String, ownerRoot:String,
		ownerEngine:String):Null<String> {
		if (ownerRoot == null || StringTools.trim(ownerRoot) == '' || ownerEngine == null
			|| ownerEngine.toLowerCase() != ImportEngine.NIGHTMARE_VISION.toLowerCase())
			return null;
		var definition = NightmareVisionCharacterData.load(ownerRoot, char);
		if (definition == null)
			return null;
		var authored:Dynamic = Reflect.field(definition, 'healthicon');
		if (authored == null)
			return 'face';
		if (Std.isOfType(authored, String))
			return cast authored;
		trace('[nightmare-vision-character-data] healthicon must be a string; using template face icon');
		return 'face';
	}

	/** Keep other engines' icon identities intact while NMV uses its source field. */
	static function iconRequestForOwner(char:String, ownerRoot:String, ownerEngine:String,
		gameplayIcon:Bool):Dynamic {
		var request = iconRequestForCharacter(char, ownerRoot, gameplayIcon);
		if (request.hidden)
			return request;
		var authored = nightmareVisionHealthIcon(char, ownerRoot, ownerEngine);
		if (authored != null)
			request.name = authored;
		return request;
	}

	function clearDeferredIconDiagnostic():Void {
		deferredMissingIconDiagnostic = null;
	}

	function handleMissingIconDiagnostic(plan:Dynamic):Void {
		if (deferMissingIconDiagnostic)
			deferredMissingIconDiagnostic = plan;
		else
			EngineCompat.reportVisualFallback(plan);
	}

	function reportDeferredIconDiagnostic():Void {
		var plan = deferredMissingIconDiagnostic;
		deferredMissingIconDiagnostic = null;
		if (plan != null)
			EngineCompat.reportVisualFallback(plan);
	}

	public function switchAnim(char:String = 'bf', ?async:Bool = false):Dynamic {
		// HXC can construct an icon with a temporary HUD-slot id and configure
		// its actual health icon in the same callback. A new selection replaces
		// the pending visual before its first frame, so only a still-missing icon
		// reaches runtime diagnostics.
		clearDeferredIconDiagnostic();
		autoUpdate = true;
		var wasNoGirlfriend = isNormal && Character.isNoGirlfriend(curCharacter);
		curCharacter = char == null ? 'bf' : char;
		var iconRequest = iconRequestForOwner(curCharacter, iconOwnerRoot, iconOwnerEngine, isNormal);
		var noGirlfriend = iconRequest.hidden;
		// V-Slice 0.3.2 creates no opponent icon when this sentinel has no
		// character definition. Keep a valid native icon for HUD bookkeeping,
		// but draw none until a real character replaces it.
		if (noGirlfriend)
			visible = false;
		else if (wasNoGirlfriend)
			visible = true;
		missingIconReference = '';
		var iconFrames:Array<Int> = [];
		bopReset();
		// A new icon owns a new bop script and defaults. Without clearing this,
		// changing from a scripted icon to a non-bopping or missing icon keeps
		// executing the previous icon's interpreter.
		interp = null;
		bopBaseSize = 150;
		antialiasing = true;
		// V-Slice Freeplay owns a separate 50px pixel portrait for each row.
		// It is scoped to the selected song import and must never replace the
		// 150px gameplay health strip (including the no-gf gameplay sentinel).
		var freeplayPixelPath = isNormal ? null : freeplayPixelIconPath(curCharacter, iconOwnerRoot);
		if (freeplayPixelPath != null && FNFAssets.exists(freeplayPixelPath)) {
			try {
				loadGraphic(FNFAssets.getBitmapData(freeplayPixelPath));
				// V-Slice 0.3.2's SongMenuItem displays this portrait at 2x.
				setGraphicSize(Std.int(width * 2), Std.int(height * 2));
				updateHitbox();
				antialiasing = false;
				isAnimated = false;
				healthColors = [0xFFFFFFFF];
				animation.add('icon', [0], false, player);
				animation.play('icon');
				animation.pause();
				return this;
			} catch (_:Dynamic) {}
		}
		final daData:Dynamic = getIconFromJsons(iconRequest.name, iconRequest.ownerRoot);
		final customIconRoot:Null<String> = daData == null ? null : daData.assetRoot + daData.path + '/';
		var directIcon = scopedCodenameIconFallbackPath(customIconRoot, iconRequest.name, iconRequest.ownerRoot);
		if (directIcon != null) {
			// Codename stores direct HUD strips under images/icons/<id>, while a
			// character may also have a registry entry without its own icons.png.
			// Use the selected owner's direct strip before the neutral-grid fallback.
			if (RuntimeSmokeHarness.enabled())
				trace('[compat-icon-selected] ' + iconRequest.name + ' path=' + directIcon);
			var directImage = FNFAssets.getBitmapData(directIcon);
			loadGraphic(directImage, true, 150, 150);
			isAnimated = false;
			healthColors = [0xFFFFFFFF];
			animation.add('icon', clampIconFrames([0, 1, 1, 0]), false, player);
			animation.play('icon');
			animation.pause();
			return this;
		}
		if (daData == null) {
			// The authored icon id is intentionally retained, but a missing donor
			// icon must not dereference a null definition or abort chart startup.
			// iconGrid is a native safe visual, not a claim that the donor asset
			// existed or that the import missing count should be reduced.
			var iconReference = missingIconReference == null || StringTools.trim(missingIconReference) == ''
				? curCharacter : missingIconReference;
			var iconPlan = EngineCompat.planVisualFallback('health-icon', iconReference,
				'runtime character metadata healthicon field',
				EngineCompat.visualDependencySearchPaths('health-icon', iconReference,
					iconRequest.ownerRoot == null || iconRequest.ownerRoot == ''
						? Song.currentCharacterRoot() : iconRequest.ownerRoot),
				'health display uses the neutral icon grid; health values, scoring, and note gameplay continue',
				'unresolved-source-dependency');
			handleMissingIconDiagnostic(iconPlan);
			isAnimated = false;
			healthColors = [0xFFFFFFFF];
			loadGraphic('assets/images/iconGrid.png', true, 150, 150);
			animation.add('icon', [0, 0, 0, 0], false, player);
			animation.play('icon');
			animation.pause();
			return this;
		}
		final daJson:Dynamic = daData.json;

		if (daJson != null && Reflect.hasField(daJson, 'icons')) {
			iconFrames = daJson.icons;
			if (isNormal) {
				if (daJson.iconbop != null)
					interp = HealthIcon.iconBop(daJson.iconbop);
				else
					interp = HealthIcon.iconBop('default');
			}
		} else {
			iconFrames = [0, 0, 0, 0];
			if (isNormal)
				interp = HealthIcon.iconBop('default');
		}

		if (daJson != null && Reflect.hasField(daJson, 'colors')) {
			var daColors:Array<String> = daJson.colors;
			healthColors = [];
			for (color in daColors) {
				healthColors.push(FlxColor.fromString(color));
			}
		} else
			healthColors = [0xFFFFFFFF];

		final charPath = daData.assetRoot + daData.path + '/';
		if (FNFAssets.exists(charPath + "icons.png")) {
			if (async) {
				return FNFAssets.loadBitmapData(charPath + "icons.png").then(function(image) {
					if (FNFAssets.exists(charPath + "icons.xml")) {
						isAnimated = true;
						frames = DynamicSprite.DynamicAtlasFrames.fromSparrow(charPath + 'icons.png', charPath + 'icons.xml');
						animation.addByPrefix('icon', 'normal', 24, true);
						animation.addByPrefix('dying', 'dying', 24, true);
						animation.addByPrefix('winning', 'winning', 24, true);
						animation.addByPrefix('poisoned', 'poisoned', 24, true);
					} else {
						isAnimated = false;
						loadGraphic(image, true, 150, 150);
						animation.add('icon', clampIconFrames(iconFrames), false, player);
					}
					animation.play('icon');
					if (!isAnimated)
						animation.pause();
					return Future.withValue(this);
				}).onComplete(function(icon) { return icon; });
			} else {
				if (FNFAssets.exists(charPath + 'icons.xml')) { // i guess it works :thumbsup:
					isAnimated = true;
					frames = DynamicSprite.DynamicAtlasFrames.fromSparrow(charPath + 'icons.png', charPath + 'icons.xml');
					animation.addByPrefix('icon', 'normal', 24, true);
					animation.addByPrefix('dying', 'dying', 24, true);
					animation.addByPrefix('winning', 'winning', 24, true);
					animation.addByPrefix('poisoned', 'poisoned', 24, true);
				} else {
					isAnimated = false;
					var rawPic:BitmapData = FNFAssets.getBitmapData(charPath + "icons.png");
					loadGraphic(rawPic, true, 150, 150);
					animation.add('icon', clampIconFrames(iconFrames), false, player);
				}
			}
		} else {
			// An imported character built on a base-library atlas inherits that
			// character's health icon when the donor shipped none: the donor's
			// icon-<id> convention cannot resolve for an id the base game never
			// drew. Retry once with the stamped native identity before settling
			// for the neutral grid.
			var nativeIdentity:Dynamic = daJson == null ? null : Reflect.field(daJson, 'nativeIconIdentity');
			if (nativeIdentity != null && Std.string(nativeIdentity).trim() != ''
				&& Std.string(nativeIdentity) != char) {
				return switchAnim(Std.string(nativeIdentity), async);
			}
			loadGraphic('assets/images/iconGrid.png', true, 150, 150);
			animation.add('icon', clampIconFrames(iconFrames), false, player);
		}
		animation.play('icon');
		if (!isAnimated)
			animation.pause();
		return this;
	}

	static function scopedCodenameIconPath(iconId:String, ownerRoot:String):Null<String> {
		var root = ownerRoot == null || ownerRoot == '' ? Song.currentCharacterRoot() : ownerRoot;
		if (root == null || root == '' || iconId == null
			|| !new EReg('^[a-zA-Z0-9_-]+$', '').match(iconId)) return null;
		for (relative in [
			'images/icons/' + iconId + '/icon.png',
			'images/icons/icon-' + iconId + '.png',
			'images/icons/' + iconId + '.png'
		]) {
			var path = root + '/' + relative;
			if (FNFAssets.exists(path)) return path;
		}
		return null;
	}

	/** Prefer an owner's direct Codename icon only when its character entry has
	 * no custom health strip; this preserves custom_chars icons when both exist. */
	static function scopedCodenameIconFallbackPath(charIconRoot:Null<String>, iconId:String, ownerRoot:String):Null<String> {
		if (charIconRoot != null && FNFAssets.exists(charIconRoot + 'icons.png')) return null;
		return scopedCodenameIconPath(iconId, ownerRoot);
	}

	static function iconRequestForCharacter(char:String, ownerRoot:String, gameplayIcon:Bool):{name:String, ownerRoot:String, hidden:Bool} {
		if (gameplayIcon && Character.isNoGirlfriend(char))
			return {name: 'face', ownerRoot: '', hidden: true};
		return {name: char, ownerRoot: ownerRoot, hidden: false};
	}

	static function freeplayPixelIconPath(char:String, ownerRoot:String):Null<String> {
		if (char == null || ownerRoot == null || ownerRoot == '')
			return null;
		var id = StringTools.trim(char).toLowerCase();
		if (id == '' || !new EReg('^[a-z0-9_-]+$', '').match(id))
			return null;
		return ownerRoot + '/images/freeplay/icons/' + id
			+ (id.endsWith('pixel') ? '' : 'pixel') + '.png';
	}

	/** Named HXC alias; native code continues to use switchAnim internally. */
	public function setCharacter(char:String):Dynamic
		return switchAnim(char);

	/** Codename's gameplay scripts change an existing HUD icon through setIcon. */
	public function setIcon(char:String):Dynamic
		return switchAnim(char);

	/**
	 * V-Slice HealthIcon configuration ABI.  Imported HXC song scripts pass a
	 * small anonymous descriptor rather than calling the donor constructor
	 * directly; keep that operation on the native icon so the callback remains
	 * safe even when the authored icon falls back to iconGrid.
	 */
	public function configure(data:Dynamic):HealthIcon {
		if (data == null)
			return this;
		var id:Dynamic = Reflect.field(data, 'id');
		if (id != null && StringTools.trim(Std.string(id)) != ''
			&& Std.string(id) != curCharacter)
			switchAnim(Std.string(id));
		var iconScale:Dynamic = Reflect.field(data, 'scale');
		if (iconScale != null) {
			var parsedScale = Std.parseFloat(Std.string(iconScale));
			if (!Math.isNaN(parsedScale) && parsedScale > 0)
				scale.set(parsedScale, parsedScale);
		}
		var iconOffsets:Dynamic = Reflect.field(data, 'offsets');
		if (iconOffsets != null && Std.isOfType(iconOffsets, Array)) {
			var values:Array<Dynamic> = cast iconOffsets;
			var xOffset = values.length > 0 && values[0] != null
				? Std.parseFloat(Std.string(values[0])) : 0;
			var yOffset = values.length > 1 && values[1] != null
				? Std.parseFloat(Std.string(values[1])) : 0;
			if (Math.isNaN(xOffset)) xOffset = 0;
			if (Math.isNaN(yOffset)) yOffset = 0;
			offset.set(xOffset, yOffset);
		}
		var pixel:Dynamic = Reflect.field(data, 'isPixel');
		if (pixel != null)
			antialiasing = pixel != true;
		var shouldFlip:Dynamic = Reflect.field(data, 'flipX');
		if (shouldFlip != null)
			flipX = shouldFlip == true;
		return this;
	}

	public function loadIcon(iconName:String):Future<HealthIcon> {
		final daData:IconData = getIconFromJsons(iconName, iconOwnerRoot);
		if (daData == null) {
			switchAnim(iconName);
			return Future.withValue(this);
		}
		final daJson = daData.json;
		var daFrame = 0;
		if (daJson != null && Reflect.hasField(daJson, 'icons'))
			daFrame = daJson.icons[0];

		final charPath = daData.assetRoot + daData.path + '/';
		// The chart editor builds its character picker from the full registry,
		// including entries that intentionally have no health strip. Match
		// switchAnim's established missing-icon fallback instead of starting a
		// disk load that throws synchronously for those entries.
		if (!FNFAssets.exists(charPath + "icons.png")) {
			switchAnim(iconName);
			return Future.withValue(this);
		}
		return FNFAssets.loadBitmapData(charPath + "icons.png")
			.then(function(image) {
				if (FNFAssets.exists(charPath + "icons.xml")) {
					frames = DynamicSprite.DynamicAtlasFrames.fromSparrow(charPath + 'icons.png', charPath + 'icons.xml');
					animation.addByPrefix('icon', 'normal', 24, true);
				} else {
					loadGraphic(image, true, 150, 150);
					animation.add('icon', [daFrame], false);
				}
				animation.play('icon');
				return Future.withValue(this);
			}).onComplete(function(icon) { return icon; });
	}

	static function getIconFromJsons(char:String, ?ownerRoot:String):IconData {
		missingIconReference = '';
		var scopeRoot = ownerRoot == null ? Song.currentCharacterRoot() : ownerRoot;
		var assetRoot = 'assets/images/custom_chars/';
		var daChar:Dynamic = null;
		var iconPath = char;
		if (scopeRoot != '') {
			daChar = Song.characterVisualRegistryEntryInManifest(char, scopeRoot);
			if (daChar != null)
				assetRoot = scopeRoot + '/images/custom_chars/';
		}
		if (daChar == null) {
			var globalKey = globalIconRegistryKey(char);
			if (globalKey != null) {
				daChar = getIconJson(globalKey);
				iconPath = globalKey;
			}
		}
		if (daChar == null) return null;

		if ((daChar.icons is String)) {
			iconPath = daChar.icons;
			var scopedAlias:Dynamic = scopeRoot == '' ? null
				: Song.characterVisualRegistryEntryInManifest(iconPath, scopeRoot);
			if (scopedAlias != null) {
				daChar = scopedAlias;
				assetRoot = scopeRoot + '/images/custom_chars/';
			} else {
				var aliasKey = globalIconRegistryKey(iconPath);
				daChar = aliasKey == null ? null : getIconJson(aliasKey);
				if (daChar != null) {
					iconPath = aliasKey;
					assetRoot = 'assets/images/custom_chars/';
				}
			}
			// A character registry entry can name a separate logical health icon.
			// Treat a missing alias target as a missing dependency, rather than
			// returning a half-valid IconData record that suppresses diagnostics.
			if (daChar == null)
				missingIconReference = iconPath;
			if (daChar == null)
				return null;
		}

		return {path: iconPath, json: daChar, assetRoot: assetRoot};
	}

	/** Registry keys and on-disk character folders may use different case than
	 * the authored healthIcon id. Keep exact matches first and reject ambiguous
	 * case-insensitive matches instead of picking another character's art. */
	static function iconRegistryKey(registry:Dynamic, requested:String):String {
		if (registry == null || requested == null || StringTools.trim(requested) == '')
			return null;
		if (Reflect.hasField(registry, requested)) return requested;
		var wanted = requested.toLowerCase();
		var match:String = null;
		for (key in Reflect.fields(registry)) {
			if (key.toLowerCase() != wanted) continue;
			if (match != null) return null;
			match = key;
		}
		return match;
	}

	static function globalIconRegistryKey(requested:String):String {
		var key = iconRegistryKey(charJson, requested);
		return key == null ? iconRegistryKey(iconJson, requested) : key;
	}

	static function getIconJson(char:String):Dynamic {
		var daChar:Dynamic = null;
		if (Reflect.hasField(charJson, char))
			daChar = Reflect.field(charJson, char);
		else if (Reflect.hasField(iconJson, char))
			daChar = Reflect.field(iconJson, char);

		return daChar;
	}

	override function update(elapsed:Float):Void {
		super.update(elapsed);
		reportDeferredIconDiagnostic();

		if (sprTracker != null)
			setPosition(sprTracker.x + sprTracker.width + 10, sprTracker.y - 30);

		if (interp != null)
			callInterp("update", [elapsed, this])
		else if (codenameBop)
			updateBump()
		else if (isNormal) {
			setGraphicSize(Std.int(FlxMath.lerp(bopBaseSize, width, 0.50)));
			updateHitbox();
		}
	}

	public function dance():Void {
		if (interp != null)
			callInterp("dance", [this]);
		else if (codenameBop)
			bump();
		else if (isNormal) {
			setGraphicSize(Std.int(width + bopPulseSize()));
			updateHitbox();
		}
	}

	public function bopPulseSize():Int {
		return Std.int(Math.max(1, Math.round(bopBaseSize * 0.2)));
	}

	public function bopReset():Void {
		if (interp != null)
			callInterp("bopReset", [this]);
		else if (isNormal) {
			setGraphicSize(bopBaseSize);
			updateHitbox();
		}	
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
		}
	}

	public function changeIconBop(bopIcon:String) {
		interp = HealthIcon.iconBop(bopIcon);
	}

	public static function iconBop(bopIcon:String):Interp {
		var interp = PluginManager.createSimpleInterp();
		var parser = new hscript.Parser();
		var program:Expr;
		if (FNFAssets.exists('assets/images/custom_chars/iconbops/' + bopIcon, Hscript)) {
			program = parser.parseString(FNFAssets.getHscript('assets/images/custom_chars/iconbops/' + bopIcon));
			interp.variables.set("hscriptPath", 'assets/images/custom_chars/iconbops/' + bopIcon + '/');
			interp.variables.set("PlayState", PlayState);
			interp.variables.set("dance", function(icon) {});
			interp.variables.set("update", function(elapsed, icon) {});
			interp.variables.set("getUV", function(variabull:String) {
				if (PlayState.universalVar.exists(variabull))
					return PlayState.universalVar.get(variabull);
				else
					return null;
			});

			interp.variables.set("updateUV", function(variabull:String, veryable:Dynamic) {
				PlayState.universalVar[variabull] = veryable;
			});
			interp.execute(program);
		}
		trace(interp);
		return interp;
	}
}
