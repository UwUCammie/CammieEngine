package;

import haxe.io.Bytes;
import haxe.io.Path;
import ImportRevision.ImportRevisionAssessment;
import sys.FileSystem;
import sys.io.File;
import sys.io.FileInput;
import sys.io.FileOutput;
import sys.io.FileSeek;
using StringTools;

typedef ImportSourceSnapshotProgress = {
	var phase:String;
	var current:String;
	var filesCompleted:Int;
	var filesTotal:Int;
	var bytesCompleted:Float;
	var bytesTotal:Float;
}

typedef ImportSourceSnapshotOptions = {
	/** Optional caller-selected cap on visited file and directory entries. */
	@:optional var maxEntries:Int;
	/** Optional caller-selected cap on retained bytes. */
	@:optional var maxBytes:Float;
	/** Copy buffer size, clamped to 4 KiB..1 MiB. */
	@:optional var chunkSize:Int;
	@:optional var cancelled:Void->Bool;
	@:optional var onProgress:ImportSourceSnapshotProgress->Void;
	/** Dependencies known by the caller to live outside the selected source. */
	@:optional var unresolvedDependencies:Array<String>;
}

typedef ImportSourceSnapshotResult = {
	var status:String;
	var complete:Bool;
	var snapshotId:String;
	var snapshotRoot:String;
	var receiptPath:String;
	var files:Int;
	var directories:Int;
	var bytes:Float;
	var exclusions:Array<Dynamic>;
	var omissions:Array<Dynamic>;
	var incompleteReasons:Array<String>;
	var error:String;
}

private typedef ImportSnapshotEntry = {
	var relativePath:String;
	var sourcePath:String;
	var canonicalPath:String;
	var size:Int;
	var modified:Float;
}

private typedef ImportSnapshotDirectory = {
	var relativePath:String;
	var sourcePath:String;
	var canonicalPath:String;
	var modified:Float;
	var ancestry:ImportSnapshotAncestry;
}

private typedef ImportSnapshotAncestry = {
	var canonicalPath:String;
	var parent:Null<ImportSnapshotAncestry>;
}

/**
	Copies a selected raw source tree into an explicit caller-owned cache.

	The cache root must be outside the donor tree, unmounted from the runtime
	import namespace, and chosen by the caller.  This class never modifies the
	donor or an existing import.  It copies bytes into a unique staging tree,
	never hardlinks mutable donor files, writes the receipt last, and publishes
	the staged tree by an atomic directory rename.  A receipt marked incomplete
	can be retained for diagnosis but must not be treated as rebuildable.
*/
class ImportSourceSnapshot {
	public static inline var RECEIPT_SCHEMA_VERSION:Int = 1;
	public static inline var DEFAULT_CHUNK_SIZE:Int = 65536;
	static inline var HEADER_PROBE_BYTES:Int = 4096;

