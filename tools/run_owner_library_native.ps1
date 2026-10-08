[CmdletBinding()]
param(
	[Parameter(Mandatory=$true)][string]$RuntimeDir,
	[Parameter(Mandatory=$true)][string]$FixtureDir,
	[Parameter(Mandatory=$true)][string]$ExpectedExeSha256,
	[int]$DurationMs = 90000
)

$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repoRoot = [IO.Path]::GetFullPath($repo).TrimEnd([char[]]@('\', '/'))
$runtime = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $RuntimeDir).Path).TrimEnd([char[]]@('\', '/'))
$fixture = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $FixtureDir).Path).TrimEnd([char[]]@('\', '/'))
$repoPrefix = $repoRoot + [IO.Path]::DirectorySeparatorChar
$tmpRoot = [IO.Path]::GetFullPath((Join-Path $repo 'tmp')).TrimEnd([char[]]@('\', '/'))
$tmpPrefix = $tmpRoot + [IO.Path]::DirectorySeparatorChar
if ($runtime.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase) -or
	$runtime.Equals($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'RuntimeDir must be a private runtime outside the checkout.'
}
if (-not [IO.Path]::GetFileName($runtime).StartsWith('cammie-owner-library-', [StringComparison]::OrdinalIgnoreCase)) {
	throw 'RuntimeDir must be a uniquely named cammie-owner-library-* private runtime.'
}
if (-not ($fixture.StartsWith($tmpPrefix, [StringComparison]::OrdinalIgnoreCase))) {
	throw 'FixtureDir must be below the checkout tmp directory.'
}
$runtimeItem = Get-Item -LiteralPath $runtime -Force
if (-not $runtimeItem.PSIsContainer -or (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
	throw 'RuntimeDir must be a real private directory, not a file or reparse point.'
}
if ($DurationMs -lt 30000 -or $DurationMs -gt 180000) { throw 'DurationMs must be between 30000 and 180000.' }

$exe = Join-Path $runtime 'Funkin.exe'
$requestSource = Join-Path $fixture 'request.json'
$runtimeTmp = [IO.Path]::GetFullPath((Join-Path $runtime 'tmp')).TrimEnd([char[]]@('\', '/'))
$runtimeTmpPrefix = $runtimeTmp + [IO.Path]::DirectorySeparatorChar
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw "Missing private native executable: $exe" }
if (-not (Test-Path -LiteralPath $requestSource -PathType Leaf)) { throw "Missing generated fixture request: $requestSource" }
$fixtureRequest = Get-Content -LiteralPath $requestSource -Raw | ConvertFrom-Json
if ($fixtureRequest.kind -ne 'psych-owner-library-typed-media' -or
	[string]::IsNullOrWhiteSpace([string]$fixtureRequest.sourceRoot) -or
	[string]::IsNullOrWhiteSpace([string]$fixtureRequest.cppSourceRoot) -or
	[string]::IsNullOrWhiteSpace([string]$fixtureRequest.unknownSourceRoot) -or
	[string]::IsNullOrWhiteSpace([string]$fixtureRequest.cppLibrary) -or
	[string]::IsNullOrWhiteSpace([string]$fixtureRequest.cppStreamMusicId)) {
	throw 'Fixture request must contain distinct HTML5, CPP, and unknown-target source roots.'
}
if (-not $runtimeTmp.StartsWith($runtime + [IO.Path]::DirectorySeparatorChar,
	[StringComparison]::OrdinalIgnoreCase)) { throw 'Runtime tmp path escaped the private runtime.' }
$actualHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $ExpectedExeSha256.ToLowerInvariant()) {
	throw "Private executable hash mismatch: expected $ExpectedExeSha256, got $actualHash"
}
if (-not (Test-Path -LiteralPath $runtimeTmp -PathType Container)) {
	[void][IO.Directory]::CreateDirectory($runtimeTmp)
}
$runtimeTmpItem = Get-Item -LiteralPath $runtimeTmp -Force
if (($runtimeTmpItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
	throw 'Runtime tmp must not be a symlink or junction.'
}
$resolvedRuntimeTmp = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $runtimeTmp).Path).TrimEnd([char[]]@('\', '/'))
if (-not $resolvedRuntimeTmp.StartsWith($runtime + [IO.Path]::DirectorySeparatorChar,
	[StringComparison]::OrdinalIgnoreCase)) { throw 'Resolved runtime tmp escaped the private runtime.' }
$requestTarget = Join-Path $runtimeTmp 'owner-library-request.json'
if (Test-Path -LiteralPath $requestTarget) { throw "Refusing to overwrite existing private request: $requestTarget" }
$requestBytes = [IO.File]::ReadAllBytes($requestSource)
$requestStream = [IO.File]::Open($requestTarget, [IO.FileMode]::CreateNew,
	[IO.FileAccess]::Write, [IO.FileShare]::None)
try { $requestStream.Write($requestBytes, 0, $requestBytes.Length) } finally { $requestStream.Dispose() }

$runId = [Guid]::NewGuid().ToString('N').Substring(0, 12)
$logRelative = 'tmp/owner-library-' + $runId + '.log'
$stdoutPath = Join-Path $runtimeTmp ('owner-library-' + $runId + '.stdout.log')
$stderrPath = Join-Path $runtimeTmp ('owner-library-' + $runId + '.stderr.log')
$saveRoot = 'tmp/owner-library-save-' + $runId
$envNames = @('CAMMIE_OWNER_LIBRARY_SMOKE', 'CAMMIE_SMOKE_SAVE_ROOT')
$envBefore = @{}
foreach ($name in $envNames) { $envBefore[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$process = $null
try {
	$env:CAMMIE_OWNER_LIBRARY_SMOKE = '1'
	$env:CAMMIE_SMOKE_SAVE_ROOT = $saveRoot
	$arguments = @('--smoke-freeplay', '--smoke-freeplay-scroll-ms', '0',
		'--smoke-duration-ms', [string]$DurationMs, '--smoke-log', $logRelative)
	$process = Start-Process -FilePath $exe -WorkingDirectory $runtime -ArgumentList $arguments `
		-PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
	if (-not $process.WaitForExit(($DurationMs + 90000))) {
		$process.Kill()
		$process.WaitForExit()
		throw 'Owner-library native probe exceeded its bounded process timeout.'
	}
	$process.Refresh()
	if ($process.ExitCode -ne 0) {
		$tail = if (Test-Path -LiteralPath $stderrPath) { (Get-Content -LiteralPath $stderrPath -Tail 40) -join "`n" } else { '' }
		throw "Owner-library native probe exited $($process.ExitCode). $tail"
	}
	$logPath = Join-Path $runtime $logRelative
	if (-not (Test-Path -LiteralPath $logPath -PathType Leaf)) { throw "Missing smoke event log: $logPath" }
	$events = @()
	foreach ($line in Get-Content -LiteralPath $logPath) {
		if (-not $line.StartsWith('RUNTIME_SMOKE|')) { continue }
		try { $events += ($line.Substring('RUNTIME_SMOKE|'.Length) | ConvertFrom-Json) }
		catch { throw "Invalid smoke event in $logPath`: $line" }
	}
	$marker = $events | Where-Object { $_.event -eq 'owner_library_native_verified' } | Select-Object -Last 1
	if ($null -eq $marker) { throw 'The native process exited without the owner_library_native_verified marker.' }
	$success = $events | Where-Object { $_.event -eq 'success' } | Select-Object -Last 1
	if ($null -eq $success) { throw 'The native smoke did not emit its success marker.' }
	[pscustomobject]@{
		verified = $true
		executableSha256 = $actualHash
		runtime = $runtime
		fixture = $fixture
		log = $logPath
		stdout = $stdoutPath
		stderr = $stderrPath
		probe = $marker
		success = $success
	} | ConvertTo-Json -Depth 8
}
finally {
	if ($null -ne $process -and -not $process.HasExited) {
		$process.Kill()
		$process.WaitForExit()
	}
	foreach ($name in $envNames) {
		[Environment]::SetEnvironmentVariable($name, $envBefore[$name], 'Process')
	}
	$resolvedRequest = [IO.Path]::GetFullPath($requestTarget)
	if ($resolvedRequest.StartsWith($runtimeTmpPrefix, [StringComparison]::OrdinalIgnoreCase) -and
		(Test-Path -LiteralPath $resolvedRequest -PathType Leaf)) {
		Remove-Item -LiteralPath $resolvedRequest -Force
	}
}
