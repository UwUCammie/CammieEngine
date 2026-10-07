[CmdletBinding()]
param(
	[Parameter(Mandatory=$true)][string]$FixtureDir,
	[Parameter(Mandatory=$true)][string]$RuntimeDir,
	[Parameter(Mandatory=$true)][string]$BuildGate,
	[switch]$Unlimited,
	[ValidateSet('None', 'Branding', 'Video', 'SkipBranding', 'AbortBranding')]
	[string]$SplashMode = 'None'
)

$ErrorActionPreference = 'Stop'
$allowedSplashModes = @('None', 'Branding', 'Video', 'SkipBranding', 'AbortBranding')
if (-not ($allowedSplashModes -ccontains $SplashMode)) {
	throw 'SplashMode must use the exact case: None, Branding, Video, SkipBranding, or AbortBranding.'
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Resolve-RequiredInput([string]$Value, [string]$Description) {
	$candidate = if ([IO.Path]::IsPathRooted($Value)) { $Value } else { Join-Path $script:repo $Value }
	if (-not (Test-Path -LiteralPath $candidate)) { throw "Missing $Description`: $candidate" }
	return (Resolve-Path -LiteralPath $candidate).Path
}

$fixture = Resolve-RequiredInput $FixtureDir 'generated fixture directory'
$runtime = Resolve-RequiredInput $RuntimeDir 'private runtime directory'
$gatedPath = Resolve-RequiredInput $BuildGate 'build hash gate'
$fixture = [IO.Path]::GetFullPath($fixture).TrimEnd([char[]]@('\', '/'))
$runtime = [IO.Path]::GetFullPath($runtime).TrimEnd([char[]]@('\', '/'))
$gatedPath = [IO.Path]::GetFullPath($gatedPath)
$source = (Resolve-Path (Join-Path $fixture 'source')).Path
$runtimeName = [IO.Path]::GetFileName($runtime)
$runtimeItem = Get-Item -LiteralPath $runtime -Force
if (-not $runtimeItem.PSIsContainer -or (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
	throw 'RuntimeDir must be a real private directory, not a file or reparse point.'
}
if (-not [IO.Path]::IsPathRooted($RuntimeDir)) {
	throw 'RuntimeDir must be an explicit absolute path.'
}
if (-not $runtimeName.StartsWith('cammie-nv-startup-', [StringComparison]::OrdinalIgnoreCase)) {
	throw 'RuntimeDir must name a unique cammie-nv-startup-* private runtime.'
}
$repoRoot = [IO.Path]::GetFullPath($repo).TrimEnd([char[]]@('\', '/'))
$repoRootPrefix = $repoRoot + [IO.Path]::DirectorySeparatorChar
if ($runtime.StartsWith($repoRootPrefix, [StringComparison]::OrdinalIgnoreCase) -or
	$runtime.Equals($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'RuntimeDir must be outside the repository checkout.'
}
$exe = Join-Path $runtime 'Funkin.exe'
$optionsPath = Join-Path $runtime 'assets/data/options.json'
$versionPath = Join-Path $runtime 'VERSION'
$fixtureManifestPath = Join-Path $fixture 'fixture.json'
$runId = [Guid]::NewGuid().ToString('N').Substring(0, 10)
$mode = if ($Unlimited) { 'unlimited' } else { '60' }
$saveRoot = 'tmp/nv-retained-state-saves-' + $runId
$captureStem = 'tmp/nv-retained-state-' + $mode + '-' + $runId
$importLog = 'tmp/nv-retained-state-import-' + $runId + '.log'
$stateLog = 'tmp/nv-retained-state-' + $mode + '-' + $runId + '.log'
$importStdout = Join-Path $runtime ('tmp/nv-retained-state-import-' + $runId + '.stdout.log')
$importStderr = Join-Path $runtime ('tmp/nv-retained-state-import-' + $runId + '.stderr.log')
$stateStdout = Join-Path $runtime ('tmp/nv-retained-state-' + $mode + '-' + $runId + '.stdout.log')
$stateStderr = Join-Path $runtime ('tmp/nv-retained-state-' + $mode + '-' + $runId + '.stderr.log')
$resultPath = Join-Path $repo ('tmp/nv-retained-state-native-run-' + $mode + '-' + $runId + '.json')
$activeProcess = $null
$envNames = @('CAMMIE_SMOKE_SAVE_ROOT', 'CAMMIE_IMPORT_UI_SMOKE', 'CAMMIE_NV_STATE_SMOKE',
	'CAMMIE_NV_STATE_RETAINED', 'CAMMIE_NV_STATE_ALPHA', 'CAMMIE_NV_STATE_BETA',
	'CAMMIE_NV_STATE_CAPTURE', 'CAMMIE_NV_FAMILY_SMOKE', 'CAMMIE_NV_SPLASH_MODE')
$envBefore = @{}
foreach ($name in $envNames) { $envBefore[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$optionsBefore = $null
$versionBefore = $null
$result = [ordered]@{ runId = $runId; mode = $mode; splashMode = $SplashMode; fixture = $fixture; runtime = $runtime }

function Assert-FileHash([string]$Path, [string]$Expected, [string]$Description) {
	if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Description`: $Path" }
	$actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
	if ($actual -ne $Expected.ToLowerInvariant()) { throw "$Description hash differs from its recorded value: $Path" }
}

function Read-EventLog([string]$Path, [string]$Prefix) {
	$events = @()
	foreach ($line in Get-Content -LiteralPath $Path) {
		if (-not $line.StartsWith($Prefix)) { continue }
		try { $events += $line.Substring($Prefix.Length) | ConvertFrom-Json }
		catch { throw "Invalid structured event in $Path`: $line" }
	}
	return ,$events
}

function Stop-PrivateProcess {
	if ($null -ne $script:activeProcess) {
		$script:activeProcess.Refresh()
		if (-not $script:activeProcess.HasExited) {
			$script:activeProcess.Kill()
			$script:activeProcess.WaitForExit()
		}
		$script:activeProcess = $null
	}
}

function Invoke-PrivateGame([string]$Arguments, [string]$StdoutPath, [string]$StderrPath,
	[int]$TimeoutMs, [string]$Phase) {
	$process = Start-Process -FilePath $script:exe -WorkingDirectory $script:runtime -ArgumentList $Arguments `
		-WindowStyle Hidden -PassThru -RedirectStandardOutput $StdoutPath -RedirectStandardError $StderrPath
	$script:activeProcess = $process
	$null = $process.Handle
	$timer = [Diagnostics.Stopwatch]::StartNew()
	while (-not $process.WaitForExit(1000)) {
		if ($timer.ElapsedMilliseconds -gt $TimeoutMs) { throw "$Phase timed out after $TimeoutMs ms" }
	}
	$process.Refresh()
	$exitCode = $process.ExitCode
	$script:activeProcess = $null
	if ($exitCode -ne 0) { throw "$Phase exited with code $exitCode; see $StdoutPath and $StderrPath" }
	return [ordered]@{ exitCode = $exitCode; elapsedMs = $timer.ElapsedMilliseconds }
}

try {
	if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Private native runtime seed missing: $exe" }
	if (-not (Test-Path -LiteralPath $optionsPath -PathType Leaf)) { throw "Private runtime options missing: $optionsPath" }
	if (-not (Test-Path -LiteralPath $gatedPath -PathType Leaf)) { throw "Root build hash gate missing: $gatedPath" }
	if (-not (Test-Path -LiteralPath $fixtureManifestPath -PathType Leaf)) { throw "Generated fixture manifest missing: $fixtureManifestPath" }
	if (-not (Test-Path -LiteralPath (Join-Path $runtime 'tmp') -PathType Container)) { throw 'Private runtime tmp directory missing' }
	$repoTmp = [IO.Path]::GetFullPath((Join-Path $repo 'tmp')).TrimEnd('\') + [IO.Path]::DirectorySeparatorChar
	if (-not $fixture.StartsWith($repoTmp, [StringComparison]::OrdinalIgnoreCase)) {
		throw 'Generated importer fixture must stay below the repository tmp directory.'
	}
	if (-not $gatedPath.StartsWith($repoTmp, [StringComparison]::OrdinalIgnoreCase)) {
		throw 'BuildGate must stay below the repository tmp directory.'
	}
	$resolvedRuntime = [IO.Path]::GetFullPath($runtime).TrimEnd('\')
	$running = Get-CimInstance Win32_Process -Filter "Name='Funkin.exe'" | Where-Object { $_.ExecutablePath -eq $exe }
	if ($running) { throw 'The isolated retained-state game runtime is already running' }
	if (Test-Path -LiteralPath (Join-Path $runtime 'import-cache')) {
		throw 'Refusing a non-fresh retained importer seed; use a new isolated copy so prior import receipts stay untouched.'
	}

	$fixtureData = Get-Content -LiteralPath $fixtureManifestPath -Raw | ConvertFrom-Json
	$fixtureSplashMode = 'None'
	$splashModeProperty = $fixtureData.PSObject.Properties['splashMode']
	if ($null -ne $splashModeProperty -and -not [string]::IsNullOrWhiteSpace([string]$splashModeProperty.Value)) {
		$fixtureSplashMode = [string]$splashModeProperty.Value
	}
	$splashAssets = $fixtureData.splashAssets
	if ($null -eq $splashAssets) { $splashAssets = [PSCustomObject]@{} }
	if (($fixtureData.importEngine -ne 'Nightmare Vision') -or ($fixtureData.packages.Count -ne 2) -or
		($fixtureData.packages[0].directory -ne 'alpha') -or ($fixtureData.packages[1].directory -ne 'beta') -or
		($fixtureSplashMode -ne $SplashMode)) {
		throw 'Generated fixture manifest does not describe the requested two-member Nightmare Vision splash fixture.'
	}
	$splashAssetNames = @($splashAssets.PSObject.Properties | ForEach-Object { $_.Name })
	switch ($SplashMode) {
		'None' {
			if ($splashAssetNames.Count -ne 0) { throw 'None mode fixture unexpectedly contains source splash assets.' }
		}
		'Video' {
			if (($splashAssetNames.Count -ne 1) -or ($splashAssets.video -ne 'content/beta/assets/videos/intro.mp4')) {
				throw 'Video mode fixture does not declare only the selected-owner intro video.'
			}
		}
		default {
			if (($splashAssetNames.Count -ne 2) -or
				($splashAssets.watermark -ne 'content/beta/assets/images/branding/watermarks/NMV.png') -or
				($splashAssets.sound -ne 'content/beta/assets/sounds/intro.ogg')) {
				throw 'Branding mode fixture is missing its selected-owner watermark or intro sound.'
			}
		}
	}
	foreach ($entry in $fixtureData.files) {
		$relative = $entry.path.Replace('/', [IO.Path]::DirectorySeparatorChar)
		$path = [IO.Path]::GetFullPath((Join-Path $source $relative))
		if (-not $path.StartsWith($source.TrimEnd('\') + [IO.Path]::DirectorySeparatorChar,
			[ StringComparison ]::OrdinalIgnoreCase)) { throw "Fixture file escaped the generated source root: $($entry.path)" }
		if ((Get-Item -LiteralPath $path).Length -ne $entry.bytes) { throw "Fixture size changed: $($entry.path)" }
		Assert-FileHash $path $entry.sha256 "Generated fixture file $($entry.path)"
	}
	foreach ($seedInput in $fixtureData.readOnlySeedInputs) {
		Assert-FileHash $seedInput.path $seedInput.sha256 "Read-only runtime seed input $($seedInput.path)"
	}

	$gate = Get-Content -LiteralPath $gatedPath -Raw | ConvertFrom-Json
	foreach ($binaryName in @('Funkin.exe', 'lime.ndll')) {
		$exported = Join-Path $repo ('export/release/windows/bin/' + $binaryName)
		$expected = $gate.files.PSObject.Properties[$binaryName].Value
		if ([string]::IsNullOrWhiteSpace($expected)) { throw "Root gate has no accepted hash for $binaryName" }
		Assert-FileHash $exported $expected "Gated export $binaryName"
		Copy-Item -LiteralPath $exported -Destination (Join-Path $runtime $binaryName) -Force
		Assert-FileHash (Join-Path $runtime $binaryName) $expected "Gated private runtime $binaryName"
	}

	$optionsBefore = [IO.File]::ReadAllBytes($optionsPath)
	$versionBefore = [IO.File]::ReadAllBytes($versionPath)
	$options = [Text.Encoding]::UTF8.GetString($optionsBefore) | ConvertFrom-Json
	$options | Add-Member -NotePropertyName unlimitedFPS -NotePropertyValue ([bool]$Unlimited) -Force
	$options | Add-Member -NotePropertyName fpsCap -NotePropertyValue 60 -Force
	[IO.File]::WriteAllText($optionsPath, ($options | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
	[IO.File]::WriteAllText($versionPath, [IO.File]::ReadAllText((Join-Path $repo 'VERSION')), [Text.UTF8Encoding]::new($false))

	$savePath = [IO.Path]::GetFullPath((Join-Path $runtime $saveRoot))
	if (-not $savePath.StartsWith($resolvedRuntime + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
		throw 'Smoke save root escaped the isolated runtime.'
	}
	if (Test-Path -LiteralPath $savePath) { throw "Refusing to reuse a save directory: $savePath" }
	[IO.Directory]::CreateDirectory($savePath) | Out-Null
	$result.saveRoot = $savePath

	foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $null, 'Process') }
	$importArgs = '--smoke-import-source "' + $source + '" --smoke-import-type "Nightmare Vision" --smoke-import-timeout-ms 300000 --smoke-import-log "' + $importLog + '"'
	$result.import = Invoke-PrivateGame $importArgs $importStdout $importStderr 360000 'Native retained-source import'
	$importEvents = Read-EventLog (Join-Path $runtime $importLog) 'RUNTIME_IMPORT_SMOKE|'
	$scan = @($importEvents | Where-Object { $_.event -eq 'scan_ready' })
	$importStarted = @($importEvents | Where-Object { $_.event -eq 'import_start' })
	$importSuccess = @($importEvents | Where-Object { $_.event -eq 'success' })
	$importFailures = @($importEvents | Where-Object { $_.event -eq 'failure' })
	if (($scan.Count -ne 1) -or ($scan[0].songsToImport -lt 1) -or ($scan[0].errors -ne 0) -or
		($importStarted.Count -ne 1) -or ($importSuccess.Count -ne 1) -or ($importFailures.Count -ne 0) -or
		($importSuccess[0].found -lt 1) -or ($importSuccess[0].imported -lt 1) -or ($importSuccess[0].failed -ne 0)) {
		throw 'Actual RuntimeImportSmokeHarness import did not complete with one or more imported songs.'
	}
	$result.importEvents = $importEvents

	$env:CAMMIE_SMOKE_SAVE_ROOT = $saveRoot.Replace('\', '/')
	$env:CAMMIE_NV_STATE_SMOKE = '1'
	$env:CAMMIE_NV_STATE_RETAINED = '1'
	$env:CAMMIE_NV_STATE_CAPTURE = $captureStem.Replace('\', '/')
	$env:CAMMIE_NV_SPLASH_MODE = $SplashMode
	$stateArgs = '--smoke-freeplay --smoke-freeplay-scroll-ms 0 --smoke-duration-ms 45000 --smoke-log "' + $stateLog + '"'
	$result.state = Invoke-PrivateGame $stateArgs $stateStdout $stateStderr 120000 'Retained source-state native probe'
	$stateEvents = Read-EventLog (Join-Path $runtime $stateLog) 'RUNTIME_SMOKE|'
	$retained = @($stateEvents | Where-Object { $_.event -eq 'nv_state_retained_import_verified' })
	$verified = @($stateEvents | Where-Object { $_.event -eq 'nv_state_verified' })
	$splashVerified = @($stateEvents | Where-Object { $_.event -eq 'nv_splash_verified' })
	$stateSuccess = @($stateEvents | Where-Object { $_.event -eq 'success' })
	$stateFailures = @($stateEvents | Where-Object { $_.event -eq 'failure' })
	$callbacks = @($stateEvents | Where-Object { $_.event -eq 'nv_state_callback' })
	if (($retained.Count -ne 1) -or ($verified.Count -ne 1) -or ($stateSuccess.Count -ne 1) -or ($stateFailures.Count -ne 0) -or
		($verified[0].retainedImport -ne $true) -or ($verified[0].bootstrapComplete -ne $true) -or
		($verified[0].sourceHighscoreService -ne $true) -or ($verified[0].sourceStartMeta -ne $true) -or
		($verified[0].sourceMainRuntime -ne $true) -or
		($verified[0].retiredStartupState -ne $true) -or
		($verified[0].resets -ne 2)) {
		throw 'Native source-state log lacks complete retained-import, Init, service or lifecycle evidence.'
	}
	if ($SplashMode -eq 'None') {
		if ($splashVerified.Count -ne 0) { throw 'Default None mode unexpectedly entered the source Splash state.' }
	} else {
		if (($splashVerified.Count -ne 1) -or ($verified[0].sourceSplash -ne $true) -or
			($splashVerified[0].mode -ne $SplashMode) -or
			($splashVerified[0].formattedOrLogoVisible -ne $true) -or
			($splashVerified[0].completed -ne $true) -or
			($splashVerified[0].disposed -ne $true) -or
			($splashVerified[0].cleaned -ne $true) -or
			($splashVerified[0].audioRestored -ne $true) -or
			($splashVerified[0].noLateSwitch -ne $true)) {
			throw 'Opt-in native Splash log lacks its rendering, completion/abort cleanup, audio restore or no-late-switch evidence.'
		}
	}
	if ((@($callbacks | Where-Object { $_.name -eq 'highscore-bound' }).Count -ne 1) -or
		(@($callbacks | Where-Object { $_.name -eq 'start-meta-title-class' }).Count -ne 1)) {
		throw 'Native plugin did not prove the imported Highscore and source Main.startMeta bindings.'
	}
	if (($retained[0].sourceCore.path -ne 'assets/data/retained-source-core.txt') -or
		($retained[0].sourceCore.sha256 -notmatch '^[a-f0-9]{64}$') -or
		($retained[0].sourceFont.path -ne 'assets/fonts/consolas.ttf') -or
		($retained[0].sourceFont.sha256 -notmatch '^[a-f0-9]{64}$')) {
		throw 'Native importer did not retain the verified root-owned core marker and Consolas source font.'
	}
	$captures = @('redirect', 'native-title')
	if ($SplashMode -ne 'None') { $captures += 'splash' }
	foreach ($capture in $captures) {
		$path = Join-Path $runtime ($captureStem + '-' + $capture + '.png')
		if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing native source-state capture: $path" }
	}
	$result.stateEvents = $stateEvents
	$result.verified = $verified[0]
	if ($SplashMode -ne 'None') { $result.splashVerified = $splashVerified[0] }
	$result.retainedImport = $retained[0]
	[IO.File]::WriteAllText($resultPath, ($result | ConvertTo-Json -Depth 24), [Text.UTF8Encoding]::new($false))
	Write-Output "Retained native source-state evidence: $resultPath"
	Write-Output "Import log: $(Join-Path $runtime $importLog)"
	Write-Output "State log: $(Join-Path $runtime $stateLog)"
	Write-Output "Import, receipt/catalog resolution, Init, Highscore, source state lifecycle and cleanup verified: $mode / splash $SplashMode"
}
finally {
	Stop-PrivateProcess
	if ($null -ne $optionsBefore) { [IO.File]::WriteAllBytes($optionsPath, $optionsBefore) }
	if ($null -ne $versionBefore) { [IO.File]::WriteAllBytes($versionPath, $versionBefore) }
	foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $envBefore[$name], 'Process') }
}

Write-Output 'Private options and version restored, process environment restored, and isolated saves/importer outputs retained for review.'
