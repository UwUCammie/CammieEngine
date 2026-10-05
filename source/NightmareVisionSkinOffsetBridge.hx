package;

import haxe.ds.Vector;
import flixel.math.FlxPoint;
import nightmarevision.modchart.NightmareVisionModchartObject;
import nightmarevision.modchart.NightmareVisionModchartVector;

/** Read the live source runtime vectors, including replacement skins and points. */
class NightmareVisionSkinOffsetBridge {
	public static function read(skin:NightmareVisionNoteSkin, kind:String, lane:Int,
		isSustain:Bool = false):NightmareVisionModchartVector {
		var result = new NightmareVisionModchartVector();
		if (skin == null) return result;
		var offsets = switch (kind) {
			case NightmareVisionModchartObject.NOTE: skin.noteOffsets;
			case NightmareVisionModchartObject.RECEPTOR: skin.receptorOffsets;
			case NightmareVisionModchartObject.NOTE_SPLASH: skin.splashOffsets;
			case NightmareVisionModchartObject.SUSTAIN_SPLASH: skin.sustainSplashOffsets;
			case 'sustainEnd': skin.susEndOffsets;
			default: null;
		};
		add(result, offsets, lane);
		if (kind == NightmareVisionModchartObject.NOTE && isSustain)
			add(result, skin.sustainOffsets, lane);
		return result;
	}

	static function add(result:NightmareVisionModchartVector, offsets:Vector<FlxPoint>, lane:Int):Void {
		if (offsets == null || offsets.length == 0) return;
		var point = offsets[((lane % offsets.length) + offsets.length) % offsets.length];
		if (point == null) return;
		result.x += point.x;
		result.y += point.y;
	}
}
