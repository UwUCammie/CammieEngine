package;

import haxe.Json;

#if (sys && windows)
import haxe.io.Path;
import sys.FileSystem;
import sys.io.File;
import sys.thread.Deque;
import sys.thread.Thread;
#end

typedef UpdateRelease = {
	var tag:String;
	var archiveName:String;
	var archiveUrl:String;
	var checksumUrl:String;
	var sha256:String;
	var sizeBytes:Int;
}

typedef UpdateCheckResult = {
	var requestId:Int;
	var currentTag:String;
	var latest:Null<UpdateRelease>;
	var updateAvailable:Bool;
	var error:Null<String>;
}

typedef UpdateStartResult = {
	var statusPath:Null<String>;
	var error:Null<String>;
}

typedef UpdateProgress = {
	var status:String;
	var label:String;
	var fraction:Float;
	@:optional var detail:String;
	@:optional var indeterminate:Bool;
}

/** User-initiated updater for the published Windows x64 ZIP releases. */
#if (cpp && windows)
@:headerCode('extern "C" __declspec(dllimport) unsigned long __stdcall GetCurrentProcessId(void);')
#end
class UpdateChecker {
	public static inline var RELEASES_API:String = 'https://api.github.com/repos/UwUCammie/CammieEngine/releases?per_page=20';
	public static inline var RELEASE_DOWNLOAD_ROOT:String = 'https://github.com/UwUCammie/CammieEngine/releases/download/';
	static var nextRequestId:Int = 0;
	#if (sys && windows)
	static var checkResults:Deque<UpdateCheckResult> = new Deque<UpdateCheckResult>();
	static var activeStatusPath:Null<String>;
	static var activeRelease:Null<UpdateRelease>;
	#end

	public static function versionFromTag(tag:String):Null<Array<Dynamic>> {
		if (tag == null) return null;
		var match = ~/^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?$/;
		if (!match.match(StringTools.trim(tag))) return null;
		var prerelease = match.matched(4);
		return [Std.parseInt(match.matched(1)), Std.parseInt(match.matched(2)),
			Std.parseInt(match.matched(3)), prerelease == null ? '' : prerelease];
	}

	/** Compare release tags by SemVer precedence. Invalid or missing installed
	 * tags are treated as unknown so the settings screen can offer the latest
	 * package with an explicit "unknown" label. */
	public static function compareTags(left:String, right:String):Null<Int> {
		var a = versionFromTag(left);
		var b = versionFromTag(right);
		if (a == null || b == null) return null;
		for (index in 0...3) {
			var difference:Int = cast a[index] - cast b[index];
			if (difference != 0) return difference < 0 ? -1 : 1;
		}
		var aPre:String = cast a[3];
		var bPre:String = cast b[3];
		if (aPre == bPre) return 0;
		if (aPre == '') return 1;
		if (bPre == '') return -1;
		return comparePrerelease(aPre, bPre);
	}

	public static function isNewerTag(installedTag:String, latestTag:String):Bool {
		if (installedTag == null || installedTag == '' || installedTag == 'unknown') return true;
		var comparison = compareTags(installedTag, latestTag);
		return comparison == null || comparison < 0;
	}

	public static function archiveFileName(tag:String):Null<String> {
		if (versionFromTag(tag) == null || !isSafeTag(tag)) return null;
		return 'CammieEngine-' + tag + '-windows-x64.zip';
	}

