@echo off
setlocal enabledelayedexpansion
title IndicConformer ASR - Windows Installer

echo.
echo =====================================================
echo   IndicConformer ASR Web App - Windows Installer
echo   Model: ai4bharat/indic-conformer-600m-multilingual
echo =====================================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Download Python 3.10+ from: https://www.python.org/downloads/
    echo         Make sure to tick "Add Python to PATH" during install.
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% found

:: ── Check pip ─────────────────────────────────────────────────────────────
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip not found. Run: python -m ensurepip --upgrade
    pause & exit /b 1
)
echo [OK] pip found

:: ── Virtual environment ───────────────────────────────────────────────────
echo.
echo [1/5] Setting up virtual environment...
if exist venv (
    echo      venv\ already exists, skipping creation.
) else (
    python -m venv venv
    if errorlevel 1 ( echo [ERROR] venv creation failed. & pause & exit /b 1 )
    echo      Created venv\
)
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

:: ── Upgrade pip ───────────────────────────────────────────────────────────
echo.
echo [2/5] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded

:: ── PyTorch ───────────────────────────────────────────────────────────────
echo.
echo [3/5] Installing PyTorch + torchaudio...
echo.
echo   Choose your hardware:
echo     1. CPU only  (works everywhere, slower)
echo     2. CUDA 11.8 (NVIDIA GPU, older driver)
echo     3. CUDA 12.1 (NVIDIA GPU, newer driver)  -- recommended for RTX 30/40xx
echo.
set /p CHOICE="Enter 1, 2 or 3 (default=1): "
if "%CHOICE%"=="2" (
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118 --quiet
) else if "%CHOICE%"=="3" (
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet
) else (
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu --quiet
)
if errorlevel 1 ( echo [ERROR] PyTorch install failed. & pause & exit /b 1 )
echo [OK] PyTorch installed

:: ── Transformers + Flask ──────────────────────────────────────────────────
echo.
echo [4/5] Installing transformers and Flask...
pip install "transformers>=4.40.0" "flask>=3.0.0" --quiet
if errorlevel 1 ( echo [ERROR] Install failed. & pause & exit /b 1 )
echo [OK] transformers and Flask installed

:: ── Folders ───────────────────────────────────────────────────────────────
echo.
echo [5/5] Creating required folders...
if not exist uploads mkdir uploads
echo [OK] uploads\ ready

echo.
echo =====================================================
echo   INSTALLATION COMPLETE
echo =====================================================
echo.
echo   HOW TO RUN
echo   ----------
echo   1. Activate the virtual environment:
echo         venv\Scripts\activate
echo.
echo   2a. Run with auto-download (needs internet first time):
echo         python app.py
echo.
echo   2b. Run with a locally downloaded .nemo or HF snapshot:
echo         set INDIC_CONFORMER_MODEL=C:\path\to\model_folder
echo         python app.py
echo.
echo   3. Open your browser at:
echo         http://localhost:5000
echo.
echo   NOTES
echo   -----
echo   - First run downloads ~2 GB from HuggingFace (cached after that).
echo   - GPU (CUDA) is used automatically if available.
echo   - Model supports 22 Indian languages + English.
echo   - CTC decoder is fast; RNNT is more accurate.
echo =====================================================
echo.
pause
