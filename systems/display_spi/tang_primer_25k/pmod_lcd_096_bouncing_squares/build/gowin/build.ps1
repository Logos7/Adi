$ErrorActionPreference = "Stop"

$gwSh = $env:GOWIN_GWSH
if ([string]::IsNullOrWhiteSpace($gwSh)) {
    $gwSh = "C:\Gowin\Gowin_V1.9.12.02_SP1_x64\IDE\bin\gw_sh.exe"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir
try {
    & $gwSh "build.tcl"
} finally {
    Pop-Location
}
