package;

using StringTools;

#if sys
import sys.FileSystem;
#end
import haxe.io.Path;

/**
	Small runtime services shared by generated HXC adapters.

	The donor's Save/Preferences objects are process-wide native singletons.  A
	generated HXC script must not be given those objects directly: doing so would
	let an imported module read or mutate unrelated engine data.  This adapter
	keeps a namespaced, in-memory view instead.  The namespace is selected by the
	translator for each foreign script, so two imported roots cannot accidentally
	share keys unless the caller explicitly gives them the same namespace.
*/
class HxcCompatRuntime {
	/** Cameras constructed by HXC remain engine-owned after FlxG insertion. */
	static var hxcFunkinCameras:Array<Dynamic> = [];

	/** Native pooled point for a source-declared HXC class field initializer. */
	#if flixel
	public static function point(x:Float = 0, y:Float = 0):flixel.math.FlxPoint
		return flixel.math.FlxPoint.get(x, y);
	#end

	/**
		Provide the small ReflectUtil surface used by imported V-Slice scripts.
		Imports are metadata in HXC, so the HScript interpreter needs an explicit
		facade for the class-name and anonymous-field queries that remain after
		translation.  Keep class-name aliases limited to native equivalents whose
		old fully-qualified names are present in the mounted HXC corpus.
	*/
	public static function reflectUtilFacade():Dynamic {
		return {
			getClassNameOf: function(value:Dynamic):String {
				if (value == null)
					return null;
				var classType = Type.getClass(value);
				if (classType == null)
					return null;
				var className = Type.getClassName(classType);
				if (className == 'StoryMenuState' || StringTools.endsWith(className, '.StoryMenuState'))
					return 'funkin.ui.story.StoryMenuState';
				if (className == 'FreeplayState' || StringTools.endsWith(className, '.FreeplayState'))
					return 'funkin.ui.freeplay.FreeplayState';
				return className;
			},
			getAnonymousField: function(value:Dynamic, fieldName:Dynamic):Dynamic {
				return value == null || fieldName == null ? null : Reflect.field(value, Std.string(fieldName));
			}
		};
	}

	/** Evaluate generated HXC null-coalescing operands lazily in menu scopes. */
	public static function hxcCoalesce(left:Dynamic, right:Dynamic):Dynamic {
		var value = Reflect.isFunction(left) ? Reflect.callMethod(null, left, []) : left;
		if (value != null)
			return value;
		return Reflect.isFunction(right) ? Reflect.callMethod(null, right, []) : right;
	}

	/** Materialize a generated HXC map literal without donor classes. */
	public static function hxcMap(entries:Array<Dynamic>):Dynamic {
		return new HxcDynamicMap(entries);
	}

	/** Read one sprite pixel through the native integer-coordinate bitmap API. */
	public static function spritePixelColor32(sprite:Dynamic, x:Dynamic, y:Dynamic):Int {
		if (sprite == null)
			return 0;
		var pixels = runtimeField(sprite, 'pixels');
		if (pixels == null)
			return 0;
		var getPixel32 = runtimeField(pixels, 'getPixel32');
		if (getPixel32 == null || !Reflect.isFunction(getPixel32))
			return 0;
		var pixelX = spritePixelCoordinate(x);
		var pixelY = spritePixelCoordinate(y);
		if (pixelX < 0 || pixelY < 0)
			return 0;
		var width = runtimeField(pixels, 'width');
		var height = runtimeField(pixels, 'height');
		if ((width != null && pixelX >= runtimeIntValue(width))
			|| (height != null && pixelY >= runtimeIntValue(height)))
			return 0;
		try {
			var color:Dynamic = Reflect.callMethod(pixels, getPixel32, [pixelX, pixelY]);
			return color == null ? 0 : runtimeIntValue(color);
		} catch (_:Dynamic) {
			return 0;
		}
	}

	static function spritePixelCoordinate(value:Dynamic):Int {
		if (value == null)
			return -1;
		var parsed:Float;
		if (Std.isOfType(value, Float) || Std.isOfType(value, Int))
			parsed = cast value;
		else
			parsed = Std.parseFloat(Std.string(value));
		if (Math.isNaN(parsed) || parsed < 0 || parsed > 2147483647.0)
			return -1;
		return Std.int(parsed);
	}

	static var stores:Map<String, Dynamic> = new Map<String, Dynamic>();
	/**
		V-Slice exposes zIndex on every display object.  Flixel's native
		FlxSprite/FlxText classes do not carry that donor field, so translated HXC
		accesses keep their value in this bounded engine-owned side table.  Stage
		objects are mirrored into StageHelper's z-order map as well; HUD objects
		still get a stable value for later reads without pretending that Flixel's
		global member list has a donor display-list implementation.
	*/
	// Keep this side table self-contained: the importer diagnostics copy this
	// runtime into an isolated fixture without the rest of source/.  A pair of
	// arrays preserves object identity on both interp and native targets.
	static var zIndexKeys:Array<Dynamic> = [];
	static var zIndexValues:Array<Int> = [];
	static var constantsViews:Map<String, Dynamic> = new Map<String, Dynamic>();
	static var preferencesView:Dynamic;
	static var talliesView:HxcCompatTallyView;
	static var activeState:Dynamic;
	/** Donor CharacterType values carried until the canonical PlayState bridge. */
	static var characterTypeHints:Array<Dynamic> = [];
	/**
		Per-song game-over/pause audio selections written by imported HXC
		character callbacks.  The donor exposes these as static fields on its
		substates; keeping the values here gives the native substates one bounded
		engine-owned hand-off without exposing donor classes to HScript.
	*/
	static var gameOverMusicSuffixValue:String = '';
	static var gameOverBlueBallSuffixValue:String = '';
	static var pauseMusicSuffixValue:String = '';
	/** Current chart variation exposed to imported character hooks. */
	static var currentVariationValue:String = '';
	/** Window-close requests are deliberately bounded to a no-op. */
	static var windowCloseDiagnosticShown:Bool = false;
	/** Process-local metadata views used by generic imported HXC modules. */
	static var creditsEntriesValue:Array<Dynamic> = [];
	static var discordRPCIconValue:String = '';
	static var discordRPCAlbumValue:String = '';
	static var currentChartAlbumValue:String = '';
	/** Process-local geometry view for V-Slice's FullScreenScaleMode singleton. */
	static var fullScreenScaleModeView:Dynamic;
	static var skipNextTransInValue:Bool = false;
	static var skipNextTransOutValue:Bool = false;
	/** Native owner of the currently mounted menu overlay, if any. */
	static var activeMenuOverlayState:Dynamic;
	/** Native owner of the currently mounted pause overlay, if any. */
	static var activePauseOverlayState:Dynamic;
	/**
		Compatibility dimensions retained for V-Slice's static Strumline fields.
		The native receptor group owns its real geometry; imported teardown code may
		read/write these bounded values without replacing that group or touching the
		extra-note adapter's private queues.
	*/
	static var strumlineSizeValue:Float = 104;
	static var noteSpacingValue:Float = 112;

	public static var strumlineSize(get, set):Float;
	static function get_strumlineSize():Float
		return strumlineSizeValue;
	static function set_strumlineSize(value:Float):Float {
		if (!Math.isNaN(value) && value > 0 && value <= 4096)
			strumlineSizeValue = value;
		return strumlineSizeValue;
	}

	public static var noteSpacing(get, set):Float;
	static function get_noteSpacing():Float
		return noteSpacingValue;
	static function set_noteSpacing(value:Float):Float {
		if (!Math.isNaN(value) && value > 0 && value <= 4096)
			noteSpacingValue = value;
		return noteSpacingValue;
	}

	public static var creditsEntries(get, never):Array<Dynamic>;
	static function get_creditsEntries():Array<Dynamic>
		return creditsEntriesValue;

	public static var discordRPCIcon(get, set):String;
	static function get_discordRPCIcon():String
		return discordRPCIconValue;
	static function set_discordRPCIcon(value:String):String {
		discordRPCIconValue = value == null ? '' : value;
		return discordRPCIconValue;
	}

	public static var discordRPCAlbum(get, set):String;
	static function get_discordRPCAlbum():String
		return discordRPCAlbumValue;
	static function set_discordRPCAlbum(value:String):String {
		discordRPCAlbumValue = value == null ? '' : value;
		return discordRPCAlbumValue;
	}

	/** Read the album from the live native chart while keeping a standalone fallback. */
	public static var currentChartAlbum(get, never):String;
	static function get_currentChartAlbum():String {
		try {
			var stateClass = Type.resolveClass('PlayState');
			if (stateClass != null) {
				var chart = Reflect.field(stateClass, 'SONG');
				var album = chart == null ? null : Reflect.field(chart, 'album');
				if (album != null)
					return Std.string(album);
			}
		} catch (_:Dynamic) {}
		return currentChartAlbumValue;
	}

	/** Desktop-native HXC modules use this only as a constructor guard. */
	public static var onMobile(get, never):Bool;
	static function get_onMobile():Bool
		return false;

	/**
		V-Slice song/stage scripts read the donor StageData through
		`PlayState.instance.currentStage._data` (DDTO's extra-opponent setup uses
		`_data.characters.dad.position` and `.cameraOffsets`). The native
		StageHelper already keeps those values in its persistent slot info, so
		rebuild the donor-shaped view from that instead of retaining the raw
		donor JSON. Reads go through reflection to stay standalone-testable.
	*/
	public static function stageDataSnapshot():Dynamic {
		var characters:Dynamic = {};
		for (role in ['dad', 'bf', 'gf'])
			Reflect.setField(characters, role, stageCharacterData(role));
		return {characters: characters};
	}

	public static function stageCharacterData(role:String):Dynamic {
		var normalized = switch (role == null ? '' : role.toLowerCase()) {
			case 'bf' | 'boyfriend' | 'player': 'bf';
			case 'gf' | 'girlfriend': 'gf';
			case 'dad' | 'opponent': 'dad';
			default: role;
		}
		var info:Dynamic = null;
		try {
			var stateClass = Type.resolveClass('PlayState');
			var instance = stateClass == null ? null : Reflect.field(stateClass, 'instance');
			var stage = instance == null ? null : Reflect.field(instance, 'curStage');
			if (stage != null)
				info = Reflect.callMethod(stage, Reflect.field(stage, 'getInfo'), [normalized]);
		} catch (_:Dynamic) {}
		if (info == null)
			info = {x: 0, y: 0, camOffsetX: 0, camOffsetY: 0, scrollFactor: {x: 1, y: 1}, zIndex: 0};
		var scroll = info.scrollFactor == null ? {x: 1, y: 1} : info.scrollFactor;
		return {
			position: [info.x, info.y],
			cameraOffsets: [info.camOffsetX, info.camOffsetY],
			scroll: [scroll.x, scroll.y],
			zIndex: info.zIndex,
			alpha: 1,
			angle: 0,
			scale: 1
		};
	}

	/**
		Read-only Conductor timing aliases used by V-Slice HXC scripts. These
		properties deliberately read the native static fields through reflection so
		the compatibility layer remains standalone-testable and never exposes an
		arbitrary Conductor object or update method to imported code.
	*/
	public static var conductorStepLengthMs(get, never):Float;
	static function get_conductorStepLengthMs():Float
		return conductorNumber('stepCrochet');

	public static var conductorBeatLengthMs(get, never):Float;
	static function get_conductorBeatLengthMs():Float
		return conductorNumber('crochet');

	public static var conductorSongPosition(get, never):Float;
	static function get_conductorSongPosition():Float
		return conductorNumber('songPosition');

	/** Native Conductor.offset is this fork's bounded combined timing offset. */
	public static var conductorCombinedOffset(get, never):Float;
	static function get_conductorCombinedOffset():Float
		return conductorNumber('offset');

	/**
		Bound the donor Conductor.update facade to the native static clock. The
		old engine exposes a mutable singleton, while this fork keeps timing in
		PlayState/Conductor fields. A numeric argument is accepted only within a
		reasonable song-time range; a no-argument update is intentionally a no-op
		because MusicBeatState already advances the native clock every frame.
	*/
	public static function conductorUpdate(?position:Dynamic):Void {
		if (position == null)
			return;
		var numeric = runtimeFloatValue(position);
		if (Math.isNaN(numeric) || numeric < -86400000 || numeric > 86400000)
			return;
		try {
			var conductor = Type.resolveClass('Conductor');
			if (conductor == null)
				return;
			var previous = Reflect.field(conductor, 'songPosition');
			Reflect.setField(conductor, 'lastSongPos', previous == null ? numeric : previous);
			Reflect.setField(conductor, 'songPosition', numeric);
		} catch (_:Dynamic) {}
	}

	/**
		Data-only replacement for V-Slice's process-wide fullscreen geometry
		singleton. This engine has no cutout-safe mobile viewport, so the native
		defaults are zero cutout and unit-wide scale. `enabled` remains mutable in
		the isolated view and `removeCutouts()` is a bounded no-op.
	*/
	public static var fullScreenScaleMode(get, never):Dynamic;
	static function get_fullScreenScaleMode():Dynamic {
		if (fullScreenScaleModeView == null)
			fullScreenScaleModeView = {
				enabled: true,
				gameCutoutSize: {x: 0.0, y: 0.0},
				wideScale: {x: 1.0, y: 1.0},
				removeCutouts: function() {}
			};
		return fullScreenScaleModeView;
	}

	static function conductorNumber(field:String):Float {
		try {
			var conductor = Type.resolveClass('Conductor');
			if (conductor != null) {
				var value = Reflect.field(conductor, field);
				if (value != null)
					return runtimeFloatValue(value);
			}
		} catch (_:Dynamic) {}
		return 0;
	}

	/** PlayStatePlaylist.isStoryMode maps to the native static story flag. */
	public static var playStatePlaylistIsStoryMode(get, never):Bool;
	static function get_playStatePlaylistIsStoryMode():Bool {
		try {
			var stateClass = Type.resolveClass('PlayState');
			if (stateClass != null)
				return Reflect.field(stateClass, 'isStoryMode') == true;
		} catch (_:Dynamic) {}
		var state = activeState != null ? activeState : resolveActiveState();
		return runtimeField(state, 'isStoryMode') == true;
	}

	/** Native extra-event gates used by imported lyric/vignette modules. */
	public static var lyricsEnabled(get, never):Bool;
	static function get_lyricsEnabled():Bool {
		var options = nativeOptions();
		var value = options == null ? null : runtimeField(options, 'lyricsEnabled');
		return value == null ? true : value == true;
	}

	public static var vignetteEffects(get, never):Bool;
	static function get_vignetteEffects():Bool {
		var options = nativeOptions();
		var value = options == null ? null : runtimeField(options, 'vignetteEffects');
		return value == null ? true : value == true;
	}

	/** Standalone-safe wall-clock timestamp for presence URL cache-busting. */
	public static function timestamp():Float {
		return Date.now().getTime();
	}

	/** HXC's Date.now().getDay() uses the host's local Sunday-based weekday. */
	public static function weekday():Int {
		return Date.now().getDay();
	}

	/**
		Run a camera flash authored by an HXC song-event callback and claim the
		native event operation at the same time.  HXC stage callbacks run before
		PlayState's native event switch; without this small ownership boundary a
		donor callback which directly flashes its camera would be followed by the
		canonical Camera Flash route and apply the same effect twice.  The helper
		uses reflection so standalone HXC tests can provide a tiny fake camera and
		the runtime does not expose Flixel types to the compatibility layer.
	*/
	public static function hxcCameraFlash(event:Dynamic, camera:Dynamic, color:Dynamic,
		duration:Dynamic, ?force:Dynamic):Dynamic {
		var applied = false;
		if (camera != null) {
			try {
				var flash = Reflect.field(camera, 'flash');
				if (flash != null) {
					Reflect.callMethod(camera, flash, [color, duration, force == null ? false : force]);
					applied = true;
				}
			} catch (_:Dynamic) {}
		}
		if (applied)
			markSongEventNativeHandled(event);
		return camera;
	}

	/** Claim only the native side of a shared HXC song event. */
	public static function markSongEventNativeHandled(event:Dynamic):Void {
		if (event == null)
			return;
		try {
			Reflect.setField(event, 'nativeHandled', true);
			Reflect.setField(event, 'handled', true);
			var data = Reflect.field(event, 'eventData');
			if (data != null) {
				Reflect.setField(data, 'nativeHandled', true);
				Reflect.setField(data, 'handled', true);
			}
		} catch (_:Dynamic) {}
	}

	static function nativeOptions():Dynamic {
		try {
			var optionsClass = Type.resolveClass('OptionsHandler');
			return optionsClass == null ? null : Reflect.field(optionsClass, 'options');
		} catch (_:Dynamic) {
			return null;
		}
	}

