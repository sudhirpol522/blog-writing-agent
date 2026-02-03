# Blog Writing Agent - Run Script for Windows
# This script activates the virtual environment and runs the Streamlit app

param(
    [switch]$Debug
)

Write-Host "========================================"
Write-Host "Blog Writing Agent"
Write-Host "========================================"
Write-Host ""

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "ERROR: Virtual environment not found!"
    Write-Host "Please run: .\setup.ps1"
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"
Write-Host ""

# Check .env file
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!"
    Write-Host "Please run: .\setup.ps1"
    exit 1
}

# Start the application
Write-Host "Starting Streamlit application..."
Write-Host "Open http://localhost:8501 in your browser"
Write-Host ""
Write-Host "Press Ctrl+C to stop the server"
Write-Host ""

if ($Debug) {
    streamlit run app.py --server.port=8501 --logger.level=debug
} else {
    streamlit run app.py --server.port=8501
}
