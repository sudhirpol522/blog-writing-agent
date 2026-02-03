# Blog Writing Agent - Setup Script for Windows
# This script sets up the project with a virtual environment

Write-Host "========================================"
Write-Host "Blog Writing Agent - Setup"
Write-Host "========================================"
Write-Host ""

# Check Python installation
Write-Host "Checking Python installation..."
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    Write-Host "ERROR: Python not found. Please install Python 3.11 or higher."
    exit 1
}
$pythonVersion = python --version
Write-Host "Found: $pythonVersion"
Write-Host ""

# Create virtual environment
Write-Host "Creating virtual environment..."
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists"
} else {
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Virtual environment created"
    } else {
        Write-Host "ERROR: Failed to create virtual environment"
        exit 1
    }
}
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..."
& ".\venv\Scripts\Activate.ps1"
Write-Host ""

# Upgrade pip
Write-Host "Upgrading pip..."
python -m pip install --upgrade pip --quiet
Write-Host "Pip upgraded"
Write-Host ""

# Install dependencies
Write-Host "Installing dependencies (this may take a few minutes)..."
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "Dependencies installed successfully"
} else {
    Write-Host "ERROR: Failed to install dependencies"
    exit 1
}
Write-Host ""

# Create .env file
Write-Host "Setting up environment file..."
if (Test-Path ".env") {
    Write-Host ".env file already exists"
} else {
    Copy-Item ".env.example" ".env"
    Write-Host ".env file created"
    Write-Host "IMPORTANT: Edit .env and add your API keys!"
}
Write-Host ""

# Create directories
Write-Host "Creating directories..."
if (-not (Test-Path "images")) {
    New-Item -ItemType Directory -Path "images" | Out-Null
}
if (-not (Test-Path "outputs")) {
    New-Item -ItemType Directory -Path "outputs" | Out-Null
}
Write-Host "Directories created"
Write-Host ""

# Summary
Write-Host "========================================"
Write-Host "Setup Complete!"
Write-Host "========================================"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit .env file and add your API keys"
Write-Host "   - Required: OPENAI_API_KEY"
Write-Host "   - Optional: TAVILY_API_KEY, GOOGLE_API_KEY"
Write-Host ""
Write-Host "2. Run the application:"
Write-Host "   .\run.ps1"
Write-Host ""
