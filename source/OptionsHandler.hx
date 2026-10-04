package;
import lime.utils.Assets;
#if sys
import sys.io.File;
#end
import flixel.FlxG;
import flixel.FlxSprite;
import openfl.display.StageQuality;
enum abstract AccuracyMode(Int) from Int to Int {
    var None = -1;
    var Simple;
    var Complex;
    var Binary;
}
/**
 * Avaliable options. 
 * 
 */
typedef TOptions = {
    var skipVictoryScreen:Bool;
    var skipModifierMenu:Bool;
    var alwaysDoCutscenes:Bool;
    var useCustomInput:Bool;
    var singYourHeartOut:Bool;
    var modernSustains:Bool;
    // var DJFKKeys:Bool;
    var allowEditOptions:Bool;
    var downscroll:Bool;
    var midscroll:Bool;
    var useSaveDataMenu:Bool;
    var preferredSave:Int;
    var showSongPos:Bool;
    var showTimings:Bool;
    var showNoteSplashes:Bool;
    var style:Bool;
    var stressTankmen:Bool;
    // var ignoreShittyTiming:Bool;
    var ignoreUnlocks:Bool;
    var judge:Int;
    var preferJudgement:Int;
    var newJudgementPos:Bool;
    var emuOsuLifts:Bool;
    var showComboBreaks:Bool;
    var useKadeHealth:Bool;
    var useCharColor:Bool;
    var useMissStun:Bool;
    var offset:Float;
    var fastSceneTransitions:Bool;
    var accuracyMode:AccuracyMode;
    var danceMode:Bool;
    var dontMuteMiss:Bool;
    //var moddingOptions:Bool;
    //var funnyOptions:Bool;
    var allowStoryMode:Bool;
    var allowFreeplay:Bool;
    var allowDonate:Bool;
    var hitSounds:Bool;
    var titleToggle:Bool;
    var fpsCap:Int;
    var unlimitedFPS:Bool;
    var showFPS:Bool;
    var showMemory:Bool;
    var ignoreVile:Bool;
    var scrollSpeed:Float;
    var dynamicScrollSpeed:Float;
    var camNotes:Bool;
    var highwayDim:Float;
    // Donor engines expose these visual/accessibility gates through their
    // Preferences/Save objects. Keep the native defaults enabled so older
    // options files retain their historical behaviour.
    var zoomCamera:Bool;
    var flashingLights:Bool;
    var autoPause:Bool;
    // Codename exposes these user preferences through its Options API. Keep
    // them in the host's normal options save so imported scripts and the
    // shared options menu observe one persistent value.
    var naughtyness:Bool;
    var volumeMusic:Float;
    var volumeSFX:Float;
    var normalizeSongAudio:Bool;
    var week6PixelPerfect:Bool;
    var quality:Int;
    var antialiasing:Bool;
    var gameplayShaders:Bool;
    var lowMemoryMode:Bool;
    var gpuOnlyBitmaps:Bool;
    var vignetteEffects:Bool;
    var lyricsEnabled:Bool;
}
/**
 * All options that can display on the savedatamenu. Used with mask
 * for some shenanangins : ))
 */
typedef FullOptions = {
    > TOptions,
    var newChar:Bool;
    var newstage:Bool;
    var newsong:Bool;
    var newweek:Bool;
    var sort:Bool;
    var soundtest:Bool;
    var controls:Bool;
    var credits:Bool;
}
/**
 * OptionsHandler Handles options : )
 */
class OptionsHandler {
    /**
     *  The options. On desktop it's read from file then cached. 
     */
    public static var options(get, set):TOptions;
    // Preformance!
    // We only read the file once...
    // As all calls to options should go through options handler
    // we can just cache the last options read until the file gets edited. 
    static var lastOptions:TOptions;
    static var needToRefresh:Bool = true;
    static var autoPauseInitialized:Bool = false;
    public static inline var DYNAMIC_SCROLL_SPEED_DEFAULT:Float = 0;
    public static inline var DYNAMIC_SCROLL_SPEED_MIN:Float = 0;
    public static inline var DYNAMIC_SCROLL_SPEED_MAX:Float = 10;
    public static inline var DYNAMIC_SCROLL_SPEED_STEP:Float = 0.5;
    // Flixel, Lime, and the save format all carry frame rates as signed Ints.
    // The menu accepts the full positive range of that native value.
    public static inline var MAX_FPS_CAP:Int = 2147483647;

    public static function sanitizeFpsCap(raw:Dynamic):Int {
        if (raw == null || !(Std.isOfType(raw, Float) || Std.isOfType(raw, Int)))
            return 60;
        var value:Float = raw;
        if (!Math.isFinite(value) || value <= 0)
            return 60;
        // Clamp before rounding so a huge saved Float cannot overflow Int.
        value = Math.min(MAX_FPS_CAP, value);
        var cap = Std.int(Math.floor(value + 0.5));
        return cap < 1 ? 60 : cap;
    }

