package;

import flixel.FlxCamera;
import flixel.FlxSprite;
import flixel.addons.display.FlxBackdrop;
import flixel.addons.transition.FlxTransitionableState;
import flixel.addons.text.FlxTypeText;
import flixel.animation.FlxAnimationController;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup;
import flixel.math.FlxMath;
import flixel.math.FlxPoint;
import flixel.math.FlxPoint.FlxBasePoint;
import flixel.math.FlxRect;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextFormat;
import flixel.text.FlxText.FlxTextAlign;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.tweens.FlxEase;
import flixel.tweens.FlxTween.FlxTweenType;
import flixel.ui.FlxBar;
import flixel.ui.FlxBar.FlxBarFillDirection;
import flixel.util.FlxAxes;
import flixel.util.FlxDestroyUtil;
import flixel.util.FlxSort;
import flixel.util.FlxSpriteUtil;
import flixel.util.FlxStringUtil;
import flixel.util.FlxTimer;
import flixel.util.FlxTimer.FlxTimerManager;
import haxe.Timer as HaxeTimer;
import openfl.display.BlendMode;
import openfl.display.BitmapData;
import openfl.display.FPS;
import openfl.display.Sprite;
import openfl.text.TextField;
import openfl.text.TextFormat;
import openfl.system.System;
import haxe.io.Path as HaxePath;
import CodenameRatingManager.CodenameWindowPreset;

/** Shared explicit Codename imports used by gameplay and imported-state hosts.
 * Owner-specific paths, constructors and state classes are bound by the host. */
