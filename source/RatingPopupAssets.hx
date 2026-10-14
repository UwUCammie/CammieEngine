package;

/**
	Image choices for the rating and combo popups of one UI pack, worked out
	once per song instead of on every note hit.
**/
class RatingPopupAssets {
	/** Every rating name the popup can show. */
	public static final RATINGS:Array<String> = ['sick', 'good', 'bad', 'shit', 'wayoff', 'miss'];

	public final uses:String;
	public final isPixel:Bool;
	/** Library epoch the paths were resolved in. A later import can add or
		remove pack images, so the owner rebuilds when it moves. */
	public final epoch:Int;
	final digits:Array<String> = [];

	public function new(uses:String, isPixel:Bool, exists:String->Bool, epoch:Int = 0) {
		this.uses = uses;
		this.isPixel = isPixel;
		this.epoch = epoch;
		for (digit in 0...10)
			digits.push(digitPath(uses, Std.string(digit), isPixel, exists));
	}

	/** The pack's own digit wins, then the stock pixel or stock digit. */
	public static function digitPath(uses:String, numeral:String, isPixel:Bool, exists:String->Bool):String {
		var packed = 'assets/images/custom_ui/ui_packs/' + uses + '/num' + numeral + (isPixel ? '-pixel' : '') + '.png';
		if (exists(packed))
			return packed;
		return isPixel ? 'assets/images/weeb/pixelUI/num' + numeral + '-pixel.png'
			: 'assets/images/num' + numeral + '.png';
	}

	public inline function matches(uses:String, isPixel:Bool, epoch:Int = 0):Bool {
		return this.uses == uses && this.isPixel == isPixel && this.epoch == epoch;
	}

	/** Path for one character of the combo text, or null when it is not a
		digit and the caller has to resolve it the long way. */
	public function digit(numeral:String):Null<String> {
		if (numeral == null || numeral.length != 1)
			return null;
		var index = numeral.charCodeAt(0) - '0'.code;
		return index < 0 || index > 9 ? null : digits[index];
	}

	/** Hand every digit image to `retain` once. A missing image is skipped so
		one bad pack file cannot stop the rest from loading. */
	public function preload(retain:String->Void):Int {
		var done = 0;
		var seen:Map<String, Bool> = new Map();
		for (path in digits) {
			if (seen.exists(path))
				continue;
			seen.set(path, true);
			try {
				retain(path);
				done++;
			} catch (_:Dynamic) {}
		}
		return done;
	}
}