	/**
		Capture all selected source content, including files with unknown
		extensions, Windows executables and empty directories. Shared libraries
		and other native payloads are omitted by extension/header and described in the
		receipt. Path escapes, loops, caller-declared external dependencies, and
		bounded-walk omissions are also described and make the receipt incomplete.
	*/
	public static function capture(sourceRoot:String, cacheRoot:String, engine:String,
		?applicationVersion:String, ?options:ImportSourceSnapshotOptions):ImportSourceSnapshotResult {
		var output = result("failed");
		var stagePath = "";
		var published = false;
		var stageExists = false;
		try {
			var canonicalEngine = ImportRevision.normalizeEngine(engine);
			if (canonicalEngine == "") throw "A supported source engine is required.";
			if (sourceRoot == null || sourceRoot == "" || !FileSystem.exists(sourceRoot)
				|| !FileSystem.isDirectory(sourceRoot)) throw "The selected source root is not an accessible directory.";
			if (cacheRoot == null || cacheRoot.trim() == "") throw "An explicit snapshot cache root is required.";

			var donor = canonicalPath(sourceRoot);
			var cache = canonicalDestination(cacheRoot);
			if (isWithin(cache, donor)) throw "The snapshot cache root must be outside the selected source tree.";

			var maxEntries = options != null && options.maxEntries != null ? options.maxEntries : 0;
			var maxBytes = options != null && options.maxBytes != null ? options.maxBytes : Math.POSITIVE_INFINITY;
			var chunkSize = options != null && options.chunkSize != null ? options.chunkSize : DEFAULT_CHUNK_SIZE;
			if (maxEntries < 0) throw "Snapshot entry limit cannot be negative.";
			if (maxBytes < 0) throw "Snapshot byte limit cannot be negative.";
			if (chunkSize < 4096) chunkSize = 4096;
			if (chunkSize > 1048576) chunkSize = 1048576;

			var entries:Array<ImportSnapshotEntry> = [];
			var directories:Array<ImportSnapshotDirectory> = [];
			var exclusions:Array<Dynamic> = [];
			var omissions:Array<Dynamic> = [];
			var incompleteReasons:Array<String> = [];
			var plannedBytes:Float = 0;
			var visited = 0;
			var rootStat = FileSystem.stat(donor);
			var rootModified = rootStat.mtime.getTime();
			var stack:Array<ImportSnapshotDirectory> = [{
				relativePath: "", sourcePath: donor, canonicalPath: donor,
				modified: rootModified, ancestry: {canonicalPath: donor, parent: null}
			}];
			var stopWalk = false;

			while (stack.length > 0 && !stopWalk) {
				if (isCancelled(options)) return finishFailure(output, "cancelled", "Snapshot capture was cancelled.", stagePath, stageExists);
				var directory = stack.pop();
				var children:Array<String>;
				try {
					children = FileSystem.readDirectory(directory.sourcePath);
				} catch (error:Dynamic) {
					addOmission(omissions, incompleteReasons, directory.relativePath, "unreadable-directory", "The directory could not be read.");
					continue;
				}
				for (name in children) {
					if (isCancelled(options)) return finishFailure(output, "cancelled", "Snapshot capture was cancelled.", stagePath, stageExists);
					visited++;
					if (maxEntries > 0 && visited > maxEntries) {
						addReason(incompleteReasons, "entry-limit-exceeded");
						stopWalk = true;
						break;
					}
					if (!validComponent(name)) {
						addOmission(omissions, incompleteReasons, joinRelative(directory.relativePath, name), "invalid-path-component", "The filesystem returned an invalid child name.");
						continue;
					}
					var relative = joinRelative(directory.relativePath, name);
					var child = joinFsPath(directory.sourcePath, name);
					var resolved:String;
					try {
						resolved = canonicalPath(child);
					} catch (error:Dynamic) {
						addOmission(omissions, incompleteReasons, relative, "unresolvable-entry", "The entry could not be canonicalized.");
						continue;
					}
					if (!isWithin(resolved, donor)) {
						addOmission(omissions, incompleteReasons, relative, "path-escapes-source-root", "The canonical entry path leaves the selected source root.");
						continue;
					}
					var isDirectory:Bool;
				try isDirectory = FileSystem.isDirectory(child) catch (error:Dynamic) {
						addOmission(omissions, incompleteReasons, relative, "unreadable-entry", "The entry type could not be inspected.");
						continue;
					}
				var stat:sys.FileStat;
				try stat = FileSystem.stat(child) catch (error:Dynamic) {
					addOmission(omissions, incompleteReasons, relative, "unreadable-entry", "The entry metadata could not be read.");
					continue;
				}
				var specialNode = specialNodeKind(stat.mode);
				if (specialNode != "") {
					addOmission(omissions, incompleteReasons, relative, "special-filesystem-node-" + specialNode,
						"Non-regular filesystem nodes are not copied into retained source snapshots.");
					continue;
				}
				if (isDirectory) {
						if (containsAncestor(directory.ancestry, resolved)) {
							addOmission(omissions, incompleteReasons, relative, "directory-loop", "Directory resolution points to an ancestor already being traversed.");
							continue;
						}
						var childAncestry = {canonicalPath: resolved, parent: directory.ancestry};
						directories.push({relativePath: relative, sourcePath: child, canonicalPath: resolved,
							modified: stat.mtime.getTime(), ancestry: childAncestry});
						stack.push({relativePath: relative, sourcePath: child, canonicalPath: resolved,
							modified: stat.mtime.getTime(), ancestry: childAncestry});
					} else {
						var exclusionReason = nativeExtension(name);
						var detectedHeader = "";
						if (exclusionReason == "") {
							try detectedHeader = nativeHeader(child, stat.size) catch (error:Dynamic) {
								addOmission(omissions, incompleteReasons, relative, "unreadable-header", "The file header could not be read.");
								continue;
							}
							// Keep Windows executables as source evidence. They can
							// contain the only engine marker used by future rescans.
							if (detectedHeader != "" && !name.toLowerCase().endsWith(".exe"))
								exclusionReason = "native-header-" + detectedHeader;
						}
						if (exclusionReason != "") {
							exclusions.push({path: relative, size: stat.size, reason: exclusionReason, detectedHeader: detectedHeader});
						} else if (plannedBytes + stat.size > maxBytes) {
							addOmission(omissions, incompleteReasons, relative, "byte-limit-exceeded", "The retained source exceeded the configured byte limit.");
						} else {
							plannedBytes += stat.size;
							entries.push({relativePath: relative, sourcePath: child, canonicalPath: resolved,
								size: stat.size, modified: stat.mtime.getTime()});
						}
					}
					progress(options, "scan", relative, entries.length, -1, plannedBytes, -1);
				}
			}

			if (options != null && options.unresolvedDependencies != null) {
				for (dependency in options.unresolvedDependencies) {
					var value = dependency == null ? "" : dependency.trim();
					if (value != "") addReason(incompleteReasons, "external-dependency:" + value);
				}
			}
			entries.sort(function(a, b) return Reflect.compare(a.relativePath, b.relativePath));
			directories.sort(function(a, b) return Reflect.compare(a.relativePath, b.relativePath));
			exclusions.sort(function(a, b) return Reflect.compare(Reflect.field(a, "path"), Reflect.field(b, "path")));

			createDirectoryRecursive(cache);
			stagePath = uniqueStagePath(cache);
			FileSystem.createDirectory(stagePath);
			stageExists = true;
			var contentStagePath = joinFsPath(stagePath, "content");
			FileSystem.createDirectory(contentStagePath);
			var copied:Array<Dynamic> = [];
			var copiedBytes:Float = 0;
			var completedFiles = 0;
			var buffer = Bytes.alloc(chunkSize);
			for (directory in directories) {
				if (isCancelled(options)) return finishFailure(output, "cancelled", "Snapshot capture was cancelled.", stagePath, stageExists);
				createContainedDirectory(contentStagePath, directory.relativePath);
			}
			for (entry in entries) {
				if (isCancelled(options)) return finishFailure(output, "cancelled", "Snapshot capture was cancelled.", stagePath, stageExists);
				var currentCanonical = canonicalPath(entry.sourcePath);
				if (!isWithin(currentCanonical, donor) || currentCanonical != entry.canonicalPath)
					throw "Source path changed or escaped during snapshot capture: " + entry.relativePath;
				var before = FileSystem.stat(entry.sourcePath);
				if (!isRegularFileMode(before.mode))
					throw "Source entry is no longer a regular file: " + entry.relativePath;
				if (before.size != entry.size || before.mtime.getTime() != entry.modified)
					throw "Source file changed after snapshot scanning: " + entry.relativePath;
				var destination = joinFsRelative(contentStagePath, entry.relativePath);
				createContainedDirectory(contentStagePath, relativeDirectory(entry.relativePath));
				var input:FileInput = null;
				var target:FileOutput = null;
				var fileHash = new ImportSnapshotSha256();
				var remaining = entry.size;
				try {
					input = File.read(entry.sourcePath, true);
					target = File.write(destination, true);
					while (remaining > 0) {
						if (isCancelled(options)) throw new ImportSnapshotCancelled();
						var count = remaining < buffer.length ? remaining : buffer.length;
						var read = input.readBytes(buffer, 0, count);
						if (read != count) throw "Short read while copying " + entry.relativePath;
						target.writeBytes(buffer, 0, read);
						fileHash.update(buffer, 0, read);
						remaining -= read;
						copiedBytes += read;
						progress(options, "copy", entry.relativePath, completedFiles, entries.length, copiedBytes, plannedBytes);
					}
					input.close(); input = null;
					target.close(); target = null;
				} catch (error:Dynamic) {
					if (input != null) try input.close() catch (_:Dynamic) {}
					if (target != null) try target.close() catch (_:Dynamic) {}
					if (Std.isOfType(error, ImportSnapshotCancelled))
						return finishFailure(output, "cancelled", "Snapshot capture was cancelled.", stagePath, stageExists);
					throw error;
				}
				var after = FileSystem.stat(entry.sourcePath);
				if (after.size != entry.size || after.mtime.getTime() != entry.modified
					|| canonicalPath(entry.sourcePath) != entry.canonicalPath)
					throw "Source file changed while being copied: " + entry.relativePath;
				copied.push({path: entry.relativePath, size: entry.size, sha256: fileHash.digestHex()});
				completedFiles++;
				progress(options, "copy", entry.relativePath, completedFiles, entries.length, copiedBytes, plannedBytes);
			}

			// Directory timestamps catch additions/removals during the bounded walk.
			for (directory in directories) {
				var nowPath = canonicalPath(directory.sourcePath);
				var nowStat = FileSystem.stat(directory.sourcePath);
				if (!isWithin(nowPath, donor) || nowPath != directory.canonicalPath
					|| !FileSystem.isDirectory(directory.sourcePath) || nowStat.mtime.getTime() != directory.modified)
					addReason(incompleteReasons, "source-changed-during-copy:" + directory.relativePath);
			}
			if (FileSystem.stat(donor).mtime.getTime() != rootModified)
				addReason(incompleteReasons, "source-root-changed-during-copy");

			var snapshotHash = new ImportSnapshotSha256();
			var snapshotHeader = Bytes.ofString("ImportSourceSnapshot\n" + RECEIPT_SCHEMA_VERSION + "\n" + canonicalEngine + "\n");
			snapshotHash.update(snapshotHeader, 0, snapshotHeader.length);
			for (directory in directories) hashRecord(snapshotHash, "D", directory.relativePath);
			for (file in copied) hashRecord(snapshotHash, "F", file.path + "\t" + file.size + "\t" + file.sha256);
			for (exclusion in exclusions) hashRecord(snapshotHash, "X", Reflect.field(exclusion, "path") + "\t"
				+ Reflect.field(exclusion, "size") + "\t" + Reflect.field(exclusion, "reason") + "\t"
				+ Reflect.field(exclusion, "detectedHeader"));
			omissions.sort(function(a, b) {
				var byPath = Reflect.compare(Reflect.field(a, "path"), Reflect.field(b, "path"));
				if (byPath != 0) return byPath;
				return Reflect.compare(Reflect.field(a, "reason"), Reflect.field(b, "reason"));
			});
			incompleteReasons.sort(Reflect.compare);
			for (omission in omissions) hashRecord(snapshotHash, "O", Reflect.field(omission, "path") + "\t"
				+ Reflect.field(omission, "reason") + "\t" + Reflect.field(omission, "detail"));
			for (reason in incompleteReasons) hashRecord(snapshotHash, "I", reason);
			var snapshotId = snapshotHash.digestHex();
			var finalRoot = joinFsPath(cache, snapshotId);
			var receipt:Dynamic = {
				snapshotSchemaVersion: RECEIPT_SCHEMA_VERSION,
				snapshotId: snapshotId,
				contentRoot: "content",
				importRevision: ImportRevision.current(canonicalEngine, applicationVersion),
				files: copied,
				directories: [for (directory in directories) directory.relativePath],
				bytes: copiedBytes,
				exclusions: exclusions,
				omissions: omissions,
				incompleteReasons: incompleteReasons
			};

			if (FileSystem.exists(finalRoot)) {
				if (!validExistingSnapshot(finalRoot, snapshotId))
					throw "Snapshot ID collision with an invalid or incompatible existing receipt.";
				deleteTree(stagePath, stagePath);
				stageExists = false;
				output.status = "existing";
				output.complete = existingSnapshotComplete(finalRoot);
				output.snapshotId = snapshotId;
				output.snapshotRoot = finalRoot;
				output.receiptPath = joinFsPath(finalRoot, "receipt.json");
				output.files = copied.length;
				output.directories = directories.length;
				output.bytes = copiedBytes;
				output.exclusions = exclusions;
				output.omissions = omissions;
				output.incompleteReasons = incompleteReasons;
				return output;
			}

			var stagedReceipt = joinFsPath(stagePath, "receipt.json");
			var tempReceipt = joinFsPath(stagePath, ".receipt.tmp");
			File.saveContent(tempReceipt, haxe.Json.stringify(receipt, null, "\t"));
			if (FileSystem.exists(stagedReceipt)) throw "Unexpected receipt already exists in staging tree.";
			FileSystem.rename(tempReceipt, stagedReceipt);
			progress(options, "commit", snapshotId, completedFiles, entries.length, copiedBytes, plannedBytes);
			if (isCancelled(options)) return finishFailure(output, "cancelled", "Snapshot capture was cancelled before publication.", stagePath, stageExists);
			FileSystem.rename(stagePath, finalRoot);
			stageExists = false;
			published = true;
			output.status = incompleteReasons.length == 0 ? "complete" : "incomplete";
			output.complete = incompleteReasons.length == 0;
			output.snapshotId = snapshotId;
			output.snapshotRoot = finalRoot;
			output.receiptPath = joinFsPath(finalRoot, "receipt.json");
			output.files = copied.length;
			output.directories = directories.length;
			output.bytes = copiedBytes;
			output.exclusions = exclusions;
			output.omissions = omissions;
			output.incompleteReasons = incompleteReasons;
			return output;
		} catch (error:Dynamic) {
			if (stageExists && !published) deleteTree(stagePath, stagePath);
			output.status = "failed";
			output.complete = false;
			output.error = Std.string(error);
			return output;
		}
	}

