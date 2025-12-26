@echo off
title VitalSort Launcher
cls

echo ==================================================
echo [1/2] Compiling C++ Backend (VitalSort)...
echo ==================================================

:: 1. Safety Check
if not exist "src" (
    echo [ERROR] 'src' folder is missing!
    pause
    exit /b
)

:: 2. Compile
cd src
g++ *.cpp -o ../triage.exe
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Compilation Failed! Please fix the C++ errors above.
    cd ..
    pause
    exit /b
)
cd ..

echo [SUCCESS] Backend compiled successfully.
echo.

echo ==================================================
echo [2/2] Launching Python Interface...
echo ==================================================

:: 3. Launch (Try all common Python commands)
:: 2>nul hides ugly "command not found" errors if one method fails
python gui/GUI.py 2>nul || py gui/GUI.py 2>nul || python3 gui/GUI.py 2>nul

:: 4. Crash Check
if %errorlevel% neq 0 (
    echo.
    echo [CRASH] The Python GUI closed unexpectedly or Python is not installed.
    pause
)