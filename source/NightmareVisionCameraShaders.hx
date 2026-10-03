package;

import flixel.FlxCamera;
import flixel.graphics.tile.FlxGraphicsShader;
import openfl.filters.BitmapFilter;
import openfl.filters.ShaderFilter;

/** The addShader/removeShader camera methods supplied by Nightmare Vision's
 * FlxCamera build macro. Filters belong to the script that attached them. */
class NightmareVisionCameraShaders {
	final owned:Array<{camera:FlxCamera, filter:ShaderFilter}> = [];

	public function new() {}
	public function isCamera(value:Dynamic):Bool return Std.isOfType(value, FlxCamera);

	public function add(camera:FlxCamera, shader:Dynamic):Void {
		if (camera == null || shader == null) return;
		if (!Std.isOfType(shader, FlxGraphicsShader))
			throw '[nightmare-vision-camera-shader] addShader requires a FlxGraphicsShader';
		var filter = new ShaderFilter(cast shader);
		var filters:Array<BitmapFilter> = camera.filters == null ? [] : camera.filters.copy();
		filters.push(filter);
		camera.filters = filters;
		owned.push({camera:camera, filter:filter});
	}

	public function remove(camera:FlxCamera, shader:Dynamic):Bool {
		if (camera == null || camera.filters == null) return false;
		var filters:Array<BitmapFilter> = camera.filters.copy();
		for (filter in filters) {
			if (Std.isOfType(filter, ShaderFilter) && (cast filter:ShaderFilter).shader == shader) {
				filters.remove(filter);
				camera.filters = filters;
				forget(camera, cast filter);
				return true;
			}
		}
		return false;
	}

	function forget(camera:FlxCamera, filter:ShaderFilter):Void {
		for (entry in owned.copy())
			if (entry.camera == camera && entry.filter == filter) owned.remove(entry);
	}

	public function release():Void {
		for (entry in owned) {
			if (entry.camera == null || entry.camera.filters == null) continue;
			var filters = entry.camera.filters.copy();
			if (filters.remove(entry.filter)) entry.camera.filters = filters;
		}
		owned.resize(0);
	}
}
