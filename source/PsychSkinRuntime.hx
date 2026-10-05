package;

import flixel.graphics.frames.FlxAtlasFrames;
import PsychSkinResolver.PsychSkinDescriptor;
import DynamicSprite.DynamicAtlasFrames;
import Strumline.StrumNote;

/** Atomic Psych 1.0.4 skin reload for an individual native sprite. */
class PsychSkinRuntime {
	public static inline var DEFAULT_SKIN:String = 'noteSkins/NOTE_assets';
	static var noteColors:Array<String> = ['purple', 'blue', 'green', 'red'];
	static var directions:Array<String> = ['left', 'down', 'up', 'right'];
	static var receptorIdle:Array<String> = ['arrowLEFT', 'arrowDOWN', 'arrowUP', 'arrowRIGHT'];

	public static function reloadNote(note:Note, authored:String, ownerRoot:String, chartSkin:String,
		pixel:Bool, postfix:String, ?diagnostics:Bool = false):Bool {
		markDiagnostic(diagnostics, 'reload:resolve');
		var skin = authored == null || authored == '' ? (chartSkin == null || chartSkin == '' ? DEFAULT_SKIN : chartSkin) : authored;
		var result = PsychSkinResolver.resolveDetailed(skin, ownerRoot, pixel, postfix);
		if (result.descriptor == null) {
			markDiagnostic(diagnostics, 'reload:missing-descriptor');
			trace('[psych-skin] note ' + result.reason);
			return false;
		}
		var lane = ((note.noteData % 4) + 4) % 4;
		var color = noteColors[lane];
		var descriptor = result.descriptor;
		markDiagnostic(diagnostics, 'reload:atlas');
		var frames = pixel ? null : atlas(descriptor);
		markDiagnostic(diagnostics, 'reload:validate');
		if (!validNote(descriptor, frames, color, note.isSustainNote)) {
			markDiagnostic(diagnostics, 'reload:incomplete-animations');
			trace('[psych-skin] incomplete note animations for ' + descriptor.key + ' in ' + descriptor.ownerRoot);
			return false;
		}
		note.psychSkinUsesNativeDefaultFallback = descriptor.nativeDefaultFallback;
		markDiagnostic(diagnostics, 'reload:read-current-visual');
		var oldAnim = note.animation.curAnim == null ? null : note.animation.curAnim.name;
		var oldScaleY = note.scale.y;
		if (pixel) {
			markDiagnostic(diagnostics, 'reload:pixel-sheet');
			var bitmap = FNFAssets.getBitmapData(note.isSustainNote ? descriptor.endsImage : descriptor.image);
			note.loadGraphic(bitmap, true, Std.int(bitmap.width / 4), Std.int(bitmap.height / (note.isSustainNote ? 2 : 5)));
			if (note.isSustainNote) note.originalHeight = bitmap.height / 2;
			note.setGraphicSize(Std.int(note.width * PlayState.daPixelZoom));
			if (note.isSustainNote) {
				note.offsetX += note.psychLastNoteOffX;
				note.psychLastNoteOffX = (note.width - 7) * (PlayState.daPixelZoom / 2);
				note.offsetX -= note.psychLastNoteOffX;
			}
			if (note.isSustainNote) {
				note.animation.add('holdend', [lane + 4], 24, true);
				note.animation.add('hold', [lane], 24, true);
			} else note.animation.add('Scroll', [lane + 4], 24, true);
		} else {
			markDiagnostic(diagnostics, 'reload:install-atlas');
			note.frames = frames;
			if (note.isSustainNote) {
				var endPrefix = color + ' hold end';
				if (color == 'purple' && !hasPrefix(frames, endPrefix)) endPrefix = 'pruple end hold';
				note.animation.addByPrefix('holdend', endPrefix, 24, true);
				note.animation.addByPrefix('hold', color + ' hold piece', 24, true);
			} else note.animation.addByPrefix('Scroll', color + '0', 24, true);
			note.setGraphicSize(Std.int(note.width * 0.7));
		}
		markDiagnostic(diagnostics, 'reload:geometry');
		note.antialiasing = !pixel;
		if (note.isSustainNote) note.scale.y = oldScaleY;
		note.resetPsychVisualOffset();
		if (!note.isSustainNote) {
			note.centerOffsets();
			note.centerOrigin();
		}
		markDiagnostic(diagnostics, 'reload:hitbox');
		note.updateHitbox();
		if (note.sourceTimingMode == 1 && note.isSustainNote && !note.psychSustainLayoutInitialized)
			note.psychSustainStartWidth = note.width;
		markDiagnostic(diagnostics, 'reload:animation');
		if (oldAnim != null && note.animation.exists(oldAnim)) note.animation.play(oldAnim, true);
		else note.animation.play(note.isSustainNote ? 'holdend' : 'Scroll', true);
		markDiagnostic(diagnostics, 'reload:complete');
		return true;
	}

