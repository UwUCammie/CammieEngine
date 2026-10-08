package;

import lime.app.Future;
import lime.app.Promise;
import lime.text.Font as LimeFont;
import lime.utils.AssetCache as LimeAssetCache;
import lime.utils.AssetType;
import lime.utils.AssetLibrary;
import lime.utils.AssetManifest;
import RuntimeOwnerAssetIdentity.RuntimeOwnerAssetIdentityEntry;
import RuntimeOwnerAssetIdentity.RuntimeOwnerAssetLibraryLoadProfile;
import openfl.display.BitmapData;
import openfl.media.Sound;
import openfl.text.Font;

using StringTools;

private typedef PsychOwnerAssetLibraryCacheEntry = {
	var identity:RuntimeOwnerAssetIdentity;
	var libraryName:String;
	var sourceLibrary:AssetLibrary;
	var limeLibrary:PsychOwnerAssetLibraryView;
	var openFlLibrary:Dynamic;
	var loadFuture:Future<AssetLibrary>;
	var openFlLoadFuture:Future<Dynamic>;
}

private typedef PsychOwnerAssetCacheState = {
	var identity:Null<RuntimeOwnerAssetIdentity>;
	var lime:LimeAssetCache;
	var openFl:PsychOwnerOpenFlAssetCache;
}

typedef PsychOwnerAssetLibraryAssetView = {
	var identity:RuntimeOwnerAssetIdentity;
	var library:AssetLibrary;
	var libraryName:String;
	var cacheId:String;
	var id:String;
	var entry:RuntimeOwnerAssetIdentityEntry;
}

/**
	Owner-local Lime AssetLibrary instances for receipt-verified file-backed
	indexes. They deliberately never enter Lime/OpenFL's process-global library
	registries or caches.
*/
@:keep
@:access(openfl.utils.AssetLibrary)
class PsychOwnerAssetLibraryCache {
	static var entries:Map<String, PsychOwnerAssetLibraryCacheEntry> = new Map();
	static var assetCaches:Map<String, PsychOwnerAssetCacheState> = new Map();

	/** Each owner scope exposes ordinary Lime cache methods without sharing IDs
		or cache lifetimes with the host's global Assets cache. */
	public static function limeAssetCache(identity:RuntimeOwnerAssetIdentity):LimeAssetCache
		return cacheState(identity).lime;

	/** OpenFL's base cache removes matching entries from Lime's global cache.
		The owner subtype keeps cache mutations within this identity. */
	public static function openFlAssetCache(identity:RuntimeOwnerAssetIdentity):PsychOwnerOpenFlAssetCache
		return cacheState(identity).openFl;

	/** Facades retain this cache object for their lifetime. cacheState reuses the
		object for a later proof of the same owner scope, clearing its old values. */
	public static function limeAssetCacheForOwner(owner:String, engine:String,
		scope:String, fallback:Dynamic):Dynamic {
		try {
			var identity = RuntimeOwnerAssetIdentity.acquire(owner, engine, scope);
			if (identity != null && identity.bindingState == "ready") return limeAssetCache(identity);
		} catch (_:Dynamic) {}
		// A facade can outlive the import transaction that publishes its owner
		// index. Keep its cache owner-local while that binding is pending; using
		// the host global cache here would let a same-ID host asset win later.
		return pendingCacheState(owner, engine, scope).lime;
	}

	public static function openFlAssetCacheForOwner(owner:String, engine:String,
		scope:String, fallback:Dynamic):Dynamic {
		try {
			var identity = RuntimeOwnerAssetIdentity.acquire(owner, engine, scope);
			if (identity != null && identity.bindingState == "ready") return openFlAssetCache(identity);
		} catch (_:Dynamic) {}
		return pendingCacheState(owner, engine, scope).openFl;
	}

	public static function cachedLimeAsset(identity:RuntimeOwnerAssetIdentity, id:String,
		type:lime.utils.AssetType, useCache:Bool):Dynamic {
		return cachedLimeAssetIn(limeAssetCache(identity), id, type, useCache);
	}

	/** Read the caller's scoped Lime cache before attempting library resolution. */
	public static function cachedLimeAssetIn(cache:LimeAssetCache, id:String,
		type:lime.utils.AssetType, useCache:Bool):Dynamic {
		if (!useCache || cache == null || !cache.enabled) return null;
		var asset:Dynamic = switch (type) {
			case FONT: cache.font.get(id);
			case IMAGE: cache.image.get(id);
			case SOUND | MUSIC: cache.audio.get(id);
			default: null;
		};
		return switch (type) {
			case IMAGE: asset != null && (cast asset:lime.graphics.Image).buffer != null ? asset : null;
			case SOUND | MUSIC: asset != null ? asset : null;
			case FONT: asset;
			default: null;
		};
	}

