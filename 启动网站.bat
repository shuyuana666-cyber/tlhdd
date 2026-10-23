@echo off
chcp 65001 >nul
setlocal EnableExtensions

rem 仅在你手动运行本文件时启动本地网站，不会自动拉起服务。

cd /d "%~dp0" || exit /b 1
set "APP_DIR=%CD%"
set "PYTHONPATH=%APP_DIR%"
if not defined PORT set "PORT=4173"
set "PYTHONUNBUFFERED=1"
set "PYTHONUTF8=1"
set "LOG_DIR=%APP_DIR%\logs"
set "LOG_FILE=%LOG_DIR%\server.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if errorlevel 1 (
    echo [ERROR] Could not create the logs directory: "%LOG_DIR%"
    goto :failed
)

if not defined MYSQL_PASSWORD (
    echo [ERROR] MYSQL_PASSWORD is not set.
    echo Set it in the PowerShell window before running this BAT file.
    goto :failed
)

where py.exe >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_LAUNCHER=py"
) else (
    where python.exe >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python 3 was not found. Install Python or add it to PATH.
        goto :failed
    )
    set "PYTHON_LAUNCHER=python"
)

echo.
echo ========================================
echo   手动启动最新本地网站代码
echo   Project: %APP_DIR%
echo   Open:    http://127.0.0.1:%PORT%/
echo   Admin:   http://127.0.0.1:%PORT%/admin/
echo   Log:     %LOG_FILE%
echo ========================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { $port=[int]$env:PORT; $owners=@(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); if($owners.Count -gt 0) { try { $response=Invoke-WebRequest -Uri ('http://127.0.0.1:' + $port + '/admin/') -UseBasicParsing -TimeoutSec 3; if($response.StatusCode -eq 200 -and $response.Content.Contains('通利华汽车集团后台管理系统')) { Write-Output ('This website is already running at http://127.0.0.1:' + $port + '/'); exit 2 } } catch {}; Write-Error ('Port ' + $port + ' is occupied by another process; it was left untouched.'); exit 1 } } catch { Write-Error $_; exit 1 }"
if errorlevel 2 goto :already_running
if errorlevel 1 goto :failed

echo Starting the latest local server code. Press Ctrl+C to stop it.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$scriptPath=Join-Path $env:APP_DIR 'server.py'; if($env:PYTHON_LAUNCHER -eq 'py') { & py -3 $scriptPath 2>&1 | Tee-Object -FilePath $env:LOG_FILE -Append } else { & python $scriptPath 2>&1 | Tee-Object -FilePath $env:LOG_FILE -Append }; exit $LASTEXITCODE"
set "SERVER_EXIT=%ERRORLEVEL%"

echo.
if not "%SERVER_EXIT%"=="0" echo Server exited with code %SERVER_EXIT%. Check the log above or "%LOG_FILE%".
echo Server stopped. Press any key to close...
pause >nul
exit /b %SERVER_EXIT%

:already_running
echo Website is already running. No duplicate server was started.
echo Open:  http://127.0.0.1:%PORT%/
echo Admin: http://127.0.0.1:%PORT%/admin/
pause
exit /b 0

:failed
echo.
echo Startup aborted. Press any key to close...
pause >nul
exit /b 1
