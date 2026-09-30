package;

import haxe.io.Bytes;
import lime.app.Future;
import lime.graphics.Image;
import lime.media.AudioBuffer;
import lime.text.Font;
import lime.utils.AssetType;
import lime.utils.Assets as LimeAssets;
import PsychOwnerAssetPath.PsychOwnerAssetPathResult;

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
		var proxy:Dynamic = {};
		Reflect.setField(proxy, 'cache', LimeAssets.cache);
		Reflect.setField(proxy, 'onChange', LimeAssets.onChange);
		Reflect.setField(proxy, 'exists', function(id:String, ?type:AssetType):Bool {
			var resolved = resolve(owner, id);
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return LimeAssets.exists(id, type) || (resolved.path != null && FNFAssets.exists(resolved.path));
		});
		Reflect.setField(proxy, 'getText', function(id:String):String {
			var resolved = required(owner, id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !LimeAssets.exists(id, AssetType.TEXT)))
				return FNFAssets.getText(resolved.path);
			return LimeAssets.getText(id);
		});
		Reflect.setField(proxy, 'getBytes', function(id:String):Bytes {
			var resolved = required(owner, id);
			if (resolved.owned || (resolved.path != null && FNFAssets.exists(resolved.path)
				&& !LimeAssets.exists(id, AssetType.BINARY)))
				return FNFAssets.getBytes(resolved.path);
			return LimeAssets.getBytes(id);
		});
		Reflect.setField(proxy, 'getImage', function(id:String, ?useCache:Bool = true):Image {
			var resolved = required(owner, id);
			if (!resolved.owned && LimeAssets.exists(id, AssetType.IMAGE))
				return LimeAssets.getImage(id, useCache);
			var key = cacheKey(owner, resolved.path);
			if (useCache && LimeAssets.cache.enabled) {
				var cached = LimeAssets.cache.image.get(key);
				if (cached != null) return cached;
			}
			var image = Image.fromBytes(FNFAssets.getBytes(resolved.path));
			if (image != null && useCache && LimeAssets.cache.enabled)
				LimeAssets.cache.set(key, AssetType.IMAGE, image);
			return image;
		});
		Reflect.setField(proxy, 'getAudioBuffer', function(id:String, ?useCache:Bool = true):AudioBuffer {
			var resolved = required(owner, id);
			if (!resolved.owned && LimeAssets.exists(id, AssetType.SOUND))
				return LimeAssets.getAudioBuffer(id, useCache);
			var key = cacheKey(owner, resolved.path);
			if (useCache && LimeAssets.cache.enabled) {
				var cached = LimeAssets.cache.audio.get(key);
				if (cached != null) return cached;
			}
			var audio = AudioBuffer.fromBytes(FNFAssets.getBytes(resolved.path));
			if (audio != null && useCache && LimeAssets.cache.enabled)
				LimeAssets.cache.set(key, AssetType.SOUND, audio);
			return audio;
		});
		Reflect.setField(proxy, 'getFont', function(id:String, ?useCache:Bool = true):Font {
			var resolved = required(owner, id);
			if (!resolved.owned && LimeAssets.exists(id, AssetType.FONT))
				return LimeAssets.getFont(id, useCache);
			var key = cacheKey(owner, resolved.path);
			if (useCache && LimeAssets.cache.enabled) {
				var cached:Dynamic = LimeAssets.cache.font.get(key);
				if (cached != null) return cast cached;
			}
			var font = Font.fromBytes(FNFAssets.getBytes(resolved.path));
			if (font != null && useCache && LimeAssets.cache.enabled)
				LimeAssets.cache.set(key, AssetType.FONT, font);
			return font;
		});
		Reflect.setField(proxy, 'getAsset', function(id:String, type:AssetType, ?useCache:Bool = true):Dynamic {
			var resolved = required(owner, id);
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
			var resolved = resolve(owner, id);
			if (resolved.blocked || resolved.unavailable) return null;
			if (resolved.path != null && (resolved.owned || FNFAssets.exists(resolved.path))) return resolved.path;
			return LimeAssets.getPath(id);
		});
		Reflect.setField(proxy, 'isLocal', function(id:String, ?type:AssetType, ?useCache:Bool = true):Bool {
			var resolved = resolve(owner, id);
			if (resolved.blocked || resolved.unavailable) return false;
			if (resolved.owned) return true;
			return LimeAssets.isLocal(id, type, useCache);
		});
		Reflect.setField(proxy, 'list', function(?type:AssetType):Array<String> return LimeAssets.list(type));
		Reflect.setField(proxy, 'getLibrary', function(name:String):Dynamic {
			if (unsafeLibraryName(name)) throw '[psych-assets] Lime asset libraries cannot escape the selected owner';
			return LimeAssets.getLibrary(name);
		});
		Reflect.setField(proxy, 'hasLibrary', function(name:String):Bool {
			return !unsafeLibraryName(name) && LimeAssets.hasLibrary(name);
		});
		Reflect.setField(proxy, 'registerLibrary', function(name:String, library:Dynamic):Void
			LimeAssets.registerLibrary(name, library));
		Reflect.setField(proxy, 'unloadLibrary', function(name:String):Void LimeAssets.unloadLibrary(name));
		Reflect.setField(proxy, 'removeLibrary', function(name:String, ?unload:Bool = true):Void
			LimeAssets.removeLibrary(name, unload));
		Reflect.setField(proxy, 'loadLibrary', function(id:String):Dynamic {
			if (unsafeLibraryName(id)) return Future.withError('[psych-assets] Lime asset libraries cannot escape the selected owner');
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
		var resolved = resolve(owner, id);
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

	static function required(owner:String, id:String):PsychOwnerAssetPathResult {
		var resolved = resolve(owner, id);
		if (resolved.blocked)
			throw '[psych-assets] Refused asset outside selected owner: ' + Std.string(id);
		if (resolved.unavailable)
			throw '[psych-assets] Asset is unavailable in selected owner: ' + Std.string(id);
		if (resolved.path == null)
			throw '[psych-assets] Asset is unavailable to selected owner: ' + Std.string(id);
		return resolved;
	}

	static function resolve(owner:String, id:String):PsychOwnerAssetPathResult {
		var ownerPath = PsychOwnerAssetPath.resolve(owner, id);
		if (ownerPath.blocked || ownerPath.unavailable || ownerPath.owned)
			return ownerPath;
		var clean = PsychOwnerAssetPath.cleanId(id);
		if (clean == null) return ownerPath;
		if (LimeAssets.exists(id)) return {path:id, owned:false, blocked:false, unavailable:false};
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

	static function cacheKey(owner:String, path:String):String return 'psych-owner:' + owner + ':' + path;
}
