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
import SourceOwnerAssetContext;

using StringTools;

/**
	Lime Assets view for one selected Psych import.  Native asset IDs keep Lime's
	regular behavior; relative IDs first resolve inside the selected import root.
*/
class PsychOwnerLimeAssets {
	public static function create(ownerRoot:String):Dynamic
		return createForContext(SourceOwnerAssetContext.psych(ownerRoot));

	/** Build the same Lime facade for one authenticated source engine/scope.
		The context selects an exact identity; it does not grant fallback rights. */
	public static function createForContext(context:SourceOwnerAssetContext):Dynamic {
		if (context == null) throw '[psych-assets] A selected-owner source context is required';
		var owner = context.ownerRoot;
		var engine = context.engine;
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
			? SourceOwnerAssetContextCache.lime(context)
			: PsychOwnerAssetLibraryCache.limeAssetCacheForOwner(owner, engine, context.cacheScope, LimeAssets.cache));
		var ownerCache:LimeAssetCache = cast Reflect.field(proxy, 'cache');
		var assetEvents = SourceOwnerAssetsEvents.forContext(context);
		Reflect.setField(proxy, 'onChange', assetEvents.limeOnChange);
		Reflect.setField(proxy, 'exists', function(id:String, ?type:AssetType):Bool {
			var resolved = resolveSelected(id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return (context.allowNativeFallback && LimeAssets.exists(id, type))
				|| (resolved.path != null && FNFAssets.exists(resolved.path));
		});
		Reflect.setField(proxy, 'getText', function(id:String):String {
			var resolved = requiredSelected(id, 'TEXT');
			var indexed = ownerLibraryAssetSelected(id, 'TEXT');
			if (indexed != null) return indexed.library.getText(indexed.id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& (!context.allowNativeFallback || !LimeAssets.exists(id, AssetType.TEXT))))
				return FNFAssets.getText(resolved.path);
			if (!context.allowNativeFallback) throw '[psych-assets] Asset is unavailable to selected owner: ' + id;
			return LimeAssets.getText(id);
		});
		Reflect.setField(proxy, 'getBytes', function(id:String):Bytes {
			var resolved = requiredSelected(id, 'BINARY');
			var indexed = ownerLibraryAssetSelected(id, 'BINARY');
			if (indexed != null) return indexed.library.getBytes(indexed.id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& (!context.allowNativeFallback || !LimeAssets.exists(id, AssetType.BINARY))))
				return FNFAssets.getBytes(resolved.path);
			if (!context.allowNativeFallback) throw '[psych-assets] Asset is unavailable to selected owner: ' + id;
			return LimeAssets.getBytes(id);
		});
		Reflect.setField(proxy, 'getImage', function(id:String, ?useCache:Bool = true):Image {
			var indexedCacheId = ownerIndexCacheIdSelected(id, 'IMAGE');
			var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
			var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, 'IMAGE');
			var cached = sourceCacheId == null ? null : PsychOwnerAssetLibraryCache.cachedLimeAssetIn(
				ownerCache, sourceCacheId, AssetType.IMAGE, useCache);
			if (cached != null && (cacheGuard == null || cacheGuard())) return cast cached;
			var resolved = requiredSelected(id, 'IMAGE');
			var indexed = ownerLibraryAssetSelected(id, 'IMAGE');
			if (indexed != null) {
				var current = context.composite ? context.selectionGuard(id, 'IMAGE', indexed.identity) : null;
				return cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
					AssetType.IMAGE, useCache, context.composite ? ownerCache : null, current);
			}
			if (context.allowNativeFallback && !resolved.owned && LimeAssets.exists(id, AssetType.IMAGE))
				return LimeAssets.getImage(id, useCache);
			var key = ownerCacheKeySelected(id, 'IMAGE', resolved.path);
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
			var indexedCacheId = ownerIndexCacheIdSelected(id, 'SOUND');
			var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
			var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, 'SOUND');
			var cached = sourceCacheId == null ? null : PsychOwnerAssetLibraryCache.cachedLimeAssetIn(
				ownerCache, sourceCacheId, AssetType.SOUND, useCache);
			if (cached != null && (cacheGuard == null || cacheGuard())) return cast cached;
			var resolved = requiredSelected(id, 'SOUND');
			var indexed = ownerLibraryAssetSelected(id, 'SOUND');
			if (indexed != null) {
				var current = context.composite ? context.selectionGuard(id, 'SOUND', indexed.identity) : null;
				return cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
					AssetType.SOUND, useCache, context.composite ? ownerCache : null, current);
			}
			if (context.allowNativeFallback && !resolved.owned && LimeAssets.exists(id, AssetType.SOUND))
				return LimeAssets.getAudioBuffer(id, useCache);
			var key = ownerCacheKeySelected(id, 'SOUND', resolved.path);
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
			var indexedCacheId = ownerIndexCacheIdSelected(id, 'FONT');
			var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
			var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, 'FONT');
			var cached = sourceCacheId == null ? null : PsychOwnerAssetLibraryCache.cachedLimeAssetIn(
				ownerCache, sourceCacheId, AssetType.FONT, useCache);
			if (cached != null && (cacheGuard == null || cacheGuard())) return cast cached;
			var resolved = requiredSelected(id, 'FONT');
			var indexed = ownerLibraryAssetSelected(id, 'FONT');
			if (indexed != null) {
				var current = context.composite ? context.selectionGuard(id, 'FONT', indexed.identity) : null;
				return cast PsychOwnerAssetLibraryCache.getLimeAsset(indexed,
					AssetType.FONT, useCache, context.composite ? ownerCache : null, current);
			}
			if (context.allowNativeFallback && !resolved.owned && LimeAssets.exists(id, AssetType.FONT))
				return LimeAssets.getFont(id, useCache);
			var key = ownerCacheKeySelected(id, 'FONT', resolved.path);
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
			var indexedCacheId = ownerIndexCacheIdSelected(id, assetTypeName(type));
			var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
			var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, assetTypeName(type));
			var cached = sourceCacheId == null ? null
				: PsychOwnerAssetLibraryCache.cachedLimeAssetIn(ownerCache, sourceCacheId, type, useCache);
			if (cached != null && (cacheGuard == null || cacheGuard())) return cached;
			var resolved = requiredSelected(id, assetTypeName(type));
			var indexed = ownerLibraryAssetSelected(id, assetTypeName(type));
			if (indexed != null) {
				var current = context.composite ? context.selectionGuard(id, assetTypeName(type), indexed.identity) : null;
				return PsychOwnerAssetLibraryCache.getLimeAsset(indexed, type, useCache,
					context.composite ? ownerCache : null, current);
			}
			if (context.allowNativeFallback && !resolved.owned && LimeAssets.exists(id, type))
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
			var resolved = resolveSelected(id, null);
			if (resolved.blocked || resolved.unavailable) return null;
			if (resolved.path != null && (resolved.owned || FNFAssets.exists(resolved.path))) return resolved.path;
			return context.allowNativeFallback ? LimeAssets.getPath(id) : null;
		});
		Reflect.setField(proxy, 'isLocal', function(id:String, ?type:AssetType, ?useCache:Bool = true):Bool {
			var resolved = resolveSelected(id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return context.allowNativeFallback && LimeAssets.isLocal(id, type, useCache);
		});
		Reflect.setField(proxy, 'list', function(?type:AssetType):Array<String>
			return list(context, type, null));
		Reflect.setField(proxy, 'getLibrary', function(name:String):Dynamic {
			if (unsafeLibraryName(name)) throw '[psych-assets] Lime asset libraries cannot escape the selected owner';
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(name);
			var identities = context.identitiesForLibrary(libraryName);
			if (identities.length > 0) {
				if (context.composite)
					return SourceOwnerAssetContextCache.limeLibrary(context, libraryName, proxy);
				if (identities.length == 1 && identities[0].indexVersion >= 2)
					return PsychOwnerAssetLibraryCache.getLime(identities[0], libraryName);
				return ownerLibrary(context, name, proxy);
			}
			var state = context.libraryState(libraryName);
			if (state == 'unknown') throw '[psych-assets] Asset library identity is incomplete for selected owner: ' + name;
			return context.allowNativeFallback ? LimeAssets.getLibrary(name) : null;
		});
		Reflect.setField(proxy, 'hasLibrary', function(name:String):Bool {
			if (unsafeLibraryName(name)) return false;
			var state = context.libraryState(SourceLimeAssetIdentity.canonicalLibrary(name));
			if (state == 'declared') return true;
			if (state == 'unknown') return false;
			return context.allowNativeFallback && LimeAssets.hasLibrary(name);
		});
		Reflect.setField(proxy, 'registerLibrary', function(name:String, library:Dynamic):Void {
			guardGlobalLibraryMutationSelected(name, 'register');
			LimeAssets.registerLibrary(name, library);
		});
		Reflect.setField(proxy, 'unloadLibrary', function(name:String):Void {
			if (releaseOwnerLibrarySelected(name, 'unload', true)) return;
			guardGlobalLibraryMutationSelected(name, 'unload');
			LimeAssets.unloadLibrary(name);
		});
		Reflect.setField(proxy, 'removeLibrary', function(name:String, ?unload:Bool = true):Void {
			if (releaseOwnerLibrarySelected(name, 'remove', unload)) return;
			guardGlobalLibraryMutationSelected(name, 'remove');
			LimeAssets.removeLibrary(name, unload);
		});
		Reflect.setField(proxy, 'loadLibrary', function(id:String):Dynamic {
			if (unsafeLibraryName(id)) return Future.withError('[psych-assets] Lime asset libraries cannot escape the selected owner');
			var libraryName = SourceLimeAssetIdentity.canonicalLibrary(id);
			var identities:Array<RuntimeOwnerAssetIdentity>;
			try identities = context.identitiesForLibrary(libraryName) catch (error:Dynamic)
				return Future.withError(error);
			if (identities.length > 0) {
				if (context.composite)
					return SourceOwnerAssetContextCache.limeLibrary(context, libraryName, proxy).load();
				if (identities.length == 1) {
					if (identities[0].indexVersion < 2)
						return Future.withError('[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: ' + id);
					return PsychOwnerAssetLibraryCache.loadLime(identities[0], libraryName);
				}
				return loadCompositeLibrary(context, identities, libraryName, proxy);
			}
			var state = context.libraryState(libraryName);
			if (state == 'unknown') return Future.withError('[psych-assets] Asset library identity is incomplete for selected owner: ' + id);
			return context.allowNativeFallback ? LimeAssets.loadLibrary(id)
				: Future.withError('[psych-assets] Lime library is not declared by selected owner: ' + id);
		});
		Reflect.setField(proxy, 'loadAsset', function(id:String, type:AssetType, ?useCache:Bool = true):Dynamic {
			return load(owner, id, type, useCache, proxy, context);
		});
		Reflect.setField(proxy, 'loadText', function(id:String):Dynamic return load(owner, id, AssetType.TEXT, false, proxy, context));
		Reflect.setField(proxy, 'loadBytes', function(id:String):Dynamic return load(owner, id, AssetType.BINARY, false, proxy, context));
		Reflect.setField(proxy, 'loadImage', function(id:String, ?useCache:Bool = true):Dynamic return load(owner, id, AssetType.IMAGE, useCache, proxy, context));
		Reflect.setField(proxy, 'loadAudioBuffer', function(id:String, ?useCache:Bool = true):Dynamic return load(owner, id, AssetType.SOUND, useCache, proxy, context));
		Reflect.setField(proxy, 'loadFont', function(id:String, ?useCache:Bool = true):Dynamic return load(owner, id, AssetType.FONT, useCache, proxy, context));
		return proxy;
	}

	static function load(owner:String, id:String, type:AssetType, useCache:Bool, proxy:Dynamic,
		context:SourceOwnerAssetContext):Dynamic {
		var cache:LimeAssetCache = cast Reflect.field(proxy, 'cache');
		var cacheable = switch (type) { case FONT | IMAGE | MUSIC | SOUND: true; default: false; };
		var indexedCacheId = ownerIndexCacheIdForContext(context, id, assetTypeName(type));
		var sourceCacheId = indexedCacheId == null && context.composite ? id : indexedCacheId;
		var cacheGuard = indexedCacheId == null ? null : selectionGuardForContext(context, id, assetTypeName(type));
		if (useCache && cacheable && sourceCacheId != null) {
			var cached = PsychOwnerAssetLibraryCache.cachedLimeAssetIn(cache, sourceCacheId, type, true);
			if (cached != null && (cacheGuard == null || cacheGuard())) return Future.withValue(cached);
		}
		var resolved = resolveForContext(context, id, assetTypeName(type));
		var indexed:PsychOwnerAssetLibraryAssetView;
		try indexed = ownerLibraryAssetForContext(context, id, assetTypeName(type)) catch (error:Dynamic)
			return Future.withError(error);
		if (indexed != null) {
			var current = context.composite ? context.selectionGuard(id, assetTypeName(type), indexed.identity) : null;
			return switch (type) {
				case BINARY: PsychOwnerAssetLibraryCache.guardFuture(indexed.library.loadBytes(indexed.id), current);
				case TEXT: PsychOwnerAssetLibraryCache.guardFuture(indexed.library.loadText(indexed.id), current);
				case IMAGE | FONT | SOUND | MUSIC:
					PsychOwnerAssetLibraryCache.loadLimeAsset(indexed, type, useCache,
						context.composite ? cache : null, current);
				default: Future.withError('[psych-assets] Unsupported selected-owner Lime asset type: ' + Std.string(type));
			};
		}
		if (resolved.blocked) return Future.withError('[psych-assets] Refused asset outside selected owner: ' + id);
		if (resolved.unavailable) return Future.withError('[psych-assets] Asset is unavailable in selected owner: ' + id);
		if (context.allowNativeFallback && !resolved.owned && LimeAssets.exists(id, type)) {
			return switch (type) {
				case BINARY: LimeAssets.loadBytes(id);
				case TEXT: LimeAssets.loadText(id);
				case IMAGE: LimeAssets.loadImage(id, useCache);
				case FONT: LimeAssets.loadFont(id, useCache);
				case SOUND | MUSIC: LimeAssets.loadAudioBuffer(id, useCache);
				default: LimeAssets.loadAsset(id, type, useCache);
			};
		}
		if (resolved.path == null || (!resolved.owned && !FNFAssets.exists(resolved.path))) {
			if (!context.allowNativeFallback)
				return Future.withError('[psych-assets] Asset is unavailable to selected owner: ' + id);
			return LimeAssets.loadAsset(id, type, useCache);
		}
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

	static function requiredForContext(context:SourceOwnerAssetContext, id:String,
		?expectedType:String):PsychOwnerAssetPathResult {
		var resolved = resolveForContext(context, id, expectedType);
		if (resolved.blocked)
			throw '[psych-assets] Refused asset outside selected owner: ' + Std.string(id);
		if (resolved.unavailable)
			throw '[psych-assets] Asset is unavailable in selected owner: ' + Std.string(id);
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
		if (expectedType == null ? LimeAssets.exists(id) : LimeAssets.exists(id, cast expectedType))
			return {path:id, owned:false, blocked:false, unavailable:false};
		if (FNFAssets.exists(clean)) return {path:clean, owned:false, blocked:false, unavailable:false};
		if (!clean.toLowerCase().startsWith('assets/')) {
			var nativePath = 'assets/' + clean;
			if (FNFAssets.exists(nativePath)) return {path:nativePath, owned:false, blocked:false, unavailable:false};
		}
		return {path:id, owned:false, blocked:false, unavailable:false};
	}

	static function list(context:SourceOwnerAssetContext, type:AssetType,
		library:Null<String>):Array<String> {
		var output = context.allowNativeFallback ? LimeAssets.list(type) : [];
		var importedPrefix = CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/';
		output = output.filter(function(id:String) return id == null || !id.toLowerCase().startsWith(importedPrefix));
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
			return context.listAssets(library, assetTypeName(type)));
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
		PsychOwnerAssetLibraryCache.limeAssetCache(selected.identity);
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

	static function unsafeLibraryName(name:String):Bool {
		if (name == null || StringTools.trim(name) == '') return false;
		var clean = PsychOwnerAssetPath.cleanId(name);
		return clean == null || clean.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/');
	}

	/** Owner libraries are virtual index views, not Lime AssetLibrary instances.
		Never let an owner-scoped mutation unload or replace a same-named host
		library. Unclaimed global libraries retain Lime's legacy behavior. */
	static function guardGlobalLibraryMutation(context:SourceOwnerAssetContext,
		name:String, operation:String):Void {
		if (unsafeLibraryName(name))
			throw '[psych-assets] Lime library mutation cannot escape the selected owner';
		if (!context.allowNativeFallback
			|| context.libraryState(SourceLimeAssetIdentity.canonicalLibrary(name)) != 'unclaimed')
			throw '[psych-assets] Dynamic ' + operation + ' is unsupported for selected-owner asset libraries: ' + name;
	}

	static function cacheKey(owner:String, engine:String, scope:String, path:String):String
		return 'source-owner:' + owner + ':' + engine + ':' + scope + ':' + path;

	static function loadCompositeLibrary(context:SourceOwnerAssetContext,
		identities:Array<RuntimeOwnerAssetIdentity>, library:String, proxy:Dynamic):Dynamic {
		for (identity in identities) if (identity.indexVersion < 2)
			return Future.withError('[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: ' + library);
		var promise = new lime.app.Promise<Dynamic>();
		var remaining = identities.length;
		var view = ownerLibrary(context, library, proxy);
		for (identity in identities) {
			var future = PsychOwnerAssetLibraryCache.loadLime(identity, library);
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
}
