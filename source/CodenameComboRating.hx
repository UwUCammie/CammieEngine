package;

/** Source ComboRating's four constructor fields. FlxColor is an Int-backed
 * abstract in this engine; keep the color value script-writable as Int.
 * Donor TranslationUtil lookup requires a separate selected-owner locale
 * resolver; preserve the authored fallback label until that exists. */
@:keep
class CodenameComboRating {
	public var percent:Float;
	public var rating:String;
	public var color:Int;
	public var maxMisses:Float;

	public function new(?percent:Float, ?rating:String, ?color:Int, ?misses:Float) {
		maxMisses = misses == null || Math.isNaN(misses) ? Math.POSITIVE_INFINITY : misses;
		this.percent = percent;
		this.rating = rating;
		this.color = color;
	}
}
