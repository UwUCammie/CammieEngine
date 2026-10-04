package;

import openfl.display.BitmapData;
import openfl.media.Sound;
import openfl.utils.Assets;
import flixel.FlxG;
import flixel.graphics.FlxGraphic;

/** Source-shaped per-owner FunkinAssets cache. Every key passes through the
 * owning Paths resolver, so cache removal cannot evict another import's data. */
@:keep
@:access(openfl.display.BitmapData)
class NightmareVisionFunkinAssetCache {
	final paths:NightmareVisionPaths;
	public final currentTrackedGraphics:NightmareVisionAssetCacheMap<FlxGraphic> = new NightmareVisionAssetCacheMap();
	public final currentTrackedSounds:NightmareVisionAssetCacheMap<Sound> = new NightmareVisionAssetCacheMap();
	public final currentTrackedTexts:NightmareVisionAssetCacheMap<String> = new NightmareVisionAssetCacheMap();
	public final localTrackedAssets:Array<String> = [];
	var released:Bool = false;

	public function new(paths:NightmareVisionPaths) this.paths = paths;

	public function clearStoredMemory():Void {
		ensureAlive();
		for (key in currentTrackedSounds.keys())
			if (!localTrackedAssets.contains(key) && !currentTrackedSounds.permanentKeys.contains(key))
				removeFromCache(key);
		localTrackedAssets.resize(0);
	}

	public function clearUnusedMemory():Void {
		ensureAlive();
		for (key in currentTrackedGraphics.keys())
			if (!localTrackedAssets.contains(key) && !currentTrackedGraphics.permanentKeys.contains(key))
				removeFromCache(key);
		for (key in currentTrackedTexts.keys())
			if (!localTrackedAssets.contains(key) && !currentTrackedTexts.permanentKeys.contains(key))
				removeFromCache(key);
	}

	public function removeFromCache(key:String, disposeToo:Bool = true):Bool {
		ensureAlive();
		var selected = cacheKey(key);
		if (selected == null) return false;
		if (currentTrackedGraphics.exists(selected)) {
			var graphic = currentTrackedGraphics.get(selected);
			if (disposeToo) disposeGraphic(graphic);
			currentTrackedGraphics.remove(selected);
			return true;
		}
		if (currentTrackedSounds.exists(selected)) {
			if (disposeToo) Assets.cache.clear(selected);
			currentTrackedSounds.remove(selected);
			return true;
		}
		if (currentTrackedTexts.exists(selected)) {
			if (disposeToo) Assets.cache.clear(selected);
			currentTrackedTexts.remove(selected);
			return true;
		}
		return false;
	}

	public function disposeGraphic(graphic:FlxGraphic):Void {
		ensureAlive();
		if (graphic == null) return;
		for (key in currentTrackedGraphics.keys())
			if (currentTrackedGraphics.get(key) == graphic) {
				if (graphic.bitmap != null && graphic.bitmap.__texture != null)
					graphic.bitmap.__texture.dispose();
				FlxG.bitmap.remove(graphic);
				return;
			}
	}

	public function cacheBitmap(key:String, bitmap:BitmapData, allowGPU:Bool = true):Null<FlxGraphic> {
		ensureAlive();
		var selected = cacheKey(key);
		if (selected == null || bitmap == null) return null;
		return cacheBitmapAt(selected, bitmap, allowGPU, nativeOwnerKey(selected));
	}

	/** Track a native canonical graphic returned by FNFAssets without creating
	 * another FlxGraphic over the same BitmapData. The source-facing cache remains
	 * keyed by its owner asset path. */
	public function trackGraphic(key:String, graphic:FlxGraphic, allowGPU:Bool = true):Null<FlxGraphic> {
		ensureAlive();
		var selected = paths.scopeAssetPath(key);
		if (selected == null || graphic == null) return null;
		prepareGraphic(graphic, allowGPU);
		currentTrackedGraphics.set(selected, graphic);
		localTrackedAssets.push(selected);
		return graphic;
	}

