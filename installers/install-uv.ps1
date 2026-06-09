# ----------------------------------------------------------------------------
# LAAP one-liner installer — uv-based (Windows: PowerShell / pwsh)
# ----------------------------------------------------------------------------
# Usage:
#   irm https://laap.dev/install-uv.ps1 | iex
#   iwr https://laap.dev/install-uv.ps1 -UseBasicParsing | iex
#
# What it does:
#   1. Detect / install uv
#   2. `uv tool install laap` — creates an isolated venv and drops a
#      `laap.exe` shim into %USERPROFILE%\.local\bin
#   3. Persist that directory in the user PATH (HKCU\Environment)
#
# Environment overrides:
#   $env:LAAP_VERSION="0.3.0"   install a specific version
#   $env:LAAP_EXTRAS="tui"      pass --with extras
#   $env:LAAP_FROM="git+..."    install from a custom URL
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
    $color = "DarkYellow"
    Write-Host $banner -ForegroundColor $color
}

function Get-IsAdmin {
    $id  = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $pr  = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $pr.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
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
    # also reflect in current process so we can run laap right now
    if ($env:Path -notlike "*$Dir*") {
        $env:Path = "$Dir;$env:Path"
    }
}

function Install-Uv {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $ver = & uv --version
        Write-Host "[laap] uv found: $ver" -ForegroundColor DarkGray
        return
    }
    Write-Host "[laap] uv not found. Installing via the official installer..." -ForegroundColor Yellow
    try {
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    } catch {
        throw "Failed to install uv. Install manually from https://docs.astral.sh/uv/"
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        $localBin = Join-Path $env:USERPROFILE ".local\bin"
        if (Test-Path (Join-Path $localBin "uv.exe")) {
            $env:Path = "$localBin;$env:Path"
        } else {
            throw "uv still not on PATH. Please restart PowerShell and re-run."
        }
    }
    Write-Host "[laap] uv installed: $(& uv --version)" -ForegroundColor Green
}

function Install-Laap {
    $target = "laap"
    $extras = @()
    if ($env:LAAP_FROM)  { $target = $env:LAAP_FROM }
    elseif ($env:LAAP_VERSION) { $target = "laap==$env:LAAP_VERSION" }

    if ($env:LAAP_EXTRAS) { $extras = @("--with", $env:LAAP_EXTRAS) }

    Write-Host "[laap] Installing $target via uv tool..." -ForegroundColor Yellow
    & uv tool install --upgrade @extras $target
    if ($LASTEXITCODE -ne 0) {
        throw "uv tool install failed (exit $LASTEXITCODE)."
    }
}

# ---- main ----------------------------------------------------------------
Write-LaapBanner
Install-Uv
Install-Laap

# Add the uv tool bin directory to the user PATH
$localBin = Join-Path $env:USERPROFILE ".local\bin"
Add-ToUserPath -Dir $localBin

if (Get-Command laap -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-Host "[laap] laap installed successfully." -ForegroundColor Green
    Write-Host "Try it:" -ForegroundColor White
    Write-Host "    laap --version"        -ForegroundColor DarkYellow
    Write-Host "    laap -i"               -ForegroundColor DarkYellow
    Write-Host "    laap -q `"hi`""         -ForegroundColor DarkYellow
    Write-Host "    laap"                  -ForegroundColor DarkYellow
} else {
    Write-Host "[laap] Installation complete. Open a new terminal and type 'laap'." -ForegroundColor Green
}
