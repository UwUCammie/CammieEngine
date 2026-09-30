package;

import flixel.FlxG;

@:keep
class HLUICheckbox extends HLUIComponent {
	public var text:String;
	public var value:Bool;
	public var onChange:Null<Bool->Void>;
	var label:HLUILabel;
	var check:HLUILabel;

	public function new(?text:String = '', ?value:Bool = false) {
		super();
		this.text = text == null ? '' : text;
		this.value = value == true;
		label = new HLUILabel(this.text);
		check = new HLUILabel(this.value ? '[x]' : '[ ]');
		label.componentWidth = 250;
		check.componentWidth = 36;
		componentWidth = 286;
		componentHeight = 32;
		check.componentOffset.x = 250;
		addComponent(label);
		addComponent(check);
		setHitArea();
	}

	public function setValue(value:Bool, notify:Bool = true):Void {
		if (this.value == value) return;
		this.value = value;
		check.text = value ? '[x]' : '[ ]';
		if (notify && onChange != null) onChange(value);
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		updateHover();
		if (_hovered && FlxG.mouse.justPressed) setValue(!value);
	}

	override public function destroy():Void {
		onChange = null;
		label = null;
		check = null;
		super.destroy();
	}
}
