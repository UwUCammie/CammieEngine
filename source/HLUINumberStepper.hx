package;

import flixel.FlxG;

@:keep
class HLUINumberStepper extends HLUIComponent {
	public var text:String;
	public var value:Int;
	public var min:Int;
	public var max:Int;
	public var step:Int;
	public var onChange:Null<Int->Void>;
	var label:HLUILabel;
	var readout:HLUILabel;
	var decrement:HLUIButton;
	var increment:HLUIButton;

	public function new(?text:String = '', ?value:Int = 0, ?min:Int = 0,
		?max:Int = 100, ?step:Int = 1) {
		super();
		this.text = text == null ? '' : text;
		this.min = min;
		this.max = max < min ? min : max;
		this.step = step <= 0 ? 1 : step;
		this.value = clamp(value);
		componentWidth = 380;
		componentHeight = 34;
		label = new HLUILabel(this.text);
		label.componentWidth = 190;
		readout = new HLUILabel(Std.string(this.value));
		readout.componentWidth = 72;
		readout.componentOffset.x = 190;
		decrement = new HLUIButton('<');
		decrement.componentWidth = 42;
		decrement.componentHeight = 30;
		decrement.componentOffset.x = 270;
		decrement.onClickCallback = function():Void change(-this.step);
		increment = new HLUIButton('>');
		increment.componentWidth = 42;
		increment.componentHeight = 30;
		increment.componentOffset.x = 320;
		increment.onClickCallback = function():Void change(this.step);
		addComponent(label);
		addComponent(readout);
		addComponent(decrement);
		addComponent(increment);
		setHitArea();
	}

	function clamp(number:Int):Int return number < min ? min : (number > max ? max : number);
	function change(amount:Int):Void {
		var next = clamp(value + amount);
		if (next == value) return;
		value = next;
		readout.text = Std.string(value);
		if (onChange != null) onChange(value);
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		if (_hovered && FlxG.keys.justPressed.LEFT) change(-step);
		else if (_hovered && FlxG.keys.justPressed.RIGHT) change(step);
	}

	override public function destroy():Void {
		onChange = null;
		label = null;
		readout = null;
		decrement = null;
		increment = null;
		super.destroy();
	}
}
