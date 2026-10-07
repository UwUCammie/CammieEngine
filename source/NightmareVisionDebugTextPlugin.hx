package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.group.FlxGroup.FlxTypedGroup;
import flixel.text.FlxText;
import flixel.text.FlxText.FlxTextBorderStyle;
import flixel.util.FlxColor;
import flixel.util.FlxDestroyUtil;

/** Debug output group owned by one source runtime. */
@:keep
class NightmareVisionDebugTextPlugin extends FlxTypedGroup<NightmareVisionDebugText> {
	final fontPath:String;
	var released:Bool = false;

	public function new(fontPath:String) {
		super();
		if (fontPath == null || fontPath == '')
			throw '[nmv-bootstrap-service] DebugText requires the selected owner font path';
		this.fontPath = fontPath;
	}

	public function addText(message:String, colour:FlxColor = FlxColor.WHITE):Void {
		if (released) throw '[nmv-bootstrap-service] DebugText owner has been released';
		var text = grabText(message);
		text.resetText();
		text.setText(message, colour);
		remove(text, true);
		insert(0, text);
		repositionTexts();
		var cameras = FlxG.cameras.list;
		text.camera = cameras != null && cameras.length > 0 ? cameras[cameras.length - 1] : FlxG.camera;
	}

	function grabText(message:String):NightmareVisionDebugText {
		for (text in members)
			if (text != null && text.alive && text._trace == message)
				return text;
		return recycle(NightmareVisionDebugText, function() return new NightmareVisionDebugText(fontPath, ''));
	}

	function repositionTexts():Void {
		var count = 0;
		var startY = 25.0;
		var mainType = Type.resolveClass('Main');
		var fpsCounter:Dynamic = mainType == null ? null : Reflect.field(mainType, 'fpsCounter');
		if (fpsCounter != null && Reflect.getProperty(fpsCounter, 'visible') == true) {
			var top:Dynamic = Reflect.getProperty(fpsCounter, 'y');
			var height:Dynamic = Reflect.getProperty(fpsCounter, 'height');
			if ((Std.isOfType(top, Int) || Std.isOfType(top, Float))
				&& (Std.isOfType(height, Int) || Std.isOfType(height, Float)))
				startY = Math.max(startY, (top : Float) + (height : Float) + 5);
		}
		forEachAlive(function(text:NightmareVisionDebugText) {
			text.y = startY + text.height * count;
			count++;
		});
	}

	public function clearText():Void {
		for (text in members.copy()) {
			if (text == null) continue;
			remove(text, true);
			FlxDestroyUtil.destroy(text);
		}
		clear();
	}

	public function release():Void {
		if (released) return;
		released = true;
		FlxG.plugins.remove(this);
		clearText();
		destroy();
	}
}

/** One recyclable donor-shaped debug message. */
@:keep
class NightmareVisionDebugText extends FlxText {
	static inline var UNDERLAY_PADDING:Float = 5;
	public var disableTime:Float = 4;
	public var traceCount:Int = 1;
	public var _trace:String = '';
	final underlay:FlxSprite;
	var dirtyText:Bool = false;

	public function new(fontPath:String, text:String, colour:FlxColor = FlxColor.WHITE) {
		super(10, 10, FlxG.width, text, 16);
		setFormat(fontPath, 18, FlxColor.WHITE, LEFT, FlxTextBorderStyle.OUTLINE, FlxColor.BLACK);
		scrollFactor.set();
		borderSize = 1.25;
		this.color = colour;
		_trace = text;
		underlay = new FlxSprite().makeGraphic(1, 1, FlxColor.WHITE);
		underlay.color = FlxColor.BLACK;
		underlay.alpha = 0;
		underlay.scrollFactor.set();
	}

	public function setText(input:String, colour:FlxColor = FlxColor.WHITE):Void {
		_trace = input;
		color = colour;
		dirtyText = true;
	}

	public function resetText():Void {
		traceCount++;
		disableTime = 4;
		alpha = 1;
	}

	override public function kill():Void {
		traceCount = 0;
		super.kill();
	}

	override public function update(elapsed:Float):Void {
		super.update(elapsed);
		disableTime -= elapsed;
		if (y >= FlxG.height || disableTime <= 0) kill();
		else if (disableTime < 1) alpha = disableTime;
	}

	override public function draw():Void {
		if (underlay.exists) {
			underlay.scale.set(textField.textWidth + UNDERLAY_PADDING * 2, height);
			underlay.updateHitbox();
			underlay.setPosition(x - UNDERLAY_PADDING / 2, y);
			underlay.camera = camera;
			underlay.alpha = alpha * 0.4;
			underlay.draw();
		}
		if (dirtyText) {
			text = '${traceCount > 1 ? '[$traceCount] - ' : ''}$_trace';
			dirtyText = false;
		}
		super.draw();
	}

	override public function destroy():Void {
		FlxDestroyUtil.destroy(underlay);
		super.destroy();
	}
}
