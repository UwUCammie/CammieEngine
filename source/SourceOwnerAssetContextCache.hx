package;

import lime.utils.AssetCache as LimeAssetCache;
import PsychOwnerAssetLibraryCache.PsychOwnerOpenFlAssetCache;
import RuntimeOwnerAssetIdentity;
import haxe.io.Path;
import StringTools;

using StringTools;

private typedef SourceOwnerAssetContextCacheEntry = {
	var signature:String;
	var lime:LimeAssetCache;
	var openFl:PsychOwnerOpenFlAssetCache;
	var libraries:Map<String, SourceCompositeAssetLibrary>;
	var openFlLibraries:Map<String, openfl.utils.AssetLibrary>;
}

/**
	Stable cache objects for a facade that composes several exact owner scopes.
	The scoped identities remain the authority for individual reads. This cache
	only preserves the source Assets.cache surface and is cleared whenever any
	selected scope proof changes.
*/
@:keep
@:access(openfl.utils.AssetLibrary)
class SourceOwnerAssetContextCache {
	static var entries:Map<String, SourceOwnerAssetContextCacheEntry> = new Map();

	public static function lime(context:SourceOwnerAssetContext):LimeAssetCache
		return state(context).lime;

	public static function openFl(context:SourceOwnerAssetContext):PsychOwnerOpenFlAssetCache
		return state(context).openFl;

	public static function limeLibrary(context:SourceOwnerAssetContext, library:String,
		assets:Dynamic):SourceCompositeAssetLibrary {
		var entry = state(context);
		var name = SourceLimeAssetIdentity.canonicalLibrary(library);
		var view = entry.libraries.get(name);
		if (view == null) {
			view = new SourceCompositeAssetLibrary(context, name, assets);
			entry.libraries.set(name, view);
		}
		return view;
	}

	public static function openFlLibrary(context:SourceOwnerAssetContext, library:String,
		assets:Dynamic):openfl.utils.AssetLibrary {
		var entry = state(context);
		var name = SourceLimeAssetIdentity.canonicalLibrary(library);
		var view = entry.openFlLibraries.get(name);
		if (view == null) {
			view = new openfl.utils.AssetLibrary();
			view.__proxy = limeLibrary(context, name, assets);
			entry.openFlLibraries.set(name, view);
		}
		return view;
	}

	public static function refresh(context:SourceOwnerAssetContext,
		identities:Array<RuntimeOwnerAssetIdentity>):Void {
		if (context == null || !context.composite) return;
		var entry = entries.get(key(context));
		if (entry == null) return;
		var signature = proofSignature(context, identities);
		if (entry.signature == signature) return;
		clear(entry);
		entry.signature = signature;
	}

	public static function releaseOwner(ownerRoot:String):Void {
		// Retirement can run after the owned directory has already been removed.
		// Do not use normalizeOwner here: it requires that directory to exist and
		// would leave the cache objects retained on the exact cleanup path.
		if (ownerRoot == null) return;
		var owner = Path.normalize(StringTools.replace(StringTools.trim(ownerRoot), '\\', '/'));
		if (!owner.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/')) return;
		#if windows
		owner = owner.toLowerCase();
		#end
		var prefix = owner + '|';
		var remove:Array<String> = [];
		for (cacheKey in entries.keys()) if (cacheKey.startsWith(prefix)) remove.push(cacheKey);
		for (cacheKey in remove) {
			var entry = entries.get(cacheKey);
			clear(entry);
			entries.remove(cacheKey);
		}
	}

	static function state(context:SourceOwnerAssetContext):SourceOwnerAssetContextCacheEntry {
		if (context == null || !context.composite)
			throw '[source-assets] A composite owner context is required for this cache';
		var cacheKey = key(context);
		var found = entries.get(cacheKey);
		if (found == null) {
			var lime = new LimeAssetCache();
			found = {signature:'', lime:lime, openFl:new PsychOwnerOpenFlAssetCache(lime),
				libraries:new Map(), openFlLibraries:new Map()};
			entries.set(cacheKey, found);
		}
		var identities:Array<RuntimeOwnerAssetIdentity> = [];
		for (scope in context.identityScopes)
			identities.push(RuntimeOwnerAssetIdentity.acquire(context.ownerRoot, context.engine, scope));
		var signature = proofSignature(context, identities);
		if (found.signature != signature) {
			clear(found);
			found.signature = signature;
		}
		return found;
	}

	public static function proofSignature(context:SourceOwnerAssetContext,
		identities:Array<RuntimeOwnerAssetIdentity>):String {
		var parts:Array<String> = [];
		for (i in 0...context.identityScopes.length) {
			var identity = identities != null && i < identities.length ? identities[i] : null;
			parts.push(context.identityScopes[i] + '=' + (identity == null ? 'missing'
				: identity.bindingState + ':' + (identity.bindingSignature == null ? '' : identity.bindingSignature)));
		}
		return parts.join('|');
	}

	static function clear(entry:SourceOwnerAssetContextCacheEntry):Void {
		if (entry.lime != null) entry.lime.clear();
		if (entry.openFl != null) entry.openFl.clear();
		for (library in entry.libraries) library.retire();
		entry.libraries.clear();
		entry.openFlLibraries.clear();
	}

	static function key(context:SourceOwnerAssetContext):String {
		#if windows
		var owner = context.ownerRoot.toLowerCase();
		#else
		var owner = context.ownerRoot;
		#end
		return owner + '|' + context.engine + '|' + context.identityScopes.join(',');
	}
}
