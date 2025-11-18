@echo off
REM Setup Python virtual environment for Uplifted Mascot development
REM This installs all dependencies needed for scripts and RAG service

echo Creating/updating Python virtual environment...

REM Create venv if it doesn't exist
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install script dependencies
echo Installing script dependencies...
pip install -r scripts\requirements.txt

REM Install RAG service dependencies
echo Installing RAG service dependencies...
pip install -r rag-service\requirements.txt

REM Install additional dependencies that might be needed
echo Installing additional dependencies...
pip install "importlib-metadata>=6.0.0" vertexai

echo.
echo Done! Virtual environment is ready.
echo.
echo To activate in the future, run:
echo   venv\Scripts\activate.bat
echo.
pause

