package;

import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextAlign;
import flixel.util.FlxTimer;
import MenuStyle.MenuCardLook;

/** A list card in the Freeplay style: a backed row that grows into a taller,
 * brighter card with a pink edge when selected, easing there on the same clock
 * Freeplay's cards use. A card can carry an icon on its left, a value on its
 * right (text, or a switch drawn as a chip) and a caption that appears once it
 * is selected. */
class MenuCard extends FlxTypedGroup<FlxSprite> {
	public static inline var ICON_COMPACT:Int = 34;
	public static inline var ICON_SELECTED:Int = 54;

	public var x:Float = 0;
	public var y:Float = 0;
	/** Fades the whole card; 1 is fully drawn. */
	public var opacity(default, set):Float = 1;
	public var cardWidth(default, null):Int;
	public var motion(default, null) = new FreeplayCardMotion();
	public var selected(default, null):Bool = false;
	public var disabled(default, null):Bool = false;
	public var label(default, null):String;
	public var captionText(default, null):String = '';
	public var panel(default, null):FlxSprite;
	public var stripe(default, null):FlxSprite;
	public var chip(default, null):FlxSprite;
	public var title(default, null):FlxText;
	public var value(default, null):FlxText;
	public var caption(default, null):FlxText;
	public var icon(default, null):FlxSprite;
	/** Heights and text placement of this card. */
	public var idleHeight(default, null):Int = MenuStyle.ROW_HEIGHT;
	public var selectedHeight(default, null):Int = MenuStyle.SELECTED_HEIGHT;
	var titleSize:Int = MenuStyle.TITLE_SIZE;
	var selectedTitleSize:Int = MenuStyle.SELECTED_TITLE_SIZE;
	var titleTop:Float = 8;
	var titleLift:Float = 5;
	var captionTop:Float = 50;
	var titleLeft:Int;
	var valueWidth:Int = 0;
	var switchState:Null<Bool> = null;
	var presentedHeight:Float = -1;
	var shownSelected:Null<Bool> = null;

	public function new(label:String, width:Int, titleLeft:Int = 24, ?look:MenuCardLook) {
		super();
		this.label = label; cardWidth = width; this.titleLeft = titleLeft;
		if (look == null) look = {};
		if (look.idle != null) idleHeight = look.idle;
		if (look.selected != null) selectedHeight = look.selected;
		if (look.titleSize != null) titleSize = look.titleSize;
		if (look.selectedTitleSize != null) selectedTitleSize = look.selectedTitleSize;
		if (look.titleTop != null) titleTop = look.titleTop;
		if (look.titleLift != null) titleLift = look.titleLift;
		if (look.captionTop != null) captionTop = look.captionTop;
		panel = new FlxSprite().makeGraphic(width, 1, MenuStyle.WHITE);
		stripe = new FlxSprite().makeGraphic(MenuStyle.STRIPE_WIDTH, 1, MenuStyle.PINK);
		chip = new FlxSprite().makeGraphic(52, 24, MenuStyle.WHITE);
		chip.visible = false;
		title = MenuWidgets.text(0, 0, width - titleLeft - (look.reserve == null ? 150 : look.reserve), '', titleSize, MenuStyle.TEXT);
		title.wordWrap = false;
		value = MenuWidgets.text(0, 0, 220, '', look.valueSize == null ? MenuStyle.BODY_SIZE : look.valueSize, MenuStyle.MUTED, FlxTextAlign.RIGHT);
		value.wordWrap = false;
		caption = MenuWidgets.text(0, 0, width - titleLeft - 24, '', look.captionSize == null ? MenuStyle.SMALL_SIZE : look.captionSize, MenuStyle.MUTED);
		caption.wordWrap = look.captionLines != null && look.captionLines > 1;
		add(panel); add(stripe); add(chip); add(title); add(value); add(caption);
		stripe.visible = false;
	}

	function set_opacity(next:Float):Float {
		opacity = MenuStyle.clamp01(next);
		if (panel != null) drawPresentation(true);
		return opacity;
	}

	/** An icon on the card's left; the card's title must start right of it. */
	public function setIcon(sprite:FlxSprite):Void {
		if (icon != null) remove(icon, true);
		icon = sprite;
		if (icon != null) {
			icon.antialiasing = true;
			// Icons from the character sheets are screen-fixed by default; a card scrolls with its screen.
			icon.scrollFactor.set(1, 1);
			add(icon);
		}
		drawPresentation(true);
	}

	/** Text on the card's right edge; with no colour it is muted. */
	public function setValue(text:String, color:Int = MenuStyle.MUTED, width:Int = 220):Void {
		switchState = null; chip.visible = false;
		valueWidth = width;
		value.fieldWidth = width;
		value.alignment = FlxTextAlign.RIGHT;
		value.text = text;
		value.color = color;
		drawPresentation(true);
	}

