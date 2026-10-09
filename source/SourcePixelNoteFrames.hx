package;

/** Shared Psych-family pixel sheet geometry and frame-index animations. */
class SourcePixelNoteFrames {
	public static function install(sprite:Dynamic, graphic:Dynamic, rows:Int, zoom:Float):Bool {
		if (graphic == null || graphic.width < 4 || graphic.height < rows) return false;
		sprite.loadGraphic(graphic, true, Std.int(graphic.width / 4), Std.int(graphic.height / rows));
		sprite.setGraphicSize(Std.int(sprite.width * zoom));
		return true;
	}

	public static function noteAnimations(sprite:Dynamic, lane:Int, sustain:Bool, aliases:Bool = false):Void {
		if (sustain) {
			sprite.animation.add('holdend', [lane + 4], aliases ? 30 : 24, true);
			sprite.animation.add('hold', [lane], aliases ? 30 : 24, true);
		} else sprite.animation.add('Scroll', [lane + 4], aliases ? 30 : 24, true);
		if (aliases) {
			var colors = ['purple', 'blue', 'green', 'red'];
			for (i in 0...4) {
				if (sustain) {
					sprite.animation.add(colors[i] + 'holdend', [i + 4], 30, true);
					sprite.animation.add(colors[i] + 'hold', [i], 30, true);
				} else sprite.animation.add(colors[i] + 'Scroll', [i + 4], 30, true);
			}
		}
	}

	public static function receptorAnimations(sprite:Dynamic, lane:Int, aliases:Bool = false):Void {
		sprite.animation.add('static', [lane]);
		sprite.animation.add('pressed', [lane + 4, lane + 8], 12, false);
		sprite.animation.add('confirm', [lane + 12, lane + 16], lane == 2 ? 12 : 24, false);
		if (aliases) {
			var colors = ['purple', 'blue', 'green', 'red'];
			for (i in 0...4) sprite.animation.add(colors[i], [i + 4]);
		}
	}
}
