package;

/** One hint in a footer bar: the key, and what it does. */
typedef MenuHint = {
	var key:String;
	var action:String;
}

/** How tall a card is and how its text sits; anything left out is Freeplay's. */
typedef MenuCardLook = {
	@:optional var idle:Int;
	@:optional var selected:Int;
	@:optional var titleSize:Int;
	@:optional var selectedTitleSize:Int;
	@:optional var titleTop:Float;
	@:optional var titleLift:Float;
	@:optional var captionTop:Float;
	@:optional var captionSize:Int;
	@:optional var captionLines:Int;
	@:optional var valueSize:Int;
	/** Room kept clear on the right of the title for the value. */
	@:optional var reserve:Int;
}

/** The Freeplay look as plain values: palette, fonts, sizes and the few rules
 * that turn a state into a colour or a position. Freeplay reads every one of
 * these, and the options, import and main menus read the same ones, so the
 * screens cannot drift apart. No display objects live here; MenuWidgets builds
 * with them. */
class MenuStyle {
	public static inline var FONT:String = 'assets/fonts/vcr.ttf';

	// Surfaces, darkest first.
	/** The dim laid over the menu background. */
	public static inline var SHADE:Int = 0xE6101622;
	/** The footer strip. */
	public static inline var BAR:Int = 0xFF101622;
	/** An idle card, and a detail card. */
	public static inline var CARD:Int = 0xFF182235;
	/** The selected card. */
	public static inline var CARD_SELECTED:Int = 0xFF354963;
	public static inline var CARD_ALPHA:Float = 0.78;
	/** How much opacity the selected card gains over an idle one. */
	public static inline var CARD_ALPHA_GAIN:Float = 0.22;
	public static inline var DETAIL_ALPHA:Float = 0.82;
	/** A popup panel over a dimmed menu. */
	public static inline var DIM:Int = 0xFF05080F;
	public static inline var PANEL:Int = 0xFF141C2C;
	public static inline var PANEL_ROW:Int = 0xFF2B3C57;
	public static inline var PANEL_RULE:Int = 0xFF3A4A66;
	/** A thin rule between footer hints. */
	public static inline var RULE:Int = 0xFF3A4A63;
	/** A switched-off toggle chip and an empty progress track. */
	public static inline var CHIP_OFF:Int = 0xFF2A3550;

	// Accents. Pink marks the selection and the title, teal a section, gold a key.
	public static inline var PINK:Int = 0xFFFF66B7;
	public static inline var TEAL:Int = 0xFF80E3D0;
	public static inline var GOLD:Int = 0xFFFFD166;
	/** A status or caution line. */
	public static inline var AMBER:Int = 0xFFFFC86A;
	/** A selected popup choice. */
	public static inline var CHOICE:Int = 0xFFFFD76A;

	// Text, brightest first.
	public static inline var WHITE:Int = 0xFFFFFFFF;
	public static inline var CREAM:Int = 0xFFFFF4DC;
	public static inline var TEXT:Int = 0xFFCFD8E5;
	public static inline var MUTED:Int = 0xFF9DB2CC;
	public static inline var DISABLED:Int = 0xFF8B97A8;

	// Sizes.
	public static inline var HEADING_SIZE:Int = 44;
	public static inline var TITLE_SIZE:Int = 22;
	public static inline var SELECTED_TITLE_SIZE:Int = 28;
	public static inline var BODY_SIZE:Int = 18;
	public static inline var SMALL_SIZE:Int = 14;
	public static inline var SECTION_SIZE:Int = 12;
	public static inline var HINT_SIZE:Int = 15;

	// Geometry shared by every screen.
	/** Height of the footer strip. */
	public static inline var BAR_HEIGHT:Int = 68;
	/** Left edge of the list, and the gutter on the far side. */
	public static inline var MARGIN:Int = 24;
	/** Top of the list, below the header. */
	public static inline var LIST_TOP:Int = 64;
	public static inline var ROW_HEIGHT:Int = 42;
	public static inline var SELECTED_HEIGHT:Int = 82;
	/** Width of the selected card's pink edge. */
	public static inline var STRIPE_WIDTH:Int = 5;
	public static inline var ACCENT_WIDTH:Int = 4;

	/** Fraction 0..1 clamped, so a stray tween value cannot leave the palette. */
	public static function clamp01(value:Float):Float
		return !Math.isFinite(value) ? 0 : Math.max(0, Math.min(1, value));

