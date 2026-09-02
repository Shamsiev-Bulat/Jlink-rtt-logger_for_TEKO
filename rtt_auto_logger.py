#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTT Auto Logger - Автоматическое чтение и сохранение логов J-Link RTT
С функцией автоматической ротации логов по дням
Работает на Windows и Linux
"""

import socket
import time
import argparse
import sys
from datetime import datetime
from pathlib import Path

class RTTAutoLogger:
    def __init__(self, host='localhost', rtt_port=19021, output_dir=None, 
                 rotate_daily=True):
        self.host = host
        self.rtt_port = rtt_port
        self.output_dir = output_dir or Path.cwd()
        self.rotate_daily = rotate_daily
        self.running = False
        self.socket = None
        self.file_handle = None
        self.log_file = None
        self.current_date = None  # Отслеживаем текущую дату для ротации
        
    def get_timestamp(self):
        """Возвращает текущую временную метку"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def get_today_string(self):
        """Возвращает строку с текущей датой (YYYY-MM-DD)"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def create_log_filename(self):
        """Создаёт имя файла с датой и временем запуска"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        
        if self.rotate_daily:
            # При ежедневной ротации имя файла содержит только дату
            filename = f"RTT_log_{date_str}.txt"
        else:
            # Без ротации - дата и время запуска
            filename = f"RTT_log_{date_str}_{time_str}.txt"
        
        return Path(self.output_dir) / filename
    
    def check_and_rotate_log(self):
        """Проверяет, не сменился ли день, и создаёт новый файл при необходимости"""
        if not self.rotate_daily:
            return
        
        today = self.get_today_string()
        
        # Если дата изменилась, закрываем старый файл и создаём новый
        if self.current_date != today:
            if self.file_handle:
                try:
                    old_file = self.log_file
                    self.file_handle.close()
                    print(f"\n[✓] Предыдущий лог сохранён: {old_file}")
                except Exception as e:
                    print(f"[-] Ошибка при закрытии файла: {e}")
            
            self.current_date = today
            self.open_log_file()
    
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
            self.file_handle = open(self.log_file, 'a', encoding='utf-8')
            print(f"[+] Файл лога: {self.log_file}")
            return True
        except Exception as e:
            print(f"[-] Ошибка создания файла: {e}")
            return False
    
    def read_from_telnet(self):
        """Чтение данных из Telnet соединения"""
        buffer = b''
        line_count = 0
        last_rotation_check = time.time()
        
        while self.running:
            try:
                # Проверяем необходимость ротации каждые 60 секунд
                current_time = time.time()
                if current_time - last_rotation_check >= 60:
                    self.check_and_rotate_log()
                    last_rotation_check = current_time
                
                data = self.socket.recv(4096)
                if data:
                    buffer += data
                    # Обрабатываем полные строки
                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        line_str = line.decode('utf-8', errors='replace').strip()
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
        timestamped_line = f"[{timestamp}] {line}"
        
        # Вывод в консоль
        print(timestamped_line)
        
        # Запись в файл
        if self.file_handle:
            try:
                self.file_handle.write(timestamped_line + '\n')
                self.file_handle.flush()  # Гарантируем запись на диск
            except Exception as e:
                print(f"[-] Ошибка записи в файл: {e}")
    
    def start(self):
        """Запуск логгера"""
        self.running = True
        self.current_date = self.get_today_string()
        
        # Подключение к RTT
        if not self.connect_rtt_telnet():
            print("[-] Не удалось подключиться к RTT.")
            print("[!] Убедитесь, что JLinkGDBServer запущен.")
            return False
        
        # Создание файла лога
        if not self.open_log_file():
            return False
        
        if self.rotate_daily:
            print(f"[*] Ежедневная ротация логов: ВКЛ")
        
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
  python rtt_auto_logger.py                    # С ежедневной ротацией
  python rtt_auto_logger.py --no-rotation      # Без ротации (один файл)
  python rtt_auto_logger.py -d ./logs          # Сохранение в папку ./logs
  python rtt_auto_logger.py -H 192.168.1.100   # Подключение к удалённому хосту

Имя файла будет создано автоматически в формате:
  RTT_log_2026-01-15.txt (с ежедневной ротацией)
  RTT_log_2026-01-15_14-23-45.txt (без ротации)
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
    parser.add_argument('--no-rotation', action='store_true',
                       help='Отключить ежедневную ротацию (один файл на весь сеанс)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("RTT Auto Logger v2.0")
    print("Автоматическое сохранение логов с временными метками")
    print("="*60)
    print(f"Хост: {args.host}")
    print(f"Порт RTT: {args.port}")
    print(f"Ротация логов: {'ОТКЛ' if args.no_rotation else 'ВКЛ (ежедневно)'}")
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
        rotate_daily=not args.no_rotation
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
                rotate_daily=not args.no_rotation
            )
    else:
        logger.start()

if __name__ == '__main__':
    main()
