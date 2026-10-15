package;

#if sys
import haxe.io.Path;
import sys.FileSystem;

typedef NightmareVisionSharedCoreFileOps = {
	var link:(existing:String, created:String) -> Bool;
	var replace:(source:String, target:String) -> Bool;
	var sameFile:(left:String, right:String) -> Bool;
	/** Names the stored file has; 0 when unknown. */
	@:optional var linkCount:(path:String) -> Int;
}

typedef NightmareVisionSharedCoreResult = {
	var linked:Int;
	var bytesShared:Float;
	var supported:Bool;
}

/**
	One stored copy of a Nightmare Vision game's base assets for all of its
	content packages.

	Each package namespace of a game keeps the game's base assets below its own
	`__nmv_core` folder, because the runtime, the asset identity index and
	removal all treat a namespace as self-contained. Those folders hold the same
	files for every package of the game (about 70 MB each for a ten-package
	example). After an import commits, identical `__nmv_core` files of that
	import are turned into hard links to one stored file. A package file whose
	bytes equal a core file joins the same stored file: a game's compiled asset
	list can repeat every content package inside the core.

	Paths, manifests and hashes stay exactly as they were, so nothing else in the
	engine changes. Removing a package deletes only its own names; the stored
	file is freed by the filesystem when the last package that uses it is gone.
	Older imports join the shared copy on their next refresh. Files whose bytes
	no longer match the committed manifest, or that another program holds open,
	are left as they are. On a filesystem without hard links nothing changes.
*/
class NightmareVisionSharedCore {
	public static inline var CORE_FOLDER:String = "__nmv_core";
	static inline var TEMP_SUFFIX:String = ".shared-core.tmp";
	/** NTFS gives one stored file at most 1024 names. A refused link from a
	 * file this close to that limit says nothing about the filesystem. */
	static inline var FULL_LINK_COUNT:Int = 1000;

	/** Tests replace the filesystem operations; null uses NativeFileLink. */
	public static var fileOps:Null<NightmareVisionSharedCoreFileOps> = null;

	/** Link identical core files listed in a committed import manifest. */
	public static function linkCommitted(install:String, manifest:Dynamic):NightmareVisionSharedCoreResult {
		var result:NightmareVisionSharedCoreResult = {linked:0, bytesShared:0, supported:true};
		var files:Dynamic = manifest == null ? null : Reflect.field(manifest, "files");
		if (install == null || !Std.isOfType(files, Array)) return result;
		var ops = fileOps != null ? fileOps : {
			link:NativeFileLink.link, replace:NativeFileLink.replace, sameFile:NativeFileLink.sameFile,
			linkCount:NativeFileLink.linkCount
		};
		var groups:Map<String, Array<String>> = new Map();
		var withCore:Map<String, Bool> = new Map();
		var order:Array<String> = [];
		for (file in (cast files:Array<Dynamic>)) {
			var path:Dynamic = file == null ? null : Reflect.field(file, "path");
			var sha:Dynamic = file == null ? null : Reflect.field(file, "sha256");
			if (!Std.isOfType(path, String) || !Std.isOfType(sha, String) || !isNamespaceFile(path)) continue;
			var key = Std.string(sha).toLowerCase();
			var group = groups.get(key);
			if (group == null) {
				groups.set(key, group = []);
				order.push(key);
			}
			group.push(path);
			if (isCoreFile(path)) withCore.set(key, true);
		}
		var root = Path.normalize(FileSystem.fullPath(install));
		for (sha in order) {
			var group = groups.get(sha);
			if (group.length < 2 || !withCore.exists(sha)) continue;
			group.sort(Reflect.compare);
			var anchor:String = null;
			var anchorSize = -1;
			for (path in group) {
				ImportWorkScheduler.cooperate();
				var live = Path.join([root, path]);
				if (anchor == null) {
					if (matches(live, sha)) {
						anchor = live;
						anchorSize = FileSystem.stat(live).size;
					}
					continue;
				}
				if (anchorSize == 0) break;
				if (!isRegularFile(live) || ops.sameFile(anchor, live)) continue;
				if (FileSystem.stat(live).size != anchorSize || !matches(live, sha)) continue;
				var temp = live + TEMP_SUFFIX;
				if (FileSystem.exists(temp)) try FileSystem.deleteFile(temp) catch (_:Dynamic) continue;
				if (!ops.link(anchor, temp)) {
					// A stored file that already has the most names a file can have
					// (many identical small files across many packages) hands over
					// to this copy, which keeps the rest of the group shared instead
					// of ending the whole pass.
					if (ops.linkCount != null && ops.linkCount(anchor) >= FULL_LINK_COUNT) {
						anchor = live;
						continue;
					}
					// Any other refusal means this filesystem has no hard links;
					// every other attempt would fail the same way.
					result.supported = false;
					return result;
				}
				if (!ops.replace(temp, live)) {
					try FileSystem.deleteFile(temp) catch (_:Dynamic) {}
					continue;
				}
				result.linked++;
				result.bytesShared += anchorSize;
			}
		}
		return result;
	}

	/** `assets/imported_mods/<namespace>/__nmv_core/<file>` */
	public static function isCoreFile(path:String):Bool {
		var parts = path.split("/");
		return isNamespaceFile(path) && parts.length >= 5 && parts[3] == CORE_FOLDER;
	}

	/** `assets/imported_mods/<namespace>/<file>` */
	static function isNamespaceFile(path:String):Bool {
		var parts = path.split("/");
		return parts.length >= 4 && parts[0].toLowerCase() == "assets" && parts[1].toLowerCase() == "imported_mods"
			&& parts.indexOf("..") < 0 && parts.indexOf("") < 0 && parts.indexOf(".") < 0;
	}

	static function matches(path:String, sha:String):Bool {
		try return isRegularFile(path) && ImportSourceSnapshot.sha256File(path) == sha catch (_:Dynamic) return false;
	}

	static function isRegularFile(path:String):Bool {
		try return FileSystem.exists(path) && !FileSystem.isDirectory(path) catch (_:Dynamic) return false;
	}
}
#end
