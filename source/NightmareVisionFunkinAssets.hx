package;

import haxe.io.Bytes;
import haxe.io.Path;
import openfl.display.BitmapData;
import openfl.media.Sound;
#if !sys
import openfl.utils.Assets;
#end
import flixel.FlxG;
import flixel.graphics.FlxGraphic;
import flixel.system.FlxAssets;
#if sys
import sys.FileSystem;
import sys.io.File;
#end
#if lime_vorbis
import lime.media.AudioBuffer;
import lime.media.vorbis.VorbisFile;
#end
using StringTools;

/** Owner-scoped source FunkinAssets API. The resolver accepts only paths
 * returned by this owner's Paths facade (including its explicit core subtree). */
@:keep
class NightmareVisionFunkinAssets {
	final paths:NightmareVisionPaths;
	public final cache:NightmareVisionFunkinAssetCache;

	public function new(paths:NightmareVisionPaths) {
		if (paths == null) throw '[nightmare-vision-assets] Missing selected owner paths';
		this.paths = paths;
		cache = paths.getOwnerAssetCache();
		paths.bindOwnerAssetFacade(this);
	}

	function resolve(path:String):Null<String> return paths.scopeAssetPath(path);

	public function parseJson(content:String, ?pos:haxe.PosInfos):Null<Any> {
		if (content == null) return null;
		try return haxe.Json.parse(content) catch (error:Dynamic) {
			trace('[nightmare-vision-json] failed to parse content: ' + Std.string(error));
			return null;
		}
	}

	public function parseJson5(content:String, ?pos:haxe.PosInfos):Null<Any> {
		if (content == null) return null;
		try {
			#if json5hx
			return haxe.Json5.parse(content);
			#else
			return haxe.Json.parse(content);
			#end
		} catch (error:Dynamic) {
			trace('[nightmare-vision-json5] failed to parse content: ' + Std.string(error));
			return null;
		}
	}

	public function getBytes(path:String):Bytes {
		var selected = resolve(path);
		if (selected == null) throw '[nightmare-vision-assets] Refused out-of-owner byte read: ' + path;
		#if sys
		if (!FileSystem.exists(selected) || FileSystem.isDirectory(selected))
			throw '[nightmare-vision-assets] Could not find file at path [' + selected + ']';
		return File.getBytes(selected);
		#else
		if (!FNFAssets.exists(selected)) throw '[nightmare-vision-assets] Could not find file at path [' + selected + ']';
		return FNFAssets.getBytes(selected);
		#end
	}

	public function getContentUnsafe(key:String, useCache:Bool = true):String {
		var selected = resolve(key);
		if (selected == null) return '';
		useCache = useCache && !paths.devModeEnabled();
		if (useCache && cache.currentTrackedTexts.exists(selected)) {
			cache.localTrackedAssets.push(selected);
			return cache.currentTrackedTexts.get(selected);
		}
		var text = readText(selected);
		if (text.length > 0 && useCache) cache.cacheData(selected, text);
		return text;
	}

	public function getContent(key:String, useCache:Bool = true):String {
		var text = getContentUnsafe(key, useCache);
		if (text.length == 0) trace('[nightmare-vision-assets] text (' + key + ') was not found; returning empty string');
		return text;
	}

	function readText(selected:String):String {
		#if sys
		if (!FileSystem.exists(selected) || FileSystem.isDirectory(selected)) return '';
		try return File.getContent(selected) catch (_:Dynamic) return '';
		#else
		if (!FNFAssets.exists(selected)) return '';
		try return FNFAssets.getText(selected) catch (_:Dynamic) return '';
		#end
	}

	public function getBitmapData(path:String, useCache:Bool = true):Null<BitmapData> {
		var selected = resolve(path);
		if (selected == null || !exists(selected)) return null;
		try return FNFAssets.getBitmapData(selected, useCache) catch (_:Dynamic) return null;
	}

	public function exists(path:String):Bool {
		var selected = resolve(path);
		if (selected == null) return false;
		#if sys
		return FileSystem.exists(selected);
		#else
		return FNFAssets.exists(selected);
		#end
	}

