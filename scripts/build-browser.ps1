param([switch]$SelfContained)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$project = Join-Path $repoRoot 'browser\ATBridge.FabBrowser.csproj'
$buildRoot = Join-Path $repoRoot 'dist\fab-browser'
$buildName = (Get-Date).ToUniversalTime().ToString('yyyyMMdd-HHmmss-fff')
$output = Join-Path $buildRoot $buildName
$contained = if ($SelfContained) { 'true' } else { 'false' }
dotnet publish $project -c Release -r win-x64 --self-contained $contained -o $output
if ($LASTEXITCODE -ne 0) { throw 'Browser build failed.' }
Set-Content -LiteralPath (Join-Path $buildRoot 'current.txt') -Value $buildName -Encoding ascii
Write-Host "Browser ready: $output\ATBridge.FabBrowser.exe"