	public static function storeLimeAsset(identity:RuntimeOwnerAssetIdentity, id:String,
		type:lime.utils.AssetType, asset:Dynamic):Void {
		if (asset == null || !cacheIdentityIsCurrent(identity)) return;
		var cache = limeAssetCache(identity);
		if (!cache.enabled) return;
		try cache.set(id, type, asset) catch (_:Dynamic) {}
	}

	/** Exact Lime Assets.getAsset behavior for cacheable owner-library entries. */
	public static function getLimeAsset(view:PsychOwnerAssetLibraryAssetView,
		type:AssetType, useCache:Bool):Dynamic {
		if (view == null) return null;
		var cached = cachedLimeAsset(view.identity, view.cacheId, type, useCache);
		if (cached != null) return cached;
		var asset = view.library.getAsset(view.id, Std.string(type).toUpperCase());
		if (useCache && limeCacheable(type) && asset != null && limeAssetCache(view.identity).enabled)
			storeLimeAsset(view.identity, view.cacheId, type, asset);
		return asset;
	}

	/** Exact Lime Assets.loadAsset behavior, including cache hits and the
		load-start enabled snapshot used by its completion callback. */
	public static function loadLimeAsset(view:PsychOwnerAssetLibraryAssetView,
		type:AssetType, useCache:Bool):Dynamic {
		if (view == null) return null;
		var cacheable = limeCacheable(type);
		var cacheEnabledAtStart = useCache && cacheable && limeAssetCache(view.identity).enabled;
		if (cacheEnabledAtStart) {
			var cached = cachedLimeAsset(view.identity, view.cacheId, type, true);
			if (cached != null) return Future.withValue(cached);
		}
		var future = view.library.loadAsset(view.id, Std.string(type).toUpperCase());
		if (cacheEnabledAtStart) {
			future.onComplete(function(asset:Dynamic) {
				storeLimeAssetIgnoringEnabled(view.identity, view.cacheId, type, asset);
			});
		}
		return future;
	}

	/** Matches Lime Assets.loadAsset: write only after completion and keep the
		original Future's identity, progress, and error behavior. */
	public static function trackLimeLoad<T>(identity:RuntimeOwnerAssetIdentity, id:String,
		type:lime.utils.AssetType, useCache:Bool, future:Future<T>):Future<T> {
		if (!useCache || !limeCacheable(type) || !limeAssetCache(identity).enabled) return future;
		future.onComplete(function(asset:T) storeLimeAssetIgnoringEnabled(identity, id, type, asset));
		return future;
	}

	public static function cachedOpenFlSound(identity:RuntimeOwnerAssetIdentity,
		id:String):Null<Sound> {
		var cache = openFlAssetCache(identity);
		return cache.enabled ? cache.getSound(id) : null;
	}

	public static function cachedOpenFlBitmapData(identity:RuntimeOwnerAssetIdentity,
		id:String):Null<BitmapData> {
		var cache = openFlAssetCache(identity);
		return cache.enabled ? cache.getBitmapData(id) : null;
	}

	public static function storeOpenFlBitmapData(identity:RuntimeOwnerAssetIdentity,
		id:String, bitmap:BitmapData):Void {
		if (bitmap == null || !cacheIdentityIsCurrent(identity)) return;
		var cache = openFlAssetCache(identity);
		if (cache.enabled) cache.setBitmapData(id, bitmap);
	}

	public static function storeOpenFlSound(identity:RuntimeOwnerAssetIdentity,
		id:String, sound:Sound):Void {
		if (sound == null || !cacheIdentityIsCurrent(identity)) return;
		var cache = openFlAssetCache(identity);
		if (cache.enabled) cache.setSound(id, sound);
	}

	public static function cachedOpenFlFont(identity:RuntimeOwnerAssetIdentity,
		id:String):Null<Font> {
		var cache = openFlAssetCache(identity);
		return cache.enabled ? cache.getFont(id) : null;
	}

	public static function storeOpenFlFont(identity:RuntimeOwnerAssetIdentity,
		id:String, font:Font):Void {
		if (font == null || !cacheIdentityIsCurrent(identity)) return;
		var cache = openFlAssetCache(identity);
		if (cache.enabled) cache.setFont(id, font);
	}

