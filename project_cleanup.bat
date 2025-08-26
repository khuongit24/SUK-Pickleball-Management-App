@echo off
echo ==========================================
echo    PROJECT CLEANUP - SUK PICKLEBALL
echo ==========================================
echo.

set CLEANUP_LOG=cleanup_log_%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%.txt
echo Cleanup started at %date% %time% > %CLEANUP_LOG%

echo 🗂️  Analyzing project structure...
echo.

REM Count files before cleanup
for /f %%i in ('dir /s /b *.* ^| find /c /v ""') do set BEFORE_COUNT=%%i
echo Files before cleanup: %BEFORE_COUNT% >> %CLEANUP_LOG%

echo 📁 CURRENT STRUCTURE:
echo ├── Core Application Files (KEEP)
echo │   ├── main.py, models.py, utils.py
echo │   ├── requirements.txt, README.md
echo │   └── icon_suk.ico
echo │
echo ├── Data Files (KEEP)
echo │   ├── *.csv files
echo │   └── config/ folder
echo │
echo ├── Build & Distribution (REVIEW)
echo │   ├── SUK_Pickleball_Package/ (KEEP - Customer delivery)
echo │   ├── dist/ (TEMP - Can delete after delivery)
echo │   ├── build/ (TEMP - PyInstaller cache)
echo │   └── .venv/ (DEV - Keep for development)
echo │
echo ├── Backup Files (CLEAN UP NEEDED)
echo │   ├── main_backup_temp.py (DELETE)
echo │   ├── main_clean.py (DELETE) 
echo │   ├── main_fixed.py (DELETE)
echo │   ├── old/ folder (DELETE - outdated)
echo │   └── cleaned_backup/ (DELETE - redundant)
echo │
echo └── Documentation & Logs (ORGANIZE)
echo     ├── logs/ (KEEP - but clean old logs)
echo     └── backups/ (KEEP recent, delete old)
echo.

echo 🔍 CLEANUP PLAN:

echo.
echo ❌ Files to DELETE:
echo    - main_backup_temp.py
echo    - main_clean.py  
echo    - main_fixed.py
echo    - old/ folder (outdated code)
echo    - cleaned_backup/ folder (redundant)
echo    - build/ folder (PyInstaller temp)
echo    - Older backup PDFs (keep latest only)

echo.
echo ✅ Files to KEEP:
echo    - All core .py files (main.py, models.py, utils.py)
echo    - All .csv data files
echo    - config/ folder
echo    - SUK_Pickleball_Package/ (customer delivery)
echo    - Recent documentation
echo    - .venv/ (development environment)

echo.
set /p CONFIRM="Proceed with cleanup? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Cleanup cancelled.
    goto :END
)

echo.
echo 🧹 Starting cleanup...

REM Delete temporary Python files
if exist "main_backup_temp.py" (
    del "main_backup_temp.py"
    echo ✓ Deleted main_backup_temp.py >> %CLEANUP_LOG%
    echo ✓ Deleted main_backup_temp.py
)

if exist "main_clean.py" (
    del "main_clean.py"
    echo ✓ Deleted main_clean.py >> %CLEANUP_LOG%
    echo ✓ Deleted main_clean.py
)

if exist "main_fixed.py" (
    del "main_fixed.py"
    echo ✓ Deleted main_fixed.py >> %CLEANUP_LOG%
    echo ✓ Deleted main_fixed.py
)

REM Delete outdated folders
if exist "old\" (
    rmdir /s /q "old"
    echo ✓ Deleted old/ folder >> %CLEANUP_LOG%
    echo ✓ Deleted old/ folder
)

if exist "cleaned_backup\" (
    rmdir /s /q "cleaned_backup"
    echo ✓ Deleted cleaned_backup/ folder >> %CLEANUP_LOG%
    echo ✓ Deleted cleaned_backup/ folder
)

REM Delete PyInstaller build cache
if exist "build\" (
    rmdir /s /q "build"
    echo ✓ Deleted build/ folder >> %CLEANUP_LOG%
    echo ✓ Deleted build/ folder (PyInstaller cache)
)

REM Clean old backup PDFs (keep only the latest)
cd backups 2>nul
if exist "Bao_cao_du_lieu_20250825_093359.pdf" (
    del "Bao_cao_du_lieu_20250825_093359.pdf"
    echo ✓ Deleted old backup PDF >> ..\%CLEANUP_LOG%
    echo ✓ Deleted old backup PDF
)
if exist "repair_backup_20250825_102243\" (
    rmdir /s /q "repair_backup_20250825_102243"
    echo ✓ Deleted old repair backup >> ..\%CLEANUP_LOG%
    echo ✓ Deleted old repair backup
)
cd ..

REM Clean old log files (keep recent ones)
cd logs 2>nul
forfiles /m *.log /d -7 /c "cmd /c del @path" 2>nul
echo ✓ Cleaned old log files (7+ days) >> ..\%CLEANUP_LOG%
echo ✓ Cleaned old log files
cd ..

REM Count files after cleanup
for /f %%i in ('dir /s /b *.* ^| find /c /v ""') do set AFTER_COUNT=%%i
set /a REMOVED_COUNT=%BEFORE_COUNT%-%AFTER_COUNT%

echo.
echo ==========================================
echo    CLEANUP COMPLETED SUCCESSFULLY!
echo ==========================================
echo.
echo 📊 CLEANUP SUMMARY:
echo    Files before: %BEFORE_COUNT%
echo    Files after:  %AFTER_COUNT%
echo    Files removed: %REMOVED_COUNT%
echo.

echo Files after cleanup: %AFTER_COUNT% >> %CLEANUP_LOG%
echo Files removed: %REMOVED_COUNT% >> %CLEANUP_LOG%
echo Cleanup completed at %date% %time% >> %CLEANUP_LOG%

echo 📁 FINAL PROJECT STRUCTURE:
dir /b | findstr /v "%CLEANUP_LOG%"

echo.
echo ✅ Project is now clean and organized!
echo 📝 Cleanup log saved as: %CLEANUP_LOG%
echo.

:END
pause
