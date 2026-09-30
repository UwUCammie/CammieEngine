package;

import flixel.FlxState;
import flixel.text.FlxText;
import flixel.util.FlxColor;

@:keep
class HLUILabel extends HLUIComponent {
	public static inline var TEXT_COL:FlxColor = 0xFFFFFFFF;
	public static inline var TEXT_SELEC_COL:FlxColor = 0xFFFFCC66;
	public static inline var HIGHLIGHT_COL:FlxColor = 0xFF666666;

	public var text(get, set):String;
	public var size(get, set):Int;
	public var textCol(get, set):FlxColor;
	public var labelSprite(default, null):FlxText;
	var labelText:String = '';
	var labelSize:Int = 16;
	var labelColor:FlxColor = TEXT_COL;
	var ownerFontName:String;
	var ownerFontResolved:Bool = false;
	var mountedTextStates:Map<FlxState, Bool> = new Map();

	public function new(?text:String = '') {
		super();
		// A zero field width lets FlxText size to its content. A one-pixel field
		// clips every HLUITable cell and wraps each character into a tofu-like
		// sliver in OpenFL's native renderer.
		labelSprite = new FlxText(0, 0, 0, '', labelSize);
		labelSprite.antialiasing = true;
		this.text = text;
	}

	function get_text():String return labelText;
	function set_text(value:String):String {
		labelText = value == null ? '' : value;
		if (labelSprite != null) {
			labelSprite.text = labelText;
			applyTextStyle();
		}
		return labelText;
	}

	function get_size():Int return labelSize;
	function set_size(value:Int):Int {
		labelSize = value < 1 ? 1 : value;
		applyTextStyle();
		return labelSize;
	}

	function get_textCol():FlxColor return labelColor;
	function set_textCol(value:FlxColor):FlxColor {
		labelColor = value;
		applyTextStyle();
		return labelColor;
	}

	override public function bindOwner(paths:CodenamePaths, claim:flixel.FlxBasic->Void):Void {
		if (ownerPaths != paths) {
			ownerFontName = null;
			ownerFontResolved = false;
		}
		super.bindOwner(paths, claim);
	}

	public function drawText():Void applyTextStyle();

	override public function buildUI(?options:Dynamic):Void {
		super.buildUI(options);
		applyTextStyle();
	}

	function applyTextStyle():Void {
		if (labelSprite == null) return;
		if (labelSprite.text != labelText) labelSprite.text = labelText;
		if (labelSprite.size != labelSize) labelSprite.size = labelSize;
		if (labelSprite.color != labelColor) labelSprite.color = labelColor;
		if (ownerPaths != null) {
			if (!ownerFontResolved) {
				ownerFontName = ownerPaths.getFontName(ownerPaths.font('verdana.ttf'));
				ownerFontResolved = true;
			}
			if (labelSprite.font != ownerFontName) labelSprite.font = ownerFontName;
		}
		var textWidth = labelSprite.width;
		var textHeight = labelSprite.height;
		if (componentWidth <= 0) componentWidth = textWidth;
		if (componentHeight <= 0) componentHeight = textHeight;
		labelSprite.x = x + (componentWidth > 0 ? (componentWidth - textWidth) / 2 : 0);
		labelSprite.y = y + (componentHeight > 0 ? (componentHeight - textHeight) / 2 : 0);
	}

	override public function syncPosition():Void {
		super.syncPosition();
		applyTextStyle();
	}

	override public function mountExtraSprites(state:FlxState):Void {
		if (state != null && !mountedTextStates.exists(state)) {
			mountedTextStates.set(state, true);
			state.add(labelSprite);
			if (claimed != null) claimed(labelSprite);
		}
	}

	override public function removeThisAndChildComponentsFromState(state:FlxState):Void {
		if (state != null && mountedTextStates.exists(state)) {
			mountedTextStates.remove(state);
			state.remove(labelSprite, false);
			if (claimed != null) claimed(labelSprite);
		}
		super.removeThisAndChildComponentsFromState(state);
	}

	override public function destroy():Void {
		if (labelSprite != null) {
			labelSprite.destroy();
			labelSprite = null;
		}
		mountedTextStates = new Map();
		super.destroy();
	}
}
