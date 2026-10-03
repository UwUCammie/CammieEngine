package;

import flixel.FlxSprite;

/** Small layout and rating-shape operations identical in classic Psych and
	NMV's separate persistent popup renderers. */
class PsychRatingPresentationCommon {
	public static function positionRating(sprite:FlxSprite, placement:Float, offsets:Array<Int>):Void {
		sprite.x = placement - 40 + offsets[0];
		sprite.y -= 60 + offsets[1];
	}

	public static function positionComboDigit(sprite:FlxSprite, placement:Float,
		index:Int, offsets:Array<Int>):Void {
		sprite.x = placement + (43 * index) - 90 + offsets[2];
		sprite.y += 80 - offsets[3];
	}

	/** The shared host represents its judgement as a string; NMV callbacks read
		the source Psych rating's `name` and `image` fields. */
	public static function sourceRating(rating:Dynamic):Dynamic {
		if (Std.isOfType(rating, String)) {
			var name:String = cast rating;
			return {name:name, image:name};
		}
		return rating;
	}

	/** Project an accepted native host hit into the source Psych/NMV rating set.
	 * The host adds a wider `wayoff` window (and `ignoreVile` can call that same
	 * accepted hit `miss`), but source Rating.judgeNote has no such rows: after
	 * the configured hit windows it returns the final built-in `shit` row.
	 * This changes popup presentation only; host score and miss bookkeeping stay
	 * with the host. Call only for host judgement strings, never custom objects.
	 */
	public static function acceptedHostRating(rating:String):Dynamic {
		var sourceName = rating;
		if (rating != null) {
			switch (rating.toLowerCase()) {
				case 'wayoff' | 'miss': sourceName = 'shit';
			}
		}
		return {name:sourceName, image:sourceName};
	}

	public static function sourceRatingImage(rating:Dynamic):String {
		if (rating == null) throw '[psych-hud] Popup rating is missing';
		if (Std.isOfType(rating, String)) return cast rating;
		var value:Dynamic = Reflect.getProperty(rating, 'image');
		if (value == null) throw '[psych-hud] Popup rating has no image field';
		return Std.string(value);
	}
}
