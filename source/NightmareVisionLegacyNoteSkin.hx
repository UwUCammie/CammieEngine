package;

import flixel.math.FlxPoint;
import nightmarevision.modchart.NightmareVisionModchartVector;

/** Historical noteskin startup uses the shared script module and main registry. */
class NightmareVisionLegacyNoteSkin {
	public var script(default, null):NightmareVisionScriptModule;
	public var textures(default, null):Array<String> = ['NOTE_assets', 'NOTE_assets'];
	public var arrowSkin(default, null):String;

	public static function offsets(keys:Int):Array<FlxPoint> {
		return [for (_ in 0...keys) new FlxPoint()];
	}

	public static function positionOffset(kind:String, direction:Int, sustain:Bool,
		notes:Array<FlxPoint>, receptors:Array<FlxPoint>, sustains:Array<FlxPoint>, out:NightmareVisionModchartVector):NightmareVisionModchartVector {
		out.setTo(0, 0, 0);
		if (kind != 'note' && kind != 'receptor') return out;
		var point = kind == 'receptor' ? receptors[direction] : notes[direction];
		out.x = point.x; out.y = point.y;
		if (kind == 'note' && sustain) {
			out.x += sustains[direction].x; out.y += sustains[direction].y;
		}
		return out;
	}

	public function new(path:Null<String>, load:String->NightmareVisionScriptModule,
		register:NightmareVisionScriptModule->Void, notes:Array<FlxPoint>, receptors:Array<FlxPoint>, sustains:Array<FlxPoint>) {
		if (path == null) return;
		script = load(path);
		if (script == null) return;
		if (script.parsingFailed()) {
			script.destroy();
			script = null;
			return;
		}
		script.callValue('offset', [notes, receptors, sustains]);
		register(script);
		textures = [cast script.callValue('bfSkin', []), cast script.callValue('dadSkin', [])];
		arrowSkin = cast script.callValue('arrowSkin', []);
	}
}
