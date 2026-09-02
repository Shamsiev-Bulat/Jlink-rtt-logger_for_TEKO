#!/bin/bash

# ============================================================
#    Установка зависимостей для RTT Auto Logger (Linux)
# ============================================================

echo "============================================================"
echo "   Установка зависимостей для RTT Auto Logger"
echo "============================================================"
echo ""

# Проверка Python
echo "[1/4] Проверка Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "[✓] Найден: $PYTHON_VERSION"
else
    echo "[-] Python3 не найден!"
    echo "[!] Установите Python 3.8+:"
    echo "    Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "    Fedora: sudo dnf install python3 python3-pip"
    echo "    Arch: sudo pacman -S python python-pip"
    exit 1
fi
echo ""

# Проверка pip
echo "[2/4] Проверка pip..."
if command -v pip3 &> /dev/null; then
    PIP_VERSION=$(pip3 --version)
    echo "[✓] Найден: $PIP_VERSION"
elif python3 -m pip --version &> /dev/null; then
    echo "[✓] pip доступен через python3 -m pip"
else
    echo "[-] pip не найден!"
    echo "[!] Попытка установки..."
    python3 -m ensurepip --upgrade 2>/dev/null || {
        echo "[-] Не удалось установить pip автоматически"
        echo "[!] Установите pip вручную:"
        echo "    Ubuntu/Debian: sudo apt install python3-pip"
        exit 1
    }
fi
echo ""

# Проверка requirements.txt
echo "[3/4] Проверка requirements.txt..."
if [ ! -f "requirements.txt" ]; then
    echo "[-] Файл requirements.txt не найден!"
    echo "[!] Убедитесь, что вы находитесь в папке проекта"
    exit 1
fi
echo "[✓] requirements.txt найден"
echo ""

# Установка зависимостей
echo "[4/4] Установка зависимостей..."
echo ""
echo "-------------------------------------------------------"
echo "  Проверка и установка пакетов..."
echo "-------------------------------------------------------"
echo ""

# Читаем requirements.txt построчно
while IFS= read -r line || [ -n "$line" ]; do
    # Пропускаем комментарии и пустые строки
    [[ "$line" =~ ^#.*$ ]] && continue
    [[ -z "$line" ]] && continue
    
    # Извлекаем имя пакета (до >=, ==, <=, !=)
    PACKAGE=$(echo "$line" | sed 's/[><=!].*//g' | xargs)
    
    if [ -n "$PACKAGE" ]; then
        echo "[*] Проверка: $PACKAGE"
        
        # Проверяем, установлен ли пакет
        if python3 -c "import $PACKAGE" 2>/dev/null; then
            echo "    [✓] Уже установлен: $PACKAGE"
        else
            echo "    [-] Не установлен. Устанавливаю..."
            pip3 install "$PACKAGE" --user
            if [ $? -eq 0 ]; then
                echo "    [✓] Установлен: $PACKAGE"
            else
                echo "    [-] Ошибка установки $PACKAGE"
                echo "    [!] Попробуйте: sudo pip3 install $PACKAGE"
            fi
        fi
    fi
done < requirements.txt

echo ""
echo "============================================================"
echo "   Установка завершена!"
echo "============================================================"
echo ""
echo "[*] Теперь можно запустить программу:"
echo "    python3 rtt_auto_logger_gui.py"
echo ""
