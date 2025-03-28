# PowerShell script to activate Python virtual environment
$venvPath = Join-Path -Path $PSScriptRoot -ChildPath "venv"
$activatePath = Join-Path -Path $venvPath -ChildPath "bin/activate.ps1"

# Check if activate.ps1 exists
if (Test-Path $activatePath) {
    & $activatePath
} else {
    # If no PowerShell script, try to create a shell and source the bash version
    Write-Host "No PowerShell activation script found. Using bash activation method..."
    bash -c "source $venvPath/bin/activate && exec pwsh"
}

# Verify python path
Write-Host "Python executable: $(Get-Command python | Select-Object -ExpandProperty Source)"
Write-Host "Python version: $(python --version)"
Write-Host "Virtual environment activated successfully!" 