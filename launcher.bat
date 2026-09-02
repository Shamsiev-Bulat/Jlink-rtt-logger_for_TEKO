@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo    RTT Auto Logger - Автоматический запуск
echo ============================================================
echo.

:: Проверка Python
echo [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [-] Python не найден!
    echo.
    echo [!] Python необходимо установить вручную:
    echo     1. Перейдите на https://www.python.org/downloads/
    echo     2. Скачайте Python 3.8 или выше
    echo     3. При установке ОБЯЗАТЕЛЬНО отметьте "Add Python to PATH"
    echo     4. Перезапустите этот скрипт
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [✓] Найден: %PYTHON_VERSION%
echo.

:: Проверка pip
echo [2/4] Проверка pip...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [-] pip не найден! Устанавливаю...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo [-] Не удалось установить pip
        pause
        exit /b 1
    )
)
echo [✓] pip доступен
echo.

:: Установка зависимостей
echo [3/4] Установка зависимостей...
if exist "requirements.txt" (
    echo [*] Установка пакетов из requirements.txt...
    python -m pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo [-] Ошибка установки зависимостей
        pause
        exit /b 1
    )
    echo [✓] Зависимости установлены
) else (
    echo [-] requirements.txt не найден!
    pause
    exit /b 1
)
echo.

:: Запуск программы
echo [4/4] Запуск RTT Auto Logger GUI...
echo ============================================================
echo.

if exist "rtt_auto_logger_gui.py" (
    echo [*] Запуск графического интерфейса...
    echo [*] Для остановки программы закройте окно или нажмите Ctrl+C
    echo.
    python rtt_auto_logger_gui.py
) else (
    echo [-] Файл rtt_auto_logger_gui.py не найден!
    echo [!] Убедитесь, что вы находитесь в папке проекта
    pause
    exit /b 1
)

echo.
echo ============================================================
echo    Программа завершена
echo ============================================================
pause
