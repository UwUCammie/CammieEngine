package;

import lime.app.Future;
import lime.app.Promise;
import lime.graphics.Image;
import lime.media.AudioBuffer;
import lime.media.vorbis.VorbisFile;
import lime.text.Font as LimeFont;
import openfl.display.BitmapData;
import openfl.events.Event;
import openfl.media.Sound;
import openfl.text.Font;
import openfl.utils.AssetType;
import openfl.utils.Assets as OpenFlAssets;
import openfl.utils.ByteArray;
import PsychOwnerAssetPath.PsychOwnerAssetPathResult;
import PsychOwnerAssetLibraryCache.PsychOwnerAssetLibraryAssetView;
import PsychOwnerAssetLibraryCache.PsychOwnerOpenFlAssetCache;
import RuntimeOwnerAssetIdentity;

using StringTools;

@:access(openfl.text.Font)
@:access(openfl.display.BitmapData)
@:access(openfl.utils.Assets)
/** OpenFL Assets facade that keeps Psych file reads inside the selected import. */
class PsychOwnerOpenFlAssets {
	public static function create(ownerRoot:String):Dynamic {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == '')
			throw '[psych-assets] A valid selected import owner root is required';
		var engine = 'Psych Engine';
		var scope = 'package';
		var proxy:Dynamic = {};
		Reflect.setField(proxy, 'cache', PsychOwnerAssetLibraryCache.openFlAssetCacheForOwner(
			owner, engine, scope, OpenFlAssets.cache));
		var ownerCache:PsychOwnerOpenFlAssetCache = cast Reflect.field(proxy, 'cache');
		Reflect.setField(proxy, 'exists', function(id:String, ?type:AssetType):Bool {
			var resolved = resolve(owner, id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return OpenFlAssets.exists(id, type) || (resolved.path != null && FNFAssets.exists(resolved.path));
		});
		Reflect.setField(proxy, 'getText', function(id:String):String {
			var resolved = required(owner, id, 'TEXT');
			var indexed = ownerLibraryAsset(owner, id, 'TEXT');
			if (indexed != null) return indexed.library.getText(indexed.id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !OpenFlAssets.exists(id, AssetType.TEXT)))
				return FNFAssets.getText(resolved.path);
			return OpenFlAssets.getText(id);
		});
		Reflect.setField(proxy, 'getBytes', function(id:String):ByteArray {
			var resolved = required(owner, id, 'BINARY');
			var indexed = ownerLibraryAsset(owner, id, 'BINARY');
			if (indexed != null) return ByteArray.fromBytes(indexed.library.getBytes(indexed.id));
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !OpenFlAssets.exists(id, AssetType.BINARY)))
				return ByteArray.fromBytes(FNFAssets.getBytes(resolved.path));
			return OpenFlAssets.getBytes(id);
		});
		Reflect.setField(proxy, 'getBitmapData', function(id:String, ?useCache:Bool = true):BitmapData {
			var indexedCacheId = ownerIndexCacheId(owner, id, 'IMAGE');
			if (indexedCacheId != null && useCache && ownerCache != null && ownerCache.enabled
				&& ownerCache.hasBitmapData(indexedCacheId)) {
				var cached = ownerCache.getBitmapData(indexedCacheId);
				if (OpenFlAssets.isValidBitmapData(cached)) return cached;
			}
			var resolved = required(owner, id, 'IMAGE');
			var indexed = ownerLibraryAsset(owner, id, 'IMAGE');
			if (indexed != null) {
				var cache = PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
				if (useCache && cache.enabled && cache.hasBitmapData(id)) {
					var cached = cache.getBitmapData(id);
					if (OpenFlAssets.isValidBitmapData(cached)) return cached;
				}
				var image:Image = cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
					toLimeAssetType(AssetType.IMAGE), false);
				var bitmap = image == null ? null : BitmapData.fromImage(image);
				if (bitmap != null) bitmap.__asset = true;
				if (bitmap != null && useCache && cache.enabled)
					PsychOwnerAssetLibraryCache.storeOpenFlBitmapData(indexed.identity, id, bitmap);
				return bitmap;
			}
			if (!resolved.owned && OpenFlAssets.exists(id, AssetType.IMAGE))
				return OpenFlAssets.getBitmapData(id, useCache);
			var key = ownerCacheKey(owner, id, 'IMAGE', resolved.path);
			if (useCache && ownerCache != null && ownerCache.enabled && ownerCache.hasBitmapData(key)) {
				var cached = ownerCache.getBitmapData(key);
				if (cached != null) return cached;
			}
			var bitmap = FNFAssets.getBitmapData(resolved.path, useCache);
			if (bitmap != null && useCache && ownerCache != null && ownerCache.enabled)
				ownerCache.setBitmapData(key, bitmap);
			return bitmap;
		});
		Reflect.setField(proxy, 'getSound', function(id:String, ?useCache:Bool = true):Sound {
			return getSound(owner, id, useCache, 'SOUND', proxy);
		});
		Reflect.setField(proxy, 'getMusic', function(id:String, ?useCache:Bool = true):Sound {
			return getMusic(owner, id, useCache, proxy);
		});
		Reflect.setField(proxy, 'getFont', function(id:String, ?useCache:Bool = true):Font {
			var indexedCacheId = ownerIndexCacheId(owner, id, 'FONT');
			if (indexedCacheId != null && useCache && ownerCache != null && ownerCache.enabled
				&& ownerCache.hasFont(indexedCacheId)) {
				var cached = ownerCache.getFont(indexedCacheId);
				if (cached != null) return cached;
			}
			var resolved = required(owner, id, 'FONT');
			var indexed = ownerLibraryAsset(owner, id, 'FONT');
			if (indexed != null) {
				var cache = PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
				if (useCache && cache.enabled && cache.hasFont(id)) {
					var cached = cache.getFont(id);
					if (cached != null) return cached;
				}
				var limeFont:LimeFont = cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
					toLimeAssetType(AssetType.FONT), false);
				if (limeFont == null) return new Font();
				var font = new Font();
				font.__fromLimeFont(limeFont);
				if (useCache && cache.enabled) PsychOwnerAssetLibraryCache.storeOpenFlFont(indexed.identity, id, font);
				return font;
			}
			if (!resolved.owned && OpenFlAssets.exists(id, AssetType.FONT))
				return OpenFlAssets.getFont(id, useCache);
			var key = ownerCacheKey(owner, id, 'FONT', resolved.path);
			if (useCache && ownerCache != null && ownerCache.enabled && ownerCache.hasFont(key)) {
				var cached = ownerCache.getFont(key);
				if (cached != null) return cached;
			}
			var font = Font.fromBytes(ByteArray.fromBytes(FNFAssets.getBytes(resolved.path)));
			if (font != null && useCache && ownerCache != null && ownerCache.enabled)
				ownerCache.setFont(key, font);
			return font;
		});
		Reflect.setField(proxy, 'getPath', function(id:String):String {
			var resolved = resolve(owner, id, null);
			if (resolved.blocked || resolved.unavailable) return null;
			if (resolved.path != null && (resolved.owned || FNFAssets.exists(resolved.path))) return resolved.path;
			return OpenFlAssets.getPath(id);
		});
		Reflect.setField(proxy, 'isLocal', function(id:String, ?type:AssetType, ?useCache:Bool = true):Bool {
			var resolved = resolve(owner, id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return OpenFlAssets.isLocal(id, type, useCache);
		});
		Reflect.setField(proxy, 'list', function(?type:AssetType):Array<String> {
			return list(owner, engine, scope, type, null);
		});
		Reflect.setField(proxy, 'getLibrary', function(name:String):Dynamic {
			if (unsafeLibraryName(name)) throw '[psych-assets] OpenFL asset libraries cannot escape the selected owner';
			var identity = RuntimeOwnerAssetIdentity.acquire(owner, engine, scope);
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(name);
			var state = identity.libraryState(libraryName);
			if (state == 'declared') {
				if (identity.indexVersion < 2) return ownerLibrary(owner, engine, scope, name, proxy);
				return PsychOwnerAssetLibraryCache.getOpenFl(identity, libraryName);
			}
			if (state == 'unknown') throw '[psych-assets] Asset library identity is incomplete for selected owner: ' + name;
			return OpenFlAssets.getLibrary(name);
		});
		Reflect.setField(proxy, 'getMovieClip', function(id:String):Dynamic {
			if (unsafeMovieClipId(id)) throw '[psych-assets] OpenFL movie clips cannot escape the selected owner';
			var resolved = resolve(owner, id, 'MOVIE_CLIP');
			if (resolved.blocked || resolved.unavailable)
				throw '[psych-assets] Movie clip identity is unavailable in selected owner: ' + id;
			if (resolved.owned)
				throw '[psych-assets] Owner MovieClip bindings are unsupported by the file-backed asset facade: ' + id;
			return OpenFlAssets.getMovieClip(id);
		});
		Reflect.setField(proxy, 'hasLibrary', function(name:String):Bool {
			if (unsafeLibraryName(name)) return false;
			var state = RuntimeOwnerAssetIdentity.ownerLibraryState(owner, engine, scope,
				SourceLimeAssetIdentity.canonicalLibrary(name));
			if (state == 'declared') return true;
			if (state == 'unknown') return false;
			return OpenFlAssets.hasLibrary(name);
		});
		Reflect.setField(proxy, 'initBinding', function(className:String, ?instance:Dynamic):Void
			throw '[psych-assets] Dynamic OpenFL bindings are unsupported by the owner-scoped facade');
		Reflect.setField(proxy, 'addEventListener', function(type:String, listener:Dynamic,
			?useCapture:Bool = false, ?priority:Int = 0, ?useWeakReference:Bool = false):Void
			OpenFlAssets.addEventListener(type, listener, useCapture, priority, useWeakReference));
		Reflect.setField(proxy, 'dispatchEvent', function(event:Event):Bool return OpenFlAssets.dispatchEvent(event));
		Reflect.setField(proxy, 'hasEventListener', function(type:String):Bool return OpenFlAssets.hasEventListener(type));
		Reflect.setField(proxy, 'removeEventListener', function(type:String, listener:Dynamic, ?capture:Bool = false):Void
			OpenFlAssets.removeEventListener(type, listener, capture));
		Reflect.setField(proxy, 'loadBitmapData', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(owner, id, AssetType.IMAGE, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadBytes', function(id:String):Dynamic return load(owner, id, AssetType.BINARY, false, proxy));
		Reflect.setField(proxy, 'loadFont', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(owner, id, AssetType.FONT, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadMusic', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(owner, id, AssetType.MUSIC, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadSound', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(owner, id, AssetType.SOUND, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadText', function(id:String):Dynamic return load(owner, id, AssetType.TEXT, false, proxy));
		Reflect.setField(proxy, 'loadMovieClip', function(id:String):Dynamic {
			if (unsafeMovieClipId(id)) return Future.withError('[psych-assets] OpenFL movie clips cannot escape the selected owner');
			var resolved = resolve(owner, id, 'MOVIE_CLIP');
			if (resolved.blocked || resolved.unavailable)
				return Future.withError('[psych-assets] Movie clip identity is unavailable in selected owner: ' + id);
			if (resolved.owned)
				return Future.withError('[psych-assets] Owner MovieClip bindings are unsupported by the file-backed asset facade: ' + id);
			return OpenFlAssets.loadMovieClip(id);
		});
		Reflect.setField(proxy, 'loadLibrary', function(name:String):Dynamic {
			if (unsafeLibraryName(name)) return Future.withError('[psych-assets] OpenFL asset libraries cannot escape the selected owner');
			var identity = RuntimeOwnerAssetIdentity.acquire(owner, engine, scope);
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(name);
			var state = identity.libraryState(libraryName);
			if (state == 'declared') {
				if (identity.indexVersion < 2)
					return Future.withError('[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: ' + name);
				return PsychOwnerAssetLibraryCache.loadOpenFl(identity, libraryName);
			}
			if (state == 'unknown') return Future.withError('[psych-assets] Asset library identity is incomplete for selected owner: ' + name);
			return OpenFlAssets.loadLibrary(name);
		});
		Reflect.setField(proxy, 'registerBinding', function(className:String, library:Dynamic):Void
			throw '[psych-assets] Dynamic OpenFL bindings are unsupported by the owner-scoped facade');
		Reflect.setField(proxy, 'unregisterBinding', function(className:String, library:Dynamic):Void
			throw '[psych-assets] Dynamic OpenFL bindings are unsupported by the owner-scoped facade');
		Reflect.setField(proxy, 'registerLibrary', function(name:String, library:Dynamic):Void {
			guardGlobalLibraryMutation(owner, engine, scope, name, 'register');
			OpenFlAssets.registerLibrary(name, library);
		});
		Reflect.setField(proxy, 'unloadLibrary', function(name:String):Void {
			if (releaseOwnerLibrary(owner, engine, scope, name, 'unload', true)) return;
			guardGlobalLibraryMutation(owner, engine, scope, name, 'unload');
			OpenFlAssets.unloadLibrary(name);
		});
		return proxy;
	}

	static function getSound(owner:String, id:String, useCache:Bool, expectedType:String,
		proxy:Dynamic):Sound {
		var ownerCache:PsychOwnerOpenFlAssetCache = cast Reflect.field(proxy, 'cache');
		var indexedCacheId = ownerIndexCacheId(owner, id, expectedType);
		if (indexedCacheId != null && useCache && ownerCache != null && ownerCache.enabled
			&& ownerCache.hasSound(indexedCacheId)) {
			var cached = ownerCache.getSound(indexedCacheId);
			if (OpenFlAssets.isValidSound(cached)) return cached;
		}
		var resolved = required(owner, id, expectedType);
		var indexed = ownerLibraryAsset(owner, id, expectedType);
		if (indexed != null) {
			var cache = PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
			if (useCache && cache.enabled && cache.hasSound(id)) {
				var cached = cache.getSound(id);
				if (OpenFlAssets.isValidSound(cached)) return cached;
			}
			var audio:AudioBuffer = cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
				toLimeAssetType(AssetType.SOUND), false);
			var sound = audio == null ? null : Sound.fromAudioBuffer(audio);
			if (sound != null && useCache && cache.enabled)
				PsychOwnerAssetLibraryCache.storeOpenFlSound(indexed.identity, id, sound);
			return sound;
		}
		if (!resolved.owned && OpenFlAssets.exists(id, AssetType.SOUND))
			return expectedType == 'MUSIC' ? OpenFlAssets.getMusic(id, useCache) : OpenFlAssets.getSound(id, useCache);
		var key = ownerCacheKey(owner, id, expectedType, resolved.path);
		if (useCache && ownerCache != null && ownerCache.enabled && ownerCache.hasSound(key)) {
			var cached = ownerCache.getSound(key);
			if (cached != null) return cached;
		}
		var sound = FNFAssets.getSound(resolved.path, useCache);
		if (sound != null && useCache && ownerCache != null && ownerCache.enabled)
			ownerCache.setSound(key, sound);
		return sound;
	}

	static function getMusic(owner:String, id:String, useCache:Bool, proxy:Dynamic):Sound {
		var indexed = ownerLibraryAsset(owner, id, 'MUSIC');
		if (indexed == null) return getSound(owner, id, useCache, 'MUSIC', proxy);
		#if (lime_vorbis && lime > "7.9.0")
		var sound = PsychOwnerMusicStreamLease.getSound(indexed.identity, indexed.entry);
		if (sound != null) return sound;
		#end
		return getSound(owner, id, useCache, 'MUSIC', proxy);
	}

	static function list(owner:String, engine:String, scope:String, type:AssetType,
		library:Null<String>):Array<String> {
		var output = OpenFlAssets.list(type);
		var importedPrefix = CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/';
		output = output.filter(function(id:String)
			return id == null || !id.toLowerCase().startsWith(importedPrefix));
		return output.concat(RuntimeOwnerAssetIdentity.ownerList(owner, engine, scope,
			library, assetTypeName(type)));
	}

	static function ownerLibrary(owner:String, engine:String, scope:String, name:String,
		assetsProxy:Dynamic):Dynamic {
		var library = SourceLimeAssetIdentity.canonicalLibrary(name);
		var proxy:Dynamic = {name:library};
		var qualified = function(id:String):String return library + ':' + id;
		var call = function(method:String, args:Array<Dynamic>):Dynamic {
			return Reflect.callMethod(assetsProxy, Reflect.field(assetsProxy, method), args);
		};
		Reflect.setField(proxy, 'exists', function(id:String, ?type:AssetType):Bool
			return call('exists', [qualified(id), type]));
		Reflect.setField(proxy, 'getText', function(id:String):String return call('getText', [qualified(id)]));
		Reflect.setField(proxy, 'getBytes', function(id:String):ByteArray return call('getBytes', [qualified(id)]));
		Reflect.setField(proxy, 'getBitmapData', function(id:String, ?useCache:Bool = true):BitmapData
			return call('getBitmapData', [qualified(id), useCache]));
		Reflect.setField(proxy, 'getSound', function(id:String, ?useCache:Bool = true):Sound
			return call('getSound', [qualified(id), useCache]));
		Reflect.setField(proxy, 'getMusic', function(id:String, ?useCache:Bool = true):Sound
			return call('getMusic', [qualified(id), useCache]));
		Reflect.setField(proxy, 'getFont', function(id:String, ?useCache:Bool = true):Font
			return call('getFont', [qualified(id), useCache]));
		Reflect.setField(proxy, 'getPath', function(id:String):String return call('getPath', [qualified(id)]));
		Reflect.setField(proxy, 'isLocal', function(id:String, ?type:AssetType, ?useCache:Bool = true):Bool
			return call('isLocal', [qualified(id), type, useCache]));
		Reflect.setField(proxy, 'list', function(?type:AssetType):Array<String>
			return RuntimeOwnerAssetIdentity.ownerList(owner, engine, scope, library, assetTypeName(type)));
		Reflect.setField(proxy, 'getAsset', function(id:String, type:AssetType, ?useCache:Bool = true):Dynamic
			return call('getAsset', [qualified(id), type, useCache]));
		Reflect.setField(proxy, 'loadBitmapData', function(id:String, ?useCache:Null<Bool> = true):Dynamic
			return call('loadBitmapData', [qualified(id), useCache]));
		Reflect.setField(proxy, 'loadBytes', function(id:String):Dynamic return call('loadBytes', [qualified(id)]));
		Reflect.setField(proxy, 'loadFont', function(id:String, ?useCache:Null<Bool> = true):Dynamic
			return call('loadFont', [qualified(id), useCache]));
		Reflect.setField(proxy, 'loadMusic', function(id:String, ?useCache:Null<Bool> = true):Dynamic
			return call('loadMusic', [qualified(id), useCache]));
		Reflect.setField(proxy, 'loadSound', function(id:String, ?useCache:Null<Bool> = true):Dynamic
			return call('loadSound', [qualified(id), useCache]));
		Reflect.setField(proxy, 'loadText', function(id:String):Dynamic return call('loadText', [qualified(id)]));
		return proxy;
	}

	static function load(owner:String, id:String, type:AssetType, useCache:Bool, proxy:Dynamic):Dynamic {
		var ownerCache:PsychOwnerOpenFlAssetCache = cast Reflect.field(proxy, 'cache');
		var indexedCacheId = ownerIndexCacheId(owner, id, assetTypeName(type));
		if (indexedCacheId != null && useCache && ownerCache != null && ownerCache.enabled) switch (type) {
			case IMAGE:
				var cached = ownerCache.getBitmapData(indexedCacheId);
				if (OpenFlAssets.isValidBitmapData(cached)) return Future.withValue(cached);
			case FONT:
				var cached = ownerCache.getFont(indexedCacheId);
				if (cached != null) return Future.withValue(cached);
			default:
		}
		var resolved = resolve(owner, id, assetTypeName(type));
		var indexed:PsychOwnerAssetLibraryAssetView;
		try indexed = ownerLibraryAsset(owner, id, assetTypeName(type)) catch (error:Dynamic)
			return Future.withError(error);
		if (indexed != null) {
			var cache = PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
			if (useCache && cache.enabled) switch (type) {
				case IMAGE:
					var bitmap = cache.getBitmapData(id);
					if (OpenFlAssets.isValidBitmapData(bitmap)) return Future.withValue(bitmap);
				case FONT:
					var font = cache.getFont(id);
					if (font != null) return Future.withValue(font);
				default:
			}
			return switch (type) {
			case IMAGE: loadBitmapDataFromImage(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
				indexed, toLimeAssetType(AssetType.IMAGE), false), indexed.identity, id, useCache);
			case BINARY: indexed.library.loadBytes(indexed.id).then(function(bytes)
				return Future.withValue(ByteArray.fromBytes(bytes)));
			case FONT: loadFontFromLime(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
				indexed, toLimeAssetType(AssetType.FONT), true), indexed.identity, id, useCache);
			case SOUND: loadSoundFromAudio(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
				indexed, toLimeAssetType(AssetType.SOUND), useCache), indexed.identity, id, useCache);
			case MUSIC:
				#if html5
				new Future<Sound>(function() return getMusic(owner, id, useCache, proxy));
				#else
				loadSoundFromAudio(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
					indexed, toLimeAssetType(AssetType.SOUND), useCache), indexed.identity, id, useCache);
				#end
			case TEXT: indexed.library.loadText(indexed.id);
			default: Future.withError('[psych-assets] Unsupported selected-owner OpenFL asset type: ' + Std.string(type));
			};
		}
		if (resolved.blocked) return Future.withError('[psych-assets] Refused asset outside selected owner: ' + id);
		if (resolved.unavailable) return Future.withError('[psych-assets] Asset is unavailable in selected owner: ' + id);
		if (!resolved.owned && OpenFlAssets.exists(id, type)) {
			return switch (type) {
				case IMAGE: OpenFlAssets.loadBitmapData(id, useCache);
				case BINARY: OpenFlAssets.loadBytes(id);
				case FONT: OpenFlAssets.loadFont(id, useCache);
				case SOUND: OpenFlAssets.loadSound(id, useCache);
				case MUSIC: OpenFlAssets.loadMusic(id, useCache);
				case TEXT: OpenFlAssets.loadText(id);
				default: null;
			};
		}
		if (!resolved.owned && (resolved.path == null || !FNFAssets.exists(resolved.path)))
			return switch (type) {
				case IMAGE: OpenFlAssets.loadBitmapData(id, useCache);
				case BINARY: OpenFlAssets.loadBytes(id);
				case FONT: OpenFlAssets.loadFont(id, useCache);
				case SOUND: OpenFlAssets.loadSound(id, useCache);
				case MUSIC: OpenFlAssets.loadMusic(id, useCache);
				case TEXT: OpenFlAssets.loadText(id);
				default: null;
			};
		try {
			var value:Dynamic = switch (type) {
				case IMAGE: Reflect.callMethod(proxy, Reflect.field(proxy, 'getBitmapData'), [id, useCache]);
				case BINARY: ByteArray.fromBytes(FNFAssets.getBytes(resolved.path));
				case FONT: Reflect.callMethod(proxy, Reflect.field(proxy, 'getFont'), [id, useCache]);
				case SOUND | MUSIC: Reflect.callMethod(proxy, Reflect.field(proxy, 'getSound'), [id, useCache]);
				case TEXT: FNFAssets.getText(resolved.path);
				default: null;
			};
			return Future.withValue(value);
		} catch (error:Dynamic) {
			return Future.withError(error);
		}
	}

	static function ownerLibraryAsset(owner:String, id:String,
		expectedType:Null<String>):Null<PsychOwnerAssetLibraryAssetView> {
		var identity = RuntimeOwnerAssetIdentity.acquire(owner, 'Psych Engine', 'package');
		return PsychOwnerAssetLibraryCache.findLimeAsset(identity, id, expectedType);
	}

	static function releaseOwnerLibrary(owner:String, engine:String, scope:String,
		name:String, operation:String, unload:Bool):Bool {
		if (unsafeLibraryName(name)) return false;
		var identity = RuntimeOwnerAssetIdentity.acquire(owner, engine, scope);
		var library = SourceLimeAssetIdentity.canonicalLibrary(name);
		var state = identity.libraryState(library);
		if (state == 'declared') {
			if (identity.indexVersion < 2)
				throw '[psych-assets] Dynamic ' + operation + ' is unsupported for selected-owner asset libraries: ' + name;
			PsychOwnerAssetLibraryCache.unload(identity, library, unload);
			return true;
		}
		if (state == 'unknown')
			throw '[psych-assets] Asset library identity is incomplete for selected owner: ' + name;
		return false;
	}

	static function loadBitmapDataFromImage(imageFuture:Future<Image>, identity:RuntimeOwnerAssetIdentity,
		id:String,
		useCache:Bool):Future<BitmapData> {
		var promise = new Promise<BitmapData>();
		imageFuture.onProgress(promise.progress);
		imageFuture.onError(promise.error);
		imageFuture.onComplete(function(image:Image) {
			if (image == null) {
				promise.error('[Assets] Could not load Image "' + id + '"');
				return;
			}
			var bitmap = BitmapData.fromImage(image);
			if (bitmap != null) bitmap.__asset = true;
			if (bitmap != null && useCache) PsychOwnerAssetLibraryCache.storeOpenFlBitmapData(identity, id, bitmap);
			promise.complete(bitmap);
		});
		return promise.future;
	}

	static function loadFontFromLime(fontFuture:Future<LimeFont>, identity:RuntimeOwnerAssetIdentity,
		id:String,
		useCache:Bool):Future<Font> {
		var promise = new Promise<Font>();
		fontFuture.onProgress(promise.progress);
		fontFuture.onError(promise.error);
		fontFuture.onComplete(function(limeFont:LimeFont) {
			var font = new Font();
			font.__fromLimeFont(limeFont);
			if (useCache) PsychOwnerAssetLibraryCache.storeOpenFlFont(identity, id, font);
			promise.complete(font);
		});
		return promise.future;
	}

	static function loadSoundFromAudio(audioFuture:Future<AudioBuffer>, identity:RuntimeOwnerAssetIdentity,
		id:String,
		useCache:Bool):Future<Sound> {
		var promise = new Promise<Sound>();
		audioFuture.onProgress(promise.progress);
		audioFuture.onError(promise.error);
		audioFuture.onComplete(function(audio:AudioBuffer) {
			if (audio == null) {
				promise.error('[Assets] Could not load Sound "' + id + '"');
				return;
			}
			var sound = Sound.fromAudioBuffer(audio);
			if (useCache) PsychOwnerAssetLibraryCache.storeOpenFlSound(identity, id, sound);
			promise.complete(sound);
		});
		return promise.future;
	}

	static function required(owner:String, id:String, ?expectedType:String):PsychOwnerAssetPathResult {
		var resolved = resolve(owner, id, expectedType);
		if (resolved.blocked)
			throw '[psych-assets] Refused asset outside selected owner: ' + Std.string(id);
		if (resolved.unavailable)
			throw '[psych-assets] Asset is unavailable in selected owner: ' + Std.string(id);
		if (resolved.path == null)
			throw '[psych-assets] Asset is unavailable to selected owner: ' + Std.string(id);
		return resolved;
	}

	static function resolve(owner:String, id:String, ?expectedType:String):PsychOwnerAssetPathResult {
		var indexed = RuntimeOwnerAssetIdentity.lookup(owner, 'Psych Engine', 'package', id, expectedType);
		if (indexed.state == 'found')
			return {path:indexed.path, owned:true, blocked:false, unavailable:false};
		if (indexed.state != 'no-index' && indexed.state != 'unclaimed') {
			// Keep the established selected-owner physical-path API available for
			// files which have no Lime identity record. Symbolic IDs still fail
			// closed when their declared owner library has no matching entry.
			var physical = PsychOwnerAssetPath.resolve(owner, id);
			if (indexed.state != 'type-mismatch' && physical.owned) return physical;
			return {path:null, owned:false, blocked:false, unavailable:true};
		}
		var ownerPath = PsychOwnerAssetPath.resolve(owner, id);
		if (ownerPath.blocked || ownerPath.unavailable || ownerPath.owned)
			return ownerPath;
		var clean = PsychOwnerAssetPath.cleanId(id);
		if (clean == null) return ownerPath;
		if (expectedType == null ? OpenFlAssets.exists(id) : OpenFlAssets.exists(id, cast expectedType))
			return {path:id, owned:false, blocked:false, unavailable:false};
		if (FNFAssets.exists(clean)) return {path:clean, owned:false, blocked:false, unavailable:false};
		if (!clean.toLowerCase().startsWith('assets/')) {
			var nativePath = 'assets/' + clean;
			if (FNFAssets.exists(nativePath)) return {path:nativePath, owned:false, blocked:false, unavailable:false};
		}
		return {path:id, owned:false, blocked:false, unavailable:false};
	}

	static function unsafeLibraryName(name:String):Bool {
		if (name == null || StringTools.trim(name) == '') return false;
		var clean = PsychOwnerAssetPath.cleanId(name);
		return clean == null || clean.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/');
	}

	/** Owner libraries are virtual index views, not OpenFL AssetLibrary
		instances. Never mutate a same-named host library through this facade. */
	static function guardGlobalLibraryMutation(owner:String, engine:String, scope:String,
		name:String, operation:String):Void {
		if (unsafeLibraryName(name))
			throw '[psych-assets] OpenFL library mutation cannot escape the selected owner';
		var state = RuntimeOwnerAssetIdentity.ownerLibraryState(owner, engine, scope,
			SourceLimeAssetIdentity.canonicalLibrary(name));
		if (state != 'unclaimed')
			throw '[psych-assets] Dynamic ' + operation + ' is unsupported for selected-owner asset libraries: ' + name;
	}

	static function unsafeMovieClipId(id:String):Bool {
		if (id == null || StringTools.trim(id) == '') return true;
		var colon = id.indexOf(':');
		if (colon <= 0) {
			var clean = PsychOwnerAssetPath.cleanId(id);
			return clean == null || clean.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/');
		}
		var library = id.substr(0, colon);
		var symbol = id.substr(colon + 1);
		return unsafeLibraryName(library) || PsychOwnerAssetPath.cleanId(library + '/' + symbol) == null;
	}

	static function cacheKey(owner:String, path:String):String return 'psych-owner:' + owner + ':' + path;

	static function ownerCacheKey(owner:String, id:String, type:String, path:String):String {
		var indexed = RuntimeOwnerAssetIdentity.lookup(owner, 'Psych Engine', 'package', id, type);
		return indexed.state == 'found' ? id : cacheKey(owner, path);
	}

	static function ownerIndexCacheId(owner:String, id:String, type:String):Null<String> {
		var identity = RuntimeOwnerAssetIdentity.acquire(owner, 'Psych Engine', 'package');
		if (identity.bindingState == 'ready') PsychOwnerAssetLibraryCache.openFlAssetCache(identity);
		var indexed = identity.resolve(id, type);
		return indexed.state == 'found' ? id : null;
	}

	static function assetTypeName(type:AssetType):Null<String>
		return type == null ? null : Std.string(type).toUpperCase();

	static function toLimeAssetType(type:AssetType):lime.utils.AssetType
		return cast (Std.string(type).toUpperCase():String);
}