	/** Pick the newest non-draft release with the expected Windows ZIP and a
	 * GitHub SHA-256 asset digest. GitHub's release list includes prereleases. */
	public static function parseLatestRelease(body:String):Null<UpdateRelease> {
		var releases:Dynamic = Json.parse(body);
		if (!Std.isOfType(releases, Array)) throw 'GitHub returned a release list in an unexpected format';
		var selected:Null<UpdateRelease> = null;
		for (candidate in (cast releases:Array<Dynamic>)) {
			if (candidate == null || Reflect.field(candidate, 'draft') == true) continue;
			var tag:Dynamic = Reflect.field(candidate, 'tag_name');
			if (!Std.isOfType(tag, String) || versionFromTag(cast tag) == null) continue;
			var archiveName = archiveFileName(cast tag);
			if (archiveName == null) continue;
			var assets:Dynamic = Reflect.field(candidate, 'assets');
			if (!Std.isOfType(assets, Array)) continue;
			var hasArchive = false;
			var hasChecksum = false;
			var digest:Null<String> = null;
			var sizeBytes:Int = 0;
			for (asset in (cast assets:Array<Dynamic>)) {
				var name:Dynamic = Reflect.field(asset, 'name');
				if (!Std.isOfType(name, String)) continue;
				if (name == archiveName) {
					hasArchive = true;
					var rawDigest:Dynamic = Reflect.field(asset, 'digest');
					if (Std.isOfType(rawDigest, String)) digest = parseSha256(cast rawDigest);
					var rawSize:Dynamic = Reflect.field(asset, 'size');
					if (Std.isOfType(rawSize, Int)) sizeBytes = cast rawSize;
					else if (Std.isOfType(rawSize, Float) && (cast rawSize:Float) > 0)
						sizeBytes = Std.int(Math.min(cast rawSize, 2147483647));
				}
				if (name == 'SHA256SUMS.txt') hasChecksum = true;
			}
			if (!hasArchive || !hasChecksum || digest == null) continue;
			var release:UpdateRelease = {
				tag:cast tag,
				archiveName:archiveName,
				archiveUrl:releaseAssetUrl(cast tag, archiveName),
				checksumUrl:releaseAssetUrl(cast tag, 'SHA256SUMS.txt'),
				sha256:digest,
				sizeBytes:sizeBytes
			};
			if (selected == null || compareTags(release.tag, selected.tag) > 0)
				selected = release;
		}
		return selected;
	}

	public static function parseSha256(raw:String):Null<String> {
		if (raw == null) return null;
		var match = ~/^(?:sha256:)?([0-9a-fA-F]{64})$/;
		if (!match.match(StringTools.trim(raw))) return null;
		return match.matched(1).toLowerCase();
	}

	public static function formatSize(sizeBytes:Int):String {
		if (sizeBytes <= 0) return 'size unavailable';
		var sizeMb:Float = sizeBytes / 1048576.0;
		if (sizeMb < 1024) return Std.string(Math.round(sizeMb)) + ' MB';
		return Std.string(Math.round(sizeMb / 102.4) / 10) + ' GB';
	}

	#if (sys && windows)
	public static function installedReleaseTag():String {
		try {
			var root = Path.directory(FileSystem.fullPath(Sys.programPath()));
			var releaseTagPath = Path.join([root, 'RELEASE_TAG']);
			if (FileSystem.exists(releaseTagPath) && !FileSystem.isDirectory(releaseTagPath)) {
				var tag = StringTools.trim(File.getContent(releaseTagPath));
				if (versionFromTag(tag) != null && isSafeTag(tag)) return tag;
			}
		} catch (error:Dynamic) {}
		return 'unknown';
	}

	public static function beginCheck(currentTag:String):Int {
		var requestId = ++nextRequestId;
		var queue = checkResults;
		Thread.create(function() {
			var result:UpdateCheckResult;
			try {
				var body = WindowsUpdateDownload.getText(RELEASES_API);
				var latest = parseLatestRelease(body);
				result = {
					requestId:requestId,
					currentTag:currentTag == null || currentTag == '' ? 'unknown' : currentTag,
					latest:latest,
					updateAvailable:latest != null && isNewerTag(currentTag, latest.tag),
					error:latest == null ? 'No downloadable Windows x64 release with a verified checksum was found.' : null
				};
			} catch (error:Dynamic) {
				result = {requestId:requestId, currentTag:currentTag, latest:null,
					updateAvailable:false, error:Std.string(error)};
			}
			queue.add(result);
		});
		return requestId;
	}

