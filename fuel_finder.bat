@echo off
:: Title properties for the deployment window
title Fuel Tracker Mobile Engine Launcher
echo ===================================================
echo   Initializing Fuel Tracker Mobile App Launcher...
echo ===================================================
echo.

:: Verify if python module structure responds cleanly
echo [1/2] Checking local Python environment dependencies...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python was not found responding on your system path.
    echo Please ensure your Windows Store Python installation is active.
    goto error_halt
)

echo [2/2] Launching Streamlit web server engine...
echo.
echo ---------------------------------------------------
echo   The browser dashboard will open automatically.
echo   Keep this black window OPEN while using the app!
echo ---------------------------------------------------
echo.

:: Explicitly use the python module execution flag targeting your exact script name
python -m streamlit run "fuel_finder.py"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Streamlit failed to execute. 
    echo Verifying if alternative launcher pathway works...
    echo.
    py -m streamlit run "fuel_finder.py"
)

:error_halt
echo.
echo Execution interrupted. Press any key to close this launcher shell.
pause