	/** Read a staged receipt and assess whether its importer semantics are
	 * current. Receipts without an explicit revision remain unknown. */
	public static function assessReceipt(receiptPath:String, engine:String):ImportRevisionAssessment {
		try {
			var receipt:Dynamic = haxe.Json.parse(File.getContent(receiptPath));
			var snapshotSchema:Dynamic = Reflect.field(receipt, "snapshotSchemaVersion");
			var unknown = ImportRevision.assess(null, engine);
			if (!Std.isOfType(snapshotSchema, Int)) return unknown;
			var schema:Int = cast snapshotSchema;
			if (schema > RECEIPT_SCHEMA_VERSION) {
				unknown.status = ImportRevision.FUTURE;
				unknown.reason = "The snapshot receipt uses a newer receipt schema.";
				return unknown;
			}
			if (schema < RECEIPT_SCHEMA_VERSION) {
				unknown.status = ImportRevision.OUTDATED;
				unknown.reason = "The snapshot receipt predates the current receipt schema.";
				return unknown;
			}
			return ImportRevision.assess(Reflect.field(receipt, "importRevision"), engine);
		} catch (_:Dynamic) {
			return ImportRevision.assess(null, engine);
		}
	}

	/** Hash one regular file with bounded memory. Callers that need cancellation
	 * or progress while hashing can use the public incremental helper directly. */
	public static function sha256File(path:String, ?chunkSize:Int):String {
		if (chunkSize == null || chunkSize < 4096) chunkSize = DEFAULT_CHUNK_SIZE;
		if (chunkSize > 1048576) chunkSize = 1048576;
		var hash = new ImportSnapshotSha256();
		var stat = FileSystem.stat(path);
		if (!isRegularFileMode(stat.mode)) throw "Cannot hash a non-regular filesystem node: " + path;
		var remaining = stat.size;
		var input = File.read(path, true);
		var buffer = Bytes.alloc(chunkSize);
		try {
			while (remaining > 0) {
				var count = remaining < buffer.length ? remaining : buffer.length;
				var read = input.readBytes(buffer, 0, count);
				if (read != count) throw "Short read while hashing " + path;
				hash.update(buffer, 0, read);
				remaining -= read;
			}
		} catch (error:Dynamic) {
			input.close();
			throw error;
		}
		input.close();
		return hash.digestHex();
	}