	public static function reloadStrum(strum:StrumNote, authored:String, ownerRoot:String,
		chartSkin:String, pixel:Bool, postfix:String):Bool {
		var skin = authored == null || authored == '' ? (chartSkin == null || chartSkin == '' ? DEFAULT_SKIN : chartSkin) : authored;
		var result = PsychSkinResolver.resolveDetailed(skin, ownerRoot, pixel, postfix);
		if (result.descriptor == null) {
			trace('[psych-skin] receptor ' + result.reason);
			return false;
		}
		var lane = ((strum.ID % 4) + 4) % 4;
		var descriptor = result.descriptor;
		var frames = pixel ? null : atlas(descriptor);
		if (!validStrum(descriptor, frames, lane)) {
			trace('[psych-skin] incomplete receptor animations for ' + descriptor.key + ' in ' + descriptor.ownerRoot);
			return false;
		}
		strum.psychSkinUsesNativeDefaultFallback = descriptor.nativeDefaultFallback;
		var oldAnim = strum.animation.curAnim == null ? null : strum.animation.curAnim.name;
		if (pixel) {
			var bitmap = FNFAssets.getBitmapData(descriptor.image);
			strum.loadGraphic(bitmap, true, Std.int(bitmap.width / 4), Std.int(bitmap.height / 5));
			strum.animation.add('static', [lane]);
			strum.animation.add('pressed', [lane + 4, lane + 8], 12, false);
			strum.animation.add('confirm', [lane + 12, lane + 16], lane == 2 ? 12 : 24, false);
			strum.setGraphicSize(Std.int(strum.width * PlayState.daPixelZoom));
		} else {
			strum.frames = frames;
			strum.animation.addByPrefix('static', receptorIdle[lane]);
			strum.animation.addByPrefix('pressed', directions[lane] + ' press', 24, false);
			strum.animation.addByPrefix('confirm', directions[lane] + ' confirm', 24, false);
			strum.setGraphicSize(Std.int(strum.width * 0.7));
		}
		strum.antialiasing = !pixel;
		strum.isPixel = pixel;
		strum.updateHitbox();
		strum.normalSize = strum.scale.x;
		strum.playAnim(oldAnim != null && strum.animation.exists(oldAnim) ? oldAnim : 'static', true);
		return true;
	}

	static function atlas(descriptor:PsychSkinDescriptor):FlxAtlasFrames {
		try {
			return DynamicAtlasFrames.fromSparrow(descriptor.image, descriptor.metadata);
		} catch (error:Dynamic) {
			trace('[psych-skin] invalid atlas ' + descriptor.key + ' in ' + descriptor.ownerRoot + ': ' + error);
			return null;
		}
	}

	static function validNote(descriptor:PsychSkinDescriptor, frames:FlxAtlasFrames,
		color:String, sustain:Bool):Bool {
		if (descriptor.pixel) {
			try {
				var bitmap = FNFAssets.getBitmapData(sustain ? descriptor.endsImage : descriptor.image);
				return bitmap != null && bitmap.width >= 4 && bitmap.height >= (sustain ? 2 : 5)
					&& bitmap.width % 4 == 0 && bitmap.height % (sustain ? 2 : 5) == 0;
			} catch (error:Dynamic) {
				trace('[psych-skin] invalid pixel sheet ' + descriptor.key + ': ' + error);
				return false;
			}
		}
		return sustain ? hasPrefix(frames, color + ' hold piece')
			&& (hasPrefix(frames, color + ' hold end') || color == 'purple' && hasPrefix(frames, 'pruple end hold'))
			: hasPrefix(frames, color + '0');
	}

	static function validStrum(descriptor:PsychSkinDescriptor, frames:FlxAtlasFrames, lane:Int):Bool {
		if (descriptor.pixel) {
			try {
				var bitmap = FNFAssets.getBitmapData(descriptor.image);
				return bitmap != null && bitmap.width >= 4 && bitmap.height >= 5
					&& bitmap.width % 4 == 0 && bitmap.height % 5 == 0;
			} catch (error:Dynamic) {
				trace('[psych-skin] invalid pixel sheet ' + descriptor.key + ': ' + error);
				return false;
			}
		}
		return hasPrefix(frames, receptorIdle[lane])
			&& hasPrefix(frames, directions[lane] + ' press')
			&& hasPrefix(frames, directions[lane] + ' confirm');
	}

	static function hasPrefix(frames:FlxAtlasFrames, prefix:String):Bool {
		if (frames == null) return false;
		for (frame in frames.frames)
			if (frame.name != null && StringTools.startsWith(frame.name, prefix)) return true;
		return false;
	}

	static function markDiagnostic(enabled:Bool, phase:String):Void {
		if (enabled)
			RuntimeSmokeHarness.setPsychSkinDiagnosticPhase(phase);
	}
}