    public static function sanitizeOffset(raw:Dynamic):Float {
        if (raw == null || !(Std.isOfType(raw, Float) || Std.isOfType(raw, Int)))
            return 0;
        var value:Float = raw;
        if (!Math.isFinite(value))
            return 0;
        // Above this size Float cannot represent tenths; returning the original
        // value avoids overflowing while scaling it for rounding.
        if (Math.abs(value) >= 1e307)
            return value;
        return Math.floor(value * 10 + 0.5) / 10;
    }

    public static function sanitizeDynamicScrollSpeed(raw:Dynamic):Float {
        if (raw == null || !(Std.isOfType(raw, Float) || Std.isOfType(raw, Int)))
            return DYNAMIC_SCROLL_SPEED_DEFAULT;
        var value:Float = raw;
        if (!Math.isFinite(value))
            return DYNAMIC_SCROLL_SPEED_DEFAULT;
        // Bound before rounding so huge saved values cannot overflow Math.round.
        value = Math.max(DYNAMIC_SCROLL_SPEED_MIN, Math.min(DYNAMIC_SCROLL_SPEED_MAX, value));
        return Math.round(value / DYNAMIC_SCROLL_SPEED_STEP) * DYNAMIC_SCROLL_SPEED_STEP;
    }

    static function sanitizeBool(raw:Dynamic, fallback:Bool):Bool
        return Std.isOfType(raw, Bool) ? cast raw : fallback;

    static function sanitizeVolume(raw:Dynamic):Float {
        if (raw == null || !(Std.isOfType(raw, Float) || Std.isOfType(raw, Int)))
            return 1.0;
        var value:Float = raw;
        if (!Math.isFinite(value)) return 1.0;
        return Math.max(0.0, Math.min(1.0, value));
    }

    static function sanitizeOptions(opt:TOptions):TOptions {
        // Resolve migration before sanitizing the legacy custom-quality fields.
        // Older saves have no `quality` key, so a complete non-HIGH AA/shader
        // triple must stay unlocked and retain its exact values.
        var quality = CodenameOptionsQualityCompat.infer(opt);
        opt.fpsCap = sanitizeFpsCap(Reflect.field(opt, "fpsCap"));
        opt.offset = sanitizeOffset(Reflect.field(opt, "offset"));
        opt.unlimitedFPS = sanitizeBool(Reflect.field(opt, "unlimitedFPS"), false);
        opt.fastSceneTransitions = sanitizeBool(Reflect.field(opt, "fastSceneTransitions"), false);
        opt.dynamicScrollSpeed = sanitizeDynamicScrollSpeed(Reflect.field(opt, "dynamicScrollSpeed"));
        opt.antialiasing = sanitizeBool(Reflect.field(opt, "antialiasing"), true);
        opt.gameplayShaders = sanitizeBool(Reflect.field(opt, "gameplayShaders"), true);
        opt.lowMemoryMode = sanitizeBool(Reflect.field(opt, "lowMemoryMode"), false);
        #if (mac || web)
        opt.gpuOnlyBitmaps = sanitizeBool(Reflect.field(opt, "gpuOnlyBitmaps"), false);
        #else
        opt.gpuOnlyBitmaps = sanitizeBool(Reflect.field(opt, "gpuOnlyBitmaps"), true);
        #end
        opt.naughtyness = sanitizeBool(Reflect.field(opt, "naughtyness"), true);
        opt.volumeMusic = sanitizeVolume(Reflect.field(opt, "volumeMusic"));
        opt.volumeSFX = sanitizeVolume(Reflect.field(opt, "volumeSFX"));
        opt.normalizeSongAudio = sanitizeBool(Reflect.field(opt, "normalizeSongAudio"), false);
        opt.useCharColor = sanitizeBool(Reflect.field(opt, "useCharColor"), true);
        opt.week6PixelPerfect = sanitizeBool(Reflect.field(opt, "week6PixelPerfect"), true);
        opt.quality = quality;
        CodenameOptionsQualityCompat.apply(opt);
        if (Reflect.field(opt, "zoomCamera") == null)
            opt.zoomCamera = true;
        if (Reflect.field(opt, "flashingLights") == null)
            opt.flashingLights = true;
        if (Reflect.field(opt, "autoPause") == null)
            opt.autoPause = true;
        if (Reflect.field(opt, "vignetteEffects") == null)
            opt.vignetteEffects = true;
        if (Reflect.field(opt, "lyricsEnabled") == null)
            opt.lyricsEnabled = true;
        return opt;
    }

