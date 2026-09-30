package;

import flixel.math.FlxPoint;

/** Mutable scene callback for Codename's automatic character-line camera.
 * strumLine shares the live input model when available; note/receptor groups
 * and source signals are not yet implemented by that model. */
@:keep
class CodenameCameraMoveEvent extends CodenameGameEvent {
	public var position:Dynamic;
	public var strumLine:Dynamic;
	public var focusedCharacters:Int;
	public var lineIndex:Int;

	public function new(position:FlxPoint, strumLine:Dynamic, focusedCharacters:Int, lineIndex:Int) {
		super();
		this.position = new CodenameCameraMovePoint(position);
		this.strumLine = strumLine;
		this.focusedCharacters = focusedCharacters;
		this.lineIndex = lineIndex;
	}
}
