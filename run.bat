@echo off
echo ==========================================
echo      VitalSort: Compiling C++ Backend...
echo ==========================================

:: 1. Compile the C++ code
g++ *.cpp -o app
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Compilation Failed! See errors above.
    pause
    exit /b
)

echo [SUCCESS] Compilation complete. app.exe updated.
echo.

:: 2. Launch the Python GUI
echo ==========================================
echo      Launching Python GUI...
echo ==========================================

:: Try 'python', if that fails try 'py' (common on Windows)
python GUI.py || py GUI.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Python script crashed or Python is not installed.
    pause
)