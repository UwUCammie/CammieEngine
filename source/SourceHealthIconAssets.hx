package;

import flixel.FlxG;
import flixel.graphics.FlxGraphic;

/** Owner-local icon graphics, keeping source GPU disposal away from native caches. */
@:access(openfl.display.BitmapData)
class SourceHealthIconAssets {
	var graphics:Map<String, FlxGraphic> = [];
	var released:Bool = false;
	public function new() {}
	public function psychImage(key:String, load:Void->FlxGraphic, allowGPU:Bool, cacheOnGPU:Bool):FlxGraphic {
		if (released) throw '[source-icon] Asset owner has been released';
		if (graphics.exists(key)) return graphics.get(key);
		var original = load();
		if (original == null) return null;
		var bitmap = original.bitmap.clone();
		if (allowGPU && cacheOnGPU && bitmap.image != null) {
			bitmap.lock();
			if (bitmap.__texture == null) {
				bitmap.image.premultiplied = true;
				bitmap.getTexture(FlxG.stage.context3D);
			}
			bitmap.getSurface();
			bitmap.disposeImage();
			bitmap.image.data = null;
			bitmap.image = null;
			bitmap.readable = true;
		}
		var graphic = FlxGraphic.fromBitmapData(bitmap, false, null, false);
		graphic.persist = true;
		graphic.destroyOnNoUse = false;
		graphics.set(key, graphic);
		return graphic;
	}
	public function release():Void {
		if (released) return;
		released = true;
		for (graphic in graphics) if (graphic != null) graphic.destroy();
		graphics.clear();
	}
}
