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
		Resolve comma-separated `definition.image` atlas paths to prefixes accepted
		by Character.loadTextureAtlas or Character.loadSparrow. The returned paths
		remain relative to the game working directory and stay in this owner/core.
	*/
	public static function imageRoot(ownerRoot:String, definition:Dynamic):Null<String> {
		if (definition == null)
			return null;
		var image:Dynamic = Reflect.field(definition, 'image');
		if (!Std.isOfType(image, String))
			return null;
		var prefixes:Array<String> = [];
		for (authoredPart in Std.string(image).split(',')) {
			// Source character JSON can contain Windows separators even when the
			// owner is loaded on another platform. Canonicalize this authored path
			// before extension and containment checks; normalizeRelative still
			// rejects traversal, absolute paths, and drive-qualified values.
			var relativeImage = StringTools.replace(StringTools.trim(authoredPart), '\\', '/');
			if (relativeImage.startsWith('images/'))
				relativeImage = relativeImage.substr('images/'.length);
			var extension = Path.extension(relativeImage).toLowerCase();
			if (['png', 'xml', 'json'].indexOf(extension) >= 0)
				relativeImage = Path.withoutExtension(relativeImage);
			var imagePath = normalizeRelative(relativeImage);
			if (imagePath == '')
				return null;

			#if sys
			var prefix = resolveImagePrefix(ownerRoot, imagePath);
			if (prefix == null)
				return null;
			prefixes.push(prefix);
			#end
		}
		return prefixes.length == 0 ? null : prefixes.join(',');
	}

	#if sys
	static function resolveImagePrefix(ownerRoot:String, imagePath:String):Null<String> {
		var ownerRelative = 'images/' + imagePath;
		var prefix = normalizeOwnerPath(ownerRoot, ownerRelative);
		if (prefix != null && hasAnimateAtlas(prefix))
			return prefix;
		var sparrowPrefix = resolveSparrowPrefix(ownerRoot, ownerRelative);
		if (sparrowPrefix != null)
			return sparrowPrefix;
		var coreRelative = '__nmv_core/' + ownerRelative;
		var corePrefix = normalizeOwnerPath(ownerRoot, coreRelative);
		if (corePrefix != null && hasAnimateAtlas(corePrefix))
			return corePrefix;
		return resolveSparrowPrefix(ownerRoot, coreRelative);
	}
	#end

	/** Owner file first, then the package's core dependency. The path keeps the
		owner root as given and the file's on-disk spelling. */
	static function resolveOwnerFile(ownerRoot:String, relative:String):Null<String> {
		#if sys
		var ownerFile = SourceOwnerFiles.resolveFile(ownerRoot, relative);
		if (ownerFile != null)
			return ownerFile;
		return SourceOwnerFiles.resolveFile(ownerRoot, '__nmv_core/' + relative);
		#else
		return null;
		#end
	}

	static function normalizeOwnerPath(ownerRoot:String, relative:String):Null<String> {
		#if sys
		return SourceOwnerFiles.resolveDirectory(ownerRoot, relative);
		#else
		return null;
		#end
	}

	static function normalizeRelative(value:String):String {
		var clean = SourceOwnerFiles.cleanRelative(value);
		return clean == null ? '' : clean;
	}

	#if sys

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
		var image = SourceOwnerFiles.resolveFile(ownerRoot, relativePrefix + '.png');
		if (image == null || SourceOwnerFiles.resolveFile(ownerRoot, relativePrefix + '.xml') == null)
			return null;
		// The loader appends the extensions to this prefix, so it takes the
		// image's on-disk spelling.
		return Path.withoutExtension(image);
	}
	#end
}