	/** A switch, drawn as an ON or OFF chip on the card's right edge. */
	public function setSwitch(on:Bool):Void {
		if (switchState == on) return;
		switchState = on;
		valueWidth = 52;
		value.fieldWidth = 52;
		value.alignment = FlxTextAlign.CENTER;
		value.text = MenuStyle.switchLabel(on);
		value.color = MenuStyle.switchColor(on);
		chip.color = MenuStyle.chipColor(on);
		drawPresentation(true);
	}

	public function clearValue():Void {
		switchState = null; chip.visible = false; value.text = ''; valueWidth = 0;
	}

	/** The line under the title that shows once the card is selected. */
	public function setCaption(text:String):Void {
		var next = text == null ? '' : text;
		if (captionText == next) return;
		captionText = next;
		caption.text = captionText;
		drawPresentation(true);
	}

	public function rename(text:String):Void {
		if (label == text) return;
		label = text; shownSelected = null;
		drawPresentation(true);
	}

	public function moveTo(x:Float, y:Float, snap:Bool = false):Void {
		motion.target(x, y, selected ? selectedHeight : idleHeight, selected, snap);
		if (snap) { this.x = motion.x; this.y = motion.y; drawPresentation(true); }
	}

	public function present(selected:Bool, disabled:Bool = false):Void {
		this.selected = selected; this.disabled = disabled;
		if (!motion.initialized) motion.target(x, y, selected ? selectedHeight : idleHeight, selected, true);
		drawPresentation(true);
	}

	/** Blink the card, then call `onComplete` with the card hidden, the way
	 * FlxFlicker blinks a sprite. */
	public function flicker(duration:Float, interval:Float, ?onComplete:Void->Void):Void {
		var blinks = Std.int(Math.max(1, Math.round(duration / interval)));
		new FlxTimer().start(interval, function(timer:FlxTimer):Void {
			visible = !visible;
			if (timer.loopsLeft == 0) {
				visible = false;
				if (onComplete != null) onComplete();
			}
		}, blinks);
	}

	/** Whether the card's body overlaps a screen point, for a pointer. */
	public function contains(px:Float, py:Float):Bool
		return px >= x && px <= x + cardWidth && py >= y && py <= y + motion.height - 4;

	override public function update(elapsed:Float):Void {
		if (motion.advance(elapsed)) { x = motion.x; y = motion.y; drawPresentation(false); }
		super.update(elapsed);
	}

	function drawPresentation(force:Bool):Void {
		var height = motion.height - 4;
		if (force || presentedHeight != height) {
			presentedHeight = height;
			panel.scale.y = height; panel.updateHitbox();
			stripe.scale.y = height; stripe.updateHitbox();
		}
		panel.setPosition(x, y); stripe.setPosition(x, y);
		var focus = motion.focus;
		var changed = shownSelected == null || shownSelected != selected;
		if (changed) { shownSelected = selected; title.text = label; }
		title.color = MenuStyle.titleColor(selected, disabled);
		var scale = MenuStyle.titleScale(focus, titleSize, selectedTitleSize);
		title.scale.set(scale, scale);
		if (changed || force) title.updateHitbox();
		title.offset.set(0, 0); title.origin.set(0, 0);
		title.setPosition(x + titleLeft, y + titleTop + focus * titleLift);
		panel.color = MenuStyle.cardColor(focus);
		panel.alpha = MenuStyle.cardAlpha(focus) * opacity;
		stripe.visible = focus > 0; stripe.alpha = focus * opacity;
		title.alpha = opacity;
		var rightEdge = x + cardWidth - 16;
		if (switchState != null) {
			chip.visible = true;
			chip.alpha = opacity;
			chip.setPosition(rightEdge - 52, y + titleTop + 1 + focus * titleLift);
			value.setPosition(chip.x, chip.y + 3);
		} else {
			chip.visible = false;
			value.setPosition(rightEdge - valueWidth, y + titleTop + 3 + focus * titleLift);
		}
		value.alpha = (disabled ? 0.5 : 1) * opacity;
		caption.setPosition(x + titleLeft, y + captionTop);
		caption.visible = captionText != '' && focus > 0.02;
		caption.alpha = focus * opacity;
		if (icon != null) {
			var size = ICON_COMPACT + (ICON_SELECTED - ICON_COMPACT) * focus;
			var fit = size / Math.max(1, Math.max(icon.frameWidth, icon.frameHeight));
			icon.scale.set(fit, fit);
			icon.updateHitbox();
			icon.setPosition(x + 24 + (ICON_COMPACT - icon.width) / 2 - 4 * focus, y + titleTop - 5 + focus * titleLift);
			icon.alpha = opacity;
		}
	}
}