	public static var skipNextTransIn(get, set):Bool;
	static function get_skipNextTransIn():Bool
		return skipNextTransInValue;
	static function set_skipNextTransIn(value:Bool):Bool {
		skipNextTransInValue = value;
		return value;
	}

	public static var skipNextTransOut(get, set):Bool;
	static function get_skipNextTransOut():Bool
		return skipNextTransOutValue;
	static function set_skipNextTransOut(value:Bool):Bool {
		skipNextTransOutValue = value;
		return value;
	}

	public static var gameOverMusicSuffix(get, never):String;
	static function get_gameOverMusicSuffix():String
		return gameOverMusicSuffixValue;

	public static var gameOverBlueBallSuffix(get, never):String;
	static function get_gameOverBlueBallSuffix():String
		return gameOverBlueBallSuffixValue;

	public static var pauseMusicSuffix(get, never):String;
	static function get_pauseMusicSuffix():String
		return pauseMusicSuffixValue;

	/** Generic HXC variation plumbing; charts without a variation use empty text. */
	public static var currentVariation(get, set):String;
	static function get_currentVariation():String {
		var state = activeState != null ? activeState : resolveActiveState();
		var value = runtimeField(state, 'currentVariation');
		return value == null ? currentVariationValue : Std.string(value);
	}
	static function set_currentVariation(value:String):String {
		currentVariationValue = value == null ? '' : value;
		return currentVariationValue;
	}

	/** Reset the imported audio selection at the beginning of every native song. */
	public static function resetGameOverSettings():Void {
		gameOverMusicSuffixValue = '';
		gameOverBlueBallSuffixValue = '';
		pauseMusicSuffixValue = '';
		currentVariationValue = '';
		windowCloseDiagnosticShown = false;
	}

	/** Setters used by the centralized HXC source lowering pass. */
	public static function setGameOverMusicSuffix(value:Dynamic):String {
		gameOverMusicSuffixValue = value == null ? '' : Std.string(value);
		return gameOverMusicSuffixValue;
	}

	public static function setGameOverBlueBallSuffix(value:Dynamic):String {
		gameOverBlueBallSuffixValue = value == null ? '' : Std.string(value);
		return gameOverBlueBallSuffixValue;
	}

	public static function setPauseMusicSuffix(value:Dynamic):String {
		pauseMusicSuffixValue = value == null ? '' : Std.string(value);
		return pauseMusicSuffixValue;
	}

	/**
		Resolve the donor's suffix convention against assets actually owned by the
		native runtime.  Missing imported variants fall back to the normal native
		track, and the existing pixel fallback remains intact.
	*/
	public static function resolveGameOverTrack(asset:String, directory:String,
		?pixel:Bool = false, ?ending:Bool = false):String {
		var value = asset == null || StringTools.trim(asset) == ''
			? (ending ? 'gameOverEnd.ogg' : 'gameOver.ogg') : asset;
		var suffix = gameOverMusicSuffixValue;
		if (suffix != null && suffix != '' && isDefaultGameOverTrack(value, ending)) {
			var withSuffix = appendTrackSuffix(value, suffix);
			if (trackExists(directory, withSuffix))
				return withSuffix;
		}
		if (pixel && isDefaultGameOverTrack(value, ending)) {
			var pixelValue = appendTrackSuffix(value, '-pixel');
			if (trackExists(directory, pixelValue))
				return pixelValue;
		}
		return value;
	}

	/** Resolve the donor blue-ball/death SFX suffix with the native pixel fallback. */
	public static function resolveBlueBallTrack(asset:String, directory:String,
		?pixel:Bool = false):String {
		var value = asset == null || StringTools.trim(asset) == '' ? 'fnf_loss_sfx.ogg' : asset;
		var suffix = gameOverBlueBallSuffixValue;
		if (suffix != null && suffix != '') {
			var withSuffix = appendTrackSuffix(value, suffix);
			if (trackExists(directory, withSuffix))
				return withSuffix;
		}
		if (pixel) {
			var pixelValue = appendTrackSuffix(value, '-pixel');
			if (trackExists(directory, pixelValue))
				return pixelValue;
		}
		return value;
	}

	static function isDefaultGameOverTrack(value:String, ending:Bool):Bool {
		return value == (ending ? 'gameOverEnd.ogg' : 'gameOver.ogg');
	}

	static function appendTrackSuffix(value:String, suffix:String):String {
		if (value == null || suffix == null || suffix == '')
			return value;
		var extension = '';
		var stem = value;
		var dot = value.lastIndexOf('.');
		if (dot >= 0) {
			extension = value.substr(dot);
			stem = value.substr(0, dot);
		}
		return stem + suffix + extension;
	}

	static function trackExists(directory:String, value:String):Bool {
		if (value == null || value == '')
			return false;
		var root = directory == null || directory == '' ? 'assets/music' : directory;
		var path = root + '/' + value;
		// Resolve the asset manifest lazily so standalone HXC/import fixtures do
		// not have to pull the native OpenFL asset layer into an eval build.
		try {
			var assetsClass = Type.resolveClass('FNFAssets');
			var exists = assetsClass == null ? null : Reflect.field(assetsClass, 'exists');
			if (exists != null)
				return Reflect.callMethod(assetsClass, exists, [path]) == true;
		} catch (_:Dynamic) {}
		#if sys
		return FileSystem.exists(path);
		#else
		return false;
		#end
	}

	/**
		The only HXC highscore surface exposed by the native runtime.  It is a
		view over the active PlayState rather than the engine's persistent
		Highscore maps, so imported modules cannot read or mutate unrelated song
		saves. The fields mirror only native per-song counters; no persistent donor
		score table is exposed.
	*/
	public static var tallies(get, never):Dynamic;
	static function get_tallies():Dynamic {
		ensureActiveState();
		if (talliesView == null)
			talliesView = new HxcCompatTallyView();
		return talliesView;
	}

	/** Bind the tally view to a live PlayState (or a test double). */
	public static function bindActiveState(state:Dynamic):Void {
		if (activeState != state)
			clearConstantsViews();
		if (activeState == state && talliesView != null)
			return;
		activeState = state;
		if (talliesView == null)
			talliesView = new HxcCompatTallyView();
		talliesView.bind(state);
	}

	/**
		Start a fresh gameplay tally. PlayState resets its native miss counter
		before countdown; seeding here therefore also gives retry a clean view.
		The optional state exists for standalone compatibility fixtures.
	*/
	public static function beginActiveSong(?state:Dynamic):Void {
		if (state != null)
			bindActiveState(state);
		else
			ensureActiveState();
		if (talliesView == null)
			talliesView = new HxcCompatTallyView();
		talliesView.beginSong();
	}

	/** Observe an incoming native note before HXC callbacks can mutate it. */
	public static function observeIncoming(note:Dynamic):Void {
		ensureActiveState();
		if (talliesView == null)
			talliesView = new HxcCompatTallyView();
		talliesView.observeIncoming(note);
	}

	/** Prepare the shared plain-field view immediately before one HXC callback. */
	public static function prepareTallyCallback():Void {
		ensureActiveState();
		if (talliesView != null)
			talliesView.syncBeforeCallback();
	}

	/** Commit the shared plain-field view after one HXC callback. */
	public static function commitTallyCallback():Void {
		if (talliesView != null)
			talliesView.syncAfterCallback();
	}

	/** Drop active-song tally state without touching persistent engine scores. */
	public static function clearActiveState(?state:Dynamic):Void {
		if (state != null && activeState != state)
			return;
		var owner = state != null ? state : activeState;
		if (owner != null) {
			var clearShaders = runtimeField(owner, 'hxcClearRuntimeShaderBindings');
			if (clearShaders != null && Reflect.isFunction(clearShaders))
				try Reflect.callMethod(owner, clearShaders, []) catch (_:Dynamic) {}
		}
		activeState = null;
		clearConstantsViews();
		zIndexKeys = [];
		zIndexValues = [];
		characterTypeHints = [];
		// A PlayState can be destroyed before another song is created (for
		// example when returning to Freeplay). Do not let a character's audio
		// selection leak into a later state or pause menu.
		resetGameOverSettings();
		if (talliesView != null)
			talliesView.clear();
	}

	static function ensureActiveState():Dynamic {
		var current = resolveActiveState();
		if (current != null && current != activeState)
			bindActiveState(current);
		return activeState;
	}

	/** Resolve PlayState.instance without making the isolated HXC fixture import Flixel. */
	static function resolveActiveState():Dynamic {
		try {
			var stateClass = Type.resolveClass('PlayState');
			if (stateClass != null)
				return Reflect.field(stateClass, 'instance');
		} catch (_:Dynamic) {}
		return null;
	}

	/**
		Read the V-Slice display-list ordering field without requiring every native
		Flixel object to grow a donor-only `zIndex` member.  StageHelper owns the
		actual ordering for stage objects; the side table covers HUD sprites and
		other dynamic objects which are not registered with a stage.
	*/
	public static function getZIndex(target:Dynamic):Dynamic {
		if (target == null)
			return 0;
		var nativeValue = runtimeField(target, 'zIndex');
		if (nativeValue != null)
			return nativeValue;
		var storedIndex = zIndexIndex(target);
		if (storedIndex >= 0)
			return zIndexValues[storedIndex];
		var stage = activeStageForZIndex();
		if (stage != null) {
			var getter = runtimeField(stage, 'getZIndexForElement');
			if (getter != null && Reflect.isFunction(getter))
				try {
					var result = Reflect.callMethod(stage, getter, [target]);
					if (result != null)
						return result;
				} catch (_:Dynamic) {}
		}
		return 0;
	}

	/**
		Write a V-Slice zIndex through the native stage ordering map when one is
		available, while retaining a value for objects owned by HUD/gameplay code.
		The operator argument is emitted by the HXC property rewriter and keeps
		compound assignments (`+=`, `-=`, etc.) equivalent to the donor field.
	*/
	public static function setZIndex(target:Dynamic, value:Dynamic, ?assignmentOperator:String = '='):Dynamic {
		if (target == null)
			return null;
		var current = runtimeIntValue(getZIndex(target));
		var next = runtimeIntValue(value);
		switch (assignmentOperator) {
			case '+=': next = current + next;
			case '-=': next = current - next;
			case '*=': next = current * next;
			case '/=': if (next != 0) next = Std.int(current / next);
		}
		var storedIndex = zIndexIndex(target);
		if (storedIndex < 0) {
			zIndexKeys.push(target);
			zIndexValues.push(next);
		} else {
			zIndexValues[storedIndex] = next;
		}
		try {
			if (Reflect.hasField(target, 'zIndex'))
				Reflect.setField(target, 'zIndex', next);
		} catch (_:Dynamic) {}
		var stage = activeStageForZIndex();
		if (stage != null) {
			var setter = runtimeField(stage, 'setZIndex');
			if (setter != null && Reflect.isFunction(setter))
				try Reflect.callMethod(stage, setter, [target, next]) catch (_:Dynamic) {}
		}
		return next;
	}

	static function activeStageForZIndex():Dynamic {
		var state = activeState != null ? activeState : resolveActiveState();
		if (state == null)
			return null;
		var stage = runtimeField(state, 'curStage');
		if (stage == null)
			stage = runtimeField(state, 'currentStage');
		return stage;
	}

	static function zIndexIndex(target:Dynamic):Int {
		for (index in 0...zIndexKeys.length)
			if (zIndexKeys[index] == target)
				return index;
		return -1;
	}
	/**
		Small mutable replacement for the common V-Slice `Constants` bag.  These
		values are engine defaults, not donor state; keeping the object namespaced
		also means an imported module cannot resolve arbitrary foreign classes.
	*/
	public static var constants(get, never):Dynamic;
	static function get_constants():Dynamic {
		return constantsForRoot('assets');
	}

	/**
		Return the mutable Constants facade owned by one imported root in the
		current PlayState session. V-Slice modules extend the default difficulty
		array during initialization, so a process-global bag would leak those
		changes into later songs (and into another imported owner).
	*/
	public static function constantsForRoot(root:Dynamic):Dynamic {
		var current = resolveActiveState();
		if (current != null && current != activeState)
			bindActiveState(current);
		var owner = importedManifestRoot(root);
		var key = owner == '' ? '__native__' : owner;
		var view = constantsViews.get(key);
		if (view == null) {
			view = {
				TITLE: "CammieEngine",
				VERSION: engineVersion(),
				COLOR_HEALTH_BAR_GREEN: 0xFF66FF33,
				COLOR_HEALTH_BAR_RED: 0xFFFF0000,
				COUNTDOWN_VOLUME: 0.6,
				DEFAULT_CAMERA_FOLLOW_RATE: 0.04,
				DEFAULT_VARIATION: "default",
				PIXELS_PER_MS: 0.45,
				PIXEL_ART_SCALE: 6.0,
				STRUMLINE_X_OFFSET: 48.0,
				STRUMLINE_Y_OFFSET: 24.0,
				DEFAULT_DIFFICULTY_LIST_FULL: ["easy", "normal", "hard"]
			};
			constantsViews.set(key, view);
		}
		return view;
	}

	static function clearConstantsViews():Void {
		constantsViews = new Map<String, Dynamic>();
	}

	/**
		Read-only preference values with an explicit native fallback. This fork has
		no strumline-opacity setting, so imported modules see fully opaque strum
		backgrounds instead of reaching into a donor save singleton. Unknown
		Preferences fields remain diagnostics.
	*/
	public static var preferences(get, never):Dynamic;
	static function get_preferences():Dynamic {
		if (preferencesView == null)
			preferencesView = {strumlineBackgroundOpacity: 100.0};
		return preferencesView;
	}

	/**
		Conservative replacement for V-Slice's Scoring.calculateRank. Its plain
		tally input is the surface emitted by HXC adapters; the output uses the
		rank names consumed by the mounted score modules without claiming to match
		donor-specific weighted judgement maths.
	*/
	public static function calculateRank(data:Dynamic):String {
		if (data == null)
			return null;
		var tallies:Dynamic = runtimeField(data, 'tallies');
		if (tallies == null)
			tallies = data;
		var totalNotes = runtimeIntValue(runtimeField(tallies, 'totalNotes'));
		if (totalNotes <= 0)
			return null;
		var missed = runtimeIntValue(runtimeField(tallies, 'missed'));
		var good = runtimeIntValue(runtimeField(tallies, 'good'));
		var sick = runtimeIntValue(runtimeField(tallies, 'sick'));
		var completion:Float = (sick + good - missed) / totalNotes;
		if (completion < 0) completion = 0;
		if (completion > 1) completion = 1;
		// Match the mounted V-Slice scoring contract: an empty chart has no
		// rank, an all-sick chart is the gold rank, and the remaining thresholds
		// are based on the clamped successful-completion ratio.
		if (sick == totalNotes && good == 0 && missed == 0)
			return 'PERFECT_GOLD';
		if (completion >= 1) return 'PERFECT';
		if (completion >= 0.90) return 'EXCELLENT';
		if (completion >= 0.80) return 'GREAT';
		if (completion >= 0.60) return 'GOOD';
		return 'SHIT';
	}

	/** String predicate used by generated character animation adapters. */
	public static function stringContains(value:Dynamic, needle:Dynamic):Bool {
		if (value == null || needle == null)
			return false;
		return Std.string(value).indexOf(Std.string(needle)) >= 0;
	}

	/** Null-safe string predicate used by translated HXC member calls. */
	public static function stringStartsWith(value:Dynamic, prefix:Dynamic):Bool {
		if (value == null || prefix == null)
			return false;
		return StringTools.startsWith(Std.string(value), Std.string(prefix));
	}

	/**
		Apply a donor difficulty order to the native Freeplay selector.  The
		adapter accepts authored names but never constructs donor DifficultyDot or
		DotType instances; FreeplayState owns the actual integer selector and
		filters names against its native difficulty registry.
	*/
	public static function reorderFreeplayDifficulties(state:Dynamic,
		?order:Array<String>):Dynamic {
		if (state == null)
			return state;
		var method = runtimeField(state, 'hxcApplyDifficultyOrder');
		if (method != null)
			try return Reflect.callMethod(state, method, [order == null ? [] : order]) catch (_:Dynamic) {}
		return state;
	}

	/**
		Native menu back boundary for imported Freeplay callbacks.  It is safe to
		call from a generated HXC interpreter and does not expose the donor's
		mover/tween graph or transition singleton.
	*/
	public static function freeplayReturnToMenu(state:Dynamic):Bool {
		if (state == null)
			return false;
		var method = runtimeField(state, 'hxcReturnToMenu');
		if (method != null)
			try return Reflect.callMethod(state, method, []) == true catch (_:Dynamic) {}
		return false;
	}

	/**
		Bound the V-Slice Countdown facade to the active PlayState. The owner keeps
		the timer private and decides whether a skip starts the song immediately or
		merely cancels a pending timer; foreign HXC never receives that object.
	*/
	public static function skipCountdown(state:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcSkipCountdown');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, []) == true catch (_:Dynamic) return false;
	}