	public static function getLime(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):AssetLibrary {
		return item(identity, libraryName).limeLibrary;
	}

	/** Return an existing owner library without constructing or loading one. */
	public static function peekLime(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):Null<AssetLibrary> {
		if (identity == null) return null;
		var entry = entries.get(cacheKey(identity, libraryName));
		return entry != null && entry.identity == identity && isCurrent(entry)
			? entry.limeLibrary : null;
	}

	public static function peekOpenFl(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):Dynamic {
		if (identity == null) return null;
		var entry = entries.get(cacheKey(identity, libraryName));
		return entry != null && entry.identity == identity && isCurrent(entry)
			? entry.openFlLibrary : null;
	}

	public static function findLimeAsset(identity:RuntimeOwnerAssetIdentity, id:String,
		expectedType:Null<String>):Null<PsychOwnerAssetLibraryAssetView> {
		if (identity == null) return null;
		var found = identity.resolve(id, expectedType);
		if (found.state != "found" || found.entry == null) return null;
		var library:AssetLibrary = null;
		if (identity.indexVersion >= 2) {
			if (!canConstructFileBackedLibrary(identity, found.library)) return null;
			library = getLime(identity, found.library);
		} else {
			library = peekLime(identity, found.library);
		}
		return library == null ? null : {identity:identity, library:library,
			libraryName:found.library, cacheId:id, id:found.id, entry:found.entry};
	}

	static function canConstructFileBackedLibrary(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):Bool {
		if (identity == null || identity.bindingState != "ready" || identity.indexVersion < 2
			|| identity.libraryState(libraryName) != "declared" || !identity.complete
			|| !identity.librariesComplete || identity.loadTarget == null) return false;
		var profile = identity.libraryLoadProfile(libraryName);
		if (profile == null || profile.state != "standard-file"
			|| profile.projectPreloadState != "known" || profile.projectEmbedState != "known") return false;
		for (entry in identity.entriesForLibrary(libraryName)) {
			if (entry.preloadState != "enabled" && entry.preloadState != "disabled") return false;
			var typeName = SourceLimeAssetIdentity.normalizeType(entry.type);
			var supported = switch (typeName) {
				case "BINARY" | "FONT" | "IMAGE" | "MUSIC" | "SOUND" | "TEXT": true;
				default: false;
			};
			if (!supported || entry.size < 0
				|| identity.resolve(libraryName + ":" + entry.id, typeName).state != "found") return false;
		}
		return true;
	}

	public static function getOpenFl(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):Dynamic {
		return openFlForEntry(item(identity, libraryName));
	}

	public static function loadLime(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):Future<AssetLibrary> {
		var entry:PsychOwnerAssetLibraryCacheEntry;
		try entry = item(identity, libraryName) catch (error:Dynamic) return cast Future.withError(error);
		if (entry.loadFuture != null) return entry.loadFuture;

		var promise = new Promise<AssetLibrary>();
		entry.loadFuture = promise.future;
		var loading:Future<AssetLibrary>;
		try loading = entry.limeLibrary.load() catch (error:Dynamic) {
			promise.error(error);
			return entry.loadFuture;
		}
		loading.onProgress(promise.progress);
		loading.onError(function(error:Dynamic) {
			if (!identityIsCurrent(entry.identity)) {
				entry.sourceLibrary.unload();
				promise.error(staleMessage());
			} else {
				promise.error(error);
			}
		});
		loading.onComplete(function(_loaded:AssetLibrary) {
			if (!identityIsCurrent(entry.identity)) {
				entry.sourceLibrary.unload();
				promise.error(staleMessage());
				return;
			}
			promise.complete(entry.limeLibrary);
		});
		return entry.loadFuture;
	}

	public static function loadOpenFl(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):Dynamic {
		var entry:PsychOwnerAssetLibraryCacheEntry;
		try entry = item(identity, libraryName) catch (error:Dynamic) return Future.withError(error);
		if (entry.openFlLoadFuture != null) return entry.openFlLoadFuture;
		var promise = new Promise<Dynamic>();
		entry.openFlLoadFuture = promise.future;
		var wrapper:Dynamic;
		try wrapper = openFlForEntry(entry) catch (error:Dynamic) {
			promise.error(error);
			return entry.openFlLoadFuture;
		}
		var limeFuture = loadLime(identity, libraryName);
		limeFuture.onProgress(promise.progress);
		limeFuture.onError(function(error:Dynamic)
			promise.error(identityIsCurrent(entry.identity) ? error : staleMessage()));
		limeFuture.onComplete(function(_library:AssetLibrary) {
			if (!identityIsCurrent(entry.identity)) {
				promise.error(staleMessage());
				return;
			}
			promise.complete(wrapper);
		});
		return entry.openFlLoadFuture;
	}

