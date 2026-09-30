param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

# Flixel 6.1.2 can leave _frame null when a sprite has no usable graphic.  The
# native draw path dereferences that frame, so keep the same generated 1x1
# fallback used by run.sh on Linux.  This script is deliberately idempotent:
# haxelib sources are patched only after the pinned package is installed.
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
    throw "FlxSprite.hx was not found at $Path"
}

$source = [System.IO.File]::ReadAllText($Path)
if ($source.Contains("dpui-fallback-frame")) {
    Write-Output ">> flixel empty-frame fallback already patched"
    exit 0
}

$newline = "`n"
if ($source.Contains("`r`n")) {
    $newline = "`r`n"
}

# The pinned haxelib has appeared in both braced and unbraced forms across
# patch-level releases.  Match either form while preserving the file's line
# ending and indentation.
$patterns = @(
    '(?m)^(?<indent>[ \t]*)if \(_frame == null\)\r?\n(?<openIndent>[ \t]*)\{\r?\n(?<loadIndent>[ \t]*)loadGraphic\("flixel/images/logo/default\.png"\);\r?\n(?<closeIndent>[ \t]*)\}',
    '(?m)^(?<indent>[ \t]*)if \(_frame == null\)\r?\n(?<loadIndent>[ \t]*)loadGraphic\("flixel/images/logo/default\.png"\);'
)

$match = $null
foreach ($pattern in $patterns) {
    $candidate = [regex]::Match($source, $pattern)
    if ($candidate.Success) {
        $match = $candidate
        break
    }
}
if ($null -eq $match) {
    throw "The expected FlxSprite.checkEmptyFrame fallback pattern was not found in $Path"
}

$indent = $match.Groups["indent"].Value
$loadIndent = $match.Groups["loadIndent"].Value
$replacementLines = @(
    ($indent + "if (_frame == null)")
    ($indent + "{")
    ($loadIndent + 'loadGraphic("flixel/images/logo/default.png");')
    ($loadIndent + "// local patch (DisappointingPlus): generated 1x1 last resort")
    ($loadIndent + "// keeps native draw() from dereferencing a null _frame")
    ($loadIndent + "if (_frame == null)")
    ($loadIndent + '    makeGraphic(1, 1, 0, true, "dpui-fallback-frame");')
    ($indent + "}")
)

$replacement = [string]::Join($newline, $replacementLines)
$updated = $source.Remove($match.Index, $match.Length).Insert($match.Index, $replacement)

$utf8NoBom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
[System.IO.File]::WriteAllText($Path, $updated, $utf8NoBom)
Write-Output ">> patched flixel checkEmptyFrame null-frame fallback"
