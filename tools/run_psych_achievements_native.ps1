[CmdletBinding()]
param(
	[Parameter(Mandatory=$true)][string]$FixtureDir,
	[Parameter(Mandatory=$true)][string]$RuntimeDir,
	[Parameter(Mandatory=$true)][string]$BuildGate,
	[switch]$Unlimited,
	[switch]$StandardServices
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repoRoot = [IO.Path]::GetFullPath($repo).TrimEnd([char[]]@('\', '/'))
$repoRootPrefix = $repoRoot + [IO.Path]::DirectorySeparatorChar
function Resolve-RequiredInput([string]$Value, [string]$Description) {
	$candidate = if ([IO.Path]::IsPathRooted($Value)) { $Value } else { Join-Path $script:repo $Value }
	if (-not (Test-Path -LiteralPath $candidate)) { throw "Missing $Description`: $candidate" }
	return (Resolve-Path -LiteralPath $candidate).Path
}

$fixture = [IO.Path]::GetFullPath((Resolve-RequiredInput $FixtureDir 'generated Psych achievement fixture')).TrimEnd([char[]]@('\', '/'))
$runtime = [IO.Path]::GetFullPath((Resolve-RequiredInput $RuntimeDir 'fresh private native runtime')).TrimEnd([char[]]@('\', '/'))
$gatedPath = [IO.Path]::GetFullPath((Resolve-RequiredInput $BuildGate 'root build hash gate'))
$fixtureRoot = [IO.Path]::GetFullPath((Join-Path $repo 'tmp')).TrimEnd([char[]]@('\', '/'))
$fixturePrefix = $fixtureRoot + [IO.Path]::DirectorySeparatorChar
if (-not $fixture.StartsWith($fixturePrefix, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'Generated Psych fixture must stay below the repository tmp directory.'
}
$runtimeItem = Get-Item -LiteralPath $runtime -Force
if (-not $runtimeItem.PSIsContainer -or (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
	throw 'RuntimeDir must be a real private directory, not a file or reparse point.'
}
if (-not [IO.Path]::IsPathRooted($RuntimeDir)) { throw 'RuntimeDir must be an explicit absolute path.' }
if (($runtime.StartsWith($repoRootPrefix, [StringComparison]::OrdinalIgnoreCase)) -or
	($runtime.Equals($repoRoot, [StringComparison]::OrdinalIgnoreCase))) {
	throw 'RuntimeDir must be outside the repository checkout.'
}
$runtimeName = [IO.Path]::GetFileName($runtime)
if (-not $runtimeName.StartsWith('cammie-psych-achievements-', [StringComparison]::OrdinalIgnoreCase)) {
	throw 'RuntimeDir must name a unique cammie-psych-achievements-* private runtime.'
}

$exe = Join-Path $runtime 'Funkin.exe'
$optionsPath = Join-Path $runtime 'assets/data/options.json'
$versionPath = Join-Path $runtime 'VERSION'
$manifestPath = Join-Path $fixture 'fixture.json'
$source = (Resolve-Path -LiteralPath (Join-Path $fixture 'source')).Path
$runtimeTmp = [IO.Path]::GetFullPath((Join-Path $runtime 'tmp')).TrimEnd([char[]]@('\', '/'))
$runtimeTmpPrefix = $runtimeTmp + [IO.Path]::DirectorySeparatorChar
$runId = [Guid]::NewGuid().ToString('N').Substring(0, 12)
$mode = if ($Unlimited) { 'unlimited' } else { '60' }
$saveRoot = 'tmp/psych-achievements-save-' + $runId
$captureStem = 'tmp/psych-achievements-' + $mode + '-' + $runId
$importLog = 'tmp/psych-achievements-import-' + $runId + '.log'
$stateLog = 'tmp/psych-achievements-' + $mode + '-' + $runId + '.log'
$importStdout = Join-Path $runtime ('tmp/psych-achievements-import-' + $runId + '.stdout.log')
$importStderr = Join-Path $runtime ('tmp/psych-achievements-import-' + $runId + '.stderr.log')
$stateStdout = Join-Path $runtime ('tmp/psych-achievements-' + $mode + '-' + $runId + '.stdout.log')
$stateStderr = Join-Path $runtime ('tmp/psych-achievements-' + $mode + '-' + $runId + '.stderr.log')
$resultPath = Join-Path $repo ('tmp/psych-achievements-native-run-' + $mode + '-' + $runId + '.json')
$popupCapture = Join-Path $runtime ($captureStem + '-popup.png')
$activeProcess = $null
$envNames = @('CAMMIE_SMOKE_SAVE_ROOT', 'CAMMIE_IMPORT_UI_SMOKE', 'CAMMIE_NV_STATE_SMOKE',
	'CAMMIE_NV_STATE_RETAINED', 'CAMMIE_NV_STATE_ALPHA', 'CAMMIE_NV_STATE_BETA',
	'CAMMIE_NV_STATE_CAPTURE', 'CAMMIE_NV_FAMILY_SMOKE', 'CAMMIE_NV_SPLASH_MODE',
	'CAMMIE_PSYCH_ACHIEVEMENTS_SMOKE', 'CAMMIE_PSYCH_ACHIEVEMENTS_CAPTURE', 'CAMMIE_PSYCH_STANDARD_SMOKE')
$envBefore = @{}
foreach ($name in $envNames) { $envBefore[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$optionsBefore = $null
$versionBefore = $null
$result = [ordered]@{ runId = $runId; mode = $mode; fixture = $fixture; runtime = $runtime }

function Assert-FileHash([string]$Path, [long]$Bytes, [string]$Expected, [string]$Description) {
	if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Description`: $Path" }
	$item = Get-Item -LiteralPath $Path
	$actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
	if (($item.Length -ne $Bytes) -or ($actual -ne $Expected.ToLowerInvariant())) {
		throw "$Description changed from its recorded input: $Path"
	}
}

function Write-NewTextFile([string]$Path, [string]$Text) {
	$stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew,
		[System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
	$writer = [System.IO.StreamWriter]::new($stream, [System.Text.UTF8Encoding]::new($false))
	try { $writer.Write($Text) } finally { $writer.Dispose() }
}

function Read-EventLog([string]$Path, [string]$Prefix) {
	if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing structured event log: $Path" }
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
	if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Private native runtime executable is missing: $exe" }
	if (-not (Test-Path -LiteralPath $optionsPath -PathType Leaf)) { throw "Private runtime options are missing: $optionsPath" }
	if (-not (Test-Path -LiteralPath $versionPath -PathType Leaf)) { throw "Private runtime VERSION is missing: $versionPath" }
	if (-not (Test-Path -LiteralPath $gatedPath -PathType Leaf)) { throw "Root build hash gate is missing: $gatedPath" }
	if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { throw "Fixture manifest is missing: $manifestPath" }
	if (-not (Test-Path -LiteralPath $runtimeTmp -PathType Container)) { throw "Private runtime tmp directory is missing: $runtimeTmp" }
	$tmpItem = Get-Item -LiteralPath $runtimeTmp -Force
	if (($tmpItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Private runtime tmp must not be a reparse point.' }
	if (-not $runtimeTmp.StartsWith([IO.Path]::GetFullPath($runtime).TrimEnd([char[]]@('\', '/')) + [IO.Path]::DirectorySeparatorChar,
		[StringComparison]::OrdinalIgnoreCase)) { throw 'Private runtime tmp escaped RuntimeDir.' }
	if (-not $gatedPath.StartsWith($fixturePrefix, [StringComparison]::OrdinalIgnoreCase)) {
		throw 'BuildGate must stay below the repository tmp directory.'
	}
	$running = Get-CimInstance Win32_Process -Filter "Name='Funkin.exe'" | Where-Object { $_.ExecutablePath -eq $exe }
	if ($running) { throw 'The isolated Psych achievement runtime is already running.' }
	if (Test-Path -LiteralPath (Join-Path $runtime 'import-cache')) {
		throw 'Refusing a non-fresh private runtime with an existing import-cache.'
	}

	$fixtureData = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json -ErrorAction Stop
	if (($fixtureData.schemaVersion -ne 1) -or ($fixtureData.importEngine -ne 'Psych') -or
		($fixtureData.songName -ne 'Achievement Runtime Fixture') -or
		($fixtureData.songFolder -ne 'achievement-runtime-fixture') -or
		($fixtureData.chart -ne 'assets/data/achievement-runtime-fixture/achievement-runtime-fixture.json') -or
		($fixtureData.audio -ne 'assets/songs/achievement-runtime-fixture/Inst.ogg') -or
		($fixtureData.achievements -ne 'assets/data/achievements.json') -or
		($fixtureData.images.popupPixel -ne 'assets/images/achievements/fixture_popup-pixel.png')) {
		throw 'Generated fixture manifest does not describe the expected Psych achievement source.'
	}
	foreach ($entry in $fixtureData.files) {
		$relative = $entry.path.Replace('/', [IO.Path]::DirectorySeparatorChar)
		$path = [IO.Path]::GetFullPath((Join-Path $source $relative))
		if (-not $path.StartsWith($source.TrimEnd([char[]]@('\', '/')) + [IO.Path]::DirectorySeparatorChar,
			[StringComparison]::OrdinalIgnoreCase)) { throw "Fixture file escaped generated source: $($entry.path)" }
		Assert-FileHash $path $entry.bytes $entry.sha256 "Generated fixture file $($entry.path)"
	}
	foreach ($input in $fixtureData.readOnlyInputs) {
		Assert-FileHash $input.path $input.bytes $input.sha256 "Read-only source input $($input.path)"
	}
	if (Test-Path -LiteralPath $popupCapture) { throw "Refusing to reuse a native popup capture: $popupCapture" }
	foreach ($output in @($resultPath, (Join-Path $runtime $importLog), (Join-Path $runtime $stateLog),
		$importStdout, $importStderr, $stateStdout, $stateStderr)) {
		if (Test-Path -LiteralPath $output) { throw "Refusing to overwrite an existing native smoke output: $output" }
	}
	$captureResolved = [IO.Path]::GetFullPath($popupCapture)
	if (-not $captureResolved.StartsWith($runtimeTmpPrefix, [StringComparison]::OrdinalIgnoreCase)) {
		throw 'Native popup capture must stay below the isolated runtime tmp directory.'
	}
	$savePath = [IO.Path]::GetFullPath((Join-Path $runtime $saveRoot))
	$runtimePathPrefix = [IO.Path]::GetFullPath($runtime).TrimEnd([char[]]@('\', '/'))
		+ [IO.Path]::DirectorySeparatorChar
	if (-not $savePath.StartsWith($runtimePathPrefix, [StringComparison]::OrdinalIgnoreCase)) {
		throw 'Smoke save root escaped the isolated runtime.'
	}
	if (Test-Path -LiteralPath $savePath) { throw "Refusing to reuse an isolated smoke save: $savePath" }

	$gate = Get-Content -LiteralPath $gatedPath -Raw | ConvertFrom-Json -ErrorAction Stop
	foreach ($binaryName in @('Funkin.exe', 'lime.ndll')) {
		$exported = Join-Path $repo ('export/release/windows/bin/' + $binaryName)
		$expected = $gate.files.PSObject.Properties[$binaryName].Value
		if ([string]::IsNullOrWhiteSpace($expected)) { throw "Root gate has no accepted hash for $binaryName" }
		$exportInfo = Get-Item -LiteralPath $exported
		Assert-FileHash $exported $exportInfo.Length $expected "Gated export $binaryName"
		Copy-Item -LiteralPath $exported -Destination (Join-Path $runtime $binaryName) -Force
		$copiedInfo = Get-Item -LiteralPath (Join-Path $runtime $binaryName)
		Assert-FileHash (Join-Path $runtime $binaryName) $copiedInfo.Length $expected "Gated private runtime $binaryName"
	}

	$optionsBefore = [IO.File]::ReadAllBytes($optionsPath)
	$versionBefore = [IO.File]::ReadAllBytes($versionPath)
	$options = [Text.Encoding]::UTF8.GetString($optionsBefore) | ConvertFrom-Json -ErrorAction Stop
	$options | Add-Member -NotePropertyName unlimitedFPS -NotePropertyValue ([bool]$Unlimited) -Force
	$options | Add-Member -NotePropertyName fpsCap -NotePropertyValue 60 -Force
	[IO.File]::WriteAllText($optionsPath, ($options | ConvertTo-Json -Depth 20), [Text.UTF8Encoding]::new($false))
	[IO.File]::WriteAllText($versionPath, [IO.File]::ReadAllText((Join-Path $repo 'VERSION')), [Text.UTF8Encoding]::new($false))
	[IO.Directory]::CreateDirectory($savePath) | Out-Null
	$result.saveRoot = $savePath
	$result.standardServices = [bool]$StandardServices
	if (-not $StandardServices) { $result.capture = $captureResolved }

	foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $null, 'Process') }
	$importArgs = '--smoke-import-source "' + $source + '" --smoke-import-type "Psych" --smoke-import-timeout-ms 300000 --smoke-import-log "' + $importLog + '"'
	$result.import = Invoke-PrivateGame $importArgs $importStdout $importStderr 360000 'Native Psych retained-source import'
	$importEvents = Read-EventLog (Join-Path $runtime $importLog) 'RUNTIME_IMPORT_SMOKE|'
	$scan = @($importEvents | Where-Object { $_.event -eq 'scan_ready' })
	$importStarted = @($importEvents | Where-Object { $_.event -eq 'import_start' })
	$importSuccess = @($importEvents | Where-Object { $_.event -eq 'success' })
	$importFailures = @($importEvents | Where-Object { $_.event -eq 'failure' })
	if (($scan.Count -ne 1) -or ($scan[0].songsToImport -ne 1) -or ($scan[0].errors -ne 0) -or
		($importStarted.Count -ne 1) -or ($importSuccess.Count -ne 1) -or ($importFailures.Count -ne 0) -or
		($importSuccess[0].found -ne 1) -or ($importSuccess[0].imported -ne 1) -or
		($importSuccess[0].failed -ne 0)) {
		throw 'Actual RuntimeImportSmokeHarness did not publish the single Psych fixture chart.'
	}
	$result.importEvents = $importEvents

	$env:CAMMIE_SMOKE_SAVE_ROOT = $saveRoot.Replace('\', '/')
	if ($StandardServices) {
		if (-not $fixtureData.standardServices) { throw 'Standard service probe requires the generated language inputs.' }
		$env:CAMMIE_PSYCH_STANDARD_SMOKE = '1'
	} else { $env:CAMMIE_PSYCH_ACHIEVEMENTS_SMOKE = '1' }
	$env:CAMMIE_PSYCH_ACHIEVEMENTS_CAPTURE = $captureStem.Replace('\', '/')
	$stateArgs = '--smoke-freeplay --smoke-duration-ms 45000 --smoke-log "' + $stateLog + '"'
	$result.smoke = Invoke-PrivateGame $stateArgs $stateStdout $stateStderr 120000 'Psych achievement native component probe'
	$stateEvents = Read-EventLog (Join-Path $runtime $stateLog) 'RUNTIME_SMOKE|'
	$verifiedEvent = if ($StandardServices) { 'psych_standard_verified' } else { 'psych_achievements_verified' }
	$verified = @($stateEvents | Where-Object { $_.event -eq $verifiedEvent })
	$success = @($stateEvents | Where-Object { $_.event -eq 'success' })
	$failures = @($stateEvents | Where-Object { $_.event -eq 'failure' })
	if (($verified.Count -ne 1) -or ($success.Count -ne 1) -or ($failures.Count -ne 0)) {
		throw 'Native Psych achievement smoke did not produce exactly one verified result and successful smoke completion.'
	}
	$requiredFields = if ($StandardServices) {
		@('hscript', 'lua', 'reflected', 'languageReload', 'rpcMarshalling', 'ownerCleanup')
	} else { @('hscript', 'lua', 'reflected', 'persistence', 'sameOwnerReuse', 'otherOwnerCleanup', 'popupLifecycle') }
	foreach ($field in $requiredFields) {
		$property = $verified[0].PSObject.Properties[$field]
		if ($null -eq $property -or $property.Value -ne $true) {
			throw "Native Psych achievement probe did not verify $field."
		}
	}
	if (-not $StandardServices -and -not (Test-Path -LiteralPath $popupCapture -PathType Leaf)) {
		throw "Native popup screenshot is missing: $popupCapture"
	}
	$result.stateEvents = $stateEvents
	$result.verified = $verified[0]
	Write-NewTextFile $resultPath ($result | ConvertTo-Json -Depth 24)
	Write-Output "Psych achievement native evidence: $resultPath"
	Write-Output "Import log: $(Join-Path $runtime $importLog)"
	Write-Output "Smoke log: $(Join-Path $runtime $stateLog)"
	if (-not $StandardServices) { Write-Output "Popup capture: $popupCapture" }
}
finally {
	Stop-PrivateProcess
	if ($null -ne $optionsBefore) { [IO.File]::WriteAllBytes($optionsPath, $optionsBefore) }
	if ($null -ne $versionBefore) { [IO.File]::WriteAllBytes($versionPath, $versionBefore) }
	foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $envBefore[$name], 'Process') }
}

Write-Output 'Private options and version restored, process environment restored, and isolated saves/import outputs retained for review.'
