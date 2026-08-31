#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTT Auto Logger - С фильтрацией управляющих символов
Работает на Windows и Linux
"""

import socket
import time
import argparse
import sys
import re
from datetime import datetime
from pathlib import Path

class RTTAutoLogger:
    def __init__(self, host='localhost', rtt_port=19021, output_dir=None, 
                 filter_control_chars=True, show_hex=False):
        self.host = host
        self.rtt_port = rtt_port
        self.output_dir = output_dir or Path.cwd()
        self.running = False
        self.socket = None
        self.file_handle = None
        self.log_file = None
        self.filter_control_chars = filter_control_chars
        self.show_hex = show_hex
        
        # Паттерн для удаления управляющих символов (кроме \n, \r, \t)
        self.control_char_pattern = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
        
    def get_timestamp(self):
        """Возвращает текущую временную метку"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def clean_line(self, line):
        """Очистка строки от управляющих символов"""
        if not self.filter_control_chars:
            return line
        
        # Удаляем управляющие символы
        cleaned = self.control_char_pattern.sub('', line)
        
        # Заменяем множественные пробелы на один (опционально)
        # cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        return cleaned
    
    def decode_data(self, data):
        """Декодирование данных с обработкой ошибок"""
        # Пытаемся декодировать как UTF-8
        try:
            return data.decode('utf-8', errors='replace')
        except Exception:
            return data.decode('latin-1', errors='replace')
    
    def create_log_filename(self):
        """Создаёт имя файла с датой и временем запуска"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        filename = f"RTT_log_{date_str}_{time_str}.txt"
        return Path(self.output_dir) / filename
    
    def connect_rtt_telnet(self):
        """Подключение к RTT через Telnet (порт 19021)"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2.0)
            self.socket.connect((self.host, self.rtt_port))
            self.socket.setblocking(0)
            print(f"[+] Подключено к RTT через Telnet порт {self.rtt_port}")
            return True
        except Exception as e:
            print(f"[-] Ошибка подключения к RTT Telnet: {e}")
            return False
    
    def open_log_file(self):
        """Открывает файл лога с автоматическим именем"""
        self.log_file = self.create_log_filename()
        try:
            self.file_handle = open(self.log_file, 'w', encoding='utf-8')
            print(f"[+] Файл лога создан: {self.log_file}")
            print(f"[*] Логи автоматически сохраняются в реальном времени")
            if self.filter_control_chars:
                print(f"[*] Фильтрация управляющих символов: ВКЛ")
            return True
        except Exception as e:
            print(f"[-] Ошибка создания файла: {e}")
            return False
    
    def read_from_telnet(self):
        """Чтение данных из Telnet соединения"""
        buffer = b''
        line_count = 0
        
        while self.running:
            try:
                data = self.socket.recv(4096)
                if data:
                    buffer += data
                    # Обрабатываем полные строки
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        line_str = self.decode_data(line)
                        line_str = line_str.strip()
                        if line_str:
                            self.process_line(line_str)
                            line_count += 1
                time.sleep(0.01)
            except socket.timeout:
                continue
            except BlockingIOError:
                time.sleep(0.01)
            except Exception as e:
                if self.running:
                    print(f"[-] Ошибка чтения: {e}")
                break
        
        print(f"\n[*] Всего строк получено: {line_count}")
    
    def process_line(self, line):
        """Обработка строки лога с временной меткой"""
        timestamp = self.get_timestamp()
        
        # Очистка от управляющих символов
        cleaned_line = self.clean_line(line)
        
        timestamped_line = f"[{timestamp}] {cleaned_line}"
        
        # Вывод в консоль
        print(timestamped_line)
        
        # Запись в файл
        if self.file_handle:
            try:
                self.file_handle.write(timestamped_line + '\n')
                self.file_handle.flush()
            except Exception as e:
                print(f"[-] Ошибка записи в файл: {e}")
    
    def start(self):
        """Запуск логгера"""
        self.running = True
        
        # Подключение к RTT
        if not self.connect_rtt_telnet():
            print("[-] Не удалось подключиться к RTT.")
            print("[!] Убедитесь, что JLinkGDBServer запущен.")
            return False
        
        # Создание файла лога
        if not self.open_log_file():
            return False
        
        print("\n" + "="*60)
        print("[*] Чтение RTT логов началось")
        print("[*] Нажмите Ctrl+C для остановки")
        print("="*60 + "\n")
        
        try:
            self.read_from_telnet()
        except KeyboardInterrupt:
            print("\n[*] Остановка по команде пользователя")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Остановка логгера"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.file_handle:
            try:
                self.file_handle.close()
                print(f"\n[+] Файл сохранён: {self.log_file}")
            except:
                pass
        print("[*] RTT Logger остановлен")