	/** Verify a retained snapshot before regeneration. This rechecks its receipt,
	 * exact content tree, containment, and every retained file's size and hash. */
	public static function verify(snapshotRoot:String, expectedId:String, ?cancel:Void->Bool,
		?onProgress:ImportSourceSnapshotProgress->Void):Void {
		if (snapshotRoot == null || StringTools.trim(snapshotRoot) == "")
			throw "A snapshot root is required for verification.";
		if (!isSha256(expectedId)) throw "Expected snapshot ID is invalid.";
		var rootPath = normalizeAbsolute(FileSystem.absolutePath(snapshotRoot));
		if (!FileSystem.exists(rootPath) || !FileSystem.isDirectory(rootPath))
			throw "Snapshot root is missing or is not a directory.";
		var rootCanonical = canonicalPath(rootPath);
		if (rootCanonical != rootPath) throw "Snapshot root cannot traverse symbolic links.";
		var normalizedId = expectedId.toLowerCase();
		if (baseFsName(rootCanonical).toLowerCase() != normalizedId)
			throw "Snapshot directory name does not match the expected ID.";
		var receiptPath = joinFsPath(rootCanonical, "receipt.json");
		if (!FileSystem.exists(receiptPath) || FileSystem.isDirectory(receiptPath)
			|| canonicalPath(receiptPath) != receiptPath)
			throw "Snapshot receipt is missing or is not a regular file.";
		var receiptStat = FileSystem.stat(receiptPath);
		if (specialNodeKind(receiptStat.mode) != "" || !isRegularFileMode(receiptStat.mode))
			throw "Snapshot receipt is not a regular file.";
		if (receiptStat.size < 0) throw "Snapshot receipt has an invalid size.";
		var receipt:Dynamic;
		try receipt = haxe.Json.parse(File.getContent(receiptPath)) catch (error:Dynamic)
			throw "Snapshot receipt is invalid: " + Std.string(error);
		if (Reflect.field(receipt, "snapshotSchemaVersion") != RECEIPT_SCHEMA_VERSION)
			throw "Snapshot receipt uses an unsupported schema.";
		if (Reflect.field(receipt, "snapshotId") != normalizedId)
			throw "Snapshot receipt ID does not match the expected ID.";
		if (Reflect.field(receipt, "contentRoot") != "content")
			throw "Snapshot receipt content root is invalid.";
		var revision:Dynamic = Reflect.field(receipt, "importRevision");
		var engineValue:Dynamic = revision == null ? null : Reflect.field(revision, "sourceEngine");
		var engine = engineValue == null ? "" : ImportRevision.normalizeEngine(Std.string(engineValue));
		if (engine == "") throw "Snapshot receipt source engine is invalid.";

		var fileValues:Dynamic = Reflect.field(receipt, "files");
		var directoryValues:Dynamic = Reflect.field(receipt, "directories");
		var exclusionValues:Dynamic = Reflect.field(receipt, "exclusions");
		var omissionValues:Dynamic = Reflect.field(receipt, "omissions");
		var incompleteValues:Dynamic = Reflect.field(receipt, "incompleteReasons");
		if (!Std.isOfType(fileValues, Array) || !Std.isOfType(directoryValues, Array)
			|| !Std.isOfType(exclusionValues, Array) || !Std.isOfType(omissionValues, Array)
			|| !Std.isOfType(incompleteValues, Array))
			throw "Snapshot receipt entry lists are invalid.";
		var files:Array<Dynamic> = cast fileValues;
		var directories:Array<Dynamic> = cast directoryValues;
		var exclusions:Array<Dynamic> = cast exclusionValues;
		var omissions:Array<Dynamic> = cast omissionValues;
		var incompleteReasons:Array<Dynamic> = cast incompleteValues;
		var expectedFiles:Map<String, Dynamic> = new Map();
		var expectedDirectories:Map<String, String> = new Map();
		var fileHashEntries:Array<Dynamic> = [];
		var directoryHashEntries:Array<String> = [];
		var expectedBytes:Float = 0;
		for (entry in files) {
			var relative = requiredString(Reflect.field(entry, "path"), "file path");
			var key = snapshotPathKey(relative);
			if (!validSnapshotRelative(relative) || expectedFiles.exists(key) || expectedDirectories.exists(key))
				throw "Snapshot receipt has a duplicate or invalid file path: " + relative;
			var sizeValue:Dynamic = Reflect.field(entry, "size");
			if (!Std.isOfType(sizeValue, Int) || (cast sizeValue:Int) < 0)
				throw "Snapshot receipt has an invalid file size: " + relative;
			var digest = requiredString(Reflect.field(entry, "sha256"), "file hash").toLowerCase();
			if (!isSha256(digest)) throw "Snapshot receipt has an invalid file hash: " + relative;
			expectedFiles.set(key, {path:relative, size:(cast sizeValue:Int), sha256:digest});
			expectedBytes += (cast sizeValue:Int);
			fileHashEntries.push({path:relative, size:(cast sizeValue:Int), sha256:digest});
		}
		for (value in directories) {
			var relative = requiredString(value, "directory path");
			var key = snapshotPathKey(relative);
			if (!validSnapshotRelative(relative) || expectedDirectories.exists(key) || expectedFiles.exists(key))
				throw "Snapshot receipt has a duplicate or invalid directory path: " + relative;
			expectedDirectories.set(key, relative);
			directoryHashEntries.push(relative);
		}
		for (entry in fileHashEntries) {
			var parentPath = relativeDirectory(Reflect.field(entry, "path"));
			while (parentPath != "") {
				if (!expectedDirectories.exists(snapshotPathKey(parentPath)))
					throw "Snapshot receipt omits a parent directory: " + parentPath;
				parentPath = relativeDirectory(parentPath);
			}
		}
		for (relative in directoryHashEntries) {
			var parentPath = relativeDirectory(relative);
			while (parentPath != "") {
				if (!expectedDirectories.exists(snapshotPathKey(parentPath)))
					throw "Snapshot receipt omits a parent directory: " + parentPath;
				parentPath = relativeDirectory(parentPath);
			}
		}
		var receiptBytes:Dynamic = Reflect.field(receipt, "bytes");
		if (!Std.isOfType(receiptBytes, Int) && !Std.isOfType(receiptBytes, Float))
			throw "Snapshot receipt byte total is invalid.";
		if (expectedBytes != (cast receiptBytes:Float))
			throw "Snapshot receipt byte total does not match its file entries.";
		var computedId = receiptSnapshotId(engine, directoryHashEntries, fileHashEntries,
			exclusions, omissions, incompleteReasons);
		if (computedId != normalizedId)
			throw "Snapshot receipt contents do not match the expected ID.";

		var contentRoot = joinFsPath(rootCanonical, "content");
		if (!FileSystem.exists(contentRoot) || !FileSystem.isDirectory(contentRoot)
			|| canonicalPath(contentRoot) != contentRoot || !isWithin(contentRoot, rootCanonical))
			throw "Snapshot content root is missing or escapes the snapshot.";
		var actualFiles:Map<String, Bool> = new Map();
		var actualDirectories:Map<String, Bool> = new Map();
		var directoryTimes:Map<String, Float> = new Map();
		var pending:Array<String> = [""];
		var filesCompleted = 0;
		var bytesCompleted:Float = 0;
		var totalBytes = expectedBytes;
		while (pending.length > 0) {
			if (verificationCancelled(cancel)) throw "Snapshot verification was cancelled.";
			var directory = pending.pop();
			var directoryPath = directory == "" ? contentRoot : joinFsRelative(contentRoot, directory);
			var directoryCanonical = canonicalPath(directoryPath);
			if (directoryCanonical != normalizeAbsolute(directoryPath) || !isWithin(directoryCanonical, contentRoot)
				|| !FileSystem.isDirectory(directoryPath))
				throw "Snapshot directory is invalid or escapes its content root: " + directory;
			var beforeDirectory = FileSystem.stat(directoryPath);
			directoryTimes.set(directory, beforeDirectory.mtime.getTime());
			var children:Array<String>;
			try children = FileSystem.readDirectory(directoryPath) catch (error:Dynamic)
				throw "Could not list snapshot directory " + directory + ": " + Std.string(error);
			for (name in children) {
				if (verificationCancelled(cancel)) throw "Snapshot verification was cancelled.";
				if (!validComponent(name)) throw "Snapshot contains an invalid path component.";
				var relative = joinRelative(directory, name);
				var path = joinFsPath(directoryPath, name);
				var canonical = canonicalPath(path);
				if (canonical != normalizeAbsolute(path) || !isWithin(canonical, contentRoot))
					throw "Snapshot entry escapes its content root or follows a symbolic link: " + relative;
				if (FileSystem.isDirectory(path)) {
					var key = snapshotPathKey(relative);
					if (!expectedDirectories.exists(key)) throw "Unexpected snapshot directory: " + relative;
					actualDirectories.set(key, true);
					pending.push(relative);
					continue;
				}
				var stat = FileSystem.stat(path);
				var special = specialNodeKind(stat.mode);
				if (special != "") throw "Snapshot contains a non-regular filesystem node (" + special + "): " + relative;
				var key = snapshotPathKey(relative);
				if (!expectedFiles.exists(key)) throw "Unexpected snapshot file: " + relative;
				if (actualFiles.exists(key)) throw "Duplicate snapshot file path: " + relative;
				var expected:Dynamic = expectedFiles.get(key);
				if (stat.size != Reflect.field(expected, "size")) throw "Snapshot file size changed: " + relative;
				var digest = verifyFileHash(path, relative, stat, cancel, onProgress,
					filesCompleted, files.length, bytesCompleted, totalBytes);
				if (digest != Reflect.field(expected, "sha256")) throw "Snapshot file hash changed: " + relative;
				actualFiles.set(key, true);
				filesCompleted++;
				bytesCompleted += stat.size;
				verificationProgress(onProgress, relative, filesCompleted, files.length, bytesCompleted, totalBytes);
			}
			var afterDirectory = FileSystem.stat(directoryPath);
			if (afterDirectory.mtime.getTime() != directoryTimes.get(directory))
				throw "Snapshot directory changed during verification: " + directory;
		}
		for (key in expectedFiles.keys()) if (!actualFiles.exists(key)) throw "Snapshot file is missing: " + Reflect.field(expectedFiles.get(key), "path");
		for (key in expectedDirectories.keys()) if (!actualDirectories.exists(key)) throw "Snapshot directory is missing: " + expectedDirectories.get(key);
	}

