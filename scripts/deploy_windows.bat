@echo off
REM Windows Deployment Script for TikTok Video Processing Tool

echo TikTok Video Processing Tool - Windows Deployment
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Found Python %PYTHON_VERSION%

REM Check if FFmpeg is installed
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg is not installed or not in PATH
    echo Please install FFmpeg from https://ffmpeg.org/download.html
    echo The application will not work without FFmpeg
    pause
)

REM Create installation directory
set INSTALL_DIR=%USERPROFILE%\TikTokVideoProcessor
echo Creating installation directory: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy application files
echo Copying application files...
xcopy /E /I /Y "src" "%INSTALL_DIR%\src"
copy /Y "main.py" "%INSTALL_DIR%\"
copy /Y "requirements.txt" "%INSTALL_DIR%\"
copy /Y "README.md" "%INSTALL_DIR%\"
copy /Y "config.json" "%INSTALL_DIR%\" 2>nul
if exist "config\default.json" copy /Y "config\default.json" "%INSTALL_DIR%\"

REM Install Python dependencies
echo Installing Python dependencies...
cd /d "%INSTALL_DIR%"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python dependencies
    pause
    exit /b 1
)

REM Create batch files for easy execution
echo Creating launcher scripts...

REM GUI launcher
echo @echo off > "%INSTALL_DIR%\TikTokProcessor-GUI.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%\TikTokProcessor-GUI.bat"
echo python main.py >> "%INSTALL_DIR%\TikTokProcessor-GUI.bat"
echo pause >> "%INSTALL_DIR%\TikTokProcessor-GUI.bat"

REM CLI launcher
echo @echo off > "%INSTALL_DIR%\TikTokProcessor-CLI.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%\TikTokProcessor-CLI.bat"
echo python main.py --cli %%* >> "%INSTALL_DIR%\TikTokProcessor-CLI.bat"

REM Configuration launcher
echo @echo off > "%INSTALL_DIR%\TikTokProcessor-Config.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%\TikTokProcessor-Config.bat"
echo python main.py --config-info >> "%INSTALL_DIR%\TikTokProcessor-Config.bat"
echo pause >> "%INSTALL_DIR%\TikTokProcessor-Config.bat"

REM Create desktop shortcuts (optional)
set /p CREATE_SHORTCUTS="Create desktop shortcuts? (y/n): "
if /i "%CREATE_SHORTCUTS%"=="y" (
    echo Creating desktop shortcuts...
    
    REM Create VBS script to create shortcuts
    echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
    echo sLinkFile = "%USERPROFILE%\Desktop\TikTok Video Processor.lnk" >> "%TEMP%\CreateShortcut.vbs"
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.TargetPath = "%INSTALL_DIR%\TikTokProcessor-GUI.bat" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.WorkingDirectory = "%INSTALL_DIR%" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.Description = "TikTok Video Processing Tool" >> "%TEMP%\CreateShortcut.vbs"
    echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"
    
    cscript //nologo "%TEMP%\CreateShortcut.vbs"
    del "%TEMP%\CreateShortcut.vbs"
)

REM Create uninstaller
echo Creating uninstaller...
echo @echo off > "%INSTALL_DIR%\Uninstall.bat"
echo echo Uninstalling TikTok Video Processing Tool... >> "%INSTALL_DIR%\Uninstall.bat"
echo cd /d "%USERPROFILE%" >> "%INSTALL_DIR%\Uninstall.bat"
echo rmdir /s /q "%INSTALL_DIR%" >> "%INSTALL_DIR%\Uninstall.bat"
echo del "%USERPROFILE%\Desktop\TikTok Video Processor.lnk" 2^>nul >> "%INSTALL_DIR%\Uninstall.bat"
echo echo Uninstallation complete. >> "%INSTALL_DIR%\Uninstall.bat"
echo pause >> "%INSTALL_DIR%\Uninstall.bat"

REM Test installation
echo Testing installation...
cd /d "%INSTALL_DIR%"
python main.py --help >nul 2>&1
if errorlevel 1 (
    echo ERROR: Installation test failed
    pause
    exit /b 1
)

echo.
echo ================================================
echo Installation completed successfully!
echo ================================================
echo.
echo Installation directory: %INSTALL_DIR%
echo.
echo To run the application:
echo   GUI Mode: Double-click TikTokProcessor-GUI.bat
echo   CLI Mode: Run TikTokProcessor-CLI.bat from command prompt
echo   Config:   Double-click TikTokProcessor-Config.bat
echo.
echo To uninstall: Run Uninstall.bat in the installation directory
echo.
pause