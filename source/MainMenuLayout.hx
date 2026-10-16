package;

import MenuStyle.MenuCardLook;

/**
	Layout of the main menu's front page.

	The entries are a stack of large cards on the left, centred in the space
	between the header and the footer, with the highlighted card open. What the
	highlighted entry leads to is a panel beside the stack, sized to its text.
*/
class MainMenuLayout {
	public static inline var LEFT:Int = 48;
	public static inline var WIDTH:Int = 560;
	public static inline var IDLE:Int = 64;
	public static inline var SELECTED:Int = 120;
	public static inline var GAP:Int = 8;
	/** Space for the stack: below the engine's name, above the footer. */
	public static inline var REGION_TOP:Int = 150;
	public static inline var REGION_BOTTOM:Int = 640;
	public static inline var STAGE_X:Int = LEFT + WIDTH + 48;
	public static inline var STAGE_WIDTH:Int = 576;
	/** Most label and value rows the context panel can show. */
	public static inline var FACT_ROWS:Int = 6;

	public static var LOOK:MenuCardLook = {idle: IDLE, selected: SELECTED, titleSize: 32, selectedTitleSize: 40,
		titleTop: 14, titleLift: 6, captionTop: 70, captionSize: 16};

	/** Height of the space the stack lives in. */
	public static function room(screenHeight:Float):Float return screenHeight - (720 - REGION_BOTTOM) - REGION_TOP;

	/** Top of the stack: centred in its region, never above it. */
	public static function stackStart(count:Int, screenHeight:Float):Float
		return REGION_TOP + Math.max(0, (room(screenHeight) - MenuStyle.stackHeight(count, IDLE, SELECTED, GAP)) / 2);

	/** Top of the card at `index` when `selected` is the chosen row. A stack
	 * taller than its region scrolls to keep the selection in the middle. */
	public static function rowTop(index:Int, selected:Int, count:Int, screenHeight:Float):Float
		return MenuStyle.stackTop(index, selected, stackStart(count, screenHeight), IDLE, SELECTED, GAP)
			- MenuStyle.stackScroll(selected, count, IDLE, SELECTED, GAP, room(screenHeight));

	/** Whether the card at `index` is drawn at all in that layout. */
	public static function shown(index:Int, selected:Int, count:Int, screenHeight:Float):Bool
		return MenuStyle.fitsRegion(rowTop(index, selected, count, screenHeight), index == selected ? SELECTED : IDLE,
			REGION_TOP - 8, screenHeight - (720 - REGION_BOTTOM));

	/** The most rows that are all drawn wherever the selection is. */
	public static function capacity(screenHeight:Float):Int {
		var count = 1;
		while (count < 32) {
			var next = count + 1;
			for (selected in 0...next)
				for (index in 0...next)
					if (!shown(index, selected, next, screenHeight))
						return count;
			count = next;
		}
		return count;
	}

	/** Top of the context panel: level with the highlighted card so the two read
	 * as one, pulled up only as far as needed to stay above the footer. */
	public static function stageTop(selectedTop:Float, panelHeight:Float, screenHeight:Float):Float {
		var limit = screenHeight - (720 - REGION_BOTTOM) - panelHeight;
		return Math.max(REGION_TOP - 20, Math.min(selectedTop, limit));
	}
}
