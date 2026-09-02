#!/bin/bash

# ============================================================
#    RTT Auto Logger - Автоматический запуск (Linux)
# ============================================================

echo "============================================================"
echo "   RTT Auto Logger - Автоматический запуск"
echo "============================================================"
echo ""

# Проверка Python
echo "[1/4] Проверка Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "[✓] Найден: $PYTHON_VERSION"
else
    echo "[-] Python3 не найден!"
    echo ""
    echo "[!] Python необходимо установить:"
    echo "    Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "    Fedora: sudo dnf install python3 python3-pip"
    echo "    Arch: sudo pacman -S python python-pip"
    echo ""
    echo "    Или скачайте с https://www.python.org/downloads/"
    echo ""
    exit 1
fi
echo ""

# Проверка pip
echo "[2/4] Проверка pip..."
if command -v pip3 &> /dev/null; then
    echo "[✓] pip3 доступен"
elif python3 -m pip --version &> /dev/null; then
    echo "[✓] pip доступен через python3 -m pip"
else
    echo "[-] pip не найден! Устанавливаю..."
    python3 -m ensurepip --upgrade 2>/dev/null || {
        echo "[-] Не удалось установить pip"
        echo "[!] Установите pip вручную:"
        echo "    Ubuntu/Debian: sudo apt install python3-pip"
        exit 1
    }
fi
echo ""

# Установка зависимостей
echo "[3/4] Установка зависимостей..."
if [ -f "requirements.txt" ]; then
    echo "[*] Установка пакетов из requirements.txt..."
    pip3 install -r requirements.txt --user --quiet
    if [ $? -ne 0 ]; then
        echo "[-] Ошибка установки зависимостей"
        echo "[!] Попробуйте: sudo pip3 install -r requirements.txt"
        exit 1
    fi
    echo "[✓] Зависимости установлены"
else
    echo "[-] requirements.txt не найден!"
    exit 1
fi
echo ""

# Запуск программы
echo "[4/4] Запуск RTT Auto Logger GUI..."
echo "============================================================"
echo ""

if [ -f "rtt_auto_logger_gui.py" ]; then
    echo "[*] Запуск графического интерфейса..."
    echo "[*] Для остановки программы нажмите Ctrl+C"
    echo ""
    python3 rtt_auto_logger_gui.py
else
    echo "[-] Файл rtt_auto_logger_gui.py не найден!"
    echo "[!] Убедитесь, что вы находитесь в папке проекта"
    exit 1
fi

echo ""
echo "============================================================"
echo "   Программа завершена"
echo "============================================================"
