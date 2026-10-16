package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;

/** A detail card whose size follows its content: the backing, its accent edge
 * and its heading, resized together by MenuWidgets.sizePanel. */
typedef MenuPanelParts = {
	var card:FlxSprite;
	var accent:FlxSprite;
	var heading:FlxText;
}

/** Builders for the pieces every Freeplay-style screen is made of. Each one
 * reads MenuStyle, so a change to the palette reaches every screen at once. */
class MenuWidgets {
	/** The menu background, centred, without the dim over it. */
	public static function backdrop():FlxSprite {
		var bg = new FlxSprite();
		bg.loadGraphic(FNFAssets.exists('assets/images/Custom_Menu_BGs/Default/menuDesat.png')
			? 'assets/images/Custom_Menu_BGs/Default/menuDesat.png' : 'assets/images/menuDesat.png');
		bg.screenCenter();
		return bg;
	}

	/** The dim that lets the cards read against the background. */
	public static function shade():FlxSprite
		return new FlxSprite().makeGraphic(FlxG.width, FlxG.height, MenuStyle.SHADE);

	/** Background and dim, added to a state in the order Freeplay draws them. */
	public static function background(state:FlxGroup):FlxSprite {
		var bg = backdrop();
		state.add(bg);
		state.add(shade());
		return bg;
	}

	/** Plain VCR text with no outline, as Freeplay sets it. */
	public static function text(x:Float, y:Float, width:Float, value:String, size:Int, color:Int,
		alignment:FlxTextAlign = FlxTextAlign.LEFT):FlxText {
		var label = new FlxText(x, y, width, value, size);
		label.setFormat(MenuStyle.FONT, size, color, alignment);
		return label;
	}

	/** A flat rectangle. */
	public static function rect(x:Float, y:Float, width:Float, height:Float, color:Int, alpha:Float = 1):FlxSprite {
		var block = new FlxSprite(x, y).makeGraphic(Std.int(Math.max(1, width)), Std.int(Math.max(1, height)), color);
		block.alpha = alpha;
		return block;
	}

	/** One backed card for a group of details. The accent spans the whole card
	 * and shares its colour with the heading, so it marks a section, not a row.
	 * Returns the card so its text can be placed from `card.x + 12`. */
	public static function detailCard(group:FlxGroup, x:Float, y:Float, width:Float, height:Float,
		title:String, accent:Int):FlxSprite {
		var card = rect(x, y, width, height, MenuStyle.CARD, MenuStyle.DETAIL_ALPHA);
		group.add(card);
		group.add(rect(x, y, MenuStyle.ACCENT_WIDTH, height, accent));
		group.add(text(x + 12, y + 6, width - 24, title, MenuStyle.SECTION_SIZE, accent));
		return card;
	}

	/** A detail card that can be resized to fit what it holds. */
	public static function sizedPanel(group:FlxGroup, accentColor:Int, title:String):MenuPanelParts {
		var parts:MenuPanelParts = {
			card: new FlxSprite().makeGraphic(1, 1, MenuStyle.CARD),
			accent: new FlxSprite().makeGraphic(1, 1, MenuStyle.WHITE),
			heading: text(0, 0, 0, title, MenuStyle.SECTION_SIZE, accentColor)
		};
		parts.card.alpha = MenuStyle.DETAIL_ALPHA;
		// A white graphic tinted by the accent, so the tint can change to any colour later.
		parts.accent.color = accentColor;
		parts.heading.wordWrap = false;
		group.add(parts.card);
		group.add(parts.accent);
		group.add(parts.heading);
		return parts;
	}

	public static function sizePanel(parts:MenuPanelParts, x:Float, y:Float, width:Float, height:Float):Void {
		parts.card.scale.set(width, height);
		parts.card.updateHitbox();
		parts.card.setPosition(x, y);
		parts.accent.scale.set(MenuStyle.ACCENT_WIDTH, height);
		parts.accent.updateHitbox();
		parts.accent.setPosition(x, y);
		parts.heading.setPosition(x + 12, y + 6);
	}

	public static function showPanel(parts:MenuPanelParts, on:Bool):Void {
		parts.card.visible = parts.accent.visible = parts.heading.visible = on;
	}

	/** A popup panel over a dimmed menu: shadow, teal border, body and pink cap. */
	public static function panel(group:FlxGroup, x:Float, y:Float, width:Int, height:Int):Void {
		var dim = new FlxSprite().makeGraphic(FlxG.width, FlxG.height, MenuStyle.DIM);
		dim.alpha = 0.58;
		group.add(dim);
		group.add(rect(x + 10, y + 12, width, height, 0xFF000000, 0.35));
		group.add(rect(x - 2, y - 2, width + 4, height + 4, MenuStyle.TEAL, 0.55));
		group.add(rect(x, y, width, height, MenuStyle.PANEL, 0.93));
		group.add(rect(x, y, width, 4, MenuStyle.PINK));
	}
}