	static function result(status:String):ImportSourceSnapshotResult return {
		status: status, complete: false, snapshotId: "", snapshotRoot: "", receiptPath: "",
		files: 0, directories: 0, bytes: 0, exclusions: [], omissions: [], incompleteReasons: [], error: ""
	};

	static function finishFailure(output:ImportSourceSnapshotResult, status:String, error:String,
		stagePath:String, stageExists:Bool):ImportSourceSnapshotResult {
		if (stageExists && stagePath != "") deleteTree(stagePath, stagePath);
		output.status = status;
		output.complete = false;
		output.error = error;
		return output;
	}

	static function isCancelled(options:ImportSourceSnapshotOptions):Bool {
		if (options == null || options.cancelled == null) return false;
		try return options.cancelled() catch (_:Dynamic) return true;
	}

	static function progress(options:ImportSourceSnapshotOptions, phase:String, current:String,
		filesCompleted:Int, filesTotal:Int, bytesCompleted:Float, bytesTotal:Float):Void {
		if (options == null || options.onProgress == null) return;
		try options.onProgress({phase: phase, current: current, filesCompleted: filesCompleted,
			filesTotal: filesTotal, bytesCompleted: bytesCompleted, bytesTotal: bytesTotal}) catch (_:Dynamic) {}
	}

	static function canonicalPath(path:String):String {
		return normalizeAbsolute(FileSystem.fullPath(path));
	}

	/** Canonicalize a possibly nonexistent destination through its nearest
	 * existing ancestor, so symlinked cache parents cannot bypass containment. */
	static function canonicalDestination(path:String):String {
		var absolute = normalizeAbsolute(FileSystem.absolutePath(path));
		var cursor = absolute;
		var suffix:Array<String> = [];
		while (!FileSystem.exists(cursor)) {
			var parent = parentFsPath(cursor);
			var name = baseFsName(cursor);
			if (parent == "" || parent == cursor || name == "") throw "Cannot resolve snapshot cache root.";
			suffix.unshift(name);
			cursor = parent;
		}
		var resolved = canonicalPath(cursor);
		for (part in suffix) resolved = joinFsPath(resolved, part);
		return normalizeAbsolute(resolved);
	}

	static function normalizeAbsolute(path:String):String {
		#if windows
		var normalized = Path.normalize(path).replace("\\", "/").toLowerCase();
		#else
		var absolute = path.startsWith("/");
		var parts:Array<String> = [];
		for (part in path.split("/")) {
			if (part == "" || part == ".") continue;
			if (part == ".." && parts.length > 0 && parts[parts.length - 1] != "..") parts.pop();
			else if (part != ".." || !absolute) parts.push(part);
		}
		var normalized = (absolute ? "/" : "") + parts.join("/");
		#end
		while (normalized.length > 1 && normalized.endsWith("/")) normalized = normalized.substr(0, normalized.length - 1);
		return normalized;
	}

	static function isWithin(path:String, root:String):Bool {
		if (path == root) return true;
		var prefix = root.endsWith("/") ? root : root + "/";
		return path.startsWith(prefix);
	}

	static function validComponent(value:String):Bool {
		if (value == null || value == "" || value == "." || value == ".." || value.indexOf("/") >= 0) return false;
		#if windows
		if (value.indexOf("\\") >= 0) return false;
		#end
		return true;
	}

	static function joinRelative(parent:String, name:String):String return parent == "" ? name : parent + "/" + name;

	static function joinFsPath(parent:String, child:String):String {
		#if windows
		return Path.join([parent, child]);
		#else
		return parent == "" || parent.endsWith("/") ? parent + child : parent + "/" + child;
		#end
	}

	static function joinFsRelative(parent:String, relative:String):String {
		var path = parent;
		if (relative == "") return path;
		for (part in relative.split("/")) path = joinFsPath(path, part);
		return path;
	}

	static function relativeDirectory(relative:String):String {
		var slash = relative.lastIndexOf("/");
		return slash < 0 ? "" : relative.substr(0, slash);
	}

	static function parentFsPath(path:String):String {
		#if windows
		return Path.directory(path);
		#else
		var slash = path.lastIndexOf("/");
		if (slash < 0) return "";
		return slash == 0 ? "/" : path.substr(0, slash);
		#end
	}

	static function baseFsName(path:String):String {
		#if windows
		return Path.withoutDirectory(path);
		#else
		var slash = path.lastIndexOf("/");
		return slash < 0 ? path : path.substr(slash + 1);
		#end
	}

	static function contains(items:Array<String>, value:String):Bool {
		for (item in items) if (item == value) return true;
		return false;
	}

	static function containsAncestor(ancestry:ImportSnapshotAncestry, value:String):Bool {
		var current = ancestry;
		while (current != null) {
			if (current.canonicalPath == value) return true;
			current = current.parent;
		}
		return false;
	}

	static function addReason(reasons:Array<String>, reason:String):Void {
		if (!contains(reasons, reason)) reasons.push(reason);
	}

	static function addOmission(omissions:Array<Dynamic>, reasons:Array<String>, path:String,
		code:String, detail:String):Void {
		omissions.push({path: path, reason: code, detail: detail});
		addReason(reasons, code + (path == "" ? "" : ":" + path));
	}

