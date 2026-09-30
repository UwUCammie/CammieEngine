package;

import haxe.ds.StringMap;

/** The timing-window presets used by Codename Engine's HitWindowData. */
enum abstract CodenameWindowPreset(Int) from Int to Int {
	var DEFAULT = 0;
	var CNE_CLASSIC = 1;
	var FNF_CLASSIC = 2;
	var FNF_VSLICE = 3;

	public function toString():String {
		return switch (cast this : CodenameWindowPreset) {
			case CNE_CLASSIC: "Codename (Classic)";
			case FNF_CLASSIC: "Funkin' (Week 7)";
			case FNF_VSLICE: "Funkin' (V-Slice)";
			case _: "Default";
		}
	}
}

/** Mutable counterpart of funkin.game.scoring.RatingManager.Rating. */
@:keep
class CodenameRating {
	public var name:String = "unknown";
	public var accuracy:Float = 0.0;
	public var window:Float = -1;
	public var score:Int = 0;
	public var health:Float = 0.023;
	public var splash:Bool = false;
	public var breaksCombo:Bool = false;
	public var hittable:Bool = true;

	public function new() {}
}

/**
 * Source-compatible note rating data and timing selection for imported
 * Codename charts and scripts. Keep this class independent of PlayState so
 * the scoring rules can be used by every Codename input path.
 */
@:keep
class CodenameRatingManager {
	/** Mirrors the upstream flag default; PlayState integration may sync it. */
	public static var SHITS_BREAK_COMBO:Bool = true;

	public var hitWindows:StringMap<Float>;
	public var ratingData:Array<CodenameRating> = [];
	public var lastHitWindow:Float = -1;

	public function new(?preset:CodenameWindowPreset):Void {
		var usedPreset:CodenameWindowPreset = preset != null ? preset : CodenameWindowPreset.DEFAULT;
		hitWindows = getWindows(usedPreset);
		initDefaultData(hitWindows);
	}

	/** Return the first rating whose inclusive timing window contains `time`. */
	public function judgeNote(time:Float):CodenameRating {
		for (rating in ratingData) {
			if (rating.hittable && rating.window > -1 && time <= rating.window)
				return rating;
		}
		return ratingData.length == 0 ? null : ratingData[ratingData.length - 1];
	}

	/** Project source judgements into the four-category Psych observer API. */
	public function psychJudgement(name:String, accuracy:Null<Float>):String {
		var standard = ['sick', 'good', 'bad', 'shit'];
		if (standard.indexOf(name) >= 0) return name;
		// Psych observers have four judgement categories. Group additional
		// source ratings by their accuracy value, using the source's current
		// standard tiers (and its built-in values if a tier was removed).
		// The original name, timing, score and accuracy stay on the source event.
		if (accuracy == null) {
			for (rating in ratingData) if (rating.name == name) accuracy = rating.accuracy;
		}
		if (accuracy == null || !Math.isFinite(accuracy)) return 'unknown';
		var thresholds:Array<Float> = [1, 0.75, 0.45, 0.25];
		for (rating in ratingData) {
			var index = standard.indexOf(rating.name);
			if (index >= 0) thresholds[index] = rating.accuracy;
		}
		var best = 'shit';
		var bestAccuracy = Math.NEGATIVE_INFINITY;
		for (index in 0...standard.length) {
			var threshold = thresholds[index];
			if (threshold <= accuracy && threshold > bestAccuracy) {
				best = standard[index];
				bestAccuracy = threshold;
			}
		}
		return best;
	}

	/** Initialize the four built-in Codename judgements from the selected windows. */
	public function initDefaultData(windows:StringMap<Float>):Void {
		inline function getWindow(name:String):Float
			return windows.exists(name) ? windows.get(name) : -1;

		addRating({name: "sick", window: getWindow("sick"), accuracy: 1, score: 300, splash: true});
		addRating({name: "good", window: getWindow("good"), accuracy: 0.75, score: 200, health: 0.015});
		addRating({name: "bad", window: getWindow("bad"), accuracy: 0.45, score: 100, health: 0});
		addRating({name: "shit", window: getWindow("shit"), accuracy: 0.25, score: 50, health: -0.05,
			breaksCombo: SHITS_BREAK_COMBO});
	}

	/** Add or replace a rating using RatingManager's source defaults. */
	public function addRating(data:Dynamic):Void {
		if (data == null) return;
		var rawName:Dynamic = Reflect.field(data, "name");
		if (rawName == null) return;

		var name:String = cast rawName;
		name = name.toLowerCase();
		var rawWindow:Dynamic = Reflect.field(data, "window");
		var window:Float = rawWindow != null
			? cast rawWindow
			: (hitWindows.exists(name) ? hitWindows.get(name) : -1);

		if (window > lastHitWindow) lastHitWindow = window;
		var newRating = new CodenameRating();
		newRating.name = name;
		newRating.window = window;
		newRating.accuracy = floatField(data, "accuracy", 1);
		newRating.score = intField(data, "score", 0);
		newRating.health = floatField(data, "health", 0.023);
		newRating.splash = boolField(data, "splash", false);
		newRating.breaksCombo = boolField(data, "breaksCombo", false);
		newRating.hittable = boolField(data, "hittable", true);

		var existingIndex = -1;
		for (i in 0...ratingData.length)
			if (ratingData[i].name == name)
				existingIndex = i;
		if (existingIndex >= 0)
			ratingData[existingIndex] = newRating;
		else
			ratingData.push(newRating);

		ratingData.sort((a, b) -> Reflect.compare(a.window, b.window));
	}

	public function removeRating(name:String):Void {
		if (name == null) return;
		name = name.toLowerCase();
		var toRemove = ratingData.filter(rating -> rating.name == name);
		for (rating in toRemove)
			ratingData.remove(rating);
	}

	public function getHitWindow(name:String):Float
		return hitWindows.exists(name) ? hitWindows.get(name) : -1;

	static function getWindows(preset:CodenameWindowPreset):StringMap<Float> {
		var windows = new StringMap<Float>();
		switch (preset) {
			case CodenameWindowPreset.CNE_CLASSIC:
				windows.set("sick", 50.0);
				windows.set("good", 187.5);
				windows.set("bad", 225.0);
				windows.set("shit", 250.0);
			case CodenameWindowPreset.FNF_CLASSIC:
				windows.set("sick", 33.334);
				windows.set("good", 125.0025);
				windows.set("bad", 150.003);
				windows.set("shit", 166.67);
			case CodenameWindowPreset.FNF_VSLICE:
				windows.set("sick", 45.0);
				windows.set("good", 90.0);
				windows.set("bad", 135.4);
				windows.set("shit", 180.0);
			case _:
				windows.set("sick", 37.8);
				windows.set("good", 75.6);
				windows.set("bad", 113.4);
				windows.set("shit", 180.0);
		}
		return windows;
	}

	static inline function floatField(data:Dynamic, name:String, fallback:Float):Float {
		var value:Dynamic = Reflect.field(data, name);
		return value == null ? fallback : cast value;
	}

	static inline function intField(data:Dynamic, name:String, fallback:Int):Int {
		var value:Dynamic = Reflect.field(data, name);
		return value == null ? fallback : cast value;
	}

	static inline function boolField(data:Dynamic, name:String, fallback:Bool):Bool {
		var value:Dynamic = Reflect.field(data, name);
		return value == null ? fallback : value == true;
	}
}
