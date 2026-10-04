package;

/** Owner-local view of Nightmare Vision's live gameplay ratings API. */
@:keep
class SourceRatingBindings {
	var host:Dynamic;
	var prefs:Dynamic;
	var isActive:Void->Bool;
	var resolveHost:Void->Dynamic;
	var released:Bool = false;

	public function new(host:Dynamic, prefs:Dynamic, ?isActive:Void->Bool,
		?resolveHost:Void->Dynamic) {
		this.host = host;
		this.prefs = prefs;
		this.isActive = isActive;
		this.resolveHost = resolveHost;
	}

	/** Install both source import spellings and bind construction by identity. */
	public static function installNightmare(interp:NightmareVisionScriptInterp,
		host:Dynamic, prefs:Dynamic, ?isActive:Void->Bool,
		?resolveHost:Void->Dynamic):SourceRatingBindings {
		if (interp == null) throw '[source-rating] Missing script interpreter';

		var old = interp.importBindings.get('funkin.game.Rating');
		if (Std.isOfType(old, SourceRatingBindings)) {
			interp.unbindConstructorFactory(old);
			(cast old:SourceRatingBindings).release();
		}

		var api = new SourceRatingBindings(host, prefs, isActive, resolveHost);
		interp.variables.set('Rating', api);
		interp.bindImport('Rating', api);
		interp.bindImport('funkin.game.Rating', api);
		interp.bindConstructorFactory(api, function(args:Array<Dynamic>):Dynamic {
			if (args == null || args.length == 0 || args[0] == null)
				throw '[source-rating] Rating requires a name';
			return api.newRating(Std.string(args[0]));
		}, api);
		return api;
	}

	/** Match NV's static Rating.judgeNote API; the current ratings list is read
	 * for every call so replacing or editing the host list remains visible. */
	public function judgeNote(_note:Dynamic, diff:Float = 0):Null<SourceRating>
		return judgeTime(diff);

	/** Match NV's static Rating.judgeTime API against this owner's live list. */
	public function judgeTime(time:Float = 0):Null<SourceRating> {
		var ratings = activeRatings();
		return ratings == null ? null : SourceRating.judge(ratings, time);
	}

	/** Construct a detached NV descriptor using this import owner's preferences. */
	public function newRating(name:String):SourceRating {
		if (released) throw '[source-rating] Rating API has been released';
		var rating = SourceRating.nightmareConstructor(name, prefs);
		rating.counterChanged = function(counter:String, amount:Int):Void {
			changeCounter(counter, amount);
		};
		return rating;
	}

	function activeRatings():Null<Array<SourceRating>> {
		var owner = currentHost();
		if (owner == null) return null;
		var ratings:Dynamic = null;
		try ratings = Reflect.getProperty(owner, 'ratingsData') catch (_:Dynamic) return null;
		if (!Std.isOfType(ratings, Array)) return null;
		return cast ratings;
	}

	function currentHost():Dynamic {
		if (released) return null;
		var owner:Dynamic = host;
		if (resolveHost != null) {
			try owner = resolveHost() catch (_:Dynamic) return null;
		}
		if (owner == null) return null;
		if (isActive != null) {
			var active = false;
			try active = isActive() catch (_:Dynamic) return null;
			if (!active) return null;
		}
		return owner;
	}

	function changeCounter(counter:String, amount:Int):Void {
		var owner = currentHost();
		if (owner == null) return;
		var callback:Dynamic = null;
		try callback = Reflect.field(owner, 'changeSourceRatingCounter') catch (_:Dynamic) return;
		if (Reflect.isFunction(callback)) Reflect.callMethod(owner, callback, [counter, amount]);
	}

	/** Break callbacks held by descriptors retained outside the interpreter. */
	public function release():Void {
		if (released) return;
		released = true;
		host = null;
		prefs = null;
		isActive = null;
		resolveHost = null;
	}
}
