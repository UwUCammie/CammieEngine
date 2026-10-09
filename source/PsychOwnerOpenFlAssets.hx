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
import SourceOwnerAssetContext;

using StringTools;

@:access(openfl.text.Font)
@:access(openfl.display.BitmapData)
@:access(openfl.utils.Assets)
/** OpenFL Assets facade that keeps Psych file reads inside the selected import. */
class PsychOwnerOpenFlAssets {
	public static function create(ownerRoot:String):Dynamic
		return createForContext(SourceOwnerAssetContext.psych(ownerRoot));

	/** Create the OpenFL facade over the same exact source-owner context as Lime. */
	public static function createForContext(context:SourceOwnerAssetContext):Dynamic {
		if (context == null) throw '[psych-assets] A selected-owner source context is required';
		var owner = context.ownerRoot;
		var engine = context.engine;
		var scope = context.cacheScope;
		var resolveSelected = function(id:String, ?expectedType:String):PsychOwnerAssetPathResult
			return resolveForContext(context, id, expectedType);
		var requiredSelected = function(id:String, ?expectedType:String):PsychOwnerAssetPathResult
			return requiredForContext(context, id, expectedType);
		var ownerLibraryAssetSelected = function(id:String,
			expectedType:Null<String>):Null<PsychOwnerAssetLibraryAssetView>
			return ownerLibraryAssetForContext(context, id, expectedType);
		var ownerIndexCacheIdSelected = function(id:String, type:String):Null<String>
			return ownerIndexCacheIdForContext(context, id, type);
		var ownerCacheKeySelected = function(id:String, type:String, path:String):String
			return ownerCacheKeyForContext(context, id, type, path);
		var guardGlobalLibraryMutationSelected = function(name:String, operation:String):Void
			guardGlobalLibraryMutation(context, name, operation);
		var releaseOwnerLibrarySelected = function(name:String, operation:String, unload:Bool):Bool
			return releaseOwnerLibrary(context, name, operation, unload);
		var proxy:Dynamic = {};
		Reflect.setField(proxy, 'cache', context.composite
			? SourceOwnerAssetContextCache.openFl(context)
			: PsychOwnerAssetLibraryCache.openFlAssetCacheForOwner(owner, engine, scope, OpenFlAssets.cache));
		var ownerCache:PsychOwnerOpenFlAssetCache = cast Reflect.field(proxy, 'cache');
		var assetEvents = SourceOwnerAssetsEvents.forContext(context);
		Reflect.setField(proxy, 'exists', function(id:String, ?type:AssetType):Bool {
			var resolved = resolveSelected(id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return (context.allowNativeFallback && OpenFlAssets.exists(id, type))
				|| (resolved.path != null && FNFAssets.exists(resolved.path));
		});
		Reflect.setField(proxy, 'getText', function(id:String):String {
			var resolved = requiredSelected(id, 'TEXT');
			var indexed = ownerLibraryAssetSelected(id, 'TEXT');
			if (indexed != null) return indexed.library.getText(indexed.id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& (!context.allowNativeFallback || !OpenFlAssets.exists(id, AssetType.TEXT))))
				return FNFAssets.getText(resolved.path);
			if (!context.allowNativeFallback) throw '[psych-assets] Asset is unavailable to selected owner: ' + id;
			return OpenFlAssets.getText(id);
		});
		Reflect.setField(proxy, 'getBytes', function(id:String):ByteArray {
			var resolved = requiredSelected(id, 'BINARY');
			var indexed = ownerLibraryAssetSelected(id, 'BINARY');
			if (indexed != null) return ByteArray.fromBytes(indexed.library.getBytes(indexed.id));
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& (!context.allowNativeFallback || !OpenFlAssets.exists(id, AssetType.BINARY))))
				return ByteArray.fromBytes(FNFAssets.getBytes(resolved.path));
			if (!context.allowNativeFallback) throw '[psych-assets] Asset is unavailable to selected owner: ' + id;
			return OpenFlAssets.getBytes(id);
		});
		Reflect.setField(proxy, 'getBitmapData', function(id:String, ?useCache:Bool = true):BitmapData {
			var indexedCacheId = ownerIndexCacheIdSelected(id, 'IMAGE');
			var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
			var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, 'IMAGE');
			if (sourceCacheId != null && useCache && ownerCache != null && ownerCache.enabled
				&& ownerCache.hasBitmapData(sourceCacheId)) {
				var cached = ownerCache.getBitmapData(sourceCacheId);
				if (OpenFlAssets.isValidBitmapData(cached) && (cacheGuard == null || cacheGuard())) return cached;
			}
			var resolved = requiredSelected(id, 'IMAGE');
			var indexed = ownerLibraryAssetSelected(id, 'IMAGE');
			if (indexed != null) {
				var current = context.composite ? context.selectionGuard(id, 'IMAGE', indexed.identity) : null;
				var cache = context.composite ? ownerCache : PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
				if (useCache && cache.enabled && cache.hasBitmapData(id) && (current == null || current())) {
					var cached = cache.getBitmapData(id);
					if (OpenFlAssets.isValidBitmapData(cached)) return cached;
				}
				var image:Image = cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
					toLimeAssetType(AssetType.IMAGE), false,
					context.composite ? SourceOwnerAssetContextCache.lime(context) : null, current);
				var bitmap = image == null ? null : BitmapData.fromImage(image);
				if (bitmap != null) bitmap.__asset = true;
				if (bitmap != null && useCache && cache.enabled)
					PsychOwnerAssetLibraryCache.storeOpenFlBitmapData(indexed.identity, id, bitmap,
						context.composite ? ownerCache : null, current);
				return bitmap;
			}
			if (context.allowNativeFallback && !resolved.owned && OpenFlAssets.exists(id, AssetType.IMAGE))
				return OpenFlAssets.getBitmapData(id, useCache);
			var key = ownerCacheKeySelected(id, 'IMAGE', resolved.path);
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
			return getSound(context, id, useCache, 'SOUND', proxy);
		});
		Reflect.setField(proxy, 'getMusic', function(id:String, ?useCache:Bool = true):Sound {
			return getMusic(context, id, useCache, proxy);
		});
		Reflect.setField(proxy, 'getFont', function(id:String, ?useCache:Bool = true):Font {
			var indexedCacheId = ownerIndexCacheIdSelected(id, 'FONT');
			var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
			var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, 'FONT');
			if (sourceCacheId != null && useCache && ownerCache != null && ownerCache.enabled
				&& ownerCache.hasFont(sourceCacheId)) {
				var cached = ownerCache.getFont(sourceCacheId);
				if (cached != null && (cacheGuard == null || cacheGuard())) return cached;
			}
			var resolved = requiredSelected(id, 'FONT');
			var indexed = ownerLibraryAssetSelected(id, 'FONT');
			if (indexed != null) {
				var current = context.composite ? context.selectionGuard(id, 'FONT', indexed.identity) : null;
				var cache = context.composite ? ownerCache : PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
				if (useCache && cache.enabled && cache.hasFont(id) && (current == null || current())) {
					var cached = cache.getFont(id);
					if (cached != null) return cached;
				}
				var limeFont:LimeFont = cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
					toLimeAssetType(AssetType.FONT), false,
					context.composite ? SourceOwnerAssetContextCache.lime(context) : null, current);
				if (limeFont == null) return new Font();
				var font = new Font();
				font.__fromLimeFont(limeFont);
				if (useCache && cache.enabled) PsychOwnerAssetLibraryCache.storeOpenFlFont(indexed.identity, id, font,
					context.composite ? ownerCache : null, current);
				return font;
			}
			if (context.allowNativeFallback && !resolved.owned && OpenFlAssets.exists(id, AssetType.FONT))
				return OpenFlAssets.getFont(id, useCache);
			var key = ownerCacheKeySelected(id, 'FONT', resolved.path);
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
			var resolved = resolveSelected(id, null);
			if (resolved.blocked || resolved.unavailable) return null;
			if (resolved.path != null && (resolved.owned || FNFAssets.exists(resolved.path))) return resolved.path;
			return context.allowNativeFallback ? OpenFlAssets.getPath(id) : null;
		});
		Reflect.setField(proxy, 'isLocal', function(id:String, ?type:AssetType, ?useCache:Bool = true):Bool {
			var resolved = resolveSelected(id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return context.allowNativeFallback && OpenFlAssets.isLocal(id, type, useCache);
		});
		Reflect.setField(proxy, 'list', function(?type:AssetType):Array<String> {
			return list(context, type, null);
		});
		Reflect.setField(proxy, 'getLibrary', function(name:String):Dynamic {
			if (unsafeLibraryName(name)) throw '[psych-assets] OpenFL asset libraries cannot escape the selected owner';
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(name);
			var identities = context.identitiesForLibrary(libraryName);
			if (identities.length > 0) {
				if (context.composite)
					return SourceOwnerAssetContextCache.openFlLibrary(context, libraryName, proxy);
				if (identities.length == 1 && identities[0].indexVersion >= 2)
					return PsychOwnerAssetLibraryCache.getOpenFl(identities[0], libraryName);
				return ownerLibrary(context, name, proxy);
			}
			var state = context.libraryState(libraryName);
			if (state == 'unknown') throw '[psych-assets] Asset library identity is incomplete for selected owner: ' + name;
			return context.allowNativeFallback ? OpenFlAssets.getLibrary(name) : null;
		});
		Reflect.setField(proxy, 'getMovieClip', function(id:String):Dynamic {
			if (unsafeMovieClipId(id)) throw '[psych-assets] OpenFL movie clips cannot escape the selected owner';
			var resolved = resolveSelected(id, 'MOVIE_CLIP');
			if (resolved.blocked || resolved.unavailable)
				throw '[psych-assets] Movie clip identity is unavailable in selected owner: ' + id;
			if (resolved.owned)
				throw '[psych-assets] Owner MovieClip bindings are unsupported by the file-backed asset facade: ' + id;
			if (!context.allowNativeFallback) throw '[psych-assets] Movie clips are unavailable to selected owner: ' + id;
			return OpenFlAssets.getMovieClip(id);
		});
		Reflect.setField(proxy, 'hasLibrary', function(name:String):Bool {
			if (unsafeLibraryName(name)) return false;
			var state = context.libraryState(SourceLimeAssetIdentity.canonicalLibrary(name));
			if (state == 'declared') return true;
			if (state == 'unknown') return false;
			return context.allowNativeFallback && OpenFlAssets.hasLibrary(name);
		});
		Reflect.setField(proxy, 'initBinding', function(className:String, ?instance:Dynamic):Void
			throw '[psych-assets] Dynamic OpenFL bindings are unsupported by the owner-scoped facade');
		Reflect.setField(proxy, 'addEventListener', function(type:String, listener:Dynamic,
			?useCapture:Bool = false, ?priority:Int = 0, ?useWeakReference:Bool = false):Void
			assetEvents.addEventListener(type, listener, useCapture, priority, useWeakReference));
		Reflect.setField(proxy, 'dispatchEvent', function(event:Event):Bool return assetEvents.dispatchEvent(event));
		Reflect.setField(proxy, 'hasEventListener', function(type:String):Bool return assetEvents.hasEventListener(type));
		Reflect.setField(proxy, 'willTrigger', function(type:String):Bool return assetEvents.willTrigger(type));
		Reflect.setField(proxy, 'removeEventListener', function(type:String, listener:Dynamic, ?capture:Bool = false):Void
			assetEvents.removeEventListener(type, listener, capture));
		Reflect.setField(proxy, 'loadBitmapData', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(context, id, AssetType.IMAGE, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadBytes', function(id:String):Dynamic return load(context, id, AssetType.BINARY, false, proxy));
		Reflect.setField(proxy, 'loadFont', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(context, id, AssetType.FONT, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadMusic', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(context, id, AssetType.MUSIC, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadSound', function(id:String, ?useCache:Null<Bool> = true):Dynamic {
			return load(context, id, AssetType.SOUND, useCache == null ? true : useCache, proxy);
		});
		Reflect.setField(proxy, 'loadText', function(id:String):Dynamic return load(context, id, AssetType.TEXT, false, proxy));
		Reflect.setField(proxy, 'loadMovieClip', function(id:String):Dynamic {
			if (unsafeMovieClipId(id)) return Future.withError('[psych-assets] OpenFL movie clips cannot escape the selected owner');
			var resolved = resolveSelected(id, 'MOVIE_CLIP');
			if (resolved.blocked || resolved.unavailable)
				return Future.withError('[psych-assets] Movie clip identity is unavailable in selected owner: ' + id);
			if (resolved.owned)
				return Future.withError('[psych-assets] Owner MovieClip bindings are unsupported by the file-backed asset facade: ' + id);
			if (!context.allowNativeFallback) return Future.withError('[psych-assets] Movie clips are unavailable to selected owner: ' + id);
			return OpenFlAssets.loadMovieClip(id);
		});
		Reflect.setField(proxy, 'loadLibrary', function(name:String):Dynamic {
			if (unsafeLibraryName(name)) return Future.withError('[psych-assets] OpenFL asset libraries cannot escape the selected owner');
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(name);
			var identities:Array<RuntimeOwnerAssetIdentity>;
			try identities = context.identitiesForLibrary(libraryName) catch (error:Dynamic)
				return Future.withError(error);
			if (identities.length > 0) {
				if (context.composite) {
					var view = SourceOwnerAssetContextCache.limeLibrary(context, libraryName, proxy);
					var wrapper = SourceOwnerAssetContextCache.openFlLibrary(context, libraryName, proxy);
					return view.load().then(function(_)
						return Future.withValue(wrapper));
				}
				if (identities.length == 1) {
					if (identities[0].indexVersion < 2)
						return Future.withError('[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: ' + name);
					return PsychOwnerAssetLibraryCache.loadOpenFl(identities[0], libraryName);
				}
				return loadCompositeLibrary(context, identities, libraryName, proxy);
			}
			var state = context.libraryState(libraryName);
			if (state == 'unknown') return Future.withError('[psych-assets] Asset library identity is incomplete for selected owner: ' + name);
			return context.allowNativeFallback ? OpenFlAssets.loadLibrary(name)
				: Future.withError('[psych-assets] OpenFL library is not declared by selected owner: ' + name);
		});
		Reflect.setField(proxy, 'registerBinding', function(className:String, library:Dynamic):Void
			throw '[psych-assets] Dynamic OpenFL bindings are unsupported by the owner-scoped facade');
		Reflect.setField(proxy, 'unregisterBinding', function(className:String, library:Dynamic):Void
			throw '[psych-assets] Dynamic OpenFL bindings are unsupported by the owner-scoped facade');
		Reflect.setField(proxy, 'registerLibrary', function(name:String, library:Dynamic):Void {
			guardGlobalLibraryMutationSelected(name, 'register');
			OpenFlAssets.registerLibrary(name, library);
		});
		Reflect.setField(proxy, 'unloadLibrary', function(name:String):Void {
			if (releaseOwnerLibrarySelected(name, 'unload', true)) return;
			guardGlobalLibraryMutationSelected(name, 'unload');
			OpenFlAssets.unloadLibrary(name);
		});
		return proxy;
	}

	static function getSound(context:SourceOwnerAssetContext, id:String, useCache:Bool,
		expectedType:String, proxy:Dynamic):Sound {
		var ownerCache:PsychOwnerOpenFlAssetCache = cast Reflect.field(proxy, 'cache');
		var indexedCacheId = ownerIndexCacheIdForContext(context, id, expectedType);
		var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
		var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, expectedType);
		if (sourceCacheId != null && useCache && ownerCache != null && ownerCache.enabled
			&& ownerCache.hasSound(sourceCacheId)) {
			var cached = ownerCache.getSound(sourceCacheId);
			if (OpenFlAssets.isValidSound(cached) && (cacheGuard == null || cacheGuard())) return cached;
		}
		var resolved = requiredForContext(context, id, expectedType);
		var indexed = ownerLibraryAssetForContext(context, id, expectedType);
		if (indexed != null) {
			var current = context.composite ? context.selectionGuard(id, expectedType, indexed.identity) : null;
			var cache = context.composite ? ownerCache : PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
			if (useCache && cache.enabled && cache.hasSound(id) && (current == null || current())) {
				var cached = cache.getSound(id);
				if (OpenFlAssets.isValidSound(cached)) return cached;
			}
			var audio:AudioBuffer = cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
				toLimeAssetType(AssetType.SOUND), false,
				context.composite ? SourceOwnerAssetContextCache.lime(context) : null, current);
			var sound = audio == null ? null : Sound.fromAudioBuffer(audio);
			if (sound != null && useCache && cache.enabled)
				PsychOwnerAssetLibraryCache.storeOpenFlSound(indexed.identity, id, sound,
					context.composite ? ownerCache : null, current);
			return sound;
		}
		if (context.allowNativeFallback && !resolved.owned && OpenFlAssets.exists(id, AssetType.SOUND))
			return expectedType == 'MUSIC' ? OpenFlAssets.getMusic(id, useCache) : OpenFlAssets.getSound(id, useCache);
		var key = ownerCacheKeyForContext(context, id, expectedType, resolved.path);
		if (useCache && ownerCache != null && ownerCache.enabled && ownerCache.hasSound(key)) {
			var cached = ownerCache.getSound(key);
			if (cached != null) return cached;
		}
		var sound = FNFAssets.getSound(resolved.path, useCache);
		if (sound != null && useCache && ownerCache != null && ownerCache.enabled)
			ownerCache.setSound(key, sound);
		return sound;
	}

	static function getMusic(context:SourceOwnerAssetContext, id:String, useCache:Bool,
		proxy:Dynamic):Sound {
		var indexed = ownerLibraryAssetForContext(context, id, 'MUSIC');
		if (indexed == null) return getSound(context, id, useCache, 'MUSIC', proxy);
		var current = context.composite ? context.selectionGuard(id, 'MUSIC', indexed.identity) : null;
		if (current != null && !current()) throw '[psych-assets] Selected owner identity changed while music was being resolved';
		#if (lime_vorbis && lime > "7.9.0")
		var sound = PsychOwnerMusicStreamLease.getSound(indexed.identity, indexed.entry);
		if (current != null && !current()) throw '[psych-assets] Selected owner identity changed while music was being resolved';
		if (sound != null) return sound;
		#end
		return getSound(context, id, useCache, 'MUSIC', proxy);
	}

	static function list(context:SourceOwnerAssetContext, type:AssetType,
		library:Null<String>):Array<String> {
		var output = context.allowNativeFallback ? OpenFlAssets.list(type) : [];
		var importedPrefix = CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/';
		output = output.filter(function(id:String)
			return id == null || !id.toLowerCase().startsWith(importedPrefix));
		return output.concat(context.listAssets(library, assetTypeName(type)));
	}

	static function ownerLibrary(context:SourceOwnerAssetContext, name:String,
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
			return context.listAssets(library, assetTypeName(type)));
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

	static function load(context:SourceOwnerAssetContext, id:String, type:AssetType,
		useCache:Bool, proxy:Dynamic):Dynamic {
		var ownerCache:PsychOwnerOpenFlAssetCache = cast Reflect.field(proxy, 'cache');
		var indexedCacheId = ownerIndexCacheIdForContext(context, id, assetTypeName(type));
		var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
		var cacheGuard = indexedCacheId == null ? null
			: selectionGuardForContext(context, id, assetTypeName(type));
		if (sourceCacheId != null && useCache && ownerCache != null && ownerCache.enabled) switch (type) {
			case IMAGE:
				var cached = ownerCache.getBitmapData(sourceCacheId);
				if (OpenFlAssets.isValidBitmapData(cached) && (cacheGuard == null || cacheGuard())) return Future.withValue(cached);
			case FONT:
				var cached = ownerCache.getFont(sourceCacheId);
				if (cached != null && (cacheGuard == null || cacheGuard())) return Future.withValue(cached);
			default:
		}
		var resolved = resolveForContext(context, id, assetTypeName(type));
		var indexed:PsychOwnerAssetLibraryAssetView;
		try indexed = ownerLibraryAssetForContext(context, id, assetTypeName(type)) catch (error:Dynamic)
			return Future.withError(error);
		if (indexed != null) {
			var current = context.composite ? context.selectionGuard(id, assetTypeName(type), indexed.identity) : null;
			var cache = context.composite ? ownerCache : PsychOwnerAssetLibraryCache.openFlAssetCache(indexed.identity);
			if (useCache && cache.enabled) switch (type) {
				case IMAGE:
					var bitmap = cache.getBitmapData(id);
					if (OpenFlAssets.isValidBitmapData(bitmap) && (current == null || current())) return Future.withValue(bitmap);
				case FONT:
					var font = cache.getFont(id);
					if (font != null && (current == null || current())) return Future.withValue(font);
				default:
			}
			return switch (type) {
			case IMAGE: loadBitmapDataFromImage(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
				indexed, toLimeAssetType(AssetType.IMAGE), false), indexed.identity, id, useCache,
				context.composite ? ownerCache : null, current);
			case BINARY: PsychOwnerAssetLibraryCache.guardFuture(indexed.library.loadBytes(indexed.id), current)
				.then(function(bytes) return Future.withValue(ByteArray.fromBytes(bytes)));
			case FONT: loadFontFromLime(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
				indexed, toLimeAssetType(AssetType.FONT), true,
				context.composite ? SourceOwnerAssetContextCache.lime(context) : null, current),
				indexed.identity, id, useCache, context.composite ? ownerCache : null, current);
			case SOUND: loadSoundFromAudio(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
				indexed, toLimeAssetType(AssetType.SOUND), useCache,
				context.composite ? SourceOwnerAssetContextCache.lime(context) : null, current),
				indexed.identity, id, useCache, context.composite ? ownerCache : null, current);
			case MUSIC:
				#if html5
				new Future<Sound>(function() return getMusic(context, id, useCache, proxy));
				#else
				loadSoundFromAudio(cast PsychOwnerAssetLibraryCache.loadLimeAsset(
					indexed, toLimeAssetType(AssetType.SOUND), useCache,
					context.composite ? SourceOwnerAssetContextCache.lime(context) : null, current),
					indexed.identity, id, useCache, context.composite ? ownerCache : null, current);
				#end
			case TEXT: PsychOwnerAssetLibraryCache.guardFuture(indexed.library.loadText(indexed.id), current);
			default: Future.withError('[psych-assets] Unsupported selected-owner OpenFL asset type: ' + Std.string(type));
			};
		}
		if (resolved.blocked) return Future.withError('[psych-assets] Refused asset outside selected owner: ' + id);
		if (resolved.unavailable) return Future.withError('[psych-assets] Asset is unavailable in selected owner: ' + id);
		if (context.allowNativeFallback && !resolved.owned && OpenFlAssets.exists(id, type)) {
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
		if (resolved.path == null || (!resolved.owned && !FNFAssets.exists(resolved.path))) {
			if (!context.allowNativeFallback)
				return Future.withError('[psych-assets] Asset is unavailable to selected owner: ' + id);
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

	static function loadBitmapDataFromImage(imageFuture:Future<Image>, identity:RuntimeOwnerAssetIdentity,
		id:String,
		useCache:Bool, ?cacheOverride:PsychOwnerOpenFlAssetCache,
		?isCurrent:Void->Bool):Future<BitmapData> {
		var promise = new Promise<BitmapData>();
		imageFuture.onProgress(promise.progress);
		imageFuture.onError(promise.error);
		imageFuture.onComplete(function(image:Image) {
			if (isCurrent != null && !isCurrent()) {
				promise.error('[psych-assets] Selected owner identity changed while image was loading');
				return;
			}
			if (image == null) {
				promise.error('[Assets] Could not load Image "' + id + '"');
				return;
			}
			var bitmap = BitmapData.fromImage(image);
			if (bitmap != null) bitmap.__asset = true;
			if (bitmap != null && useCache) PsychOwnerAssetLibraryCache.storeOpenFlBitmapData(
				identity, id, bitmap, cacheOverride, isCurrent);
			if (isCurrent != null && !isCurrent()) {
				if (cacheOverride != null) cacheOverride.removeBitmapData(id);
				promise.error('[psych-assets] Selected owner identity changed while image was loading');
				return;
			}
			promise.complete(bitmap);
		});
		return promise.future;
	}

	static function loadFontFromLime(fontFuture:Future<LimeFont>, identity:RuntimeOwnerAssetIdentity,
		id:String,
		useCache:Bool, ?cacheOverride:PsychOwnerOpenFlAssetCache,
		?isCurrent:Void->Bool):Future<Font> {
		var promise = new Promise<Font>();
		fontFuture.onProgress(promise.progress);
		fontFuture.onError(promise.error);
		fontFuture.onComplete(function(limeFont:LimeFont) {
			if (isCurrent != null && !isCurrent()) {
				promise.error('[psych-assets] Selected owner identity changed while font was loading');
				return;
			}
			var font = new Font();
			font.__fromLimeFont(limeFont);
			if (useCache) PsychOwnerAssetLibraryCache.storeOpenFlFont(identity, id, font,
				cacheOverride, isCurrent);
			if (isCurrent != null && !isCurrent()) {
				if (cacheOverride != null) cacheOverride.removeFont(id);
				promise.error('[psych-assets] Selected owner identity changed while font was loading');
				return;
			}
			promise.complete(font);
		});
		return promise.future;
	}

	static function loadSoundFromAudio(audioFuture:Future<AudioBuffer>, identity:RuntimeOwnerAssetIdentity,
		id:String,
		useCache:Bool, ?cacheOverride:PsychOwnerOpenFlAssetCache,
		?isCurrent:Void->Bool):Future<Sound> {
		var promise = new Promise<Sound>();
		audioFuture.onProgress(promise.progress);
		audioFuture.onError(promise.error);
		audioFuture.onComplete(function(audio:AudioBuffer) {
			if (isCurrent != null && !isCurrent()) {
				promise.error('[psych-assets] Selected owner identity changed while sound was loading');
				return;
			}
			if (audio == null) {
				promise.error('[Assets] Could not load Sound "' + id + '"');
				return;
			}
			var sound = Sound.fromAudioBuffer(audio);
			if (useCache) PsychOwnerAssetLibraryCache.storeOpenFlSound(identity, id, sound,
				cacheOverride, isCurrent);
			if (isCurrent != null && !isCurrent()) {
				if (cacheOverride != null) cacheOverride.removeSound(id);
				promise.error('[psych-assets] Selected owner identity changed while sound was loading');
				return;
			}
			promise.complete(sound);
		});
		return promise.future;
	}

	static function requiredForContext(context:SourceOwnerAssetContext, id:String,
		?expectedType:String):PsychOwnerAssetPathResult {
		var resolved = resolveForContext(context, id, expectedType);
		if (resolved.blocked)
			throw '[psych-assets] Refused asset outside selected owner: ' + Std.string(id);
		if (resolved.unavailable) {
			var lookup = context.lookupAsset(id, expectedType);
			throw '[psych-assets] Asset is unavailable in selected owner: ' + Std.string(id)
				+ ' (owner=' + context.ownerRoot + ', scope=' + (lookup == null ? context.scope : lookup.identity.scope)
				+ ', state=' + (lookup == null ? 'no-lookup' : lookup.result.state) + ')';
		}
		if (resolved.path == null)
			throw '[psych-assets] Asset is unavailable to selected owner: ' + Std.string(id);
		return resolved;
	}

	static function resolveForContext(context:SourceOwnerAssetContext, id:String,
		?expectedType:String):PsychOwnerAssetPathResult {
		var selected = context.lookupAsset(id, expectedType);
		if (selected != null && selected.result.state == 'found')
			return {path:selected.result.path, owned:true, blocked:false, unavailable:false};
		if (selected != null && selected.result.state != 'no-index'
			&& selected.result.state != 'unclaimed' && selected.result.state != 'missing') {
			if (context.allowOwnerPathFallback && selected.result.state != 'type-mismatch') {
				var indexedPhysical = PsychOwnerAssetPath.resolveInScope(context.ownerRoot, id,
					context.pathRoot, context.excludedSubtree);
				if (indexedPhysical.owned || indexedPhysical.blocked || indexedPhysical.unavailable)
					return indexedPhysical;
			}
			return {path:null, owned:false, blocked:false, unavailable:true};
		}
		if (context.allowOwnerPathFallback) {
			var ownerPath = PsychOwnerAssetPath.resolveInScope(context.ownerRoot, id,
				context.pathRoot, context.excludedSubtree);
			if (ownerPath.blocked || ownerPath.unavailable || ownerPath.owned) return ownerPath;
		}
		if (!context.allowNativeFallback)
			return {path:null, owned:false, blocked:false, unavailable:true};
		var clean = PsychOwnerAssetPath.cleanId(id);
		if (clean == null) return {path:null, owned:false, blocked:true, unavailable:false};
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
	static function guardGlobalLibraryMutation(context:SourceOwnerAssetContext,
		name:String, operation:String):Void {
		if (unsafeLibraryName(name))
			throw '[psych-assets] OpenFL library mutation cannot escape the selected owner';
		if (!context.allowNativeFallback
			|| context.libraryState(SourceLimeAssetIdentity.canonicalLibrary(name)) != 'unclaimed')
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

	static function cacheKey(owner:String, engine:String, scope:String, path:String):String
		return 'source-owner:' + owner + ':' + engine + ':' + scope + ':' + path;

	static function ownerLibraryAssetForContext(context:SourceOwnerAssetContext, id:String,
		expectedType:Null<String>):Null<PsychOwnerAssetLibraryAssetView> {
		var selected = context.lookupAsset(id, expectedType);
		if (selected == null || selected.result.state != 'found') return null;
		return PsychOwnerAssetLibraryCache.findLimeAsset(selected.identity, id, expectedType);
	}

	static function ownerIndexCacheIdForContext(context:SourceOwnerAssetContext, id:String,
		type:String):Null<String> {
		var selected = context.lookupAsset(id, type);
		if (selected == null || selected.result.state != 'found') return null;
		PsychOwnerAssetLibraryCache.openFlAssetCache(selected.identity);
		return id;
	}

	static function selectionGuardForContext(context:SourceOwnerAssetContext, id:String,
		type:Null<String>):Null<Void->Bool> {
		if (context == null || !context.composite) return null;
		var selected = context.lookupAsset(id, type);
		return selected != null && selected.result.state == 'found'
			? context.selectionGuard(id, type, selected.identity) : null;
	}

	static function ownerCacheKeyForContext(context:SourceOwnerAssetContext, id:String,
		type:String, path:String):String {
		var selected = context.lookupAsset(id, type);
		return selected != null && selected.result.state == 'found' ? id
			: cacheKey(context.ownerRoot, context.engine, context.cacheScope, path);
	}

	static function releaseOwnerLibrary(context:SourceOwnerAssetContext,
		name:String, operation:String, unload:Bool):Bool {
		if (unsafeLibraryName(name)) return false;
		var library = SourceLimeAssetIdentity.canonicalLibrary(name);
		var identities = context.identitiesForLibrary(library);
		if (identities.length > 0) {
			for (identity in identities) {
				if (identity.indexVersion < 2)
					throw '[psych-assets] Dynamic ' + operation + ' is unsupported for selected-owner asset libraries: ' + name;
				PsychOwnerAssetLibraryCache.unload(identity, library, unload);
			}
			return true;
		}
		if (context.libraryState(library) == 'unknown')
			throw '[psych-assets] Asset library identity is incomplete for selected owner: ' + name;
		return false;
	}

	static function loadCompositeLibrary(context:SourceOwnerAssetContext,
		identities:Array<RuntimeOwnerAssetIdentity>, library:String, proxy:Dynamic):Dynamic {
		for (identity in identities) if (identity.indexVersion < 2)
			return Future.withError('[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: ' + library);
		var promise = new Promise<Dynamic>();
		var remaining = identities.length;
		var view = ownerLibrary(context, library, proxy);
		for (identity in identities) {
			var future = PsychOwnerAssetLibraryCache.loadOpenFl(identity, library);
			future.onProgress(promise.progress);
			future.onError(promise.error);
			future.onComplete(function(_) {
				remaining--;
				if (remaining == 0) promise.complete(view);
			});
		}
		return promise.future;
	}

	static function assetTypeName(type:AssetType):Null<String>
		return type == null ? null : Std.string(type).toUpperCase();

	static function toLimeAssetType(type:AssetType):lime.utils.AssetType
		return cast (Std.string(type).toUpperCase():String);
}