	static function requiredString(value:Dynamic, label:String):String {
		if (!Std.isOfType(value, String)) throw "Snapshot receipt has an invalid " + label + ".";
		return cast value;
	}

	static function validSnapshotRelative(path:String):Bool {
		if (path == null || path == "" || Path.isAbsolute(path)) return false;
		for (part in path.split("/")) if (!validComponent(part)) return false;
		return true;
	}

	static function snapshotPathKey(path:String):String {
		#if windows
		return path.toLowerCase();
		#else
		return path;
		#end
	}

	static function isSha256(value:String):Bool {
		if (value == null || value.length != 64) return false;
		for (index in 0...value.length) {
			var code = value.charCodeAt(index);
			if (!((code >= 48 && code <= 57) || (code >= 65 && code <= 70) || (code >= 97 && code <= 102)))
				return false;
		}
		return true;
	}

	static function receiptSnapshotId(engine:String, directories:Array<String>, files:Array<Dynamic>,
		exclusions:Array<Dynamic>, omissions:Array<Dynamic>, incompleteReasons:Array<Dynamic>):String {
		var hash = new ImportSnapshotSha256();
		var header = Bytes.ofString("ImportSourceSnapshot\n" + RECEIPT_SCHEMA_VERSION + "\n" + engine + "\n");
		hash.update(header, 0, header.length);
		for (directory in directories) hashRecord(hash, "D", directory);
		for (file in files)
			hashRecord(hash, "F", Reflect.field(file, "path") + "\t" + Reflect.field(file, "size")
				+ "\t" + Reflect.field(file, "sha256"));
		for (exclusion in exclusions) {
			var path = requiredString(Reflect.field(exclusion, "path"), "exclusion path");
			var size:Dynamic = Reflect.field(exclusion, "size");
			var reason = requiredString(Reflect.field(exclusion, "reason"), "exclusion reason");
			var detected = requiredString(Reflect.field(exclusion, "detectedHeader"), "exclusion header");
			if (!validSnapshotRelative(path) || !Std.isOfType(size, Int) || (cast size:Int) < 0)
				throw "Snapshot receipt has an invalid exclusion.";
			hashRecord(hash, "X", path + "\t" + size + "\t" + reason + "\t" + detected);
		}
		for (omission in omissions) {
			var path = requiredString(Reflect.field(omission, "path"), "omission path");
			var reason = requiredString(Reflect.field(omission, "reason"), "omission reason");
			var detail = requiredString(Reflect.field(omission, "detail"), "omission detail");
			if (path != "" && !validSnapshotRelative(path)) throw "Snapshot receipt has an invalid omission path.";
			hashRecord(hash, "O", path + "\t" + reason + "\t" + detail);
		}
		for (reason in incompleteReasons) {
			var value = requiredString(reason, "incomplete reason");
			hashRecord(hash, "I", value);
		}
		return hash.digestHex();
	}

	static function verificationCancelled(cancel:Void->Bool):Bool {
		if (cancel == null) return false;
		try return cancel() catch (_:Dynamic) return true;
	}

	static function verificationProgress(onProgress:ImportSourceSnapshotProgress->Void,
		current:String, filesCompleted:Int, filesTotal:Int, bytesCompleted:Float, bytesTotal:Float):Void {
		if (onProgress == null) return;
		try onProgress({phase:"verify", current:current, filesCompleted:filesCompleted,
			filesTotal:filesTotal, bytesCompleted:bytesCompleted, bytesTotal:bytesTotal}) catch (_:Dynamic) {}
	}

	static function verifyFileHash(path:String, relative:String, before:sys.FileStat,
		cancel:Void->Bool, onProgress:ImportSourceSnapshotProgress->Void,
		filesCompleted:Int, filesTotal:Int, bytesCompleted:Float, bytesTotal:Float):String {
		if (!isRegularFileMode(before.mode)) throw "Snapshot entry is not a regular file: " + relative;
		var input:FileInput = null;
		var hash = new ImportSnapshotSha256();
		var buffer = Bytes.alloc(DEFAULT_CHUNK_SIZE);
		var remaining = before.size;
		try {
			input = File.read(path, true);
			while (remaining > 0) {
				if (verificationCancelled(cancel)) throw "Snapshot verification was cancelled.";
				var count = remaining < buffer.length ? remaining : buffer.length;
				var read = input.readBytes(buffer, 0, count);
				if (read != count) throw "Short read while verifying snapshot file: " + relative;
				hash.update(buffer, 0, read);
				remaining -= read;
				verificationProgress(onProgress, relative, filesCompleted, filesTotal,
					bytesCompleted + before.size - remaining, bytesTotal);
			}
			input.close(); input = null;
		} catch (error:Dynamic) {
			if (input != null) try input.close() catch (_:Dynamic) {}
			throw error;
		}
		var after = FileSystem.stat(path);
		if (!isRegularFileMode(after.mode) || after.size != before.size || after.mtime.getTime() != before.mtime.getTime())
			throw "Snapshot file changed during verification: " + relative;
		return hash.digestHex();
	}

	/** POSIX and the Haxe Windows CRT share the S_IFMT type-bit values. */
	static function specialNodeKind(mode:Int):String {
		return switch (mode & 0xF000) {
			case 0x1000: "fifo";
			case 0x2000: "character-device";
			case 0x6000: "block-device";
			case 0xC000: "socket";
			default: "";
		}
	}

	static function isRegularFileMode(mode:Int):Bool {
		var kind = mode & 0xF000;
		// Some non-POSIX targets expose permissions but omit type bits. Keep
		// those usable; reject a known directory or special node at copy time.
		return kind == 0 || kind == 0x8000;
	}

	static function nativeExtension(name:String):String {
		var lower = name.toLowerCase();
		if (lower.endsWith(".dll") || lower.endsWith(".ndll")
			|| lower.endsWith(".dylib") || lower.endsWith(".so") || hasVersionedSoSuffix(lower)
			|| lower.endsWith(".a") || lower.endsWith(".lib"))
			return "native-extension";
		return "";
	}

	static function hasVersionedSoSuffix(name:String):Bool {
		var marker = name.lastIndexOf(".so.");
		if (marker < 0) return false;
		var version = name.substr(marker + 4);
		if (version == "") return false;
		for (index in 0...version.length) {
			var code = version.charCodeAt(index);
			if ((code < 48 || code > 57) && code != 46) return false;
		}
		return true;
	}

