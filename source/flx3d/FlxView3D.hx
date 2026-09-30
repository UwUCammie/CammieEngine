package flx3d;

#if THREE_D_SUPPORT
import away3d.containers.View3D;
import away3d.library.assets.IAsset;
import flixel.FlxG;
import openfl.display.BitmapData;
import RuntimeSmokeHarness;
#end
import flixel.FlxSprite;

/**
 * @author Ne_Eo
 * @see https://twitter.com/Ne_Eo_Twitch
 *
 * @author lunarcleint
 * @see https://twitter.com/lunarcleint
 */
class FlxView3D extends FlxSprite
{
	#if THREE_D_SUPPORT
	@:noCompletion private var bmp:BitmapData;
	private var destroyed3DView:Bool = false;
	private var smokeOutputFrames:Int = 0;

	/**
	 * The Away3D View
	 */
	public var view:View3D;

	/**
	 * Set this flag to true to force the View3D to update during the `draw()` call.
	 */
	public var dirty3D:Bool = true;

	/**
	 * Creates a new instance of a View3D from Away3D and renders it as a FlxSprite
	 * ! Call Flx3DUtil.is3DAvailable(); to make sure a 3D stage is usable
	 * @param x
	 * @param y
	 * @param width Leave as -1 for screen width
	 * @param height Leave as -1 for screen height
	 */
	public function new(x:Float = 0, y:Float = 0, width:Int = -1, height:Int = -1)
	{
		super(x, y);

		view = new View3D();
		view.visible = false;

		view.width = width == -1 ? FlxG.width : width;
		view.height = height == -1 ? FlxG.height : height;

		view.backgroundAlpha = 0;
		FlxG.stage.addChildAt(view, 0);

		bmp = new BitmapData(Std.int(view.width), Std.int(view.height), true, 0x0);
		loadGraphic(bmp);
	}

	/**
	 * Disposes (destroys) the asset and returns null
	 * @param obj
	 * @return T null
	 */
	public static function dispose<T:IAsset>(obj:Null<T>):T
	{
		return Flx3DUtil.dispose(obj);
	}

	/**
	 * Disposes of all the Away3D assets associated with the FlxView3D
	 */
	override function destroy():Void
	{
		if (destroyed3DView) return;
		destroyed3DView = true;
		var oldView = view;
		var oldBitmap = bmp;
		var oldGraphic = graphic;
		if (oldView != null && oldView.parent != null) oldView.parent.removeChild(oldView);
		view = null;
		bmp = null;
		super.destroy();

		// FlxSprite releases its graphic on destroy. Remove it explicitly only if
		// Flixel did not already dispose it through the use-count path.
		if (oldGraphic != null && !oldGraphic.isDestroyed)
			FlxG.bitmap.remove(oldGraphic);
		else if (oldGraphic == null && oldBitmap != null)
			oldBitmap.dispose();

		if (oldView != null) oldView.dispose();
	}

	@:noCompletion override function draw()
	{
		super.draw();

		if (dirty3D && view != null && bmp != null)
		{
			view.visible = false;
			FlxG.stage.addChildAt(view, 0);

			var old = FlxG.game.filters;
			FlxG.game.filters = null;

			// This wrapper exposes the Away3D view as a sprite, so it must render to
			// its authored-size bitmap rather than draw into Stage3D's backbuffer.
			view.shareContext = false;
			view.renderer.queueSnapshot(bmp);
			view.render();

			if (RuntimeSmokeHarness.enabled())
			{
				smokeOutputFrames++;
				if (smokeOutputFrames == 1 || smokeOutputFrames == 2 || smokeOutputFrames == 60
					|| smokeOutputFrames == 300 || smokeOutputFrames == 360 || smokeOutputFrames == 420)
					traceSmokeSnapshot();
			}

			FlxG.game.filters = old;
			FlxG.stage.removeChild(view);
		}
	}

	private function traceSmokeSnapshot():Void
	{
		var alphaSamples = 0;
		var nonWhiteSamples = 0;
		var sampleCount = 0;
		for (sampleY in 1...6)
		{
			for (sampleX in 1...6)
			{
				var x = Std.int((bmp.width - 1) * sampleX / 6);
				var y = Std.int((bmp.height - 1) * sampleY / 6);
				var pixel = bmp.getPixel32(x, y);
				var alpha = (pixel >>> 24) & 0xFF;
				var red = (pixel >>> 16) & 0xFF;
				var green = (pixel >>> 8) & 0xFF;
				var blue = pixel & 0xFF;
				sampleCount++;
				if (alpha > 0)
				{
					alphaSamples++;
					if (red < 250 || green < 250 || blue < 250)
						nonWhiteSamples++;
				}
			}
		}
		RuntimeSmokeHarness.markStep('3d-render-output:frame=' + smokeOutputFrames
			+ ':mode=snapshot:readback=true'
			+ ':size=' + bmp.width + 'x' + bmp.height
			+ ':view=' + Std.int(view.width) + 'x' + Std.int(view.height)
			+ ':logical=' + width + 'x' + height + ':samples=' + sampleCount
			+ ':alpha=' + alphaSamples + ':nonWhite=' + nonWhiteSamples);
		if (smokeOutputFrames == 2 || smokeOutputFrames == 60 || smokeOutputFrames == 300
			|| smokeOutputFrames == 360 || smokeOutputFrames == 420)
			traceSmokeSceneOrder();
	}

	private function traceSmokeSceneOrder():Void
	{
		var state = PlayState.instance;
		if (state == null) return;
		var describe = function(name:String, node:Dynamic):String {
			if (node == null) return name + '=-';
			var index = state.members.indexOf(cast node);
			var cameras:Array<Dynamic> = cast Reflect.field(node, 'cameras');
			var cameraNames:Array<String> = [];
			if (cameras == null) cameraNames.push('inherit');
			else for (camera in cameras) {
				if (camera == FlxG.camera) cameraNames.push('game');
				else if (camera == state.camHUD) cameraNames.push('hud');
				else cameraNames.push('other');
			}
			return name + '=' + index + ':visible=' + Std.string(Reflect.field(node, 'visible'))
				+ ':alpha=' + Std.string(Reflect.field(node, 'alpha'))
				+ ':cameras=' + cameraNames.join('+')
				+ ':zIndex=' + Std.string(Reflect.field(node, 'zIndex'));
		};
		RuntimeSmokeHarness.markStep('codename-scene-live-order:drawFrame=' + smokeOutputFrames
			+ ':' + describe('view', this)
			+ ':' + describe('gf', state.gf)
			+ ':' + describe('dad', state.dad)
			+ ':' + describe('bf', state.boyfriend));
	}

	@:noCompletion override function set_width(newWidth:Float):Float
	{
		super.set_width(newWidth);
		return view != null ? view.width = width : width;
	}

	@:noCompletion override function set_height(newHeight:Float):Float
	{
		super.set_height(newHeight);
		return view != null ? view.height = height : height;
	}
	#end
}
