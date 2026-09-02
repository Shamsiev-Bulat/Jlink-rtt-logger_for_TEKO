# 📟 Jlink-rtt-logger_for_TEKO

**Automated J-Link RTT Log Capture with Timestamps and Text Filtering**

A lightweight, cross-platform Python utility designed to seamlessly capture, timestamp, and save logs from J-Link RTT (Real-Time Transfer) interfaces. It automatically generates log files with date/time stamps and filters out annoying control characters, making your embedded debugging experience much cleaner.

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ⚠️ Ветки репозитория / Repository Branches

**Важно! Этот проект имеет две ветки для разных операционных систем:**

- **`Windows`** — для пользователей Windows (скрипты `.bat`)
- **`Linux`** — для пользователей Linux (скрипты `.sh`)

**Выберите ветку под вашу операционную систему перед началом работы!**

```bash
# Переключение на ветку Windows
git checkout Windows

# Переключение на ветку Linux
git checkout Linux
```

## ✨ Features

- 🕒 **Automatic Timestamps:** Injects precise system timestamps (down to milliseconds) into every log line.
- 📂 **Smart File Naming:** Automatically creates log files named with the exact date and time of launch (e.g., `RTT_log_2026-08-31_14-30-00.txt`).
- 🧹 **Text Filtering:** Automatically strips out invisible control characters, null bytes, and ANSI escape sequences that often corrupt RTT logs.
- 🔄 **Auto-Reconnect:** Keeps listening and automatically reconnects if the J-Link connection drops.
-  **Cross-Platform:** Works flawlessly on both Windows and Linux.
- 🎨 **Modern GUI:** Beautiful graphical interface with color-coded log levels, search, filters, and statistics.
- 🚀 **One-Click Launch:** Includes ready-to-use launcher scripts that check dependencies and start the application automatically.

## 🛠️ Prerequisites

- Python 3.8 or higher
- SEGGER J-Link Software and Documentation Pack (specifically `JLinkGDBServerCL`)
- A target microcontroller with RTT enabled in your firmware

## 🚀 Installation & Quick Start

### Шаг 1: Клонируйте репозиторий

```bash
git clone https://github.com/Shamsiev-Bulat/Jlink-rtt-logger_for_TEKO.git
cd Jlink-rtt-logger_for_TEKO
```

### Шаг 2: Выберите ветку под вашу систему

```bash
# Для Windows
git checkout Windows

# Для Linux
git checkout Linux
```

### Шаг 3: Запустите лаунчер

**Для Windows:**
```cmd
launcher.bat
```

**Для Linux:**
```bash
chmod +x launcher.sh
./launcher.sh
```

Лаунчер автоматически:
- ✅ Проверит наличие Python 3.8+
- ✅ Проверит наличие pip
- ✅ Установит все необходимые зависимости (`customtkinter`, `colorama`)
- ✅ Запустит графический интерфейс программы

### Альтернативная ручная установка

Если лаунчер не сработал, установите зависимости вручную:

```bash
pip install -r requirements.txt
```

Или по отдельности:
```bash
pip install customtkinter
pip install colorama
```

Затем запустите программу:
```bash
python rtt_auto_logger_gui.py
```

## 📦 Dependencies

| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| `customtkinter` | ≥ 5.2.0 | Modern graphical user interface (GUI) | ✅ Yes |
| `colorama` | ≥ 0.4.6 | ANSI color support for Windows (optional) | ⚠️ Optional |

> **Note:** All dependencies are lightweight Python packages. No complex system requirements.

## 🖥️ GUI Features

### Основные возможности интерфейса:

- **Цветовое выделение логов** — разные цвета для ERROR, WARN, INFO, DEBUG
- **Поиск по логам** (Ctrl+F) — быстрый поиск с подсветкой совпадений
- **Кнопка паузы** (Ctrl+P) — приостановка отображения без остановки сбора данных
- **Фильтрация** — по тексту сообщения и серийному номеру устройства
- **Статистика в реальном времени** — счётчики ошибок, предупреждений, информационных сообщений
- **Регулировка размера шрифта** — от 8 до 20 пунктов
- **Переключение тем** — светлая и тёмная темы
- **Экспорт логов** — в TXT и CSV форматы
- **Автосохранение настроек** — все параметры запоминаются между сессиями
- **Горячие клавиши:**
  - `Ctrl+F` — поиск
  - `Ctrl+L` — очистка логов
  - `Ctrl+P` — пауза
  - `Ctrl+S` — экспорт

### Панель управления:

- **Хост и порт** — настройка подключения к J-Link серверу
- **Серийный номер** — для идентификации устройства в логах
- **Папка сохранения** — выбор директории для логов
- **Ротация по дням** — автоматическое создание нового файла каждый день
- **Автосохранение** — запись логов в файл в реальном времени

## 📊 Example Output

**Console & File Output:**
```
[2026-08-31 14:30:05.123] System initialized successfully
[2026-08-31 14:30:05.456] Sensor value: 42.5
[2026-08-31 14:30:06.789] State changed: IDLE -> RUNNING
```

**Generated File Name:**
```
RTT_log_2026-08-31_14-30-00.txt
```

##  Project Structure

```
Jlink-rtt-logger_for_TEKO/
├── rtt_auto_logger_gui.py      # Main GUI application
── rtt_auto_logger.py          # Console version (optional)
├── launcher.bat                # Windows launcher (auto-check & run)
├── launcher.sh                 # Linux launcher (auto-check & run)
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── LICENSE                     # MIT License
```

## ️ Advanced Usage

### Command Line Arguments (Console Version)

```bash
python rtt_auto_logger.py [OPTIONS]

Options:
  -d, --directory DIR     Save logs to specified directory
  -H, --host HOST         J-Link server host (default: localhost)
  -p, --port PORT         RTT Telnet port (default: 19021)
  --reconnect             Auto-reconnect on connection drop
  --no-rotation           Disable daily log rotation
  --buffer-size SIZE      Max buffer size in bytes (default: 65536)
  --no-color              Disable color output
```

### Examples

```bash
# Save logs to specific folder with auto-reconnect
python rtt_auto_logger.py -d ./my_logs --reconnect

# Connect to remote J-Link server
python rtt_auto_logger.py -H 192.168.1.100 -p 19022

# Disable daily rotation
python rtt_auto_logger.py --no-rotation
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you encounter any issues or have questions, please open an issue on GitHub.

---

**Happy debugging! 🔍**

*Developed with ❤️ for embedded systems developers*
