# Builds release packages from the working tree:
#   dist/release/<tag>/ATBridge_<tag>.zip              add-on only (all platforms)
#   dist/release/<tag>/ATBridge_<tag>_windows-x64.zip  add-on + self-contained Fab browser
#   dist/release/<tag>/SHA256SUMS.txt
# Usage: powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1 [-Suffix beta.1] [-SkipBrowser]
param([string]$Suffix = '', [switch]$SkipBrowser)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

$init = Get-Content -Raw -LiteralPath (Join-Path $repoRoot '__init__.py')
if ($init -notmatch '"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)') { throw 'bl_info version not found.' }
$version = "$($Matches[1]).$($Matches[2]).$($Matches[3])"
$tag = if ($Suffix) { "v$version-$Suffix" } else { "v$version" }

$out = Join-Path $repoRoot "dist\release\$tag"
if (Test-Path $out) { Remove-Item -Recurse -Force $out }
$stage = Join-Path $out 'stage\ATBridge'
New-Item -ItemType Directory -Force $stage | Out-Null

# Only runtime add-on content goes into the package.
$include = @('__init__.py', 'config.py', 'LICENSE', 'assets', 'compat', 'core', 'locales', 'operators',
             'preferences', 'properties', 'server', 'state', 'tools', 'ui', 'utils')
foreach ($item in $include) {
    $src = Join-Path $repoRoot $item
    if (-not (Test-Path $src)) { throw "Missing package item: $item" }
    Copy-Item -Recurse -Force $src (Join-Path $stage $item)
}
Get-ChildItem -Recurse -Force $stage -Include '__pycache__', '*.pyc', '*.pyo', '.DS_Store' |
    Remove-Item -Recurse -Force

function New-Zip([string]$name) {
    $zip = Join-Path $out $name
    Compress-Archive -Path $stage -DestinationPath $zip -CompressionLevel Optimal
    return $zip
}

$zips = @(New-Zip "ATBridge_$tag.zip")

if (-not $SkipBrowser) {
    $bin = Join-Path $stage 'bin\fab-browser'
    dotnet publish (Join-Path $repoRoot 'browser\ATBridge.FabBrowser.csproj') -c Release -r win-x64 `
        --self-contained true -p:Version=$version -p:DebugType=none -o $bin
    if ($LASTEXITCODE -ne 0) { throw 'Browser publish failed.' }
    if (-not (Test-Path (Join-Path $bin 'ATBridge.FabBrowser.exe'))) { throw 'Browser executable missing.' }
    $zips += New-Zip "ATBridge_${tag}_windows-x64.zip"
}

Remove-Item -Recurse -Force (Join-Path $out 'stage')
$sums = foreach ($zip in $zips) {
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zip).Hash.ToLower()
    "$hash  $(Split-Path -Leaf $zip)"
}
Set-Content -LiteralPath (Join-Path $out 'SHA256SUMS.txt') -Value $sums -Encoding ascii
Get-ChildItem $out | ForEach-Object { '{0,10:N1} MB  {1}' -f ($_.Length / 1MB), $_.Name }
