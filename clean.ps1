# Blog Writing Agent - Clean Script for Windows
# This script cleans up generated files and cache

param(
    [switch]$All,
    [switch]$Venv,
    [switch]$Full
)

Write-Host "========================================"
Write-Host "Blog Writing Agent - Cleanup"
Write-Host "========================================"
Write-Host ""

# Clean Python cache
Write-Host "Cleaning Python cache..."
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Include *.pyc -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Include *.pyo -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Include *.egg-info -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "Python cache cleaned"

# Clean generated content if requested
if ($All -or $Full) {
    Write-Host ""
    Write-Host "Cleaning generated content..."
    
    if (Test-Path "images") {
        Get-ChildItem -Path "images" -File | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "Images cleaned"
    }
    
    if (Test-Path "outputs") {
        Get-ChildItem -Path "outputs" -File | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "Outputs cleaned"
    }
    
    Get-ChildItem -Path . -Filter "*.md" -File | 
        Where-Object { $_.Name -ne "README.md" -and $_.Name -ne "QUICKSTART.md" -and $_.Name -ne "PROJECT_STRUCTURE.md" -and $_.Name -ne "WINDOWS_GUIDE.md" -and $_.Name -ne "COMMANDS_CHEATSHEET.md" -and $_.Name -ne "START_HERE.md" } | 
        Remove-Item -Force -ErrorAction SilentlyContinue
    Write-Host "Generated markdown files cleaned"
}

# Clean virtual environment if requested
if ($Venv -or $Full) {
    Write-Host ""
    Write-Host "Removing virtual environment..."
    if (Test-Path "venv") {
        Remove-Item -Path "venv" -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "Virtual environment removed"
    } else {
        Write-Host "No virtual environment found"
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host "Cleanup Complete!"
Write-Host "========================================"
Write-Host ""

if ($Venv -or $Full) {
    Write-Host "To recreate environment, run: .\setup.ps1"
}