	public function readDirectory(directory:String):Array<String> {
		var selected = resolve(directory);
		if (selected == null || !isDirectory(selected)) return [];
		#if sys
		try return FileSystem.readDirectory(selected) catch (_:Dynamic) return [];
		#else
		var prefix = selected.endsWith('/') ? selected : selected + '/';
		var entries:Array<String> = [];
		for (asset in Assets.list()) {
			if (!asset.startsWith(prefix)) continue;
			var relative = asset.substr(prefix.length);
			var slash = relative.indexOf('/');
			var entry = slash < 0 ? relative : relative.substr(0, slash);
			if (entry != '' && !entries.contains(entry)) entries.push(entry);
		}
		return entries;
		#end
	}

	public function isDirectory(directory:String):Bool {
		var selected = resolve(directory);
		if (selected == null) return false;
		#if sys
		return FileSystem.exists(selected) && FileSystem.isDirectory(selected);
		#else
		return FNFAssets.isDirectory(selected);
		#end
	}

	public function getGraphicUnsafe(key:String, useCache:Bool = true, allowGPU:Bool = true):Null<FlxGraphic> {
		var selected = resolve(key);
		if (selected == null || !exists(selected) || isDirectory(selected)) return null;
		if (useCache && cache.currentTrackedGraphics.exists(selected)) {
			cache.localTrackedAssets.push(selected);
			return cache.currentTrackedGraphics.get(selected);
		}
		try {
			// FNFAssets.getBitmapData may already register this BitmapData under
			// its canonical disk-cache key. Re-wrappping it with the owner path
			// would create a second FlxGraphic that shares the same pixels; freeing
			// either wrapper would invalidate the other. Ask FNFAssets for the
			// canonical graphic, then let our owner cache track that exact object.
			var graphic = FNFAssets.getFlxGraphic(selected);
			return graphic == null ? null : cache.trackGraphic(selected, graphic, allowGPU);
		} catch (_:Dynamic) return null;
	}

	public function getGraphic(key:String, useCache:Bool = true, allowGPU:Bool = true):FlxGraphic {
		var graphic = getGraphicUnsafe(key, useCache, allowGPU);
		if (graphic != null) return graphic;
		trace('[nightmare-vision-assets] graphic (' + key + ') was not found; returning Flixel logo');
		return FlxG.bitmap.add('flixel/images/logo/default.png');
	}

	public function getSound(key:String, useCache:Bool = true):Sound {
		var sound = getSoundUnsafe(key, useCache);
		if (sound != null) return sound;
		trace('[nightmare-vision-assets] sound (' + key + ') was not found; returning beep');
		return FlxAssets.getSoundAddExtension('flixel/sounds/beep');
	}

	public function getSoundUnsafe(key:String, useCache:Bool = true):Null<Sound> {
		var selected = resolve(key);
		return selected == null ? null : loadSound(selected, useCache);
	}

	function loadSound(selected:String, useCache:Bool):Null<Sound> {
		if (!exists(selected) || isDirectory(selected)) return null;
		useCache = useCache && !paths.devModeEnabled();
		if (useCache && cache.currentTrackedSounds.exists(selected)) {
			cache.localTrackedAssets.push(selected);
			return cache.currentTrackedSounds.get(selected);
		}
		try {
			var sound = FNFAssets.getSound(selected);
			if (sound != null && useCache) cache.cacheSound(selected, sound);
			return sound;
		} catch (_:Dynamic) return null;
	}

	public function getVorbisSound(key:String):Null<Sound> {
		var selected = resolve(key);
		return selected == null ? null : getVorbisSoundAt(selected);
	}

	/** Release the owner cache only at owner teardown, after its scripts stop. */
	public function releaseOwnerAssets():Void paths.releaseOwnerAssets();

	function getVorbisSoundAt(path:String):Null<Sound> {
		if (path == null || Path.extension(path).toLowerCase() != 'ogg') return null;
		#if !lime_vorbis
		return null;
		#else
		#if sys
		if (!FileSystem.exists(path) || FileSystem.isDirectory(path)) return null;
		#end
		try {
			var vorbisFile = VorbisFile.fromFile(path);
			if (vorbisFile == null) return null;
			return Sound.fromAudioBuffer(AudioBuffer.fromVorbisFile(vorbisFile));
		} catch (_:Dynamic) return null;
		#end
	}
}