	public static function unload(identity:RuntimeOwnerAssetIdentity, libraryName:String,
		unloadContents:Bool = true):Void {
		var library = SourceLimeAssetIdentity.canonicalLibrary(libraryName);
		var state = assetCaches.get(assetCacheKey(identity));
		if (state != null && state.identity == identity && state.lime != null)
			state.lime.clear(library + ":");
		var key = cacheKey(identity, libraryName);
		var entry = entries.get(key);
		if (entry == null || entry.identity != identity) return;
		entries.remove(key);
		if (unloadContents && entry.sourceLibrary != null) entry.sourceLibrary.unload();
		entry.openFlLibrary = null;
	}

	public static function releaseIdentity(identity:RuntimeOwnerAssetIdentity):Void {
		if (identity == null) return;
		PsychOwnerMusicStreamLease.releaseIdentity(identity);
		identity.retireAssetLibraryViews();
		var assets = assetCaches.get(assetCacheKey(identity));
		if (assets != null && assets.identity == identity) {
			clearAssetCaches(assets);
			assets.identity = null;
		}
		var remove:Array<String> = [];
		for (key in entries.keys()) {
			var entry = entries.get(key);
			if (entry != null && entry.identity == identity) remove.push(key);
		}
		for (key in remove) {
			var entry = entries.get(key);
			entries.remove(key);
			if (entry != null && entry.sourceLibrary != null) entry.sourceLibrary.unload();
		}
	}

