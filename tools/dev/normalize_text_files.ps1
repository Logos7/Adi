$ErrorActionPreference = "Stop"

$repo = git rev-parse --show-toplevel
Set-Location $repo

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$utf8Strict = [System.Text.UTF8Encoding]::new($false, $true)

$binaryPattern = '\.(png|jpe?g|gif|ico|zip|tar\.gz|vsix|fs|bit|bin|exe|dll|pdf)$'
$crlfPattern = '\.(bat|cmd|ps1)$'

$files = git ls-files

foreach ($file in $files) {
    if ($file -match $binaryPattern) {
        continue
    }

    $path = Join-Path $repo $file

    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        continue
    }

    $bytes = [System.IO.File]::ReadAllBytes($path)

    if ($bytes -contains 0) {
        Write-Host "skip binary-like file: $file"
        continue
    }

    try {
        $text = $utf8Strict.GetString($bytes)
    }
    catch {
        Write-Host "skip non-utf8 file: $file"
        continue
    }

    $text = $text -replace "`r`n", "`n"
    $text = $text -replace "`r", "`n"

    if ($file -match $crlfPattern) {
        $text = $text -replace "`n", "`r`n"
    }

    [System.IO.File]::WriteAllText($path, $text, $utf8NoBom)
}

git add --renormalize .
