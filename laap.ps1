#!/usr/bin/env pwsh
# LAAP Universal Launcher for PowerShell
$LAAP_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Try system Python first
$python = "python"
if (Test-Path "C:\Python313\python.exe") { $python = "C:\Python313\python.exe" }
if (Test-Path "C:\Python312\python.exe") { $python = "C:\Python312\python.exe" }

# Launch
& $python "$LAAP_DIR\laap.py" @args
if ($LASTEXITCODE -ne 0) {
    # Fallback
    & python "$LAAP_DIR\laap.py" @args
}
