package;

/** A lightweight descriptor shared by the Psych and Nightmare Vision score ledgers.

	`hits` models Psych's per-rating counter. `counter` names the owning PlayState
	field used by Nightmare Vision. The optional owner passed to `increase` keeps
	this class independent from either engine's PlayState implementation.
*/
@:keep
class SourceRating {
	public var name:String;
	public var image:String;
	public var hitWindow:Null<Float>;
	public var ratingMod:Float = 1;
	public var score:Int = 350;
	public var noteSplash:Bool = true;
	public var hits:Int = 0;
	public var counter:String;
	/** Typed owner callback for counters that are not instance fields. */
	public var counterChanged:Null<String->Int->Void>;

	/** Nightmare Vision's default descriptor for a rating name. */
	public function new(name:String, ?hitWindow:Float) {
		this.name = name;
		this.image = name;
		this.counter = name + 's';
		this.hitWindow = hitWindow == null ? defaultWindow(name) : hitWindow;

		switch (name) {
			case 'epic':
				ratingMod = 1;
				score = 500;
				noteSplash = true;
			case 'sick':
				ratingMod = 1;
				score = 350;
				noteSplash = true;
			case 'good':
				ratingMod = 0.7;
				score = 200;
				noteSplash = false;
			case 'bad':
				ratingMod = 0.4;
				score = 100;
				noteSplash = false;
			case 'shit':
				ratingMod = 0;
				score = 50;
				noteSplash = false;
		}
	}

	/** Match the Psych default list and its per-rating hit counters. */
	public static function psychDefaults(?prefs:Dynamic):Array<SourceRating> {
		return [
			psychRating('sick', prefs, 45, 1, 350, true),
			psychRating('good', prefs, 90, 0.67, 200, false),
			psychRating('bad', prefs, 135, 0.34, 100, false),
			psychRating('shit', prefs, 0, 0, 50, false)
		];
	}

	/** Match Nightmare Vision's defaults and optional first-position Epic rank. */
	public static function nightmareDefaults(?prefs:Dynamic, ?epic:Bool):Array<SourceRating> {
		var includeEpic = epic == null ? boolPreference(prefs, 'useEpicRankings', true) : epic;
		var ratings:Array<SourceRating> = [];
		if (includeEpic) ratings.push(nightmareRating('epic', prefs, 22.5));
		ratings.push(nightmareRating('sick', prefs, 45));
		ratings.push(nightmareRating('good', prefs, 90));
		ratings.push(nightmareRating('bad', prefs, 135));
		ratings.push(nightmareRating('shit', prefs, 0));
		return ratings;
	}

	/** Construct one detached NV rating using the supplied owner preference view.
	 * The donor constructor maps a missing window to zero and then applies the
	 * name-based score, modifier and splash defaults. */
	public static function nightmareConstructor(name:String, prefs:Dynamic):SourceRating {
		var rating = new SourceRating(name);
		rating.hitWindow = readWindow(prefs, name, 0);
		return rating;
	}

	/** Inclusive ordered thresholds; the final descriptor catches every later hit. */
	public static function judge(ratings:Array<SourceRating>, diff:Float):Null<SourceRating> {
		if (ratings == null || ratings.length == 0) return null;
		for (index in 0...ratings.length - 1) {
			var rating = ratings[index];
			if (rating != null && diff <= rating.hitWindow) return rating;
		}
		return ratings[ratings.length - 1];
	}

	/** Increment this descriptor and, when supplied, its NV owner counter. */
	public function increase(amount:Int = 1, ?owner:Dynamic):Void {
		hits += amount;
		if (counter == null || counter.length == 0) return;
		if (counterChanged != null) {
			counterChanged(counter, amount);
			return;
		}
		if (owner == null) return;
		var current:Dynamic = Reflect.getProperty(owner, counter);
		var previous:Int = current == null ? 0 : Std.int(current);
		Reflect.setProperty(owner, counter, previous + amount);
	}

	/** FlxStringUtil's default debugger precision is three decimal places. Keep
	 * this pure so source descriptors can be inspected without FlxG/debug state. */
	public function toString():String {
		var roundedMod = Math.fround(ratingMod * 1000) / 1000;
		return '(name: ' + name + ' | ratingMod: ' + Std.string(roundedMod)
			+ ' | score: ' + Std.string(score) + ')';
	}

	static function psychRating(name:String, prefs:Dynamic, defaultWindow:Float,
		ratingMod:Float, score:Int, noteSplash:Bool):SourceRating {
		var rating = new SourceRating(name, readWindow(prefs, name, defaultWindow));
		rating.ratingMod = ratingMod;
		rating.score = score;
		rating.noteSplash = noteSplash;
		return rating;
	}

	static function nightmareRating(name:String, prefs:Dynamic, defaultWindow:Float):SourceRating
		return new SourceRating(name, readWindow(prefs, name, defaultWindow));

	static function readWindow(prefs:Dynamic, name:String, fallback:Float):Float {
		var source = preferenceSource(prefs);
		if (source == null) return fallback;
		var value:Dynamic = Reflect.getProperty(source, name + 'Window');
		if (value == null) return fallback;
		var parsed = Std.parseFloat(Std.string(value));
		return Math.isFinite(parsed) ? parsed : fallback;
	}

	static function boolPreference(prefs:Dynamic, name:String, fallback:Bool):Bool {
		var source = preferenceSource(prefs);
		if (source == null) return fallback;
		var value:Dynamic = Reflect.getProperty(source, name);
		return value == null ? fallback : value == true;
	}

	static function preferenceSource(prefs:Dynamic):Dynamic {
		if (prefs == null) return null;
		var data:Dynamic = Reflect.getProperty(prefs, 'data');
		return data == null ? prefs : data;
	}

	static function defaultWindow(name:String):Float return switch (name) {
		case 'epic': 22.5;
		case 'sick': 45;
		case 'good': 90;
		case 'bad': 135;
		case 'shit': 0;
		default: 0;
	};
}