class CodenameImportBindings {
	public static function addShared(bindings:Map<String, Dynamic>, interp:CodenameScriptInterp,
		paths:CodenamePaths):Void {
		if (bindings == null || interp == null || paths == null)
			throw '[codename-import] Shared binding context is incomplete';
		bindings.set('CodenameKeyValueIterator', CodenameKeyValueIterator.facade());
		bindings.set('graphicCache', interp.graphicCache);
		bindings.set('Flags', codenameFlags());
		bindings.set('Std', Std);
		bindings.set('Reflect', Reflect);
		bindings.set('Type', typeConstants());
		bindings.set('StringTools', stringToolsConstants());
		bindings.set('haxe.Json', jsonConstants());
		bindings.set('haxe.Timer', timerConstants());
		bindings.set('flixel.FlxG', interp.flxG);
		bindings.set('flixel.FlxCamera', FlxCamera);
		bindings.set('flixel.FlxSprite', FlxSprite);
		bindings.set('flixel.input.keyboard.FlxKey', CodenameFlxKeyFacade.snapshot());
		bindings.set('FlxSprite', FlxSprite);
		bindings.set('flixel.animation.FlxAnimationController', FlxAnimationController);
		bindings.set('flixel.util.FlxDestroyUtil', FlxDestroyUtil);
		bindings.set('flixel.util.FlxSort', FlxSort);
		bindings.set('flixel.group.FlxGroup', FlxTypedGroup);
		bindings.set('flixel.group.FlxGroup.FlxTypedGroup', FlxTypedGroup);
		// FlxSpriteGroup is a typedef in this Flixel version, so scripts need
		// the concrete generic group class as the HScript runtime constructor.
		bindings.set('flixel.group.FlxSpriteGroup', FlxTypedSpriteGroup);
		bindings.set('flixel.group.FlxSpriteGroup.FlxTypedSpriteGroup', FlxTypedSpriteGroup);
		bindings.set('funkin.backend.MusicBeatGroup', CodenameMusicBeatGroupCompat);
		bindings.set('flixel.addons.text.FlxTypeText', FlxTypeText);
		bindings.set('flixel.addons.display.FlxBackdrop', FlxBackdrop);
		bindings.set('flixel.addons.transition.FlxTransitionableState', FlxTransitionableState);
		bindings.set('flixel.tweens.FlxTween', interp.tweenFacade());
		bindings.set('flixel.tweens.FlxTween.FlxTweenType', tweenTypeConstants());
		// Newer Codename scripts import the enum abstract from its top-level path.
		bindings.set('flixel.tweens.FlxTweenType', tweenTypeConstants());
		bindings.set('flixel.tweens.FlxEase', FlxEase);
		bindings.set('flixel.util.FlxTimer', FlxTimer);
		bindings.set('flixel.util.FlxTimerManager', FlxTimerManager);
		bindings.set('haxe.io.Path', pathConstants());
		bindings.set('flixel.util.FlxStringUtil', flxStringUtilConstants());
		// Math is imported by some Codename scripts even though it is normally
		// available as an interpreter global. Keep import validation and runtime
		// lookup on the same standard-library value.
		bindings.set('Math', Math);
		bindings.set('flixel.math.FlxMath', FlxMath);
		bindings.set('flixel.FlxMath', FlxMath);
		bindings.set('flixel.util.FlxSpriteUtil', CodenameFlxSpriteUtilCompat.facade());
		bindings.set('flixel.math.FlxRect', FlxRect);
		// Codename exposes the newer flattened FlxBasePoint import and scripts
		// also use FlxPoint.get without importing it. FlxPoint's inline static
		// methods need reflectable wrappers in the HScript runtime.
		bindings.set('flixel.math.FlxPoint', pointConstants());
		bindings.set('flixel.math.FlxBasePoint', FlxBasePoint);
		bindings.set('flixel.ui.FlxBar', FlxBar);
		bindings.set('flixel.ui.FlxBar.FlxBarFillDirection', barFillDirectionConstants());
		bindings.set('flixel.ui.FlxBarFillDirection', barFillDirectionConstants());
		bindings.set('flixel.util.FlxAxes', {X:FlxAxes.X, Y:FlxAxes.Y, XY:FlxAxes.XY});
		bindings.set('flixel.util.FlxColor', HxcFlxColorCompat);
		bindings.set('flixel.text.FlxText', FlxText);
		// Flixel 6.1.2 declares FlxTextFormat as a secondary type in FlxText.hx,
		// while Codename scripts commonly import its flattened path.
		bindings.set('flixel.text.FlxTextFormat', FlxTextFormat);
		bindings.set('flixel.text.FlxText.FlxTextFormat', FlxTextFormat);
		bindings.set('flixel.text.FlxTextAlign', {
			LEFT:FlxTextAlign.LEFT, CENTER:FlxTextAlign.CENTER,
			RIGHT:FlxTextAlign.RIGHT, JUSTIFY:FlxTextAlign.JUSTIFY
		});
		bindings.set('flixel.text.FlxTextBorderStyle', textBorderStyleConstants());
		bindings.set('openfl.display.BlendMode', blendModeConstants());
		bindings.set('openfl.display.BitmapData', BitmapData);
		bindings.set('openfl.display.FPS', FPS);
		bindings.set('openfl.display.Sprite', Sprite);
		bindings.set('openfl.text.TextField', TextField);
		bindings.set('openfl.text.TextFormat', TextFormat);
		bindings.set('funkin.backend.utils.MemoryUtil', memoryUtilConstants());
		bindings.set('funkin.backend.system.Main', Main);
		bindings.set('Main', Main);
		bindings.set('funkin.backend.system.framerate.Framerate', CodenameFramerateCompat.facade());
		bindings.set('openfl.utils.Assets', paths.assets());
		// Psych's Lime Assets.getText returns null for missing text files. Keep
		// that contract behind the same selected-owner path checks as OpenFL.
		bindings.set('lime.utils.Assets', paths.limeAssets());
		bindings.set('funkin.backend.FunkinSprite', CodenameFunkinSprite);
		bindings.set('funkin.backend.FunkinText', CodenameFunkinText);
		// Freeplay and gameplay scripts parse charts through the selected owner's
		// Codename adapter, which keeps authored metadata and owner boundaries.
		bindings.set('funkin.backend.chart.Chart', CodenameChartCompat.facade(paths));
		// HL17's typewriter only uses Flixel text, timers and the selected owner's
		// trebuc font. Keep the small shared behavior in-engine so the donor's
		// private Haxe class doesn't need to be compiled or imported dynamically.
		bindings.set('HLTypeText', CodenameHLTypeTextCompat);
		CodenameHL17UICompat.addBindings(bindings);
		// Shared contexts get a menu-return fallback. CodenameModBindings replaces
		// this for an active imported-state host so source Sys.exit can quit the app.
		bindings.set('Sys', CodenameSysCompat.facade());
		bindings.set('funkin.backend.MusicBeatTransition', CodenameMusicBeatTransition);
		bindings.set('MusicBeatTransition', CodenameMusicBeatTransition);
		bindings.set('StickerPack', CodenameStickerPack);
		// Older Codename releases exposed the same class from funkin.ui.
		bindings.set('funkin.ui.FunkinText', CodenameFunkinText);
		bindings.set('funkin.backend.utils.DiscordUtil', discordUtilConstants());
		bindings.set('funkin.backend.Paths', paths);
		bindings.set('Paths', paths);
		// The native chart editor is the truthful host for Codename's Charter
		// import. It edits the active native chart instead of returning a dummy.
		bindings.set('funkin.editors.charter.Charter', CodenameCharterAdapter);
		bindings.set('funkin.options.Options', new CodenameOptionsFacade());
		bindings.set('funkin.game.Character', Character);
		bindings.set('funkin.game.scoring.RatingManager', CodenameRatingManager);
		bindings.set('funkin.game.scoring.HitWindowData.WindowPreset', windowPresetConstants());
		bindings.set('funkin.game.GameOverSubstate', GameOverSubstate);
		bindings.set('funkin.game.PauseSubState', PauseSubState);
		bindings.set('funkin.savedata.FunkinSave', CodenameFunkinSaveCompat);
		bindings.set('funkin.savedata.HighscoreChange', highscoreChangeConstants());
		// Legacy Codename stages share the same owner-scoped Away3D adapter in
		// song, stage, and imported-state interpreters.
		CodenameFlx3DBindings.addShared(bindings, interp, paths);
	}