	/** Blend two opaque colours channel by channel; focus 0 is `from`, 1 is `to`. */
	public static function mix(from:Int, to:Int, focus:Float):Int {
		var amount = clamp01(focus);
		var r = Std.int(((from >> 16) & 255) + (((to >> 16) & 255) - ((from >> 16) & 255)) * amount);
		var g = Std.int(((from >> 8) & 255) + (((to >> 8) & 255) - ((from >> 8) & 255)) * amount);
		var b = Std.int((from & 255) + ((to & 255) - (from & 255)) * amount);
		return 0xFF000000 | (r << 16) | (g << 8) | b;
	}

	/** Card fill while it grows into the selected card. */
	public static function cardColor(focus:Float):Int return mix(CARD, CARD_SELECTED, focus);

	/** Card opacity while it grows into the selected card. */
	public static function cardAlpha(focus:Float):Float return CARD_ALPHA + CARD_ALPHA_GAIN * clamp01(focus);

	/** Title colour of a card in a list. */
	public static function titleColor(selected:Bool, disabled:Bool):Int
		return disabled ? DISABLED : (selected ? CREAM : TEXT);

	/** Title size of a card: the selected card's title is larger. */
	public static function titleScale(focus:Float, base:Int = TITLE_SIZE, selected:Int = SELECTED_TITLE_SIZE):Float
		return 1 + clamp01(focus) * (selected - base) / base;

	/** Top of a card in a stack that starts at `top`: cards below the selected
	 * one drop by its extra height. */
	public static function stackTop(position:Int, selectedPosition:Int, top:Float, idle:Int, selected:Int, gap:Int):Float
		return top + position * (idle + gap) + (position > selectedPosition ? selected - idle : 0);

	/** Height of a stack of `count` cards with one selected. */
	public static function stackHeight(count:Int, idle:Int, selected:Int, gap:Int):Float
		return count <= 0 ? 0 : (count - 1) * (idle + gap) + selected;

	/** How far a stack taller than its region scrolls to keep the selection in
	 * the middle; zero when it fits. */
	public static function stackScroll(selectedPosition:Int, count:Int, idle:Int, selected:Int, gap:Int, region:Float):Float {
		var total = stackHeight(count, idle, selected, gap);
		if (total <= region) return 0;
		var center = selectedPosition * (idle + gap) + selected / 2;
		return Math.max(0, Math.min(total - region, center - region / 2));
	}

	/** Whether a card sits wholly inside a region of the screen. */
	public static function fitsRegion(top:Float, height:Float, regionTop:Float, regionBottom:Float):Bool
		return top >= regionTop - 1 && top + height <= regionBottom + 1;

	/** Where a card sits in a list that keeps the selection in the middle of
	 * the screen: cards below the selected one drop by its extra height. */
	public static function rowTop(position:Int, selectedPosition:Int, screenHeight:Int,
		selectedHeight:Int = SELECTED_HEIGHT, offset:Float = 0):Float {
		var delta = position - selectedPosition;
		return screenHeight / 2 - selectedHeight / 2 + offset + delta * ROW_HEIGHT
			+ (delta > 0 ? selectedHeight - ROW_HEIGHT : 0);
	}

	/** Whether a card of this height sits wholly between the header and the footer. */
	public static function rowFits(top:Float, height:Float, screenHeight:Int):Bool
		return top >= LIST_TOP - 4 && top + height <= screenHeight - BAR_HEIGHT - 4;

	/** Text for a switch. */
	public static function switchLabel(on:Bool):String return on ? 'ON' : 'OFF';

	/** Colour of a switch's label. */
	public static function switchColor(on:Bool):Int return on ? TEAL : MUTED;

	/** Fill of a switch's chip. */
	public static function chipColor(on:Bool):Int return on ? 0xFF1F5F59 : CHIP_OFF;

	/** The fraction of a track to fill, for any raw number. */
	public static function fillWidth(trackWidth:Float, fraction:Float):Int
		return Std.int(Math.round(Math.max(0, trackWidth) * clamp01(fraction)));

	/** Width of the footer's hint row, from the key and action lengths. VCR is
	 * monospaced, so a character is close to 0.6 of the type size wide. */
	public static function hintsWidth(hints:Array<MenuHint>, size:Int = HINT_SIZE):Float {
		var width:Float = 0;
		for (index in 0...hints.length) {
			width += (hints[index].key.length + hints[index].action.length) * size * 0.6 + 15;
			if (index < hints.length - 1) width += 12;
		}
		return width;
	}

	/** Room the footer leaves for hints: everything left of the heading. */
	public static function hintsRoom(screenWidth:Int):Float return screenWidth - MARGIN - 258;
}
