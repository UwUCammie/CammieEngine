[CmdletBinding()]
param(
	[Parameter(Mandatory=$true)][string]$SeedRuntime,
	[string]$RunId,
	[ValidateSet('None', 'Branding', 'Video', 'SkipBranding', 'AbortBranding')]
	[string]$SplashMode = 'None'
)

$ErrorActionPreference = 'Stop'
$allowedSplashModes = @('None', 'Branding', 'Video', 'SkipBranding', 'AbortBranding')
if (-not ($allowedSplashModes -ccontains $SplashMode)) {
	throw 'SplashMode must use the exact case: None, Branding, Video, SkipBranding, or AbortBranding.'
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repoRoot = [IO.Path]::GetFullPath($repo).TrimEnd([char[]]@('\', '/'))
$repoPrefix = $repoRoot + [IO.Path]::DirectorySeparatorChar
if (-not [IO.Path]::IsPathRooted($SeedRuntime)) {
	throw 'SeedRuntime must be an explicit absolute path.'
}
if (-not (Test-Path -LiteralPath $SeedRuntime -PathType Container)) {
	throw "The private native runtime seed directory is missing: $SeedRuntime"
}
$runtime = (Resolve-Path -LiteralPath $SeedRuntime).Path
$runtime = [IO.Path]::GetFullPath($runtime).TrimEnd([char[]]@('\', '/'))
$runtimeItem = Get-Item -LiteralPath $runtime -Force
if (($runtimeItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
	throw 'SeedRuntime must be a real private directory, not a reparse point.'
}
if ($runtime.StartsWith($repoPrefix, [StringComparison]::OrdinalIgnoreCase) -or
	$runtime.Equals($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'SeedRuntime must be outside the repository checkout.'
}
if (-not (Test-Path -LiteralPath (Join-Path $runtime 'Funkin.exe') -PathType Leaf)) {
	throw "The isolated native runtime executable is missing: $runtime"
}

if ([string]::IsNullOrWhiteSpace($RunId)) {
	$RunId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
}
if ($RunId -notmatch '^[A-Za-z0-9][A-Za-z0-9-]{0,47}$') {
	throw 'RunId must be 1 to 48 ASCII letters, digits, or hyphens.'
}

$tmpRoot = [IO.Path]::GetFullPath((Join-Path $repo 'tmp')).TrimEnd([char[]]@('\', '/'))
if (-not (Test-Path -LiteralPath $tmpRoot -PathType Container)) {
	throw "The repository tmp directory is missing: $tmpRoot"
}
$tmpItem = Get-Item -LiteralPath $tmpRoot -Force
if (($tmpItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
	throw 'The repository tmp output root must be a real directory, not a reparse point.'
}
$tmpPrefix = $tmpRoot + [IO.Path]::DirectorySeparatorChar
$fixtureDir = [IO.Path]::GetFullPath((Join-Path $tmpRoot "nv-retained-state-native-$RunId"))
$source = Join-Path $fixtureDir 'source'
if (-not $fixtureDir.StartsWith($tmpPrefix, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'Generated fixture output must stay below the repository tmp directory.'
}
if (Test-Path -LiteralPath $fixtureDir) {
	throw "Refusing to replace an existing fixture output: $fixtureDir"
}

$runtimeAssets = Join-Path $runtime 'assets'
$vcrFontSource = Join-Path $runtimeAssets 'fonts/vcr.ttf'
$nightmareVisionSource = Join-Path (Split-Path -Parent $repo) 'fnf_sources/NightmareVision'
$consolasFontSource = Join-Path $nightmareVisionSource 'assets/embeds/fonts/consolas.ttf'
$brandingWatermarkSource = Join-Path $nightmareVisionSource 'assets/game/images/branding/watermarks/NMV.png'
$menuMusicSource = Join-Path $runtimeAssets 'music/freakyMenu.ogg'
$audioSource = Join-Path $runtime 'Templates/spooky/lightning.ogg'
$videoIntroSource = Join-Path (Split-Path -Parent $repo) 'fnf_example_mods/nightmare vision/dsides_r_11_final/content/new-dsides/videos/intro.mp4'
$brandingSplashMode = @('Branding', 'SkipBranding', 'AbortBranding') -contains $SplashMode
$readOnlyInputPaths = @($vcrFontSource, $consolasFontSource, $menuMusicSource, $audioSource)
if ($brandingSplashMode) { $readOnlyInputPaths += $brandingWatermarkSource }
if ($SplashMode -eq 'Video') { $readOnlyInputPaths += $videoIntroSource }
foreach ($required in $readOnlyInputPaths) {
	if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
		throw "A read-only runtime seed input is missing: $required"
	}
}

$seedInputs = $readOnlyInputPaths | ForEach-Object {
	$item = Get-Item -LiteralPath $_
	[ordered]@{ path = $item.FullName; bytes = $item.Length; sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLowerInvariant() }
}

$utf8 = [System.Text.UTF8Encoding]::new($false)
function Write-NewTextFile([string]$Path, [string]$Text) {
	$parent = Split-Path -Parent $Path
	[System.IO.Directory]::CreateDirectory($parent) | Out-Null
	$stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
	$writer = [System.IO.StreamWriter]::new($stream, $utf8)
	try { $writer.Write($Text) } finally { $writer.Dispose() }
}

function Write-FixtureText([string]$RelativePath, [string]$Text) {
	$path = Join-Path $source $RelativePath
	$parent = Split-Path -Parent $path
	[System.IO.Directory]::CreateDirectory($parent) | Out-Null
	Write-NewTextFile $path $Text
}

function Copy-FixtureInput([string]$SourcePath, [string]$RelativePath) {
	$path = Join-Path $source $RelativePath
	$parent = Split-Path -Parent $path
	[System.IO.Directory]::CreateDirectory($parent) | Out-Null
	$sourceStream = [System.IO.File]::OpenRead($SourcePath)
	$destinationStream = $null
	try {
		$destinationStream = [System.IO.File]::Open($path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
		$sourceStream.CopyTo($destinationStream)
	} finally {
		if ($null -ne $destinationStream) { $destinationStream.Dispose() }
		$sourceStream.Dispose()
	}
}

function Get-SeedRecord([string]$SourcePath) {
	$full = [IO.Path]::GetFullPath($SourcePath)
	foreach ($record in $seedInputs) {
		if ([IO.Path]::GetFullPath($record.path).Equals($full, [StringComparison]::OrdinalIgnoreCase)) { return $record }
	}
	throw "Missing recorded read-only input: $SourcePath"
}

[System.IO.Directory]::CreateDirectory($fixtureDir) | Out-Null
[System.IO.Directory]::CreateDirectory($source) | Out-Null

# This package id is the scanner's structural NMV proof. Both family members
# are direct children of content/ and keep a direct, package-local meta.json.
Write-FixtureText 'Project.xml' @'
<project>
  <app title="Retained NV Source State Fixture" packageName="com.nmvTeam.nightmareEngine" />
</project>
'@

# One valid NMV2 normal chart and one real Ogg audio file exercise the full
# retained import/conversion path. The Ogg is copied from the isolated runtime
# seed's shipped spooky template; no donor or seed file is modified.
$chart = @'
{
  "song": {
    "song": "Retained State Fixture",
    "format": "nmv2",
    "keys": 4,
    "lanes": 2,
    "bpm": 120,
    "speed": 1,
    "needsVoices": false,
    "player1": "bf",
    "player2": "dad",
    "gfVersion": "gf",
    "notes": [
      { "mustHitSection": false, "sectionBeats": 4, "sectionNotes": [[0, 0, 0]] }
    ]
  }
}
'@
Write-FixtureText 'content/alpha/meta.json' '{"name":"alpha","windowTitle":"Retained NV alpha","defaultFont":"vcr.ttf","uiPrefix":"fixture-ui/","defaultTransition":"none","stateRedirects":{}}'
Write-FixtureText 'content/alpha/assets/songs/retained-state-fixture/data/normal.json' $chart
Copy-FixtureInput $audioSource 'content/alpha/assets/songs/retained-state-fixture/audio/Inst.ogg'
Write-FixtureText 'content/alpha/assets/data/shared.txt' 'alpha-package-data'
Write-FixtureText 'content/alpha/assets/scripts/plugins/FixtureInit.hx' @'
import funkin.Mods;
import funkin.states.TitleState;
import funkin.backend.MusicBeatState;
import funkin.backend.MusicBeatSubstate;
import funkin.data.FunkinTransitionState;
import funkin.data.Highscore;
import funkin.scripting.ScriptedState;

var __nvFixtureInitDone = false;
function onLoad() {
  if (__nvFixtureInitDone) return;
  __nvFixtureInitDone = true;
  Probe.mark('plugin-load', script.interp.parent);

  var initial = Highscore.getScore('retained-state-probe', 0);
  var formatted = Highscore.formatSong('Retained State Fixture', 0);
  Highscore.saveScore('Retained State Fixture', 17, 0, 0.5);
  Highscore.load();
  var reloaded = Highscore.getScore('Retained State Fixture', 0);
  Probe.mark('highscore-bound', {initial:initial, formatted:formatted, reloaded:reloaded});
  Probe.mark('start-meta-title-class', Main.startMeta.initialState == TitleState
    && Main.startMeta.skipSplash == Probe.skipSplash);
  if (Main.startMeta.skipSplash != Probe.skipSplash) throw 'Source Main splash metadata differs from probe mode';
  if (Main.startMeta.startFullScreen != false) throw 'Source Main fullscreen metadata differs';
  var mainClass = Type.resolveClass('Main');
  if (mainClass != Main || Reflect.fields(Main).indexOf('onResize') < 0
      || Type.getClassFields(mainClass).indexOf('resetSpriteCache') < 0)
    throw 'Source Main reflected helpers differ';
  Probe.verifyMain(mainClass, Main.resetSpriteCache, Reflect.field(mainClass, 'resetSpriteCache'),
    Reflect.field(mainClass, 'onResize'));

  Mods.currentModDirectory = 'beta';
  Mods.updateModList();
  Mods.loadTopMod();
  var empty = new MusicBeatState();
  Probe.mark('constructed-base', empty);
  empty.destroy();
  var sub = new MusicBeatSubstate();
  Probe.mark('constructed-substate', sub);
  sub.destroy();
  var direct = new ScriptedState('FixtureDirect');
  direct.destroy();

  MusicBeatState.transitionInState = FunkinTransitionState.NONE;
  MusicBeatState.transitionOutState = FunkinTransitionState.NONE;
  FlxG.switchState(() -> { new TitleState(); });
}
'@
Copy-FixtureInput $vcrFontSource 'content/alpha/assets/fonts/vcr.ttf'
Copy-FixtureInput $menuMusicSource 'content/alpha/assets/music/freakyMenu.ogg'

# beta intentionally contains no chart rows. Its direct metadata and state
# scripts must be published through the retained v2 family catalog.
Write-FixtureText 'content/beta/meta.json' '{"name":"beta","windowTitle":"State fixture beta","defaultFont":"vcr.ttf","uiPrefix":"fixture-ui/","defaultTransition":"none","stateRedirects":{"TitleState":"FixtureTitle"}}'
Write-FixtureText 'content/beta/assets/data/shared.txt' 'beta-package-data'
Write-FixtureText 'content/beta/assets/scripts/states/FixtureTitle.hx' @'
var __redirectLoadMarked = false;
var __redirectCreateMarked = false;
var __redirectDestroyMarked = false;
var __probeResetRequested = false;
function onLoad() {
  if (__redirectLoadMarked) return;
  __redirectLoadMarked = true;
  Probe.mark('redirect-load', script.interp.parent);
}
function onCreate() {
  if (__redirectCreateMarked) return;
  __redirectCreateMarked = true;
  add(new FlxSprite(80, 160).makeGraphic(900, 300, 0xFF286EF0));
  var label = new FlxText(110, 210, 840, 'Source scripted title, selected package beta', 26);
  label.setFormat(Paths.DEFAULT_FONT, 26, 0xFFFFFFFF);
  add(label);
  Probe.mark('redirect-create', script.interp.parent);
}
function onDestroy() {
  if (__redirectDestroyMarked) return;
  __redirectDestroyMarked = true;
  Probe.mark('redirect-destroy', script.interp.parent);
}
function onProbeReset() {
  if (__probeResetRequested) return;
  __probeResetRequested = true;
  FlxG.resetState();
}
'@
Write-FixtureText 'content/beta/assets/scripts/states/FixtureDirect.hx' @'
var __directLoadMarked = false;
var __directDestroyMarked = false;
function onLoad() {
  if (__directLoadMarked) return;
  __directLoadMarked = true;
  Probe.mark('direct-state-load', script.interp.parent);
}
function onDestroy() {
  if (__directDestroyMarked) return;
  __directDestroyMarked = true;
  Probe.mark('direct-state-destroy', script.interp.parent);
}
'@
Write-FixtureText 'content/beta/assets/scripts/states/TitleState.hx' @'
var __nativeTitleLoadMarked = false;
var __nativeTitleIntroDrawn = false;
var __nativeTitleCreateMarked = false;
function onLoad() {
  if (__nativeTitleLoadMarked) return;
  __nativeTitleLoadMarked = true;
  Probe.mark('native-title-load', script.interp.parent);
}
function onStartIntro() {
  if (__nativeTitleIntroDrawn) return Function_Stop;
  __nativeTitleIntroDrawn = true;
  add(new FlxSprite(80, 160).makeGraphic(900, 300, 0xFFD82A44));
  var label = new FlxText(110, 210, 840, 'Source native title with authored onStartIntro override', 26);
  label.setFormat(Paths.DEFAULT_FONT, 26, 0xFFFFFFFF);
  add(label);
  return Function_Stop;
}
function onCreatePost() {
  if (__nativeTitleCreateMarked) return;
  __nativeTitleCreateMarked = true;
  Probe.mark('native-title-create', script.interp.parent);
}
'@
Copy-FixtureInput $vcrFontSource 'content/beta/assets/fonts/vcr.ttf'
Copy-FixtureInput $menuMusicSource 'content/beta/assets/music/freakyMenu.ogg'

# A tiny root-owned source asset gives the family importer a real engine core
# subtree to retain below each package's __nmv_core/ path.
Write-FixtureText 'assets/data/retained-source-core.txt' 'game-root-core-data'
Copy-FixtureInput $consolasFontSource 'assets/fonts/consolas.ttf'

if ($brandingSplashMode) {
	Copy-FixtureInput $brandingWatermarkSource 'content/beta/assets/images/branding/watermarks/NMV.png'
	Copy-FixtureInput $audioSource 'content/beta/assets/sounds/intro.ogg'
}
if ($SplashMode -eq 'Video') {
	Copy-FixtureInput $videoIntroSource 'content/beta/assets/videos/intro.mp4'
}

$sourceResolved = (Resolve-Path $source).Path
$files = @(Get-ChildItem -LiteralPath $sourceResolved -Recurse -File | Sort-Object FullName | ForEach-Object {
	$relative = $_.FullName.Substring($sourceResolved.Length + 1).Replace('\', '/')
	[ordered]@{ path = $relative; bytes = $_.Length; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant() }
})
$requiredOggPath = Join-Path $sourceResolved 'content/alpha/assets/songs/retained-state-fixture/audio/Inst.ogg'
$oggBytes = [System.IO.File]::ReadAllBytes($requiredOggPath)
if ($oggBytes.Length -lt 1000 -or [System.Text.Encoding]::ASCII.GetString($oggBytes, 0, 4) -ne 'OggS') {
	throw 'The generated audio is not a non-empty Ogg stream.'
}
$chartPath = Join-Path $sourceResolved 'content/alpha/assets/songs/retained-state-fixture/data/normal.json'
$null = Get-Content -LiteralPath $chartPath -Raw | ConvertFrom-Json -ErrorAction Stop
if (Test-Path -LiteralPath (Join-Path $sourceResolved 'content/beta/assets/songs')) {
	throw 'The chartless beta sibling unexpectedly has a songs directory.'
}

function Assert-FixtureHash([string]$Path, [long]$Bytes, [string]$Sha256, [string]$Description) {
	if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing $Description`: $Path" }
	$item = Get-Item -LiteralPath $Path
	$actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
	if (($item.Length -ne $Bytes) -or ($actual -ne $Sha256.ToLowerInvariant())) {
		throw "$Description changed while the fixture was being prepared: $Path"
	}
}
$vcrInput = Get-SeedRecord $vcrFontSource
$consolasInput = Get-SeedRecord $consolasFontSource
$menuMusicInput = Get-SeedRecord $menuMusicSource
$audioInput = Get-SeedRecord $audioSource
Assert-FixtureHash (Join-Path $sourceResolved 'content/alpha/assets/fonts/vcr.ttf') $vcrInput.bytes $vcrInput.sha256 'Copied VCR font'
Assert-FixtureHash (Join-Path $sourceResolved 'assets/fonts/consolas.ttf') $consolasInput.bytes $consolasInput.sha256 'Copied Consolas donor font'
Assert-FixtureHash (Join-Path $sourceResolved 'content/alpha/assets/music/freakyMenu.ogg') $menuMusicInput.bytes $menuMusicInput.sha256 'Copied alpha menu music'
Assert-FixtureHash (Join-Path $sourceResolved 'content/beta/assets/fonts/vcr.ttf') $vcrInput.bytes $vcrInput.sha256 'Copied beta VCR font'
Assert-FixtureHash (Join-Path $sourceResolved 'content/beta/assets/music/freakyMenu.ogg') $menuMusicInput.bytes $menuMusicInput.sha256 'Copied beta menu music'
Assert-FixtureHash $requiredOggPath $audioInput.bytes $audioInput.sha256 'Copied fixture chart audio'
if ($brandingSplashMode) {
	$watermarkInput = Get-SeedRecord $brandingWatermarkSource
	Assert-FixtureHash (Join-Path $sourceResolved 'content/beta/assets/images/branding/watermarks/NMV.png') $watermarkInput.bytes $watermarkInput.sha256 'Copied donor NMV watermark'
	Assert-FixtureHash (Join-Path $sourceResolved 'content/beta/assets/sounds/intro.ogg') $audioInput.bytes $audioInput.sha256 'Copied source splash sound'
}
if ($SplashMode -eq 'Video') {
	$videoInput = Get-SeedRecord $videoIntroSource
	Assert-FixtureHash (Join-Path $sourceResolved 'content/beta/assets/videos/intro.mp4') $videoInput.bytes $videoInput.sha256 'Copied donor intro video'
}
foreach ($seedRecord in $seedInputs) {
	Assert-FixtureHash $seedRecord.path $seedRecord.bytes $seedRecord.sha256 'Read-only seed input'
}

$splashAssets = [ordered]@{}
if ($SplashMode -eq 'Video') {
	$splashAssets = [ordered]@{ video = 'content/beta/assets/videos/intro.mp4' }
} elseif ($brandingSplashMode) {
	$splashAssets = [ordered]@{ watermark = 'content/beta/assets/images/branding/watermarks/NMV.png'; sound = 'content/beta/assets/sounds/intro.ogg' }
}
$markers = @('nv_state_retained_import_verified', 'plugin-load:alpha', 'highscore-bound:source', 'start-meta-title-class:source', 'constructed-base:source', 'constructed-substate:source', 'direct-state-load:beta', 'direct-state-destroy:beta', 'redirect-load:beta', 'redirect-create:beta', 'redirect-destroy:beta', 'native-title-load:beta', 'native-title-create:beta', 'nv_state_verified')
if ($SplashMode -ne 'None') { $markers += 'nv_splash_verified' }

$manifest = [ordered]@{
	schemaVersion = 1
	purpose = 'generated structurally authenticated Nightmare Vision native importer to source-state fixture'
	runId = $RunId
	splashMode = $SplashMode
	sourceRoot = $sourceResolved
	importEngine = 'Nightmare Vision'
	projectPackageName = 'com.nmvTeam.nightmareEngine'
	packages = @(
		[ordered]@{ directory = 'alpha'; directMeta = 'content/alpha/meta.json'; chart = 'content/alpha/assets/songs/retained-state-fixture/data/normal.json'; audio = 'content/alpha/assets/songs/retained-state-fixture/audio/Inst.ogg'; plugin = 'content/alpha/assets/scripts/plugins/FixtureInit.hx'; stateFiles = @() },
		[ordered]@{ directory = 'beta'; directMeta = 'content/beta/meta.json'; chartless = $true; stateFiles = @('content/beta/assets/scripts/states/FixtureTitle.hx', 'content/beta/assets/scripts/states/FixtureDirect.hx', 'content/beta/assets/scripts/states/TitleState.hx') }
	)
	splashAssets = $splashAssets
	readOnlySeedInputs = $seedInputs
	files = $files
	markers = $markers
}
$manifestPath = Join-Path $fixtureDir 'fixture.json'
Write-NewTextFile $manifestPath ($manifest | ConvertTo-Json -Depth 8)

$runtimeResolved = (Resolve-Path $runtime).Path
$quotedSource = '"' + $sourceResolved + '"'
$quotedLog = '"tmp/nv-retained-state-import-' + $RunId + '.log"'
$command = "Push-Location '$runtimeResolved'; .\Funkin.exe --smoke-import-source $quotedSource --smoke-import-type 'Nightmare Vision' --smoke-import-timeout-ms 300000 --smoke-import-log $quotedLog; Pop-Location"
$commandPath = Join-Path $fixtureDir 'run-import-command.txt'
Write-NewTextFile $commandPath ($command + [Environment]::NewLine)

Write-Output "Fixture source: $sourceResolved"
Write-Output "Fixture manifest: $manifestPath"
Write-Output "Import log target: $runtimeResolved\tmp\nv-retained-state-import-$RunId.log"
Write-Output "Import command: $command"
