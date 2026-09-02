@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ============================================================
echo    Установка зависимостей для RTT Auto Logger
echo ============================================================
echo.

:: Проверка Python
echo [1/4] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [-] Python не найден!
    echo [!] Установите Python 3.8+ с https://www.python.org/downloads/
    echo [!] При установке обязательно отметьте "Add Python to PATH"
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
    echo [-] pip не найден!
    echo [!] Попытка установки pip...
    python -m ensurepip --upgrade
    if errorlevel 1 (
        echo [-] Не удалось установить pip автоматически
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%i in ('python -m pip --version') do set PIP_VERSION=%%i
echo [✓] Найден: %PIP_VERSION%
echo.

:: Проверка requirements.txt
echo [3/4] Проверка requirements.txt...
if not exist "requirements.txt" (
    echo [-] Файл requirements.txt не найден!
    echo [!] Убедитесь, что вы находитесь в папке проекта
    pause
    exit /b 1
)
echo [✓] requirements.txt найден
echo.

:: Установка зависимостей
echo [4/4] Установка зависимостей...
echo.
echo -------------------------------------------------------
echo  Установка пакетов из requirements.txt...
echo -------------------------------------------------------
echo.

:: Проверяем каждый пакет отдельно
for /f "usebackq tokens=1,* delims=>=<!" %%a in ("requirements.txt") do (
    set PACKAGE=%%a
    :: Убираем пробелы
    for /f "tokens=1 delims= " %%b in ("!PACKAGE!") do set PACKAGE=%%b
    
    if not "!PACKAGE!"=="" (
        if not "!PACKAGE:~0,1!"=="#" (
            echo [*] Проверка: !PACKAGE!
            python -m pip show !PACKAGE! >nul 2>&1
            if errorlevel 1 (
                echo     [-] Не установлен. Устанавливаю...
                python -m pip install !PACKAGE!
                if errorlevel 1 (
                    echo     [-] Ошибка установки !PACKAGE!
                ) else (
                    echo     [✓] Установлен: !PACKAGE!
                )
            ) else (
                echo     [✓] Уже установлен: !PACKAGE!
            )
        )
    )
)

echo.
echo ============================================================
echo    Установка завершена!
echo ============================================================
echo.
echo [*] Теперь можно запустить программу:
echo     python rtt_auto_logger_gui.py
echo.
pause