	public static function releaseOwner(ownerRoot:String):Void {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == "") return;
		PsychOwnerMusicStreamLease.releaseOwner(owner);
		var keyPrefix = ownerKey(owner) + "|";
		var assetCacheKeys:Array<String> = [];
		for (key in assetCaches.keys()) if (key.startsWith(keyPrefix)) assetCacheKeys.push(key);
		for (key in assetCacheKeys) {
			var state = assetCaches.get(key);
			if (state != null) clearAssetCaches(state);
			assetCaches.remove(key);
		}
		var remove:Array<String> = [];
		for (key in entries.keys()) if (key.startsWith(keyPrefix)) remove.push(key);
		for (key in remove) {
			var entry = entries.get(key);
			entries.remove(key);
			if (entry != null && entry.sourceLibrary != null) entry.sourceLibrary.unload();
		}
	}

	static function item(identity:RuntimeOwnerAssetIdentity,
		libraryName:String):PsychOwnerAssetLibraryCacheEntry {
		if (identity == null || identity.bindingState != "ready")
			throw "[psych-assets] A verified owner asset index is required to load a Lime library";
		var library = SourceLimeAssetIdentity.canonicalLibrary(libraryName);
		if (identity.libraryState(library) != "declared")
			throw "[psych-assets] Lime library is not declared by selected owner: " + library;
		if (identity.indexVersion < 2)
			throw "[psych-assets] Selected-owner library load metadata is unavailable; refresh this import: " + library;
		var profile = identity.libraryLoadProfile(library);
		if (profile == null)
			throw "[psych-assets] Selected-owner library load profile is missing: " + library;
		if (profile.state != "standard-file")
			throw loadProfileError(profile, library);
		if (!identity.complete || !identity.librariesComplete || identity.loadTarget == null
			|| profile.projectPreloadState != "known" || profile.projectEmbedState != "known")
			throw "[psych-assets] Selected-owner Lime load profile is incomplete: " + library;

		var key = cacheKey(identity, library);
		var existing = entries.get(key);
		if (existing != null && existing.identity == identity && isCurrent(existing)) return existing;
		if (existing != null) {
			entries.remove(key);
			if (existing.sourceLibrary != null) existing.sourceLibrary.unload();
		}

		var libraryEntries = identity.entriesForLibrary(library);
		var manifest = new AssetManifest();
		manifest.name = library;
		manifest.rootPath = identity.owner;
		manifest.version = 2;
		for (entry in libraryEntries) {
			if (entry.preloadState != "enabled" && entry.preloadState != "disabled")
				throw "[psych-assets] Selected-owner preload state is unresolved for " + library + ":" + entry.id;
			var assetType = SourceLimeAssetIdentity.normalizeType(entry.type);
			var supportedType = switch (assetType) {
				case "BINARY" | "FONT" | "IMAGE" | "MUSIC" | "SOUND" | "TEXT": true;
				default: false;
			};
			if (!supportedType || entry.size < 0)
				throw "[psych-assets] Selected-owner asset entry is not file-backed: " + library + ":" + entry.id;
			var resolved = identity.resolve(library + ":" + entry.id, assetType);
			if (resolved.state != "found")
				throw "[psych-assets] Selected-owner asset is unavailable: " + library + ":" + entry.id;
			manifest.assets.push({id:entry.id, path:entry.ownerRelative, type:assetType,
				preload:entry.preloadState == "enabled", size:entry.size});
		}

		var nativeLibrary = new PsychOwnerFileAssetLibrary(manifest);
		if (nativeLibrary == null)
			throw "[psych-assets] Lime could not create the selected-owner file-backed library: " + library;
		var created:PsychOwnerAssetLibraryCacheEntry = {identity:identity, libraryName:library,
			sourceLibrary:nativeLibrary, limeLibrary:null, openFlLibrary:null,
			loadFuture:null, openFlLoadFuture:null};
		created.limeLibrary = new PsychOwnerAssetLibraryView(nativeLibrary,
			function() return identityIsCurrent(identity), staleMessage());
		identity.trackAssetLibraryView(created.limeLibrary);
		entries.set(key, created);
		return created;
	}

	static function isCurrent(entry:PsychOwnerAssetLibraryCacheEntry):Bool {
		if (entry == null || entries.get(cacheKey(entry.identity, entry.libraryName)) != entry) return false;
		return identityIsCurrent(entry.identity);
	}

	static function identityIsCurrent(identity:RuntimeOwnerAssetIdentity):Bool {
		if (identity == null || identity.bindingState != "ready") return false;
		var current:RuntimeOwnerAssetIdentity;
		try current = RuntimeOwnerAssetIdentity.acquire(identity.owner, identity.engine, identity.scope)
		catch (_:Dynamic) return false;
		return current == identity && current.bindingState == "ready"
			&& current.bindingSignature == identity.bindingSignature;
	}

	static function cacheIdentityIsCurrent(identity:RuntimeOwnerAssetIdentity):Bool {
		if (identity == null) return false;
		var current:RuntimeOwnerAssetIdentity;
		try current = RuntimeOwnerAssetIdentity.acquire(identity.owner, identity.engine, identity.scope)
		catch (_:Dynamic) return false;
		return current == identity && current.bindingState == identity.bindingState
			&& current.bindingSignature == identity.bindingSignature;
	}

	static function cacheState(identity:RuntimeOwnerAssetIdentity):PsychOwnerAssetCacheState {
		if (!cacheIdentityIsCurrent(identity))
			throw staleMessage();
		var key = assetCacheKey(identity);
		var state = assetCaches.get(key);
		if (state == null) {
			var lime = new LimeAssetCache();
			state = {identity:identity, lime:lime, openFl:new PsychOwnerOpenFlAssetCache(lime)};
			assetCaches.set(key, state);
		} else if (state.identity != identity) {
			clearAssetCaches(state);
			state.identity = identity;
		}
		return state;
	}

	/** Allocate the same stable owner cache object before an index is ready.
		cacheState(identity) will clear and bind this object to the validated
		identity when publication completes, so long-lived facades do not need a
		new proxy and never borrow the host cache. */
	static function pendingCacheState(owner:String, engine:String,
		scope:String):PsychOwnerAssetCacheState {
		var normalizedOwner = PsychOwnerAssetPath.normalizeOwner(owner);
		var normalizedEngine = ImportRevision.normalizeEngine(engine);
		var normalizedScope = scope == null || scope == "" ? "package" : scope;
		if (normalizedOwner == "" || normalizedEngine == null
			|| SourceLimeAssetIdentity.sidecarFilename(normalizedEngine, normalizedScope) == null)
			throw "[psych-assets] A valid owner asset cache identity is required";
		var key = ownerKey(normalizedOwner) + "|" + normalizedEngine + "|" + normalizedScope;
		var state = assetCaches.get(key);
		if (state == null) {
			var lime = new LimeAssetCache();
			state = {identity:null, lime:lime, openFl:new PsychOwnerOpenFlAssetCache(lime)};
			assetCaches.set(key, state);
		}
		return state;
	}

	static function clearAssetCaches(state:PsychOwnerAssetCacheState):Void {
		if (state == null) return;
		if (state.lime != null) state.lime.clear();
		if (state.openFl != null) state.openFl.clear();
	}

	static function storeLimeAssetIgnoringEnabled(identity:RuntimeOwnerAssetIdentity,
		id:String, type:AssetType, asset:Dynamic):Void {
		if (asset == null || !limeCacheable(type) || !cacheIdentityIsCurrent(identity)) return;
		try limeAssetCache(identity).set(id, type, asset) catch (_:Dynamic) {}
	}

	static function limeCacheable(type:lime.utils.AssetType):Bool
		return switch (type) {
			case FONT | IMAGE | MUSIC | SOUND: true;
			default: false;
		};

	static function openFlForEntry(entry:PsychOwnerAssetLibraryCacheEntry):Dynamic {
		if (entry == null) throw "[psych-assets] Selected-owner OpenFL library view is unavailable";
		if (entry.openFlLibrary != null) return entry.openFlLibrary;
		#if lime
		var wrapper = new openfl.utils.AssetLibrary();
		wrapper.__proxy = entry.limeLibrary;
		entry.openFlLibrary = wrapper;
		return wrapper;
		#else
		throw "[psych-assets] OpenFL owner libraries require the Lime runtime";
		#end
	}

	static function staleMessage():String
		return "[psych-assets] Selected owner identity changed while its asset library was retained";

	static function loadProfileError(profile:RuntimeOwnerAssetLibraryLoadProfile,
		library:String):String {
		var diagnostic = profile.diagnostic == null ? "" : ": " + profile.diagnostic;
		return "[psych-assets] Selected-owner library load profile is " + profile.state + diagnostic + ": " + library;
	}

	static function cacheKey(identity:RuntimeOwnerAssetIdentity, library:String):String
		return ownerKey(identity.owner) + "|" + identity.engine + "|" + identity.scope
			+ "|" + library;

	static function assetCacheKey(identity:RuntimeOwnerAssetIdentity):String
		return ownerKey(identity.owner) + "|" + identity.engine + "|" + identity.scope;

	static function ownerKey(owner:String):String {
		#if windows
		return owner.toLowerCase();
		#else
		return owner;
		#end
	}
}

