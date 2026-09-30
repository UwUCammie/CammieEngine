package;

/** Typed property access for the generic Codename line object from HScript. */
@:keep
class CodenameInputLineScriptAccess {
	public static function getEffectiveCpu<T>(line:CodenameInputLine<T>):Bool
		return line.cpu || line.botplay;

	public static function getCharacters<T>(line:CodenameInputLine<T>):Array<T>
		return line.characters;

	public static function setCharacters<T>(line:CodenameInputLine<T>, value:Array<T>):Void
		line.characters = value;

	public static function getNotes<T>(line:CodenameInputLine<T>):CodenameStrumlineNoteCollection
		return line.notes;
}
