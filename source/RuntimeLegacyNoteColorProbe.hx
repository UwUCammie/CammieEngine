package;

#if sys
import flixel.FlxG;
import flixel.FlxSprite;
import lime.app.Application;
import sys.io.File;

/** Opt-in generated shader fixture using the same shared per-object draw path. */
@:access(RuntimeSmokeHarness)
class RuntimeLegacyNoteColorProbe {
	static var camera:flixel.FlxCamera;
	static var started:Bool = false;
	static var renders:Int = 0;
	static var pass:Int = 0;
	static var sprites:Array<FlxSprite> = [];
	static var graphics:Array<NightmareVisionRGBGraphics> = [];
	static var cases:Array<Dynamic> = [];
	public static function enabled():Bool
		return RuntimeSmokeHarness.enabled() && Sys.getEnv('CAMMIE_LEGACY_NOTE_COLOR_SMOKE') == '1';
	static function check(value:Bool, message:String):Void if (!value) throw message;
	public static function tick():Void {
		if (!enabled() || started || RuntimeSmokeHarness.finished) return;
		if (!Std.isOfType(FlxG.state, FreeplayState) || ImportRefreshManager.browseTick().busy) return;
		started = true;
		try {
			check(FlxG.sound.muted && Sys.getEnv('CAMMIE_SMOKE_SAVE_ROOT') != null, 'Muted private saves required');
			var save:Dynamic = {getField:function(key:String):Dynamic return null, setField:function(key:String,value:Dynamic):Void {}};
			var first = new NightmareVisionClientPrefs('assets/imported_mods/generated-hsv-a', save);
			var other = new NightmareVisionClientPrefs('assets/imported_mods/generated-hsv-b', save);
			first.view.arrowHSV[0] = [120,0,0];
			check(other.view.arrowHSV[0][0] == 0, 'Owner HSV tables share mutable rows');
			cases = [
				{mode:'hsv', row:NightmareVisionLegacyNoteColors.laneHSV(first.view,0), alpha:1., flash:0.},
				{mode:'hsv', row:NightmareVisionLegacyNoteColors.laneHSV(other.view,0), alpha:1., flash:0.},
				{mode:'hsv', row:[0,-50,-50], alpha:1., flash:0.},
				{mode:'hsv', row:[0,0,0], alpha:0.5, flash:0.},
				{mode:'hsv', row:[0,0,0], alpha:1., flash:0.5},
				{mode:'hsl', row:[120,0,50], alpha:1., flash:0.},
				{mode:'hsl', row:[0,-100,0], alpha:1., flash:0.},
				{mode:'rgb', row:[0,0,0], alpha:1., flash:0.}
			];
			camera = new flixel.FlxCamera(); camera.bgColor = 0xFF000000;
			FlxG.cameras.add(camera,false);
			for (i in 0...cases.length) {
				var entry = cases[i];
				var sprite = new FlxSprite(80+(i%4)*250,200+Std.int(i/4)*200).makeGraphic(80,80,0xFFFF0000);
				sprite.cameras = [camera]; sprite.antialiasing = false; sprite.active = false;
				var rgb = new NightmareVisionRGBGraphics();
				if (entry.mode == 'hsv') {
					rgb.legacyHSV = new NightmareVisionLegacyColorSwap();
					NightmareVisionLegacyNoteColors.setHSV(rgb.legacyHSV, entry.row);
				} else if (entry.mode == 'hsl') {
					rgb.legacyHSL = new NightmareVisionHSLColorSwap();
					rgb.legacyHSL.hue = entry.row[0]/360;
					rgb.legacyHSL.saturation = entry.row[1]/100;
					rgb.legacyHSL.lightness = entry.row[2]/100;
				} else rgb.setColors([0x00FF00,0xFF0000,0x0000FF]);
				rgb.alpha = entry.alpha; rgb.flash = entry.flash; rgb.apply(sprite);
				FlxG.state.add(sprite); sprites.push(sprite); graphics.push(rgb);
			}
			Application.current.window.onRender.add(onRender,false,-1000);
		} catch(error:Dynamic) RuntimeSmokeHarness.fail('legacy-note-color',Std.string(error));
	}
	static function onRender(context:lime.graphics.RenderContext):Void {
		if (RuntimeSmokeHarness.finished || ++renders < 4) return;
		try {
			var image = Application.current.window.readPixels(); check(image != null,'No framebuffer');
			var path = 'tmp/legacy-note-color-native-' + pass + '.png'; File.saveBytes(path,image.encode());
			var sx = image.width/FlxG.width, sy = image.height/FlxG.height;
			var pixels:Array<Int> = [];
			for (sprite in sprites) pixels.push(image.getPixel(Std.int((sprite.x+40)*sx),Std.int((sprite.y+40)*sy),lime.graphics.PixelFormat.ARGB32));
			RuntimeSmokeHarness.emit('legacy_note_color_pixels',{pass:pass,cases:cases,pixels:pixels,path:path,
				shaders:[for(sprite in sprites) Type.getClassName(Type.getClass(sprite.shader))]});
			if (pass == 0) {
				graphics[0].legacyHSV.hue = 2/3;
				graphics[0].apply(sprites[0]); cases[0].row = [240,0,0];
				pass++; renders = 0; return;
			}
			Application.current.window.onRender.remove(onRender);
			for (sprite in sprites) {FlxG.state.remove(sprite,true);sprite.destroy();}
			sprites = []; graphics = [];
			FlxG.cameras.remove(camera,true); camera = null;
			RuntimeSmokeHarness.emit('legacy_note_color_native_verified',{generatedAssets:true,receiptImport:false,ownerIsolation:true});
			RuntimeSmokeHarness.succeed();
		} catch(error:Dynamic) {
			Application.current.window.onRender.remove(onRender);
			RuntimeSmokeHarness.fail('legacy-note-color-render',Std.string(error));
		}
	}
}
#end