def check_jlink_running(host='localhost', port=19021):
    """Проверка, запущен ли JLink сервер"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    parser = argparse.ArgumentParser(
        description='RTT Auto Logger - Автоматическое сохранение логов J-Link RTT',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python rtt_auto_logger.py                    # С фильтрацией управляющих символов
  python rtt_auto_logger.py --no-filter        # Без фильтрации (сырые данные)
  python rtt_auto_logger.py -d ./logs          # Сохранение в папку ./logs
  python rtt_auto_logger.py -H 192.168.1.100   # Подключение к удалённому хосту

Имя файла будет создано автоматически в формате:
  RTT_log_2026-01-15_14-23-45.txt
        """
    )
    
    parser.add_argument('-d', '--directory', 
                       help='Папка для сохранения логов (по умолчанию: текущая папка)')
    parser.add_argument('-H', '--host', default='localhost', 
                       help='Хост J-Link сервера (по умолчанию: localhost)')
    parser.add_argument('-p', '--port', type=int, default=19021,
                       help='RTT Telnet порт (по умолчанию: 19021)')
    parser.add_argument('--reconnect', action='store_true',
                       help='Автоматическое переподключение при обрыве')
    parser.add_argument('--no-filter', action='store_true',
                       help='Не фильтровать управляющие символы (показывать сырые данные)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("RTT Auto Logger v1.1")
    print("Автоматическое сохранение логов с временными метками")
    print("="*60)
    print(f"Хост: {args.host}")
    print(f"Порт RTT: {args.port}")
    print(f"Фильтрация символов: {'ВЫКЛ' if args.no_filter else 'ВКЛ'}")
    if args.directory:
        print(f"Папка сохранения: {args.directory}")
    else:
        print(f"Папка сохранения: {Path.cwd()}")
    print("="*60)
    
    # Проверка существования папки
    if args.directory:
        output_dir = Path(args.directory)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path.cwd()
    
    # Проверка подключения
    if not check_jlink_running(args.host, args.port):
        print(f"\n[-] Не удалось подключиться к порту {args.port}")
        print("[!] Убедитесь, что JLinkGDBServer запущен")
        print("\n[?] Попытка подключения через 5 секунд...")
        time.sleep(5)
        
        if not check_jlink_running(args.host, args.port):
            print("[-] Подключение не удалось. Завершение программы.")
            sys.exit(1)
    
    # Создание логгера
    logger = RTTAutoLogger(
        host=args.host,
        rtt_port=args.port,
        output_dir=output_dir,
        filter_control_chars=not args.no_filter
    )
    
    # Запуск с автопереподключением если нужно
    if args.reconnect:
        print("[*] Режим автоматического переподключения активирован\n")
        reconnect_count = 0
        while True:
            reconnect_count += 1
            print(f"\n{'='*60}")
            print(f"Попытка подключения #{reconnect_count}")
            print(f"{'='*60}\n")
            logger.start()
            print("\n[*] Переподключение через 5 секунд...")
            time.sleep(5)
            logger = RTTAutoLogger(
                host=args.host,
                rtt_port=args.port,
                output_dir=output_dir,
                filter_control_chars=not args.no_filter
            )
    else:
        logger.start()

if __name__ == '__main__':
    main()