	public static function takeCheckResult(requestId:Int):Null<UpdateCheckResult> {
		var count = 0;
		while (count < 32) {
			var result = checkResults.pop(false);
			if (result == null) return null;
			if (result.requestId == requestId) return result;
			count++;
		}
		return null;
	}

	public static function startInstall(release:UpdateRelease):UpdateStartResult {
		if (release == null || archiveFileName(release.tag) != release.archiveName
			|| parseSha256(release.sha256) == null
			|| release.archiveUrl != releaseAssetUrl(release.tag, release.archiveName)
			|| release.checksumUrl != releaseAssetUrl(release.tag, 'SHA256SUMS.txt'))
			return {statusPath:null, error:'The selected release information is invalid.'};

		try {
			var installRoot = Path.directory(FileSystem.fullPath(Sys.programPath()));
			var helperSource = Path.join([installRoot, 'CammieUpdateHelper.exe']);
			if (!FileSystem.exists(helperSource) || FileSystem.isDirectory(helperSource))
				return {statusPath:null, error:'This build has no bundled update helper. Install the current Windows ZIP once to enable in-app updates.'};
			var writeProbe = Path.join([installRoot,
				'.cammie-update-write-test-' + Std.string(Std.random(1000000000))]);
			if (FileSystem.exists(writeProbe))
				return {statusPath:null, error:'Could not reserve an update write test file.'};
			File.saveContent(writeProbe, 'write test');
			FileSystem.deleteFile(writeProbe);
			var tempRoot = Sys.getEnv('TEMP');
			if (tempRoot == null || tempRoot == '') tempRoot = Sys.getCwd();
			var job = 'cammie-update-' + Std.string(Std.int(Date.now().getTime())) + '-' + Std.string(Std.random(1000000));
			var workRoot = Path.join([tempRoot, job]);
			FileSystem.createDirectory(workRoot);
			var statusPath = Path.join([workRoot, 'status.txt']);
			var helperPath = Path.join([workRoot, 'CammieUpdateHelper.exe']);
			File.copy(helperSource, helperPath);
			// hxcpp's MinGW executable may need one of these DLLs beside it.
			// Copy only runtime libraries, never game assets or local user data.
			for (name in ['libc++.dll', 'libunwind.dll', 'libwinpthread-1.dll',
				'libstdc++-6.dll', 'libgcc_s_seh-1.dll']) {
				var source = Path.join([installRoot, name]);
				if (FileSystem.exists(source) && !FileSystem.isDirectory(source))
					File.copy(source, Path.join([workRoot, name]));
			}
			var process = new sys.io.Process(helperPath, [statusPath, Sys.programPath(), installRoot,
				release.archiveUrl, release.checksumUrl, release.archiveName,
				release.sha256, release.tag, Std.string(gamePid())]);
			process.close();
			activeStatusPath = statusPath;
			activeRelease = release;
			return {statusPath:statusPath, error:null};
		} catch (error:Dynamic) {
			return {statusPath:null, error:Std.string(error)};
		}
	}

	public static function readInstallStatus(statusPath:String):Null<String> {
		if (statusPath == null || !FileSystem.exists(statusPath)) return null;
		try return StringTools.trim(File.getContent(statusPath)) catch (error:Dynamic) return null;
	}

