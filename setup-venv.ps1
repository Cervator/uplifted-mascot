# Setup Python virtual environment for Uplifted Mascot development
# This installs all dependencies needed for scripts and RAG service

Write-Host "Creating/updating Python virtual environment..." -ForegroundColor Cyan

# Create venv if it doesn't exist
if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
}

# Activate venv
& .\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install script dependencies
Write-Host "Installing script dependencies..." -ForegroundColor Cyan
pip install -r scripts\requirements.txt

# Install RAG service dependencies
Write-Host "Installing RAG service dependencies..." -ForegroundColor Cyan
pip install -r rag-service\requirements.txt

# Install additional dependencies that might be needed
Write-Host "Installing additional dependencies..." -ForegroundColor Cyan
pip install "importlib-metadata>=6.0.0" vertexai

Write-Host ""
Write-Host "Done! Virtual environment is ready." -ForegroundColor Green
Write-Host ""
Write-Host "To activate in the future, run:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor White

