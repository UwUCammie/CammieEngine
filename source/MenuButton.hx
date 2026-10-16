package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;

/** A button drawn as a Freeplay card: it takes the selected card's colour and
 * pink edge when it has keyboard focus, brightens under a pointer, and dims
 * when it cannot be used. Clicking calls `onClick` while the button is active. */
class MenuButton extends FlxTypedGroup<FlxSprite> {
	public var x(default, null):Float = 0;
	public var y(default, null):Float = 0;
	public var width(default, null):Float;
	public var height(default, null):Float;
	public var onClick:Void->Void;
	public var label(default, null):FlxText;
	public var panel(default, null):FlxSprite;
	public var stripe(default, null):FlxSprite;
	public var enabled(default, null):Bool = true;
	public var focused(default, null):Bool = false;
	var hovered:Bool = false;

	public function new(text:String, width:Int, height:Int, onClick:Void->Void) {
		super();
		this.width = width; this.height = height; this.onClick = onClick;
		panel = new FlxSprite().makeGraphic(width, height, MenuStyle.WHITE);
		stripe = new FlxSprite().makeGraphic(MenuStyle.STRIPE_WIDTH, height, MenuStyle.PINK);
		label = MenuWidgets.text(0, 0, width, text, MenuStyle.BODY_SIZE, MenuStyle.TEXT, FlxTextAlign.CENTER);
		label.wordWrap = false;
		add(panel); add(stripe); add(label);
		refreshLook();
	}

	public function setPosition(x:Float, y:Float):Void {
		this.x = x; this.y = y;
		refreshLook();
	}

	/** Whether the button can be used, and whether the keyboard cursor is on it. */
	public function setLook(enabled:Bool, focused:Bool):Void {
		if (this.enabled == enabled && this.focused == focused) return;
		this.enabled = enabled; this.focused = focused;
		refreshLook();
	}

	/** Whether a screen point is over the button's body. */
	public function contains(px:Float, py:Float):Bool
		return px >= x && px <= x + width && py >= y && py <= y + height;

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		var over = visible && enabled && FlxG.mouse.visible && contains(FlxG.mouse.x, FlxG.mouse.y);
		if (over != hovered) {
			hovered = over;
			refreshLook();
		}
		if (over && FlxG.mouse.justPressed && onClick != null) onClick();
	}

	function refreshLook():Void {
		var focus = focused && enabled ? 1.0 : (hovered ? 0.55 : 0.0);
		panel.setPosition(x, y);
		panel.color = MenuStyle.cardColor(focus);
		panel.alpha = enabled ? MenuStyle.cardAlpha(focus) : 0.45;
		stripe.setPosition(x, y);
		stripe.visible = focused && enabled;
		label.setPosition(x, y + (height - label.height) / 2);
		label.color = !enabled ? MenuStyle.DISABLED : (focus > 0.5 ? MenuStyle.CREAM : MenuStyle.TEXT);
	}
}
