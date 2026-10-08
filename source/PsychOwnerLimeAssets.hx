package;

import haxe.io.Bytes;
import lime.app.Future;
import lime.graphics.Image;
import lime.media.AudioBuffer;
import lime.text.Font;
import lime.utils.AssetType;
import lime.utils.AssetCache as LimeAssetCache;
import lime.utils.Assets as LimeAssets;
import PsychOwnerAssetPath.PsychOwnerAssetPathResult;
import PsychOwnerAssetLibraryCache.PsychOwnerAssetLibraryAssetView;

using StringTools;

/**
	Lime Assets view for one selected Psych import.  Native asset IDs keep Lime's
	regular behavior; relative IDs first resolve inside the selected import root.
*/
class PsychOwnerLimeAssets {
	public static function create(ownerRoot:String):Dynamic {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == '')
			throw '[psych-assets] A valid selected import owner root is required';
		var engine = 'Psych Engine';
		var scope = 'package';
		var proxy:Dynamic = {};
		Reflect.setField(proxy, 'cache', PsychOwnerAssetLibraryCache.limeAssetCacheForOwner(
			owner, engine, scope, LimeAssets.cache));
		var ownerCache:LimeAssetCache = cast Reflect.field(proxy, 'cache');
		Reflect.setField(proxy, 'onChange', LimeAssets.onChange);
		Reflect.setField(proxy, 'exists', function(id:String, ?type:AssetType):Bool {
			var resolved = resolve(owner, id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return LimeAssets.exists(id, type) || (resolved.path != null && FNFAssets.exists(resolved.path));
		});
		Reflect.setField(proxy, 'getText', function(id:String):String {
			var resolved = required(owner, id, 'TEXT');
			var indexed = ownerLibraryAsset(owner, id, 'TEXT');
			if (indexed != null) return indexed.library.getText(indexed.id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !LimeAssets.exists(id, AssetType.TEXT)))
				return FNFAssets.getText(resolved.path);
			return LimeAssets.getText(id);
		});
		Reflect.setField(proxy, 'getBytes', function(id:String):Bytes {
			var resolved = required(owner, id, 'BINARY');
			var indexed = ownerLibraryAsset(owner, id, 'BINARY');
			if (indexed != null) return indexed.library.getBytes(indexed.id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !LimeAssets.exists(id, AssetType.BINARY)))
				return FNFAssets.getBytes(resolved.path);
			return LimeAssets.getBytes(id);
		});
		Reflect.setField(proxy, 'getImage', function(id:String, ?useCache:Bool = true):Image {
			var indexedCacheId = ownerIndexCacheId(owner, id, 'IMAGE');
			var cached = indexedCacheId == null ? null : PsychOwnerAssetLibraryCache.cachedLimeAssetIn(
				ownerCache, indexedCacheId, AssetType.IMAGE, useCache);
			if (cached != null) return cast cached;
			var resolved = required(owner, id, 'IMAGE');
			var indexed = ownerLibraryAsset(owner, id, 'IMAGE');
			if (indexed != null) return cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
				AssetType.IMAGE, useCache);
			if (!resolved.owned && LimeAssets.exists(id, AssetType.IMAGE))
				return LimeAssets.getImage(id, useCache);
			var key = ownerCacheKey(owner, id, 'IMAGE', resolved.path);
			if (useCache && ownerCache != null && ownerCache.enabled) {
				cached = PsychOwnerAssetLibraryCache.cachedLimeAssetIn(ownerCache, key, AssetType.IMAGE, useCache);
				if (cached != null) return cached;
			}
			var image = Image.fromBytes(FNFAssets.getBytes(resolved.path));
			if (image != null && useCache && ownerCache != null && ownerCache.enabled)
				ownerCache.set(key, AssetType.IMAGE, image);
			return image;
		});
		Reflect.setField(proxy, 'getAudioBuffer', function(id:String, ?useCache:Bool = true):AudioBuffer {
			var indexedCacheId = ownerIndexCacheId(owner, id, 'SOUND');
			var cached = indexedCacheId == null ? null : PsychOwnerAssetLibraryCache.cachedLimeAssetIn(
				ownerCache, indexedCacheId, AssetType.SOUND, useCache);
			if (cached != null) return cast cached;
			var resolved = required(owner, id, 'SOUND');
			var indexed = ownerLibraryAsset(owner, id, 'SOUND');
			if (indexed != null) return cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
				AssetType.SOUND, useCache);
			if (!resolved.owned && LimeAssets.exists(id, AssetType.SOUND))
				return LimeAssets.getAudioBuffer(id, useCache);
			var key = ownerCacheKey(owner, id, 'SOUND', resolved.path);
			if (useCache && ownerCache != null && ownerCache.enabled) {
				cached = PsychOwnerAssetLibraryCache.cachedLimeAssetIn(ownerCache, key, AssetType.SOUND, useCache);
				if (cached != null) return cached;
			}
			var audio = AudioBuffer.fromBytes(FNFAssets.getBytes(resolved.path));
			if (audio != null && useCache && ownerCache != null && ownerCache.enabled)
				ownerCache.set(key, AssetType.SOUND, audio);
			return audio;
		});
		Reflect.setField(proxy, 'getFont', function(id:String, ?useCache:Bool = true):Font {
			var indexedCacheId = ownerIndexCacheId(owner, id, 'FONT');
			var cached = indexedCacheId == null ? null : PsychOwnerAssetLibraryCache.cachedLimeAssetIn(
				ownerCache, indexedCacheId, AssetType.FONT, useCache);
			if (cached != null) return cast cached;
			var resolved = required(owner, id, 'FONT');
			var indexed = ownerLibraryAsset(owner, id, 'FONT');
			if (indexed != null) return cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
				AssetType.FONT, useCache);
			if (!resolved.owned && LimeAssets.exists(id, AssetType.FONT))
				return LimeAssets.getFont(id, useCache);
			var key = ownerCacheKey(owner, id, 'FONT', resolved.path);
			if (useCache && ownerCache != null && ownerCache.enabled) {
				cached = PsychOwnerAssetLibraryCache.cachedLimeAssetIn(ownerCache, key, AssetType.FONT, useCache);
				if (cached != null) return cast cached;
			}
			var font = Font.fromBytes(FNFAssets.getBytes(resolved.path));
			if (font != null && useCache && ownerCache != null && ownerCache.enabled)
				ownerCache.set(key, AssetType.FONT, font);
			return font;
		});
		Reflect.setField(proxy, 'getAsset', function(id:String, type:AssetType, ?useCache:Bool = true):Dynamic {
			var indexedCacheId = ownerIndexCacheId(owner, id, assetTypeName(type));
			var cached = indexedCacheId == null ? null
				: PsychOwnerAssetLibraryCache.cachedLimeAssetIn(ownerCache, indexedCacheId, type, useCache);
			if (cached != null) return cached;
			var resolved = required(owner, id, assetTypeName(type));
			var indexed = ownerLibraryAsset(owner, id, assetTypeName(type));
			if (indexed != null) return PsychOwnerAssetLibraryCache.getLimeAsset(indexed, type, useCache);
			if (!resolved.owned && LimeAssets.exists(id, type))
				return LimeAssets.getAsset(id, type, useCache);
			return switch (type) {
				case BINARY: FNFAssets.getBytes(resolved.path);
				case TEXT: FNFAssets.getText(resolved.path);
				case IMAGE: Reflect.callMethod(proxy, Reflect.field(proxy, 'getImage'), [id, useCache]);
				case FONT: Reflect.callMethod(proxy, Reflect.field(proxy, 'getFont'), [id, useCache]);
				case SOUND | MUSIC: Reflect.callMethod(proxy, Reflect.field(proxy, 'getAudioBuffer'), [id, useCache]);
				case TEMPLATE: throw 'Lime Assets does not support TEMPLATE assets';
				default: null;
			};
		});
		Reflect.setField(proxy, 'getPath', function(id:String):String {
			var resolved = resolve(owner, id, null);
			if (resolved.blocked || resolved.unavailable) return null;
			if (resolved.path != null && (resolved.owned || FNFAssets.exists(resolved.path))) return resolved.path;
			return LimeAssets.getPath(id);
		});
		Reflect.setField(proxy, 'isLocal', function(id:String, ?type:AssetType, ?useCache:Bool = true):Bool {
			var resolved = resolve(owner, id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return LimeAssets.isLocal(id, type, useCache);
		});
		Reflect.setField(proxy, 'list', function(?type:AssetType):Array<String>
			return list(owner, engine, scope, type, null));
		Reflect.setField(proxy, 'getLibrary', function(name:String):Dynamic {
			if (unsafeLibraryName(name)) throw '[psych-assets] Lime asset libraries cannot escape the selected owner';
			var identity = RuntimeOwnerAssetIdentity.acquire(owner, engine, scope);
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(name);
			var state = identity.libraryState(libraryName);
			if (state == 'declared') {
				if (identity.indexVersion < 2) return ownerLibrary(owner, engine, scope, name, proxy);
				return PsychOwnerAssetLibraryCache.getLime(identity, libraryName);
			}
			if (state == 'unknown') throw '[psych-assets] Asset library identity is incomplete for selected owner: ' + name;
			return LimeAssets.getLibrary(name);
		});
		Reflect.setField(proxy, 'hasLibrary', function(name:String):Bool {
			if (unsafeLibraryName(name)) return false;
			var state = RuntimeOwnerAssetIdentity.ownerLibraryState(owner, engine, scope,
				SourceLimeAssetIdentity.canonicalLibrary(name));
			if (state == 'declared') return true;
			if (state == 'unknown') return false;
			return LimeAssets.hasLibrary(name);
		});
		Reflect.setField(proxy, 'registerLibrary', function(name:String, library:Dynamic):Void {
			guardGlobalLibraryMutation(owner, engine, scope, name, 'register');
			LimeAssets.registerLibrary(name, library);
		});
		Reflect.setField(proxy, 'unloadLibrary', function(name:String):Void {
			if (releaseOwnerLibrary(owner, engine, scope, name, 'unload', true)) return;
			guardGlobalLibraryMutation(owner, engine, scope, name, 'unload');
			LimeAssets.unloadLibrary(name);
		});
		Reflect.setField(proxy, 'removeLibrary', function(name:String, ?unload:Bool = true):Void {
			if (releaseOwnerLibrary(owner, engine, scope, name, 'remove', unload)) return;
			guardGlobalLibraryMutation(owner, engine, scope, name, 'remove');
			LimeAssets.removeLibrary(name, unload);
		});
		Reflect.setField(proxy, 'loadLibrary', function(id:String):Dynamic {
			if (unsafeLibraryName(id)) return Future.withError('[psych-assets] Lime asset libraries cannot escape the selected owner');
			var identity = RuntimeOwnerAssetIdentity.acquire(owner, engine, scope);
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(id);
			var state = identity.libraryState(
				libraryName);
			if (state == 'declared') {
				if (identity.indexVersion < 2)
					return Future.withError('[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: ' + id);
				return PsychOwnerAssetLibraryCache.loadLime(identity, libraryName);
			}
			if (state == 'unknown') return Future.withError('[psych-assets] Asset library identity is incomplete for selected owner: ' + id);
			return LimeAssets.loadLibrary(id);
		});
		Reflect.setField(proxy, 'loadAsset', function(id:String, type:AssetType, ?useCache:Bool = true):Dynamic {
			return load(owner, id, type, useCache, proxy);
		});
		Reflect.setField(proxy, 'loadText', function(id:String):Dynamic return load(owner, id, AssetType.TEXT, false, proxy));
		Reflect.setField(proxy, 'loadBytes', function(id:String):Dynamic return load(owner, id, AssetType.BINARY, false, proxy));
		Reflect.setField(proxy, 'loadImage', function(id:String, ?useCache:Bool = true):Dynamic return load(owner, id, AssetType.IMAGE, useCache, proxy));
		Reflect.setField(proxy, 'loadAudioBuffer', function(id:String, ?useCache:Bool = true):Dynamic return load(owner, id, AssetType.SOUND, useCache, proxy));
		Reflect.setField(proxy, 'loadFont', function(id:String, ?useCache:Bool = true):Dynamic return load(owner, id, AssetType.FONT, useCache, proxy));
		return proxy;
	}

	static function load(owner:String, id:String, type:AssetType, useCache:Bool, proxy:Dynamic):Dynamic {
		var cache:LimeAssetCache = cast Reflect.field(proxy, 'cache');
		var cacheable = switch (type) { case FONT | IMAGE | MUSIC | SOUND: true; default: false; };
		var indexedCacheId = ownerIndexCacheId(owner, id, assetTypeName(type));
		if (useCache && cacheable && indexedCacheId != null) {
			var cached = PsychOwnerAssetLibraryCache.cachedLimeAssetIn(cache, indexedCacheId, type, true);
			if (cached != null) return Future.withValue(cached);
		}
		var resolved = resolve(owner, id, assetTypeName(type));
		var indexed:PsychOwnerAssetLibraryAssetView;
		try indexed = ownerLibraryAsset(owner, id, assetTypeName(type)) catch (error:Dynamic)
			return Future.withError(error);
		if (indexed != null) return switch (type) {
			case BINARY: indexed.library.loadBytes(indexed.id);
			case TEXT: indexed.library.loadText(indexed.id);
			case IMAGE | FONT | SOUND | MUSIC:
				PsychOwnerAssetLibraryCache.loadLimeAsset(indexed, type, useCache);
			default: Future.withError('[psych-assets] Unsupported selected-owner Lime asset type: ' + Std.string(type));
		};
		if (resolved.blocked) return Future.withError('[psych-assets] Refused asset outside selected owner: ' + id);
		if (resolved.unavailable) return Future.withError('[psych-assets] Asset is unavailable in selected owner: ' + id);
		if (!resolved.owned && LimeAssets.exists(id, type)) {
			return switch (type) {
				case BINARY: LimeAssets.loadBytes(id);
				case TEXT: LimeAssets.loadText(id);
				case IMAGE: LimeAssets.loadImage(id, useCache);
				case FONT: LimeAssets.loadFont(id, useCache);
				case SOUND | MUSIC: LimeAssets.loadAudioBuffer(id, useCache);
				default: LimeAssets.loadAsset(id, type, useCache);
			};
		}
		if (!resolved.owned && (resolved.unavailable || resolved.path == null
			|| !FNFAssets.exists(resolved.path)))
			return LimeAssets.loadAsset(id, type, useCache);
		try {
			var asset:Dynamic = switch (type) {
				case BINARY: FNFAssets.getBytes(resolved.path);
				case TEXT: FNFAssets.getText(resolved.path);
				case IMAGE: Reflect.callMethod(proxy, Reflect.field(proxy, 'getImage'), [id, useCache]);
				case FONT: Reflect.callMethod(proxy, Reflect.field(proxy, 'getFont'), [id, useCache]);
				case SOUND | MUSIC: Reflect.callMethod(proxy, Reflect.field(proxy, 'getAudioBuffer'), [id, useCache]);
				default: null;
			};
			return Future.withValue(asset);
		} catch (error:Dynamic) {
			return Future.withError(error);
		}
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
			var physical = PsychOwnerAssetPath.resolve(owner, id);
			if (indexed.state != 'type-mismatch' && physical.owned) return physical;
			return {path:null, owned:false, blocked:false, unavailable:true};
		}
		var ownerPath = PsychOwnerAssetPath.resolve(owner, id);
		if (ownerPath.blocked || ownerPath.unavailable || ownerPath.owned)
			return ownerPath;
		var clean = PsychOwnerAssetPath.cleanId(id);
		if (clean == null) return ownerPath;
		if (expectedType == null ? LimeAssets.exists(id) : LimeAssets.exists(id, cast expectedType))
			return {path:id, owned:false, blocked:false, unavailable:false};
		if (FNFAssets.exists(clean)) return {path:clean, owned:false, blocked:false, unavailable:false};
		if (!clean.toLowerCase().startsWith('assets/')) {
			var nativePath = 'assets/' + clean;
			if (FNFAssets.exists(nativePath)) return {path:nativePath, owned:false, blocked:false, unavailable:false};
		}
		return {path:id, owned:false, blocked:false, unavailable:false};
	}

	static function list(owner:String, engine:String, scope:String, type:AssetType,
		library:Null<String>):Array<String> {
		var output = LimeAssets.list(type);
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
		Reflect.setField(proxy, 'getBytes', function(id:String):Bytes return call('getBytes', [qualified(id)]));
		Reflect.setField(proxy, 'getImage', function(id:String, ?useCache:Bool = true):Image
			return call('getImage', [qualified(id), useCache]));
		Reflect.setField(proxy, 'getAudioBuffer', function(id:String, ?useCache:Bool = true):AudioBuffer
			return call('getAudioBuffer', [qualified(id), useCache]));
		Reflect.setField(proxy, 'getFont', function(id:String, ?useCache:Bool = true):Font
			return call('getFont', [qualified(id), useCache]));
		Reflect.setField(proxy, 'getAsset', function(id:String, type:AssetType, ?useCache:Bool = true):Dynamic
			return call('getAsset', [qualified(id), type, useCache]));
		Reflect.setField(proxy, 'getPath', function(id:String):String return call('getPath', [qualified(id)]));
		Reflect.setField(proxy, 'isLocal', function(id:String, ?type:AssetType, ?useCache:Bool = true):Bool
			return call('isLocal', [qualified(id), type, useCache]));
		Reflect.setField(proxy, 'list', function(?type:AssetType):Array<String>
			return RuntimeOwnerAssetIdentity.ownerList(owner, engine, scope, library, assetTypeName(type)));
		Reflect.setField(proxy, 'loadAsset', function(id:String, type:AssetType, ?useCache:Bool = true):Dynamic
			return call('loadAsset', [qualified(id), type, useCache]));
		Reflect.setField(proxy, 'loadText', function(id:String):Dynamic return call('loadText', [qualified(id)]));
		Reflect.setField(proxy, 'loadBytes', function(id:String):Dynamic return call('loadBytes', [qualified(id)]));
		Reflect.setField(proxy, 'loadImage', function(id:String, ?useCache:Bool = true):Dynamic
			return call('loadImage', [qualified(id), useCache]));
		Reflect.setField(proxy, 'loadAudioBuffer', function(id:String, ?useCache:Bool = true):Dynamic
			return call('loadAudioBuffer', [qualified(id), useCache]));
		Reflect.setField(proxy, 'loadFont', function(id:String, ?useCache:Bool = true):Dynamic
			return call('loadFont', [qualified(id), useCache]));
		return proxy;
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

	static function unsafeLibraryName(name:String):Bool {
		if (name == null || StringTools.trim(name) == '') return false;
		var clean = PsychOwnerAssetPath.cleanId(name);
		return clean == null || clean.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/');
	}

	/** Owner libraries are virtual index views, not Lime AssetLibrary instances.
		Never let an owner-scoped mutation unload or replace a same-named host
		library. Unclaimed global libraries retain Lime's legacy behavior. */
	static function guardGlobalLibraryMutation(owner:String, engine:String, scope:String,
		name:String, operation:String):Void {
		if (unsafeLibraryName(name))
			throw '[psych-assets] Lime library mutation cannot escape the selected owner';
		var state = RuntimeOwnerAssetIdentity.ownerLibraryState(owner, engine, scope,
			SourceLimeAssetIdentity.canonicalLibrary(name));
		if (state != 'unclaimed')
			throw '[psych-assets] Dynamic ' + operation + ' is unsupported for selected-owner asset libraries: ' + name;
	}

	static function cacheKey(owner:String, path:String):String return 'psych-owner:' + owner + ':' + path;

	static function ownerCacheKey(owner:String, id:String, type:String, path:String):String {
		var indexed = RuntimeOwnerAssetIdentity.lookup(owner, 'Psych Engine', 'package', id, type);
		return indexed.state == 'found' ? id : cacheKey(owner, path);
	}

	static function ownerIndexCacheId(owner:String, id:String, type:String):Null<String> {
		var identity = RuntimeOwnerAssetIdentity.acquire(owner, 'Psych Engine', 'package');
		if (identity.bindingState == 'ready') PsychOwnerAssetLibraryCache.limeAssetCache(identity);
		var indexed = identity.resolve(id, type);
		return indexed.state == 'found' ? id : null;
	}

	static function assetTypeName(type:AssetType):Null<String>
		return type == null ? null : Std.string(type).toUpperCase();
}
