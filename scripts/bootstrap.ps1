# RoboWitness Windows PowerShell Bootstrap Script
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "RoboWitness - Environment Setup and Bootstrap" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Error "Python 3.11+ is required but not found in PATH."
    exit 1
}
Write-Host "Found Python: $($pythonCmd.Source)" -ForegroundColor Green

# Create and configure backend venv if not present
if (-not (Test-Path "backend\.venv")) {
    Write-Host "Creating Python virtual environment in backend\.venv..."
    python -m venv backend\.venv
}

Write-Host "Activating venv and installing backend requirements..."
& backend\.venv\Scripts\python.exe -m pip install --upgrade pip
# wheel/setuptools first: pybullet 3.2.5 has no Windows wheel and builds from source (needs MSVC 2019+)
& backend\.venv\Scripts\python.exe -m pip install wheel setuptools
& backend\.venv\Scripts\python.exe -m pip install -e backend/.[dev]

# Setup artifacts directories
if (-not (Test-Path "artifacts\runs")) {
    New-Item -ItemType Directory -Force -Path "artifacts\runs" | Out-Null
}
if (-not (Test-Path "artifacts\verifications")) {
    New-Item -ItemType Directory -Force -Path "artifacts\verifications" | Out-Null
}

# Check Node.js
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    Write-Host "Found Node: $($nodeCmd.Source)" -ForegroundColor Green
    if (Test-Path "apps\web\package.json") {
        Write-Host "Installing frontend dependencies..."
        Push-Location apps\web
        npm install
        Pop-Location
    }
} else {
    Write-Warning "Node.js not found. Frontend dev requires Node 18+."
}

Write-Host "Bootstrap complete! You can now run tests or launch services." -ForegroundColor Cyan
