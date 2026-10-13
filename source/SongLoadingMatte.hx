package;

import haxe.io.Bytes;

/** Cuts the loading artwork out of its flat chartreuse backdrop.
 *
 * The cut is made once on the artwork's own pixels, before any scaling. Doing
 * it on the scaled picture left a rim, because smoothing had already mixed the
 * backdrop into every outline. Pixels are four bytes each: alpha, red, green,
 * blue. */
class SongLoadingMatte {
	public static inline var KEY_RED:Int = 202;
	public static inline var KEY_GREEN:Int = 255;
	public static inline var KEY_BLUE:Int = 77;
	/** Colour distance, of 0..1 per channel, below which a pixel is backdrop. */
	public static inline var KEY_DISTANCE:Float = 0.07;
	/** Pixels around the backdrop that can still carry some of it. */
	public static inline var EDGE:Int = 3;

	static inline function distance(red:Int, green:Int, blue:Int):Float {
		var r = (red - KEY_RED) / 255; var g = (green - KEY_GREEN) / 255; var b = (blue - KEY_BLUE) / 255;
		return Math.sqrt(r * r + g * g + b * b);
	}

	/** Coverage 0..1 of a rim pixel that mixes the backdrop with artwork.
	 *
	 * Outlines are near black, so a rim pixel is mostly a darker backdrop and
	 * its channels keep the backdrop's proportions. The most backdrop it could
	 * hold, without leaving a negative colour behind, is then taken out. A pixel
	 * with proportions of its own is artwork and stays whole. */
	public static function coverage(red:Int, green:Int, blue:Int):Float {
		var length = Math.sqrt(red * red + green * green + blue * blue);
		if (length < 1) return 1;
		var keyLength = Math.sqrt(KEY_RED * KEY_RED + KEY_GREEN * KEY_GREEN + KEY_BLUE * KEY_BLUE);
		var alike = (red * KEY_RED + green * KEY_GREEN + blue * KEY_BLUE) / (length * keyLength);
		if (alike < 0.97) return 1;
		var share = Math.min(1, Math.min(red / KEY_RED, Math.min(green / KEY_GREEN, blue / KEY_BLUE)));
		return 1 - share;
	}

	/** Mark every pixel within EDGE pixels of a marked one, across then down. */
	static function grow(mask:Bytes, width:Int, height:Int):Bytes {
		var count = width * height;
		var across = Bytes.alloc(count);
		for (y in 0...height) {
			var row = y * width; var reach = -1;
			for (x in 0...width) { if (mask.get(row + x) == 1) reach = x + EDGE; if (x <= reach) across.set(row + x, 1); }
			reach = width + EDGE;
			var x = width - 1;
			while (x >= 0) { if (mask.get(row + x) == 1) reach = x - EDGE; if (x >= reach) across.set(row + x, 1); x--; }
		}
		var near = Bytes.alloc(count);
		for (x in 0...width) {
			var reach = -1;
			for (y in 0...height) { if (across.get(y * width + x) == 1) reach = y + EDGE; if (y <= reach) near.set(y * width + x, 1); }
			reach = height + EDGE;
			var y = height - 1;
			while (y >= 0) { if (across.get(y * width + x) == 1) reach = y - EDGE; if (y >= reach) near.set(y * width + x, 1); y--; }
		}
		return near;
	}

	/** Make the backdrop transparent, clean the rim around it and feather the
	 * cut edge, in place. */
	public static function apply(pixels:Bytes, width:Int, height:Int):Void {
		var count = width * height;
		if (width <= 0 || height <= 0 || pixels.length < count * 4) return;
		// 1 where the pixel is backdrop, or was found to be mostly backdrop.
		var gone = Bytes.alloc(count);
		for (i in 0...count) {
			var at = i * 4;
			if (distance(pixels.get(at + 1), pixels.get(at + 2), pixels.get(at + 3)) < KEY_DISTANCE) { gone.set(i, 1); pixels.setInt32(at, 0); }
		}
		// 1 where a pixel has been looked at as part of the rim.
		var rim = Bytes.alloc(count);
		// A soft edge in the artwork can be wider than one rim. Pixels the first
		// round found to be mostly backdrop extend the backdrop for the second.
		for (round in 0...2) {
			var near = grow(gone, width, height);
			for (i in 0...count) {
				if (near.get(i) == 0 || gone.get(i) == 1 || rim.get(i) == 1) continue;
				rim.set(i, 1);
				var at = i * 4;
				var red = pixels.get(at + 1); var green = pixels.get(at + 2); var blue = pixels.get(at + 3);
				var kept = coverage(red, green, blue);
				if (kept >= 0.999) continue;
				if (kept < 0.4) gone.set(i, 1);
				if (kept <= 0.02) { pixels.setInt32(at, 0); continue; }
				// Take the backdrop's share back out of the colour that remains.
				var share = 1 - kept;
				pixels.set(at, Std.int(pixels.get(at) * kept));
				pixels.set(at + 1, clamp((red - KEY_RED * share) / kept));
				pixels.set(at + 2, clamp((green - KEY_GREEN * share) / kept));
				pixels.set(at + 3, clamp((blue - KEY_BLUE * share) / kept));
			}
		}
		// Feather: along the cut, each pixel takes the average opacity of its
		// neighbourhood when that is lower. The edge melts into the screen and
		// artwork away from the cut is untouched.
		var alpha = Bytes.alloc(count);
		for (i in 0...count) alpha.set(i, pixels.get(i * 4));
		for (y in 0...height) for (x in 0...width) {
			var i = y * width + x;
			if (rim.get(i) == 0 || alpha.get(i) == 0) continue;
			var sum = 0; var cells = 0;
			for (dy in -1...2) {
				var ny = y + dy; if (ny < 0 || ny >= height) continue;
				for (dx in -1...2) { var nx = x + dx; if (nx < 0 || nx >= width) continue; sum += alpha.get(ny * width + nx); cells++; }
			}
			var soft = Std.int(sum / cells);
			if (soft < alpha.get(i)) pixels.set(i * 4, soft);
		}
	}

	static inline function clamp(value:Float):Int return value <= 0 ? 0 : value >= 255 ? 255 : Std.int(value);
}
