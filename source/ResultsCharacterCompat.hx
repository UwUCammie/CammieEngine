package;

import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** Character selection for the engine's default results presentation only.
 * Gameplay character identities and mod-owned results scripts remain untouched. */
class ResultsCharacterCompat {
	var families:Map<String, String> = new Map();

	public function new(owner:String) {
		#if sys
		// Standard results animation families. Unknown gameplay characters never
		// reach a provider's random-character fallback.
		for (family in ['bf', 'pico'])
			if (hasAnimationTree(Path.join([owner, 'images', 'results-' + family]), owner)) {
				families.set(family, family);
				if (family == 'bf') families.set('boyfriend', family);
			}
		// Other providers may declare exact character aliases and all animation
		// dependencies in their existing pack.json; imports already preserve it.
		try {
			var pack:Dynamic = haxe.Json.parse(File.getContent(Path.join([owner, 'pack.json'])));
			var definitions:Dynamic = Reflect.field(pack, 'resultsCharacterFamilies');
			if (definitions != null && !Std.isOfType(definitions, Array))
				for (family in Reflect.fields(definitions)) {
					if (!safeToken(family)) continue;
					var definition = Reflect.field(definitions, family);
					var aliases:Dynamic = Reflect.field(definition, 'characterIds');
					var assets:Dynamic = Reflect.field(definition, 'requiredAssets');
					if (!Std.isOfType(aliases, Array) || !Std.isOfType(assets, Array)) continue;
					var required:Array<Dynamic> = cast assets;
					var valid = required.length > 0;
					for (asset in required) {
						if (!Std.isOfType(asset, String) || !safeRelative(asset)) { valid = false; break; }
						var path = Path.join([owner, cast asset]);
						if (!within(path, owner) || !FileSystem.exists(path) || FileSystem.isDirectory(path)) {
							valid = false; break;
						}
					}
					if (!valid) continue;
					for (alias in (cast aliases:Array<Dynamic>))
						if (Std.isOfType(alias, String) && safeToken(alias))
							families.set(Std.string(alias).toLowerCase(), family.toLowerCase());
				}
		} catch (_:Dynamic) {}
		#end
	}

	public function resolve(requested:String):String {
		if (requested == null) return 'bf';
		var id = requested.trim().toLowerCase();
		if (families.exists(id)) return families.get(id);
		// Standard engine character variants (bf-car, pico-speaker, etc.).
		// Arbitrary names merely containing these letters are not identities.
		for (family in ['bf', 'boyfriend', 'pico'])
			if (families.exists(family) && (id.startsWith(family + '-') || id.startsWith(family + '_')))
				return families.get(family);
		return 'bf';
	}

	static function safeToken(value:String):Bool {
		return value != null && ~/^[A-Za-z0-9_-]+$/.match(value);
	}

	static function safeRelative(value:String):Bool {
		if (value == null || value == '' || Path.isAbsolute(value) || value.indexOf(':') >= 0
			|| value.indexOf('\\') >= 0 || value.indexOf(String.fromCharCode(0)) >= 0) return false;
		for (part in value.split('/')) if (part == '' || part == '.' || part == '..') return false;
		return true;
	}

	#if sys
	static function within(path:String, owner:String):Bool {
		try return StringTools.replace(FileSystem.fullPath(path), '\\', '/')
			.startsWith(StringTools.replace(FileSystem.fullPath(owner), '\\', '/') + '/')
		catch (_:Dynamic) return false;
	}

	static function hasAnimationTree(root:String, owner:String):Bool {
		if (!FileSystem.exists(root) || !FileSystem.isDirectory(root) || !within(root, owner)) return false;
		var pending = [root];
		var seen:Map<String, Bool> = new Map();
		while (pending.length > 0) {
			var directory = pending.pop();
			var canonical = FileSystem.fullPath(directory);
			if (seen.exists(canonical) || !within(directory, owner)) continue;
			seen.set(canonical, true);
			for (entry in FileSystem.readDirectory(directory)) {
				var path = Path.join([directory, entry]);
				if (!within(path, owner)) continue;
				if (FileSystem.isDirectory(path)) pending.push(path);
				else if (entry.endsWith('.png') && FileSystem.exists(Path.withExtension(path, 'xml'))
					&& within(Path.withExtension(path, 'xml'), owner)) return true;
				else if (entry == 'Animation.json' && FileSystem.exists(Path.join([directory, 'spritemap1.png']))
					&& FileSystem.exists(Path.join([directory, 'spritemap1.json']))
					&& within(Path.join([directory, 'spritemap1.png']), owner)
					&& within(Path.join([directory, 'spritemap1.json']), owner)) return true;
			}
		}
		return false;
	}
	#end
}