	/** Poll the same helper job from any browsing state. Download bytes are read
	 * from its temporary ZIP; the helper remains responsible for verification. */
	public static function installProgress():Null<UpdateProgress> {
		if (activeStatusPath == null || activeRelease == null) return null;
		var status = readInstallStatus(activeStatusPath);
		if (status == null) status = 'starting';
		if (StringTools.startsWith(status, 'error:'))
			return {status:status, label:status.substr('error:'.length), fraction:0};
		if (status == 'complete')
			return {status:status, label:'Update installed', fraction:1};
		if (status == 'verifying' || status == 'extracting' || status == 'installing' || status == 'rolling-back') {
			var label = switch (status) {
				case 'verifying': 'Verifying update';
				case 'extracting': 'Preparing files';
				case 'installing': 'Installing update';
				default: 'Restoring previous version';
			};
			try {
				var path = Path.join([Path.directory(activeStatusPath), 'progress.json']);
				var record:Dynamic = Json.parse(File.getContent(path));
				if (record.phase == status && Std.isOfType(record.completed, Float)
					&& Std.isOfType(record.total, Float) && record.total > 0
					&& Math.isFinite(record.completed) && Math.isFinite(record.total)) {
					var fraction = Math.max(0, Math.min(1, record.completed / record.total));
					var elapsed:Float = Std.isOfType(record.elapsed, Float) && Math.isFinite(record.elapsed)
						? Math.max(0, record.elapsed) : 0;
					var detail = Std.int(elapsed) + 's elapsed';
					if (elapsed >= 2 && fraction > 0 && fraction < 1)
						detail += ' | about ' + Std.int(elapsed * (1 - fraction) / fraction) + 's left';
					if (Std.isOfType(record.files, Int) && record.files > 0)
						detail += ' | ' + record.files + ' files';
					if (Std.isOfType(record.updatedAt, Float)
						&& Date.now().getTime() - record.updatedAt > 5000)
						detail += ' | waiting for progress';
					return {status:status, label:label + ' — ' + Std.int(fraction * 100) + '%',
						fraction:fraction, detail:detail, indeterminate:false};
				}
			} catch (_:Dynamic) {}
			return {status:status, label:label + ' ' + activeRelease.tag,
				fraction:0, detail:'Waiting for progress...', indeterminate:true};
		}
		if (status == 'downloading' || status == 'starting') {
			var fraction = 0.0;
			if (activeRelease.sizeBytes > 0) try {
				var archivePath = Path.join([Path.directory(activeStatusPath), activeRelease.archiveName]);
				if (FileSystem.exists(archivePath))
					fraction = Math.max(0, Math.min(1, FileSystem.stat(archivePath).size / activeRelease.sizeBytes));
			} catch (_:Dynamic) {}
			var percent = Std.int(fraction * 100);
			return {status:status, label:'Downloading update ' + activeRelease.tag + ' — ' + percent + '%', fraction:fraction};
		}
		return switch (status) {
			case 'ready': {status:status, label:'Update ready — installs after exit', fraction:1};
			default: {status:status, label:'Update status: ' + status, fraction:0};
		};
	}

	public static function activeInstallStatusPath():Null<String> return activeStatusPath;

	public static function clearInstallProgress():Void {
		activeStatusPath = null;
		activeRelease = null;
	}

	static function gamePid():Int {
		#if cpp
		return untyped __cpp__('GetCurrentProcessId()');
		#else
		return 0;
		#end
	}

	#end

	static function releaseAssetUrl(tag:String, name:String):String
		return RELEASE_DOWNLOAD_ROOT + StringTools.urlEncode(tag) + '/' + StringTools.urlEncode(name);

	static function isSafeTag(tag:String):Bool
		return tag != null && tag != '.' && tag != '..' && ~/^v?[0-9A-Za-z][0-9A-Za-z._-]{0,99}$/.match(tag);

	static function comparePrerelease(left:String, right:String):Int {
		var a = left.split('.');
		var b = right.split('.');
		var count = Std.int(Math.min(a.length, b.length));
		for (index in 0...count) {
			if (a[index] == b[index]) continue;
			var aNumber = ~/^[0-9]+$/.match(a[index]);
			var bNumber = ~/^[0-9]+$/.match(b[index]);
			if (aNumber && bNumber) {
				var an = Std.parseInt(a[index]);
				var bn = Std.parseInt(b[index]);
				if (an != bn) return an < bn ? -1 : 1;
			} else if (aNumber != bNumber) return aNumber ? -1 : 1;
			else return a[index] < b[index] ? -1 : 1;
		}
		if (a.length == b.length) return 0;
		return a.length < b.length ? -1 : 1;
	}

	#if (sys && windows)

	#end
}
