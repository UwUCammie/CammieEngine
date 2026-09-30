package;

import flixel.graphics.frames.FlxAtlasFrames;
import openfl.display.BitmapData;
import haxe.io.Path;

using StringTools;

/**
	Manifest-scoped Paths/Assets proxies used by standalone imported states.
	Only the selected destination root is searched before native assets; another
	compatibility root can never satisfy a relative lookup by accident.
*/
class HxcStateAssetScope {
	static var fallbackDiagnostics:Map<String, Bool> = new Map<String, Bool>();

	/**
		Resolve one manifest-owned Sparrow atlas for a native adapter.  Both the
		PNG and XML must be present in the selected namespace; a partial atlas is
		not passed to Flixel and the caller receives its explicit fallback.
	*/
	public static function sparrowAtlas(root:String, key:String, ?fallback:FlxAtlasFrames,
		?context:String):FlxAtlasFrames {
		var clean = atlasKey(key);
		var image = scopedAssetPath(root, 'images/' + clean + '.png');
		var metadata = scopedAssetPath(root, 'images/' + clean + '.xml');
		var label = context == null || StringTools.trim(context) == ''
			? 'HXC Sparrow atlas ' + clean : context;
		// HXC CharacterInfo scripts commonly keep the image key in the donor's
		// shared `images/characters` tree while the importer namespaces only the
		// script itself.  Those static files are deliberately copied into the
		// native asset tree, so allow the normal engine resolver as a second,
		// engine-owned source after the manifest root.  The selected manifest still
		// wins whenever it contains a complete pair, and no donor path is exposed.
		if (image == null || metadata == null) {
			var nativeImage = image == null ? nativeAssetPath('images/' + clean + '.png') : image;
			var nativeMetadata = metadata == null ? nativeAssetPath('images/' + clean + '.xml') : metadata;
			if (nativeImage != null && nativeMetadata != null) {
				image = nativeImage;
				metadata = nativeMetadata;
			}
		}
		if (image == null || metadata == null) {
			diagnoseFallback(root, clean, label, image != null, metadata != null);
			return fallback;
		}
		try {
			return FlxAtlasFrames.fromSparrow(FNFAssets.getBitmapData(image), FNFAssets.getText(metadata));
		} catch (error:Dynamic) {
			diagnoseFallback(root, clean, label, true, true, Std.string(error));
			return fallback;
		}
	}

	/**
		Resolve an HXC event atlas only from its manifest-selected destination
		root. Event-owned visuals never fall through to another import or the native
		asset tree, since a same-named atlas there could render unrelated content.
	*/
	public static function eventAtlas(root:String, key:String, atlasType:String,
		?context:String):FlxAtlasFrames {
		var clean = HxcEventSpriteDescriptor.safeAtlasKey(key);
		var packer = atlasType == 'packer';
		if (clean == '' || (atlasType != 'sparrow' && atlasType != 'packer'))
			return null;
		var image = scopedAssetPath(root, 'images/' + clean + '.png');
		var metadata = scopedAssetPath(root, 'images/' + clean + (packer ? '.txt' : '.xml'));
		var label = context == null || StringTools.trim(context) == ''
			? 'HXC event atlas ' + clean : context;
		if (image == null || metadata == null) {
			diagnoseFallback(root, clean, label, image != null, metadata != null);
			return null;
		}
		try {
			var pixels = FNFAssets.getBitmapData(image);
			var atlasText = FNFAssets.getText(metadata);
			return packer
				? FlxAtlasFrames.fromSpriteSheetPacker(pixels, atlasText)
				: FlxAtlasFrames.fromSparrow(pixels, atlasText);
		} catch (error:Dynamic) {
			diagnoseFallback(root, clean, label, true, true, Std.string(error));
			return null;
		}
	}

