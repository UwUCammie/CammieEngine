import haxe.crypto.Crc32;
import haxe.io.Bytes;
import haxe.io.Eof;
import haxe.io.Input;
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import sys.io.FileInput;

/**
 * Small standalone updater used by the Windows release. It only depends on
 * Haxe's sys APIs, so it runs as an ordinary Windows process under Wine too.
 *
 * Arguments: statusPath exePath installRoot archiveUrl checksumUrl archiveName
 * apiSha256 releaseTag [originatingGamePid]
 */
#if (cpp && windows && !updater_test)
@:buildXml("<target id='haxe' if='HXCPP_MINGW'><lib name='-lcomctl32'/><lib name='-lgdi32'/></target><target id='haxe' unless='HXCPP_MINGW'><lib name='comctl32.lib'/><lib name='gdi32.lib'/></target>")
@:cppFileCode('
#include <windows.h>
#include <commctrl.h>
static HWND cammie_update_window = NULL;
static HWND cammie_update_label = NULL;
static HWND cammie_update_bar = NULL;
static void cammie_update_pump() {
 MSG message;
 while (PeekMessageW(&message, NULL, 0, 0, PM_REMOVE)) {
  TranslateMessage(&message);
  DispatchMessageW(&message);
 }
}
static void cammie_update_progress(const wchar_t* text, int percent) {
 if (!IsWindow(cammie_update_window)) {
  INITCOMMONCONTROLSEX controls = {sizeof(controls), ICC_PROGRESS_CLASS};
  InitCommonControlsEx(&controls);
  cammie_update_window = CreateWindowExW(WS_EX_APPWINDOW, L"STATIC", L"CammieEngine update",
   WS_OVERLAPPED | WS_CAPTION | WS_BORDER | WS_VISIBLE, CW_USEDEFAULT, CW_USEDEFAULT,
   620, 155, NULL, NULL, GetModuleHandleW(NULL), NULL);
  cammie_update_label = CreateWindowExW(0, L"STATIC", L"", WS_CHILD | WS_VISIBLE,
   16, 15, 580, 65, cammie_update_window, NULL, GetModuleHandleW(NULL), NULL);
  cammie_update_bar = CreateWindowExW(0, PROGRESS_CLASSW, L"", WS_CHILD | WS_VISIBLE,
   16, 86, 580, 18, cammie_update_window, NULL, GetModuleHandleW(NULL), NULL);
  SendMessageW(cammie_update_label, WM_SETFONT, (WPARAM)GetStockObject(DEFAULT_GUI_FONT), TRUE);
  SendMessageW(cammie_update_bar, PBM_SETRANGE32, 0, 100);
 }
 SetWindowTextW(cammie_update_label, text);
 SendMessageW(cammie_update_bar, PBM_SETPOS, percent, 0);
 cammie_update_pump();
}
static void cammie_update_close() {
 if (IsWindow(cammie_update_window)) DestroyWindow(cammie_update_window);
 cammie_update_window = NULL;
}
')
#end
class CammieUpdateHelper {
	static inline var CHUNK_SIZE:Int = 65536;
	static inline var PAYLOAD_ROOT:String = "CammieEngine-windows-x64";
	static inline var HELPER_EXE:String = "CammieUpdateHelper.exe";
	static var progressStatusPath:Null<String>;
	static var progressPhase:String = "";
	static var progressStarted:Float = 0;
	static var progressLastWrite:Float = 0;
	static var progressFiles:Int = 0;
	static var progressFile:String = "";

	static function main():Void {
		var args = Sys.args();
		#if updater_test
		if (args.length == 3 && args[0] == "--test-download") {
			try downloadHttps(args[1], args[2]) catch (error:Dynamic) {
				Sys.println("error:" + cleanError(Std.string(error)));
				Sys.exit(1);
			}
			return;
		}
		if (args.length > 0 && args[0] == "--test-install") {
			try runLocalInstallTest(args.slice(1)) catch (error:Dynamic) {
				var message = "error:" + cleanError(Std.string(error));
				if (args.length > 6) try setStatus(args[6], message) catch (_:Dynamic) {}
				Sys.println(message);
				Sys.exit(1);
			}
			return;
		}
		#end
		if (args.length < 8 || args.length > 9) {
			Sys.println("CammieUpdateHelper expects eight arguments and an optional game PID.");
			Sys.exit(2);
			return;
		}
		var statusPath = args[0];
		try {
			run(args);
		} catch (error:Dynamic) {
			var message = cleanError(Std.string(error));
			if (!StringTools.startsWith(message, "Update failed:")) message = "Update failed: " + message;
			try setStatus(statusPath, "error:" + message) catch (_:Dynamic) {}
			#if (cpp && windows && !updater_test)
			closeProgressWindow();
			var detail = message + "\n\nUpdate log: " + statusPath;
			untyped __cpp__('MessageBoxW(NULL, {0}.__WCStr(), L"CammieEngine update failed", MB_OK | MB_ICONERROR)', detail);
			#end
			try Sys.println(message) catch (_:Dynamic) {}
			Sys.exit(1);
		}
	}

	static function run(args:Array<String>):Void {
		var statusPath = args[0];
		var exePath = Path.normalize(args[1]);
		var installRoot = Path.normalize(args[2]);
		var archiveUrl = args[3];
		var checksumUrl = args[4];
		var archiveName = args[5];
		var apiSha256 = args[6].toLowerCase();
		var releaseTag = args[7];
		var originPid = args.length == 9 ? Std.parseInt(args[8]) : 0;
		validateArguments(exePath, installRoot, archiveUrl, checksumUrl, archiveName, apiSha256, releaseTag);

		var workRoot = Path.directory(Path.normalize(statusPath));
		var archivePath = Path.join([workRoot, archiveName]);
		var checksumPath = Path.join([workRoot, "SHA256SUMS.txt"]);
		var stageRoot = Path.join([workRoot, "expanded"]);
		var payloadRoot = Path.join([stageRoot, PAYLOAD_ROOT]);
		var backupRoot = Path.join([workRoot, "backup"]);
		var createdFiles:Array<String> = [];
		var backedUp:Array<String> = [];
		var backupIndex:Map<String, String> = new Map();
		var installing = false;
		var progress = {count:0, failAfter:-1};
		currentInstallRoot = installRoot;
		progressStatusPath = statusPath;

		try {
			setStatus(statusPath, "downloading");
			downloadHttps(archiveUrl, archivePath);
			downloadHttps(checksumUrl, checksumPath);

			beginProgress(statusPath, "verifying");
			var sidecarHash = parseSidecarHash(File.getContent(checksumPath), archiveName);
			if (sidecarHash == null || sidecarHash != apiSha256)
				throw "The release checksum file did not contain the expected ZIP digest.";
			var actualHash = sha256File(archivePath);
			if (actualHash != apiSha256)
				throw "The downloaded ZIP failed its SHA-256 checks.";

			beginProgress(statusPath, "extracting");
			if (FileSystem.exists(stageRoot)) throw "The temporary extraction path already exists.";
			payloadRoot = extractArchive(archivePath, stageRoot, releaseTag);
			if (!FileSystem.exists(exePath) || FileSystem.isDirectory(exePath))
				throw "The installed executable could not be found.";
			setStatus(statusPath, "ready");
			reportProgress(1, 1, true);
			showProgressWindow("Update ready. Close the game to install.", 100);
			waitForGame(exePath, originPid);

			beginProgress(statusPath, "installing");
			var fileTotal = countReleaseFiles(payloadRoot);
			installTotal = fileTotal;
			installing = true;
			copyReleaseTree(payloadRoot, installRoot, "", backupRoot, backupIndex, backedUp, createdFiles, progress);
			var stagedTag = StringTools.trim(File.getContent(Path.join([payloadRoot, "RELEASE_TAG"])));
			if (stagedTag != releaseTag) throw "The release tag changed after package validation.";
			installOne(Path.join([payloadRoot, "RELEASE_TAG"]), Path.join([installRoot, "RELEASE_TAG"]),
				"RELEASE_TAG", backupRoot, backupIndex, backedUp, createdFiles);
			reportProgress(fileTotal, fileTotal, true);
			setStatus(statusPath, "complete");
			installing = false;
			try deleteIfExists(archivePath) catch (_:Dynamic) {}
			try deleteIfExists(checksumPath) catch (_:Dynamic) {}
			try deleteTree(stageRoot) catch (_:Dynamic) {}
			try deleteTree(backupRoot) catch (_:Dynamic) {}
			closeProgressWindow();
			if (promptRestart(releaseTag)) {
				Sys.setCwd(installRoot);
				Sys.command(exePath, []);
			}
		} catch (error:Dynamic) {
			var message = "Update failed: " + cleanError(Std.string(error));
			if (installing) {
				try beginProgress(statusPath, "rolling-back") catch (_:Dynamic) {}
				try {
					rollback(backupRoot, backedUp, createdFiles);
				} catch (rollbackError:Dynamic) {
					message += " Rollback also failed: " + cleanError(Std.string(rollbackError));
				}
			}
			try deleteIfExists(archivePath) catch (_:Dynamic) {}
			try deleteIfExists(checksumPath) catch (_:Dynamic) {}
			try deleteTree(stageRoot) catch (_:Dynamic) {}
			if (!StringTools.contains(message, "Rollback also failed:"))
				try deleteTree(backupRoot) catch (_:Dynamic) {}
			throw message;
		}
	}

	#if updater_test
	/** Local-only integration entrypoint compiled into the Wine test binary, never the release helper. */
	public static function runLocalInstallTest(args:Array<String>):Void {
		if (args.length < 6 || args.length > 7)
			throw "Usage: --test-install ZIP CHECKSUMS INSTALL_ROOT TAG SHA256 STATUS_PATH [FAIL_AFTER_FILES]";
		var archivePath = Path.normalize(args[0]);
		var checksumPath = Path.normalize(args[1]);
		var installRoot = Path.normalize(args[2]);
		var tag = args[3];
		var digest = args[4].toLowerCase();
		var statusPath = Path.normalize(args[5]);
		var failAfter = args.length == 7 ? Std.parseInt(args[6]) : -1;
		var archiveName = "CammieEngine-" + tag + "-windows-x64.zip";
		if (parseSidecarHash(File.getContent(checksumPath), archiveName) != digest || sha256File(archivePath) != digest)
			throw "The local test package failed SHA-256 validation.";
		var workRoot = Path.directory(archivePath);
		var stageRoot = Path.join([workRoot, "cammie-updater-test-expanded"]);
		var backupRoot = Path.join([workRoot, "cammie-updater-test-backup"]);
		if (FileSystem.exists(stageRoot) || FileSystem.exists(backupRoot))
			throw "A previous local updater test did not clean up its temporary folders.";
		beginProgress(statusPath, "extracting");
		var payloadRoot = extractArchive(archivePath, stageRoot, tag);
		var created:Array<String> = [];
		var backedUp:Array<String> = [];
		var backupIndex:Map<String, String> = new Map();
		var progress = {count:0, failAfter:failAfter};
		currentInstallRoot = installRoot;
		beginProgress(statusPath, "installing");
		installTotal = countReleaseFiles(payloadRoot);
		try {
			copyReleaseTree(payloadRoot, installRoot, "", backupRoot, backupIndex, backedUp, created, progress);
			installOne(Path.join([payloadRoot, "RELEASE_TAG"]), Path.join([installRoot, "RELEASE_TAG"]),
				"RELEASE_TAG", backupRoot, backupIndex, backedUp, created);
			reportProgress(installTotal, installTotal, true);
			setStatus(statusPath, "complete");
			deleteTree(stageRoot);
			deleteTree(backupRoot);
		} catch (error:Dynamic) {
			try rollback(backupRoot, backedUp, created) catch (rollbackError:Dynamic)
				throw Std.string(error) + " Rollback also failed: " + Std.string(rollbackError);
			try deleteTree(stageRoot) catch (_:Dynamic) {}
			try deleteTree(backupRoot) catch (_:Dynamic) {}
			try setStatus(statusPath, "error:" + cleanError(Std.string(error))) catch (_:Dynamic) {}
			throw error;
		}
	}
	#end

	/** Narrow validation also protects this executable if it is launched with damaged arguments. */
	public static function validateArguments(exePath:String, installRoot:String, archiveUrl:String,
		checksumUrl:String, archiveName:String, apiSha256:String, releaseTag:String):Void {
		if (!~/^v?[0-9A-Za-z][0-9A-Za-z._-]{0,99}$/.match(releaseTag)
			|| releaseTag == "." || releaseTag == "..") throw "The selected release tag is invalid.";
		var expectedName = "CammieEngine-" + releaseTag + "-windows-x64.zip";
		if (archiveName != expectedName) throw "The selected release archive name is invalid.";
		if (!~/^[0-9a-f]{64}$/.match(apiSha256)) throw "The selected release SHA-256 is invalid.";
		var expectedPrefix = "https://github.com/UwUCammie/CammieEngine/releases/download/" + releaseTag + "/";
		if (!StringTools.startsWith(archiveUrl, expectedPrefix + archiveName)
			|| !StringTools.startsWith(checksumUrl, expectedPrefix + "SHA256SUMS.txt"))
			throw "The selected release download URLs are invalid.";
		if (exePath == null || exePath == "" || installRoot == null || installRoot == "")
			throw "The installed game path is invalid.";
	}

	/** Parse exactly one matching checksum line from SHA256SUMS.txt. */
	public static function parseSidecarHash(contents:String, archiveName:String):Null<String> {
		if (contents == null || archiveName == null) return null;
		var pattern = ~/^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$/;
		var count = 0;
		var digest:Null<String> = null;
		for (line in contents.split("\n")) {
			var trimmed = StringTools.trim(line);
			if (!pattern.match(trimmed)) continue;
			if (pattern.matched(2) != archiveName) continue;
			count++;
			digest = pattern.matched(1).toLowerCase();
		}
		return count == 1 ? digest : null;
	}

	/** Reject paths that could escape the one expected package root. */
	public static function safeEntryPath(rawName:String):Null<{relative:String, directory:Bool}> {
		if (rawName == null || rawName == "" || rawName.indexOf("\\") >= 0
			|| rawName.charAt(0) == "/" || rawName.indexOf(":") >= 0) return null;
		var isDirectory = StringTools.endsWith(rawName, "/");
		var name = isDirectory ? rawName.substr(0, rawName.length - 1) : rawName;
		var parts = name.split("/");
		if (parts.length < 2 || parts[0] != PAYLOAD_ROOT) return null;
		for (part in parts) {
			if (part == "" || part == "." || part == "..") return null;
			for (index in 0...part.length) {
				var code = part.charCodeAt(index);
				if (code != null && (code < 32 || code == 127)) return null;
			}
		}
		return {relative:parts.slice(1).join("/"), directory:isDirectory};
	}

	/** The updater keeps user data and imported files that already exist. */
	public static function isProtectedRelative(relative:String):Bool {
		if (relative == null) return false;
		var first = relative.split("/")[0].toLowerCase();
		return first == "assets" || first == "mods" || first == "imported_mods";
	}

	public static function sha256File(path:String):String {
		var input = File.read(path, true);
		var hash = new CammieUpdateSha256();
		var buffer = Bytes.alloc(CHUNK_SIZE);
		var processed = 0;
		var total = FileSystem.stat(path).size;
		try {
			while (true) {
				var count:Int;
				try count = input.readBytes(buffer, 0, buffer.length) catch (_:Eof) break;
				if (count <= 0) break;
				hash.update(buffer, 0, count);
				processed += count;
				if (progressPhase == "verifying") reportProgress(processed, total);
			}
		} catch (error:Dynamic) {
			input.close();
			throw error;
		}
		input.close();
		if (progressPhase == "verifying") reportProgress(total, total, true);
		return hash.digestHex();
	}

	/** The shared Windows transport streams through URLMon with Wine TLS support. */
	static function downloadHttps(url:String, destination:String):Void
		WindowsUpdateDownload.toFile(url, destination);

	/** Parse local ZIP headers and stream file contents; no archive-sized allocation. */
	public static function extractArchive(archivePath:String, stageRoot:String, releaseTag:String):String {
		var input:FileInput = File.read(archivePath, true);
		var seen:Map<String, Bool> = new Map();
		var fileEntries:Map<String, Bool> = new Map();
		var directoryEntries:Map<String, Bool> = new Map();
		var requiredExe = false;
		var requiredLime = false;
		var requiredHelper = false;
		var requiredAssets = false;
		var releaseTagSeen = false;
		var entries = 0;
		var payloadRoot = Path.join([stageRoot, PAYLOAD_ROOT]);
		var archiveSize = FileSystem.stat(archivePath).size;
		createDirectory(stageRoot);
		try {
			while (true) {
				var start = input.tell();
				var signature:Int;
				try signature = readUInt32(input) catch (_:Eof) break;
				if (signature == 0x02014B50 || signature == 0x06054B50 || signature == 0x06064B50) break;
				if (signature != 0x04034B50) throw "The release ZIP contains an invalid local file header.";
				var version = readUInt16(input);
				var flags = readUInt16(input);
				var method = readUInt16(input);
				readUInt16(input); // DOS time
				readUInt16(input); // DOS date
				var crcExpected = readUInt32(input);
				var compressedSize = readUInt32(input);
				var uncompressedSize = readUInt32(input);
				var nameLength = readUInt16(input);
				var extraLength = readUInt16(input);
				if (version > 63 || (flags & 1) != 0 || (flags & 8) != 0 || (flags & 0x40) != 0)
					throw "The release ZIP uses unsupported or encrypted entry flags.";
				if (method != 0 && method != 8) throw "The release ZIP uses an unsupported compression method.";
				if (compressedSize < 0 || uncompressedSize < 0 || compressedSize == -1 || uncompressedSize == -1)
					throw "The release ZIP uses an unsupported ZIP64 entry.";
				var nameBytes = Bytes.alloc(nameLength);
				readFully(input, nameBytes, 0, nameLength);
				var rawName = nameBytes.toString();
				if ((flags & 0x800) == 0 && !isAsciiBytes(nameBytes))
					throw "The release ZIP contains a non-UTF-8 path without the UTF-8 flag.";
				var safe = safeEntryPath(rawName);
				if (safe == null) throw "The release ZIP contains an unsafe path.";
				var key = safe.relative.toLowerCase();
				if (seen.exists(key)) throw "The release ZIP contains a duplicate path.";
				var components = safe.relative.split("/");
				for (index in 1...components.length) {
					var ancestor = components.slice(0, index).join("/").toLowerCase();
					if (fileEntries.exists(ancestor)) throw "The release ZIP contains a file/directory path collision.";
					directoryEntries.set(ancestor, true);
				}
				if (!safe.directory) {
					if (directoryEntries.exists(key)) throw "The release ZIP contains a file/directory path collision.";
					fileEntries.set(key, true);
				} else directoryEntries.set(key, true);
				seen.set(key, true);
				entries++;
				progressFiles = entries;
				progressFile = safe.relative;
				reportProgress(input.tell(), archiveSize);
				if (entries > 100000) throw "The release ZIP contains too many entries.";
				if (extraLength > 0) {
					var extra = Bytes.alloc(extraLength);
					readFully(input, extra, 0, extraLength);
					if (containsZip64Extra(extra)) throw "The release ZIP uses an unsupported ZIP64 entry.";
				}
				var destination = Path.join([payloadRoot, safe.relative]);
			if (safe.directory) {
				if (compressedSize != 0 || uncompressedSize != 0)
					throw "The release ZIP contains a non-empty directory entry.";
				if (crcExpected != 0) throw "The release ZIP directory entry has an invalid CRC.";
				createDirectory(destination);
				} else {
					var parent = Path.directory(destination);
					createDirectory(parent);
					var output = File.write(destination, true);
						var actualCrc = new CammieUpdateCrc32();
					var written = 0;
					try {
						if (method == 0) {
							var buffer = Bytes.alloc(CHUNK_SIZE);
						var remaining = compressedSize;
						while (remaining > 0) {
							var wanted = remaining < buffer.length ? remaining : buffer.length;
							var count = input.readBytes(buffer, 0, wanted);
							if (count <= 0 || count > remaining) throw "The release ZIP entry is truncated.";
							output.writeBytes(buffer, 0, count);
							actualCrc.update(buffer, 0, count);
							written += count;
								remaining -= count;
								reportProgress(input.tell(), archiveSize);
						}
						} else {
							#if cpp
							// Use hxcpp's zlib with bounded chunks rather than Haxe's
							// byte-at-a-time inflater on large native release archives.
							var inflater = new haxe.zip.Uncompress(-15);
							var outputBuffer = Bytes.alloc(CHUNK_SIZE);
							var compressedRemaining = compressedSize;
							var compressedBuffer = Bytes.alloc(0);
							var compressedPosition = 0;
							try {
								while (true) {
									if (compressedPosition == compressedBuffer.length && compressedRemaining > 0) {
										var count = Std.int(Math.min(compressedRemaining, CHUNK_SIZE));
										compressedBuffer = Bytes.alloc(count);
										readFully(input, compressedBuffer, 0, count);
										compressedRemaining -= count;
										compressedPosition = 0;
									}
									var result = inflater.execute(compressedBuffer, compressedPosition, outputBuffer, 0);
									compressedPosition += result.read;
									if (written + result.write > uncompressedSize)
										throw "The release ZIP entry exceeds its declared size.";
									output.writeBytes(outputBuffer, 0, result.write);
									actualCrc.update(outputBuffer, 0, result.write);
									written += result.write;
									reportProgress(input.tell() - compressedBuffer.length + compressedPosition, archiveSize);
									if (result.done) {
										if (compressedRemaining != 0 || compressedPosition != compressedBuffer.length)
											throw "The release ZIP entry has unused compressed bytes.";
										break;
									}
									if (result.read == 0 && result.write == 0)
										throw "The release ZIP entry is truncated.";
								}
							} catch (error:Dynamic) {
								inflater.close();
								throw error;
							}
							inflater.close();
							#else
							var limited = new CammieUpdateBoundedInput(input, compressedSize);
						var inflater = new haxe.zip.InflateImpl(limited, false, false);
						var buffer = Bytes.alloc(CHUNK_SIZE);
						while (true) {
							var count = inflater.readBytes(buffer, 0, buffer.length);
							if (count == 0) break;
							if (written + count > uncompressedSize) throw "The release ZIP entry exceeds its declared size.";
							output.writeBytes(buffer, 0, count);
							actualCrc.update(buffer, 0, count);
								written += count;
								reportProgress(input.tell(), archiveSize);
						}
							if (limited.remaining != 0) throw "The release ZIP entry has unused compressed bytes.";
							#end
					}
					} catch (error:Dynamic) {
						output.close();
						throw error;
					}
					output.close();
				if (written != uncompressedSize) throw "The release ZIP entry has an incorrect uncompressed size.";
				if (actualCrc.get() != crcExpected) throw "The release ZIP entry failed its CRC check.";
				if (safe.relative == "Funkin.exe") requiredExe = true;
				if (safe.relative == "lime.ndll") requiredLime = true;
				if (safe.relative == HELPER_EXE) requiredHelper = true;
				if (StringTools.startsWith(safe.relative.toLowerCase(), "assets/")) requiredAssets = true;
				if (safe.relative == "RELEASE_TAG") releaseTagSeen = true;
			}
			}
			if (entries == 0 || !requiredExe || !requiredLime || !requiredHelper || !requiredAssets || !releaseTagSeen)
				throw "The release ZIP is missing a required runtime file.";
			var packagedTag = StringTools.trim(File.getContent(Path.join([payloadRoot, "RELEASE_TAG"])));
			if (packagedTag != releaseTag) throw "The release ZIP tag does not match the checked release.";
		} catch (error:Dynamic) {
			try input.close() catch (_:Dynamic) {}
			try deleteTree(stageRoot) catch (_:Dynamic) {}
			throw error;
		}
		input.close();
		reportProgress(archiveSize, archiveSize, true);
		return payloadRoot;
	}

	static function copyReleaseTree(source:String, destination:String, relative:String, backupRoot:String,
		backupIndex:Map<String, String>, backedUp:Array<String>, createdFiles:Array<String>, progress:{count:Int, failAfter:Int}):Void {
		createDirectory(destination);
		var names = FileSystem.readDirectory(source);
		names.sort(Reflect.compare);
		for (name in names) {
			var relativePath = relative == "" ? name : relative + "/" + name;
			if (relativePath == "RELEASE_TAG") continue;
			var sourcePath = Path.join([source, name]);
			var targetPath = Path.join([destination, name]);
			if (FileSystem.isDirectory(sourcePath)) {
				if (FileSystem.exists(targetPath) && !FileSystem.isDirectory(targetPath))
					throw "The installed path conflicts with a release directory: " + relativePath;
				copyReleaseTree(sourcePath, targetPath, relativePath, backupRoot, backupIndex, backedUp, createdFiles, progress);
			} else {
				progressFile = relativePath;
				if (isProtectedRelative(relativePath) && FileSystem.exists(targetPath)) {
					progressFiles++;
					reportProgress(progressFiles, installTotal);
					continue;
				}
				installOne(sourcePath, targetPath, relativePath, backupRoot, backupIndex, backedUp, createdFiles);
				progress.count++;
				progressFiles++;
				reportProgress(progressFiles, installTotal);
				if (progress.failAfter > 0 && progress.count >= progress.failAfter)
					throw "Injected local updater test failure after an installed file.";
			}
		}
	}

	static function installOne(source:String, destination:String, relative:String, backupRoot:String,
		backupIndex:Map<String, String>, backedUp:Array<String>, createdFiles:Array<String>):Void {
		if (!FileSystem.exists(source) || FileSystem.isDirectory(source))
			throw "A release file disappeared during installation: " + relative;
		createDirectory(Path.directory(destination));
		if (FileSystem.exists(destination) && FileSystem.isDirectory(destination))
			throw "The installed path conflicts with a release file: " + relative;
		var key = relative.toLowerCase();
		var oldExists = FileSystem.exists(destination);
		// Windows can keep fonts and other unchanged files open after the game
		// exits. There is no reason to replace an identical file.
		if (oldExists && sameFileContents(source, destination)) return;
		if (oldExists && !backupIndex.exists(key)) {
			var saved = Path.join([backupRoot, relative]);
			copyFile(destination, saved);
			backupIndex.set(key, saved);
		}
		var temporary = uniqueSibling(destination, "cammie-update-tmp");
		try {
			copyFile(source, temporary);
			if (oldExists) {
				deleteIfExists(destination);
				// Record a mutation only after deletion succeeds. A locked file
				// remains intact and must not be touched during rollback.
				if (backedUp.indexOf(relative) < 0) backedUp.push(relative);
			} else if (!backupIndex.exists(key)) createdFiles.push(relative);
			FileSystem.rename(temporary, destination);
		} catch (error:Dynamic) {
			try deleteIfExists(temporary) catch (_:Dynamic) {}
			throw "Could not replace " + relative + ": " + Std.string(error);
		}
	}

	static function sameFileContents(left:String, right:String):Bool {
		if (FileSystem.stat(left).size != FileSystem.stat(right).size) return false;
		var a = File.read(left, true);
		var b:FileInput = null;
		var identical = true;
		try {
			b = File.read(right, true);
			var first = Bytes.alloc(CHUNK_SIZE);
			var second = Bytes.alloc(CHUNK_SIZE);
			var remaining = FileSystem.stat(left).size;
			while (remaining > 0) {
				var count = Std.int(Math.min(remaining, CHUNK_SIZE));
				readFully(a, first, 0, count);
				readFully(b, second, 0, count);
				for (index in 0...count) if (first.get(index) != second.get(index)) {
					identical = false;
					break;
				}
				if (!identical) break;
				remaining -= count;
			}
		} catch (error:Dynamic) {
			a.close();
			if (b != null) b.close();
			throw error;
		}
		a.close();
		b.close();
		return identical;
	}

	static function copyFile(sourcePath:String, destinationPath:String):Void {
		createDirectory(Path.directory(destinationPath));
		var input = File.read(sourcePath, true);
		var output = File.write(destinationPath, true);
		var buffer = Bytes.alloc(CHUNK_SIZE);
		try {
			while (true) {
				var count:Int;
				try count = input.readBytes(buffer, 0, buffer.length) catch (_:Eof) break;
				if (count <= 0) break;
				output.writeBytes(buffer, 0, count);
			}
		} catch (error:Dynamic) {
			input.close();
			output.close();
			throw error;
		}
		input.close();
		output.close();
	}

	static function rollback(backupRoot:String, backedUp:Array<String>, createdFiles:Array<String>):Void {
		var firstError:Null<String> = null;
		var total = createdFiles.length + backedUp.length;
		var completed = 0;
		for (relative in createdFiles) {
			progressFile = relative;
			try {
				var path = Path.join([currentInstallRoot, relative]);
				if (FileSystem.exists(path) && !FileSystem.isDirectory(path)) deleteIfExists(path);
			} catch (error:Dynamic) if (firstError == null) firstError = Std.string(error);
			reportProgress(++completed, total);
		}
		var index = backedUp.length - 1;
		while (index >= 0) {
			var relative = backedUp[index--];
			progressFile = relative;
			try {
				var saved = Path.join([backupRoot, relative]);
				var destination = Path.join([currentInstallRoot, relative]);
				if (!FileSystem.exists(saved)) throw "Missing backup for " + relative;
				if (FileSystem.exists(destination) && !FileSystem.isDirectory(destination)
					&& sameFileContents(saved, destination)) {
					reportProgress(++completed, total);
					continue;
				}
				createDirectory(Path.directory(destination));
				if (FileSystem.exists(destination) && !FileSystem.isDirectory(destination)) deleteIfExists(destination);
				var temporary = uniqueSibling(destination, "cammie-rollback-tmp");
				copyFile(saved, temporary);
				FileSystem.rename(temporary, destination);
			} catch (error:Dynamic) if (firstError == null) firstError = Std.string(error);
			reportProgress(++completed, total);
		}
		reportProgress(completed, total, true);
		if (firstError != null) throw firstError;
	}

	static var currentInstallRoot:String;

	static function uniqueSibling(destination:String, suffix:String):String {
		var candidate:String;
		do {
			candidate = destination + "." + suffix + "-" + Std.string(Std.random(1000000000));
		} while (FileSystem.exists(candidate));
		return candidate;
	}

	static function waitForGame(exePath:String, pid:Null<Int>):Void {
		if (pid != null && pid > 0) {
			while (true) {
				var running = processStatus(pid);
				if (running == false) return;
				if (running == true) {
					pumpProgressWindow();
					Sys.sleep(0.5);
				} else break;
			}
		}
		while (isExecutableLocked(exePath)) {
			pumpProgressWindow();
			Sys.sleep(0.5);
		}
	}

	static function processStatus(pid:Int):Null<Bool> {
		#if cpp
		var handle = CammieUpdateWin32.openProcess(0x00100000, 0, pid);
		if (handle == null) return null;
		var result = CammieUpdateWin32.waitForSingleObject(handle, 0);
		CammieUpdateWin32.closeHandle(handle);
		if (result == 258) return true;
		if (result == 0) return false;
		return null;
		#else
		return null;
		#end
	}

	static function isExecutableLocked(exePath:String):Bool {
		#if cpp
		var handle = CammieUpdateWin32.openExclusive(exePath);
		if (handle == null || handle == CammieUpdateWin32.invalidHandle()) return true;
		CammieUpdateWin32.closeHandle(handle);
		return false;
		#else
		return false;
		#end
	}

	static var installTotal:Int = 0;

	static function countReleaseFiles(root:String):Int {
		var total = 0;
		for (name in FileSystem.readDirectory(root)) {
			var path = Path.join([root, name]);
			total += FileSystem.isDirectory(path) ? countReleaseFiles(path) : 1;
		}
		return total;
	}

	static function beginProgress(path:String, phase:String):Void {
		progressStatusPath = path;
		progressPhase = phase;
		progressStarted = haxe.Timer.stamp();
		progressLastWrite = 0;
		progressFiles = 0;
		progressFile = "";
		setStatus(path, phase);
		reportProgress(0, 0, true);
	}

	/** Keep status.txt compatible with installed older games; richer progress
	 * lives beside it and is also shown by the helper's own Windows window. */
	static function reportProgress(completed:Float, total:Float, force:Bool = false):Void {
		if (progressStatusPath == null) return;
		var now = haxe.Timer.stamp();
		if (!force && now - progressLastWrite < 0.2) return;
		progressLastWrite = now;
		var elapsed = Math.max(0, now - progressStarted);
		var percent = total > 0 ? Std.int(Math.max(0, Math.min(1, completed / total)) * 100) : 0;
		var data = {phase:progressPhase, completed:completed, total:total, files:progressFiles,
			currentFile:progressFile, elapsed:elapsed, updatedAt:Date.now().getTime()};
		try File.saveContent(Path.join([Path.directory(progressStatusPath), "progress.json"]),
			haxe.Json.stringify(data)) catch (_:Dynamic) {}
		var label = switch (progressPhase) {
			case "verifying": "Verifying package";
			case "extracting": "Preparing files";
			case "installing": "Installing update";
			case "rolling-back": "Restoring previous version";
			default: progressPhase;
		};
		label += " - " + percent + "% | " + Std.int(elapsed) + "s elapsed";
		if (elapsed >= 2 && completed > 0 && completed < total)
			label += " | about " + Std.int(elapsed * (total - completed) / completed) + "s left";
		if (progressFile != "") label += "\n" + progressFiles + " files | " + progressFile;
		showProgressWindow(label, percent);
	}

	static function showProgressWindow(label:String, percent:Int):Void {
		#if (cpp && windows && !updater_test)
		untyped __cpp__('cammie_update_progress({0}.__WCStr(), {1})', label, percent);
		#end
	}

	static function pumpProgressWindow():Void {
		#if (cpp && windows && !updater_test)
		untyped __cpp__('cammie_update_pump()');
		#end
	}

	static function closeProgressWindow():Void {
		#if (cpp && windows && !updater_test)
		untyped __cpp__('cammie_update_close()');
		#end
	}

	static function setStatus(path:String, value:String):Void File.saveContent(path, value + "\n");

	static function createDirectory(path:String):Void {
		if (path == null || path == "" || FileSystem.exists(path)) {
			if (path != null && path != "" && !FileSystem.isDirectory(path)) throw "A file blocks directory creation: " + path;
			return;
		}
		var parent = Path.directory(path);
		if (parent != null && parent != path && !FileSystem.exists(parent)) createDirectory(parent);
		FileSystem.createDirectory(path);
	}

	static function deleteIfExists(path:String):Void {
		if (FileSystem.exists(path) && !FileSystem.isDirectory(path)) FileSystem.deleteFile(path);
	}

	static function deleteTree(path:String):Void {
		if (!FileSystem.exists(path)) return;
		if (FileSystem.isDirectory(path)) {
			for (name in FileSystem.readDirectory(path)) deleteTree(Path.join([path, name]));
			FileSystem.deleteDirectory(path);
		} else FileSystem.deleteFile(path);
	}

	static function readUInt16(input:Input):Int {
		var a = input.readByte();
		var b = input.readByte();
		return a | (b << 8);
	}

	static function readUInt32(input:Input):Int {
		var a = input.readByte();
		var b = input.readByte();
		var c = input.readByte();
		var d = input.readByte();
		return a | (b << 8) | (c << 16) | (d << 24);
	}

	static function readFully(input:Input, bytes:Bytes, position:Int, length:Int):Void {
		var offset = 0;
		while (offset < length) {
			var count = input.readBytes(bytes, position + offset, length - offset);
			if (count <= 0) throw new Eof();
			offset += count;
		}
	}

	static function isAsciiBytes(bytes:Bytes):Bool {
		for (i in 0...bytes.length) if (bytes.get(i) > 127) return false;
		return true;
	}

	static function containsZip64Extra(extra:Bytes):Bool {
		var position = 0;
		while (position + 4 <= extra.length) {
			var id = extra.get(position) | (extra.get(position + 1) << 8);
			var size = extra.get(position + 2) | (extra.get(position + 3) << 8);
			position += 4;
			if (position + size > extra.length) throw "The release ZIP contains a malformed extra field.";
			if (id == 0x0001) return true;
			position += size;
		}
		return position == extra.length ? false : throw "The release ZIP contains a malformed extra field.";
	}

	static function cleanError(message:String):String {
		if (message == null || message == "") return "Unknown updater error.";
		return StringTools.replace(StringTools.replace(message, "\r", " "), "\n", " ");
	}

	static function promptRestart(releaseTag:String):Bool {
		#if cpp
		var message = "CammieEngine " + releaseTag + " is installed. Start it now?";
		return CammieUpdateWin32.messageBox(null, cast message, "CammieEngine update", 0x00000024) == 6;
		#else
		return false;
		#end
	}
}

/** Lookup-table CRC avoids eight bit operations per extracted byte. */
private class CammieUpdateCrc32 {
	static var table:Array<Int> = makeTable();
	var crc:Int = -1;
	public function new() {}
	static function makeTable():Array<Int> {
		var result = [];
		for (index in 0...256) {
			var value = index;
			for (_ in 0...8) value = (value >>> 1) ^ (-(value & 1) & 0xEDB88320);
			result.push(value);
		}
		return result;
	}
	public function update(bytes:Bytes, position:Int, length:Int):Void {
		for (index in position...position + length)
			crc = (crc >>> 8) ^ table[(crc ^ bytes.get(index)) & 255];
	}
	public function get():Int return crc ^ -1;
}

private class CammieUpdateBoundedInput extends Input {
	var source:Input;
	public var remaining:Int;

	public function new(source:Input, length:Int) {
		this.source = source;
		remaining = length;
	}

	public override function readByte():Int {
		if (remaining <= 0) throw new Eof();
		remaining--;
		return source.readByte();
	}

	public override function readBytes(bytes:Bytes, position:Int, length:Int):Int {
		if (length <= 0) return 0;
		if (remaining <= 0) throw new Eof();
		var wanted = length < remaining ? length : remaining;
		var count = source.readBytes(bytes, position, wanted);
		if (count > wanted) throw "Invalid bounded stream read.";
		remaining -= count;
		return count;
	}
}

/** Incremental SHA-256 with a fixed 64-byte working block. */
private class CammieUpdateSha256 {
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
	var words:Array<Int> = [for (_ in 0...64) 0];
	var buffered:Int = 0;
	var totalBytes:Int = 0;
	var finished:Bool = false;

	public function new() {}

	public function update(bytes:Bytes, position:Int, length:Int):Void {
		if (finished) throw "SHA-256 digest was already finalized.";
		if (length < 0 || position < 0 || position + length > bytes.length) throw "Invalid SHA-256 input range.";
		totalBytes += length;
		var offset = 0;
		while (offset < length) {
			var count = length - offset;
			if (count > 64 - buffered) count = 64 - buffered;
			block.blit(buffered, bytes, position + offset, count);
			buffered += count;
			offset += count;
			if (buffered == 64) {
				compress(block);
				buffered = 0;
			}
		}
	}

	public function digestHex():String {
		if (finished) throw "SHA-256 digest was already finalized.";
		finished = true;
		var bitLow = totalBytes << 3;
		var bitHigh = totalBytes >>> 29;
		block.set(buffered++, 0x80);
		if (buffered > 56) {
			while (buffered < 64) block.set(buffered++, 0);
			compress(block);
			buffered = 0;
		}
		while (buffered < 56) block.set(buffered++, 0);
		setBigEndian32(block, 56, bitHigh);
		setBigEndian32(block, 60, bitLow);
		compress(block);
		var out = new StringBuf();
		for (word in state) out.add(StringTools.hex(word, 8).toLowerCase());
		return out.toString();
	}

	function compress(bytes:Bytes):Void {
		for (index in 0...16) {
			var position = index * 4;
			words[index] = (bytes.get(position) << 24) | (bytes.get(position + 1) << 16)
				| (bytes.get(position + 2) << 8) | bytes.get(position + 3);
		}
		for (index in 16...64)
			words[index] = add4(smallSigma1(words[index - 2]), words[index - 7], smallSigma0(words[index - 15]), words[index - 16]);
		var a = state[0]; var b = state[1]; var c = state[2]; var d = state[3];
		var e = state[4]; var f = state[5]; var g = state[6]; var h = state[7];
		for (index in 0...64) {
			var t1 = add5(h, bigSigma1(e), choose(e, f, g), K[index], words[index]);
			var t2 = add2(bigSigma0(a), majority(a, b, c));
			h = g; g = f; f = e; e = add2(d, t1); d = c; c = b; b = a; a = add2(t1, t2);
		}
		state[0] = add2(state[0], a); state[1] = add2(state[1], b);
		state[2] = add2(state[2], c); state[3] = add2(state[3], d);
		state[4] = add2(state[4], e); state[5] = add2(state[5], f);
		state[6] = add2(state[6], g); state[7] = add2(state[7], h);
	}

	static inline function rotate(value:Int, amount:Int):Int return (value >>> amount) | (value << (32 - amount));
	static inline function smallSigma0(x:Int):Int return rotate(x, 7) ^ rotate(x, 18) ^ (x >>> 3);
	static inline function smallSigma1(x:Int):Int return rotate(x, 17) ^ rotate(x, 19) ^ (x >>> 10);
	static inline function bigSigma0(x:Int):Int return rotate(x, 2) ^ rotate(x, 13) ^ rotate(x, 22);
	static inline function bigSigma1(x:Int):Int return rotate(x, 6) ^ rotate(x, 11) ^ rotate(x, 25);
	static inline function choose(x:Int, y:Int, z:Int):Int return (x & y) ^ (~x & z);
	static inline function majority(x:Int, y:Int, z:Int):Int return (x & y) ^ (x & z) ^ (y & z);
	static inline function add2(a:Int, b:Int):Int {
		var low = (a & 0xFFFF) + (b & 0xFFFF);
		var high = (a >> 16) + (b >> 16) + (low >> 16);
		return (high << 16) | (low & 0xFFFF);
	}
	static inline function add4(a:Int, b:Int, c:Int, d:Int):Int return add2(add2(add2(a, b), c), d);
	static inline function add5(a:Int, b:Int, c:Int, d:Int, e:Int):Int return add2(add4(a, b, c, d), e);
	static function setBigEndian32(bytes:Bytes, position:Int, value:Int):Void {
		bytes.set(position, value >>> 24);
		bytes.set(position + 1, value >>> 16);
		bytes.set(position + 2, value >>> 8);
		bytes.set(position + 3, value);
	}
}

#if cpp
@:buildXml("<target id='haxe' if='HXCPP_MINGW'><lib name='-luser32'/></target><target id='haxe' unless='HXCPP_MINGW'><lib name='user32.lib'/></target>")
@:include("windows.h")
extern class CammieUpdateWin32 {
	@:native("OpenProcess") static function openProcess(access:cpp.UInt32, inherit:Int, processId:cpp.UInt32):cpp.RawPointer<cpp.Void>;
	@:native("WaitForSingleObject") static function waitForSingleObject(handle:cpp.RawPointer<cpp.Void>, milliseconds:cpp.UInt32):cpp.UInt32;
	@:native("CloseHandle") static function closeHandle(handle:cpp.RawPointer<cpp.Void>):Int;
	@:native("MessageBoxA") static function messageBox(window:cpp.RawPointer<cpp.Void>, text:cpp.ConstCharStar,
		caption:cpp.ConstCharStar, style:cpp.UInt32):Int;
	static inline function invalidHandle():cpp.RawPointer<cpp.Void> return cast -1;
	static inline function openExclusive(path:String):cpp.RawPointer<cpp.Void>
		return untyped __cpp__('CreateFileW({0}.__WCStr(), GENERIC_READ, 0, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL)', path);
}
#end
