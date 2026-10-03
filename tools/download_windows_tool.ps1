param(
	[Parameter(Mandatory=$true)][string]$Url,
	[Parameter(Mandatory=$true)][string]$Destination,
	[Parameter(Mandatory=$true)][string]$Required,
	[string]$Sha256 = ""
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$toolsRoot = [IO.Path]::GetFullPath((Join-Path $root '.tools')) + '\'
$destinationPath = [IO.Path]::GetFullPath($Destination)
if (-not $destinationPath.StartsWith($toolsRoot, [StringComparison]::OrdinalIgnoreCase)) {
	throw 'Portable tools must be installed inside this project''s .tools directory'
}
$scratch = Join-Path (Join-Path $root 'tmp') ('download-' + [Guid]::NewGuid())
New-Item -ItemType Directory -Force $scratch | Out-Null
try {
	$zip = Join-Path $scratch 'tool.zip'
	Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $zip
	if ($Sha256 -and (Get-FileHash -Algorithm SHA256 $zip).Hash -ne $Sha256) {
		throw 'Portable tool archive checksum mismatch'
	}
	$unpack = Join-Path $scratch 'unpack'
	Expand-Archive -LiteralPath $zip -DestinationPath $unpack
	$leaf = [IO.Path]::GetFileName($Required)
	$item = Get-ChildItem -LiteralPath $unpack -Filter $leaf -File -Recurse | Select-Object -First 1
	if ($null -eq $item) { throw "Archive did not contain $Required" }
	$source = $item.FullName.Substring(0, $item.FullName.Length - $Required.Length).TrimEnd('\')
	if (-not (Test-Path -LiteralPath (Join-Path $source $Required))) {
		throw "Archive layout did not match $Required"
	}
	# Preserve an existing toolchain (including a copied Linux toolchain).
	# Both source and backup are verified to remain under this project's .tools.
	if (Test-Path -LiteralPath $destinationPath) {
		$backup = $destinationPath + '.previous-' + [Guid]::NewGuid()
		Move-Item -LiteralPath $destinationPath -Destination $backup
	}
	New-Item -ItemType Directory -Force $destinationPath | Out-Null
	Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $destinationPath -Recurse -Force
} finally {
	$checkedScratch = [IO.Path]::GetFullPath($scratch)
	$tmpRoot = [IO.Path]::GetFullPath((Join-Path $root 'tmp')) + '\'
	if ($checkedScratch.StartsWith($tmpRoot, [StringComparison]::OrdinalIgnoreCase)) {
		Remove-Item -LiteralPath $checkedScratch -Recurse -Force
	}
}