	/** Resolve a static HXC media key through the native importer-owned asset
	 * layer.  Kept separate from scopedAssetPath so all manifest-relative input
	 * remains traversal-safe and the fallback is explicit in diagnostics. */
	static function nativeAssetPath(relative:String):String {
		if (relative == null || StringTools.trim(relative) == '')
			return null;
		var clean = StringTools.replace(StringTools.trim(relative), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		while (clean.startsWith('/'))
			clean = clean.substr(1);
		if (clean == '' || clean.indexOf('..') >= 0 || clean.indexOf(':') >= 0)
			return null;
		var candidate = Path.normalize('assets/' + clean);
		return FNFAssets.exists(candidate) ? candidate : null;
	}

	/** Return the destination path for one manifest-owned relative asset. */
	public static function scopedAssetPath(root:String, relative:String):String {
		if (root == null || StringTools.trim(root) == '' || relative == null)
			return null;
		var cleanRoot = Path.normalize(StringTools.replace(StringTools.trim(root), '\\', '/'));
		if (!cleanRoot.startsWith(CompatScriptManifest.ROOT_PREFIX + '/'))
			return null;
		var clean = StringTools.replace(StringTools.trim(relative), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		while (clean.startsWith('/'))
			clean = clean.substr(1);
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean == '' || clean.indexOf('..') >= 0 || clean.indexOf(':') >= 0)
			return null;
		var candidate = Path.normalize(Path.join([cleanRoot, clean]));
		if (candidate != cleanRoot && !candidate.startsWith(cleanRoot + '/'))
			return null;
		return FNFAssets.exists(candidate) ? candidate : null;
	}

	static function atlasKey(value:String):String {
		var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
		while (clean.startsWith('./'))
			clean = clean.substr(2);
		while (clean.startsWith('/'))
			clean = clean.substr(1);
		if (clean.toLowerCase().startsWith('assets/'))
			clean = clean.substr('assets/'.length);
		if (clean.toLowerCase().startsWith('images/'))
			clean = clean.substr('images/'.length);
		if (clean.toLowerCase().endsWith('.png'))
			clean = clean.substr(0, clean.length - 4);
		if (clean.toLowerCase().endsWith('.xml'))
			clean = clean.substr(0, clean.length - 4);
		return clean;
	}

	static function diagnoseFallback(root:String, key:String, context:String,
		imageFound:Bool, metadataFound:Bool, ?detail:String):Void {
		var identity = (root == null ? '' : root) + ':' + key;
		if (fallbackDiagnostics.exists(identity))
			return;
		fallbackDiagnostics.set(identity, true);
		var message = '[hxc-asset-fallback] ' + context + ' has no complete scoped atlas in '
			+ (root == null ? '<no manifest root>' : root) + ' ('
			+ (imageFound ? 'png' : 'missing png') + ', '
			+ (metadataFound ? 'xml' : 'missing xml') + ')';
		if (detail != null && StringTools.trim(detail) != '')
			message += ': ' + detail;
		trace(message);
	}

	public static function paths(root:String):Dynamic {
		var proxy:Dynamic = {};
		var rootKey = Path.normalize(StringTools.replace(root == null ? '' : root, '\\', '/')).toLowerCase();
		var blocked = function(value:String):Bool {
			var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
			while (clean.startsWith('./'))
				clean = clean.substr(2);
			var lower = clean.toLowerCase();
			if (!lower.startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/'))
				return false;
			return rootKey == '' || (lower != rootKey && !lower.startsWith(rootKey + '/'));
		};
		var cleanKey = function(value:String):String {
			var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
			while (clean.startsWith('./'))
				clean = clean.substr(2);
			while (clean.startsWith('/'))
				clean = clean.substr(1);
			if (clean.toLowerCase().startsWith('assets/'))
				clean = clean.substr('assets/'.length);
			return clean;
		};
		var scopedFile = function(relative:String):String {
			if (blocked(relative))
				return null;
			var clean = cleanKey(relative);
			var raw = StringTools.replace(StringTools.trim(relative == null ? '' : relative), '\\', '/');
			if (raw.toLowerCase().startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/'))
				return FNFAssets.exists(Path.normalize(raw)) ? Path.normalize(raw) : null;
			if (clean == '' || clean.indexOf('..') >= 0)
				return null;
			if (root == null || root == '')
				return null;
			var candidate = Path.normalize(Path.join([root, clean]));
			return FNFAssets.exists(candidate) ? candidate : null;
		};
		var scopedImage = function(key:String):String {
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('images/'))
				clean = clean.substr('images/'.length);
			if (clean.toLowerCase().endsWith('.png'))
				clean = clean.substr(0, clean.length - 4);
			return scopedFile('images/' + clean + '.png');
		};
		var nativeImage = function(key:String, library:String):Dynamic {
			var candidates = VSliceSharedAssetPaths.imageCandidates(key);
			for (candidate in candidates) {
				var path = Paths.image(candidate, library);
				if (path != null && FNFAssets.exists(path))
					return path;
			}
			if (candidates.length > 0)
				throw '[hxc-vslice-image-missing] V-Slice countdown image "' + key
					+ '" has no selected-owner resource or native fallback (' + candidates.join(', ') + ').';
			return Paths.image(key, library);
		};
		var scopedAtlas = function(key:String, packer:Bool):Dynamic {
			if (blocked(key))
				return null;
			var image = scopedImage(key);
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('images/'))
				clean = clean.substr('images/'.length);
			if (clean.toLowerCase().endsWith('.png'))
				clean = clean.substr(0, clean.length - 4);
			var metadata = scopedFile('images/' + clean + (packer ? '.txt' : '.xml'));
			if (image == null)
				image = nativeImage(key, null);
			if (metadata == null)
				metadata = packer ? Paths.file('images/' + clean + '.txt') : Paths.file('images/' + clean + '.xml');
			var imageValue:Dynamic = image;
			if (image != null && FNFAssets.exists(image))
				imageValue = FNFAssets.getBitmapData(image);
			var metadataValue:Dynamic = metadata;
			if (metadata != null && FNFAssets.exists(metadata))
				metadataValue = FNFAssets.getText(metadata);
			return packer
				? FlxAtlasFrames.fromSpriteSheetPacker(imageValue, metadataValue)
				: FlxAtlasFrames.fromSparrow(imageValue, metadataValue);
		};
		Reflect.setField(proxy, 'image', function(key:String, ?library:String):Dynamic {
			if (blocked(key))
				return null;
			var scoped = scopedImage(key);
			return scoped == null ? nativeImage(key, library) : FNFAssets.getBitmapData(scoped);
		});
		Reflect.setField(proxy, 'getSparrowAtlas', function(key:String, ?library:String):Dynamic return scopedAtlas(key, false));
		Reflect.setField(proxy, 'getPackerAtlas', function(key:String, ?library:String):Dynamic return scopedAtlas(key, true));
		Reflect.setField(proxy, 'file', function(file:String, ?type:Dynamic, ?library:String):String {
			if (blocked(file))
				return null;
			var scoped = scopedFile(file);
			return scoped == null ? Paths.file(file) : scoped;
		});
		Reflect.setField(proxy, 'xml', function(key:String, ?library:String):String {
			if (blocked(key))
				return null;
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('data/'))
				clean = clean.substr('data/'.length);
			var scoped = scopedFile('data/' + clean + '.xml');
			return scoped == null ? Paths.xml(key, library) : scoped;
		});
		Reflect.setField(proxy, 'txt', function(key:String, ?library:String):String {
			if (blocked(key))
				return null;
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('data/'))
				clean = clean.substr('data/'.length);
			var scoped = scopedFile('data/' + clean + '.txt');
			return scoped == null ? Paths.txt(key, library) : scoped;
		});
		Reflect.setField(proxy, 'json', function(key:String, ?library:String):String {
			if (blocked(key))
				return null;
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('data/'))
				clean = clean.substr('data/'.length);
			var scoped = scopedFile('data/' + clean + '.json');
			return scoped == null ? Paths.json(key, library) : scoped;
		});
		Reflect.setField(proxy, 'frag', function(key:String, ?library:String):String {
			if (blocked(key))
				return null;
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('shaders/'))
				clean = clean.substr('shaders/'.length);
			var scoped = scopedFile('shaders/' + (clean.toLowerCase().endsWith('.frag') ? clean : clean + '.frag'));
			if (scoped != null)
				return scoped;
			return ShaderPaths.resolve(key, root == null || root == '' ? null : [root]);
		});
		Reflect.setField(proxy, 'sound', function(key:String, ?library:String):String {
			if (blocked(key))
				return null;
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('sounds/'))
				clean = clean.substr('sounds/'.length);
			var scoped = scopedFile('sounds/' + (clean.toLowerCase().endsWith('.ogg') ? clean : clean + '.ogg'));
			return scoped == null ? Paths.sound(key, library) : scoped;
		});
		Reflect.setField(proxy, 'music', function(key:String, ?library:String):String {
			if (blocked(key))
				return null;
			var clean = cleanKey(key);
			if (clean.toLowerCase().startsWith('music/'))
				clean = clean.substr('music/'.length);
			var scoped = scopedFile('music/' + (clean.toLowerCase().endsWith('.ogg') ? clean : clean + '.ogg'));
			return scoped == null ? Paths.music(key, library) : scoped;
		});
		Reflect.setField(proxy, 'font', function(key:String):String {
			if (blocked(key))
				return null;
			var scoped = scopedFile('fonts/' + cleanKey(key));
			return scoped == null ? Paths.font(key) : scoped;
		});
		return proxy;
	}

	public static function assets(root:String):Dynamic {
		var proxy:Dynamic = {};
		var rootKey = Path.normalize(StringTools.replace(root == null ? '' : root, '\\', '/')).toLowerCase();
		var blocked = function(value:String):Bool {
			var clean = StringTools.replace(StringTools.trim(value == null ? '' : value), '\\', '/');
			while (clean.startsWith('./'))
				clean = clean.substr(2);
			var lower = clean.toLowerCase();
			if (!lower.startsWith(CompatScriptManifest.ROOT_PREFIX.toLowerCase() + '/'))
				return false;
			return rootKey == '' || (lower != rootKey && !lower.startsWith(rootKey + '/'));
		};
		var scoped = function(id:String):String {
			if (blocked(id))
				return null;
			if (id == null || id == '')
				return null;
			var clean = StringTools.replace(StringTools.trim(id), '\\', '/');
			while (clean.startsWith('./'))
				clean = clean.substr(2);
			if (clean.startsWith('/') || clean.indexOf('..') >= 0)
				return null;
			if (clean.toLowerCase().startsWith('assets/'))
				clean = clean.substr('assets/'.length);
			if (root == null || root == '')
				return null;
			var candidate = Path.normalize(Path.join([root, clean]));
			return FNFAssets.exists(candidate) ? candidate : null;
		};
		Reflect.setField(proxy, 'getText', function(id:String):String {
			if (blocked(id))
				return null;
			var path = scoped(id);
			return path == null ? FNFAssets.getText(id) : FNFAssets.getText(path);
		});
		Reflect.setField(proxy, 'getBitmapData', function(id:Dynamic, ?useCache:Bool = true):Dynamic {
			if (id != null && Std.isOfType(id, BitmapData))
				return id;
			var key = Std.string(id);
			if (blocked(key))
				return null;
			var path = scoped(key);
			return FNFAssets.getBitmapData(path == null ? key : path, useCache);
		});
		Reflect.setField(proxy, 'loadBitmapData', function(id:String, ?useCache:Bool = true):Dynamic {
			if (blocked(id))
				return null;
			var path = scoped(id);
			return FNFAssets.loadBitmapData(path == null ? id : path, useCache);
		});
		Reflect.setField(proxy, 'getSound', function(id:String, ?useCache:Bool = true):Dynamic {
			if (blocked(id))
				return null;
			var path = scoped(id);
			return FNFAssets.getSound(path == null ? id : path, useCache);
		});
		Reflect.setField(proxy, 'getBytes', function(id:String):Dynamic {
			if (blocked(id))
				return null;
			var path = scoped(id);
			return FNFAssets.getBytes(path == null ? id : path);
		});
		Reflect.setField(proxy, 'exists', function(id:Dynamic, ?type:Dynamic):Bool {
			if (id == null)
				return false;
			if (Std.isOfType(id, BitmapData))
				return true;
			var key = Std.string(id);
			if (blocked(key))
				return false;
			var path = scoped(key);
			return path == null ? FNFAssets.exists(key) : FNFAssets.exists(path);
		});
		return proxy;
	}
}
