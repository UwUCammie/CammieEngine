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

/** User-initiated updater for the published Windows x64 ZIP releases. */
class UpdateChecker {
	public static inline var RELEASES_API:String = 'https://api.github.com/repos/UwUCammie/CammieEngine/releases?per_page=20';
	public static inline var RELEASE_DOWNLOAD_ROOT:String = 'https://github.com/UwUCammie/CammieEngine/releases/download/';
	static var nextRequestId:Int = 0;
	#if (sys && windows)
	static var checkResults:Deque<UpdateCheckResult> = new Deque<UpdateCheckResult>();
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
				var body = getText(RELEASES_API, 'application/vnd.github+json');
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
			File.saveContent(Path.join([workRoot, 'install-update.ps1']), installerScript());
			var scriptPath = Path.join([workRoot, 'install-update.ps1']);
			var arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File '
				+ windowsArg(scriptPath) + ' ' + windowsArg(statusPath) + ' '
				+ windowsArg(Sys.programPath()) + ' ' + windowsArg(installRoot) + ' '
				+ windowsArg(release.archiveUrl) + ' ' + windowsArg(release.checksumUrl) + ' '
				+ windowsArg(release.archiveName) + ' ' + windowsArg(release.sha256) + ' '
				+ windowsArg(release.tag);
			var launch = '$$shell = New-Object -ComObject WScript.Shell; [void]$$shell.Run('
				+ powershellLiteral('powershell.exe ' + arguments) + ', 0, $$false)';
			var exitCode = Sys.command('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', launch]);
			if (exitCode != 0) return {statusPath:null, error:'Could not start the Windows update helper.'};
			return {statusPath:statusPath, error:null};
		} catch (error:Dynamic) {
			return {statusPath:null, error:Std.string(error)};
		}
	}

	public static function readInstallStatus(statusPath:String):Null<String> {
		if (statusPath == null || !FileSystem.exists(statusPath)) return null;
		try return StringTools.trim(File.getContent(statusPath)) catch (error:Dynamic) return null;
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

	static function windowsArg(value:String):String
		return '"' + StringTools.replace(value, '"', '\\"') + '"';

	static function powershellLiteral(value:String):String
		return "'" + StringTools.replace(value, "'", "''") + "'";

	static function getText(url:String, accept:String):String {
		var body:Null<String> = null;
		var error:Null<String> = null;
		var status:Int = 0;
		var request = new haxe.Http(url);
		request.cnxTimeout = 20;
		request.setHeader('Accept', accept);
		request.setHeader('X-GitHub-Api-Version', '2022-11-28');
		request.setHeader('User-Agent', 'CammieEngine-Updater');
		request.onStatus = function(code:Int) status = code;
		request.onData = function(data:String) body = data;
		request.onError = function(message:String) error = message;
		request.request(false);
		if (error != null) throw error;
		if (status < 200 || status >= 300) throw 'GitHub returned HTTP ' + status;
		if (body == null) throw 'GitHub returned an empty response';
		return body;
	}

	static function installerScript():String {
		return [
			'param([string]$$StatusPath,[string]$$ExePath,[string]$$InstallRoot,[string]$$ArchiveUrl,[string]$$ChecksumUrl,[string]$$ArchiveName,[string]$$ApiSha256,[string]$$ReleaseTag)',
			'$$ErrorActionPreference = "Stop"',
			'function Set-UpdateStatus([string]$$Value) { Set-Content -LiteralPath $$StatusPath -Value $$Value -Encoding ASCII }',
			'function Show-UpdateMessage([string]$$Message, [string]$$Title) { try { Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show($$Message, $$Title, "OK", "Information") } catch {} }',
			'$$workRoot = Split-Path -Parent $$StatusPath',
			'$$archivePath = Join-Path $$workRoot $$ArchiveName',
			'$$checksumPath = Join-Path $$workRoot "SHA256SUMS.txt"',
			'$$stageRoot = Join-Path $$workRoot "expanded"',
			'try {',
			'  Set-UpdateStatus "downloading"',
			'  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12',
			'  $$client = New-Object System.Net.WebClient',
			'  $$client.Headers.Add("User-Agent", "CammieEngine-Updater")',
			'  $$client.DownloadFile($$ArchiveUrl, $$archivePath)',
			'  $$client.DownloadFile($$ChecksumUrl, $$checksumPath)',
			'  Set-UpdateStatus "verifying"',
			'  $$pattern = "^(?<hash>[0-9a-fA-F]{64})\\s+\\*?" + [regex]::Escape($$ArchiveName) + "\\s*$$"',
			'  $$checksumEntries = @(Get-Content -LiteralPath $$checksumPath | Where-Object { $$_ -match $$pattern })',
			'  if ($$checksumEntries.Count -ne 1) { throw "The release checksum file did not contain exactly one matching ZIP entry." }',
			'  $$sidecarHash = ([regex]::Match($$checksumEntries[0], $$pattern)).Groups["hash"].Value.ToLowerInvariant()',
			'  $$actualHash = (Get-FileHash -LiteralPath $$archivePath -Algorithm SHA256).Hash.ToLowerInvariant()',
			'  if ($$sidecarHash -ne $$ApiSha256 -or $$actualHash -ne $$ApiSha256) { throw "The downloaded ZIP failed its SHA-256 checks." }',
			'  Set-UpdateStatus "extracting"',
			'  Add-Type -AssemblyName System.IO.Compression.FileSystem',
			'  $$zip = [System.IO.Compression.ZipFile]::OpenRead($$archivePath)',
			'  try {',
			'    $$stageFull = [System.IO.Path]::GetFullPath($$stageRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar',
			'    $$seenEntries = New-Object "System.Collections.Generic.HashSet[string]" ([System.StringComparer]::OrdinalIgnoreCase)',
			'    foreach ($$entry in $$zip.Entries) {',
			'      $$entryPath = $$entry.FullName.Replace([char]92, "/")',
			'      if ([System.IO.Path]::IsPathRooted($$entryPath) -or $$entryPath -match "^[A-Za-z]:" -or ($$entryPath -split "/") -contains "..") { throw "The release ZIP contains an unsafe path." }',
			'      if (-not $$seenEntries.Add($$entryPath)) { throw "The release ZIP contains a duplicate path." }',
			'      $$destinationFull = [System.IO.Path]::GetFullPath((Join-Path $$stageRoot $$entryPath))',
			'      if (-not $$destinationFull.StartsWith($$stageFull, [System.StringComparison]::OrdinalIgnoreCase)) { throw "The release ZIP contains a path outside its extraction folder." }',
			'    }',
			'  } finally { $$zip.Dispose() }',
			'  Expand-Archive -LiteralPath $$archivePath -DestinationPath $$stageRoot -Force',
			'  Remove-Item -LiteralPath $$archivePath,$$checksumPath -Force',
			'  $$payloadRoot = Join-Path $$stageRoot "CammieEngine-windows-x64"',
			'  foreach ($$required in @("Funkin.exe", "lime.ndll", "RELEASE_TAG", "assets")) { if (-not (Test-Path -LiteralPath (Join-Path $$payloadRoot $$required))) { throw "The release ZIP is missing $$required." } }',
			'  $$packageTag = (Get-Content -LiteralPath (Join-Path $$payloadRoot "RELEASE_TAG") -Raw).Trim()',
			'  if ($$packageTag -ne $$ReleaseTag) { throw "The release ZIP tag does not match the checked release." }',
			'  if (-not (Test-Path -LiteralPath $$ExePath)) { throw "The installed executable could not be found." }',
			'  Set-UpdateStatus "ready"',
			'  function Test-GameProcessOpen {',
			'    $$exeFullPath = [System.IO.Path]::GetFullPath($$ExePath)',
			'    $$matching = @(Get-Process -Name "Funkin" -ErrorAction SilentlyContinue | Where-Object { $$_.Path -and [System.IO.Path]::GetFullPath($$_.Path) -ieq $$exeFullPath })',
			'    if ($$matching.Count -gt 0) { return $$true }',
			'    try { $$stream = [System.IO.File]::Open($$ExePath,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::None); $$stream.Dispose(); return $$false } catch { return $$true }',
			'  }',
			'  while (Test-GameProcessOpen) { Start-Sleep -Seconds 1 }',
			'  Set-UpdateStatus "installing"',
			'  $$protectedRoots = @("assets", "mods", "imported_mods")',
			'  $$backupRoot = Join-Path $$workRoot "backup"',
			'  $$script:createdFiles = New-Object System.Collections.ArrayList',
			'  $$script:installStarted = $$true',
			'  function Copy-ReleaseFiles([string]$$Source,[string]$$Destination,[string]$$Relative) {',
			'    foreach ($$item in Get-ChildItem -LiteralPath $$Source -Force) {',
			'      $$relativePath = if ($$Relative -eq "") { $$item.Name } else { Join-Path $$Relative $$item.Name }',
			'      $$targetPath = Join-Path $$Destination $$item.Name',
			'      if ($$item.PSIsContainer) {',
			'        if (-not (Test-Path -LiteralPath $$targetPath)) { New-Item -ItemType Directory -Path $$targetPath -Force | Out-Null }',
			'        Copy-ReleaseFiles $$item.FullName $$targetPath $$relativePath',
			'      } else {',
			'        $$isUserContent = $$false',
			'        foreach ($$root in $$protectedRoots) { if ($$relativePath -ieq $$root -or $$relativePath.StartsWith($$root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) { $$isUserContent = $$true; break } }',
			'        if ($$isUserContent -and (Test-Path -LiteralPath $$targetPath)) { continue }',
			'        if ($$relativePath -ieq "RELEASE_TAG") { continue }',
			'        if (Test-Path -LiteralPath $$targetPath) {',
			'          $$backupPath = Join-Path $$backupRoot $$relativePath',
			'          if (-not (Test-Path -LiteralPath $$backupPath)) {',
			'            $$backupDirectory = Split-Path -Parent $$backupPath',
			'            if (-not (Test-Path -LiteralPath $$backupDirectory)) { New-Item -ItemType Directory -Path $$backupDirectory -Force | Out-Null }',
			'            Copy-Item -LiteralPath $$targetPath -Destination $$backupPath -Force',
			'          }',
			'        } else { [void]$$script:createdFiles.Add($$targetPath) }',
			'        Copy-Item -LiteralPath $$item.FullName -Destination $$targetPath -Force',
			'      }',
			'    }',
			'  }',
			'  Copy-ReleaseFiles $$payloadRoot $$InstallRoot ""',
			'  $$tagPath = Join-Path $$InstallRoot "RELEASE_TAG"',
			'  $$tagBackupPath = Join-Path $$backupRoot "RELEASE_TAG"',
			'  if (Test-Path -LiteralPath $$tagPath) {',
			'    if (-not (Test-Path -LiteralPath $$backupRoot)) { New-Item -ItemType Directory -Path $$backupRoot -Force | Out-Null }',
			'    Copy-Item -LiteralPath $$tagPath -Destination $$tagBackupPath -Force',
			'  } else { [void]$$script:createdFiles.Add($$tagPath) }',
			'  $$tagTemporaryPath = Join-Path $$InstallRoot ".RELEASE_TAG.update.tmp"',
			'  Set-Content -LiteralPath $$tagTemporaryPath -Value $$ReleaseTag -Encoding ASCII',
			'  Move-Item -LiteralPath $$tagTemporaryPath -Destination $$tagPath -Force',
			'  Remove-Item -LiteralPath $$stageRoot -Recurse -Force',
			'  Set-UpdateStatus "complete"',
			'  $$script:installStarted = $$false',
			'  try {',
			'    Add-Type -AssemblyName System.Windows.Forms',
			'    $$choice = [System.Windows.Forms.MessageBox]::Show("CammieEngine " + $$ReleaseTag + " is installed. Start it now?", "CammieEngine update", "YesNo", "Information")',
			'    if ($$choice -eq [System.Windows.Forms.DialogResult]::Yes) { Start-Process -FilePath $$ExePath -WorkingDirectory $$InstallRoot }',
			'  } catch {}',
			'} catch {',
			'  $$message = "Update failed: " + $$_.Exception.Message',
			'  if ($$script:installStarted) {',
			'    try {',
			'      foreach ($$newFile in $$script:createdFiles) { if (Test-Path -LiteralPath $$newFile) { Remove-Item -LiteralPath $$newFile -Force } }',
			'      if (Test-Path -LiteralPath $$backupRoot) {',
			'        $$backupFull = [System.IO.Path]::GetFullPath($$backupRoot).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar',
			'        foreach ($$savedFile in Get-ChildItem -LiteralPath $$backupRoot -File -Recurse) {',
			'          $$relativeSavedPath = $$savedFile.FullName.Substring($$backupFull.Length)',
			'          $$restorePath = Join-Path $$InstallRoot $$relativeSavedPath',
			'          $$restoreDirectory = Split-Path -Parent $$restorePath',
			'          if (-not (Test-Path -LiteralPath $$restoreDirectory)) { New-Item -ItemType Directory -Path $$restoreDirectory -Force | Out-Null }',
			'          Copy-Item -LiteralPath $$savedFile.FullName -Destination $$restorePath -Force',
			'        }',
			'      }',
			'    } catch { $$message += " Rollback also failed: " + $$_.Exception.Message }',
			'  }',
			'  if ($$tagTemporaryPath -and (Test-Path -LiteralPath $$tagTemporaryPath)) { Remove-Item -LiteralPath $$tagTemporaryPath -Force -ErrorAction SilentlyContinue }',
			'  Set-UpdateStatus ("error:" + $$message)',
			'  Show-UpdateMessage $$message "CammieEngine update failed"',
			'}'
		].join('\n');
	}
	#end
}
