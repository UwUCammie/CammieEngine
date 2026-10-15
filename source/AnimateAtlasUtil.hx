package;

import animate.FlxAnimate;
import animate.FlxAnimateFrames;
import flixel.graphics.frames.FlxAtlasFrames;

/**
	Base-game helpers for Adobe Animate texture atlas sprites.

	Every engine family that ships Animate atlases (Psych, Nightmare Vision,
	Codename and V-Slice) registers its animations through the same three
	flixel-animate entry points: a frame label, a nested symbol, or a label
	tried first with the symbol as fallback.  Keeping that choice here gives
	native characters, imported character scripts and generated stage props
	one implementation instead of one copy per importer.

	flixel-animate's `combineAtlas` is an inline extern overload, which
	scripts cannot call, so the combine step lives here as a plain function.
**/
class AnimateAtlasUtil {
	/** Load the Animate export in `path` (the folder holding Animation.json).
	 * Returns null when the folder is not an Animate export, so a caller can
	 * fall back to a static graphic instead of crashing. */
	public static function folder(path:String):FlxAtlasFrames {
		if (path == null)
			return null;
		var clean = StringTools.replace(StringTools.trim(path), '\\', '/');
		while (StringTools.endsWith(clean, '/'))
			clean = clean.substr(0, clean.length - 1);
		if (clean == '' || !FNFAssets.exists(clean + '/Animation.json'))
			return null;
		return FlxAnimateFrames.fromAnimate(clean);
	}

	/** Merge Animate and Sparrow frame sets in order, skipping missing parts.
	 * The first part keeps its timeline as the default one, the same order
	 * V-Slice's multi-atlas characters use. */
	public static function combine(parts:Array<FlxAtlasFrames>):FlxAtlasFrames {
		if (parts == null)
			return null;
		var usable:Array<FlxAtlasFrames> = [];
		for (part in parts)
			if (part != null)
				usable.push(part);
		if (usable.length == 0)
			return null;
		if (usable.length == 1)
			return usable[0];
		return FlxAnimateFrames.combineAtlas(usable);
	}

	/**
		Register one Animate animation and report whether it exists afterwards.

		`animType` follows V-Slice's AnimationData: `framelabel` and `symbol`
		pick that lookup only.  Any other value (Psych and Nightmare Vision do
		not author one) tries the frame label first and the nested symbol when
		no such label exists.  A label or symbol that is missing leaves no
		animation behind, so nothing can wait on a zero-frame alias.
	**/
	public static function addAnimation(sprite:FlxAnimate, name:String, label:String, ?indices:Array<Int>,
			?frameRate:Float = 24, ?looped:Bool = false, ?animType:String, ?flipX:Bool = false,
			?flipY:Bool = false):Bool {
		if (sprite == null || sprite.anim == null || name == null || name == '' || label == null || label == '')
			return false;
		if (!sprite.isAnimate)
			return false;
		var controller = sprite.anim;
		var fps:Float = frameRate == null || frameRate <= 0 ? 24 : frameRate;
		var loop = looped == true;
		var useIndices = indices != null && indices.length > 0;
		var mode = animType == null ? '' : StringTools.trim(animType).toLowerCase();
		var useLabel = mode == 'framelabel';
		var useSymbol = mode == 'symbol';
		if (!useLabel && !useSymbol) {
			useLabel = hasFrameLabel(controller, label);
			useSymbol = !useLabel;
		}
		if (useLabel) {
			if (useIndices)
				controller.addByFrameLabelIndices(name, label, indices, fps, loop, flipX, flipY);
			else
				controller.addByFrameLabel(name, label, fps, loop, flipX, flipY);
		} else if (useSymbol) {
			if (useIndices)
				controller.addBySymbolIndices(name, label, indices, fps, loop, flipX, flipY);
			else
				controller.addBySymbol(name, label, fps, loop, flipX, flipY);
		}
		return controller.exists(name);
	}

	/** Whether any timeline the label lookup searches holds `label`.  The
	 * frame-label adders also search the timelines of atlases combined into
	 * this one, so a multi-atlas label outside the main document still counts
	 * as a label and is not mistaken for a symbol name. */
	static function hasFrameLabel(controller:animate.FlxAnimateController, label:String):Bool {
		if (controller.findFrameLabelIndices(label).length > 0)
			return true;
		for (timeline in controller.getCollectionTimelines())
			if (timeline != null && timeline.findFrameLabelIndices(label).length > 0)
				return true;
		return false;
	}
}
