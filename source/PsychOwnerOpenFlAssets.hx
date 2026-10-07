package;

import lime.app.Future;
import openfl.display.BitmapData;
import openfl.events.Event;
import openfl.media.Sound;
import openfl.text.Font;
import openfl.utils.AssetType;
import openfl.utils.Assets as OpenFlAssets;
import openfl.utils.ByteArray;
import PsychOwnerAssetPath.PsychOwnerAssetPathResult;

using StringTools;

/** OpenFL Assets facade that keeps Psych file reads inside the selected import. */
class PsychOwnerOpenFlAssets {
	public static function create(ownerRoot:String):Dynamic {
		var owner = PsychOwnerAssetPath.normalizeOwner(ownerRoot);
		if (owner == '')
			throw '[psych-assets] A valid selected import owner root is required';
		var engine = 'Psych Engine';
		var scope = 'package';
		var proxy:Dynamic = {};
		Reflect.setField(proxy, 'cache', OpenFlAssets.cache);
		Reflect.setField(proxy, 'exists', function(id:String, ?type:AssetType):Bool {
			var resolved = resolve(owner, id, assetTypeName(type));
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return OpenFlAssets.exists(id, type) || (resolved.path != null && FNFAssets.exists(resolved.path));
		});
		Reflect.setField(proxy, 'getText', function(id:String):String {
			var resolved = required(owner, id, 'TEXT');
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !OpenFlAssets.exists(id, AssetType.TEXT)))
				return FNFAssets.getText(resolved.path);
			return OpenFlAssets.getText(id);
		});
		Reflect.setField(proxy, 'getBytes', function(id:String):ByteArray {
			var resolved = required(owner, id, 'BINARY');
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !OpenFlAssets.exists(id, AssetType.BINARY)))
				return ByteArray.fromBytes(FNFAssets.getBytes(resolved.path));
			return OpenFlAssets.getBytes(id);
		});
		Reflect.setField(proxy, 'getBitmapData', function(id:String, ?useCache:Bool = true):BitmapData {
			var resolved = required(owner, id, 'IMAGE');
			if (!resolved.owned && OpenFlAssets.exists(id, AssetType.IMAGE))
				return OpenFlAssets.getBitmapData(id, useCache);
			var key = cacheKey(owner, resolved.path);
			if (useCache && OpenFlAssets.cache.enabled && OpenFlAssets.cache.hasBitmapData(key)) {
				var cached = OpenFlAssets.cache.getBitmapData(key);
				if (cached != null) return cached;
			}
			var bitmap = FNFAssets.getBitmapData(resolved.path, useCache);
			if (bitmap != null && useCache && OpenFlAssets.cache.enabled)
				OpenFlAssets.cache.setBitmapData(key, bitmap);
			return bitmap;
		});
		Reflect.setField(proxy, 'getSound', function(id:String, ?useCache:Bool = true):Sound {
			return getSound(owner, id, useCache, 'SOUND');
		});
		Reflect.setField(proxy, 'getMusic', function(id:String, ?useCache:Bool = true):Sound {
			return getSound(owner, id, useCache, 'MUSIC');
		});
		Reflect.setField(proxy, 'getFont', function(id:String, ?useCache:Bool = true):Font {
			var resolved = required(owner, id, 'FONT');
			if (!resolved.owned && OpenFlAssets.exists(id, AssetType.FONT))
				return OpenFlAssets.getFont(id, useCache);
			var key = cacheKey(owner, resolved.path);
			if (useCache && OpenFlAssets.cache.enabled && OpenFlAssets.cache.hasFont(key)) {
				var cached = OpenFlAssets.cache.getFont(key);
				if (cached != null) return cached;
			}
			var font = Font.fromBytes(ByteArray.fromBytes(FNFAssets.getBytes(resolved.path)));
			if (font != null && useCache && OpenFlAssets.cache.enabled)
				OpenFlAssets.cache.setFont(key, font);
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
			var state = RuntimeOwnerAssetIdentity.ownerLibraryState(owner, engine, scope,
				SourceLimeAssetIdentity.canonicalLibrary(name));
			if (state == 'declared') return ownerLibrary(owner, engine, scope, name, proxy);
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
			var state = RuntimeOwnerAssetIdentity.ownerLibraryState(owner, engine, scope,
				SourceLimeAssetIdentity.canonicalLibrary(name));
			if (state == 'declared') return Future.withValue(ownerLibrary(owner, engine, scope, name, proxy));
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
			guardGlobalLibraryMutation(owner, engine, scope, name, 'unload');
			OpenFlAssets.unloadLibrary(name);
		});
		return proxy;
	}

	static function getSound(owner:String, id:String, useCache:Bool, expectedType:String):Sound {
		var resolved = required(owner, id, expectedType);
		if (!resolved.owned && OpenFlAssets.exists(id, AssetType.SOUND))
			return expectedType == 'MUSIC' ? OpenFlAssets.getMusic(id, useCache) : OpenFlAssets.getSound(id, useCache);
		var key = cacheKey(owner, resolved.path);
		if (useCache && OpenFlAssets.cache.enabled && OpenFlAssets.cache.hasSound(key)) {
			var cached = OpenFlAssets.cache.getSound(key);
			if (cached != null) return cached;
		}
		var sound = FNFAssets.getSound(resolved.path, useCache);
		if (sound != null && useCache && OpenFlAssets.cache.enabled)
			OpenFlAssets.cache.setSound(key, sound);
		return sound;
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
		var resolved = resolve(owner, id, assetTypeName(type));
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

	static function assetTypeName(type:AssetType):Null<String>
		return type == null ? null : Std.string(type).toUpperCase();
}
