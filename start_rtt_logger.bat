@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo    RTT Logger - Автоматический запуск
echo ============================================================
echo.

cd /d "C:\Program Files\SEGGER\JLink_V796s"

echo [1/3] Запуск J-Link GDB Server...
start "" JLinkGDBServerCL.Exe -device GD32F407VG -if SWD -excdbg -noir -localhostonly -silent -noreset -nohalt

echo [2/3] Ожидание запуска сервера (3 секунды)...
timeout /t 3 /nobreak >nul

echo [3/3] Запуск RTT логгера...
echo.
echo ============================================================
echo.

cd /d "%~dp0"

python rtt_auto_logger.py --reconnect

echo.
echo ============================================================
echo Остановка J-Link сервера...
taskkill /F /FI "WINDOWTITLE eq JLinkGDBServerCL*" /T >nul 2>&1
echo Готово!
pause