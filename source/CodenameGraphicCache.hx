package;

import flixel.FlxG;
import flixel.FlxSprite;
import flixel.FlxState;
import flixel.graphics.FlxGraphic;
import haxe.io.Path;

/** Owner-scoped implementation of Codename's MusicBeatState graphicCache.
	The original engine keeps a GraphicCacheSprite on each state, draws queued
	graphics before scene members, then releases its temporary use-count holds
	when the state dies. This instance follows the same rules and is released
	with the Codename interpreter that exposed it.
*/
@:keep
class CodenameGraphicCache extends FlxSprite {
	public final paths:CodenamePaths;
	public var cachedGraphics:Array<FlxGraphic> = [];
	public var nonRenderedCachedGraphics:Array<FlxGraphic> = [];
	var parentState:FlxState;
	var released:Bool = false;
	var informationalNotes:Map<String, Bool> = new Map();

	public function new(paths:CodenamePaths) {
		super();
		if (paths == null) throw '[codename-graphic-cache] Missing owner path resolver';
		this.paths = paths;
		alpha = 0.00001;
	}

	/** Validate the selected-owner path before trying Flixel's raster loader.
		Codename's source implementation quietly ignores a null FlxGraphic; MP4
		video paths therefore remain the responsibility of FlxVideoSprite.load.
	*/
	public function cache(path:String):Void {
		ensureLive();
		var resolved = paths.getPath(path);
		var extension = '.' + Path.extension(resolved).toLowerCase();
		if (!isRasterExtension(extension)) {
			noteOnce(resolved, 'The graphic cache skips non-raster media; playback APIs still handle this owner-scoped path.');
			return;
		}

		var graphic:FlxGraphic = null;
		try graphic = paths.graphic(resolved) catch (error:Dynamic) {
			trace('[codename-graphic-cache-info] Could not prewarm ' + resolved + ': ' + Std.string(error));
			return;
		}
		if (graphic == null) {
			noteOnce(resolved, 'No FlxGraphic was produced for this owner-scoped asset.');
			return;
		}
		cacheGraphic(graphic);
	}

	/** Hold an already resolved FlxGraphic just like Codename's source API. */
	public function cacheGraphic(graphic:FlxGraphic):Void {
		ensureLive();
		if (graphic == null) return;
		// If the graphic carries an asset key, reject cross-owner keys. Memory
		// graphics without an asset key remain valid inputs to cacheGraphic.
		if (graphic.assetsKey != null) {
			try paths.getPath(graphic.assetsKey) catch (_:Dynamic) {
				noteOnce(graphic.assetsKey, 'Skipped a FlxGraphic whose asset key is outside the selected owner.');
				return;
			}
		}
		graphic.incrementUseCount();
		graphic.destroyOnNoUse = false;
		cachedGraphics.push(graphic);
		nonRenderedCachedGraphics.push(graphic);
		mountForDraw();
	}

	function isRasterExtension(extension:String):Bool {
		return extension == '.png' || extension == '.jpg' || extension == '.jpeg'
			|| extension == '.bmp';
	}

	function noteOnce(key:String, message:String):Void {
		if (informationalNotes.exists(key)) return;
		informationalNotes.set(key, true);
		trace('[codename-graphic-cache-info] ' + message + ' (' + key + ')');
	}

	function mountForDraw():Void {
		if (parentState != null) return;
		var state = FlxG.state;
		if (!Std.isOfType(state, FlxState)) {
			noteOnce('state', 'Graphic prewarming has no active FlxState; cached references are retained until interpreter cleanup.');
			return;
		}
		parentState = cast state;
		parentState.insert(0, this);
	}

	function ensureLive():Void {
		if (released) throw '[codename-graphic-cache] This owner cache has been released';
	}

	/** Drain once before ordinary state members draw so Flixel uploads queued
		bitmaps before the stage uses them, matching MusicBeatState.draw ordering.
	*/
	@:keep
	public override function draw():Void {
		if (released) return;
		while (nonRenderedCachedGraphics.length > 0) {
			var graphic = nonRenderedCachedGraphics.shift();
			loadGraphic(graphic);
			drawComplex(FlxG.camera);
		}
	}

	/** Explicit interpreter cleanup removes this sprite from its state and
		releases every use-count hold. */
	public function release():Void {
		if (released) return;
		if (parentState != null) try parentState.remove(this, true) catch (_:Dynamic) {}
		parentState = null;
		destroy();
	}

	public override function destroy():Void {
		if (released) return;
		released = true;
		for (graphic in cachedGraphics) if (graphic != null) {
			graphic.destroyOnNoUse = true;
			graphic.decrementUseCount();
		}
		cachedGraphics.resize(0);
		nonRenderedCachedGraphics.resize(0);
		informationalNotes.clear();
		graphic = null;
		parentState = null;
		super.destroy();
	}
}
