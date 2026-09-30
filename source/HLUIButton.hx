package;

import flixel.FlxG;

@:keep
class HLUIButton extends HLUIComponent {
	public var _label:HLUILabel;
	public var onClick:Null<Void->Void>;
	public var onRelease:Null<Void->Void>;
	public var onClickCallback:Null<Void->Void>;
	public var useLabel:Bool = true;
	public var useImage:Bool = false;
	public var isPressed(default, null):Bool = false;

	public function new(?text:String = '') {
		super();
		_label = new HLUILabel(text);
		addComponent(_label);
		componentWidth = Math.max(48, _label.componentWidth + 20);
		componentHeight = Math.max(30, _label.componentHeight + 12);
		_label.componentWidth = componentWidth;
		_label.componentHeight = componentHeight;
		setHitArea();
	}

	public function setText(text:String):Void {
		_label.text = text;
		componentWidth = Math.max(48, _label.componentWidth + 20);
		_label.componentWidth = componentWidth;
		_label.componentHeight = componentHeight;
		setHitArea();
	}

	public function setGraphic(graphic:Dynamic):Void {
		useImage = graphic != null;
		if (graphic != null) loadGraphic(graphic);
	}

	public function set_useImage(value:Bool):Bool return useImage = value;
	public function set_useLabel(value:Bool):Bool return useLabel = value;

	override public function buildUI(?options:Dynamic):Void {
		super.buildUI(options);
		_label.componentWidth = componentWidth;
		_label.componentHeight = componentHeight;
		_label.buildUI();
		_label.syncPosition();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		var wasHovering = _hovered;
		updateHover();
		if (_hovered && FlxG.mouse.justPressed) {
			isPressed = true;
			if (onClick != null) onClick();
			if (onClickCallback != null) onClickCallback();
		}
		if (isPressed && FlxG.mouse.justReleased) {
			isPressed = false;
			if (_hovered && onRelease != null) onRelease();
		}
		if (!wasHovering && _hovered) _label.textCol = HLUILabel.TEXT_SELEC_COL;
		else if (wasHovering && !_hovered) _label.textCol = HLUILabel.TEXT_COL;
	}

	override public function destroy():Void {
		onClick = null;
		onRelease = null;
		onClickCallback = null;
		_label = null;
		super.destroy();
	}
}
