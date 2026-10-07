package;

import flixel.FlxG;
import flixel.system.scaleModes.RatioScaleMode;

/** Owner-installed copy of the donor ratio scale adapter. */
@:keep
class NightmareVisionRatioScaleMode extends RatioScaleMode {
	@:isVar public var width(get, set):Null<Int> = null;
	@:isVar public var height(get, set):Null<Int> = null;

	override public function updateGameSize(Width:Int, Height:Int):Void {
		var ratio:Float = width / height;
		var realRatio:Float = Width / Height;
		var scaleY:Bool = realRatio < ratio;
		if (fillScreen) scaleY = !scaleY;

		if (scaleY) {
			gameSize.x = Width;
			gameSize.y = Math.floor(gameSize.x / ratio);
		} else {
			gameSize.y = Height;
			gameSize.x = Math.floor(gameSize.y * ratio);
		}

		@:privateAccess {
			for (camera in FlxG.cameras.list) {
				if (camera.width == FlxG.width && camera.height == FlxG.height) {
					camera.width = width;
					camera.height = height;
				}
			}
			FlxG.width = width;
			FlxG.height = height;
		}
	}

	public function resetSize():Void {
		width = null;
		height = null;
	}

	inline function get_width():Null<Int> return this.width == null ? FlxG.initialWidth : this.width;
	inline function get_height():Null<Int> return this.height == null ? FlxG.initialHeight : this.height;

	function set_width(value:Null<Int>):Null<Int> {
		this.width = value;
		@:privateAccess if (FlxG.game != null) FlxG.game.onResize(null);
		return value;
	}

	function set_height(value:Null<Int>):Null<Int> {
		this.height = value;
		@:privateAccess if (FlxG.game != null) FlxG.game.onResize(null);
		return value;
	}
}