    public static function applyDisplayOptions(opt:TOptions):Void {
        if (opt == null) return;
        FlxSprite.defaultAntialiasing = opt.antialiasing;
        if (FlxG.game != null && FlxG.game.stage != null)
            FlxG.game.stage.quality = opt.antialiasing ? StageQuality.BEST : StageQuality.LOW;
    }

    public static function applyAudioOptions(opt:TOptions):Void {
        if (opt == null || FlxG.sound == null) return;
        if (FlxG.sound.defaultMusicGroup != null)
            FlxG.sound.defaultMusicGroup.volume = opt.volumeMusic;
        if (FlxG.sound.defaultSoundGroup != null)
            FlxG.sound.defaultSoundGroup.volume = opt.volumeSFX;
    }


    static function get_options() {
        #if sys
        // update the file
        if (needToRefresh) {
            lastOptions = CoolUtil.parseJson(FNFAssets.getJson('assets/data/options'));
            sanitizeOptions(lastOptions);
            needToRefresh = false;
        }
		applyDisplayOptions(lastOptions);
		applyAudioOptions(lastOptions);
		if (!autoPauseInitialized) {
			FlxG.autoPause = lastOptions.autoPause;
			autoPauseInitialized = true;
		}
		// options.json files written before highwayDim existed must still
		// yield a Float (PlayState reads it every frame)
		if (Reflect.field(lastOptions, "highwayDim") == null)
			lastOptions.highwayDim = 0;
        // these are the canon options
        // if your options aren't these it isn't canon
        if (lastOptions.danceMode) {
            lastOptions.showMemory = false;
            lastOptions.showFPS = false;
            lastOptions.skipVictoryScreen = false;
			lastOptions.skipModifierMenu = true; // i'm going to use a special thing to do it
			lastOptions.alwaysDoCutscenes = false;
			lastOptions.useCustomInput = true;
            lastOptions.singYourHeartOut = false;
            lastOptions.modernSustains = true;
            lastOptions.allowEditOptions = false;
            lastOptions.useSaveDataMenu = false;
            // lastOptions.downscroll // we are going to add this to a special new menu
            lastOptions.preferredSave = 0;
            lastOptions.style = true;
            lastOptions.stressTankmen = false; // sorry guys no funny songs  : (
            lastOptions.ignoreUnlocks = true; // If we are in an arcade a person won't have enough time to unlock everything
            // lastOptions.preferJudgement // going to the new menu
            // lastOptions.judge // new menu
			lastOptions.newJudgementPos = true;
			lastOptions.emuOsuLifts = false;
            // lastOptions.skipDebugScreen // i'm removing debug entirely in dance mode
            // lastOptions.showComboBreaks // i'm going to add this to the special new menu
            lastOptions.useKadeHealth = false;
            lastOptions.useCharColor = true;
            // lastOptions.offset // i'll remove it from options, but json can still be edited. perfect those things!
            lastOptions.useMissStun = false;
			lastOptions.accuracyMode = Simple;
            lastOptions.dontMuteMiss = true;
            //lastOptions.moddingOptions = true;
            //lastOptions.funnyOptions = true;
            lastOptions.allowStoryMode = true;
            lastOptions.allowFreeplay = true;
            lastOptions.allowDonate = false;
            lastOptions.hitSounds = false;
            lastOptions.titleToggle = true;
            lastOptions.fpsCap = 60;
            lastOptions.unlimitedFPS = false;
            lastOptions.scrollSpeed = 1;
            lastOptions.dynamicScrollSpeed = 0;
            lastOptions.camNotes = false;
            lastOptions.showTimings = true;
            lastOptions.showNoteSplashes = true;
            lastOptions.zoomCamera = true;
            lastOptions.flashingLights = true;
            lastOptions.vignetteEffects = true;
            lastOptions.lyricsEnabled = true;
        }
		return lastOptions;
        #else
        if (!Reflect.hasField(FlxG.save.data, "options"))
			FlxG.save.data.options = CoolUtil.parseJson(FNFAssets.getJson('assets/data/options'));
        // Older web saves stored JSON strings instead of option objects.
        if (Std.isOfType(FlxG.save.data.options, String))
            FlxG.save.data.options = CoolUtil.parseJson(FlxG.save.data.options);
        var options = sanitizeOptions(FlxG.save.data.options);
        applyDisplayOptions(options);
		if (!autoPauseInitialized) {
			FlxG.autoPause = options.autoPause;
			autoPauseInitialized = true;
		}
		return options;
        #end
    }
    static function set_options(opt:TOptions) {
        sanitizeOptions(opt);
        applyDisplayOptions(opt);
		applyAudioOptions(opt);
		FramerateOptionsCompat.apply(opt);
        #if sys
        needToRefresh = true;
        File.saveContent('assets/data/options.json', CoolUtil.stringifyJson(opt));
        #else
        FlxG.save.data.options = opt;
        #end
        return opt;
    }
}
