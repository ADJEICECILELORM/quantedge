@echo off
REM Quick Retraining Script for Windows
REM Double-click this file to retrain models quickly

echo ========================================
echo QuantEdge V5 - Quick Model Retraining
echo ========================================
echo.

cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo Starting retraining...
echo.

REM Run retraining with default settings
python retrain_models.py --symbol EURUSD --bars 10000

echo.
echo ========================================
echo Retraining Complete!
echo ========================================
echo.
pause
