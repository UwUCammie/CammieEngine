package;

/** Sizes of the library popup, kept free of display objects for checks. */
class LibraryMenuLayout {
	public static inline var PANEL_WIDTH:Int = 760;
	public static inline var PANEL_HEIGHT:Int = 520;
	public static inline var ROW_PITCH:Int = 40;
	public static inline var VISIBLE_ROWS:Int = 7;

	/** Top of the first choice inside the panel, lower when a card is shown. */
	public static function rowsTop(hasCard:Bool):Int return hasCard ? 132 : 72;
	/** First choice shown so the selection stays in view, three from the top when it can. */
	public static function firstVisible(selected:Int, count:Int, visible:Int = VISIBLE_ROWS):Int
		return Std.int(Math.max(0, Math.min(selected - 3, count - visible)));
}
