# LAAP Hermes v5.0 PowerShell Alias
# Add this to your PowerShell profile for 'laap-hermes-v5' command
function laap-hermes-v5 {
    $dir = "D:\hermes-agent-LAAP数字生命版\hermes-agent-LAAP"
    if (-not (Test-Path $dir)) {
        Write-Error "LAAP directory not found: $dir"
        return
    }
    Push-Location $dir
    if ($args -contains "--hermes") {
        python "laap-hermes-v5" "--hermes"
    } else {
        python "laap-hermes-v5"
    }
    Pop-Location
}

# Short alias
Set-Alias -Name lh5 -Value laap-hermes-v5 -Scope Global