	static function nativeHeader(path:String, size:Int):String {
		if (size < 4) return "";
		var length = size < HEADER_PROBE_BYTES ? size : HEADER_PROBE_BYTES;
		var input = File.read(path, true);
		var bytes = Bytes.alloc(length);
		try {
			input.readBytes(bytes, 0, length);
			input.close();
		} catch (error:Dynamic) {
			input.close();
			throw error;
		}
		if (bytes.get(0) == 0x7F && bytes.get(1) == 0x45 && bytes.get(2) == 0x4C && bytes.get(3) == 0x46) return "elf";
		if (starts(bytes, [0xFE, 0xED, 0xFA, 0xCE]) || starts(bytes, [0xCE, 0xFA, 0xED, 0xFE])
			|| starts(bytes, [0xFE, 0xED, 0xFA, 0xCF]) || starts(bytes, [0xCF, 0xFA, 0xED, 0xFE])) return "mach-o";
		if (isFatMachOHeader(path, bytes, size)) return "mach-o-fat";
		if (size >= 8 && bytes.get(0) == 0x21 && bytes.get(1) == 0x3C && bytes.get(2) == 0x61
			&& bytes.get(3) == 0x72 && bytes.get(4) == 0x63 && bytes.get(5) == 0x68
			&& bytes.get(6) == 0x3E && bytes.get(7) == 0x0A) return "archive";
		if (bytes.get(0) == 0x4D && bytes.get(1) == 0x5A && bytes.length >= 64) {
			var offset = bytes.get(0x3C) | (bytes.get(0x3D) << 8) | (bytes.get(0x3E) << 16) | (bytes.get(0x3F) << 24);
			if (offset >= 0 && offset + 4 <= bytes.length && startsAt(bytes, offset, [0x50, 0x45, 0, 0])) return "pe";
		}
		return "";
	}

	static function isFatMachOHeader(path:String, bytes:Bytes, size:Int):Bool {
		var big32 = starts(bytes, [0xCA, 0xFE, 0xBA, 0xBE]);
		var little32 = starts(bytes, [0xBE, 0xBA, 0xFE, 0xCA]);
		var big64 = starts(bytes, [0xCA, 0xFE, 0xBA, 0xBF]);
		var little64 = starts(bytes, [0xBF, 0xBA, 0xFE, 0xCA]);
		if (!big32 && !little32 && !big64 && !little64) return false;
		if (size < 8 || bytes.length < 8) return false;

		var littleEndian = little32 || little64;
		var entryWidth = big64 || little64 ? 32 : 20;
		var architectureCount = readUInt32(bytes, 4, littleEndian);
		var tableEnd = 8 + architectureCount * entryWidth;
		if (architectureCount <= 0 || architectureCount > Math.floor((size - 8) / entryWidth)
			|| tableEnd > bytes.length) return false;

		var input:FileInput = null;
		try {
			input = File.read(path, true);
			var sliceMagic = Bytes.alloc(4);
			var count = Std.int(architectureCount);
			for (index in 0...count) {
				var entryOffset = 8 + index * entryWidth;
				var sliceOffset:Float;
				var sliceSize:Float;
				if (entryWidth == 20) {
					sliceOffset = readUInt32(bytes, entryOffset + 8, littleEndian);
					sliceSize = readUInt32(bytes, entryOffset + 12, littleEndian);
				} else {
					sliceOffset = readUInt64(bytes, entryOffset + 8, littleEndian);
					sliceSize = readUInt64(bytes, entryOffset + 16, littleEndian);
				}
				if (sliceOffset < tableEnd || sliceSize < 4 || sliceOffset + sliceSize > size
					|| sliceOffset > 2147483647.0) {
					input.close();
					return false;
				}
				input.seek(Std.int(sliceOffset), FileSeek.SeekBegin);
				if (input.readBytes(sliceMagic, 0, 4) != 4 || !isThinMachOMagic(sliceMagic)) {
					input.close();
					return false;
				}
			}
			input.close();
			return true;
		} catch (_:Dynamic) {
			if (input != null) try input.close() catch (_:Dynamic) {}
			return false;
		}
	}

	static function readUInt32(bytes:Bytes, offset:Int, littleEndian:Bool):Float {
		if (offset < 0 || offset + 4 > bytes.length) return -1;
		if (littleEndian)
			return bytes.get(offset) + bytes.get(offset + 1) * 256.0
				+ bytes.get(offset + 2) * 65536.0 + bytes.get(offset + 3) * 16777216.0;
		return bytes.get(offset) * 16777216.0 + bytes.get(offset + 1) * 65536.0
			+ bytes.get(offset + 2) * 256.0 + bytes.get(offset + 3);
	}

	static function readUInt64(bytes:Bytes, offset:Int, littleEndian:Bool):Float {
		if (offset < 0 || offset + 8 > bytes.length) return -1;
		var high = readUInt32(bytes, littleEndian ? offset + 4 : offset, littleEndian);
		var low = readUInt32(bytes, littleEndian ? offset : offset + 4, littleEndian);
		return high * 4294967296.0 + low;
	}

	static function isThinMachOMagic(bytes:Bytes):Bool {
		return starts(bytes, [0xFE, 0xED, 0xFA, 0xCE]) || starts(bytes, [0xCE, 0xFA, 0xED, 0xFE])
			|| starts(bytes, [0xFE, 0xED, 0xFA, 0xCF]) || starts(bytes, [0xCF, 0xFA, 0xED, 0xFE]);
	}

	static function starts(bytes:Bytes, header:Array<Int>):Bool return startsAt(bytes, 0, header);
	static function startsAt(bytes:Bytes, offset:Int, header:Array<Int>):Bool {
		if (offset < 0 || offset + header.length > bytes.length) return false;
		for (index in 0...header.length) if (bytes.get(offset + index) != header[index]) return false;
		return true;
	}

	static function uniqueStagePath(cache:String):String {
		for (_ in 0...32) {
			var candidate = joinFsPath(cache, ".staging-" + Std.string(Std.random(0x3FFFFFFF)) + "-" + Std.string(Date.now().getTime()));
			if (!FileSystem.exists(candidate)) return candidate;
		}
		throw "Could not reserve a unique snapshot staging directory.";
	}

	static function createContainedDirectory(stage:String, relative:String):Void {
		if (relative == null || relative == "" || relative == ".") return;
		var parts = relative.split("/");
		var path = stage;
		for (part in parts) {
			if (!validComponent(part)) throw "Invalid relative directory in snapshot plan.";
			path = joinFsPath(path, part);
			if (!FileSystem.exists(path)) FileSystem.createDirectory(path);
			else if (!FileSystem.isDirectory(path)) throw "Snapshot destination path is not a directory.";
		}
	}

	static function createDirectoryRecursive(path:String):Void {
		if (FileSystem.exists(path)) {
			if (!FileSystem.isDirectory(path)) throw "Snapshot cache path exists and is not a directory.";
			return;
		}
		var parent = parentFsPath(path);
		if (parent == "" || parent == path) throw "Cannot create snapshot cache root.";
		createDirectoryRecursive(parent);
		FileSystem.createDirectory(path);
	}

	static function deleteTree(path:String, stageRoot:String):Void {
		if (path == null || path == "" || !FileSystem.exists(path)) return;
		var root:String;
		try root = canonicalPath(stageRoot) catch (_:Dynamic) return;
		var resolved:String;
		try resolved = canonicalPath(path) catch (_:Dynamic) {
			try FileSystem.deleteFile(path) catch (_:Dynamic) {}
			return;
		}
		if (!isWithin(resolved, root)) {
			try FileSystem.deleteFile(path) catch (_:Dynamic) {}
			return;
		}
		if (FileSystem.isDirectory(path)) {
			try {
				for (name in FileSystem.readDirectory(path)) deleteTree(joinFsPath(path, name), stageRoot);
			} catch (_:Dynamic) {}
			try FileSystem.deleteDirectory(path) catch (_:Dynamic) {}
		} else try FileSystem.deleteFile(path) catch (_:Dynamic) {}
	}

