package;

import DynamicSprite.DynamicAtlasFrames;
import CodenameNoteMetadata.CodenameNoteOrigin;
import Judgement.TUI;
import openfl.errors.Error;
import flixel.util.typeLimit.OneOfTwo;
import flixel.FlxSprite;
import flixel.FlxCamera;
import flixel.graphics.frames.FlxAtlasFrames;
import flixel.graphics.frames.FlxFrame;
import flixel.graphics.frames.FlxFrame.FlxFrameAngle;
import flixel.math.FlxAngle;
import flixel.math.FlxMatrix;
import flixel.math.FlxPoint;
import flixel.math.FlxRect;
import flixel.math.FlxMath;
import flixel.util.FlxColor;
import lime.system.System;
import flash.display.BitmapData;
#if sys
import sys.io.File;
import sys.FileSystem;
import haxe.io.Path;
import openfl.utils.ByteArray;
import lime.media.AudioBuffer;
import flash.media.Sound;
#end
using StringTools;
enum abstract Direction(Int) from Int to Int {
	var left;
	var down;
	var up;
	var right;

}
/**
 * What NoteiNfo jsons are like. 
 */
typedef NoteInfo = {
	/**
	 * The name of the note that appears in charting state
	 */
	var noteName:String;
	/**
	 * The animation names of the notes. 1-4
	 * left, down, up, right
	 */
	var animNames:Array<String>;
	/**
	 * Pixel animation thingies. same order as names.
	 */
	var animInt:Array<Int>;
	/**
	 * Amount to heal
	 */
	var ?healAmount:Null<Float>;
	/**
	 * Amount to damange. Is added so should be negative to hurt people!
	 */
	var ?damageAmount:Null<Float>;
	/**
	 * Whether it should be sung. 
	 */
	var ?shouldSing:Null<Bool>;
	/** Whether this custom note emits a character crossfade afterimage. */
	var ?crossFade:Null<Bool>;
	/** Let the computer hit, sing, and strum this note even when players should avoid it. */
	var ?aiShouldHit:Null<Bool>;
	/** Explicitly skip this note for player-side autoplay. */
	var ?avoidAutoHit:Null<Bool>;
	/**
	 * Overwritten by healAmount. How much the healing should be multiplied.
	 */
	var ?healMultiplier:Null<Float>;
	/**
	 * Overwritten by damage amount. How much damage should be multiplied by.
	 */
	var ?damageMultiplier:Null<Float>;
	/**
	 * Whether to heal the same amount or hurt the same amount.
	 */
	var ?consistentHealth:Null<Bool>;
	/**
	 * When to stop healing and start hurting. can be
	 * sick
	 * good
	 * bad
	 * shit
	 * wayoff
	 * miss
	 */
	var ?healCutoff:Null<String>;
	/**
	 * How easy it is to hit note. Higher numbers are easier. 0 is literally impossible.
	 */
	var ?timingMultiplier:Null<Float>;
	/**
	 * Whether to ignore health modifiers and use straight numbers. 
	 */
	var ?ignoreHealthMods:Null<Bool>;
	/**
	 * Whether missing the note should add to the combo break counter
	 */
	var ?dontCountNote:Null<Bool>;
	/**
	 * Whether or not you should strum it, for mine/nuke type notes, lowers their priority
	 */
	var ?dontStrum:Null<Bool>;
	/**
	 * Info about how the opponent sings the note. The opponent _always_ sings this note even if it isn't hit.
	 */
	var ?singInfo:Null<SingInfo>;
	/**
	 * An array of string that can be checked for.
	 */
	var ?classes:Null<Array<String>>;
	/**
	 * A unique string that can be checked for. 
	 */
	var ?id:Null<String>;
	/**
	 * The function for when a note is hit
	 */
	var ?noteHit:Null<String>;
		/**
	 * The function for when a note is missed
	 */
	var ?noteMiss:Null<String>;
	/**
	 * The function for when a note is at the strumline
	 * VERY BROKEN DONT USE PLEASE
	 */
	var ?noteStrum:Null<String>;
	/**
	 * Custom note path for if your note isn't in the selected note path
	 */
	var ?customNotePath:Null<String>;
	/**
	 * Same as customNotePath but for the sustain parts
	 * Leave null (or just not include it) to use standard sustains
	 */
	var ?customSustainPath:Null<String>;
	/** Per-kind V-Slice note-style rendering metadata. */
	var ?customNoteIsPixel:Null<Bool>;
	var ?customNoteScale:Null<Float>;
	var ?customNoteOffsetX:Null<Float>;
	var ?customNoteOffsetY:Null<Float>;
	/** Source-engine note type retained for runtime bridges (for example,
		Psych's GF Sing note). */
	var ?sourceNoteType:Null<String>;
	/** Authored HXC/V-Slice kind retained separately from the native note id. */
	var ?sourceKind:Null<String>;
	var ?sourceEngine:Null<String>;
}
/**
 * Used to make opponent sing.
 */
typedef SingInfo = {
	/**
	 * Direction of singing. 0-3 left, down, up, right
	 */
	var direction:Int;
	/**
	 * Alt note. 0 is no alt. 
	 */
	var ?alt:Null<Int>;
	/**
	 * Whether to miss or not. 
	 */
	var ?miss:Null<Bool>;
}
// sinful dynamic sprite
@:build(NightmareVisionSpriteMacro.build())
class Note extends DynamicSprite {
	/** Psych 0.7.3 logical texture. Empty means the current chart's arrow skin. */
	public var texture(get, set):String;
	var psychTexture:String = '';
	var psychSkinOwner:String = null;
	var psychChartSkin:String = null;
	var psychPixelSkin:Bool = false;
	var psychSkinPostfix:String = '';
	var psychRGBDisabled:Bool = false;
	@:allow(PsychSkinRuntime) public var psychSkinUsesNativeDefaultFallback(default, null):Bool = false;
	/** Psych pixel ends retain their unscaled source height across reloads. */
	@:keep public static inline var SUSTAIN_SIZE:Int = 44;
	@:keep public var originalHeight:Float = 6;
	@:allow(PsychSkinRuntime) var psychLastNoteOffX:Float = 0;
	@:allow(PsychSkinRuntime) var psychSustainStartWidth:Float = 0;
	@:allow(PsychSkinRuntime) var psychSustainLayoutInitialized:Bool = false;
	var psychRGBShader:PsychRGBShaderReference = null;
	@:keep public var rgbShader(get, never):PsychRGBShaderReference;
	@:keep function get_rgbShader():PsychRGBShaderReference return psychRGBShader;
	var psychSkinDiagnosticNoteIndex:Int = 0;
	var psychSkinDiagnosticsEnabled:Bool = false;
	function get_texture():String return psychTexture;
	function set_texture(value:String):String {
		if (value == null) value = '';
		if (psychSkinOwner == null) return psychTexture = value;
		if (value != psychTexture && PsychSkinRuntime.reloadNote(this, value, psychSkinOwner,
			psychChartSkin, psychPixelSkin, psychSkinPostfix, psychSkinDiagnosticsEnabled)) {
			psychTexture = value;
			refreshPsychNoteType();
		}
		return psychTexture;
	}

