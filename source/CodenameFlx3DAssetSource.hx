package;

import away3d.loaders.misc.AssetLoaderContext;
import haxe.io.Bytes;
import haxe.io.Path;
import openfl.utils.ByteArray;

using StringTools;

/** Owner-scoped resolver for textual OBJ material-library dependencies. The
 * stage-provided BitmapData remains the final mesh material; mapped sidecars
 * are still read only from the same selected owner as the model. */
class CodenameFlx3DAssetSource {
	public static function mapObjDependencies(paths:CodenamePaths, context:AssetLoaderContext,
		assetPath:String, modelData:Bytes):Void {
		if (paths == null || context == null || modelData == null)
			throw '[codename-3d] Incomplete owner model context';
		var modelPath = paths.getPath(assetPath);
		var modelDirectory = Path.directory(modelPath);
		for (line in modelData.toString().split('\n')) {
			var words = tokens(line);
			if (words.length < 2 || words[0] != 'mtllib') continue;
			// Away3D's OBJParser consumes the first MTL filename on an mtllib
			// directive, so use that same dependency key here.
			var material = loadOwnerResource(paths, modelDirectory, words[1]);
			if (material.path == null)
				trace('[codename-3d-mtl-missing] ' + words[1] + ' referenced by ' + assetPath
					+ ' is missing in the selected owner; continuing without MTL data');
			mapResource(context, words[1], material.bytes);
			if (material.path != null)
				mapMtlTextures(paths, context, Path.directory(material.path), material.bytes);
		}
	}

	static function mapMtlTextures(paths:CodenamePaths, context:AssetLoaderContext,
		materialDirectory:String, materialData:Bytes):Void {
		for (line in materialData.toString().split('\n')) {
			var words = tokens(line);
			if (words.length < 2 || words[0] != 'map_Kd') continue;
			var index = textureFilenameIndex(words);
			if (index >= words.length) continue;
			var textureName = words.slice(index).join(' ');
			var texture = loadOwnerResource(paths, materialDirectory, textureName);
			if (texture.path == null)
				trace('[codename-3d-texture-missing] ' + textureName
					+ ' is missing in the selected owner; continuing without MTL texture data');
			mapResource(context, textureName, texture.bytes);
		}
	}

	/** Match the option skipping used by Away3D's OBJParser.parseMapKdString. */
	static function textureFilenameIndex(words:Array<String>):Int {
		var index = 1;
		while (index < words.length) {
			switch (words[index]) {
				case '-blendu', '-blendv', '-cc', '-clamp', '-texres': index += 2;
				case '-mm': index += 3;
				case '-o', '-s', '-t': index += 4;
				default: return index;
			}
		}
		return index;
	}

	static function tokens(line:String):Array<String> {
		return ~/[	 ]+/g.split(StringTools.trim(line));
	}

	static function loadOwnerResource(paths:CodenamePaths, directory:String,
		name:String):{path:Null<String>, bytes:Bytes} {
		var normalized = normalizeName(name);
		var candidate = Path.join([directory, normalized]);
		var exists = FNFAssets.exists(candidate);
		#if sys
		if (exists && sys.FileSystem.isDirectory(candidate)) exists = false;
		#end
		if (!exists) return {path:null, bytes:Bytes.alloc(0)};
		var resolved = paths.getPath(candidate);
		return {path:resolved, bytes:FNFAssets.getBytes(resolved)};
	}

	static function mapResource(context:AssetLoaderContext, originalName:String,
		data:Dynamic):Void {
		var normalized = normalizeName(originalName);
		// Away3D's OBJ/MTL/image parsers expect OpenFL ByteArrayData. The
		// owner facade returns haxe.io.Bytes, which parses as empty data unless
		// converted before registering the dependency.
		if (Std.isOfType(data, Bytes))
			data = ByteArray.fromBytes(cast data);
		// The OBJ parser strips a leading ./ for MTL paths, while MTL texture
		// paths can retain it. Mapping both spellings keeps the key owner-local.
		context.mapUrlToData(originalName, data);
		context.mapUrlToData(normalized, data);
	}

	static function normalizeName(name:String):String {
		if (name == null) throw '[codename-3d] Missing model dependency name';
		var clean = name.replace('\\', '/');
		if (clean.startsWith('./')) clean = clean.substr(2);
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0
			|| clean.indexOf('?') >= 0 || clean.indexOf('#') >= 0)
			throw '[codename-3d] Invalid model dependency name: ' + name;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..')
				throw '[codename-3d] Invalid model dependency name: ' + name;
		return clean;
	}
}