	public static function stopCountdown(state:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcStopCountdown');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, []) == true catch (_:Dynamic) return false;
	}

	/** Play one manifest-scoped HXC video through PlayState's native cutscene API. */
	public static function playVideoCutscene(state:Dynamic, filename:Dynamic,
		?ending:Bool = false):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcPlayImportedVideo');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [filename, ending == true]) == true
		catch (_:Dynamic) return false;
	}

	/** Construct a state-owned host for the structurally recognized HXC video module. */
	public static function createVideoModule(state:Dynamic, assetRoot:String):Dynamic {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return null;
		var method = runtimeField(owner, 'hxcCreateVideoModule');
		if (method == null || !Reflect.isFunction(method))
			return null;
		try return Reflect.callMethod(owner, method, [assetRoot])
		catch (_:Dynamic) return null;
	}

	public static function videoModuleDefaults(state:Dynamic, host:Dynamic):Dynamic
		return videoModuleHostCall(host, 'getDefaultConfig', []);

	public static function videoModuleCreateVideo(state:Dynamic, host:Dynamic,
		filename:Dynamic, config:Dynamic):Dynamic
		return videoModuleHostCall(host, 'createVideo', [filename, config]);

	public static function videoModuleCheckResync(state:Dynamic, host:Dynamic,
		video:Dynamic, instant:Dynamic, resume:Dynamic):Void {
		videoModuleHostCall(host, 'checkResync', [video, videoModuleBool(instant, false), videoModuleBool(resume, true)]);
	}

	public static function videoModuleClear(state:Dynamic, host:Dynamic):Void
		videoModuleHostCall(host, 'clearVideoSprites', []);

	public static function videoModuleDestroy(state:Dynamic, host:Dynamic):Void
		videoModuleHostCall(host, 'destroy', []);

	public static function videoModuleUpdate(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'update', [event]);

	public static function videoModuleFocusGained(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'focusGained', [event]);

	public static function videoModuleStepHit(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'stepHit', [event]);

	public static function videoModulePause(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'pause', [event]);

	public static function videoModuleResume(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'resume', [event]);

	public static function videoModuleSongRetry(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'songRetry', [event]);

	public static function videoModuleGameOver(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'gameOver', [event]);

	public static function videoModuleSongEnd(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'songEnd', [event]);

	public static function videoModuleCountdownStart(state:Dynamic, host:Dynamic, event:Dynamic):Void
		videoModuleHostCall(host, 'countdownStart', [event]);

	static function videoModuleHostCall(host:Dynamic, methodName:String, args:Array<Dynamic>):Dynamic {
		if (host == null || methodName == null)
			return null;
		var method = runtimeField(host, methodName);
		if (method == null || !Reflect.isFunction(method))
			return null;
		try return Reflect.callMethod(host, method, args == null ? [] : args)
		catch (_:Dynamic) return null;
	}

	static function videoModuleBool(value:Dynamic, fallback:Bool):Bool {
		if (value == null)
			return fallback;
		if (Std.isOfType(value, Bool))
			return cast value;
		var text = StringTools.trim(Std.string(value)).toLowerCase();
		return text == 'true' || text == '1' || text == 'yes' || text == 'on';
	}

	/** Route the donor player vocal bus to the native split-stem owner. */
	public static function setPlayerVocalVolume(state:Dynamic, volume:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcSetPlayerVocalVolume');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [runtimeFloatValue(volume)]) == true
		catch (_:Dynamic) return false;
	}

	public static function getPlayerVocalVolume(state:Dynamic):Float {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return 1;
		var method = runtimeField(owner, 'hxcGetPlayerVocalVolume');
		if (method == null || !Reflect.isFunction(method))
			return 1;
		try return runtimeFloatValue(Reflect.callMethod(owner, method, []))
		catch (_:Dynamic) return 1;
	}

	public static function opponentVocalTracks(state:Dynamic):Array<Dynamic> {
		var owner = state == null ? resolveActiveState() : state;
		var method = runtimeField(owner, 'hxcOpponentVocalTracks');
		if (method == null || !Reflect.isFunction(method)) return [];
		var tracks:Dynamic = Reflect.callMethod(owner, method, []);
		return Std.isOfType(tracks, Array) ? cast tracks : [];
	}

	/**
		Optional native boundary for a menu module's BACK handling.  The imported
		callback supplies only its bounded Freeplay view, save bag, and event; it
		never receives the donor Story/Freeplay object graph.  Hosts that do not
		expose this hook leave the ordinary native menu behavior unchanged.
	*/
	public static function updateMenuOverrides(state:Dynamic, save:Dynamic,
		event:Dynamic):Bool {
		if (save == null || runtimeField(save, 'menus') != true)
			return false;
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcHandleImportedMenuBack');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [event]) == true catch (_:Dynamic) return false;
	}

	/**
		Optional native boundary for state-change menu redirection.  The donor
		options/menu pages are deliberately opaque; a destination can implement
		this hook without exposing those collections to HScript.
	*/
	public static function applyMenuOverrides(state:Dynamic, store:Dynamic):Bool {
		if (state == null)
			return false;
		var method = runtimeField(state, 'hxcApplyImportedMenuOverrides');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, [store]) == true catch (_:Dynamic) return false;
	}

	/**
		Redirect-state helper fallback.  Imported state objects are selected-root
		values and must not replace FlxG.game._state directly; native hosts may
		consume the request through this optional hook instead.
	*/
	public static function applyMenuRedirect(state:Dynamic):Bool {
		if (state == null)
			return false;
		var method = runtimeField(state, 'hxcApplyImportedMenuRedirect');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, []) == true catch (_:Dynamic) return false;
	}

	/** Apply one manifest-scoped, literal Freeplay customization plan. */
	public static function applyFreeplayCustomization(state:Dynamic, capsule:Dynamic,
		plan:Dynamic):Bool {
		if (state == null || plan == null)
			return false;
		var method = runtimeField(state, 'hxcApplyImportedFreeplayCustomization');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, [capsule, plan]) == true catch (_:Dynamic) return false;
	}

	/**
		Route a positional two-line lyric request to the native PlayState owner.
		The positional shape is the stable part of the Wacky/V-Slice helper ABI;
		all FlxText construction, font validation, layering, and tween cleanup stay
		inside PlayState. Unknown or short payloads use the native lyric defaults.
	*/
	public static function setLyricText(state:Dynamic, values:Array<Dynamic>,
		?second:Bool = false):Bool {
		if (!lyricsEnabled)
			return false;
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcSetLyricText');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method,
			[values == null ? [] : values, second]) == true catch (_:Dynamic) return false;
	}

	/** Clear both native lyric lines without exposing donor FlxText objects. */
	public static function clearLyricText(state:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcClearLyricText');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, []) == true catch (_:Dynamic) return false;
	}

	/**
		Return the native pixel-UI decision used by the bounded song-credit
		adapter.  Imported HXC only receives this boolean; the stage/UI objects
		which contribute to it remain owned by PlayState.
	*/
	public static function songCreditsPixel(state:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcSongCreditsPixel');
		if (method != null && Reflect.isFunction(method))
			try return Reflect.callMethod(owner, method, []) == true catch (_:Dynamic) {}
		var stage = runtimeField(owner, 'currentStageId');
		return stage != null && Std.string(stage).toLowerCase().indexOf('pixel') >= 0;
	}

	/**
		Keep icon selection data-only.  The translated HXC body can pass only a
		literal identifier selected from its authored default/switch values; path
		separators and oversized keys are rejected before they reach the native
		manifest resolver.
	*/
	public static function songCreditsIcon(value:Dynamic):String {
		if (value == null)
			return '';
		var key = StringTools.trim(Std.string(value));
		if (key == '' || key.length > 48
			|| !new EReg('^[A-Za-z0-9_-]+$', '').match(key))
			return '';
		return key;
	}

	/** Show one native song-credit banner without exposing donor display objects. */
	public static function showSongCredits(state:Dynamic, songName:Dynamic,
		artist:Dynamic, pixel:Dynamic, iconKey:Dynamic, assetRoot:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcShowSongCredits');
		if (method == null || !Reflect.isFunction(method))
			return false;
		var key = songCreditsIcon(iconKey);
		try return Reflect.callMethod(owner, method, [songName, artist, pixel == true,
			key, assetRoot == null ? '' : Std.string(assetRoot)]) == true
		catch (_:Dynamic) return false;
	}

	/** Clear the active native song-credit banner, if one exists. */
	public static function clearSongCredits(state:Dynamic):Bool
		return callNativeSongCredits(state, 'hxcClearSongCredits');

	/** Pause only the native banner timer/tweens owned by the active PlayState. */
	public static function pauseSongCredits(state:Dynamic):Bool
		return callNativeSongCredits(state, 'hxcPauseSongCredits');

	/** Resume only the native banner timer/tweens owned by the active PlayState. */
	public static function resumeSongCredits(state:Dynamic):Bool
		return callNativeSongCredits(state, 'hxcResumeSongCredits');

	static function callNativeSongCredits(state:Dynamic, methodName:String):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, methodName);
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, []) == true catch (_:Dynamic) return false;
	}

	/** Prepare, mutate, and tear down one native vignette lifecycle. */
	public static function prepareVignette(state:Dynamic):Bool
		return callNativeVignette(state, 'hxcPrepareVignette', []);

	public static function clearVignette(state:Dynamic):Bool
		return callNativeVignette(state, 'hxcClearVignette', []);

	public static function pauseVignette(state:Dynamic):Bool
		return callNativeVignette(state, 'hxcPauseVignette', []);

	public static function resumeVignette(state:Dynamic):Bool
		return callNativeVignette(state, 'hxcResumeVignette', []);

	public static function setVignette(state:Dynamic, values:Array<Dynamic>):Bool
		return callNativeVignette(state, 'hxcSetVignette', [values == null ? [] : values]);

	/**
		Read one generated option bucket without exposing a donor Module object.
		`bucket`/`field` come from a literal descriptor and are validated before
		looking through the isolated store.  A missing bucket uses the descriptor's
		authored default rather than accidentally enabling a foreign effect.
	*/
	static function shaderGateEnabled(store:Dynamic, descriptor:Dynamic):Bool {
		var gate:Dynamic = descriptor == null ? null : runtimeField(descriptor, 'gate');
		if (gate == null)
			return true;
		var bucket = runtimeString(runtimeField(gate, 'bucket'));
		var field = runtimeString(runtimeField(gate, 'field'));
		if (!safeShaderToken(bucket) || !safeShaderToken(field))
			return false;
		var defaultValue = runtimeField(gate, 'defaultValue') == true;
		if (store == null)
			return defaultValue;
		var options = runtimeField(store, 'modOptions');
		var bag = options == null ? null : runtimeCall(options, 'get', [bucket]);
		if (bag == null)
			return defaultValue;
		var value = runtimeField(bag, field);
		return value == null ? defaultValue : value == true;
	}

	/** Strictly read one field from a source-backed HXC Save/preferences view. */
	public static function preferenceEnabled(save:Dynamic, field:Dynamic):Bool {
		var name = runtimeString(field);
		if (save == null || !safeShaderToken(name))
			return false;
		var value = runtimeField(save, name);
		return value != null && Type.typeof(value) == TBool && (cast value:Bool);
	}

	/**
		Apply one bounded shader/filter descriptor.  The generated option argument
		is an isolated data store (not ModuleHandler); `assetRoot` is passed through
		unchanged so the native owner can resolve only the selected manifest root.
	*/
	public static function applyShaderDescriptor(state:Dynamic, descriptor:Dynamic,
		?optionStore:Dynamic, ?assetRoot:Dynamic):Bool {
		if (descriptor == null || !shaderGateEnabled(optionStore, descriptor))
			return false;
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcApplyRuntimeShaderDescriptor');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [descriptor, assetRoot]) == true
		catch (_:Dynamic) return false;
	}

	/** Create an opaque, state-owned shader handle. The returned token carries no
	 * Flixel object and is only meaningful to the methods below. */
	public static function createShaderHandle(state:Dynamic, descriptor:Dynamic,
		?assetRoot:Dynamic):Dynamic {
		if (descriptor == null)
			return null;
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return null;
		var method = runtimeField(owner, 'hxcCreateRuntimeShaderHandle');
		if (method == null || !Reflect.isFunction(method))
			return null;
		try return Reflect.callMethod(owner, method, [descriptor,
			assetRoot == null ? '' : Std.string(assetRoot)])
		catch (_:Dynamic) return null;
	}

	/** Lazily create or reuse one field-keyed shader handle for multi-shader HXC. */
	public static function ensureShaderHandle(state:Dynamic, handles:Dynamic,
		field:Dynamic, descriptor:Dynamic, ?assetRoot:Dynamic):Dynamic {
		var key = runtimeString(field);
		if (handles == null || !safeShaderToken(key) || descriptor == null)
			return null;
		var existing:Dynamic = null;
		try existing = Reflect.field(handles, key) catch (_:Dynamic) {}
		if (existing != null)
			return existing;
		var handle = createShaderHandle(state, descriptor, assetRoot);
		if (handle != null)
			try Reflect.setField(handles, key, handle) catch (_:Dynamic) return null;
		return handle;
	}

	/** Append/remove one exact native filter binding on an owned camera. */
	public static function bindShaderFilter(state:Dynamic, handle:Dynamic,
		camera:Dynamic, enabled:Dynamic = true):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null || handle == null)
			return false;
		var method = runtimeField(owner, 'hxcBindRuntimeShader');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [handle, camera, enabled == true]) == true
			catch (_:Dynamic) return false;
	}

	/**
		Donor-side `<target>.filters = <value>` writes pass through here. Resolve
		owned shader handles and discard values that are not native BitmapFilters:
		OpenFL clones every entry while rendering and an invalid entry can crash.
	*/
	public static function assignFilters(target:Dynamic, value:Dynamic):Dynamic {
		if (target == null)
			return value;
		var cleaned:Dynamic = null;
		var entries:Array<Dynamic> = value == null ? []
			: (Std.isOfType(value, Array) ? cast value : [value]);
		var kept:Array<Dynamic> = [];
		var owner = activeState != null ? activeState : resolveActiveState();
		var resolver = owner == null ? null : runtimeField(owner, 'hxcResolveRuntimeShaderFilter');
		var bitmapFilterClass = Type.resolveClass('openfl.filters.BitmapFilter');
		for (entry in entries) {
			if (entry == null)
				continue;
			var filter:Dynamic = entry;
			if (resolver != null && Reflect.isFunction(resolver))
				try filter = Reflect.callMethod(owner, resolver, [entry]) catch (_:Dynamic) filter = null;
			if (bitmapFilterClass != null && Std.isOfType(filter, bitmapFilterClass))
				kept.push(filter);
			else
				trace('[hxc-filter-rejected] Discarded an invalid camera filter value.');
		}
		if (kept.length > 0)
			cleaned = kept;
		try Reflect.setProperty(target, 'filters', cleaned) catch (_:Dynamic) {}
		return cleaned;
	}

	/** Set one allow-listed shader uniform through the owned native binding. */
	public static function setShaderUniform(handle:Dynamic, name:Dynamic,
		value:Dynamic):Bool {
		var owner = activeState != null ? activeState : resolveActiveState();
		if (owner == null || handle == null || !safeShaderToken(runtimeString(name)))
			return false;
		var method = runtimeField(owner, 'hxcSetRuntimeShaderUniform');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [handle, runtimeString(name), value]) == true
		catch (_:Dynamic) return false;
	}

	/** Toggle every camera binding owned by one opaque handle. */
	public static function setShaderEnabled(handle:Dynamic, enabled:Dynamic):Bool {
		var owner = activeState != null ? activeState : resolveActiveState();
		if (owner == null || handle == null)
			return false;
		var method = runtimeField(owner, 'hxcSetRuntimeShaderEnabled');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [handle, enabled == true]) == true
		catch (_:Dynamic) return false;
	}

	/** Pulse alpha through a native tween/timer pair; no donor FlxTween graph leaks. */
	public static function pulseShader(handle:Dynamic, from:Dynamic, to:Dynamic,
		pulseDuration:Dynamic, holdDuration:Dynamic, ?ease:Dynamic, ?uniformName:Dynamic):Bool {
		var owner = activeState != null ? activeState : resolveActiveState();
		if (owner == null || handle == null)
			return false;
		var method = runtimeField(owner, 'hxcPulseRuntimeShader');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [handle,
			runtimeFloat(from), runtimeFloat(to), runtimeFloat(pulseDuration),
			runtimeFloat(holdDuration), ease,
			uniformName == null ? 'alpha' : runtimeString(uniformName)]) == true
		catch (_:Dynamic) return false;
	}

	public static function pauseShader(handle:Dynamic):Bool
		return callShaderHandle(handle, 'hxcPauseRuntimeShader');

	public static function resumeShader(handle:Dynamic):Bool
		return callShaderHandle(handle, 'hxcResumeRuntimeShader');

	public static function resetShader(handle:Dynamic):Bool
		return callShaderHandle(handle, 'hxcResetRuntimeShader');

	public static function clearShader(handle:Dynamic):Bool
		return callShaderHandle(handle, 'hxcClearRuntimeShader');

	static function callShaderHandle(handle:Dynamic, methodName:String):Bool {
		var owner = activeState != null ? activeState : resolveActiveState();
		if (owner == null || handle == null)
			return false;
		var method = runtimeField(owner, methodName);
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [handle]) == true
		catch (_:Dynamic) return false;
	}

	static function safeShaderToken(value:String):Bool {
		if (value == null || value == '' || value.length > 96)
			return false;
		return new EReg('^[A-Za-z0-9_-]+$', '').match(value);
	}

	static function runtimeString(value:Dynamic):String
		return value == null ? '' : StringTools.trim(Std.string(value));

	static function runtimeFloat(value:Dynamic):Float {
		if (value == null)
			return 0;
		if (Std.isOfType(value, Float) || Std.isOfType(value, Int))
			return cast value;
		var parsed = Std.parseFloat(runtimeString(value));
		return Math.isNaN(parsed) ? 0 : parsed;
	}

	static function callNativeVignette(state:Dynamic, methodName:String,
		args:Array<Dynamic>):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, methodName);
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, args) == true catch (_:Dynamic) return false;
	}

	/**
		Bounded sound-tray host hook. The native tray is optional on this fork, so
		missing tray/theme support is an explicit false result and leaves the
		ordinary Disappointing Plus tray untouched. No donor Bitmap or asset path is
		constructed by the generated HScript adapter.
	*/
	public static function configureSoundTray(tray:Dynamic, stageId:Dynamic,
		stageAllowList:Array<Dynamic>, scale:Dynamic, custom:Bool):Bool {
		if (tray == null || stageAllowList == null)
			return false;
		var stage = stageId == null ? '' : Std.string(stageId);
		var allowed = false;
		for (candidate in stageAllowList)
			if (candidate != null && Std.string(candidate) == stage) {
				allowed = true;
				break;
			}
		if (!allowed)
			return false;
		var apply = runtimeField(tray, 'hxcApplyTheme');
		if (apply == null || !Reflect.isFunction(apply))
			return false;
		try return Reflect.callMethod(tray, apply, [scale, custom]) == true catch (_:Dynamic) return false;
	}

	/**
		Native preference-page boundary. Destination builds without the donor
		PreferencesMenu simply retain their ordinary OptionsState page; a host may
		provide `hxcApplyImportedPreferences` to opt in without exposing its object
		graph to HScript.
	*/
	public static function applyPreferencePage(state:Dynamic, store:Dynamic):Bool {
		if (state == null)
			return false;
		var method = runtimeField(state, 'hxcApplyImportedPreferences');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, [store]) == true catch (_:Dynamic) return false;
	}

	/** Standalone-safe separator fallback for preference adapters. */
	public static function addPreferenceSeparator(values:Array<Dynamic>):Bool
		return values != null && values.length >= 2;

	/**
		Route one structurally matched imported-module character hand-off through
		the native GameOverSubstate boundary.  The manifest root, finite player
		roster, and replacement id are extracted as literals by HxcCompat; the
		adapter keeps the module scope and roster decision local while the native
		substate owns the actor/layer/camera mutation.
	*/
	public static function handleImportedGameOverReplacement(event:Dynamic,
		assetRoot:Dynamic, roster:Array<Dynamic>, replacementId:Dynamic):Bool {
		var scopedRoot = importedManifestRoot(assetRoot);
		if (scopedRoot == '' || roster == null || roster.length == 0
			|| replacementId == null || StringTools.trim(Std.string(replacementId)) == '')
			return false;

		var target = runtimeField(event, 'targetState');
		if (target == null) {
			var value = runtimeField(event, 'value');
			target = runtimeField(value, 'targetState');
		}
		if (!isNamedRuntimeClass(target, ['GameOverSubstate', 'GameOverSubState']))
			return false;

		var state = activeState != null ? activeState : resolveActiveState();
		if (state == null)
			return false;
		var chart = runtimeField(state, 'SONG');
		if (chart == null) {
			try {
				var stateClass = Type.resolveClass('PlayState');
				chart = stateClass == null ? null : Reflect.field(stateClass, 'SONG');
			} catch (_:Dynamic) {}
		}
		var player = runtimeField(chart, 'player1');
		if (player == null) {
			var characters = runtimeField(chart, 'characters');
			player = runtimeField(characters, 'player');
		}
		if (!isListedGameOverPlayer(player, roster))
			return false;

		var replacement = fetchCharacter(replacementId);
		if (replacement == null)
			return false;
		var apply = runtimeField(target, 'hxcApplyImportedGameOverCharacter');
		if (apply == null || !Reflect.isFunction(apply))
			return false;
		try {
			Reflect.callMethod(target, apply,
				[replacement, runtimeField(state, 'curStage'), scopedRoot]);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/**
		Install the optional Costume menu entry on the native MainMenuState.  The
		menu state owns the sprite group and selection switch; this adapter only
		checks the state boundary and passes the manifest-scoped imported state
		object through.  No donor AtlasMenuList or asset path is reflected.
	*/
	public static function addCostumeMenuItem(state:Dynamic, target:Dynamic):Bool {
		if (!isNamedRuntimeClass(state, ['MainMenuState']) || target == null)
			return false;
		var method = runtimeField(state, 'hxcAddCostumeMenuItem');
		if (method == null || !Reflect.isFunction(method))
			return false;
		// HxcImportedState carries the selected manifest root on its factory
		// entry. Pass only that destination path to the native menu boundary;
		// donor absolute paths and donor object graphs never cross this adapter.
		var entry = runtimeField(target, 'factoryEntry');
		var assetRoot = runtimeField(entry, 'root');
		try {
			return Reflect.callMethod(state, method,
				assetRoot == null ? [target] : [target, Std.string(assetRoot)]) == true;
		} catch (_:Dynamic) return false;
	}

	/**
		Narrow native boundary for complete imported main-menu specs.  The owner is
		checked as a MainMenuState before the method is called; no donor class,
		FlxG.state value, or reflection target is exposed to generated HScript.
	*/
	public static function mountMainMenuOverlay(state:Dynamic, spec:Dynamic,
		assetRoot:Dynamic):Bool {
		if (state == null || !isNamedRuntimeClass(state, ['MainMenuState', 'HxcImportedMenuState']) || spec == null)
			return false;
		var method = runtimeField(state, 'hxcMountMenuOverlay');
		if (method == null || !Reflect.isFunction(method))
			return false;
		var root = assetRoot == null ? '' : Std.string(assetRoot);
		try {
			var mounted = Reflect.callMethod(state, method, [spec, root]) == true;
			if (mounted)
				activeMenuOverlayState = state;
			return mounted;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Clear the owner-scoped overlay; null uses only the last native owner. */
	public static function clearMainMenuOverlay(?state:Dynamic):Bool {
		var owner = state == null ? activeMenuOverlayState : state;
		if (owner == null || !isNamedRuntimeClass(owner, ['MainMenuState', 'HxcImportedMenuState']))
			return false;
		var method = runtimeField(owner, 'hxcClearMenuOverlay');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try {
			var cleared = Reflect.callMethod(owner, method, []) == true;
			if (cleared && (state == null || activeMenuOverlayState == owner))
				activeMenuOverlayState = null;
			return cleared;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Mount a validated text-cue spec on the owning PlayState. */
	public static function mountNoteTextCue(state:Dynamic, assetRoot:Dynamic,
		spec:Dynamic):Dynamic {
		if (state == null || !isNamedRuntimeClass(state, ['PlayState']))
			return null;
		var checked = HxcNoteTextSpec.fromDynamic(spec);
		if (checked == null)
			return null;
		var method = runtimeField(state, 'hxcMountNoteTextCue');
		if (method == null || !Reflect.isFunction(method))
			return null;
		var root = assetRoot == null ? '' : Std.string(assetRoot);
		try return Reflect.callMethod(state, method, [root, checked]) catch (_:Dynamic) return null;
	}

	/** Forward one shared, mutable HXC note payload to its owner-scoped cue. */
	public static function triggerNoteTextCue(state:Dynamic, handle:Dynamic,
		event:Dynamic):Bool {
		if (state == null || handle == null || event == null
			|| !isNamedRuntimeClass(state, ['PlayState']))
			return false;
		var method = runtimeField(state, 'hxcTriggerNoteTextCue');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, [handle, event]) == true catch (_:Dynamic) return false;
	}

	/** Forward a miss to the same owner without applying hit judgement rules. */
	public static function triggerMissNoteTextCue(state:Dynamic, handle:Dynamic,
		event:Dynamic):Bool {
		if (state == null || handle == null || event == null
			|| !isNamedRuntimeClass(state, ['PlayState']))
			return false;
		var method = runtimeField(state, 'hxcTriggerMissNoteTextCue');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, [handle, event]) == true catch (_:Dynamic) return false;
	}

	/** Remove the active cue while retaining its per-module handle for retry. */
	public static function resetNoteTextCue(state:Dynamic, handle:Dynamic):Bool {
		if (state == null || handle == null || !isNamedRuntimeClass(state, ['PlayState']))
			return false;
		var method = runtimeField(state, 'hxcResetNoteTextCue');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, [handle]) == true catch (_:Dynamic) return false;
	}

	/** Release one cue handle; PlayState destruction also clears all remaining cues. */
	public static function clearNoteTextCue(state:Dynamic, handle:Dynamic):Bool {
		if (state == null || handle == null || !isNamedRuntimeClass(state, ['PlayState']))
			return false;
		var method = runtimeField(state, 'hxcClearNoteTextCue');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(state, method, [handle]) == true catch (_:Dynamic) return false;
	}

	/**
		The native MainMenuState update loop owns overlay input and animation.  The
		compat callback remains a harmless heartbeat for older module dispatch and
		never evaluates donor update code.
	*/
	public static function tickMainMenuOverlay():Bool
		return activeMenuOverlayState != null;

	/**
		Apply one typed/data-only pause description through the native PauseSubState
		boundary.  The generated HScript never receives a donor object or callback;
		the host validates its own runtime class and owns all display/input state.
	*/
	public static function applyPauseOverlay(state:Dynamic, assetRoot:Dynamic,
		spec:Dynamic):Bool {
		if (state == null || !isNamedRuntimeClass(state, ['PauseSubState']) || spec == null)
			return false;
		var method = runtimeField(state, 'hxcApplyPauseOverlay');
		if (method == null || !Reflect.isFunction(method))
			return false;
		var root = assetRoot == null ? '' : Std.string(assetRoot);
		try {
			var applied = Reflect.callMethod(state, method, [root, spec]) == true;
			if (applied)
				activePauseOverlayState = state;
			return applied;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Clear only the native pause owner selected by the open/close lifecycle. */
	public static function clearPauseOverlay(?state:Dynamic):Bool {
		var owner = state == null ? activePauseOverlayState : state;
		if (owner == null || !isNamedRuntimeClass(owner, ['PauseSubState']))
			return false;
		var method = runtimeField(owner, 'hxcClearPauseOverlay');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try {
			var cleared = Reflect.callMethod(owner, method, []) == true;
			if (cleared && (state == null || activePauseOverlayState == owner))
				activePauseOverlayState = null;
			return cleared;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Explicit informational no-op for donor menu actions with no allow-listed route. */
	public static function menuRouteNoOp(label:Dynamic):Bool {
		trace('[hxc-menu-route-noop] no native route for menu item '
			+ (label == null ? '<unknown>' : Std.string(label)) + '; action ignored.');
		return false;
	}

	static function isListedGameOverPlayer(value:Dynamic, roster:Array<Dynamic>):Bool {
		if (value == null || roster == null)
			return false;
		var text = StringTools.trim(Std.string(value));
		for (entry in roster)
			if (entry != null && text == StringTools.trim(Std.string(entry)))
				return true;
		return false;
	}

	static function isNamedRuntimeClass(value:Dynamic, names:Array<String>):Bool {
		if (value == null || names == null)
			return false;
		try {
			var cls = Type.getClassName(Type.getClass(value));
			if (cls == null)
				return false;
			var simple = cls;
			var dot = simple.lastIndexOf('.');
			if (dot >= 0)
				simple = simple.substr(dot + 1);
			for (name in names)
				if (simple == name)
					return true;
		} catch (_:Dynamic) {}
		return false;
	}

	/** Test a script value without requiring HScript to resolve a String class. */
	public static function isNonemptyString(value:Dynamic):Bool {
		return Std.isOfType(value, String) && (cast value:String).length > 0;
	}

	/** Desktop-native fallback for V-Slice's FunkinSound wrapper. */
	public static function freeplayPlaySound(path:Dynamic, ?volume:Float = 1):Dynamic {
		try {
			var sound = Type.resolveClass('FNFAssets');
			var getter = sound == null ? null : Reflect.field(sound, 'getSound');
			var cached = Std.isOfType(path, String) ? cachedFunkinSounds.get(cast path) : null;
			var value = cached != null ? cached : (getter == null ? null : Reflect.callMethod(sound, getter, [path]));
			var globals = Type.resolveClass('flixel.FlxG');
			var play = globals == null ? null : runtimeField(runtimeField(globals, 'sound'), 'play');
			if (play != null)
				return Reflect.callMethod(runtimeField(globals, 'sound'), play, [value, volume]);
		} catch (_:Dynamic) {}
		return null;
	}

	/** Keep imported menu music calls inside the native audio boundary. */
	public static function freeplayPlayMusic(name:Dynamic, ?options:Dynamic):Dynamic {
		try {
			var globals = Type.resolveClass('flixel.FlxG');
			var sound = globals == null ? null : runtimeField(globals, 'sound');
			var play = sound == null ? null : runtimeField(sound, 'playMusic');
			if (play != null) {
				var volume:Dynamic = options == null ? 1.0 : runtimeField(options, 'startingVolume');
				if (volume == null)
					volume = options == null ? 1.0 : runtimeField(options, 'volume');
				if (volume == null)
					volume = 1.0;
				var looped:Dynamic = options == null ? true : runtimeField(options, 'looped');
				if (looped == null)
					looped = options == null ? true : runtimeField(options, 'loop');
				if (looped == null)
					looped = true;
				var music = name;
				if (Std.isOfType(name, String)) {
					var paths = Type.resolveClass('Paths');
					var resolver = paths == null ? null : runtimeField(paths, 'music');
					if (resolver != null)
						music = Reflect.callMethod(paths, resolver, [name]);
				}
				return Reflect.callMethod(sound, play, [music, runtimeFloatValue(volume), looped == true]);
			}
		} catch (_:Dynamic) {}
		return null;
	}

	/**
		Resolve a V-Slice image key inside the HXC manifest root.  The helper never
		falls through to the working directory or the native asset tree: malformed,
		absolute, and parent-traversal keys return null and are left for the normal
		missing-asset diagnostics.
	*/
	static function hxcScopedRoot(root:Dynamic):String {
		if (root == null)
			return '';
		var raw = StringTools.replace(StringTools.trim(Std.string(root)), '\\', '/');
		if (raw == '' || raw.startsWith('/') || raw.indexOf(':') >= 0 || raw.indexOf('..') >= 0)
			return '';
		var value = Path.normalize(raw);
		if (value != 'assets' && !value.startsWith('assets/imported_mods/'))
			return '';
		return value;
	}

	/** Accept only an imported HXC manifest root for module-owned lifecycle work. */
	public static function isImportedManifestRoot(root:Dynamic):Bool
		return importedManifestRoot(root) != '';

	static function importedManifestRoot(root:Dynamic):String {
		var value = hxcScopedRoot(root);
		return value.startsWith('assets/imported_mods/') ? value : '';
	}

	static function hxcScopedKey(value:Dynamic):String {
		if (value == null)
			return '';
		var key = StringTools.replace(StringTools.trim(Std.string(value)), '\\', '/');
		if (key == '' || key.startsWith('/') || key.indexOf(':') >= 0 || key.indexOf('..') >= 0)
			return '';
		while (key.startsWith('./'))
			key = key.substr(2);
		while (key.toLowerCase().startsWith('assets/'))
			key = key.substr('assets/'.length);
		return key;
	}

	static function hxcScopedExists(path:String):Bool {
		if (path == null || path == '')
			return false;
		try {
			var assets = Type.resolveClass('FNFAssets');
			var exists = assets == null ? null : runtimeField(assets, 'exists');
			if (exists != null && Reflect.callMethod(assets, exists, [path]) == true)
				return true;
		} catch (_:Dynamic) {}
		#if sys
		try return FileSystem.exists(path) catch (_:Dynamic) return false;
		#else
		return false;
		#end
	}

	/** Return a manifest-relative file or directory for a bounded asset key. */
	static function hxcScopedAsset(root:Dynamic, value:Dynamic, folder:String,
		extension:String = '', ?directory:Bool = false):String {
		var cleanRoot = hxcScopedRoot(root);
		var key = hxcScopedKey(value);
		if (cleanRoot == '' || key == '')
			return null;
		var rootPrefix = cleanRoot + '/';
		var candidate:String;
		if (key == cleanRoot || key.startsWith(rootPrefix)) {
			candidate = Path.normalize(key);
		} else {
			var lowerFolder = folder.toLowerCase() + '/';
			var lowerKey = key.toLowerCase();
			if (lowerKey.startsWith(lowerFolder))
				key = key.substr(lowerFolder.length);
			candidate = Path.join([cleanRoot, folder, key]);
		}
		if (extension != '' && Path.extension(candidate).toLowerCase() != extension.toLowerCase())
			candidate += extension;
		return hxcScopedExists(candidate) || directory ? candidate : null;
	}

	/**
		Resolve a static imported asset through its manifest first, then through the
		native asset tree.  FPS Plus stages commonly keep their HXC companion under
		an imported namespace while sharing media in `assets/images`; the selected
		manifest remains authoritative when it contains a complete file.
	*/
	static function hxcResolvedAsset(root:Dynamic, value:Dynamic, folder:String,
		extension:String = '', ?directory:Bool = false):String {
		var scoped = hxcScopedAsset(root, value, folder, extension, directory);
		if (scoped != null)
			return scoped;
		var key = hxcScopedKey(value);
		if (key == '')
			return null;
		var lowerFolder = folder == null ? '' : folder.toLowerCase() + '/';
		if (lowerFolder != '' && key.toLowerCase().startsWith(lowerFolder))
			key = key.substr(lowerFolder.length);
		var candidate = Path.normalize(Path.join(['assets', folder == null ? '' : folder, key]));
		if (extension != '' && Path.extension(candidate).toLowerCase() != extension.toLowerCase())
			candidate += extension;
		return hxcScopedExists(candidate) || directory ? candidate : null;
	}

	static function hxcNativeInstance(className:String, args:Array<Dynamic>):Dynamic {
		try {
			var cls = Type.resolveClass(className);
			return cls == null ? null : Type.createInstance(cls, args == null ? [] : args);
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function hxcCall(owner:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		var method = runtimeField(owner, name);
		if (method == null)
			return null;
		try return Reflect.callMethod(owner, method, args == null ? [] : args) catch (_:Dynamic) return null;
	}

	static function hxcImageValue(root:Dynamic, value:Dynamic):Dynamic {
		if (value == null || !Std.isOfType(value, String))
			return value;
		var path = hxcResolvedAsset(root, value, 'images', '.png');
		if (path == null)
			return null;
		try {
			var assets = Type.resolveClass('FNFAssets');
			var getter = assets == null ? null : runtimeField(assets, 'getBitmapData');
			return getter == null ? path : Reflect.callMethod(assets, getter, [path]);
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Native bounded equivalent of FunkinSprite's no-asset/graphic constructor. */
	public static function createFunkinSprite(root:Dynamic, x:Dynamic = 0, y:Dynamic = 0,
		?graphic:Dynamic):Dynamic {
		var sprite = hxcNativeInstance('DynamicSprite', [runtimeFloatValue(x), runtimeFloatValue(y)]);
		if (sprite == null)
			sprite = hxcNativeInstance('flixel.FlxSprite', [runtimeFloatValue(x), runtimeFloatValue(y)]);
		if (sprite != null && graphic != null) {
			var image = hxcImageValue(root, graphic);
			if (image != null)
				hxcCall(sprite, 'loadGraphic', [image]);
		}
		return sprite;
	}

	/**
		Create a source-owned in-stage video sprite.  The returned FlxVideoSprite
		keeps the source's ordinary display-list/camera/loop semantics; media access
		and state lifecycle are bounded by HxcOwnedVideoSprite.
	*/
	public static function createFunkinVideoSprite(state:Dynamic, root:Dynamic,
		x:Dynamic = 0, y:Dynamic = 0):Dynamic {
		var owner = state == null ? resolveActiveState() : state;
		try {
			return HxcOwnedVideoSprite.create(owner,
				root == null ? '' : Std.string(root), runtimeFloatValue(x), runtimeFloatValue(y));
		} catch (error:Dynamic) {
			trace('[hxc-video-create-error] ' + Std.string(error));
			return null;
		}
	}

	/** Pause only HXC videos that were playing as this PlayState paused. */
	public static function pauseFunkinVideos(state:Dynamic):Void
		callOwnedFunkinVideos('pauseForState', state);

	/** Resume only HXC videos paused by the paired engine pause. */
	public static function resumeFunkinVideos(state:Dynamic):Void
		callOwnedFunkinVideos('resumeForState', state);

	/** Stop and detach HXC videos before a song/state releases its scripts. */
	public static function destroyFunkinVideos(state:Dynamic):Void
		callOwnedFunkinVideos('destroyForState', state);

	static function callOwnedFunkinVideos(methodName:String, state:Dynamic):Void {
		try {
			switch (methodName) {
				case 'pauseForState': HxcOwnedVideoSprite.pauseForState(state);
				case 'resumeForState': HxcOwnedVideoSprite.resumeForState(state);
				case 'destroyForState': HxcOwnedVideoSprite.destroyForState(state);
			}
		} catch (error:Dynamic) {
			trace('[hxc-video-lifecycle-error] ' + methodName + ': ' + Std.string(error));
		}
	}

	/**
		Materialize the bounded PlayState character helper carried by a supported
		HXC story-menu module. The helper host validates the imported root and owns
		the Sparrow atlas/camera attachment boundary.
	*/
	public static function createStoryCharacterHelper(state:Dynamic, root:Dynamic,
		spec:Dynamic):Dynamic {
		try {
			var host = Type.resolveClass('HxcStoryMenuRuntime');
			var helper = host == null ? null : runtimeField(host, 'createCharacterHelper');
			return helper == null ? null : Reflect.callMethod(host, helper, [state, root, spec]);
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Native bounded Sparrow factory; atlas bytes stay inside the selected root. */
	public static function createFunkinSpriteSparrow(root:Dynamic, x:Dynamic = 0, y:Dynamic = 0,
		key:Dynamic = null):Dynamic {
		var sprite = createFunkinSprite(root, x, y);
		var png = hxcResolvedAsset(root, key, 'images', '.png');
		var xml = hxcResolvedAsset(root, key, 'images', '.xml');
		if (sprite == null || png == null || xml == null)
			return sprite;
		try {
			var atlasClass = Type.resolveClass('DynamicAtlasFrames');
			var factory = atlasClass == null ? null : runtimeField(atlasClass, 'fromSparrow');
			if (factory != null) {
				var frames = Reflect.callMethod(atlasClass, factory, [png, xml]);
				if (frames != null)
					Reflect.setProperty(sprite, 'frames', frames);
			}
		} catch (_:Dynamic) {}
		return sprite;
	}

	/** Native bounded Texture Atlas factory used by the selected Love N Funkin script. */
	public static function createFunkinSpriteTextureAtlas(root:Dynamic, x:Dynamic = 0, y:Dynamic = 0,
		key:Dynamic = null, ?library:Dynamic, ?settings:Dynamic):Dynamic {
		var atlasPath = hxcResolvedAsset(root, key, 'images', '', true);
		if (atlasPath != null) {
			var animate = hxcNativeInstance('animate.FlxAnimate', [runtimeFloatValue(x), runtimeFloatValue(y), atlasPath, settings]);
			if (animate != null)
				return animate;
		}
		return createFunkinSprite(root, x, y);
	}

	/**
		Native materialization of the FPS Plus `objects.BGSprite` constructor.

		BGSprite is a thin FlxSprite helper: it loads a Sparrow atlas when the
		requested asset has XML metadata, otherwise it loads a static image, sets
		the parallax factors, and optionally registers/plays the supplied prefix
		list.  Keeping this in one adapter lets every imported BaseStage share the
		same asset and animation semantics without copying a donor class.
	*/
	public static function createBGSprite(root:Dynamic, key:Dynamic = null,
		x:Dynamic = 0, y:Dynamic = 0, scrollX:Dynamic = 1, scrollY:Dynamic = 1,
		?animations:Dynamic, ?looped:Dynamic = false):Dynamic {
		var atlasReady = hxcResolvedAsset(root, key, 'images', '.png') != null
			&& hxcResolvedAsset(root, key, 'images', '.xml') != null;
		var sprite = atlasReady
			? createFunkinSpriteSparrow(root, x, y, key)
			: createFunkinSprite(root, x, y, key);
		try {
			var scroll = runtimeField(sprite, 'scrollFactor');
			if (scroll != null)
				hxcCall(scroll, 'set', [runtimeFloatValue(scrollX), runtimeFloatValue(scrollY)]);
		} catch (_:Dynamic) {}
		try Reflect.setProperty(sprite, 'active', false) catch (_:Dynamic) {}
		if (animations != null && Std.isOfType(animations, Array)) {
			var animation = runtimeField(sprite, 'animation');
			var first:String = null;
			for (entry in (cast animations:Array<Dynamic>)) {
				if (entry == null)
					continue;
				var name = StringTools.trim(Std.string(entry));
				if (name == '')
					continue;
				if (first == null)
					first = name;
				if (animation != null)
					hxcCall(animation, 'addByPrefix', [name, name, 24, looped == true]);
			}
			if (first != null && animation != null)
				hxcCall(animation, 'play', [first, true]);
		}
		return sprite;
	}

	/** Warm one manifest-scoped bitmap without exposing a global donor cache. */
	public static function cacheFunkinTexture(root:Dynamic, value:Dynamic):Dynamic {
		if (importedManifestRoot(root) == '' || value == null || !Std.isOfType(value, String))
			return null;
		var path = hxcScopedAsset(root, value, 'images', '.png');
		if (path == null)
			return null;
		try {
			var assets = Type.resolveClass('FNFAssets');
			var getter = assets == null ? null : runtimeField(assets, 'getBitmapData');
			return getter == null ? null : Reflect.callMethod(assets, getter, [path]);
		} catch (_:Dynamic) {
			return null;
		}
	}

	static var cachedFunkinSounds:Map<String, Dynamic> = new Map<String, Dynamic>();
	static var cachedFunkinSoundOrder:Array<String> = [];
	static inline var maxCachedFunkinSounds:Int = 32;

	/** Decode one literal constructor sound and retain it in the selected manifest root. */
	public static function cacheFunkinSound(root:Dynamic, value:Dynamic):Dynamic {
		if (importedManifestRoot(root) == '' || value == null || !Std.isOfType(value, String))
			return null;
		var path = hxcScopedAsset(root, value, 'sounds', '.ogg');
		if (path == null)
			return null;
		if (cachedFunkinSounds.exists(path))
			return cachedFunkinSounds.get(path);
		try {
			var assets = Type.resolveClass('FNFAssets');
			var getter = assets == null ? null : runtimeField(assets, 'getSound');
			if (getter == null)
				return null;
			var decoded = Reflect.callMethod(assets, getter, [path]);
			if (decoded != null) {
				if (cachedFunkinSoundOrder.length >= maxCachedFunkinSounds)
					cachedFunkinSounds.remove(cachedFunkinSoundOrder.shift());
				cachedFunkinSounds.set(path, decoded);
				cachedFunkinSoundOrder.push(path);
			}
			return decoded;
		} catch (_:Dynamic) {
			return null;
		}
	}

	/** Native full-window FlxCamera equivalent of FunkinCamera's named constructor. */
	public static function createFunkinCamera(stateOrName:Dynamic, ?name:Dynamic):Dynamic {
		var owner:Dynamic = stateOrName;
		var cameraName = name;
		// Keep the old one-argument helper form usable by existing HXC fixtures.
		if (cameraName == null && Std.isOfType(stateOrName, String)) {
			cameraName = stateOrName;
			owner = null;
		}
		if (owner == null)
			owner = resolveActiveState();
		// FlxCamera's zero-sized default uses the current game viewport and default
		// zoom, matching FunkinCamera's normal full-window construction.
		var camera = hxcNativeInstance('flixel.FlxCamera', []);
		if (camera != null && cameraName != null)
			try Reflect.setProperty(camera, 'name', Std.string(cameraName)) catch (_:Dynamic) {}
		if (camera != null && owner != null)
			hxcFunkinCameras.push({state: owner, camera: camera});
		return camera;
	}

	/** Desktop has no TouchUtil action surface; let source keyboard fallbacks run. */
	public static function touchPressAction(_action:Dynamic):Bool
		return false;

	/** Remove extra cameras from the shared frontend and destroy uninserted ones. */
	public static function clearFunkinCameras(state:Dynamic):Void {
		if (state == null)
			return;
		var remaining:Array<Dynamic> = [];
		for (entry in hxcFunkinCameras) {
			if (entry == null || Reflect.field(entry, 'state') != state) {
				if (entry != null) remaining.push(entry);
				continue;
			}
			var camera:Dynamic = Reflect.field(entry, 'camera');
			if (camera == null)
				continue;
			try {
				var flxG = Type.resolveClass('flixel.FlxG');
				var manager = flxG == null ? null : Reflect.field(flxG, 'cameras');
				var list:Dynamic = manager == null ? null : Reflect.getProperty(manager, 'list');
				var remove = manager == null ? null : runtimeField(manager, 'remove');
				if (Std.isOfType(list, Array) && (cast list:Array<Dynamic>).indexOf(camera) >= 0
					&& remove != null)
					Reflect.callMethod(manager, remove, [camera, true]);
				else
					hxcCall(camera, 'destroy', []);
			} catch (error:Dynamic) {
				trace('[hxc-camera-cleanup-error] ' + Std.string(error));
			}
		}
		hxcFunkinCameras = remaining;
	}

	/**
		Reconfigure one of PlayState's native receptor groups in place. HXC sees
		`playerStrumline`/`opponentStrumline` as assignable, but this fork exposes
		read-only views so replacing them would detach scoring, note ownership, and
		HUD cameras. The host method revives the existing group and rebuilds its
		receptor graphics for the requested style; `botplay` and foreign scroll
		speed are accepted for ABI compatibility but never manufacture a second
		native note queue.
	*/
	public static function configureNativeStrumline(state:Dynamic, side:Dynamic,
		style:Dynamic, botplay:Dynamic, foreignScrollSpeed:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcConfigureNativeStrumline');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, [
			StringTools.trim(side == null ? '' : Std.string(side)), style,
			botplay == true, foreignScrollSpeed
		]) == true catch (_:Dynamic) return false;
	}

	/** Refresh both native receptor groups after a bounded in-place replacement. */
	public static function refreshNativeStrumlines(state:Dynamic):Bool {
		var owner = state == null ? resolveActiveState() : state;
		if (owner == null)
			return false;
		var method = runtimeField(owner, 'hxcRefreshNativeStrumlines');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try return Reflect.callMethod(owner, method, []) == true catch (_:Dynamic) return false;
	}

	/** Native WiggleEffect owns the shader and preserves the donor update cadence. */
	public static function createWiggleEffect(frequency:Dynamic, amplitude:Dynamic,
		speed:Dynamic, ?effectType:Dynamic):Dynamic {
		var effect = hxcNativeInstance('WiggleEffect', []);
		if (effect == null)
			return null;
		try Reflect.setProperty(effect, 'waveFrequency', runtimeFloatValue(frequency)) catch (_:Dynamic) {}
		try Reflect.setProperty(effect, 'waveAmplitude', runtimeFloatValue(amplitude)) catch (_:Dynamic) {}
		try Reflect.setProperty(effect, 'waveSpeed', runtimeFloatValue(speed)) catch (_:Dynamic) {}
		if (effectType != null) {
			try {
				var enumClass = Type.resolveClass('WiggleEffectType');
				var enumValue = enumClass == null ? null
					: Type.createEnum(cast enumClass, Std.string(effectType), []);
				if (enumValue != null)
					Reflect.setProperty(effect, 'effectType', enumValue);
			} catch (_:Dynamic) {}
		}
		return effect;
	}

	/** Stop only the native Flixel sound list; no donor singleton is reflected. */
	public static function stopAllAudio():Void {
		try {
			var globals = Type.resolveClass('flixel.FlxG');
			var sound = globals == null ? null : runtimeField(globals, 'sound');
			var music = sound == null ? null : runtimeField(sound, 'music');
			hxcCall(music, 'stop', []);
			var list = sound == null ? null : runtimeField(sound, 'list');
			var members:Dynamic = list == null ? null : runtimeField(list, 'members');
			if (Std.isOfType(members, Array))
				for (item in (cast members:Array<Dynamic>))
					if (item != null)
						hxcCall(item, 'stop', []);
		} catch (_:Dynamic) {}
	}

	/**
		Donor `FlxTween.tween(target, values, ...)` writes each named field every
		frame through reflection. A field the native target does not carry (for
		example `alpha` on a non-sprite actor in this fork) would throw inside
		the tween manager - outside every script try/catch - and end the whole
		session. Filter the requested fields to ones the target actually has,
		report dropped ones once, and hand the rest to the native tween.
	*/
	public static function safeTween(target:Dynamic, values:Dynamic, ?duration:Dynamic = 0,
		?options:Dynamic = null):Dynamic {
		if (target == null || values == null)
			return null;
		var cleaned:Dynamic = {};
		var dropped:Array<String> = [];
		for (field in Reflect.fields(values)) {
			if (runtimeField(target, field) == null) {
				dropped.push(field);
				continue;
			}
			Reflect.setField(cleaned, field, Reflect.field(values, field));
		}
		if (dropped.length > 0) {
			var identity = runtimeString(runtimeField(target, 'ID')) + ':' + dropped.join(',');
			if (!missingTweenFields.exists(identity)) {
				missingTweenFields.set(identity, true);
				trace('[hxc-tween-field-gap] target has no '
					+ dropped.join('/') + ' field; tween fields dropped');
			}
		}
		if (Reflect.fields(cleaned).length == 0)
			return null;
		var tweenClass = Type.resolveClass('flixel.tweens.FlxTween');
		var method = tweenClass == null ? null : runtimeField(tweenClass, 'tween');
		if (method == null) {
			// Interpreter-only environments (translation fixtures) have no flixel
			// tween manager. Apply the final values directly so generated-handler
			// contracts stay testable; the real game always resolves flixel.
			for (field in Reflect.fields(cleaned))
				try Reflect.setProperty(target, field, Reflect.field(cleaned, field))
				catch (_:Dynamic) {}
			return target;
		}
		try {
			return Reflect.callMethod(tweenClass, method,
				[target, cleaned, runtimeFloatValue(duration), options]);
		}
		catch (_:Dynamic) {
			return null;
		}
	}

	static var missingTweenFields:Map<String, Bool> = new Map<String, Bool>();

	/** Bounded equivalent of FunkinSound.load; root checks happen before disk I/O. */
	public static function loadFunkinSound(root:Dynamic, path:Dynamic, ?volume:Dynamic = 1,
		?looped:Dynamic = false, ?autoDestroy:Dynamic = false, ?arg4:Dynamic = null,
		?arg5:Dynamic = null, ?arg6:Dynamic = null, ?arg7:Dynamic = null,
		?arg8:Dynamic = null):Dynamic {
		var soundPath:Dynamic = path;
		var scopedPath:String = null;
		if (Std.isOfType(path, String)) {
			var cleanRoot = importedManifestRoot(root);
			var exactPath:String = cast path;
			var scoped = cleanRoot != '' && exactPath.indexOf('..') < 0
				&& Path.normalize(exactPath) == exactPath && exactPath.startsWith(cleanRoot + '/sounds/')
				&& hxcScopedExists(exactPath) ? exactPath : hxcScopedAsset(root, path, 'sounds', '.ogg');
			if (scoped != null) {
				soundPath = scoped;
				scopedPath = scoped;
			}
		}
		if (soundPath == null)
			return null;
		var sound = hxcNativeInstance('DynamicSound', []);
		if (sound == null)
			sound = hxcNativeInstance('flixel.sound.FlxSound', []);
		if (sound == null)
			return null;
		var cached = scopedPath == null ? null : cachedFunkinSounds.get(scopedPath);
		var loaded = hxcCall(sound, 'loadEmbedded', [cached == null ? soundPath : cached,
			looped == true, autoDestroy == true, null]);
		if (loaded == null)
			loaded = sound;
		try Reflect.setProperty(loaded, 'volume', runtimeFloatValue(volume)) catch (_:Dynamic) {}
		return loaded;
	}

	/**
		Apply the native window/scaling equivalent of the donor fullscreen helper.

		The donor toggles three process-global values together: fullscreen is
		cleared, the ratio scale mode is restored, and the resize signal is sent so
		HUD/camera layout listeners recompute their bounds.  The native fork has no
		V-Slice FullScreenScaleMode singleton; RatioScaleMode plus FlxG's resize
		signal is its actual host boundary, so imported HXC reaches those native
		objects through this one narrow adapter instead of reflecting over arbitrary
		window classes.  The optional arguments are only for isolated runtime tests;
		generated HScript calls the zero-argument native path.
	*/
	public static function disableFullscreen(?globals:Dynamic, ?ratioScaleMode:Dynamic):Bool {
		var flxG:Dynamic = globals;
		if (flxG == null) {
			try flxG = Type.resolveClass('flixel.FlxG') catch (_:Dynamic) flxG = null;
		}
		if (flxG == null)
			return false;

		var changed = false;
		try {
			Reflect.setProperty(flxG, 'fullscreen', false);
			changed = true;
		} catch (_:Dynamic) {}

		if (ratioScaleMode == null) {
			try {
				var ratioClass = Type.resolveClass('flixel.system.scaleModes.RatioScaleMode');
				if (ratioClass != null)
					ratioScaleMode = Type.createInstance(ratioClass, []);
			} catch (_:Dynamic) {}
		}
		if (ratioScaleMode != null)
			try {
				Reflect.setProperty(flxG, 'scaleMode', ratioScaleMode);
				changed = true;
			} catch (_:Dynamic) {}

		var signals = runtimeField(flxG, 'signals');
		var resized = runtimeField(signals, 'gameResized');
		var dispatch = runtimeField(resized, 'dispatch');
		if (dispatch != null) {
			var width = runtimeField(flxG, 'width');
			var height = runtimeField(flxG, 'height');
			try {
				Reflect.callMethod(resized, dispatch, [width, height]);
				changed = true;
			} catch (_:Dynamic) {}
		}
		return changed;
	}

	/**
		Return whether the native Character registry knows an id.

		Some imported modules use CharacterDataParser as their registry boundary.
		The donor parser also knows about classes which are not part of this
		engine, so this deliberately delegates only to the real native
		Character.characterExists implementation. Missing donor content stays a
		normal false result instead of silently constructing a fallback actor.
	*/
	public static function characterExists(characterId:Dynamic):Bool {
		var characterClass = Type.resolveClass('Character');
		if (characterClass == null || characterId == null)
			return false;

		var exists = Reflect.field(characterClass, 'characterExists');
		if (exists == null)
			return false;

		try return Reflect.callMethod(characterClass, exists, [Std.string(characterId)]) == true catch (_:Dynamic) return false;
	}

	/**
		Construct a native Character from a registry id.

		This is intentionally a small factory rather than a donor parser clone:
		the native constructor is the only source of asset/script initialization
		we can promise for an imported HXC module. Unknown ids return null.
	*/
	public static function fetchCharacter(characterId:Dynamic):Dynamic {
		if (!characterExists(characterId))
			return null;

		var characterClass = Type.resolveClass('Character');
		if (characterClass == null)
			return null;

		try return Type.createInstance(characterClass, [0.0, 0.0, Std.string(characterId), false]) catch (_:Dynamic) return null;
	}

	/** Return the live native slot for a character-local HXC callback. */
	public static function characterType(character:Dynamic):String {
		if (character == null)
			return 'dad';
		var state = activeState != null ? activeState : resolveActiveState();
		if (state != null) {
			if (character == runtimeField(state, 'boyfriend')) return 'bf';
			if (character == runtimeField(state, 'gf')) return 'gf';
			if (character == runtimeField(state, 'dad')) return 'dad';
		}
		var hinted = characterTypeFor(character);
		if (hinted != null) {
			var hintedSlot = characterSlot(hinted);
			if (hintedSlot == 'boyfriend') return 'bf';
			if (hintedSlot == 'gf') return 'gf';
			if (hintedSlot == 'dad') return 'dad';
		}
		var nativeType = runtimeField(character, 'characterType');
		if (nativeType != null) {
			var nativeValue = Std.string(nativeType).toLowerCase();
			if (nativeValue == 'bf' || nativeValue == 'boyfriend' || nativeValue == 'player') return 'bf';
			if (nativeValue == 'gf' || nativeValue == 'girlfriend') return 'gf';
			if (nativeValue == 'other' || nativeValue == 'spectator' || nativeValue == '3') return 'other';
			if (nativeValue == 'dad' || nativeValue == 'opponent') return 'dad';
		}
		return runtimeField(character, 'isPlayer') == true ? 'bf' : 'dad';
	}

	/** Call the native FlxObject base implementation from an HXC position hook. */
	public static function characterBaseScreenPosition(character:Dynamic, result:Dynamic,
		camera:Dynamic):Dynamic {
		if (character == null)
			return result;
		var method = Reflect.field(character, 'hxcBaseScreenPosition');
		if (method == null)
			return result;
		try {
			var output = Reflect.callMethod(character, method, [result, camera]);
			return output == null ? result : output;
		} catch (_:Dynamic) {
			return result;
		}
	}

	/** Resolve the active named animation offset used by donor screen hooks. */
	public static function characterAnimationOffset(character:Dynamic, index:Dynamic):Float {
		if (character == null)
			return 0;
		var method = Reflect.field(character, 'getCurrentAnimationOffset');
		if (method == null)
			return 0;
		try {
			var output:Dynamic = Reflect.callMethod(character, method, [runtimeIntValue(index)]);
			var parsed = output == null ? 0 : Std.parseFloat(Std.string(output));
			return Math.isNaN(parsed) ? 0 : parsed;
		} catch (_:Dynamic) {
			return 0;
		}
	}

	/** Resolve the V-Slice CharacterData offset exposed as `globalOffsets[0/1]`. */
	public static function characterGlobalOffset(character:Dynamic, index:Dynamic):Float {
		if (character == null)
			return 0;
		var method = Reflect.field(character, 'getCurrentGlobalOffset');
		if (method == null)
			return 0;
		try {
			var output:Dynamic = Reflect.callMethod(character, method, [runtimeIntValue(index)]);
			var parsed = output == null ? 0 : Std.parseFloat(Std.string(output));
			return Math.isNaN(parsed) ? 0 : parsed;
		} catch (_:Dynamic) {
			return 0;
		}
	}

	/**
		Attach a literal HXC Sparrow animation bundle to a native Character.
		The Character owns atlas loading and frame lifetime; this reflective boundary
		keeps the standalone compatibility runtime free of Flixel imports.
	*/
	public static function addCharacterAtlasAnimations(character:Dynamic, assetPath:Dynamic,
		animations:Dynamic, offsetX:Dynamic = 0, offsetY:Dynamic = 0,
		?assetRoot:Dynamic):Dynamic {
		if (character == null)
			return character;
		var method = Reflect.field(character, 'addHxcAtlasAnimations');
		if (method == null)
			return character;
		try {
			var args:Array<Dynamic> = [assetPath == null ? '' : Std.string(assetPath),
				animations, runtimeFloatValue(offsetX), runtimeFloatValue(offsetY)];
			if (assetRoot != null && StringTools.trim(Std.string(assetRoot)) != '')
				args.push(Std.string(assetRoot));
			Reflect.callMethod(character, method, args);
		} catch (_:Dynamic) {}
		return character;
	}

	/**
		Apply a literal FPS Plus CharacterInfo definition to the live native actor.
		The definition is detached data emitted by HxcCompat; no CharacterInfoBase,
		Sparrow loader, or donor helper object is instantiated here.  Position and
		camera metadata are applied through the actor fields already consumed by
		PlayState, while atlas/frame ownership stays in Character.
	*/
	public static function applyCharacterInfo(character:Dynamic, definition:Dynamic,
		?assetRoot:Dynamic):Dynamic {
		if (character == null || definition == null)
			return character;
		if (runtimeField(character, 'hxcInfoApplied') == true)
			return character;
		try Reflect.setField(character, 'hxcInfoApplied', true) catch (_:Dynamic) {}
		var spritePath = runtimeField(definition, 'spritePath');
		var animations = runtimeField(definition, 'animations');
		// When the native custom_chars registry already resolved this actor, the
		// Character's generated script owns the atlas and every authored
		// animation.  Re-applying the same CharacterInfo through the companion
		// concatenates a second copy of the atlas and duplicates animation names,
		// which corrupts the frame collection and can SIGSEGV on the first
		// gameplay draw.  Donor extras below (icon name, camera/reposition
		// offsets) stay additive and are still applied.
		var nativeImplementation = runtimeField(character, 'resolvedImplementation');
		var nativeOwned = nativeImplementation != null
			&& StringTools.trim(Std.string(nativeImplementation)) != '';
		if (spritePath != null && animations != null && !nativeOwned)
			addCharacterAtlasAnimations(character, spritePath, animations, 0, 0, assetRoot);
		for (field in ['iconName', 'spritePath', 'frameLoadType']) {
			var value = runtimeField(definition, field);
			if (value != null && StringTools.trim(Std.string(value)) != '')
				try Reflect.setField(character, 'hxc' + field.charAt(0).toUpperCase()
					+ field.substr(1), Std.string(value)) catch (_:Dynamic) {}
		}
		var focus = runtimeField(definition, 'focusOffset');
		if (focus != null && Std.isOfType(focus, Array)) {
			var values:Array<Dynamic> = cast focus;
			var x = values.length > 0 ? runtimeFloatValue(values[0]) : 0;
			var y = values.length > 1 ? runtimeFloatValue(values[1]) : 0;
			addCharacterCameraOffset(character, x, y);
		}
		var extras = runtimeField(definition, 'extraData');
		if (extras != null && Std.isOfType(extras, Array)) {
			for (extra in (cast extras:Array<Dynamic>)) {
				if (extra == null)
					continue;
				var name = runtimeField(extra, 'name');
				var values = runtimeField(extra, 'values');
				if (name == null || values == null || !Std.isOfType(values, Array))
					continue;
				var copied:Array<Dynamic> = [];
				for (value in (cast values:Array<Dynamic>))
					copied.push(value);
				try {
					var data = runtimeField(character, 'hxcExtraData');
					if (data != null && Reflect.hasField(data, 'set'))
						Reflect.callMethod(data, Reflect.field(data, 'set'), [Std.string(name), copied]);
				} catch (_:Dynamic) {}
				if (Std.string(name).toLowerCase() == 'reposition' && copied.length >= 2)
					applyCharacterReposition(character, runtimeFloatValue(copied[0]),
						runtimeFloatValue(copied[1]));
			}
		}
		return character;
	}

	static function addCharacterCameraOffset(character:Dynamic, x:Float, y:Float):Void {
		try {
			var followX = runtimeField(character, 'followCamX');
			var followY = runtimeField(character, 'followCamY');
			Reflect.setField(character, 'followCamX', runtimeFloatValue(followX) + x);
			Reflect.setField(character, 'followCamY', runtimeFloatValue(followY) + y);
		} catch (_:Dynamic) {}
	}

	static function applyCharacterReposition(character:Dynamic, x:Float, y:Float):Void {
		try {
			var isPlayer = runtimeField(character, 'isPlayer') == true;
			var isGf = runtimeField(character, 'likeGf') == true
				|| Std.string(runtimeField(character, 'curCharacter')).toLowerCase() == 'gf';
			var xField = isGf ? 'gfOffsetX' : (isPlayer ? 'playerOffsetX' : 'enemyOffsetX');
			var yField = isGf ? 'gfOffsetY' : (isPlayer ? 'playerOffsetY' : 'enemyOffsetY');
			Reflect.setField(character, xField, runtimeIntValue(x));
			Reflect.setField(character, yField, runtimeIntValue(y));
			// HXC onAdd runs after the native stage has placed the actor. Apply the
			// authored reposition immediately as well; future character swaps read
			// the stored offset fields through PlayState's normal placement path.
			var currentX = runtimeField(character, 'x');
			var currentY = runtimeField(character, 'y');
			if (currentX != null)
				Reflect.setField(character, 'x', runtimeFloatValue(currentX) + x);
			if (currentY != null)
				Reflect.setField(character, 'y', runtimeFloatValue(currentY) + y);
		} catch (_:Dynamic) {}
	}

	/**
		Resolve the active native game-over substate without exposing it to HScript.
		The generated adapter receives only opaque handles returned by the methods
		below; missing substates are an explicit no-op for synthetic/runtime tests.
	*/
	static function gameOverTarget():Dynamic {
		try {
			var stateClass = Type.resolveClass('GameOverSubstate');
			if (stateClass == null)
				stateClass = Type.resolveClass('GameOverSubState');
			return stateClass == null ? null : Reflect.field(stateClass, 'instance');
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function gameOverCall(method:String, args:Array<Dynamic>):Dynamic
		return runtimeCall(gameOverTarget(), method, args);

	/** Create a scoped, native-owned game-over overlay handle. */
	public static function gameOverCreateOverlay(assetRoot:Dynamic, assetPath:Dynamic):Dynamic
		return gameOverCall('hxcCreateDeathOverlay', [assetRoot, assetPath]);

	public static function gameOverAddOverlay(overlay:Dynamic):Bool
		return gameOverCall('hxcAddDeathOverlay', [overlay]) == true;

	public static function gameOverSetOverlayAlpha(overlay:Dynamic, value:Dynamic):Bool
		return gameOverCall('hxcSetDeathOverlayAlpha', [overlay, value]) == true;

	public static function gameOverSetOverlayVisible(overlay:Dynamic, value:Dynamic):Bool
		return gameOverCall('hxcSetDeathOverlayVisible', [overlay, value]) == true;

	public static function gameOverSetOverlayPosition(overlay:Dynamic, x:Dynamic, y:Dynamic):Bool
		return gameOverCall('hxcSetDeathOverlayPosition', [overlay, x, y]) == true;

	public static function gameOverSetOverlayX(overlay:Dynamic, x:Dynamic):Bool
		return gameOverCall('hxcSetDeathOverlayX', [overlay, x]) == true;

	public static function gameOverSetOverlayY(overlay:Dynamic, y:Dynamic):Bool
		return gameOverCall('hxcSetDeathOverlayY', [overlay, y]) == true;

	public static function gameOverOffsetOverlay(overlay:Dynamic, x:Dynamic, y:Dynamic):Bool
		return gameOverCall('hxcOffsetDeathOverlay', [overlay, x, y]) == true;

	public static function gameOverCenterOverlay(overlay:Dynamic):Bool
		return gameOverCall('hxcCenterDeathOverlay', [overlay]) == true;

	public static function gameOverAddOverlayAnimation(overlay:Dynamic, name:Dynamic,
		prefix:Dynamic, fps:Dynamic, looped:Dynamic):Bool
		return gameOverCall('hxcAddDeathOverlayAnimation', [overlay,
			name == null ? '' : Std.string(name), prefix == null ? '' : Std.string(prefix), fps, looped]) == true;

	public static function gameOverPlayOverlayAnimation(overlay:Dynamic, name:Dynamic):Bool
		return gameOverCall('hxcPlayDeathOverlayAnimation', [overlay,
			name == null ? '' : Std.string(name)]) == true;

	public static function gameOverTweenCameraToOverlay(overlay:Dynamic, duration:Dynamic):Bool
		return gameOverCall('hxcTweenCameraToDeathOverlay', [overlay, duration]) == true;

	public static function gameOverResetCameraZoom():Bool
		return gameOverCall('hxcResetCameraZoom', []) == true;

	public static function gameOverSetMustNotExit(value:Dynamic):Bool
		return gameOverCall('hxcSetMustNotExit', [value]) == true;

	/** Explicitly reject donor process/window escape. */
	public static function gameOverCloseWindow():Bool {
		if (!windowCloseDiagnosticShown) {
			windowCloseDiagnosticShown = true;
			trace('[hxc-window-close-blocked] imported game-over hook requested window close');
		}
		return false;
	}

	/** Rebind character dispatch to a replacement owned by GameOverSubstate. */
	public static function bindGameOverCharacter(character:Dynamic):Bool {
		var state = resolveActiveState();
		if (state == null || character == null)
			return false;
		var method = runtimeField(state, 'hxcBindGameOverCharacter');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try {
			Reflect.callMethod(state, method, [character]);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	public static function clearGameOverCharacter(character:Dynamic):Bool {
		var state = resolveActiveState();
		if (state == null)
			return false;
		var method = runtimeField(state, 'hxcClearGameOverCharacter');
		if (method == null || !Reflect.isFunction(method))
			return false;
		try {
			Reflect.callMethod(state, method, [character]);
			return true;
		} catch (_:Dynamic) {
			return false;
		}
	}

	/** Native super-call targets used by composed character lifecycle methods. */
	public static function playAnimation(character:Dynamic, name:Dynamic,
		restart:Dynamic = false, ignoreOther:Dynamic = false, reversed:Dynamic = false):Dynamic {
		if (character == null)
			return character;
		var method = Reflect.field(character, 'playAnimation');
		var nativeAlias = method != null;
		if (method == null)
			method = Reflect.field(character, 'playAnim');
		if (method == null)
			return character;
		try return nativeAlias
			? Reflect.callMethod(character, method,
				[Std.string(name), restart == true, ignoreOther == true, reversed == true])
			: Reflect.callMethod(character, method,
				[Std.string(name), restart == true, reversed == true])
		catch (_:Dynamic) return character;
	}

	public static function playSingAnimation(character:Dynamic, direction:Dynamic,
		miss:Dynamic = false, suffix:Dynamic = ''):Dynamic {
		if (character == null)
			return character;
		var method = Reflect.field(character, 'playSingAnimation');
		if (method == null)
			return character;
		try return Reflect.callMethod(character, method, [runtimeIntValue(direction), miss == true,
			suffix == null ? '' : Std.string(suffix)]) catch (_:Dynamic) return character;
	}

	/**
		Lower a character's super.onNoteMiss(event) to the native actor surface,
		mirroring characterDefaultNoteHit: the donor base character answers a miss
		with the actor's miss sing animation.  Guarded reads keep ghost misses
		(payload without a live note) on the no-op path.
	*/
	public static function characterDefaultNoteMiss(character:Dynamic, event:Dynamic):Void {
		if (character == null || event == null)
			return;
		var note = runtimeField(event, 'note');
		var nativeNote = runtimeField(event, 'nativeNote');
		if (note == null && nativeNote != null)
			note = nativeNote;
		if (note == null)
			return;
		var noteData = runtimeField(note, 'noteData');
		var direction = runtimeField(note, 'direction');
		if (noteData != null) {
			var getDirection = runtimeField(noteData, 'getDirection');
			if (getDirection != null && Reflect.isFunction(getDirection))
				try direction = Reflect.callMethod(noteData, getDirection, []) catch (_:Dynamic) {}
			if (direction == null)
				direction = runtimeField(noteData, 'data');
		}
		var method = Reflect.field(character, 'playSingAnimation');
		if (method == null || !Reflect.isFunction(method))
			return;
		// The native playSingAnimation already appends the miss suffix when
		// `miss` is set, so the authored suffix stays empty here.
		try Reflect.callMethod(character, method, [runtimeIntValue(direction), true, ''])
		catch (_:Dynamic) {}
	}

	/**
		Mark a character-owned HXC note callback as having handled the actor's
		animation. V-Slice character onNoteHit overrides run before this fork's
		native singer; the marker lets the native judgement keep scoring while
		avoiding a second, normal sing animation after an authored return or
		custom playSingAnimation call.
	*/
	public static function markCharacterNoteHandled(event:Dynamic):Void {
		if (event == null)
			return;
		// Character callbacks may be generated with this marker before their
		// body so authored early returns keep ownership of custom animations.
		// Do not suppress the native singer when the callback received no usable
		// note view, as can happen when native typed Note fields are not reflected.
		var note = runtimeField(event, 'note');
		var nativeNote = runtimeField(event, 'nativeNote');
		if (note == null || nativeNote == null || runtimeField(note, 'noteData') == null)
			return;
		try Reflect.setField(event, 'characterHandled', true) catch (_:Dynamic) {}
	}

	/**
		Lower a character's super.onNoteHit(event) to the native actor surface.
		The generated wrapper marks the callback handled before reaching this
		boundary, so the normal PlayState singer is not invoked twice.
	*/
	public static function characterDefaultNoteHit(character:Dynamic, event:Dynamic):Void {
		if (character == null || event == null)
			return;
		var note = runtimeField(event, 'note');
		var nativeNote = runtimeField(event, 'nativeNote');
		if (note == null && nativeNote != null)
			note = nativeNote;
		if (note == null)
			return;
		var shouldBeSung = runtimeField(note, 'shouldBeSung');
		if (shouldBeSung == null && nativeNote != null)
			shouldBeSung = runtimeField(nativeNote, 'shouldBeSung');
		if (shouldBeSung == false)
			return;
		var noteData = runtimeField(note, 'noteData');
		var direction = runtimeField(note, 'direction');
		if (noteData != null) {
			var getDirection = runtimeField(noteData, 'getDirection');
			if (getDirection != null && Reflect.isFunction(getDirection))
				try direction = Reflect.callMethod(noteData, getDirection, []) catch (_:Dynamic) {}
			if (direction == null)
				direction = runtimeField(noteData, 'data');
		}
		var alt = runtimeField(note, 'altNum');
		if (alt == null && nativeNote != null)
			alt = runtimeField(nativeNote, 'altNum');
		var altNumber = runtimeIntValue(alt);
		var suffix = altNumber <= 0 ? '' : (altNumber == 1 ? 'alt' : 'alt' + altNumber);
		var method = Reflect.field(character, 'playSingAnimation');
		if (method == null || !Reflect.isFunction(method))
			return;
		try Reflect.callMethod(character, method, [runtimeIntValue(direction), false, suffix])
		catch (_:Dynamic) {}
	}

	public static function dance(character:Dynamic, force:Dynamic = false):Dynamic {
		if (character == null)
			return character;
		var method = Reflect.field(character, 'dance');
		if (method == null)
			return character;
		try return Reflect.callMethod(character, method, [force == true]) catch (_:Dynamic) return character;
	}

	/**
		Apply an HXC wrapper's literal `super('costumes/...')` definition through
		the native Character registry and canonical PlayState slot bridge. Unknown
		costume ids remain the existing actor, so a missing donor asset cannot crash
		gameplay or masquerade as a synthesized Character.
	*/
	public static function applyCharacterConstructor(character:Dynamic, requested:Dynamic):Dynamic {
		if (character == null || requested == null)
			return character;
		var raw = StringTools.trim(Std.string(requested));
		if (raw == '')
			return character;
		var candidates:Array<String> = [raw];
		var withoutPrefix = raw;
		if (withoutPrefix.toLowerCase().startsWith('costumes/'))
			withoutPrefix = withoutPrefix.substr('costumes/'.length);
		if (candidates.indexOf(withoutPrefix) < 0)
			candidates.push(withoutPrefix);
		var compact = StringTools.replace(raw, '/', '');
		if (candidates.indexOf(compact) < 0)
			candidates.push(compact);
		var target:String = null;
		for (candidate in candidates)
			if (characterExists(candidate)) {
				target = candidate;
				break;
			}
		if (target == null)
			return character;
		var currentName = runtimeField(character, 'curCharacter');
		if (currentName != null && StringTools.trim(Std.string(currentName)).toLowerCase()
			== target.toLowerCase())
			return character;
		var state = activeState != null ? activeState : resolveActiveState();
		if (state == null)
			return character;
		var role = characterType(character);
		var slot = characterSlot(role);
		if (slot == null)
			return character;
		var replacement = fetchCharacter(target);
		if (replacement == null)
			return character;
		copyDefaultCharacterPosition(character, replacement);
		if (Reflect.hasField(replacement, 'isPlayer'))
			Reflect.setProperty(replacement, 'isPlayer', slot == 'boyfriend');
		// Rebind the existing wrapper scope before switchToChar calls its onAdd;
		// otherwise the new native id would look dormant for one lifecycle pass.
		rebindCharacterScopes(state, character, replacement);
		var switched = runtimeCall(state, 'switchToChar', [replacement, slot, false]);
		if (switched == null && !runtimeHasMethod(state, 'switchToChar')) {
			Reflect.setField(state, slot, replacement);
			runtimeCall(state, 'add', [replacement]);
		}
		forgetCharacterType(character);
		return replacement;
	}

	static function rebindCharacterScopes(state:Dynamic, previous:Dynamic, replacement:Dynamic):Void {
		if (state == null || previous == null || replacement == null)
			return;
		var names:Dynamic = runtimeField(state, 'hxcCharacterScopeNames');
		if (names == null)
			return;
		try {
			var map:Map<String, String> = cast names;
			var previousName = runtimeField(previous, 'curCharacter');
			var replacementName = runtimeField(replacement, 'curCharacter');
			if (previousName == null || replacementName == null)
				return;
			for (scope in map.keys())
				if (StringTools.trim(Std.string(map.get(scope))).toLowerCase()
					== Std.string(previousName).toLowerCase())
					map.set(scope, Std.string(replacementName).toLowerCase());
		} catch (_:Dynamic) {}
	}

	/**
		Replace one of PlayState's three native character slots with an actor.

		StageHelper in the donor exposes addCharacter(Character, CharacterType),
		while this fork keeps actor ownership on PlayState. Route through the
		canonical native switchToChar path so slot fields, icons, control flags,
		HXC character scopes, health colours, and layer order stay synchronized.
		Only a minimal field/group fallback is used for a host test double with no
		switchToChar method; no donor stage graph or CharacterType object is
		synthesized here.
	*/
	public static function stageAddCharacter(stage:Dynamic, character:Dynamic, role:Dynamic):Dynamic {
		if (character == null)
			return null;

		var state = activeState != null ? activeState : resolveActiveState();
		var liveState = resolveActiveState();
		if (liveState != null && liveState != activeState)
			state = liveState;
		if (state == null)
			return character;

		var slot = characterSlot(role);
		if (slot == null) {
			var stageAdder = stage == null ? null : Reflect.field(stage, 'addCharacter');
			if (stageAdder != null) {
				try {
					Reflect.callMethod(stage, stageAdder, [character, role]);
					runtimeCall(stage, 'refresh', []);
					return character;
				} catch (_:Dynamic) {}
			}
			slot = characterSlot(characterTypeFor(character));
		}
		if (slot == null)
			return character;
		forgetCharacterType(character);

		var previous = runtimeField(state, slot);
		if (runtimeCall(stage, 'applyVSliceCharacterPresentation', [slot, character]) != true)
			copyDefaultCharacterPosition(previous, character);

		if (Reflect.hasField(character, 'isPlayer'))
			Reflect.setProperty(character, 'isPlayer', slot == 'boyfriend');
		// PlayState.switchToChar is the canonical native replacement path. It
		// updates the real slot, icon, control flags, HXC character scope,
		// health colours, and layer order in one place. Keep the reflective call
		// narrow: if a test double or an older host has no such method, use the
		// minimal field/group fallback rather than inventing donor semantics.
		var switched = runtimeCall(state, 'switchToChar', [character, slot, false]);
		if (switched == null && !runtimeHasMethod(state, 'switchToChar')) {
			if (previous != null && previous != character)
				runtimeCall(state, 'remove', [previous]);
			Reflect.setField(state, slot, character);
			runtimeCall(state, 'add', [character]);
		}
		if (stage != null) {
			runtimeCall(stage, 'rebindCharacterZ', [slot, previous, character]);
			runtimeCall(stage, 'refresh', []);
		}
		return character;
	}

	/**
		Carry the donor's CharacterType until stageAddCharacter reaches the
		canonical slot bridge. Native Character keeps the role as a lightweight
		characterType field; the slot argument remains authoritative for gameplay
		characters.
	*/
	public static function setCharacterType(character:Dynamic, role:Dynamic):Dynamic {
		if (character == null)
			return character;
		if (Reflect.hasField(character, 'characterType'))
			Reflect.setField(character, 'characterType', role);
		for (hint in characterTypeHints)
			if (hint != null && hint.character == character) {
				hint.role = role;
				return character;
			}
		characterTypeHints.push({character: character, role: role});
		return character;
	}

	/**
		Update the native health icon when the actor's role is known. The canonical
		PlayState switch also performs this update; this adapter covers donor calls
		which occur immediately before that switch without invoking a missing donor
		Character method. Unknown/unattached actors are returned unchanged.
	*/
	public static function initHealthIcon(character:Dynamic, isDad:Dynamic = false):Dynamic {
		var state = activeState != null ? activeState : resolveActiveState();
		if (state == null)
			return character;
		var slot = characterSlot(characterTypeFor(character));
		if (slot == null) {
			if (character == runtimeField(state, 'boyfriend'))
				slot = 'boyfriend';
			else if (character == runtimeField(state, 'dad'))
				slot = 'dad';
			else if (isDad == true)
				slot = 'dad';
		}
		if (slot == null)
			return character;
		var icon = runtimeField(state, slot == 'dad' ? 'iconP2' : 'iconP1');
		var name = runtimeField(character, 'curCharacter');
		if (name == null || Std.string(name) == '')
			name = runtimeField(character, 'requestedCharacter');
		if (icon != null && name != null)
			runtimeCall(icon, 'switchAnim', [name]);
		return character;
	}

	static function characterSlot(role:Dynamic):String {
		if (role == null)
			return null;

		var value = Std.string(role).toLowerCase();
		switch (value) {
			case 'bf', 'boyfriend', 'player', 'character.bf':
				return 'boyfriend';
			case 'dad', 'opponent', 'player2', 'character.dad':
				return 'dad';
			case 'gf', 'girlfriend', 'character.gf':
				return 'gf';
			default:
				return null;
		}
	}

	static function characterTypeFor(character:Dynamic):Dynamic {
		if (character == null)
			return null;
		for (hint in characterTypeHints)
			if (hint != null && hint.character == character)
				return hint.role;
		return null;
	}

	static function forgetCharacterType(character:Dynamic):Void {
		if (character == null)
			return;
		var remaining:Array<Dynamic> = [];
		for (hint in characterTypeHints)
			if (hint != null && hint.character != character)
				remaining.push(hint);
		characterTypeHints = remaining;
	}

	static function runtimeHasMethod(owner:Dynamic, name:String):Bool {
		return owner != null && Reflect.field(owner, name) != null;
	}

	static function copyDefaultCharacterPosition(previous:Dynamic, character:Dynamic):Void {
		if (previous == null || character == null)
			return;
		try {
			var x = runtimeField(character, 'x');
			var y = runtimeField(character, 'y');
			if ((x == null || x == 0) && (y == null || y == 0)) {
				if (Reflect.hasField(previous, 'x')) Reflect.setField(character, 'x', runtimeField(previous, 'x'));
				if (Reflect.hasField(previous, 'y')) Reflect.setField(character, 'y', runtimeField(previous, 'y'));
			}
			if (runtimeField(character, 'zIndex') == null || runtimeField(character, 'zIndex') == 0)
				if (Reflect.hasField(previous, 'zIndex')) Reflect.setField(character, 'zIndex', runtimeField(previous, 'zIndex'));
		} catch (_:Dynamic) {}
	}

	static function runtimeCall(owner:Dynamic, name:String, args:Array<Dynamic>):Dynamic {
		if (owner == null)
			return null;
		var method = Reflect.field(owner, name);
		if (method == null)
			return null;
		try return Reflect.callMethod(owner, method, args) catch (_:Dynamic) return null;
	}

	static function runtimeField(value:Dynamic, name:String):Dynamic {
		if (value == null || name == null)
			return null;
		// Compat aliases such as PlayState.currentCameraZoom are physical
		// properties; plain Reflect.field cannot see them on hxcpp.
		try {
			if (Reflect.hasField(value, name))
				return Reflect.field(value, name);
			return Reflect.getProperty(value, name);
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function runtimeIntValue(value:Dynamic):Int {
		if (value == null)
			return 0;
		if (Std.isOfType(value, Int))
			return cast value;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? 0 : Std.int(parsed);
	}

	static function runtimeFloatValue(value:Dynamic):Float {
		if (value == null)
			return 0;
		if (Std.isOfType(value, Float) || Std.isOfType(value, Int))
			return cast value;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? 0 : parsed;
	}

	/** Host application version, independent of Flixel and donor API versions. */
	static function engineVersion():String return EngineBranding.version();

	/**
		Construct only the explicit native aliases owned by this engine. Imported
		ScriptedMusicBeat state names are resolved by HxcStateFactory against the
		caller's manifest root; this helper deliberately remains native-only so it
		cannot become an arbitrary reflection/factory escape hatch.
	*/
	public static function stateInit(name:String):Dynamic {
		var key = name == null ? '' : StringTools.trim(name).toLowerCase();
		var className = switch (key) {
			case 'mainmenustate': 'MainMenuState';
			case 'storymenustate': 'StoryMenuState';
			case 'freeplaystate': 'FreeplayState';
			case 'titlestate': 'TitleState';
			// Explicit native destinations for the two V-Slice menu names used by
			// imported HXC closures. No other qualified donor class is resolved here.
			case 'creditsstate' | 'credits': 'CreditsState';
			case 'optionsstate' | 'savedatastate' | 'options': 'SaveDataState';
			default: '';
		};
		if (className == '')
			return null;
		var stateClass = Type.resolveClass(className);
		return stateClass == null ? null : Type.createInstance(stateClass, []);
	}

	/** Return the isolated store for one generated HXC script namespace. */
	public static function openStore(namespace:String):Dynamic {
		var key = normalizeNamespace(namespace);
		if (!stores.exists(key))
			stores.set(key, makeStore(key));
		return stores.get(key);
	}

	/** Seed a root-scoped options store from a complete literal preference object. */
	public static function seedStoreDefaults(store:Dynamic, defaults:Dynamic,
		?recordKey:String):Void {
		if (store == null || defaults == null)
			return;
		if (recordKey != null && StringTools.trim(recordKey) != '') {
			var getValue = runtimeField(store, 'get');
			var setValue = runtimeField(store, 'set');
			var existing = getValue != null && Reflect.isFunction(getValue)
				? Reflect.callMethod(store, getValue, [recordKey]) : null;
			if (existing == null && setValue != null && Reflect.isFunction(setValue))
				Reflect.callMethod(store, setValue, [recordKey, defaults]);
		}
		for (field in Reflect.fields(defaults))
			if (!Reflect.hasField(store, field))
				Reflect.setField(store, field, Reflect.field(defaults, field));
	}

	/** Clear the process-local adapter state. This is used by tests/tools only. */
	public static function clear():Void {
		if (activeState != null) {
			var clearShaders = runtimeField(activeState, 'hxcClearRuntimeShaderBindings');
			if (clearShaders != null && Reflect.isFunction(clearShaders))
				try Reflect.callMethod(activeState, clearShaders, []) catch (_:Dynamic) {}
		}
		stores = new Map<String, Dynamic>();
		zIndexKeys = [];
		zIndexValues = [];
		activeState = null;
		characterTypeHints = [];
		creditsEntriesValue = [];
		discordRPCIconValue = '';
		discordRPCAlbumValue = '';
		currentChartAlbumValue = '';
		skipNextTransInValue = false;
		skipNextTransOutValue = false;
		activeMenuOverlayState = null;
		activePauseOverlayState = null;
		resetGameOverSettings();
		if (talliesView != null)
			talliesView.clear();
		preferencesView = null;
		clearConstantsViews();
	}

	static function normalizeNamespace(namespace:String):String {
		var value = namespace == null ? '' : StringTools.trim(namespace);
		if (value == '')
			value = 'default';
		return ~/[^A-Za-z0-9_.:-]+/g.replace(value, '_');
	}

	static function makeStore(namespace:String):Dynamic {
		var values:Map<String, Dynamic> = new Map<String, Dynamic>();
		var store:Dynamic = {};
		var getValue = function(key:Dynamic):Dynamic {
			return key == null ? null : values.get(Std.string(key));
		};
		var setValue = function(key:Dynamic, value:Dynamic):Dynamic {
			if (key != null)
				values.set(Std.string(key), value);
			return value;
		};
		var hasValue = function(key:Dynamic):Bool {
			return key != null && values.exists(Std.string(key));
		};
		var removeValue = function(key:Dynamic):Bool {
			return key != null && values.remove(Std.string(key));
		};
		Reflect.setField(store, 'namespace', namespace);
		// FlxSave-compatible callers use `.data` after `bind()`. Point it back at
		// the same isolated object so direct option fields remain mutable and
		// never escape this namespace.
		Reflect.setField(store, 'data', store);
		Reflect.setField(store, 'bind', function(?_name:String, ?_owner:String):Dynamic return store);
		Reflect.setField(store, 'get', getValue);
		Reflect.setField(store, 'set', setValue);
		Reflect.setField(store, 'exists', hasValue);
		Reflect.setField(store, 'has', hasValue);
		Reflect.setField(store, 'remove', removeValue);
		// The native save API flushes to disk. Imported HXC stores are deliberately
		// process-local; retaining a no-op flush keeps authored lifecycle code
		// deterministic without granting it filesystem access.
		Reflect.setField(store, 'flush', function():Void {});
		Reflect.setField(store, 'hasBeatenSong', function(_song:Dynamic, ?_difficulty:Dynamic):Bool return false);
		// Static Save-like preference getters lower to this root-scoped facade.
		// Authored defaults are copied by seedStoreDefaults when a selected HXC
		// module declares and initializes a literal option record.
		Reflect.setField(store, 'getSave', function():Dynamic return store);
		// V-Slice's Save.instance.modOptions is the same key/value view. Keep it
		// self-contained rather than manufacturing donor-specific option objects.
		Reflect.setField(store, 'modOptions', store);
		return store;
	}
}

/**
	Active-song tally view used by generated HXC adapters.  This class has no
	Flixel dependency: the engine state is accessed through a narrow reflective
	surface, which keeps HxcCompatRuntime executable in standalone tests too.
*/
class HxcCompatTallyView {
	var state:Dynamic;
	var initialized:Bool = false;
	/** Plain fields are intentional: HScript accesses Dynamic members directly. */
	public var totalNotes:Int = 0;
	public var missed:Int = 0;
	public var sick:Int = 0;
	public var good:Int = 0;
	public var bad:Int = 0;
	public var shit:Int = 0;
	public var combo:Int = 0;
	public var maxCombo:Int = 0;
	public var totalNotesHit:Float = 0;

	public function new() {}

	public function bind(next:Dynamic):Void {
		state = next;
		initialized = false;
		totalNotes = 0;
		missed = 0;
		sick = 0;
		good = 0;
		bad = 0;
		shit = 0;
		combo = 0;
		maxCombo = 0;
		totalNotesHit = 0;
	}

	public function beginSong():Void {
		initialized = true;
		// A retry starts a fresh donor tally even though the view object is
		// intentionally reused by the active interpreter.  Clear derived values
		// before reading the native counters so maxCombo (and standalone fallback
		// fields) cannot leak across songs.
		sick = 0;
		good = 0;
		bad = 0;
		shit = 0;
		combo = 0;
		maxCombo = 0;
		totalNotesHit = 0;
		totalNotes = countPlayerNotes(state);
		var native = readMisses(state);
		missed = native == null ? 0 : native;
		syncNativeCounters();
	}

	public function observeIncoming(note:Dynamic):Void {
		if (initialized)
			return;
		// The current note has already left unspawnNotes when this hook runs;
		// include it once so lazy initialization cannot lose the first note.
		totalNotes = countPlayerNotes(state)
			+ (isPlayerNote(note) ? 1 : 0);
		var native = readMisses(state);
		missed = native == null ? 0 : native;
		syncNativeCounters();
		initialized = true;
	}

	/** Refresh only native-backed fields before one generated callback runs. */
	public function syncBeforeCallback():Void {
		if (!initialized)
			beginSong();
		var native = readMisses(state);
		if (native != null)
			missed = native;
		syncNativeCounters();
	}

	/** Commit mutable tally fields after one generated callback returns. */
	public function syncAfterCallback():Void {
		writeMisses(state, missed);
		writeNativeCounters();
	}

	public function clear():Void {
		state = null;
		initialized = false;
		totalNotes = 0;
		missed = 0;
		sick = 0;
		good = 0;
		bad = 0;
		shit = 0;
		combo = 0;
		maxCombo = 0;
		totalNotesHit = 0;
	}

	function syncNativeCounters():Void {
		sick = readCounter('sicks', sick);
		good = readCounter('goods', good);
		bad = readCounter('bads', bad);
		shit = readCounter('shits', shit);
		combo = readInstanceInt('combo', combo);
		if (combo > maxCombo)
			maxCombo = combo;
		// V-Slice's `Highscore.tallies.totalNotesHit` is a raw successful-hit
		// count.  PlayState.totalNotesHit is weighted accuracy (wife/simple/
		// binary), so copying it would make donor accuracy formulas drift.  The
		// native totalPlayed/misses pair preserves the raw count; test doubles
		// without totalPlayed retain the old weighted fallback for compatibility.
		var played = readInstanceIntOptional('totalPlayed');
		if (played != null) {
			var nativeMisses = readMisses(state);
			var failed = nativeMisses == null ? missed : nativeMisses;
			totalNotesHit = Math.max(0, played - failed);
		} else {
			var hit = readInstanceFloat('totalNotesHit');
			if (hit != null)
				totalNotesHit = hit;
		}
	}

	function writeNativeCounters():Void {
		writeCounter('sicks', sick);
		writeCounter('goods', good);
		writeCounter('bads', bad);
		writeCounter('shits', shit);
		if (state != null && hasField(state, 'combo')) {
			try Reflect.setField(state, 'combo', combo) catch (_:Dynamic) {}
		}
	}

	function readCounter(name:String, fallback:Int):Int {
		var value:Dynamic = field(state, name);
		if (value == null) {
			var stateClass = Type.resolveClass('PlayState');
			value = stateClass == null ? null : field(stateClass, name);
		}
		return value == null ? fallback : intValue(value);
	}

	function writeCounter(name:String, value:Int):Void {
		if (state != null && hasField(state, name)) {
			try {
				Reflect.setField(state, name, value);
				return;
			} catch (_:Dynamic) {}
		}
		var stateClass = Type.resolveClass('PlayState');
		if (stateClass != null && hasField(stateClass, name)) {
			try Reflect.setField(stateClass, name, value) catch (_:Dynamic) {}
		}
	}

	function readInstanceInt(name:String, fallback:Int):Int {
		var value = field(state, name);
		return value == null ? fallback : intValue(value);
	}

	function readInstanceIntOptional(name:String):Null<Int> {
		var value = field(state, name);
		return value == null ? null : intValue(value);
	}

	function readInstanceFloat(name:String):Null<Float> {
		var value = field(state, name);
		if (value == null)
			return null;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? null : parsed;
	}

	function countPlayerNotes(source:Dynamic):Int {
		if (source == null)
			return 0;
		var total = 0;
		var found = false;
		var pending = field(source, 'unspawnNotes');
		if (isArray(pending)) {
			found = true;
			total += countNoteList(cast pending);
		}
		var activeGroup = field(source, 'notes');
		var active = field(activeGroup, 'members');
		if (isArray(active)) {
			found = true;
			total += countNoteList(cast active);
		}
		if (found)
			return total;
		return countChartNotes(source);
	}

	function countNoteList(values:Array<Dynamic>):Int {
		var total = 0;
		if (values == null)
			return total;
		for (note in values)
			if (isPlayerNote(note))
				total++;
		return total;
	}

	function countChartNotes(source:Dynamic):Int {
		var chartClass = Type.resolveClass('PlayState');
		var chart:Dynamic = chartClass == null ? null : field(chartClass, 'SONG');
		if (chart == null)
			chart = field(source, 'SONG');
		var sections = field(chart, 'notes');
		if (!isArray(sections))
			return 0;
		var total = 0;
		for (section in (cast sections:Array<Dynamic>)) {
			var rows = field(section, 'sectionNotes');
			if (!isArray(rows))
				continue;
			var mustHit = field(section, 'mustHitSection') == true;
			for (row in (cast rows:Array<Dynamic>)) {
				if (!isArray(row))
					continue;
				var values:Array<Dynamic> = cast row;
				if (values.length < 2 || values[1] == -1)
					continue;
				var lane = intValue(values[1]);
				var player = mustHit;
				if (lane % 8 >= 4)
					player = !player;
				if (player)
					total++;
			}
		}
		return total;
	}

	function isPlayerNote(note:Dynamic):Bool
		return note != null && field(note, 'mustPress') == true;

	function readMisses(source:Dynamic):Null<Int> {
		var value = field(source, 'misses');
		if (value == null) {
			var stateClass = Type.resolveClass('PlayState');
			value = stateClass == null ? null : field(stateClass, 'misses');
		}
		return value == null ? null : intValue(value);
	}

	function writeMisses(source:Dynamic, value:Int):Bool {
		if (source != null && hasField(source, 'misses')) {
			try {
				Reflect.setField(source, 'misses', value);
				return true;
			} catch (_:Dynamic) {}
		}
		var stateClass = Type.resolveClass('PlayState');
		if (stateClass != null && hasField(stateClass, 'misses')) {
			try {
				Reflect.setField(stateClass, 'misses', value);
				return true;
			} catch (_:Dynamic) {}
		}
		return false;
	}

	static function field(value:Dynamic, name:String):Dynamic {
		if (value == null || name == null)
			return null;
		try return Reflect.field(value, name) catch (_:Dynamic) return null;
	}

	static function hasField(value:Dynamic, name:String):Bool {
		if (value == null || name == null)
			return false;
		try return Reflect.hasField(value, name) catch (_:Dynamic) return false;
	}

	static function isArray(value:Dynamic):Bool
		return value != null && Std.isOfType(value, Array);

	static function intValue(value:Dynamic):Int {
		if (value == null)
			return 0;
		if (Std.isOfType(value, Int))
			return cast value;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isNaN(parsed) ? 0 : Std.int(parsed);
	}
}