	public function configurePsychSkin(ownerRoot:String, arrowSkin:String, disableNoteRGB:Bool,
		pixel:Bool, ?postfix:String = '', ?diagnosticNoteIndex:Int = 0,
		?diagnosticEnabled:Bool = false):Bool {
		psychSkinDiagnosticsEnabled = diagnosticEnabled;
		if (diagnosticEnabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('configure:reset');
		psychSkinOwner = ownerRoot;
		psychChartSkin = arrowSkin;
		psychPixelSkin = pixel;
		psychSkinPostfix = postfix;
		psychTexture = '';
		psychRGBDisabled = disableNoteRGB;
		psychSkinDiagnosticNoteIndex = diagnosticNoteIndex;
		if (diagnosticNoteIndex > 0)
			RuntimeSmokeHarness.markStep('psych-note-skin:reload-begin count=' + diagnosticNoteIndex);
		if (diagnosticEnabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('configure:reload');
		if (!PsychSkinRuntime.reloadNote(this, '', ownerRoot, arrowSkin, pixel, postfix, diagnosticEnabled)) {
			if (diagnosticNoteIndex > 0)
				RuntimeSmokeHarness.markStep('psych-note-skin:reload-missing count=' + diagnosticNoteIndex);
			psychSkinDiagnosticNoteIndex = 0;
			return false;
		}
		if (diagnosticNoteIndex > 0)
			RuntimeSmokeHarness.markStep('psych-note-skin:reload-complete count=' + diagnosticNoteIndex);
		if (diagnosticEnabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('configure:refresh');
		if (diagnosticNoteIndex > 0)
			RuntimeSmokeHarness.markStep('psych-note-skin:rgb-refresh-begin count=' + diagnosticNoteIndex);
		refreshPsychNoteType();
		if (diagnosticNoteIndex > 0)
			RuntimeSmokeHarness.markStep('psych-note-skin:rgb-refresh-complete count=' + diagnosticNoteIndex);
		psychSkinDiagnosticNoteIndex = 0;
		if (diagnosticEnabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('configure:complete');
		return true;
	}

	/** Call after an authored note type changes; texture reload itself does not alter it. */
	public function refreshPsychNoteType():Void {
		if (psychSkinOwner == null) return;
		// Psych shares lane palettes, then gives each note a copy-on-write view.
		// This also bounds generated shader construction when large charts load.
		if (psychRGBShader == null) {
			if (psychSkinDiagnosticsEnabled)
				RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('rgb:shader-create');
			if (psychSkinDiagnosticNoteIndex > 0)
				RuntimeSmokeHarness.markStep('psych-note-skin:rgb-shader-create-begin count=' + psychSkinDiagnosticNoteIndex);
			var palette = PsychRGBPalette.defaultFor(noteData, psychPixelSkin, sourceKind == 'Hurt Note');
			psychRGBShader = new PsychRGBShaderReference(this, palette);
			if (psychRGBDisabled)
				psychRGBShader.enabled = false;
			if (psychSkinDiagnosticNoteIndex > 0)
				RuntimeSmokeHarness.markStep('psych-note-skin:rgb-shader-create-complete count=' + psychSkinDiagnosticNoteIndex);
		} else {
			if (psychSkinDiagnosticsEnabled)
				RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('rgb:palette');
			var palette = PsychRGBPalette.defaultFor(noteData, psychPixelSkin, sourceKind == 'Hurt Note');
			psychRGBShader.usePalette(palette);
		}
		if (psychSkinDiagnosticsEnabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('rgb:palette');
		if (psychSkinDiagnosticNoteIndex > 0)
			RuntimeSmokeHarness.markStep('psych-note-skin:rgb-palette-begin count=' + psychSkinDiagnosticNoteIndex);
		if (psychSkinDiagnosticNoteIndex > 0)
			RuntimeSmokeHarness.markStep('psych-note-skin:rgb-palette-complete count=' + psychSkinDiagnosticNoteIndex);
		if (psychSkinDiagnosticsEnabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('rgb:bind');
		var hasExplicitRGB = psychRGBShader != null
			&& (psychRGBShader.hasCustomPalette || psychRGBShader.explicitlyEnabled);
		shader = (!psychSkinUsesNativeDefaultFallback || hasExplicitRGB) && psychRGBShader.enabled
			? psychRGBShader.parent.shader : null;
		if (psychSkinDiagnosticsEnabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase('rgb:complete');
	}

	/** A Psych atlas swap rebuilds the sprite's frame centering from its new canvas. */
	public function resetPsychVisualOffset():Void {
		offsetState = new NoteOffsetState();
	}
	public var strumTime:Float = 0;
	public static var getFrames:Bool = true;
	static var framesKey:Array<String> = [];
	public static var gotFrames:Array<FlxAtlasFrames> = [];
	public static var getSpecialFrames:Bool = true;
	static var specialFramesKey:Array<String> = [];
	public static var gotSpecialFrames:Array<FlxAtlasFrames> = [];
	@:keep public var mustPress:Bool = false;
	public var noteData:Int = 0;
	public var trueNoteData:Int = 0;
	/** Source chart field identity, independent from the binary `mustPress`
	 * contract and from note-type bits stored in trueNoteData. */
	public var sourcePlayfieldIndex:Int = -1;
	/** Live source membership; detached notes have no owning PlayField. */
	@:keep public var playField(default, set):Dynamic = null;
	function set_playField(value:Dynamic):Dynamic {
		if (playField != value) {
			var previousNotes:Array<Dynamic> = playField == null ? null : Reflect.getProperty(playField, 'notes');
			if (previousNotes != null && previousNotes.indexOf(this) >= 0) playField.removeNote(this);
			var nextNotes:Array<Dynamic> = value == null ? null : Reflect.getProperty(value, 'notes');
			if (nextNotes != null && nextNotes.indexOf(this) < 0) value.addNote(this);
		}
		return playField = value;
	}
	/** Nightmare Vision calls the owning playfield index `lane`; noteData stays
	 * the direction inside that field. */
	@:keep public var lane(get, set):Int;
	function get_lane():Int return sourcePlayfieldIndex;
	function set_lane(value:Int):Int return sourcePlayfieldIndex = value;
	/** Direction within sourcePlayfieldIndex before destination note encoding. */
	public var sourceDirection:Int = -1;
	/** Optional source-field actor owner, independent of native mustPress. NMV has
	 * several BF-owned fields, but only one native player/opponent boolean. */
	public var sourcePlayfieldPlayerControlled:Null<Bool> = null;
	/** Source fields can autoplay independently of the user's botplay setting. */
	public var sourcePlayfieldAutoPlay:Bool = false;
	public var sourceTimingMode:Int = 0;
	@:keep public var visualTime:Float = 0;
	@:keep public var mAngle:Float = 0;
	@:keep public var hitsoundDisabled:Bool = false;
	public var nightmareVisionLegacyGeometry:Bool = false;
	public var nightmareVisionSustainInitialized:Bool = false;
	public var nightmareVisionSustainInitialWidth:Float = 0;
	@:keep public var originalHeightForCalcs:Float = 6;
	@:keep public var lastNoteOffsetXForPixelAutoAdjusting:Float = 0;
	/** Source chart quant classification is independent of a field's receptor flag. */
	@:keep public var quant:Int = 4;
	@:keep public var isQuant:Bool = false;
	@:keep public var canQuant:Bool = true;
	public var nightmareVisionQuantInitialized:Bool = false;
	/** Nightmare Vision's independent note fade, retained across renderer updates. */
	@:keep public var alphaMod:Float = 1;
	/** Psych notes follow each receptor axis/rotation unless a script opts out. */
	@:keep public var copyX:Bool = true;
	@:keep public var copyY:Bool = true;
	@:keep public var copyAngle:Bool = true;
	@:keep public var typeOffsetX:Float = 0;
	@:keep public var typeOffsetY:Float = 0;
	@:keep public var offsetX:Float = 0;
	@:keep public var offsetY:Float = 0;
	@:keep public var offsetAngle:Float = 0;
	/** Psych note speed multiplier; sustain geometry resizes with the value. */
	@:keep public var multSpeed(default, set):Float = 1.0;
	function set_multSpeed(value:Float):Float {
		resizeByRatio(value / multSpeed);
		multSpeed = value;
		return value;
	}
	@:keep public function resizeByRatio(ratio:Float):Void {
		if (isSustainNote && animation != null && animation.curAnim != null
			&& !animation.curAnim.name.endsWith('end')) {
			if (nightmareVisionLegacyGeometry && noteData == 4) return;
			scale.y *= nightmareVisionLegacyGeometry && noteData > 4 ? ratio / 1.6 : ratio;
			if (nightmareVisionLegacyGeometry) baseScaleY = scale.y;
			updateHitbox();
		}
	}
	/** Extra source sustain alignment before clipping. */
	@:keep public var correctionOffset:Float = 0;
	@:keep public var distance:Float = 0;
	/** Psych notes copy receptor alpha each frame unless a script opts out. */
	@:keep public var copyAlpha:Bool = true;
	/** Psych receptor alpha multiplier; sustains use 0.6. */
	@:keep public var multAlpha:Float = 1.0;
	public var hitbox:Float = Conductor.safeZoneOffset;
	public var earlyHitMult:Float = 1;
	public var lateHitMult:Float = 1;
	public var noteDiff(get, never):Float;
	function get_noteDiff():Float return strumTime - Conductor.songPosition;
	var cachedCanBeHit:Bool = false;
	public var canBeHit(get, set):Bool;
	function get_canBeHit():Bool {
		if (sourceTimingMode != 0 && missed) return false;
		if (sourceTimingMode == 2 && nightmareVisionTailState != null && nightmareVisionTailState.missed) return false;
		return sourceTimingMode == 2
			? SourceNoteTiming.nightmareCanBeHit(strumTime, Conductor.songPosition, hitbox, earlyHitMult) : cachedCanBeHit;
	}
	function set_canBeHit(value:Bool):Bool return cachedCanBeHit = value;
	public function isLate():Bool return SourceNoteTiming.isLate(strumTime, Conductor.songPosition, Conductor.safeZoneOffset, wasGoodHit);
	/**
		Apply Psych 1.0.4 receptor-relative position in its source presentation
		route. The songSpeed argument is already divided by
		playbackRate at the donor call site. Independent copy flags let scripts
		keep control of an axis without changing other note routes.
	*/
	@:keep public function applyPsychReceptorFollow(receptorX:Float, receptorY:Float,
		direction:Float, receptorAngle:Float, downScroll:Bool, songSpeed:Float,
		pixelStage:Bool, pixelZoom:Float):Void {
		if (sourceTimingMode != 1 || codenameInputLine != null) return;
		distance = 0.45 * (Conductor.songPosition - strumTime) * songSpeed * multSpeed;
		if (!downScroll) distance *= -1;
		var angleDir = direction * Math.PI / 180;
		if (copyAngle) angle = direction - 90 + receptorAngle + offsetAngle;
		if (copyX) x = receptorX + offsetX + Math.cos(angleDir) * distance;
		if (copyY) {
			y = receptorY + offsetY + correctionOffset + Math.sin(angleDir) * distance;
			if (downScroll && isSustainNote) {
				if (pixelStage) y -= pixelZoom * 9.5;
				y -= (frameHeight * scale.y) - (Note.swagWidth / 2);
			}
		}
	}

	/** Finish donor sustain construction after the selected source skin is installed. */
	@:keep public function finalizePsychSustainSegment(previous:Note, head:Note,
		localStep:Float, baseStep:Float, songSpeed:Float, playbackRate:Float,
		pixelStage:Bool, downScroll:Bool):Void {
		if (sourceTimingMode != 1 || codenameInputLine != null || !isSustainNote
			|| psychSustainLayoutInitialized || head == null) return;
		psychSustainLayoutInitialized = true;
		correctionOffset = !pixelStage && downScroll ? 0 : head.height / 2;
		updateHitbox();
		var startWidth = psychSustainStartWidth > 0 ? psychSustainStartWidth : head.width;
		offsetX += (startWidth - width) / 2;
		if (pixelStage) offsetX += 30;
		if (previous != null && previous.isSustainNote) {
			previous.animation.play('hold');
			previous.scale.y *= PsychSustainLayout.bodyStretchRatio(baseStep, songSpeed, pixelStage, height);
			previous.updateHitbox();
			previous.scale.y *= PsychSustainLayout.generationStretchRatio(localStep, baseStep,
				playbackRate, pixelStage, previous.frameHeight);
			previous.updateHitbox();
		}
		if (pixelStage) {
			scale.y *= PlayState.daPixelZoom;
			updateHitbox();
		}
	}

	/** Apply Psych's sustain clipping after receptor-follow geometry. */
	@:keep public function applyPsychReceptorClip(receptorY:Float, downScroll:Bool):Void {
		if (sourceTimingMode != 1 || codenameInputLine != null || !isSustainNote) return;
		if (noSustainClip) {
			clipRect = null;
			return;
		}
		if ((mustPress || !ignoreNote) && (wasGoodHit
			|| (prevNote != null && prevNote.wasGoodHit && !canBeHit))) {
			var center:Float = receptorY + offsetY + Note.swagWidth / 2;
			var swagRect:FlxRect = clipRect;
			if (swagRect == null) swagRect = new FlxRect(0, 0, frameWidth, frameHeight);
			if (downScroll) {
				if (y - offset.y * scale.y + height >= center) {
					swagRect.width = frameWidth;
					swagRect.height = (center - y) / scale.y;
					swagRect.y = frameHeight - swagRect.height;
				}
			} else if (y + offset.y * scale.y <= center) {
				swagRect.y = (center - y) / scale.y;
				swagRect.width = width / scale.x;
				swagRect.height = (height / scale.y) - swagRect.y;
			}
			clipRect = swagRect;
		}
	}

	/** Apply Psych's receptor alpha without changing the independent base/NV/Codename paths. */
	public function applyPsychReceptorAlpha(receptorAlpha:Float):Void {
		if (sourceTimingMode != 1 || codenameInputLine != null || !copyAlpha) return;
		alpha = receptorAlpha * multAlpha;
	}
	public var tooLate:Bool = false;
	public var wasGoodHit:Bool = false;
	/** NMV source marker, separate from native retirement and liveness. */
	@:keep public var garbage:Bool = false;
	public var prevNote:Note;
	@:keep public var nextNote:Note;
	@:keep public var row:Int = 0;
	/** Source note/hold views keep the authored chain available to scripts. */
	@:keep public var parent:Note = null;
	@:keep public var tail:Array<Note> = [];
	@:keep public var missed:Bool = false;
	/** The head owns a sustain's lane anchor even after it is judged. */
	var sustainHead:Note = null;
	var sustainHeadCenterX:Null<Float> = null;
	public var duoMode:Bool = false;
	public var oppMode:Bool = false;
	public var soloMode:Bool = false;
	public var sustainLength:Float = 0;
	public var isSustainNote:Bool = false;
	/** Optional Codename direction override for this note's travel path. */
	@:keep public var noteAngle:Null<Float> = null;
	public var modifiedByLua:Bool = false;
	public var funnyMode:Bool = false;
	public var noteScore:Float = 1;
	public var altNote:Bool = false;
	/** Whether this note should emit a character crossfade afterimage. */
	public var crossFade:Bool = false;
	public var altNum:Int = 0;
	public var isPixel:Bool = false;
	/** Authored NMV type behavior remains separate from Psych ignoreNote. */
	@:keep public var spawned:Bool = false;
	public var nightmareVisionTailState:{missed:Bool, notes:Array<Note>, ?active:Bool, ?splash:Dynamic};
	@:keep public var tailState(get, set):Dynamic;
	function get_tailState():Dynamic return nightmareVisionTailState;
	function set_tailState(value:Dynamic):Dynamic return nightmareVisionTailState = value;
	@:keep public var sustainSplash:Dynamic = null;
	@:keep public var noteSplash:Dynamic = null;
	public var nightmareVisionHitDispatched:Bool = false;
	/** Psych sustains stay alive after their one successful notification. */
	@:keep public var hitByOpponent:Bool = false;
	@:keep public var doAutoSustain:Bool = false;
	public var psychHitDispatched:Bool = false;
	public var psychHitCallbackArgs:Array<Dynamic>;
	public var nightmareVisionMissDispatched:Bool = false;
	public var nightmareVisionSustainDuration:Float = 0;
	public var nightmareVisionSustainEnd:Bool = false;
	@:keep public var nightmareVisionTypeRuntime:NightmareVisionNoteTypeRuntime;
	var pendingSourceCanMiss:Bool = false;
	public var nightmareVisionRenderer:nightmarevision.modchart.NightmareVisionModchartRenderer;
	public var nightmareVisionRGB:NightmareVisionRGBGraphics;
	public var nightmareVisionLegacyColors:NightmareVisionLegacyNoteColors;
	@:keep public var baseScaleX:Float = 1;
	@:keep public var baseScaleY:Float = 1;
	@:keep public var noteSplashTexture:String = 'noteSplashes';
	@:keep public var noteSplashHue:Float = 0;
	@:keep public var noteSplashSat:Float = 0;
	@:keep public var noteSplashBrt:Float = 0;
	@:keep public var colorSwap(get, set):NightmareVisionLegacyColorSwap;
	function get_colorSwap():NightmareVisionLegacyColorSwap
		return nightmareVisionLegacyColors == null ? null : nightmareVisionLegacyColors.swap;
	function set_colorSwap(value:NightmareVisionLegacyColorSwap):NightmareVisionLegacyColorSwap {
		if (nightmareVisionLegacyColors == null) throw '[nightmare-vision-hsv] Not a historical note';
		nightmareVisionLegacyColors.swap = value;
		if (nightmareVisionRGB != null) nightmareVisionRGB.legacyHSV = value;
		return value;
	}
	@:keep public var canMiss(get, set):Bool;
	function get_canMiss():Bool return nightmareVisionTypeRuntime != null && nightmareVisionTypeRuntime.api.canMiss(this);
	function set_canMiss(value:Bool):Bool {
		if (nightmareVisionTypeRuntime == null) throw '[nightmare-vision-note] No source note-type runtime';
		return nightmareVisionTypeRuntime.api.setCanMiss(this, value);
	}
	@:keep public var rgbEnabled(get, set):Bool;
	function get_rgbEnabled():Bool return nightmareVisionTypeRuntime == null
		? nightmareVisionRGB != null && nightmareVisionRGB.enabled : nightmareVisionTypeRuntime.api.getRgbEnabled(this);
	function set_rgbEnabled(value:Bool):Bool {
		if (nightmareVisionTypeRuntime == null) throw '[nightmare-vision-note] No source note-type runtime';
		return nightmareVisionTypeRuntime.api.setRgbEnabled(this, value);
	}
	@:keep public var rgbGraphics(get, never):NightmareVisionRGBGraphics;
	function get_rgbGraphics():NightmareVisionRGBGraphics return nightmareVisionRGB;
	@:keep public function setCustomColor(colors:Array<Dynamic>):Void {
		if (nightmareVisionTypeRuntime == null) throw '[nightmare-vision-note] No source note-type runtime';
		nightmareVisionTypeRuntime.api.setCustomColor(this, colors);
	}
	@:keep public function loadNoteAnims():Void {
		if (!nightmareVisionLegacyGeometry) throw '[nightmare-vision-note] Historical animation API requires the historical source profile';
		NightmareVisionLegacyNoteAnimations.load(this, false, PlayState.SONG.keys);
	}
	@:keep public function loadPixelNoteAnims():Void {
		if (!nightmareVisionLegacyGeometry) throw '[nightmare-vision-note] Historical animation API requires the historical source profile';
		NightmareVisionLegacyNoteAnimations.load(this, true, PlayState.SONG.keys);
	}
	@:keep public function reloadNote(prefix:String = '', texture:String = '', suffix:String = ''):Void {
		if (nightmareVisionTypeRuntime == null) throw '[nightmare-vision-note] No source note-type runtime';
		nightmareVisionTypeRuntime.reloadNote(this, prefix, texture, suffix);
	}
	public var normalSize:Float = 0.7;
	// Historical Nightmare Vision note types use `defScale`; the current source
	// exposes the same mutable baseline as `baseScale`. Keep one point behind
	// both names so post-skin note scripts and the modchart renderer share it.
	var nightmareVisionBaseScalePoint:FlxPoint;
	@:keep public var baseScale(get, never):FlxPoint;
	@:keep public var defScale(get, set):FlxPoint;
	function get_baseScale():FlxPoint {
		if (nightmareVisionBaseScalePoint == null) {
			var currentScale = scale;
			nightmareVisionBaseScalePoint = FlxPoint.get(
				currentScale == null ? 1 : currentScale.x,
				currentScale == null ? 1 : currentScale.y);
		}
		return nightmareVisionBaseScalePoint;
	}
	function set_defScale(value:FlxPoint):FlxPoint {
		if (value == null) throw 'Nightmare Vision baseScale cannot be null';
		var point = get_baseScale();
		if (value != point) point.set(value.x, value.y);
		return point;
	}
	function get_defScale():FlxPoint {
		return get_baseScale();
	}
	public static var swagWidth:Float = 160 * 0.7;
	public static var NOTE_AMOUNT:Int = 4;
	public static var specialNoteJson:Null<Array<NoteInfo>>;
	public var damageAmount:Null<Float> = null;
	public var healAmount:Null<Float> = null;
	/** Native notes keep null health overrides; source modes seed donor defaults. */
	public var hitHealth:Null<Float> = null;
	public var missHealth:Null<Float> = null;
	public var hitCausesMiss:Bool = false;
	public var ignoreNote:Bool = false;
	/** Psych source stages can defer player hits until an earlier action unblocks them. */
	public var blockHit:Bool = false;
	/** Psych Lua can toggle splash behavior on one live note independently of
		its note type or the global splash option. */
	public var noteSplashData:Dynamic = {disabled: false};
	@:keep public var noteSplashDisabled:Bool = false;
	// pwease freeplay state don't edit me i already have special info :grief: :grief:
	public var dontEdit:Bool = false;
	/** Psych/native notes use a string; Nightmare Vision notes may carry their live
	 * SourceRating descriptor here so scripts can inspect and edit its counters. */
	@:keep public var rating:Dynamic = "miss";
	/** Psych's ratingDisabled flag suppresses rating/accuracy bookkeeping without
	 * changing dontCountNote's separate engine-specific behavior. */
	@:keep public var ratingDisabled:Bool = false;
	var storedRatingMod:Float = 0;
	/** Historical NV/Psych store a scalar; modern NV reads its live descriptor. */
	@:keep public var ratingMod(get, set):Float;
	function get_ratingMod():Float {
		if (nightmareVisionTypeRuntime == null || nightmareVisionLegacyGeometry) return storedRatingMod;
		if (rating == null) return -1;
		var raw:Dynamic = null;
		try raw = Reflect.getProperty(rating, 'ratingMod') catch (_:Dynamic) return -1;
		if (raw == null) return -1;
		var value = Std.parseFloat(Std.string(raw));
		return !Math.isFinite(value) || value == 9 ? -1 : value;
	}
	function set_ratingMod(value:Float):Float {
		if (nightmareVisionTypeRuntime != null && !nightmareVisionLegacyGeometry)
			throw '[nightmare-vision-note] ratingMod is read-only; change rating.ratingMod instead';
		storedRatingMod = value;
		return value;
	}
	/** Restore the source note's fresh/recycled scoring defaults. Call after the
	 * Nightmare Vision runtime is attached so its rating begins as null. */
	@:keep public function resetSourceRatingState():Void {
		if (sourceTimingMode == 2) {
			garbage = false; sustainSplash = null; noteSplash = null;
			if (parent == null && nightmareVisionTailState != null) nightmareVisionTailState.splash = null;
		}
		ratingDisabled = false;
		rating = nightmareVisionLegacyGeometry ? 'unknown' : nightmareVisionTypeRuntime == null ? 'miss' : null;
		storedRatingMod = 0;
	}
	public var isLiftNote:Bool = false;
	public var mineNote:Bool = false;
	// like expurgation's notes; insta die lmao
	public var nukeNote:Bool = false;
	// tabi mod
	public var drainNote:Bool =  false;
	public var healMultiplier:Float = 1;
	public var damageMultiplier:Float = 1;
	// Whether to always do the same amount of healing for hitting and the same amount of damage for missing notes
	public var consistentHealth:Bool = false;
	// How relatively hard it is to hit the note. Lower numbers are harder, with 0 being literally impossible
	public var timingMultiplier:Float = 1;
	// whether to play the sing animation for hitting this note
	public var shouldBeSung:Bool = true;
	/** Psych can suppress hit and miss animations independently. */
	public var noAnimation:Bool = false;
	public var noMissAnimation:Bool = false;
	public var aiShouldHit:Bool = false;
	public var avoidAutoHit:Bool = false;
	/** A script canceled this computer hit; let the note pass without retrying it. */
	public var autoHitSuppressed:Bool = false;
	public var ignoreHealthMods:Bool = false;

	/** Null or partial Psych splash tables keep the native splash behavior. */
	public function isNoteSplashDisabled():Bool {
		if (noteSplashData == null)
			return false;
		return Reflect.field(noteSplashData, 'disabled') == true;
	}
	public var healCutoff:Null<String>;
	var specialNoteInfo:NoteInfo;
	public var dontCountNote = false;
	public var dontStrum = false;
	public var noteHit:Null<String> = null;
	public var noteMiss:Null<String> = null;
	public var noteStrum:Null<String> = null;
	public var oppntAnim:Null<String> = null;
	public var classes:Null<Array<String>> = [];
	public var coolId:Null<String> = null;
	/** Authored note kind used by HXC/V-Slice callback payloads. */
	public var sourceKind(default, set):Null<String> = null;
	function set_sourceKind(value:Null<String>):Null<String> {
		sourceKind = value;
		// Match the source setter's special Hurt Note priority without overwriting
		// a custom priority when a live note changes to another authored kind.
		if (NoteTypeCompat.canonical(value) == 'Hurt Note') hitPriority = 0;
		if (sourceTimingMode != 0 && NoteTypeCompat.canonical(value) == 'Hurt Note')
			applySourceHurtNoteSemantics();
		applyPsychNoteAnimationType(value);
		refreshPsychNoteType();
		return value;
	}
	@:keep public function applyPendingSourceNoteSemantics():Void {
		if (nightmareVisionTypeRuntime != null && pendingSourceCanMiss) {
			nightmareVisionTypeRuntime.api.setCanMiss(this, true);
			pendingSourceCanMiss = false;
		}
	}
	function applySourceHurtNoteSemantics():Void {
		ignoreNote = mustPress;
		lowPriority = true;
		hitCausesMiss = true;
		if (sourceTimingMode == 1) missHealth = isSustainNote ? 0.25 : 0.1;
		else if (sourceTimingMode == 2) {
			missHealth = isSustainNote ? 0.1 : 0.3;
			// Nightmare Vision's canMiss value is owned by the type-runtime sidecar.
			// Note kinds can be recovered in Note.new before that runtime is attached.
			if (nightmareVisionTypeRuntime == null) pendingSourceCanMiss = true;
			else nightmareVisionTypeRuntime.api.setCanMiss(this, true);
		}
	}
	function initializeSourceHealthDefaults():Void {
		switch (sourceTimingMode) {
			case 1:
				hitHealth = 0.02;
				missHealth = 0.1;
			case 2:
				hitHealth = 0.023;
				missHealth = 0.0475;
			default:
		}
	}
	function applyPsychNoteAnimationType(value:Null<String>):Void {
		if (value == 'No Animation') {
			noAnimation = true;
			noMissAnimation = true;
		}
	}
	public function allowsAnimation(miss:Bool = false):Bool {
		return miss ? !noMissAnimation : !noAnimation;
	}
	/** Historical NV retains the assigned type script independently of registry changes. */
	@:keep public var noteScript:Dynamic;
	@:keep public var doSlam:Bool = true;
	/** Psych Lua exposes the authored type through the mutable noteType field. */
	public var noteType(get, set):String;
	function get_noteType():String {
		return sourceKind == null ? '' : sourceKind;
	}
	function set_noteType(value:String):String {
		if (nightmareVisionLegacyColors != null && nightmareVisionTypeRuntime != null
			&& nightmareVisionTypeRuntime.legacyNoteScripts) {
			var changesType = noteData > -1 && get_noteType() != value;
			var mode = nightmareVisionLegacyColors.prepareAssignment(this, value);
			nightmareVisionTypeRuntime.assignLegacyType(this, value, mode, function() {
				// Commit after setup without reapplying another source profile's type effects.
				if (changesType) @:bypassAccessor sourceKind = value;
				nightmareVisionLegacyColors.recordAssignment(get_noteType());
			});
		} else {
			sourceKind = value;
			if (nightmareVisionLegacyColors != null && nightmareVisionTypeRuntime != null)
				nightmareVisionTypeRuntime.setupNote(this, true);
		}
		return value;
	}
	/** First generation exposes the source default type until authored setup returns. */
	public function initializeLegacyNoteType():Void {
		if (nightmareVisionLegacyColors == null || nightmareVisionLegacyColors.hasAssignment()) return;
		var authored = get_noteType();
		@:bypassAccessor sourceKind = '';
		set_noteType(authored);
	}
	/** Original authored strumline/note identity, independent of input modifiers. */
	@:keep public var codenameOrigin:CodenameNoteOrigin = null;
	/** Stable input/actor ownership for an authored source strumline. */
	@:keep public var codenameInputLine:CodenameInputLine<Character> = null;
	/** Authored horizontal shift retained while its source strumline moves.
	 * Chart notes exclude this fork's constructor lane padding. */
	@:keep public var codenameReceptorXOffset:Null<Float> = null;
	/** Chart-generation x before source callbacks, used to keep authored note
	 * motion without preserving this fork's legacy constructor lane padding. */
	public var codenameGeneratedX:Null<Float> = null;
	/** Codename's sprite-space visual nudge. Allocate only when a loaded script
	 * reads or writes it; ordinary/Psych notes never pay for a FlxPoint. */
	@:keep public var frameOffset(get, set):FlxPoint;
	var codenameFrameOffset:FlxPoint = null;
	var codenameFrameOffsetOwned:Bool = false;
	function get_frameOffset():FlxPoint {
		if (codenameFrameOffset == null) {
			codenameFrameOffset = FlxPoint.get();
			codenameFrameOffsetOwned = true;
		}
		return codenameFrameOffset;
	}
	function set_frameOffset(value:FlxPoint):FlxPoint {
		if (value == codenameFrameOffset) return value;
		// Getter-created points belong to this note's pool slot. A point assigned
		// by a script remains caller-owned, matching Codename's writable field.
		if (codenameFrameOffset != null && codenameFrameOffsetOwned)
			codenameFrameOffset.put();
		codenameFrameOffset = value;
		codenameFrameOffsetOwned = false;
		return value;
	}
	/** Source Codename splash identifier. PlayState resolves custom selections
	 * through the selected owner's data/splashes definitions. */
	@:keep public var splash:String = 'default';
	@:keep public var codenameLineConfigured:Bool = false;
	@:keep public var codenamePreparedStrumScale:Float = 1;
	@:keep public var codenameCreationScaleSet:Bool = false;
	/** The line scale applied after this note's chart/style scale. */
	@:keep public var codenameSourceStrumScale:Float = 1;
	public function applyCodenameSourceStrumScale(value:Float):Void {
		if (!Math.isFinite(value) || value <= 0) value = 1;
		if (value == codenameSourceStrumScale) return;
		var factor = value / codenameSourceStrumScale;
		scale.set(scale.x * factor, scale.y * factor);
		codenameSourceStrumScale = value;
		updateHitbox();
	}
	/** Codename scripts address the note's source line as note.strumLine. */
	@:keep public var strumLine(get, never):CodenameInputLine<Character>;
	function get_strumLine():CodenameInputLine<Character> return codenameInputLine;
	/** Codename's per-note input window scales; scripts can change these on a live note. */
	@:keep public var earlyPressWindow:Float = 1;
	@:keep public var latePressWindow:Float = 1;
	/** Source sustain hits may remain alive after their one callback. */
	@:keep public var codenameHitDispatched:Bool = false;
	/** Codename hit callbacks can keep an authored sustain visually uncut. */
	@:keep public var noSustainClip:Bool = false;
	@:keep public var noteTypeID:Int = 0;
	/** Donor note views use this to lower incoming-note priority. */
	public var lowPriority:Bool = false;
	/** Nightmare Vision's source input prioritizes taps within each playfield. */
	@:keep public var hitPriority:Int = 1;
	public var animSuffix:Null<String> = null;
	/** The Codename sing suffix before native note-skin naming rewrites animSuffix. */
	public var codenameAuthoredAnimSuffix:Null<String> = null;
	public var numSuffix:Null<Dynamic> = null;
	public var oppntSing:Null<SingInfo>;
	/** Psych/Kade GF Sing notes use the girlfriend actor without changing the
		chart row's authored string noteType. */
	public var forceGfSing:Bool = false;
	public var customNotePath:Null<String> = null;
	public var customSustainPath:Null<String> = null;
	/** Optional V-Slice hold-cover effect currently attached to this hold. */
	public var cover:NoteHoldCover = null;
	/** Imported HXC note views expose this read-only shader saturation value. */
	public var hxcHsvSaturation:Float = 0;
	var currentKey = null; // I tried pulling this from Playstate but it was being weird...
	var offsetState:NoteOffsetState;
	var offsetWritesReady:Bool = false;
	/** An ordinary V-Slice tap is centered on this fork's lane independently
	 * of receptor offsets. Null keeps native and Psych hitbox rules intact. */
	var vSliceNoteOffsetX:Null<Float> = null;
	var vSliceNoteOffsetY:Float = 0;
	// altNote can be int or bool. int just determines what alt is played
	// format: [strumTime:Float, noteDirection:Int, sustainLength:Float, altNote:Union<Bool, Int>]
	public function new(strumTime:Float, noteData:Int, ?prevNote:Note, ?sustainNote:Bool = false,
		?authoredAnimSuffix:String = null, ?authoredCodenameOrigin:CodenameNoteOrigin = null,
		?authoredMustHit:Null<Bool> = null)
	{
		super(42);
		// uh oh notedata sussy :flushed:
		if (prevNote == null)
			prevNote = this;

		this.prevNote = prevNote;
		isSustainNote = sustainNote;
		if (PlayState.instance != null) sourceTimingMode = PlayState.instance.sourceNoteTimingMode();
		initializeSourceHealthDefaults();
		if (sourceTimingMode != 0 && authoredMustHit != null) mustPress = authoredMustHit;
		if (sourceTimingMode == 1 && isSustainNote) earlyHitMult = 0;
		if (isSustainNote) {
			sustainHead = prevNote.isSustainNote ? prevNote.sustainHead : prevNote;
			if (sustainHead != null)
				sustainHeadCenterX = sustainHead.graphicCenterOffsetX();
		}
		codenameOrigin = authoredCodenameOrigin;
		codenameAuthoredAnimSuffix = authoredAnimSuffix;

		var curUiType:TUI = Reflect.field(Judgement.uiJson, PlayState.SONG.uiType);
		var noteIsPixel = curUiType.isPixel;
		setVSliceNoteOffsets(curUiType);
		/*var notePresets;
		if (FNFAssets.exists('assets/images/custom_ui/ui_packs/' + curUiType.uses + '/multiNotePresets.json'))
			notePresets = CoolUtil.parseJson(FNFAssets.getText('assets/images/custom_ui/ui_packs/' + curUiType.uses + '/multiNotePresets.json'));
		else
			notePresets = CoolUtil.parseJson(FNFAssets.getText('assets/data/defaultNotePresets.json'));
		currentKey = Reflect.field(notePresets, 'key' + NOTE_AMOUNT);*/
		currentKey = new NoteKeys(curUiType.uses);
		var noteAsset = curUiType.noteAsset == null || StringTools.trim(curUiType.noteAsset) == ''
			? (curUiType.isPixel ? 'arrows-pixels' : 'NOTE_assets') : curUiType.noteAsset;
		var holdAsset = curUiType.holdAsset == null ? '' : StringTools.trim(curUiType.holdAsset);
		var holdAssetXml = curUiType.holdAssetXml == true;
		var holdFramesPerLane = curUiType.holdFramesPerLane == null ? 1 : curUiType.holdFramesPerLane;
		if (holdFramesPerLane < 1)
			holdFramesPerLane = 1;
		
		x += 50;
		// MAKE SURE ITS DEFINITELY OFF SCREEN?
		y -= 2000;
		this.strumTime = strumTime;
		if (sourceTimingMode == 2) {
			visualTime = PlayState.instance.sourceNoteVisualTime(this.strumTime);
			nightmareVisionLegacyGeometry = PlayState.instance.sourceUsesLegacyNoteGeometry();
			if (nightmareVisionLegacyGeometry) {
				if (!isSustainNote) this.prevNote = this;
				this.prevNote.nextNote = this;
			}
		}
		if (authoredAnimSuffix != null && StringTools.trim(authoredAnimSuffix) != '')
			animSuffix = StringTools.trim(authoredAnimSuffix);

		trueNoteData = noteData;
		this.noteData = noteData % NOTE_AMOUNT;
		// overloading : )
		if (noteData >= NOTE_AMOUNT * 2 && noteData < NOTE_AMOUNT * 4) 
			mineNote = true;
		if (noteData >= NOTE_AMOUNT * 4 && noteData < NOTE_AMOUNT * 6)
			isLiftNote = true;
		// die : )
		if (noteData >= NOTE_AMOUNT * 6 && noteData < NOTE_AMOUNT * 8)
			nukeNote = true;
		if (noteData >= NOTE_AMOUNT * 8 && noteData < NOTE_AMOUNT * 10)
			drainNote = true;
		if (noteData >= NOTE_AMOUNT * 10 && specialNoteJson != null) {
			// special note...
			// get the note thingie
			var sussyNoteThing = Math.floor(noteData/ (NOTE_AMOUNT * 2));
			// there are already 4 thingies and the thing is index 0 
			sussyNoteThing -= 5;
			var thingie = specialNoteJson[sussyNoteThing];
			dontEdit = true;
			if (thingie.damageAmount != null)
				damageAmount = thingie.damageAmount;
			else if (thingie.damageMultiplier != null)
				damageMultiplier = thingie.damageMultiplier;

			if (thingie.healAmount != null)
				healAmount = thingie.healAmount;
			else if (thingie.healMultiplier != null)
				healMultiplier = thingie.healMultiplier;
			
			if (thingie.shouldSing != null)
				shouldBeSung = thingie.shouldSing;
			if (thingie.crossFade != null)
				crossFade = thingie.crossFade;
			aiShouldHit = thingie.aiShouldHit == true;
			avoidAutoHit = thingie.avoidAutoHit == true;

			if (thingie.consistentHealth != null)
				consistentHealth = thingie.consistentHealth;

			if (healAmount < 0 || healMultiplier < 0)
				dontCountNote = true;

			if (thingie.dontCountNote != null)
				dontCountNote = thingie.dontCountNote;

			if (thingie.healCutoff != null) 
				healCutoff = thingie.healCutoff;

			if (thingie.timingMultiplier != null)
				timingMultiplier = thingie.timingMultiplier;

			if (thingie.dontStrum != null)
				dontStrum = thingie.dontStrum;

			if (thingie.noteHit != null)
				noteHit = thingie.noteHit;

			if (thingie.noteMiss != null)
				noteMiss = thingie.noteMiss;

			if (thingie.noteStrum != null)
				noteStrum = thingie.noteStrum;

			if (thingie.classes != null)
				classes = thingie.classes;

			if (thingie.id != null)
				coolId = thingie.id;
			if (Reflect.field(thingie, 'sourceKind') != null)
				sourceKind = Std.string(Reflect.field(thingie, 'sourceKind'));
			else if (Reflect.field(thingie, 'sourceNoteType') != null)
				sourceKind = Std.string(Reflect.field(thingie, 'sourceNoteType'));

			if (thingie.singInfo != null) {
				oppntSing = thingie.singInfo;
				if (oppntSing.alt == null)
					oppntSing.alt = 0;
				if (oppntSing.miss == null)
					oppntSing.miss = false;
			}
			if (thingie.customNotePath != null)
				customNotePath = thingie.customNotePath;
			if (thingie.customSustainPath != null)
				customSustainPath = thingie.customSustainPath;
			if (thingie.customNoteIsPixel != null)
				noteIsPixel = thingie.customNoteIsPixel;
			if (Reflect.field(thingie, 'sourceNoteType') != null
				&& NoteTypeCompat.isGfSing(Reflect.field(thingie, 'sourceNoteType')))
				forceGfSing = true;

			specialNoteInfo = thingie;
			ignoreHealthMods = cast thingie.ignoreHealthMods;
		}
		if (mineNote || nukeNote) {
			shouldBeSung = false;
			dontCountNote = true;
			dontStrum = true;
		}
		if (isLiftNote) {
			shouldBeSung = false;
			dontStrum = true;
		}

		if (prevNote != null && isSustainNote) {
			customNotePath = prevNote.customSustainPath;
			customSustainPath = prevNote.customSustainPath;
		}

		var customStyleScale = specialNoteInfo == null ? null : specialNoteInfo.customNoteScale;
		var initialNoteScale:Float = customStyleScale != null ? customStyleScale
			: (curUiType.noteScale == null ? 0.7 : curUiType.noteScale);
		if (isSustainNote && holdAsset != ''
			&& FNFAssets.exists('assets/images/custom_ui/ui_packs/' + curUiType.uses + '/' + holdAsset + '.png'))
			initialNoteScale = curUiType.holdScale == null ? initialNoteScale : curUiType.holdScale;
		var codenameCreationEvent:CodenameNoteCreationEvent = null;
		var codenameVisualWasCancelled = false;
		var codenameAtlasWasChanged = false;
		var initialCodenameSprite = 'game/notes/default';
		var codenameOwnerActive = PlayState.instance != null
			&& PlayState.instance.codenameCreationOwnerRoot() != '';
		if (PlayState.instance != null && codenameOrigin != null) {
			noteTypeID = PlayState.instance.codenameNoteTypeIndex(sourceKind);
			initialCodenameSprite = PlayState.instance.codenameNoteSprite(sourceKind);
		}
		if (PlayState.instance != null
			&& (codenameOwnerActive
				|| initialCodenameSprite != 'game/notes/default'
				|| PlayState.instance.hasCodenameCreationCallback('onNoteCreation')
				|| PlayState.instance.hasCodenameCreationCallback('onPostNoteCreation'))) {
			PlayState.instance.prepareCodenameNoteCreation(this);
			var initialCodenameScale = initialNoteScale * codenamePreparedStrumScale;
			var strumLineID = codenameOrigin != null ? codenameOrigin.lineIndex
				: (authoredMustHit == true ? 1 : 0);
			var noteType = sourceKind == null
				? (mineNote ? 'Mine' : nukeNote ? 'Nuke' : isLiftNote ? 'Lift' : '')
				: sourceKind;
			codenameCreationEvent = new CodenameNoteCreationEvent(this,
				Std.int(Math.abs(this.noteData)) % NOTE_AMOUNT, noteType, noteTypeID, strumLineID,
				authoredMustHit == true, initialCodenameSprite,
				authoredAnimSuffix == null ? '' : authoredAnimSuffix, initialCodenameScale);
			PlayState.instance.dispatchCodenameCreationCallback('onNoteCreation', codenameCreationEvent);
			if (codenameCreationEvent.animSuffix != null) {
				var callbackSuffix = StringTools.trim(codenameCreationEvent.animSuffix);
				animSuffix = callbackSuffix == '' ? null : callbackSuffix;
				codenameAuthoredAnimSuffix = animSuffix;
			}
			codenameVisualWasCancelled = codenameCreationEvent.cancelled;
			var selectedAtlasPath = CodenameCreationVisual.selectedAtlasPath(codenameOwnerActive,
				codenameCreationEvent.noteSprite, codenameVisualWasCancelled);
			codenameCreationScaleSet = codenameCreationEvent.noteScale != null
				&& codenameCreationEvent.noteScale != initialCodenameScale;
			if (selectedAtlasPath != null) {
				try {
					var ownerFrames = selectedAtlasPath == 'game/notes/default'
						? PlayState.instance.codenameDefaultNoteAtlasFrames()
						: new CodenamePaths(PlayState.instance.codenameCreationOwnerRoot())
							.getFrames(selectedAtlasPath);
					if (CodenameCreationVisual.applyNoteAtlas(this, ownerFrames,
							CodenameCreationVisual.noteDirection(codenameCreationEvent.strumID),
							animSuffix, isSustainNote,
							codenameCreationScaleSet ? codenameCreationEvent.noteScale : initialNoteScale,
							PlayState.instance.codenameCreationOwnerRoot(), selectedAtlasPath)) {
						normalSize = codenameCreationScaleSet
							? codenameCreationEvent.noteScale : initialNoteScale;
						codenameAtlasWasChanged = true;
					}
				} catch (error:Dynamic) {
					trace('[codename-note-creation] Could not load selected-owner atlas '
						+ selectedAtlasPath + ': ' + Std.string(error));
					codenameAtlasWasChanged = false;
				}
			}
		}

		isPixel = noteIsPixel;
		if (codenameVisualWasCancelled) {
			// Cancellable creation scripts own all visual setup after cancel().
		} else if (codenameAtlasWasChanged) {
			// The selected owner's atlas and its trim/rotation metadata were
			// installed above before this note's hitbox and sustain sizing.
		} else {
		if (!noteIsPixel) {
			if (customNotePath != null) {
				if (getSpecialFrames) {
					getSpecialFrames = false;
					specialFramesKey = [];
					gotSpecialFrames = [];
				}
				var funnyNum = specialFramesKey.indexOf(customNotePath);
				if (funnyNum == -1) {
					var daFrames = DynamicAtlasFrames.fromSparrow(customNotePath + '.png', customNotePath + '.xml');
					specialFramesKey.push(customNotePath);
					gotSpecialFrames.push(daFrames);
					funnyNum = specialFramesKey.length - 1;
				}
				frames = gotSpecialFrames[funnyNum];
			} else {
				if (getFrames) {
					getFrames = false;
					framesKey = [];
					gotFrames = [];
				}
				var funnyNum = framesKey.indexOf(PlayState.SONG.uiType);
				if (funnyNum == -1) {
					var daFrames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/'
						+ curUiType.uses
						+ '/' + noteAsset + ".png",
						'assets/images/custom_ui/ui_packs/'
						+ curUiType.uses
						+ '/' + noteAsset + ".xml");
					framesKey.push(PlayState.SONG.uiType);
					gotFrames.push(daFrames);
					funnyNum = framesKey.length - 1;
				}
				frames = gotFrames[funnyNum];
			}
			if (animSuffix == null)
				animSuffix = '';
			else
				animSuffix = ' ' + animSuffix;

			final flipNoteVar = PlayState.flippedNotes ? NOTE_AMOUNT - (noteData % NOTE_AMOUNT+1) : noteData % NOTE_AMOUNT;
			final noteName = currentKey.getNote(flipNoteVar);
			if (isLiftNote)
				animation.addByPrefix('Scroll', noteName + ' lift${animSuffix}0');
			else if (nukeNote)
				animation.addByPrefix('Scroll', noteName + ' nuke${animSuffix}0');
			else if (mineNote)
				animation.addByPrefix('Scroll', noteName + ' mine${animSuffix}0');
			else if (dontEdit)
				animation.addByPrefix('Scroll', specialNoteInfo.animNames[noteData % NOTE_AMOUNT] + '0');
			else
				animation.addByPrefix('Scroll', noteName + '${animSuffix}0');

			var customHold = isSustainNote && holdAsset != '' && !dontEdit
				&& FNFAssets.exists('assets/images/custom_ui/ui_packs/' + curUiType.uses + '/' + holdAsset + '.png');
			if (customHold) {
				var holdPath = 'assets/images/custom_ui/ui_packs/' + curUiType.uses + '/' + holdAsset + '.png';
				if (holdAssetXml && FNFAssets.exists('assets/images/custom_ui/ui_packs/' + curUiType.uses + '/' + holdAsset + '.xml')) {
					frames = DynamicAtlasFrames.fromSparrow(holdPath,
						'assets/images/custom_ui/ui_packs/' + curUiType.uses + '/' + holdAsset + '.xml');
					animation.addByPrefix('holdend', currentKey.getNote(noteData % NOTE_AMOUNT) + ' hold end');
					animation.addByPrefix('hold', currentKey.getNote(noteData % NOTE_AMOUNT) + ' hold piece');
				} else {
					var holdBitmap = FNFAssets.getBitmapData(holdPath);
					var holdWidth = Std.int(holdBitmap.width / (NOTE_AMOUNT * holdFramesPerLane));
					if (holdWidth < 1) holdWidth = holdBitmap.width;
					loadGraphic(holdBitmap, true, holdWidth, holdBitmap.height);
					var holdLane = PlayState.flippedNotes ? NOTE_AMOUNT - (noteData % NOTE_AMOUNT + 1) : noteData % NOTE_AMOUNT;
					var holdFrame = holdLane * holdFramesPerLane;
					var holdEndFrame = holdFramesPerLane > 1 ? holdFrame + 1 : holdFrame;
					animation.add('holdend', [holdEndFrame]);
					animation.add('hold', [holdFrame]);
				}
				normalSize = curUiType.holdScale == null ? 0.7 : curUiType.holdScale;
				setGraphicSize(Std.int(width * normalSize));
				if (curUiType.holdOffsetX != null || curUiType.holdOffsetY != null)
					offset.set(curUiType.holdOffsetX == null ? 0 : curUiType.holdOffsetX,
						curUiType.holdOffsetY == null ? 0 : curUiType.holdOffsetY);
			} else if (prevNote.nukeNote) {
				animation.addByPrefix('holdend', noteName + ' nuke hold end${animSuffix}');
				animation.addByPrefix('hold', noteName + ' nuke hold piece${animSuffix}');
			} else if (prevNote.mineNote) {
				animation.addByPrefix('holdend', noteName + ' mine hold end${animSuffix}');
				animation.addByPrefix('hold', noteName + ' mine hold piece${animSuffix}');
			} else if (prevNote.dontEdit && customSustainPath != null) {
				animation.addByPrefix('holdend', specialNoteInfo.animNames[noteData % NOTE_AMOUNT] + ' hold end${animSuffix}');
				animation.addByPrefix('hold', specialNoteInfo.animNames[noteData % NOTE_AMOUNT] + ' hold piece${animSuffix}');
			} else {
				animation.addByPrefix('holdend', noteName + ' hold end${animSuffix}');
				animation.addByPrefix('hold', noteName + ' hold piece${animSuffix}');
			}

			var noteScale = initialNoteScale;
			if (isSustainNote && holdAsset != '' && FNFAssets.exists('assets/images/custom_ui/ui_packs/' + curUiType.uses + '/' + holdAsset + '.png'))
				noteScale = curUiType.holdScale == null ? noteScale : curUiType.holdScale;
			setGraphicSize(Std.int(width * noteScale));
			normalSize = noteScale;
			updateHitbox();
			antialiasing = true;
			// when arrowsEnds != arrowEnds :laughing_crying:
		} else {
			isPixel = true;
			if ((customNotePath != null && FNFAssets.exists(customNotePath + '.xml'))
				|| FNFAssets.exists('assets/images/custom_ui/ui_packs/' + curUiType.uses + "/arrows-pixels.xml")) {
				if (customNotePath != null) {
					if (getSpecialFrames) {
						getSpecialFrames = false;
						specialFramesKey = [];
						gotSpecialFrames = [];
					}
					var funnyNum = specialFramesKey.indexOf(customNotePath);
					if (funnyNum == -1) {
						var daFrames = DynamicAtlasFrames.fromSparrow(customNotePath + '.png', customNotePath + '.xml');
						specialFramesKey.push(customNotePath);
						gotSpecialFrames.push(daFrames);
						funnyNum = specialFramesKey.length - 1;
					}
					frames = gotSpecialFrames[funnyNum];
				} else {
					if (getFrames) {
						getFrames = false;
						framesKey = [];
						gotFrames = [];
					}
					var funnyNum = framesKey.indexOf(PlayState.SONG.uiType);
					if (funnyNum == -1) {
					var daFrames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/'
						+ curUiType.uses
						+ '/' + noteAsset + ".png",
						'assets/images/custom_ui/ui_packs/'
						+ curUiType.uses
						+ '/' + noteAsset + ".xml");
						framesKey.push(PlayState.SONG.uiType);
						gotFrames.push(daFrames);
						funnyNum = framesKey.length - 1;
					}
					frames = gotFrames[funnyNum];
				}

				if (animSuffix == null)
					animSuffix = '';
				else
					animSuffix = ' ' + animSuffix;

				final flipNoteVar = PlayState.flippedNotes ? NOTE_AMOUNT - (noteData % NOTE_AMOUNT+1)  : noteData % NOTE_AMOUNT;
				final noteName = currentKey.getNote(flipNoteVar);
				if (isLiftNote)
					animation.addByPrefix('Scroll', noteName + ' lift${animSuffix}');
				else if (nukeNote)
					animation.addByPrefix('Scroll', noteName + ' nuke${animSuffix}0');
				else if (mineNote)
					animation.addByPrefix('Scroll', noteName + ' mine${animSuffix}0');
				else if (dontEdit)
					animation.addByPrefix('Scroll', specialNoteInfo.animNames[noteData % NOTE_AMOUNT] + '0');
				else
					animation.addByPrefix('Scroll', noteName + '${animSuffix}0');

				if (isSustainNote) {
					frames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/'
							+ curUiType.uses
							+ "/arrowEnds.png",
							'assets/images/custom_ui/ui_packs/'
							+ curUiType.uses
							+ "/arrowEnds.xml");

					if (prevNote.nukeNote) {
						animation.addByPrefix('holdend', noteName + ' nuke hold end${animSuffix}');
						animation.addByPrefix('hold', noteName + ' nuke hold piece${animSuffix}');
					} else if (prevNote.mineNote) {
						animation.addByPrefix('holdend', noteName + ' mine hold end${animSuffix}');
						animation.addByPrefix('hold', noteName + ' mine hold piece${animSuffix}');
					} else if (prevNote.dontEdit) {
						animation.addByPrefix('holdend', specialNoteInfo.animNames[noteData % NOTE_AMOUNT] + ' hold end${animSuffix}');
						animation.addByPrefix('hold', specialNoteInfo.animNames[noteData % NOTE_AMOUNT] + ' hold piece${animSuffix}');
					} else {
						animation.addByPrefix('holdend', noteName + ' hold end${animSuffix}');
						animation.addByPrefix('hold', noteName + ' hold piece${animSuffix}');
					}
				}
			} else {
				if (customNotePath != null)
					loadGraphic(customNotePath + '.png', true, 17, 17);
				else
					loadGraphic('assets/images/custom_ui/ui_packs/' + curUiType.uses + "/arrows-pixels.png", true, 17, 17);

				if (animSuffix != null && numSuffix == null) {
					numSuffix = Std.parseInt(animSuffix);
				}
				if (numSuffix != null) {
					var intSuffix = numSuffix;
					animation.add('greenScroll', [intSuffix]);
					animation.add('redScroll', [intSuffix]);
					animation.add('blueScroll', [intSuffix]);
					animation.add('purpleScroll', [intSuffix]);
					if (isSustainNote) {
						loadGraphic('assets/images/custom_ui/ui_packs/' + curUiType.uses + "/arrowEnds.png", true, 7, 6);

						animation.add('purpleholdend', [intSuffix]);
						animation.add('greenholdend', [intSuffix]);
						animation.add('redholdend', [intSuffix]);
						animation.add('blueholdend', [intSuffix]);

						animation.add('purplehold', [intSuffix]);
						animation.add('greenhold', [intSuffix]);
						animation.add('redhold', [intSuffix]);
						animation.add('bluehold', [intSuffix]);
					}
				} else {
					animation.add('greenScroll', [6]);
					animation.add('redScroll', [7]);
					animation.add('blueScroll', [5]);
					animation.add('purpleScroll', [4]);

					if (isSustainNote) {
						loadGraphic('assets/images/custom_ui/ui_packs/' + curUiType.uses + "/arrowEnds.png", true, 7, 6);

						animation.add('purpleholdend', [4]);
						animation.add('greenholdend', [6]);
						animation.add('redholdend', [7]);
						animation.add('blueholdend', [5]);

						animation.add('purplehold', [0]);
						animation.add('greenhold', [2]);
						animation.add('redhold', [3]);
						animation.add('bluehold', [1]);
					}
					if (isLiftNote) {
						animation.add('greenScroll', [22]);
						animation.add('redScroll', [23]);
						animation.add('blueScroll', [21]);
						animation.add('purpleScroll', [20]);
					}
					if (mineNote) {
						animation.add('greenScroll', [26]);
						animation.add('redScroll', [27]);
						animation.add('blueScroll', [25]);
						animation.add('purpleScroll', [24]);
					}
					if (nukeNote) {
						animation.add('greenScroll', [30]);
						animation.add('redScroll', [31]);
						animation.add('blueScroll', [29]);
						animation.add('purpleScroll', [28]);
					}
				}
				if (dontEdit) {
					animation.add('greenScroll', [specialNoteInfo.animInt[2]]);
					animation.add('redScroll', [specialNoteInfo.animInt[3]]);
					animation.add('purpleScroll', [specialNoteInfo.animInt[0]]);
					animation.add('blueScroll', [specialNoteInfo.animInt[1]]);
				}
			}
			setGraphicSize(Std.int(width * PlayState.daPixelZoom));
			updateHitbox();
			normalSize = 6;
		}
		}
		if (codenameCreationScaleSet && codenameCreationEvent != null && !codenameVisualWasCancelled) {
			scale.set(codenameCreationEvent.noteScale, codenameCreationEvent.noteScale);
			updateHitbox();
			normalSize = codenameCreationEvent.noteScale;
		}
		x += swagWidth * (noteData % NOTE_AMOUNT);
		if (!codenameVisualWasCancelled)
			animation.play('Scroll');

		// trace(prevNote);
		if (isSustainNote && OptionsHandler.options.downscroll && !nightmareVisionLegacyGeometry)
			flipY = true;
		if (isSustainNote && prevNote != null) {
			noteScore * 0.2;
			alpha = 0.6;
			multAlpha = 0.6;

			// sustain notes are notes too #equalrightsforsustains
			altNote = prevNote.altNote;
			altNum = prevNote.altNum;
			crossFade = prevNote.crossFade;

			nukeNote = prevNote.nukeNote;
			mineNote = prevNote.mineNote;
			isLiftNote = prevNote.isLiftNote;
			drainNote = prevNote.drainNote;
			dontCountNote = prevNote.dontCountNote;
			ratingDisabled = prevNote.ratingDisabled;
			dontStrum = prevNote.dontStrum;
			aiShouldHit = prevNote.aiShouldHit;
			avoidAutoHit = prevNote.avoidAutoHit;

			dontEdit = prevNote.dontEdit;
			if (dontEdit) {
				shouldBeSung = prevNote.shouldBeSung;
				healAmount = prevNote.healAmount;
				healMultiplier = prevNote.healMultiplier;
				damageAmount = prevNote.damageAmount;
				damageMultiplier = prevNote.damageMultiplier;
				noteHit = prevNote.noteHit;
				noteMiss = prevNote.noteMiss;
				classes = prevNote.classes;
				coolId = prevNote.coolId;
			}

			if ((sourceTimingMode == 1 && codenameInputLine == null) || nightmareVisionLegacyGeometry) {
				// Source skin installation happens after construction. Stretch and
				// center only once its actual atlas/sheet dimensions are available.
				copyAngle = false;
				animation.play('holdend');
				scale.y = 1;
				updateHitbox();
			} else {
				x += width / 2;
				animation.play('holdend');
				updateHitbox();
				x -= width / 2;
				if (isPixel) x += 30;
				if (prevNote.isSustainNote) {
					prevNote.animation.play('hold');
					prevNote.scale.y *= Conductor.stepCrochet / 100 * 1.5 * PlayState.effectiveScrollSpeed;
					prevNote.updateHitbox();
				}
			}
		}
		offsetWritesReady = true;
		if (codenameCreationEvent != null && PlayState.instance != null) {
			PlayState.instance.dispatchCodenameCreationCallback('onPostNoteCreation', codenameCreationEvent);
			PlayState.instance.markCodenameCreationVisual('note', codenameCreationEvent.strumLineID,
				codenameCreationEvent.strumID,
				codenameAtlasWasChanged ? codenameCreationEvent.noteSprite : 'native-ui',
				codenameAtlasWasChanged && !codenameVisualWasCancelled,
				codenameFrameOffset == null ? 0 : codenameFrameOffset.x,
				codenameFrameOffset == null ? 0 : codenameFrameOffset.y);
		}
	}

	/** Flixel's drawn frame center relative to x, including its current atlas offset. */
	public function graphicCenterOffsetX():Float {
		if (origin == null || offset == null || scale == null)
			return width / 2;
		var center = origin.x - offset.x - origin.x * scale.x + width / 2;
		return Math.isFinite(center) ? center : width / 2;
	}

	/** Keep every piece under its own hold head as the receptor moves or scales. */
	public function sustainHeadAnchorX():Float {
		if (sustainHead != null) {
			if (sustainHead.alive && sustainHead.origin != null
				&& sustainHead.offset != null && sustainHead.scale != null)
				sustainHead.sustainHeadCenterX = sustainHead.graphicCenterOffsetX();
			if (sustainHead.sustainHeadCenterX != null)
				sustainHeadCenterX = sustainHead.sustainHeadCenterX;
		}
		return sustainHeadCenterX == null ? swagWidth / 2 : sustainHeadCenterX;
	}

	/** A forward seek can retire the head or predecessor of a sustain that
	 * remains on screen. Re-root that surviving piece before the next gameplay
	 * update reads fields from the destroyed note. Preserve its cached head
	 * anchor so the hold does not jump horizontally at the seek boundary. */
	public function repairSustainChainAfterSeek():Void {
		if (prevNote == null || !prevNote.exists || !prevNote.alive)
			prevNote = this;
		if (sustainHead != null && (!sustainHead.exists || !sustainHead.alive)) {
			if (sustainHeadCenterX == null)
				sustainHeadCenterX = graphicCenterOffsetX();
			sustainHead = null;
		}
	}

	override public function updateHitbox():Void {
		if (offsetState == null)
			offsetState = new NoteOffsetState();
		offsetState.capture(offset.x, offset.y, offsetWritesReady);
		super.updateHitbox();
		if (!isSustainNote && customNotePath != null && specialNoteInfo != null
			&& Reflect.field(specialNoteInfo, 'sourceNoteStyle') != null) {
			var authoredX = specialNoteInfo.customNoteOffsetX == null ? 0 : specialNoteInfo.customNoteOffsetX;
			var authoredY = specialNoteInfo.customNoteOffsetY == null ? 0 : specialNoteInfo.customNoteOffsetY;
			offset.x = NoteStyleAlignment.centeredOffsetX(width, origin.x, scale.x, swagWidth, authoredX);
			offset.y += authoredY;
		} else if (!isSustainNote && customNotePath == null && psychSkinOwner == null
			&& vSliceNoteOffsetX != null) {
			// Donor Strumline.buildNoteSprite centers a tap in its 104px lane.
			// PlayState snaps our x to the receptor without that width correction,
			// so center the canvas in this fork's 112px lane after every hitbox reset.
			offset.x = NoteStyleAlignment.centeredOffsetX(width, origin.x, scale.x,
				swagWidth, vSliceNoteOffsetX);
			offset.y += vSliceNoteOffsetY;
		}
	offsetState.finish(offset.x, offset.y);
		offset.set(offsetState.x, offsetState.y);
		if (!isSustainNote)
			sustainHeadCenterX = graphicCenterOffsetX();
	}

	/** Apply Codename's note-frame nudge in sprite space. Keep the native
	 * Flixel fast path for the overwhelmingly common zero-offset note. */
	override function drawFrameComplex(frame:FlxFrame, camera:FlxCamera):Void {
		var visualOffset = codenameFrameOffset;
		if (visualOffset == null || (visualOffset.x == 0 && visualOffset.y == 0)) {
			super.drawFrameComplex(frame, camera);
			return;
		}
		final matrix = _matrix;
		frame.prepareMatrix(matrix, FlxFrameAngle.ANGLE_0, checkFlipX(), checkFlipY());
		matrix.translate(-origin.x, -origin.y);
		CodenameCreationVisual.applyFrameOffset(matrix, visualOffset.x, visualOffset.y);
		matrix.scale(scale.x, scale.y);
		if (bakedRotationAngle <= 0) {
			updateTrig();
			if (angle != 0) matrix.rotateWithTrig(_cosAngle, _sinAngle);
		}
		getScreenPosition(_point, camera).subtract(offset);
		_point.add(origin.x, origin.y);
		matrix.translate(_point.x, _point.y);
		if (isPixelPerfectRender(camera)) {
			matrix.tx = Math.floor(matrix.tx);
			matrix.ty = Math.floor(matrix.ty);
		}
		CodenameFunkinSprite.applyCameraTransform(matrix, camera, 1, 1, true, true);
		camera.drawPixels(frame, framePixels, matrix, colorTransform, blend, antialiasing, shader);
	}

	override public function isSimpleRenderBlit(?camera:FlxCamera):Bool {
		if (codenameFrameOffset != null
			&& (codenameFrameOffset.x != 0 || codenameFrameOffset.y != 0)) return false;
		return super.isSimpleRenderBlit(camera);
	}

	/** Keep a shifted atlas frame inside its draw bounds for Flixel culling. */
	override public function getScreenBounds(?newRect:FlxRect, ?camera:FlxCamera):FlxRect {
		var visualOffset = codenameFrameOffset;
		if (visualOffset == null || (visualOffset.x == 0 && visualOffset.y == 0))
			return super.getScreenBounds(newRect, camera);
		if (camera == null) camera = getDefaultCamera();
		var bounds = super.getScreenBounds(newRect, camera);
		var scaledX = visualOffset.x * scale.x + (scale.x < 0 ? frameWidth * scale.x : 0);
		var scaledY = visualOffset.y * scale.y + (scale.y < 0 ? frameHeight * scale.y : 0);
		var radians = bakedRotationAngle <= 0 ? angle * FlxAngle.TO_RAD : 0;
		var cos = Math.cos(radians);
		var sin = Math.sin(radians);
		bounds.x -= scaledX * cos - scaledY * sin;
		bounds.y -= scaledX * sin + scaledY * cos;
		var scrollX = camera.scroll.x * scrollFactor.x;
		var scrollY = camera.scroll.y * scrollFactor.y;
		bounds.x += Std.int(scrollX) - scrollX;
		bounds.y += Std.int(scrollY) - scrollY;
		if (isPixelPerfectRender(camera)) {
			bounds.x -= 2;
			bounds.y -= 2;
			bounds.width += 4;
			bounds.height += 4;
		}
		if (!CodenameFunkinSprite.hasCameraTransform(camera, 1, 1, true, true)) {
			// The default Codename camera factors are identity; no extra bounds
			// transform is needed here.
		}
		return bounds;
	}

	override public function destroy():Void {
		if (nightmareVisionTypeRuntime != null) nightmareVisionTypeRuntime.releaseNote(this);
		nightmareVisionTypeRuntime = null;
		if (nightmareVisionRenderer != null) nightmareVisionRenderer.release(this);
		nightmareVisionRenderer = null;
		if (nightmareVisionTailState != null) nightmareVisionTailState.notes.remove(this);
		nightmareVisionTailState = null;
		nightmareVisionRGB = null;
		nightmareVisionLegacyColors = null;
		// FunkinSprite does not pool its baseScale point in destroy(). Scripts
		// may retain the point, so do not return it to FlxPoint's pool.
		nightmareVisionBaseScalePoint = null;

		if (codenameFrameOffset != null && codenameFrameOffsetOwned) {
			codenameFrameOffset.put();
		}
		codenameFrameOffset = null;
		codenameFrameOffsetOwned = false;
		super.destroy();
	}

	public function switchType(uiType:String) {
		// A timed style event can arrive while an already-hit note still has a
		// slot in the state's note group. FlxSprite.destroy() releases animation;
		// only live sprites can be rebuilt for the new receptor pack.
		if (animation == null) return;
		final newType = Reflect.field(Judgement.uiJson, uiType);
		if (newType == null)
			return;
		setVSliceNoteOffsets(newType);
		// NoteKeys is the authored animation-name table as well as the atlas
		// descriptor.  Reusing the old table made a mid-song note-style swap
		// load the new bitmap but keep the previous style's animation prefixes,
		// which is especially visible on pixel/hold notes.
		if (currentKey == null)
			currentKey = new NoteKeys(newType.uses, newType.isPixel);
		else
			currentKey.newKey(newType.uses, newType.isPixel);
		isPixel = newType.isPixel;
		var noteAsset = newType.noteAsset == null || StringTools.trim(newType.noteAsset) == ''
			? (newType.isPixel ? 'arrows-pixels' : 'NOTE_assets') : newType.noteAsset;
		var holdAsset = newType.holdAsset == null ? '' : StringTools.trim(newType.holdAsset);
		var holdFramesPerLane = newType.holdFramesPerLane == null ? 1 : newType.holdFramesPerLane;
		if (holdFramesPerLane < 1)
			holdFramesPerLane = 1;
		var customStylePixel:Dynamic = specialNoteInfo == null ? null : specialNoteInfo.customNoteIsPixel;
		if (customStylePixel != null)
			isPixel = customStylePixel == true;
		else
			isPixel = newType.isPixel;
		if (!isPixel) {
			if (customNotePath != null) {
				if (getSpecialFrames) {
					getSpecialFrames = false;
					specialFramesKey = [];
					gotSpecialFrames = [];
				}
				var funnyNum = specialFramesKey.indexOf(customNotePath);
				if (funnyNum == -1) {
					var daFrames = DynamicAtlasFrames.fromSparrow(customNotePath + '.png', customNotePath + '.xml');
					specialFramesKey.push(customNotePath);
					gotSpecialFrames.push(daFrames);
					funnyNum = specialFramesKey.length - 1;
				}
				frames = gotSpecialFrames[funnyNum];
			} else {
				if (getFrames) {
					getFrames = false;
					framesKey = [];
					gotFrames = [];
				}
				var funnyNum = framesKey.indexOf(uiType);
				if (funnyNum == -1) {
					var daFrames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/'
						+ newType.uses
						+ '/' + noteAsset + ".png",
						'assets/images/custom_ui/ui_packs/'
						+ newType.uses
						+ '/' + noteAsset + ".xml");
					framesKey.push(uiType);
					gotFrames.push(daFrames);
					funnyNum = framesKey.length - 1;
				}
				frames = gotFrames[funnyNum];
			}

			final flipNoteVar = PlayState.flippedNotes ? NOTE_AMOUNT - (noteData+1) : noteData;
			final noteName = currentKey.getNote(flipNoteVar);
			if (isLiftNote)
				animation.addByPrefix('Scroll', noteName + ' lift0');
			else if (nukeNote)
				animation.addByPrefix('Scroll', noteName + ' nuke0');
			else if (mineNote)
				animation.addByPrefix('Scroll', noteName + ' mine0');
			else if (dontEdit)
				animation.addByPrefix('Scroll', specialNoteInfo.animNames[noteData] + '0');
			else
				animation.addByPrefix('Scroll', noteName + '0');

			var customHold = isSustainNote && holdAsset != '' && !dontEdit
				&& FNFAssets.exists('assets/images/custom_ui/ui_packs/' + newType.uses + '/' + holdAsset + '.png');
			if (customHold) {
				var holdPath = 'assets/images/custom_ui/ui_packs/' + newType.uses + '/' + holdAsset + '.png';
				if (newType.holdAssetXml == true && FNFAssets.exists('assets/images/custom_ui/ui_packs/' + newType.uses + '/' + holdAsset + '.xml')) {
					frames = DynamicAtlasFrames.fromSparrow(holdPath,
						'assets/images/custom_ui/ui_packs/' + newType.uses + '/' + holdAsset + '.xml');
					animation.addByPrefix('holdend', noteName + ' hold end');
					animation.addByPrefix('hold', noteName + ' hold piece');
				} else {
					var holdBitmap = FNFAssets.getBitmapData(holdPath);
					var holdWidth = Std.int(holdBitmap.width / (NOTE_AMOUNT * holdFramesPerLane));
					if (holdWidth < 1) holdWidth = holdBitmap.width;
					loadGraphic(holdBitmap, true, holdWidth, holdBitmap.height);
					var holdLane = PlayState.flippedNotes ? NOTE_AMOUNT - (noteData % NOTE_AMOUNT + 1) : noteData % NOTE_AMOUNT;
					var holdFrame = holdLane * holdFramesPerLane;
					var holdEndFrame = holdFramesPerLane > 1 ? holdFrame + 1 : holdFrame;
					animation.add('holdend', [holdEndFrame]);
					animation.add('hold', [holdFrame]);
				}
				if (newType.holdOffsetX != null || newType.holdOffsetY != null)
					offset.set(newType.holdOffsetX == null ? 0 : newType.holdOffsetX,
						newType.holdOffsetY == null ? 0 : newType.holdOffsetY);
			} else if (prevNote.nukeNote) {
				animation.addByPrefix('holdend', noteName + ' nuke hold end');
				animation.addByPrefix('hold', noteName + ' nuke hold piece');
			} else if (prevNote.mineNote) {
				animation.addByPrefix('holdend', noteName + ' mine hold end');
				animation.addByPrefix('hold', noteName + ' mine hold piece');
			} else if (prevNote.isLiftNote) {
				animation.addByPrefix('holdend', noteName + ' lift hold end');
				animation.addByPrefix('hold', noteName + ' lift hold piece');
			} else if (prevNote.dontEdit && customSustainPath != null) {
				animation.addByPrefix('holdend', specialNoteInfo.animNames[noteData] + ' hold end');
				animation.addByPrefix('hold', specialNoteInfo.animNames[noteData] + ' hold piece');
			} else {
				animation.addByPrefix('holdend', noteName + ' hold end');
				animation.addByPrefix('hold', noteName + ' hold piece');
			}

			normalSize = (isSustainNote && holdAsset != '' && FNFAssets.exists('assets/images/custom_ui/ui_packs/' + newType.uses + '/' + holdAsset + '.png'))
				? (newType.holdScale == null ? 0.7 : newType.holdScale)
				: (newType.noteScale == null ? 0.7 : newType.noteScale);
			if (!isSustainNote && customNotePath != null && specialNoteInfo != null
				&& Reflect.field(specialNoteInfo, 'sourceNoteStyle') != null
				&& specialNoteInfo.customNoteScale != null)
				normalSize = specialNoteInfo.customNoteScale;
		} else {
			if ((customNotePath != null && FNFAssets.exists(customNotePath + '.xml'))
				|| FNFAssets.exists('assets/images/custom_ui/ui_packs/' + newType.uses + "/arrows-pixels.xml")) {
				if (customNotePath != null) {
					if (getSpecialFrames) {
						getSpecialFrames = false;
						specialFramesKey = [];
						gotSpecialFrames = [];
					}
					var funnyNum = specialFramesKey.indexOf(customNotePath);
					if (funnyNum == -1) {
						var daFrames = DynamicAtlasFrames.fromSparrow(customNotePath + '.png', customNotePath + '.xml');
						specialFramesKey.push(customNotePath);
						gotSpecialFrames.push(daFrames);
						funnyNum = specialFramesKey.length - 1;
					}
					frames = gotSpecialFrames[funnyNum];
				} else {
					if (getFrames) {
						getFrames = false;
						framesKey = [];
						gotFrames = [];
					}
					var funnyNum = framesKey.indexOf(uiType);
					if (funnyNum == -1) {
					var daFrames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/'
							+ newType.uses
							+ '/' + noteAsset + ".png",
							'assets/images/custom_ui/ui_packs/'
							+ newType.uses
							+ '/' + noteAsset + ".xml");
						framesKey.push(uiType);
						gotFrames.push(daFrames);
						funnyNum = framesKey.length - 1;
					}
					frames = gotFrames[funnyNum];
				}

				final flipNoteVar = PlayState.flippedNotes ? NOTE_AMOUNT - (noteData+1) : noteData;
				final noteName = currentKey.getNote(flipNoteVar);
				if (isLiftNote)
					animation.addByPrefix('Scroll', noteName + ' lift');
				else if (nukeNote)
					animation.addByPrefix('Scroll', noteName + ' nuke0');
				else if (mineNote)
					animation.addByPrefix('Scroll', noteName + ' mine0');
				else if (dontEdit)
					animation.addByPrefix('Scroll', specialNoteInfo.animNames[noteData] + '0');
				else
					animation.addByPrefix('Scroll', noteName + '0');

				if (isSustainNote) {
					frames = DynamicAtlasFrames.fromSparrow('assets/images/custom_ui/ui_packs/'
							+ newType.uses
							+ "/arrowEnds.png",
							'assets/images/custom_ui/ui_packs/'
							+ newType.uses
							+ "/arrowEnds.xml");

					if (prevNote.nukeNote) {
						animation.addByPrefix('holdend', noteName + ' nuke hold end');
						animation.addByPrefix('hold', noteName + ' nuke hold piece');
					} else if (prevNote.mineNote) {
						animation.addByPrefix('holdend', noteName + ' mine hold end');
						animation.addByPrefix('hold', noteName + ' mine hold piece');
					}  else if (prevNote.isLiftNote) {
						animation.addByPrefix('holdend', noteName + ' lift hold end');
						animation.addByPrefix('hold', noteName + ' lift hold piece');
					} else if (prevNote.dontEdit) {
						animation.addByPrefix('holdend', specialNoteInfo.animNames[noteData] + ' hold end');
						animation.addByPrefix('hold', specialNoteInfo.animNames[noteData] + ' hold piece');
					} else {
						animation.addByPrefix('holdend', noteName + ' hold end');
						animation.addByPrefix('hold', noteName + ' hold piece');
					}
				}
			} else {
				if (customNotePath != null)
					loadGraphic(customNotePath + '.png', true, 17, 17);
				else
					loadGraphic('assets/images/custom_ui/ui_packs/' + newType.uses + "/arrows-pixels.png", true, 17, 17);

				// only works for 4 key, use an xml next time
				var scrollNum = 4 + noteData;

				if (isLiftNote)
					scrollNum += 16;
				if (mineNote)
					scrollNum += 20;
				if (nukeNote)
					scrollNum += 24;
				if (dontEdit) 
					scrollNum = specialNoteInfo.animInt[noteData];

				animation.add('Scroll', [scrollNum]);

				if (isSustainNote) {
					loadGraphic('assets/images/custom_ui/ui_packs/' + newType.uses + "/arrowEnds.png", true, 7, 6);

					animation.add('holdend', [4 + noteData]);
					animation.add('hold', [noteData]);
				}
			}
			
			normalSize = 6;
		}

		animation.play('Scroll');

		resetSize();
		setGraphicSize(Std.int(width * normalSize));
		updateHitbox();

		antialiasing = !isPixel;

		if (isSustainNote && prevNote != null) {
			animation.play('holdend');

			updateHitbox();

			if (!nightmareVisionLegacyGeometry && (sourceTimingMode != 1 || codenameInputLine != null) && prevNote.isSustainNote && prevNote.animation != null && prevNote.exists) {
				prevNote.animation.play('hold');

				prevNote.scale.y *= Conductor.stepCrochet / 100 * 1.5 * PlayState.effectiveScrollSpeed;

				prevNote.updateHitbox();
			}
		}
	}

	function setVSliceNoteOffsets(style:TUI):Void {
		if (style.vSliceAlias == null || StringTools.trim(Std.string(style.vSliceAlias)) == '') {
			vSliceNoteOffsetX = null;
			vSliceNoteOffsetY = 0;
			return;
		}
		vSliceNoteOffsetX = style.noteOffsetX == null ? 0 : style.noteOffsetX;
		vSliceNoteOffsetY = style.noteOffsetY == null ? 0 : style.noteOffsetY;
	}

	public inline function isAutoPlayed():Bool {
		if (codenameInputLine != null)
			return funnyMode || codenameInputLine.cpu || codenameInputLine.botplay;
		if (nightmareVisionTypeRuntime != null) return sourcePlayfieldAutoPlay;
		return funnyMode || sourcePlayfieldAutoPlay || (!duoMode && (mustPress ? oppMode : !oppMode));
	}

	/** Resolve the authored actor without changing the old two-side mustPress API. */
	public inline function isPlayerControlled():Bool
		return sourcePlayfieldPlayerControlled == null ? mustPress : sourcePlayfieldPlayerControlled;

	public function canAutoHit():Bool {
		if (nightmareVisionTypeRuntime != null)
			// Nightmare Vision's PlayField sends auto-play notes to noteHit even
			// when a player-owned hazard or canMiss note makes that handler return
			// early. Keep only its outer-loop ignoreNote filter here; PlayState's
			// source-tick dispatcher owns the rest of that lifecycle.
			return !ignoreNote;
		// The opponent may opt into hazard animations; BF must still avoid them.
		if (mustPress)
			return !canMiss && !ignoreNote && !blockHit && !hitCausesMiss && !avoidAutoHit && !dontCountNote
				&& !mineNote && !nukeNote && getHealth('sick') >= 0;
		return !dontCountNote || aiShouldHit;
	}

	// Called by PlayState as well as sprite updates. Rendering/activity must
	// never decide whether a computer-controlled note gets hit.
	public function updateAutoHit(songPosition:Float):Void {
		// NV autoplay is admitted by PlayState once per source tick. Marking it
		// here would couple source callback frequency to uncapped sprite updates
		// and hide donor early-return behavior for hazards/canMiss notes.
		if (nightmareVisionTypeRuntime != null) return;
		if (!isAutoPlayed() || autoHitSuppressed) return;
		canBeHit = false;
		if (canAutoHit() && strumTime <= songPosition)
			wasGoodHit = true;
	}

	override function update(elapsed:Float) {
		super.update(elapsed);
		if (nightmareVisionTypeRuntime != null) nightmareVisionTypeRuntime.update(this, elapsed);
		if (nightmareVisionLegacyGeometry) NightmareVisionLegacyHitFlow.updateFlags(this);
		// if we are player one and it's bf's note or we are duo mode or we are player two and it's p2's note
		// and it isn't demo mode
		if (!isAutoPlayed()) {
			var signedDiff = Conductor.songPosition - strumTime;
			// ok.... so if strumTime is bigger than songPosition that means it is waiting to be hit because well the song hasn't reached it???
			// negative is early, positive is late
			var noteDiff = Math.abs(signedDiff);
			if (codenameInputLine != null && PlayState.instance != null && PlayState.instance.ratingManager != null) {
				// Codename's StrumLine gates input with its last registered rating
				// window. The late-miss threshold itself is not scaled per note.
				var hitWindow = PlayState.instance.ratingManager.lastHitWindow;
				canBeHit = signedDiff < hitWindow * latePressWindow
					&& signedDiff > -hitWindow * earlyPressWindow;
				if (signedDiff > hitWindow && !wasGoodHit) tooLate = true;
			} else if (sourceTimingMode != 0) {
				if (sourceTimingMode == 1)
					canBeHit = SourceNoteTiming.psychCanBeHit(strumTime, Conductor.songPosition,
						Conductor.safeZoneOffset, earlyHitMult, lateHitMult);
				if (isLate()) tooLate = true;
			} else {
				// The * 0.5 us so that its easier to hit them too late, instead of too early
				if (noteDiff < Judge.wayoffJudge * timingMultiplier) {
					canBeHit = true;
				} else
					canBeHit = false;
				// Nuke notes can only be hit with a bad or better because nuke notes are weird champ
				if (nukeNote && !(noteDiff < Judge.badJudge * timingMultiplier)) {
					canBeHit = false;
				}
				if (mineNote && !(noteDiff < Judge.shitJudge * timingMultiplier)) {
					canBeHit = false;
				}
				if (signedDiff > Judge.wayoffJudge)
					tooLate = true;
				if (nukeNote && signedDiff > Judge.badJudge) {
					tooLate = true;
				}
				if (mineNote && signedDiff > Judge.shitJudge) {
					tooLate = true;
				}
			}
		} else {
			updateAutoHit(Conductor.songPosition);
		}

		if (tooLate) {
			if (alpha > 0.3)
				alpha = 0.3;
		}
	}
	// inline because it's 1 fucking line dumbass
	public inline function daStrumTime():Float {
		return strumTime + OptionsHandler.options.offset;
	}
	public static inline function getTrueStrumTime(strumTime:Float):Float {
		return strumTime + OptionsHandler.options.offset;
	}
	public function getHealth(rating:String):Float {
		if (mineNote) {
			if (rating != 'miss')
				return -0.45;
			else
				return 0;
		}
		if (nukeNote) {
			if (rating != 'miss')
				return -69;
			else
				return 0;
		}
		if (rating == 'miss' && missHealth != null)
			return -missHealth * (ignoreHealthMods ? 1 : PlayState.healthLossMultiplier);
		if (rating != 'miss' && hitHealth != null)
			return hitHealth * (ignoreHealthMods ? 1 : PlayState.healthGainMultiplier);
		if (consistentHealth) {
			var ouchie = false;
			switch (healCutoff) {
				case 'shit':
					ouchie = rating == 'shit' || rating == 'wayoff' || rating == 'miss';
				case 'wayoff':
					ouchie = rating == 'wayoff' || rating == 'miss';
				case 'miss':
					ouchie = rating == 'miss';
				case 'bad' | null:
					ouchie = rating == 'shit' || rating == 'wayoff' || rating == 'bad' || rating == 'miss';
				case 'good':
					ouchie = rating == 'shit' || rating == 'wayoff' || rating == 'bad' || rating == 'miss' || rating == 'good';
				case 'sick':
					ouchie = true;
				case 'none':
					ouchie = false;
			}
			if (ouchie) {
				if (damageAmount != null) {
					return damageAmount * (ignoreHealthMods ? 1 : PlayState.healthLossMultiplier);
				} else {
					return damageMultiplier * -0.04 * (ignoreHealthMods ? 1 : PlayState.healthLossMultiplier);
				}
			} else {
				if (healAmount != null) {
					return healAmount * (ignoreHealthMods ? 1 : PlayState.healthGainMultiplier);
				} else {
					return healMultiplier * (ignoreHealthMods ? 1 : PlayState.healthGainMultiplier) * 0.04;
				}
			}
		} else {
			var healies = 0.0;
			var shitHeal = OptionsHandler.options.useKadeHealth ? 0.2 : 0.06;
			var badHeal = OptionsHandler.options.useKadeHealth ? 0.06 : 0.03;
			var goodHeal = OptionsHandler.options.useKadeHealth ? 0.04  : 0.03;
			var missHeal = 0.04;
			var sickHeal = OptionsHandler.options.useKadeHealth ? 0.1 : 0.07;
			switch (healCutoff) {
				case "shit":
					switch (rating) {
						case "shit" | 'wayoff':
							healies = -shitHeal;
						case "bad":
							healies = badHeal;
						case "good":
							healies = goodHeal;
						case "miss":
							
							healies = -missHeal;
						case "sick":
							healies = sickHeal;
					}
				case "bad" | null: 
					switch (rating) {
						case "shit" | 'wayoff':
							healies = -shitHeal;
						case "bad":
							healies = -badHeal;
						case "good":
							healies = goodHeal;
						case "miss":
							healies = -missHeal;
						case "sick":
							healies = sickHeal;
					}
				case "good": 
					switch (rating) {
						case "shit" | 'wayoff':
							healies = -shitHeal;
						case "bad":
							healies = -badHeal;
						case "good":
							healies = -goodHeal;
						case "miss":
							healies = -missHeal;
						case "sick":
							healies = sickHeal;
					}
				case "wayoff":
					switch (rating) {
						case "shit":
							healies = shitHeal;
						case 'wayoff': 
							healies = -shitHeal;
						case "bad":
							healies = badHeal;
						case "good":
							healies = goodHeal;
						case "miss":
							healies = -missHeal;
						case "sick":
							healies = sickHeal;
					}
				case "miss":
					switch (rating) {
						case "shit" | 'wayoff':
							healies = shitHeal;
						case "bad":
							healies = badHeal;
						case "good":
							healies = goodHeal;
						case "miss":
							healies = -missHeal;
						case "sick":
							healies = sickHeal;
					}

				case "sick":
					switch (rating) {
						case "shit" | 'wayoff':
							healies = -shitHeal;
						case "bad":
							healies = -badHeal;
						case "good":
							healies = -goodHeal;
						case "miss":
							healies = -missHeal;
						case "sick":
							healies = -sickHeal;
					}
			}
			if (healies > 0) {
				// this was pointless then :grief:
				if (healAmount != null) {
					return healAmount * (ignoreHealthMods ? 1 : PlayState.healthGainMultiplier);
				} else {
					return healMultiplier * healies * (ignoreHealthMods ? 1 : PlayState.healthGainMultiplier);
				}

			} else {
				if (damageAmount != null) {
					return damageAmount * (ignoreHealthMods ? 1 : PlayState.healthLossMultiplier);
				} else {
					return damageMultiplier * healies * (ignoreHealthMods ? 1 : PlayState.healthLossMultiplier);
				}
			}
		}
	}
}