	public static function pointConstants():Dynamic {
		return {
			get: function(x:Float = 0, y:Float = 0):Dynamic return FlxPoint.get(x, y),
			weak: function(x:Float = 0, y:Float = 0):Dynamic return FlxPoint.weak(x, y)
		};
	}

	/** Codename's HUD scripts use these Haxe reflection helpers to label the
	 * active native state. Keep the real Type behavior behind a reflectable
	 * facade because static methods are not consistently visible to HScript. */
	public static function typeConstants():Dynamic {
		return {
			getClass: function(value:Dynamic):Dynamic return Type.getClass(value),
			getClassName: function(value:Dynamic):String return Type.getClassName(value)
		};
	}

	/** Haxe Timer's monotonic timestamp used by imported FPS displays. */
	public static function timerConstants():Dynamic {
		return {stamp: function():Float return HaxeTimer.stamp()};
	}

	/** Codename MemoryUtil.currentMemUsage reports process memory in bytes.
	 * Use OpenFL's live native allocation counter, matching MemoryCounter's
	 * source and avoiding a synthetic or fixed value. */
	public static function memoryUtilConstants():Dynamic {
		return {currentMemUsage: function():Float return System.totalMemoryNumber};
	}

	/** HScript imports need reflectable Path statics; the native class's inline
	 * helpers do not resolve reliably through the interpreter.
	 */
	public static function pathConstants():Dynamic {
		return {
			withoutExtension: function(path:String):String return HaxePath.withoutExtension(path),
			directory: function(path:String):String return HaxePath.directory(path),
			extension: function(path:String):String return HaxePath.extension(path),
			join: function(parts:Array<String>):String return HaxePath.join(parts)
		};
	}

	/** Values used by mounted source scripts. Keep this reflectable for HScript. */
	public static function codenameFlags():Dynamic
		return {DEFAULT_BPM:100.0, DEFAULT_NOTE_MS_LIMIT:CodenameStrumlineNoteCollection.DEFAULT_NOTE_MS_LIMIT,
			ICON_LERP:0.33};

	/** Enum constants consumed by Codename's source-facing score API. */
	public static function highscoreChangeConstants():Dynamic
		return {CCoopMode:'CCoopMode', COpponentMode:'COpponentMode'};

	public static function windowPresetConstants():Dynamic {
		return {
			DEFAULT: CodenameWindowPreset.DEFAULT,
			CNE_CLASSIC: CodenameWindowPreset.CNE_CLASSIC,
			FNF_CLASSIC: CodenameWindowPreset.FNF_CLASSIC,
			FNF_VSLICE: CodenameWindowPreset.FNF_VSLICE
		};
	}

