package;

/** Older NV keeps these popup switches on PlayState. Route explicit writes
 * into the existing HUD instead of creating a second popup renderer. */
class NightmareVisionLegacyHudControls {
	public var showRating(get, set):Bool;
	public var showCombo(get, set):Bool;
	var ratingOverride:Null<Bool>;
	var comboOverride:Null<Bool>;
	var hud:Dynamic;
	var released:Bool = false;

	public function new() {}

	public function bind(target:Dynamic):Void {
		requireActive();
		if (target == null) throw '[nightmare-vision-hud] Missing popup target';
		hud = target;
		if (ratingOverride != null) applyRating(ratingOverride);
		if (comboOverride != null) applyCombo(comboOverride);
	}

	function get_showRating():Bool {requireActive(); return ratingOverride == null ? true : ratingOverride;}
	function set_showRating(value:Bool):Bool {
		requireActive(); ratingOverride = value;
		if (hud != null) applyRating(value);
		return value;
	}
	function get_showCombo():Bool {requireActive(); return comboOverride == null ? true : comboOverride;}
	function set_showCombo(value:Bool):Bool {
		requireActive(); comboOverride = value;
		if (hud != null) applyCombo(value);
		return value;
	}
	function applyRating(value:Bool):Void Reflect.setProperty(hud, 'showRating', value);
	function applyCombo(value:Bool):Void {
		// Legacy showCombo gates digits too; modern PsychHUD uses showRatingNum.
		Reflect.setProperty(hud, 'showCombo', value);
		Reflect.setProperty(hud, 'showRatingNum', value);
	}
	function requireActive():Void {
		if (released) throw '[nightmare-vision-hud] Legacy popup owner has been released';
	}
	public function release():Void {
		released = true;
		hud = null;
		ratingOverride = comboOverride = null;
	}
}
