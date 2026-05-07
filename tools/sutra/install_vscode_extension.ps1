$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$source = Join-Path $toolsDir "sutra-vscode"
$packageJson = Join-Path $source "package.json"

if (-not (Test-Path $packageJson)) {
    throw "Nie znaleziono package.json extensiona Sutra: $packageJson"
}

$pkg = Get-Content $packageJson -Raw | ConvertFrom-Json
$folderName = "$($pkg.publisher).$($pkg.name)-$($pkg.version)"
$vsix = Join-Path $source "sutra-$($pkg.version).vsix"

Write-Host "Sutra VS Code extension: $($pkg.displayName) $($pkg.version)"
Write-Host "Źródło: $source"

function Install-ByCopy($root) {
    if ([string]::IsNullOrWhiteSpace($root)) { return }
    $destRoot = Join-Path $root "extensions"
    $dest = Join-Path $destRoot $folderName
    New-Item -ItemType Directory -Force -Path $destRoot | Out-Null
    if (Test-Path $dest) {
        Remove-Item -Recurse -Force $dest
    }
    Copy-Item -Recurse -Force $source $dest
    Write-Host "Skopiowano do: $dest"
}

function Try-Install-WithCli($commandName) {
    $cmd = Get-Command $commandName -ErrorAction SilentlyContinue
    if ($null -eq $cmd) { return $false }
    if (-not (Test-Path $vsix)) { return $false }
    Write-Host "Instaluję przez CLI: $commandName --install-extension $vsix --force"
    & $commandName --install-extension $vsix --force
    return $true
}

$installedByCli = $false
$installedByCli = (Try-Install-WithCli "code") -or $installedByCli
$installedByCli = (Try-Install-WithCli "code-insiders") -or $installedByCli
$installedByCli = (Try-Install-WithCli "cursor") -or $installedByCli

Install-ByCopy (Join-Path $env:USERPROFILE ".vscode")
Install-ByCopy (Join-Path $env:USERPROFILE ".vscode-insiders")
Install-ByCopy (Join-Path $env:USERPROFILE ".cursor")

Write-Host ""
Write-Host "Gotowe. Teraz zamknij WSZYSTKIE okna VS Code/Cursor i otwórz ponownie."
Write-Host "Test: Ctrl+Shift+P -> 'Change Language Mode' -> powinno być 'Sutra'."
Write-Host "Jeśli dalej nie ma, uruchom: code --list-extensions | findstr /i sutra"