	/** HScript imports resolve static classes through runtime values. Expose the
	 * StringTools calls used by imported Codename modules as an explicit facade
	 * instead of binding the Haxe class object, whose static methods are not
	 * reflectable on all targets. */
	public static function stringToolsConstants():Dynamic {
		return {
			replace: function(value:String, search:String, replacement:String):String
				return StringTools.replace(value, search, replacement)
		};
	}

	/** HScript imports need a reflectable facade for FlxStringUtil's static
	 * methods. Keep formatting in Flixel itself so locale and rounding behavior
	 * stay aligned with the engine version scripts target. */
	public static function flxStringUtilConstants():Dynamic {
		return {
			formatMoney: function(amount:Float, showDecimal:Bool = true, englishStyle:Bool = true):String
				return FlxStringUtil.formatMoney(amount, showDecimal, englishStyle)
		};
	}

	/** HScript cannot reflect inline haxe.Json methods from the native class
	 * value reliably; keep its source-facing parse/stringify calls explicit. */
	public static function jsonConstants():Dynamic {
		return {
			parse: function(text:String):Dynamic return haxe.Json.parse(text),
			stringify: function(value:Dynamic, ?replacer:(key:Dynamic, value:Dynamic)->Dynamic,
				?space:String):String return haxe.Json.stringify(value, replacer, space)
		};
	}

	/** Codename fills DiscordUtil.user after its RPC handshake. This host's
	 * discord-rpc wrapper does not expose that callback payload, so report the
	 * documented no-user state. Scripts that check globalName then take their
	 * authored offline fallback instead of seeing an invented account name. */
	public static function discordUtilConstants():Dynamic {
		return {user:{globalName:null}};
	}

	/** Enum abstracts are compile-time values, not runtime classes. Imported
	 * scripts need their familiar static constants, so expose only those values. */
	public static function tweenTypeConstants():Dynamic {
		return {
			PERSIST: FlxTweenType.PERSIST,
			ONESHOT: FlxTweenType.ONESHOT,
			LOOPING: FlxTweenType.LOOPING,
			PINGPONG: FlxTweenType.PINGPONG,
			BACKWARD: FlxTweenType.BACKWARD
		};
	}

	public static function blendModeConstants():Dynamic {
		return {
			ADD: BlendMode.ADD, ALPHA: BlendMode.ALPHA, DARKEN: BlendMode.DARKEN,
			DIFFERENCE: BlendMode.DIFFERENCE, ERASE: BlendMode.ERASE, HARDLIGHT: BlendMode.HARDLIGHT,
			INVERT: BlendMode.INVERT, LAYER: BlendMode.LAYER, LIGHTEN: BlendMode.LIGHTEN,
			MULTIPLY: BlendMode.MULTIPLY, NORMAL: BlendMode.NORMAL, OVERLAY: BlendMode.OVERLAY,
			SCREEN: BlendMode.SCREEN, SHADER: BlendMode.SHADER, SUBTRACT: BlendMode.SUBTRACT
		};
	}

	public static function barFillDirectionConstants():Dynamic {
		return {
			LEFT_TO_RIGHT: FlxBarFillDirection.LEFT_TO_RIGHT,
			RIGHT_TO_LEFT: FlxBarFillDirection.RIGHT_TO_LEFT,
			TOP_TO_BOTTOM: FlxBarFillDirection.TOP_TO_BOTTOM,
			BOTTOM_TO_TOP: FlxBarFillDirection.BOTTOM_TO_TOP,
			HORIZONTAL_INSIDE_OUT: FlxBarFillDirection.HORIZONTAL_INSIDE_OUT,
			HORIZONTAL_OUTSIDE_IN: FlxBarFillDirection.HORIZONTAL_OUTSIDE_IN,
			VERTICAL_INSIDE_OUT: FlxBarFillDirection.VERTICAL_INSIDE_OUT,
			VERTICAL_OUTSIDE_IN: FlxBarFillDirection.VERTICAL_OUTSIDE_IN
		};
	}

	public static function textBorderStyleConstants():Dynamic {
		return {
			NONE: FlxTextBorderStyle.NONE,
			SHADOW: FlxTextBorderStyle.SHADOW,
			SHADOW_XY: FlxTextBorderStyle.SHADOW_XY,
			OUTLINE: FlxTextBorderStyle.OUTLINE,
			OUTLINE_FAST: FlxTextBorderStyle.OUTLINE_FAST
		};
	}
}
