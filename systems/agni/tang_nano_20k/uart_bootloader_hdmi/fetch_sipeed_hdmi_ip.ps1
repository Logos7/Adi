$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outDir = Join-Path $projectDir "rtl\vendor\sipeed_hdmi"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$files = @(
    @{
        Url = "https://raw.githubusercontent.com/sipeed/TangNano-20K-example/main/hdmi/src/dvi_tx/dvi_tx.v"
        Out = "dvi_tx.v"
    },
    @{
        Url = "https://raw.githubusercontent.com/sipeed/TangNano-20K-example/main/hdmi/src/gowin_rpll/TMDS_rPLL.v"
        Out = "TMDS_rPLL.v"
    }
)

foreach ($file in $files) {
    $target = Join-Path $outDir $file.Out
    Write-Host "Downloading $($file.Out)..."
    Invoke-WebRequest -Uri $file.Url -OutFile $target
}

Write-Host "Done. Files written to: $outDir"
