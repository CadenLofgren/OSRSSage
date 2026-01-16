@echo off
REM Windows batch script to set up virtual environment

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ========================================
echo Virtual environment setup complete!
echo ========================================
echo.
echo To activate the virtual environment in the future, run:
echo   venv\Scripts\activate
echo.
echo To deactivate, simply type:
echo   deactivate
echo.

pause
