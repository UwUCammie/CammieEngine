package;

import flixel.FlxState;

@:keep
class HLUITabBox extends HLUIComponent {
	public var _tabs:Array<HLUITab> = [];
	public var _content:HLUIBox;
	public var tabContent(get, set):HLUIComponent;
	var selectedContent:HLUIComponent;
	var requestedState:Null<FlxState>;

	public function new(tabs:Array<HLUITab>, width:Float, height:Float, ?state:FlxState) {
		super();
		componentWidth = width;
		componentHeight = height;
		requestedState = state;
		_content = new HLUIBox(CodenameHL17UICompat.VERTICAL);
		_content.componentWidth = width;
		_content.componentHeight = height - 30;
		_content.componentOffset.y = 30;
		addComponent(_content);
		if (tabs != null) for (tab in tabs) {
			if (tab == null) continue;
			tab.ownerTabs = this;
			_tabs.push(tab);
			addComponent(tab);
			tab.componentOffset.set(componentWidth / Math.max(1, tabs.length) * (_tabs.length - 1), 0);
			tab.componentWidth = componentWidth / Math.max(1, tabs.length);
			tab._label.componentWidth = tab.componentWidth;
			tab.onClickCallback = function():Void selectTab(tab);
		}
	}

	function get_tabContent():HLUIComponent return selectedContent;
	function set_tabContent(value:HLUIComponent):HLUIComponent {
		if (value == null) return selectedContent;
		for (tab in _tabs) if (tab != null) tab.selectedValue = tab.content == value;
		selectContent(value);
		return selectedContent;
	}

	public function selectTab(tab:HLUITab):Void {
		if (tab == null || _tabs.indexOf(tab) < 0) return;
		for (candidate in _tabs) if (candidate != null) candidate.selectedValue = candidate == tab;
		selectContent(tab.content);
	}

	function selectContent(content:HLUIComponent):Void {
		if (selectedContent == content) return;
		if (selectedContent != null) {
			_content.removeComponent(selectedContent, false);
			if (requestedState != null) selectedContent.removeThisAndChildComponentsFromState(requestedState);
		}
		selectedContent = content;
		if (content != null) {
			content.componentWidth = componentWidth;
			content.componentHeight = componentHeight - 30;
			_content.addComponent(content);
			if (requestedState != null) content.addThisAndChildComponentsToState(requestedState);
		}
	}

	override public function buildUI(?options:Dynamic):Void {
		super.buildUI(options);
		for (tab in _tabs) if (tab != null) tab.buildUI({background:tab.selected});
	}

	override public function destroy():Void {
		requestedState = null;
		selectedContent = null;
		_tabs.resize(0);
		_content = null;
		super.destroy();
	}
}