	static function validExistingSnapshot(root:String, snapshotId:String):Bool {
		try {
			var receipt:Dynamic = haxe.Json.parse(File.getContent(joinFsPath(root, "receipt.json")));
			return Reflect.field(receipt, "snapshotSchemaVersion") == RECEIPT_SCHEMA_VERSION
				&& Reflect.field(receipt, "snapshotId") == snapshotId;
		} catch (_:Dynamic) return false;
	}

	static function existingSnapshotComplete(root:String):Bool {
		try {
			var receipt:Dynamic = haxe.Json.parse(File.getContent(joinFsPath(root, "receipt.json")));
			var reasons:Dynamic = Reflect.field(receipt, "incompleteReasons");
			return Std.isOfType(reasons, Array) && (cast reasons:Array<Dynamic>).length == 0;
		} catch (_:Dynamic) return false;
	}

	static function hashRecord(hash:ImportSnapshotSha256, kind:String, value:String):Void {
		var bytes = Bytes.ofString(haxe.Json.stringify([kind, value]) + "\n");
		hash.update(bytes, 0, bytes.length);
	}
}

private class ImportSnapshotCancelled {
	public function new() {}
}

/** Independent streaming SHA-256 so snapshot capture does not depend on the
 * updater's private implementation or buffer full packages in memory. */
class ImportSnapshotSha256 {
	static var K:Array<Int> = [
		0x428A2F98,0x71374491,0xB5C0FBCF,0xE9B5DBA5,0x3956C25B,0x59F111F1,0x923F82A4,0xAB1C5ED5,
		0xD807AA98,0x12835B01,0x243185BE,0x550C7DC3,0x72BE5D74,0x80DEB1FE,0x9BDC06A7,0xC19BF174,
		0xE49B69C1,0xEFBE4786,0x0FC19DC6,0x240CA1CC,0x2DE92C6F,0x4A7484AA,0x5CB0A9DC,0x76F988DA,
		0x983E5152,0xA831C66D,0xB00327C8,0xBF597FC7,0xC6E00BF3,0xD5A79147,0x06CA6351,0x14292967,
		0x27B70A85,0x2E1B2138,0x4D2C6DFC,0x53380D13,0x650A7354,0x766A0ABB,0x81C2C92E,0x92722C85,
		0xA2BFE8A1,0xA81A664B,0xC24B8B70,0xC76C51A3,0xD192E819,0xD6990624,0xF40E3585,0x106AA070,
		0x19A4C116,0x1E376C08,0x2748774C,0x34B0BCB5,0x391C0CB3,0x4ED8AA4A,0x5B9CCA4F,0x682E6FF3,
		0x748F82EE,0x78A5636F,0x84C87814,0x8CC70208,0x90BEFFFA,0xA4506CEB,0xBEF9A3F7,0xC67178F2
	];
	var state:Array<Int> = [0x6A09E667,0xBB67AE85,0x3C6EF372,0xA54FF53A,0x510E527F,0x9B05688C,0x1F83D9AB,0x5BE0CD19];
	var block:Bytes = Bytes.alloc(64);
	var buffered:Int = 0;
	var totalBytes:Float = 0;
	var finished:Bool = false;
	public function new() {}
	public function update(bytes:Bytes, position:Int, length:Int):Void {
		if (finished || length < 0 || position < 0 || position + length > bytes.length) throw "Invalid snapshot SHA-256 input.";
		totalBytes += length;
		var offset = 0;
		while (offset < length) {
			var count = length - offset;
			if (count > 64 - buffered) count = 64 - buffered;
			block.blit(buffered, bytes, position + offset, count);
			buffered += count;
			offset += count;
			if (buffered == 64) { compress(block); buffered = 0; }
		}
	}
	public function digestHex():String {
		if (finished) throw "Snapshot SHA-256 was already finalized.";
		finished = true;
		var bitLength = totalBytes * 8.0;
		var bitLow:Float = bitLength % 4294967296.0;
		var bitHigh:Float = Math.floor(bitLength / 4294967296.0);
		block.set(buffered++, 0x80);
		if (buffered > 56) { while (buffered < 64) block.set(buffered++, 0); compress(block); buffered = 0; }
		while (buffered < 56) block.set(buffered++, 0);
		setBigEndian32(block, 56, Std.int(bitHigh));
		setBigEndian32(block, 60, Std.int(bitLow));
		compress(block);
		var out = new StringBuf();
		for (word in state) out.add(StringTools.hex(word, 8).toLowerCase());
		return out.toString();
	}
	function compress(bytes:Bytes):Void {
		var words = new Array<Int>();
		for (index in 0...16) { var p = index * 4; words[index] = (bytes.get(p) << 24) | (bytes.get(p + 1) << 16) | (bytes.get(p + 2) << 8) | bytes.get(p + 3); }
		for (index in 16...64) words[index] = add4(sigma1(words[index - 2]), words[index - 7], sigma0(words[index - 15]), words[index - 16]);
		var a=state[0]; var b=state[1]; var c=state[2]; var d=state[3]; var e=state[4]; var f=state[5]; var g=state[6]; var h=state[7];
		for (index in 0...64) { var t1=add5(h, big1(e), choose(e,f,g), K[index], words[index]); var t2=add2(big0(a), majority(a,b,c)); h=g; g=f; f=e; e=add2(d,t1); d=c; c=b; b=a; a=add2(t1,t2); }
		state[0]=add2(state[0],a); state[1]=add2(state[1],b); state[2]=add2(state[2],c); state[3]=add2(state[3],d);
		state[4]=add2(state[4],e); state[5]=add2(state[5],f); state[6]=add2(state[6],g); state[7]=add2(state[7],h);
	}
	static inline function rotate(value:Int, amount:Int):Int return (value >>> amount) | (value << (32 - amount));
	static inline function sigma0(x:Int):Int return rotate(x,7) ^ rotate(x,18) ^ (x >>> 3);
	static inline function sigma1(x:Int):Int return rotate(x,17) ^ rotate(x,19) ^ (x >>> 10);
	static inline function big0(x:Int):Int return rotate(x,2) ^ rotate(x,13) ^ rotate(x,22);
	static inline function big1(x:Int):Int return rotate(x,6) ^ rotate(x,11) ^ rotate(x,25);
	static inline function choose(x:Int,y:Int,z:Int):Int return (x & y) ^ (~x & z);
	static inline function majority(x:Int,y:Int,z:Int):Int return (x & y) ^ (x & z) ^ (y & z);
	static inline function add2(a:Int,b:Int):Int { var low=(a & 0xFFFF)+(b & 0xFFFF); var high=(a >> 16)+(b >> 16)+(low >> 16); return (high << 16) | (low & 0xFFFF); }
	static inline function add4(a:Int,b:Int,c:Int,d:Int):Int return add2(add2(add2(a,b),c),d);
	static inline function add5(a:Int,b:Int,c:Int,d:Int,e:Int):Int return add2(add4(a,b,c,d),e);
	static function setBigEndian32(bytes:Bytes, position:Int, value:Int):Void { bytes.set(position,value >>> 24); bytes.set(position+1,value >>> 16); bytes.set(position+2,value >>> 8); bytes.set(position+3,value); }
}
