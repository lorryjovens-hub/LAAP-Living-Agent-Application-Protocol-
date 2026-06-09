# ----------------------------------------------------------------------------
# LAAP one-liner installer — universal Windows (PowerShell)
# ----------------------------------------------------------------------------
# Usage:
#   irm https://laap.dev/install.ps1 | iex
#
# Strategy (in order):
#   1. uv  (fast, isolated venv, recommended)
#   2. pipx (if already installed)
#   3. pip --user (last resort)
# ----------------------------------------------------------------------------

$ErrorActionPreference = "Stop"

function Write-LaapBanner {
    $banner = @"
  _      _____    _    ____   ____
 | |    |  __ \  | |  / __ \ / __ \
 | |    | |__) | | | | |  | | |  | |
 | |    |  ___/  | | | |  | | |  | |
 | |____| |      | | | |__| | |__| |
 |______|_|      |_|  \____/ \____/

"@
    Write-Host $banner -ForegroundColor DarkYellow
}

function Add-ToUserPath {
    param([string]$Dir)
    $current = (Get-ItemProperty -Path "HKCU:\Environment" -Name "Path" `
                -ErrorAction SilentlyContinue).Path
    $paths   = if ($current) { $current -split ";" | Where-Object { $_ } } else { @() }
    if ($paths -notcontains $Dir) {
        $new = (@($paths) + $Dir) -join ";"
        [Environment]::SetEnvironmentVariable("Path", $new, "User")
        Write-Host "[laap] Added $Dir to user PATH (restart terminal to apply)." -ForegroundColor Green
    } else {
        Write-Host "[laap] $Dir already on user PATH." -ForegroundColor DarkGray
    }
    if ($env:Path -notlike "*$Dir*") {
        $env:Path = "$Dir;$env:Path"
    }
}

# ---- 1) uv path -----------------------------------------------------------
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "[laap] uv detected, delegating to install-uv.ps1" -ForegroundColor DarkGray
    & (Join-Path $PSScriptRoot "install-uv.ps1")
    return
}

# ---- 2) pipx path ---------------------------------------------------------
if (Get-Command pipx -ErrorAction SilentlyContinue) {
    Write-Host "[laap] pipx detected, using pipx install laap" -ForegroundColor Yellow
    & pipx install laap
    & pipx ensurepath
    Write-Host "[laap] laap installed via pipx." -ForegroundColor Green
    return
}

# ---- 3) pip --user fallback ----------------------------------------------
$python = $null
foreach ($cand in @("python3", "python", "py")) {
    $found = Get-Command $cand -ErrorAction SilentlyContinue
    if ($found) {
        $ver = & $found.Path -c "import sys; v=sys.version_info; print('%d.%d'%(v[0],v[1]))"
        if ($ver -and $ver -ge "3.10") { $python = $found.Path; break }
    }
}
if (-not $python) {
    throw "Python 3.10+ is required. Install from https://python.org"
}

Write-Host "[laap] Using $python" -ForegroundColor DarkGray
& $python -m pip install --user --upgrade laap
if ($LASTEXITCODE -ne 0) {
    throw "pip install laap failed (exit $LASTEXITCODE)."
}

$localBin = Join-Path $env:USERPROFILE ".local\bin"
Add-ToUserPath -Dir $localBin

if (Get-Command laap -ErrorAction SilentlyContinue) {
    Write-Host "[laap] laap installed: $((& laap --version 2>&1 | Select-Object -First 1))" -ForegroundColor Green
} else {
    Write-Host "[laap] Installation complete. Open a new terminal and type 'laap'." -ForegroundColor Green
}
