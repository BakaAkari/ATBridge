param(
    [string]$BlenderPath,
    [switch]$SmokeTest,
    [switch]$LocalSmokeTest
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

if (-not $BlenderPath) {
    $installed = Get-Command blender -ErrorAction SilentlyContinue
    if ($installed) {
        $BlenderPath = $installed.Source
    } else {
        $association = Get-Item 'Registry::HKEY_CLASSES_ROOT\.blend' -ErrorAction SilentlyContinue
        if ($association) {
            $className = $association.GetValue('')
            $openKey = Get-Item "Registry::HKEY_CLASSES_ROOT\$className\shell\open\command" -ErrorAction SilentlyContinue
            if ($openKey -and $openKey.GetValue('') -match '^"([^"]+)"') {
                $BlenderPath = Join-Path (Split-Path -Parent $Matches[1]) 'blender.exe'
            }
        }
    }
}
if (-not $BlenderPath -or -not (Test-Path -LiteralPath $BlenderPath -PathType Leaf)) {
    throw 'Blender not found. Use -BlenderPath "D:\path\to\blender.exe".'
}
$BlenderPath = (Resolve-Path -LiteralPath $BlenderPath).Path

if ($SmokeTest -and $LocalSmokeTest) {
    throw 'Choose either -SmokeTest or -LocalSmokeTest.'
}
if ($SmokeTest -or $LocalSmokeTest) {
    $testScript = if ($LocalSmokeTest) { 'tests\blender_local_zip_smoke.py' } else { 'tests\blender_inbox_smoke.py' }
    & $BlenderPath --background --factory-startup --disable-autoexec --python-exit-code 1 --python (Join-Path $repoRoot $testScript)
    exit $LASTEXITCODE
}

$bootstrap = Join-Path $PSScriptRoot 'blender_dev.py'
Write-Host "Starting ATBridge from $repoRoot"
Start-Process -FilePath $BlenderPath -WorkingDirectory $repoRoot -ArgumentList @(
    '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', ('"' + $bootstrap + '"')
)
