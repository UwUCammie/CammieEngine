package;

/** Native text editing with keyboard-owned focus, including clipboard and Unicode. */
class FreeplaySearchField extends flixel.text.FlxInputText {
	override public function update(elapsed:Float):Void {
		// Keep caret timing and selection current without pointer focus stealing.
		var shown = visible; visible = false; super.update(elapsed); visible = shown;
	}
}
