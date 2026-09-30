package;

import flixel.FlxG;

@:keep
class HLUIWindow extends HLUIComponent {
	public var _titlebar:HLUIBox;
	public var _titlebarLabel:HLUILabel;
	public var _titlebarClose:HLUIButton;
	public var volume:Float = 1;
	var lastShown:Bool = true;
	var requestedWidth:Float;
	var requestedHeight:Float;

	public function new(?x:Null<Float>, ?y:Null<Float>,
		?width:Float = 520, ?height:Float = 360) {
		super();
		requestedWidth = width == null || width <= 0 ? 520 : width;
		requestedHeight = height == null || height <= 0 ? 360 : height;
		componentWidth = requestedWidth;
		componentHeight = requestedHeight;
		this.x = x == null ? (FlxG.width - requestedWidth) / 2 : x;
		this.y = y == null ? (FlxG.height - requestedHeight) / 2 : y;
		_titlebar = new HLUIBox(CodenameHL17UICompat.HORIZONTAL);
		_titlebar.componentWidth = requestedWidth;
		_titlebar.componentHeight = 35;
		_titlebarLabel = new HLUILabel('Window');
		_titlebarLabel.componentWidth = requestedWidth - 48;
		_titlebarLabel.componentHeight = 35;
		_titlebarClose = new HLUIButton('×');
		_titlebarClose.componentWidth = 34;
		_titlebarClose.componentHeight = 30;
		_titlebarClose.componentOffset.x = requestedWidth - 38;
		_titlebarClose.componentOffset.y = 3;
		_titlebar.addComponent(_titlebarLabel);
		_titlebar.addComponent(_titlebarClose);
		_titlebarClose.onClickCallback = function():Void visible = false;
		_titlebar.componentOffset.set(0, 0);
		addComponent(_titlebar);
		setHitArea();
		buildUI({background:true});
	}

	override public function center():Void {
		x = Std.int((FlxG.width - componentWidth) / 2);
		y = Std.int((FlxG.height - componentHeight) / 2);
		layoutComponents();
	}

	public function initializeAndAddToState(state:flixel.FlxState):Void {
		buildUI({background:true});
		addThisAndChildComponentsToState(state);
	}

	override public function layoutComponents():Void {
		var cursor:Float = 0;
		for (component in _components) if (component != null) {
			component.flowOffset.set(0, cursor);
			component.syncPosition();
			cursor += component.componentHeight + component.push.y;
		}
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		_hovered = visible && FlxG.mouse.overlaps(this);
		if (lastShown != visible) {
			for (component in _components) if (component != null) component.setTreeVisible(visible);
			lastShown = visible;
		}
	}

	override public function destroy():Void {
		_titlebar = null;
		_titlebarLabel = null;
		_titlebarClose = null;
		super.destroy();
	}
}
