package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** Owner-scoped character JSON and atlas lookup for Nightmare Vision imports. */
class NightmareVisionCharacterData {
	static final CHARACTER_DIRECTORIES:Array<String> = [
		'data/characters',
		'characters',
		'shared/characters'
	];

	/** Read an authored CharacterData object from the selected owner only. */
	public static function load(ownerRoot:String, characterId:String):Dynamic {
		var path = definitionPath(ownerRoot, characterId);
		if (path == null)
			return null;
		#if sys
		try {
			var definition:Dynamic = CoolUtil.parseJson(File.getContent(path));
			return definition != null && Reflect.isObject(definition) && !Std.isOfType(definition, Array)
				? definition : null;
		} catch (_:Dynamic) {
			return null;
		}
		#else
		return null;
		#end
	}

	/** Return the owner-local JSON path used for diagnostics and resolution. */
	public static function definitionPath(ownerRoot:String, characterId:String):Null<String> {
		var id = normalizeRelative(characterId == null ? '' : characterId.trim());
		if (id == '')
			return null;
		for (directory in CHARACTER_DIRECTORIES) {
			var relative = directory + '/' + id + '.json';
			var path = resolveOwnerFile(ownerRoot, relative);
			if (path != null)
				return path;
		}
		return null;
	}

	/**
		Resolve `definition.image` to a prefix accepted by Character.loadTextureAtlas
		or Character.loadSparrow. The returned path remains relative to the game
		working directory so FlxAnimateAssets and FNFAssets use the same owner path.
	*/
	public static function imageRoot(ownerRoot:String, definition:Dynamic):Null<String> {
		if (definition == null)
			return null;
		var image:Dynamic = Reflect.field(definition, 'image');
		if (!Std.isOfType(image, String))
			return null;
		var relativeImage = StringTools.trim(Std.string(image));
		if (relativeImage.startsWith('images/'))
			relativeImage = relativeImage.substr('images/'.length);
		var extension = Path.extension(relativeImage).toLowerCase();
		if (['png', 'xml', 'json'].indexOf(extension) >= 0)
			relativeImage = Path.withoutExtension(relativeImage);
		var imagePath = normalizeRelative(relativeImage);
		if (imagePath == '')
			return null;

		#if sys
		var prefix = normalizeOwnerPath(ownerRoot, 'images/' + imagePath);
		if (prefix != null && hasAnimateAtlas(prefix))
			return prefix;
		var sparrowPrefix = resolveSparrowPrefix(ownerRoot, 'images/' + imagePath);
		if (sparrowPrefix != null)
			return sparrowPrefix;
		var corePrefix = normalizeOwnerPath(ownerRoot, '__nmv_core/images/' + imagePath);
		if (corePrefix != null && hasAnimateAtlas(corePrefix))
			return corePrefix;
		var coreSparrow = resolveSparrowPrefix(ownerRoot, '__nmv_core/images/' + imagePath);
		if (coreSparrow != null)
			return coreSparrow;
		#end
		return null;
	}

	static function resolveOwnerFile(ownerRoot:String, relative:String):Null<String> {
		var ownerFile = resolveExactFile(ownerRoot, relative);
		if (ownerFile != null)
			return Path.normalize(Path.join([ownerRoot, relative]));
		var coreRelative = '__nmv_core/' + relative;
		return resolveExactFile(ownerRoot, coreRelative) == null ? null
			: Path.normalize(Path.join([ownerRoot, coreRelative]));
	}

	static function normalizeOwnerPath(ownerRoot:String, relative:String):Null<String> {
		var clean = normalizeRelative(relative);
		if (clean == '' || ownerRoot == null || StringTools.trim(ownerRoot) == '')
			return null;
		#if sys
		try {
			var root = Path.normalize(FileSystem.fullPath(ownerRoot));
			if (!FileSystem.isDirectory(root))
				return null;
			var ownerPath = resolveExactDirectory(root, clean);
			if (ownerPath != null)
				return Path.normalize(Path.join([ownerRoot, clean]));
			return null;
		} catch (_:Dynamic) {
			return null;
		}
		#else
		return null;
		#end
	}

	static function normalizeRelative(value:String):String {
		if (value == null || value == '' || value.startsWith('/') || value.indexOf('\\') >= 0)
			return '';
		var parts = value.split('/');
		for (part in parts)
			if (part == '' || part == '.' || part == '..' || part.indexOf(':') >= 0)
				return '';
		return parts.join('/');
	}

	#if sys
	static function resolveExactFile(ownerRoot:String, relative:String):Null<String> {
		var clean = normalizeRelative(relative);
		if (clean == '' || ownerRoot == null || StringTools.trim(ownerRoot) == '')
			return null;
		try {
			var root = Path.normalize(FileSystem.fullPath(ownerRoot));
			if (!FileSystem.isDirectory(root))
				return null;
			var current = root;
			var parts = clean.split('/');
			for (i in 0...parts.length) {
				current = Path.join([current, parts[i]]);
				if (!FileSystem.exists(current) || !withinRoot(root, current))
					return null;
				if (i < parts.length - 1 && !FileSystem.isDirectory(current))
					return null;
				if (i == parts.length - 1 && FileSystem.isDirectory(current))
					return null;
			}
			return current;
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function resolveExactDirectory(ownerRoot:String, relative:String):Null<String> {
		var clean = normalizeRelative(relative);
		if (clean == '' || ownerRoot == null || StringTools.trim(ownerRoot) == '')
			return null;
		try {
			var root = Path.normalize(FileSystem.fullPath(ownerRoot));
			if (!FileSystem.isDirectory(root))
				return null;
			var current = root;
			for (part in clean.split('/')) {
				current = Path.join([current, part]);
				if (!FileSystem.isDirectory(current) || !withinRoot(root, current))
					return null;
			}
			return current;
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function hasAnimateAtlas(prefix:String):Bool {
		if (!FileSystem.isDirectory(prefix) || !FileSystem.exists(prefix + '/Animation.json'))
			return false;
		try {
			for (file in FileSystem.readDirectory(prefix)) {
				if (!file.startsWith('spritemap') || !StringTools.endsWith(file.toLowerCase(), '.png'))
					continue;
				var stem = Path.withoutExtension(file);
				if (FileSystem.exists(prefix + '/' + stem + '.json'))
					return true;
			}
		} catch (_:Dynamic) {}
		return false;
	}

	static function resolveSparrowPrefix(ownerRoot:String, relativePrefix:String):Null<String> {
		if (resolveExactFile(ownerRoot, relativePrefix + '.png') == null
			|| resolveExactFile(ownerRoot, relativePrefix + '.xml') == null)
			return null;
		return Path.normalize(Path.join([ownerRoot, relativePrefix]));
	}

	static function withinRoot(root:String, path:String):Bool {
		try {
			var base = Path.normalize(FileSystem.fullPath(root));
			var candidate = Path.normalize(FileSystem.fullPath(path));
			var prefix = base.endsWith('/') ? base : base + '/';
			return candidate == base || candidate.startsWith(prefix);
		} catch (_:Dynamic) {
			return false;
		}
	}
	#end
}
