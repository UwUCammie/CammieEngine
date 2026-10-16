package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import MenuStyle.MenuHint;

/** The Freeplay footer: a strip with a note above the key hints, and the
 * screen's title leaning in the bottom-right corner over a pink underline.
 * Keys and what they do are coloured apart, with a rule between each pair. */
class MenuFooter extends FlxTypedGroup<FlxSprite> {
	public var bar(default, null):FlxSprite;
	public var note(default, null):FlxText;
	public var heading(default, null):FlxText;
	public var underline(default, null):FlxSprite;
	public var hints(default, null):Array<MenuHint> = [];
	var hintItems:Array<FlxSprite> = [];

	/** `withBar` is false when the screen already draws its own strip below. */
	public function new(title:String, hints:Array<MenuHint>, withBar:Bool = true) {
		super();
		var top = FlxG.height - MenuStyle.BAR_HEIGHT;
		if (withBar) {
			bar = MenuWidgets.rect(0, top, FlxG.width, MenuStyle.BAR_HEIGHT, MenuStyle.BAR);
			add(bar);
		}
		note = MenuWidgets.text(MenuStyle.MARGIN, top + 6, FlxG.width - MenuStyle.MARGIN * 2 - 270, '', MenuStyle.BODY_SIZE, MenuStyle.TEXT);
		note.wordWrap = false;
		add(note);
		underline = MenuWidgets.rect(FlxG.width - 244, FlxG.height - 13, 226, 5, MenuStyle.PINK);
		underline.angle = -2;
		heading = MenuWidgets.text(FlxG.width - 246, FlxG.height - 62, 0, title, MenuStyle.HEADING_SIZE, MenuStyle.CREAM);
		heading.angle = -2;
		add(underline);
		add(heading);
		setHints(hints);
	}

	/** Replace the hint row. Hints stay under the underline and title in draw order. */
	public function setHints(next:Array<MenuHint>):Void {
		for (item in hintItems) {
			remove(item, true);
			item.destroy();
		}
		hintItems = [];
		hints = next.copy();
		var at = members.indexOf(underline);
		var hintX:Float = MenuStyle.MARGIN;
		var rowY = FlxG.height - 31;
		for (index in 0...hints.length) {
			var key = MenuWidgets.text(hintX, rowY, 0, hints[index].key, MenuStyle.HINT_SIZE, MenuStyle.GOLD);
			hintX += key.width + 5;
			var action = MenuWidgets.text(hintX, rowY, 0, hints[index].action, MenuStyle.HINT_SIZE, MenuStyle.MUTED);
			hintX += action.width + 10;
			insert(at++, key);
			insert(at++, action);
			hintItems.push(key);
			hintItems.push(action);
			if (index < hints.length - 1) {
				var rule = MenuWidgets.rect(hintX, rowY + 1, 2, 16, MenuStyle.RULE);
				insert(at++, rule);
				hintItems.push(rule);
				hintX += 12;
			}
		}
	}

	/** One line above the hints, for the selected item's description or a status. */
	public function setNote(text:String, color:Int = MenuStyle.TEXT):Void {
		note.text = text == null ? '' : text;
		note.color = color;
	}
}
