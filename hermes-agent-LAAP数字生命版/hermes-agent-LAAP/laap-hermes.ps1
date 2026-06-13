# LAAP Hermes v5.0 PowerShell Alias
# 默认启动 V5.0 全模块版
function laap-hermes {
    $dir = "D:\hermes-agent-LAAP数字生命版\hermes-agent-LAAP"
    if (-not (Test-Path $dir)) {
        Write-Error "LAAP directory not found: $dir"
        return
    }
    Push-Location $dir
    
    if ($args -contains "--hermes") {
        Write-Host "  [LAAP] Pure Hermes mode" -ForegroundColor Gray
        python "laap-hermes-v5" "--hermes"
    } elseif ($args -contains "--v4-bridge") {
        Write-Host "  [LAAP] V4 Lightweight Bridge" -ForegroundColor Cyan
        python "laap-hermes-v5" "--v4-bridge"
    } else {
        Write-Host ""
        Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Yellow
        Write-Host "  ║   ★ LAAP V5.0 — Advanced Cognitive Agent  ║" -ForegroundColor Yellow
        Write-Host "  ║   32 Classes | 123 Knowledge Facts         ║" -ForegroundColor DarkYellow
        Write-Host "  ║   9/9 Benchmark Passed                     ║" -ForegroundColor DarkYellow
        Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Yellow
        Write-Host ""
        python "laap-hermes-v5"
    }
    
    Pop-Location
}

# Short alias
Set-Alias -Name lh -Value laap-hermes -Scope Global

# V4.5 legacy alias (keep for backward compat)
function laap-hermes-v4 {
    $dir = "D:\hermes-agent-LAAP数字生命版\hermes-agent-LAAP"
    Push-Location $dir
    python "laap-hermes"
    Pop-Location
}
Set-Alias -Name lh4 -Value laap-hermes-v4 -Scope Global
