# Blog Writing Agent - Environment Check Script for Windows
# This script checks if everything is set up correctly

Write-Host "========================================"
Write-Host "Blog Writing Agent - Environment Check"
Write-Host "========================================"
Write-Host ""

$allGood = $true

# Check Python
Write-Host "Checking Python..."
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCheck) {
    $pythonVersion = python --version
    Write-Host "OK: Python installed: $pythonVersion"
} else {
    Write-Host "ERROR: Python not found"
    $allGood = $false
}

# Check Virtual Environment
Write-Host ""
Write-Host "Checking virtual environment..."
if (Test-Path "venv") {
    Write-Host "OK: Virtual environment exists"
    
    if (Test-Path "venv\Lib\site-packages") {
        $packageCount = (Get-ChildItem "venv\Lib\site-packages" -Directory -ErrorAction SilentlyContinue).Count
        Write-Host "   Packages installed: $packageCount"
    }
} else {
    Write-Host "ERROR: Virtual environment not found"
    Write-Host "   Run: .\setup.ps1"
    $allGood = $false
}

# Check .env file
Write-Host ""
Write-Host "Checking .env file..."
if (Test-Path ".env") {
    Write-Host "OK: .env file exists"
    
    $envContent = Get-Content ".env" -Raw
    
    if ($envContent -match "OPENAI_API_KEY=sk-") {
        Write-Host "   OK: OPENAI_API_KEY set"
    } else {
        Write-Host "   ERROR: OPENAI_API_KEY missing or invalid"
        $allGood = $false
    }
    
    if ($envContent -match "TAVILY_API_KEY=") {
        Write-Host "   OK: TAVILY_API_KEY set (optional)"
    } else {
        Write-Host "   WARNING: TAVILY_API_KEY not set (optional)"
    }
    
    if ($envContent -match "GOOGLE_API_KEY=") {
        Write-Host "   OK: GOOGLE_API_KEY set (optional)"
    } else {
        Write-Host "   WARNING: GOOGLE_API_KEY not set (optional)"
    }
} else {
    Write-Host "ERROR: .env file not found"
    Write-Host "   Run: .\setup.ps1"
    $allGood = $false
}

# Check required directories
Write-Host ""
Write-Host "Checking directories..."
if (Test-Path "src") {
    Write-Host "OK: src/ directory exists"
} else {
    Write-Host "ERROR: src/ directory not found"
    $allGood = $false
}

if (Test-Path "images") {
    Write-Host "OK: images/ directory exists"
} else {
    Write-Host "WARNING: images/ directory not found (will be created)"
}

if (Test-Path "outputs") {
    Write-Host "OK: outputs/ directory exists"
} else {
    Write-Host "WARNING: outputs/ directory not found (will be created)"
}

# Summary
Write-Host ""
Write-Host "========================================"
if ($allGood) {
    Write-Host "All checks passed!"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "You're ready to run the application:"
    Write-Host "  .\run.ps1"
} else {
    Write-Host "Some checks failed!"
    Write-Host "========================================"
    Write-Host ""
    Write-Host "Please run setup to fix issues:"
    Write-Host "  .\setup.ps1"
}
Write-Host ""
