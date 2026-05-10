$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$impl = Join-Path $root "impl"

if (Test-Path $impl) {
    Remove-Item -Recurse -Force $impl
}

Write-Host "Cleaned: $impl"
Write-Host "Open hdmi_320x200_1bpp_v2.gprj and make sure top module is video_top."
