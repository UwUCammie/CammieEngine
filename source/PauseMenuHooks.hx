package;

/**
 * Optional hooks a song's script layer attaches to the native pause menu.
 * Leave actions ask first and a false answer keeps the menu open, which is how
 * source pause scripts replace or delay where Exit, Options and Restart go.
 * Any field may be null.
 */
class PauseMenuHooks {
	public static inline var EXIT = 'exit';
	public static inline var OPTIONS = 'options';
	public static inline var RESTART = 'restart';

	/** Asked before EXIT, OPTIONS or RESTART runs. */
	public var allowAction:String->Bool;
	/** The menu finished building. */
	public var created:Void->Void;
	/** The item list was rebuilt. */
	public var regenerated:Void->Void;
	/** The selection moved to the given index; false skips the highlight refresh. */
	public var selectionChanged:Int->Bool;
	public var update:Float->Void;
	/** The menu is closing; release script resources here. */
	public var destroy:Void->Void;

	public function new() {}

	public inline function allows(action:String):Bool
		return allowAction == null || allowAction(action);
}
