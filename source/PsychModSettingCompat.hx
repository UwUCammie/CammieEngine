package;

import haxe.Json;
import haxe.io.Path;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

using StringTools;

/** Read-only Psych getModSetting bridge for the calling imported pack. */
class PsychModSettingCompat {
	/**
		Create one provider per script interpreter. The caller's script must live
		inside the selected Psych owner; package names are checked against that
		owner's pack.json and never used to search other imports.
	*/
	public static function create(scriptOrigin:String, selectedRoot:String,
		?diagnose:String->Void):Dynamic {
		var owner = ownerForScript(scriptOrigin, selectedRoot);
		var packageChecked = false;
		var ownerPackage:String = null;
		var settingsChecked = false;
		var settings:Map<String, Dynamic> = null;
		return function(name:Dynamic, ?requestedPackage:Dynamic):Dynamic {
			if (owner == null || name == null) return null;
			var settingName = StringTools.trim(Std.string(name));
			if (settingName == '') return null;
			if (requestedPackage != null && StringTools.trim(Std.string(requestedPackage)) != '') {
				if (!packageChecked) {
					packageChecked = true;
					ownerPackage = readPackName(owner);
				}
				// Older imported roots do not carry pack.json. In that case the
				// interpreter's validated owner remains authoritative; the argument
				// is never used to discover or read a second owner.
				if (ownerPackage != null && ownerPackage != StringTools.trim(Std.string(requestedPackage)))
					return null;
			}
			if (!settingsChecked) {
				settingsChecked = true;
				settings = readSettings(owner, diagnose);
			}
			return settings == null || !settings.exists(settingName) ? null : settings.get(settingName);
		};
	}

	/** Exposed for focused owner-scope tests and other generic bridges. */
	public static function ownerForScript(scriptOrigin:String, selectedRoot:String):Null<String> {
		#if sys
		var root = safeRelativePath(selectedRoot);
		if (root == null || scriptOrigin == null || !root.startsWith('assets/imported_mods/'))
			return null;
		var origin = StringTools.replace(StringTools.trim(scriptOrigin), '\\', '/');
		if (origin == '' || origin.indexOf(String.fromCharCode(0)) >= 0)
			return null;
		// PsychScriptDiscovery returns absolute paths for actual installed
		// scripts. Haxe represents Windows absolute paths as `C:/...` after
		// separator normalization, so don't mistake a drive path for an unsafe
		// relative path merely because it doesn't begin with `/`.
		// Relative callers still receive the stricter traversal check.
		if (!isAbsoluteScriptOrigin(origin) && safeRelativePath(origin) == null)
			return null;
		if (!FileSystem.isDirectory(root) || !FileSystem.exists(origin)) return null;
		try {
			var base = Path.normalize(FileSystem.fullPath(root));
			var candidate = Path.normalize(FileSystem.fullPath(origin));
			return candidate.startsWith(base + '/') ? root : null;
		} catch (_:Dynamic) {
			return null;
		}
		#else
		return null;
		#end
	}

	static function isAbsoluteScriptOrigin(value:String):Bool {
		if (value == null)
			return false;
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (clean.startsWith('/'))
			return true;
		if (clean.length < 3 || clean.charAt(1) != ':' || clean.charAt(2) != '/')
			return false;
		var drive = clean.charCodeAt(0);
		return (drive >= 'A'.code && drive <= 'Z'.code) || (drive >= 'a'.code && drive <= 'z'.code);
	}

	/** Resolve the actual imported owner of a globally loaded script. This is
		separate from a chart's selected owner because one song can load another
		Psych pack's globally enabled script. */
	public static function ownerForScriptRoots(scriptOrigin:String, candidateRoots:Array<String>):Null<String> {
		if (candidateRoots == null) return null;
		for (candidate in candidateRoots) {
			var owner = ownerForScript(scriptOrigin, candidate);
			if (owner != null) return owner;
		}
		return null;
	}

	static function safeRelativePath(value:String):Null<String> {
		if (value == null) return null;
		var clean = StringTools.replace(StringTools.trim(value), '\\', '/');
		if (clean == '' || clean.startsWith('/') || clean.indexOf(':') >= 0
			|| clean.indexOf(String.fromCharCode(0)) >= 0)
			return null;
		for (part in clean.split('/'))
			if (part == '' || part == '.' || part == '..') return null;
		return Path.normalize(clean);
	}

	#if sys
	static function ownedFile(owner:String, relative:String):Null<String> {
		var safeRelative = safeRelativePath(relative);
		if (owner == null || safeRelative == null) return null;
		var candidate = Path.normalize(Path.join([owner, safeRelative]));
		if (!candidate.startsWith(owner + '/') || !FileSystem.exists(candidate)) return null;
		try {
			var base = Path.normalize(FileSystem.fullPath(owner));
			var full = Path.normalize(FileSystem.fullPath(candidate));
			return full.startsWith(base + '/') ? candidate : null;
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function readPackName(owner:String):Null<String> {
		var path = ownedFile(owner, 'pack.json');
		if (path == null) return null;
		try {
			var value:Dynamic = Json.parse(File.getContent(path));
			var name:Dynamic = value == null ? null : Reflect.field(value, 'name');
			return name == null || StringTools.trim(Std.string(name)) == ''
				? null : StringTools.trim(Std.string(name));
		} catch (_:Dynamic) {
			return null;
		}
	}

	static function readSettings(owner:String, diagnose:String->Void):Map<String, Dynamic> {
		var path = ownedFile(owner, 'data/settings.json');
		if (path == null) return null;
		var raw:String;
		try raw = File.getContent(path) catch (_:Dynamic) return null;
		var parsed:Dynamic = null;
		var strictError:Dynamic = null;
		try {
			parsed = Json.parse(raw);
		} catch (error:Dynamic) {
			strictError = error;
			try {
				parsed = tjson.TJSON.parse(raw, path);
			} catch (tolerantError:Dynamic) {
				report(diagnose, 'Could not parse imported settings at ' + path + ': '
					+ Std.string(tolerantError));
				return null;
			}
		}
		var values:Map<String, Dynamic> = new Map<String, Dynamic>();
		if (Std.isOfType(parsed, Array)) {
			for (entry in (cast parsed:Array<Dynamic>)) {
				if (entry == null) continue;
				var save:Dynamic = Reflect.field(entry, 'save');
				if (save == null) continue;
				var key = StringTools.trim(Std.string(save));
				if (key != '' && Reflect.hasField(entry, 'value'))
					values.set(key, Reflect.field(entry, 'value'));
			}
		} else if (parsed != null) {
			for (key in Reflect.fields(parsed)) {
				var value:Dynamic = Reflect.field(parsed, key);
				if (value != null && Reflect.hasField(value, 'value'))
					values.set(key, Reflect.field(value, 'value'));
				else
					values.set(key, value);
			}
		} else {
			report(diagnose, 'Imported settings have an unsupported top-level value at ' + path);
			return null;
		}
		if (strictError != null)
			report(diagnose, 'Accepted malformed imported settings with the tolerant parser at '
				+ path + ': ' + Std.string(strictError));
		return values;
	}
	#else
	static function readPackName(_owner:String):Null<String> return null;
	static function readSettings(_owner:String, _diagnose:String->Void):Map<String, Dynamic> return null;
	#end

	static function report(diagnose:String->Void, message:String):Void {
		if (diagnose == null) return;
		try diagnose(message) catch (_:Dynamic) {}
	}
}