/**
	A manifest-backed Lime library for verified owner files. Lime 8.3.2's
	standard FONT path opens a native face from its filesystem path and keeps
	that path alive. Owner files can be atomically replaced during refresh, so
	decode the same verified bytes through Lime's normal Font decoder instead.
	The inherited cache and load() preload lifecycle remain the source library's.
*/
@:keep
@:access(lime.utils.AssetLibrary)
private class PsychOwnerFileAssetLibrary extends AssetLibrary {
	public function new(manifest:AssetManifest) {
		super();
		if (manifest == null) throw "[psych-assets] A verified owner manifest is required";
		__fromManifest(manifest);
	}

	public override function getFont(id:String):LimeFont {
		if (cachedFonts.exists(id)) return cachedFonts.get(id);
		return LimeFont.fromBytes(getBytes(id));
	}

	public override function loadFont(id:String):Future<LimeFont> {
		if (cachedFonts.exists(id)) return Future.withValue(cachedFonts.get(id));
		return loadBytes(id).then(function(bytes) {
			return LimeFont.loadFromBytes(bytes).then(function(font) {
				return font == null ? cast Future.withError("") : Future.withValue(font);
			});
		});
	}
}

/** OpenFL's standard removal methods also edit LimeAssets.cache by the raw ID.
	For an owner facade, route that matching removal into the same owner's Lime
	cache while keeping the inherited OpenFL cache data structure and API. */
@:keep
class PsychOwnerOpenFlAssetCache extends openfl.utils.AssetCache {
	final limeCache:LimeAssetCache;

	public function new(limeCache:LimeAssetCache) {
		super();
		if (limeCache == null) throw "[psych-assets] Owner Lime asset cache is required";
		this.limeCache = limeCache;
	}

	public override function removeBitmapData(id:String):Bool {
		limeCache.image.remove(id);
		return bitmapData.remove(id);
	}

	public override function removeFont(id:String):Bool {
		limeCache.font.remove(id);
		return font.remove(id);
	}

	public override function removeSound(id:String):Bool {
		limeCache.audio.remove(id);
		return sound.remove(id);
	}
}
