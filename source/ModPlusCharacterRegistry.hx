package;

import haxe.io.Path;
import haxe.io.Bytes;
import sys.FileSystem;
import sys.io.File;

/** Register complete loose Modding Plus characters from partial packages.
 * An existing registry entry always wins. No aliases or animation data are
 * inferred: the package must supply an exact-name script and Sparrow atlas. */
class ModPlusCharacterRegistry {
	/** A merge may leave a pre-existing global character owned by another
	 * package. Claim it only when each supplied file is byte-identical. Read
	 * fixed chunks so a large atlas never enters the Haxe heap as one blob. */
	static function sameFileBytes(source:String, destination:String):Bool {
		var size = FileSystem.stat(source).size;
		if (size != FileSystem.stat(destination).size) return false;
		var first = File.read(source, true);
		var second = File.read(destination, true);
		var firstChunk = Bytes.alloc(65536);
		var secondChunk = Bytes.alloc(65536);
		var same = true;
		try {
			var remaining = size;
			while (remaining > 0 && same) {
				var length = Std.int(Math.min(remaining, 65536));
				first.readFullBytes(firstChunk, 0, length);
				second.readFullBytes(secondChunk, 0, length);
				for (index in 0...length)
					if (firstChunk.get(index) != secondChunk.get(index)) {
						same = false;
						break;
					}
				remaining -= length;
			}
		} catch (error:Dynamic) {
			first.close();
			second.close();
			throw error;
		}
		first.close();
		second.close();
		return same;
	}

	public static function repair(contentRoot:String, destinationRoot:String):Int {
		var source = Path.join([contentRoot, 'images', 'custom_chars']);
		if (!FileSystem.isDirectory(source)) return 0;
		var destination = Path.join([destinationRoot, 'images', 'custom_chars']);
		if (!FileSystem.isDirectory(destination)) return 0;
		var registryPath = Path.join([destination, 'custom_chars.jsonc']);
		if (!FileSystem.exists(registryPath) && FileSystem.exists(Path.join([destination, 'custom_chars.json'])))
			registryPath = Path.join([destination, 'custom_chars.json']);
		var registry:Dynamic = FileSystem.exists(registryPath)
			? CoolUtil.parseJson(File.getContent(registryPath)) : {};
		if (registry == null || Std.isOfType(registry, Array))
			throw 'Invalid Modding Plus character registry: ' + registryPath;
		var names = FileSystem.readDirectory(source);
		names.sort(Reflect.compare);
		var count = 0;
		for (name in names) {
			if (!FileSystem.isDirectory(Path.join([source, name])) || name == '.' || name == '..') continue;
			var registered = false;
			for (key in Reflect.fields(registry))
				if (key.toLowerCase() == name.toLowerCase()) registered = true;
			if (registered) continue;
			var complete = true;
			for (relative in [name + '.hscript', name + '/char.png', name + '/char.xml']) {
				for (root in [source, destination]) {
					var path = Path.join([root, relative]);
					if (!FileSystem.exists(path) || FileSystem.isDirectory(path) || FileSystem.stat(path).size == 0)
						complete = false;
				}
				if (complete && !sameFileBytes(Path.join([source, relative]), Path.join([destination, relative])))
					complete = false;
			}
			if (!complete) continue;
			Reflect.setField(registry, name, {like:name, icons:[0, 1], colors:['#FFFFFF']});
			trace('[modplus-loose-character] Registered supplied script/atlas ' + name
				+ ' with default icon/color metadata; no registry entry was supplied.');
			count++;
		}
		if (count > 0) File.saveContent(registryPath, CoolUtil.stringifyJson(registry));
		return count;
	}
}
