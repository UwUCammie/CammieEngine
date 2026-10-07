[CmdletBinding()]
param(
	[Parameter(Mandatory=$true)][string]$SeedRuntime,
	[Parameter(Mandatory=$true)][string]$RunId,
	[switch]$StandardServices
)

$ErrorActionPreference = 'Stop'
$expectedPsychRevision = '5c67ced49e5a98535298a6daa3f8f4ec79ac8399'
$songName = 'Achievement Runtime Fixture'
$songFolder = 'achievement-runtime-fixture'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repoRoot = [IO.Path]::GetFullPath($repo).TrimEnd([char[]]@('\', '/'))
$repoPrefix = $repoRoot + [IO.Path]::DirectorySeparatorChar
if (-not [IO.Path]::IsPathRooted($SeedRuntime)) {
	throw 'SeedRuntime must be an explicit absolute path.'
}
if (-not (Test-Path -LiteralPath $SeedRuntime -PathType Container)) {
	throw "The private native seed runtime is missing: $SeedRuntime"
}
$seed = (Resolve-Path -LiteralPath $SeedRuntime).Path
$seed = [IO.Path]::GetFullPath($seed).TrimEnd([char[]]@('\', '/'))
$seedItem = Get-Item -LiteralPath $seed -Force
if (($seedItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
	throw 'SeedRuntime must be a real private directory, not a reparse point.'
}
if ($seed.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase) -or
	$seed.Equals($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'SeedRuntime must be outside the repository checkout.'
}
if (-not (Test-Path -LiteralPath (Join-Path $seed 'Funkin.exe') -PathType Leaf)) {
	throw "The native executable is missing from SeedRuntime: $seed"
}
if ($RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,47}$') {
	throw 'RunId must be 1 to 48 ASCII letters, digits, or hyphens.'
}

$tmpRoot = [IO.Path]::GetFullPath((Join-Path $repo 'tmp')).TrimEnd([char[]]@('\', '/'))
if (-not (Test-Path -LiteralPath $tmpRoot -PathType Container)) {
	throw "The repository tmp output root is missing: $tmpRoot"
}
$tmpItem = Get-Item -LiteralPath $tmpRoot -Force
if (($tmpItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
	throw 'The repository tmp output root must be a real directory, not a reparse point.'
}
$tmpPrefix = $tmpRoot + [IO.Path]::DirectorySeparatorChar
$fixtureDir = [IO.Path]::GetFullPath((Join-Path $tmpRoot "psych-achievements-fixture-$RunId"))
$source = Join-Path $fixtureDir 'source'
if (-not $fixtureDir.StartsWith($tmpPrefix, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'Generated fixture output must stay below the repository tmp directory.'
}
if (Test-Path -LiteralPath $fixtureDir) {
	throw "Refusing to replace an existing fixture output: $fixtureDir"
}

$psychRoot = Join-Path (Split-Path -Parent $repo) 'fnf_sources/FNF-PsychEngine'
if (-not (Test-Path -LiteralPath $psychRoot -PathType Container)) {
	throw "The pinned Psych asset source is missing: $psychRoot"
}
$revisionLines = @(& git -C $psychRoot rev-parse HEAD 2>$null)
$revisionExitCode = $LASTEXITCODE
if ($revisionExitCode -ne 0 -or $revisionLines.Count -ne 1) {
	throw "The Psych asset source must be pinned at $expectedPsychRevision."
}
$revision = [string]$revisionLines[0]
if ($revision -cne $expectedPsychRevision) {
	throw "The Psych asset source must be pinned at $expectedPsychRevision."
}
$trackedStatusLines = @(& git -C $psychRoot status --porcelain --untracked-files=no 2>$null)
$trackedStatusExitCode = $LASTEXITCODE
if ($trackedStatusExitCode -ne 0 -or $trackedStatusLines.Count -ne 0) {
	throw 'The pinned Psych tracked source inputs must be clean before fixture preparation.'
}

$seedFont = Join-Path $seed 'assets/fonts/vcr.ttf'
$seedConfirm = Join-Path $seed 'assets/sounds/confirmMenu.ogg'
$seedAudio = Join-Path $seed 'Templates/spooky/lightning.ogg'
$psychUnknown = Join-Path $psychRoot 'assets/shared/images/unknownMod.png'
$psychPixelIcon = Join-Path $psychRoot 'assets/base_game/shared/images/achievements/week6_nomiss-pixel.png'
$requiredInputs = @($seedFont, $seedConfirm, $seedAudio, $psychUnknown, $psychPixelIcon)
foreach ($inputPath in $requiredInputs) {
	if (-not (Test-Path -LiteralPath $inputPath -PathType Leaf)) {
		throw "A read-only fixture input is missing: $inputPath"
	}
}

$utf8 = [System.Text.UTF8Encoding]::new($false)
$script:readOnlyInputs = @()
function Write-NewTextFile([string]$Path, [string]$Text) {
	$parent = Split-Path -Parent $Path
	[System.IO.Directory]::CreateDirectory($parent) | Out-Null
	$stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew,
		[System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
	$writer = [System.IO.StreamWriter]::new($stream, $utf8)
	try { $writer.Write($Text) } finally { $writer.Dispose() }
}

function Get-InputRecord([string]$Path) {
	$full = [IO.Path]::GetFullPath($Path)
	foreach ($record in $script:readOnlyInputs) {
		if ([IO.Path]::GetFullPath($record.path).Equals($full, [StringComparison]::OrdinalIgnoreCase)) {
			return $record
		}
	}
	$item = Get-Item -LiteralPath $full -Force
	if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
		throw "Refusing a reparse-point fixture input: $full"
	}
	$record = [ordered]@{
		path = $item.FullName
		bytes = $item.Length
		sha256 = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
	}
	$script:readOnlyInputs += $record
	return $record
}

function Assert-InputHash([string]$Path, [long]$Bytes, [string]$Sha256, [string]$Description) {
	if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Description`: $Path" }
	$item = Get-Item -LiteralPath $Path
	$actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
	if (($item.Length -ne $Bytes) -or ($actual -ne $Sha256.ToLowerInvariant())) {
		throw "$Description changed while the fixture was being prepared: $Path"
	}
}

function Copy-FixtureInput([string]$SourcePath, [string]$RelativePath) {
	$record = Get-InputRecord $SourcePath
	$destinationPath = Join-Path $source $RelativePath
	$parent = Split-Path -Parent $destinationPath
	[System.IO.Directory]::CreateDirectory($parent) | Out-Null
	$sourceStream = [System.IO.File]::OpenRead($SourcePath)
	$destinationStream = $null
	try {
		$destinationStream = [System.IO.File]::Open($destinationPath,
			[System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
		$sourceStream.CopyTo($destinationStream)
	} finally {
		if ($null -ne $destinationStream) { $destinationStream.Dispose() }
		$sourceStream.Dispose()
	}
	Assert-InputHash $SourcePath $record.bytes $record.sha256 'Read-only fixture input'
	Assert-InputHash $destinationPath $record.bytes $record.sha256 "Copied fixture input $RelativePath"
}

function Write-FixtureText([string]$RelativePath, [string]$Text) {
	Write-NewTextFile (Join-Path $source $RelativePath) $Text
}

[System.IO.Directory]::CreateDirectory($fixtureDir) | Out-Null
[System.IO.Directory]::CreateDirectory($source) | Out-Null

Write-FixtureText 'Project.xml' @'
<project>
  <app title="Psych Achievement Runtime Fixture" packageName="com.cammie.psychachievementfixture" />
</project>
'@

$chart = @'
{
  "song": {
    "song": "Achievement Runtime Fixture",
    "bpm": 100,
    "speed": 1,
    "needsVoices": false,
    "player1": "bf",
    "player2": "dad",
    "gfVersion": "gf",
    "stage": "stage",
    "notes": [
      {
        "sectionNotes": [[0, 0, 0]],
        "sectionBeats": 4,
        "mustHitSection": false,
        "gfSection": false,
        "bpm": 100,
        "changeBPM": false,
        "altAnim": false
      }
    ],
    "events": []
  }
}
'@
Write-FixtureText "assets/data/$songFolder/$songFolder.json" $chart
Write-FixtureText 'assets/data/achievements.json' @'
[
  {
    "save": "fixture_progress",
    "name": "Fixture Progress",
    "description": "Reach three points in the native API probe.",
    "maxScore": 3,
    "maxDecimals": 2
  },
  {
    "save": "fixture_popup",
    "name": "Fixture Popup",
    "description": "Show the captured owner-scoped toast."
  }
]
'@
Copy-FixtureInput $seedAudio "assets/songs/$songFolder/Inst.ogg"
Copy-FixtureInput $seedFont 'assets/fonts/vcr.ttf'
Copy-FixtureInput $seedConfirm 'assets/sounds/confirmMenu.ogg'
Copy-FixtureInput $psychUnknown 'assets/images/achievements/fixture_progress.png'
Copy-FixtureInput $psychPixelIcon 'assets/images/achievements/fixture_popup-pixel.png'
Copy-FixtureInput $psychUnknown 'assets/images/unknownMod.png'

if ($StandardServices) {
	Write-FixtureText 'assets/shared/data/en-US.lang' @'
English (US)
fixture_phrase: "Shared {1}"
shared_only: "shared layer"
'@
	Write-FixtureText 'assets/data/en-US.lang' @'
English (US)
fixture_phrase: "Hello {1}"
images/fixture.png: "images/translated.png"
achievement_unlocked: "Fixture unlocked!"
'@
	Write-FixtureText 'assets/data/fixture-alt.lang' @'
Fixture language
fixture_phrase: "Reloaded {1}"
'@
}
$sourceResolved = (Resolve-Path -LiteralPath $source).Path
$chartPath = Join-Path $sourceResolved "assets/data/$songFolder/$songFolder.json"
$audioPath = Join-Path $sourceResolved "assets/songs/$songFolder/Inst.ogg"
$achievementsPath = Join-Path $sourceResolved 'assets/data/achievements.json'
$parsedChart = Get-Content -LiteralPath $chartPath -Raw | ConvertFrom-Json -ErrorAction Stop
$parsedAchievements = Get-Content -LiteralPath $achievementsPath -Raw | ConvertFrom-Json -ErrorAction Stop
if ($parsedChart.song.song -ne $songName -or $parsedChart.song.notes.Count -lt 1) {
	throw 'The generated source chart is not a valid one-section Psych chart.'
}
if (($parsedAchievements.Count -ne 2) -or ($parsedAchievements[0].save -ne 'fixture_progress') -or
	($parsedAchievements[0].maxScore -ne 3) -or ($parsedAchievements[0].maxDecimals -ne 2) -or
	($parsedAchievements[1].save -ne 'fixture_popup')) {
	throw 'The generated source achievement fixture has unexpected records.'
}
$audioBytes = [System.IO.File]::ReadAllBytes($audioPath)
if ($audioBytes.Length -lt 1000 -or [System.Text.Encoding]::ASCII.GetString($audioBytes, 0, 4) -ne 'OggS') {
	throw 'The generated chart instrumental is not a non-empty Ogg stream.'
}
$pngHeader = [byte[]](137, 80, 78, 71, 13, 10, 26, 10)
foreach ($relative in @('assets/images/unknownMod.png',
	'assets/images/achievements/fixture_progress.png',
	'assets/images/achievements/fixture_popup-pixel.png')) {
	$imagePath = Join-Path $sourceResolved $relative
	$imageBytes = [System.IO.File]::ReadAllBytes($imagePath)
	if ($imageBytes.Length -lt 8) {
		throw "Generated owner achievement artwork is not a PNG: $relative"
	}
	for ($index = 0; $index -lt $pngHeader.Length; $index++) {
		if ($imageBytes[$index] -ne $pngHeader[$index]) {
			throw "Generated owner achievement artwork is not a PNG: $relative"
		}
	}
}

foreach ($record in $script:readOnlyInputs) {
	Assert-InputHash $record.path $record.bytes $record.sha256 'Read-only seed/donor input'
}
$files = @(Get-ChildItem -LiteralPath $sourceResolved -Recurse -File | Sort-Object FullName | ForEach-Object {
	$relative = $_.FullName.Substring($sourceResolved.Length + 1).Replace('\', '/')
	[ordered]@{
		path = $relative
		bytes = $_.Length
		sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
	}
})
$manifest = [ordered]@{
	schemaVersion = 1
	standardServices = [bool]$StandardServices
	purpose = 'generated Psych retained-import fixture for the owner-scoped achievement native API probe'
	runId = $RunId
	psychDonorRevision = $revision.Trim()
	sourceRoot = $sourceResolved
	importEngine = 'Psych'
	songName = $songName
	songFolder = $songFolder
	chart = "assets/data/$songFolder/$songFolder.json"
	audio = "assets/songs/$songFolder/Inst.ogg"
	achievements = 'assets/data/achievements.json'
	images = [ordered]@{
		fallback = 'assets/images/unknownMod.png'
		progress = 'assets/images/achievements/fixture_progress.png'
		popupPixel = 'assets/images/achievements/fixture_popup-pixel.png'
	}
	readOnlyInputs = $script:readOnlyInputs
	files = $files
	ownerResolution = 'Native probe resolves the owner from the registered imported song and its published compatibility receipt.'
}
$manifestPath = Join-Path $fixtureDir 'fixture.json'
Write-NewTextFile $manifestPath ($manifest | ConvertTo-Json -Depth 10)

Write-Output "Fixture source: $sourceResolved"
Write-Output "Fixture manifest: $manifestPath"