	/** Source Paths.imageFromURL caches downloaded PNGs by URL. Remote keys are
	 * accepted only through this explicit entry point, never through filesystem
	 * path resolution. */
	public function cacheRemoteBitmap(url:String, bitmap:BitmapData, allowGPU:Bool = true):Null<FlxGraphic> {
		ensureAlive();
		if (!isRemotePng(url) || bitmap == null) return null;
		if (currentTrackedGraphics.exists(url)) return currentTrackedGraphics.get(url);
		return cacheBitmapAt(url, bitmap, allowGPU, nativeOwnerKey(url));
	}

	function cacheBitmapAt(key:String, bitmap:BitmapData, allowGPU:Bool, nativeKey:String):Null<FlxGraphic> {
		if (allowGPU && paths.gpuCachingEnabled()) bitmap.disposeImage();
		var graphic = FlxG.bitmap.add(bitmap, false, nativeKey);
		if (graphic != null) {
			graphic.persist = true;
			graphic.destroyOnNoUse = false;
			currentTrackedGraphics.set(key, graphic);
			localTrackedAssets.push(key);
		}
		return graphic;
	}

	function prepareGraphic(graphic:FlxGraphic, allowGPU:Bool):Void {
		if (graphic == null) return;
		if (allowGPU && paths.gpuCachingEnabled() && graphic.bitmap != null)
			graphic.bitmap.disposeImage();
		graphic.persist = true;
		graphic.destroyOnNoUse = false;
	}

	/** Native FlxG.bitmap is process-global. Keep source URLs and arbitrary
	 * source cache keys distinct between imported owners in that cache. */
	function nativeOwnerKey(key:String):String
		return 'nightmare-vision:' + paths.root + ':' + key;

	public function cacheSound(key:String, sound:Sound):Null<Sound> {
		ensureAlive();
		var selected = paths.scopeAssetPath(key);
		if (selected == null || sound == null) return null;
		currentTrackedSounds.set(selected, sound);
		localTrackedAssets.push(selected);
		return sound;
	}

	public function cacheData(key:String, data:String):Null<String> {
		ensureAlive();
		var selected = paths.scopeAssetPath(key);
		if (selected == null || data == null) return null;
		currentTrackedTexts.set(selected, data);
		localTrackedAssets.push(selected);
		return data;
	}

	/** Drop this facade's tracked references after its owner leaves gameplay. */
	public function release():Void {
		if (released) return;
		for (key in [for (key in currentTrackedGraphics.keys()) key]) removeFromCache(key);
		for (key in [for (key in currentTrackedSounds.keys()) key]) removeFromCache(key);
		for (key in [for (key in currentTrackedTexts.keys()) key]) removeFromCache(key);
		localTrackedAssets.resize(0);
		released = true;
	}

	/** Async URL callbacks retain this facade after the selected owner is torn
	 * down; callers can discard the decoded bitmap instead of repopulating a
	 * released cache. */
	public inline function isReleased():Bool return released;

	public function toString():String
		return 'Bmp Cache: ' + [for (key in currentTrackedGraphics.keys()) key]
			+ '\nSnd Cache: ' + [for (key in currentTrackedSounds.keys()) key]
			+ '\nData Cache: ' + [for (key in currentTrackedTexts.keys()) key];

	function ensureAlive():Void {
		if (released) throw '[nightmare-vision-assets] Owner cache has been released';
	}

	function cacheKey(key:String):Null<String> {
		var selected = paths.scopeAssetPath(key);
		return selected == null && isRemotePng(key) ? key : selected;
	}

	static function isRemotePng(key:String):Bool {
		if (key == null || key.indexOf('\x00') >= 0 || !StringTools.contains(key, '.png')) return false;
		return StringTools.startsWith(key, 'https://') || StringTools.startsWith(key, 'http://');
	}
}

/** Small public-map facade matching the source FunkinCache.CacheMap surface. */
@:keep
class NightmareVisionAssetCacheMap<T> {
	public var cache:Map<String, T> = new Map();
	public final permanentKeys:Array<String> = [];

	public function new() {}
	public function get(key:String):Null<T> return cache.get(key);
	public function exists(key:String):Bool return cache.exists(key);
	public function set(key:String, value:T):Void cache.set(key, value);
	public function remove(key:String):Bool return cache.remove(key);
	public function keys():Iterator<String> return cache.keys();
	public function addPermanentKey(key:String):Void if (!permanentKeys.contains(key)) permanentKeys.push(key);
}
