package;

@:keep
class HLUITab extends HLUIButton {
	public var content:HLUIComponent;
	public var selected(get, set):Bool;
	public var selectedValue:Bool = false;
	public var ownerTabs:Null<HLUITabBox>;

	public function new(label:String, content:HLUIComponent) {
		super(label);
		this.content = content;
		componentHeight = 28;
		_label.componentHeight = componentHeight;
	}

	function get_selected():Bool return selectedValue;
	function set_selected(value:Bool):Bool {
		selectedValue = value;
		_label.textCol = value ? HLUILabel.TEXT_SELEC_COL : HLUILabel.TEXT_COL;
		if (value && ownerTabs != null) ownerTabs.selectTab(this);
		return selectedValue;
	}

	public function drawBottomLine():Void {
		if (!selectedValue) return;
		var line = new HLUIComponent(x, y + componentHeight - 2);
		line.componentWidth = componentWidth;
		line.componentHeight = 2;
		line.makeGraphic(Std.int(Math.max(1, componentWidth)), 2, HLUILabel.TEXT_SELEC_COL);
		addComponent(line);
	}

	override public function destroy():Void {
		ownerTabs = null;
		content = null;
		super.destroy();
	}
}
