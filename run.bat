@echo off
echo ==========================================
echo      VitalSort: Compiling Backend...
echo ==========================================

:: 1. Compile everything in src/ and output 'app.exe' to the ROOT folder
g++ src/*.cpp -o app.exe

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Compilation Failed!
    pause
    exit /b
)

echo [SUCCESS] Backend ready.
echo.

:: 2. Launch the Python GUI from the 'gui' folder
echo ==========================================
echo      Launching Interface...
echo ==========================================

:: We pass "../app.exe" as an argument so Python knows where the backend is
cd gui
python vital_gui.py
cd ..

if %errorlevel% neq 0 (
    pause
)