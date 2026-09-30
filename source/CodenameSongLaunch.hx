package;

import haxe.io.Path;
using StringTools;
#if sys
import sys.FileSystem;
import sys.io.File;
#end

/** Resolve an imported Codename song name through the currently selected
	owner when a canonical song folder has been owner-qualified. */
class CodenameSongLaunch {
	public static function resolveStorageFolder(songName:String, activeOwner:String,
		?dataRoot:String = 'assets/data'):String {
		var clean = songName == null ? '' : StringTools.trim(songName);
		if (!validName(clean))
			throw '[codename-load-song] Unsafe song name';
		var canonical = clean.toLowerCase();
		if (activeOwner == null || StringTools.trim(activeOwner) == '')
			return canonical;
		#if sys
		var root = dataRoot == null || StringTools.trim(dataRoot) == '' ? 'assets/data' : dataRoot;
		if (!FileSystem.exists(root) || !FileSystem.isDirectory(root))
			return canonical;
		var matches:Array<String> = [];
		var canonicalHasOwnerMetadata = false;
		var entries:Array<String>;
		try entries = FileSystem.readDirectory(root) catch (error:Dynamic)
			throw '[codename-load-song] Could not inspect imported chart folders: ' + Std.string(error);
		entries.sort(function(a:String, b:String):Int return Reflect.compare(a.toLowerCase(), b.toLowerCase()));
		for (entry in entries) {
			var key = entry.toLowerCase();
			if (key != canonical && !StringTools.startsWith(key, canonical + '--'))
				continue;
			if (!validName(entry))
				continue;
			var folderPath = boundedChild(root, entry);
			if (folderPath == null || !FileSystem.isDirectory(folderPath))
				continue;
			var ownerState = inspectOwner(folderPath, entry, canonical, activeOwner);
			if (key == canonical && ownerState.metadata) canonicalHasOwnerMetadata = true;
			if (ownerState.matches) matches.push(entry);
		}
		if (matches.length > 1)
			throw '[codename-load-song] Multiple installed folders for ' + clean
				+ ' claim the selected Codename owner';
		if (matches.length == 1)
			return matches[0];
		var canonicalPath = boundedChild(root, canonical);
		if (canonicalPath != null && FileSystem.isDirectory(canonicalPath)) {
			if (canonicalHasOwnerMetadata)
				throw '[codename-load-song] Chart folder ' + canonical
					+ ' is owned by a different import; selected owner has no matching chart';
			// Unmanifested base-game charts remain addressable to imported menus.
			return canonical;
		}
		throw '[codename-load-song] No chart folder for ' + clean
			+ ' belongs to the selected Codename owner';
		#else
		return canonical;
		#end
	}

	static function validName(value:String):Bool {
		return value != null && StringTools.trim(value) != '' && value != '.' && value != '..'
			&& value.indexOf('/') < 0 && value.indexOf('\\') < 0 && value.indexOf(':') < 0
			&& value.indexOf('\u0000') < 0;
	}

	#if sys
	static function boundedChild(root:String, child:String):Null<String> {
		try {
			var fullRoot = Path.normalize(FileSystem.fullPath(root));
			var candidate = Path.normalize(FileSystem.fullPath(Path.join([root, child])));
			var prefix = fullRoot.endsWith('/') ? fullRoot : fullRoot + '/';
			if (candidate == fullRoot || StringTools.startsWith(candidate, prefix))
				return Path.join([root, child]);
		} catch (_:Dynamic) {}
		return null;
	}

	static function inspectOwner(folderPath:String, folderName:String, songKey:String,
		activeOwner:String):{matches:Bool, metadata:Bool} {
		var matches = false;
		var metadata = false;
		var isQualified = folderName.toLowerCase() != songKey;
		var compatPath = Path.join([folderPath, CompatScriptManifest.FILE_NAME]);
		if (FileSystem.exists(compatPath) && !FileSystem.isDirectory(compatPath)) {
			metadata = true;
			try {
				var manifest = CompatScriptManifest.parse(File.getContent(compatPath));
				var selected = CompatScriptManifest.selectedRoot(manifest);
				if (!isQualified && selected != '' && CompatScriptManifest.destinationKey(selected)
					== CompatScriptManifest.destinationKey(activeOwner)) matches = true;
			} catch (_:Dynamic) {}
		}
		var provenancePath = Path.join([folderPath, 'importProvenance.json']);
		if (FileSystem.exists(provenancePath) && !FileSystem.isDirectory(provenancePath)) {
			try {
				var provenance:Dynamic = haxe.Json.parse(File.getContent(provenancePath));
				var owner:Dynamic = Reflect.field(provenance, 'sourceOwner');
				var sourceFolder:Dynamic = Reflect.field(provenance, 'sourceFolder');
				var destinationFolder:Dynamic = Reflect.field(provenance, 'destinationFolder');
				if (owner != null && StringTools.trim(Std.string(owner)) != '') {
					metadata = true;
					var sourceMatches = sourceFolder != null
						&& StringTools.trim(Std.string(sourceFolder)).toLowerCase() == songKey;
					var destinationMatches = destinationFolder == null
						|| StringTools.trim(Std.string(destinationFolder)).toLowerCase() == folderName.toLowerCase();
					if (sourceMatches && destinationMatches
						&& CompatScriptManifest.destinationKey(Std.string(owner))
							== CompatScriptManifest.destinationKey(activeOwner)) matches = true;
				}
			} catch (_:Dynamic) {}
		}
		return {matches:matches, metadata:metadata};
	}
	#end
}
