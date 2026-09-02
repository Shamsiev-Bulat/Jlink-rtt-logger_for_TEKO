#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTT Auto Logger - Автоматическое чтение и сохранение логов J-Link RTT
С функцией автоматической ротации логов по дням и умной буферизацией
Работает на Windows и Linux
"""

import socket
import time
import argparse
import sys
import re
from datetime import datetime
from pathlib import Path

class SmartBuffer:
    """Умный буфер для обработки RTT данных"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.line_patterns = [
            b'\r\n',  # CRLF (наиболее распространённый)
            b'\n',    # LF (Unix)
            b'\r',    # CR (Mac/старые системы)
        ]
    
    def append(self, data):
        """Добавляет данные в буфер"""
        self.buffer.extend(data)
    
    def get_complete_lines(self):
        """
        Извлекает все полные строки из буфера
        Возвращает список строк и оставляет неполную строку в буфере
        """
        lines = []
        
        while len(self.buffer) > 0:
            # Ищем ближайший разделитель строки
            found_pos = None
            found_pattern = None
            
            for pattern in self.line_patterns:
                pos = self.buffer.find(pattern)
                if pos != -1:
                    if found_pos is None or pos < found_pos:
                        found_pos = pos
                        found_pattern = pattern
            
            if found_pos is not None:
                # Извлекаем полную строку
                line_bytes = self.buffer[:found_pos]
                # Удаляем строку и разделитель из буфера
                self.buffer = self.buffer[found_pos + len(found_pattern):]
                
                try:
                    # Декодируем с заменой невалидных символов
                    line = line_bytes.decode('utf-8', errors='replace')
                    # Очищаем от управляющих символов (кроме пробелов)
                    line = self._clean_line(line)
                    if line:  # Добавляем только непустые строки
                        lines.append(line)
                except Exception as e:
                    # Если не удалось декодировать, пропускаем
                    print(f"[-] Ошибка декодирования строки: {e}")
            else:
                # Нет полных строк, выходим
                break
        
        return lines
    
    def _clean_line(self, line):
        """Очищает строку от управляющих символов"""
        # Удаляем управляющие символы (кроме табуляции)
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', line)
        # Удаляем множественные пробелы в начале/конце
        cleaned = cleaned.strip()
        # Заменяем множественные пробелы внутри строки на один
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        return cleaned
    
    def clear(self):
        """Очищает буфер"""
        self.buffer.clear()
    
    def __len__(self):
        """Возвращает размер буфера"""
        return len(self.buffer)


class RTTAutoLogger:
    def __init__(self, host='localhost', rtt_port=19021, output_dir=None, 
                 rotate_daily=True, max_buffer_size=65536):
        self.host = host
        self.rtt_port = rtt_port
        self.output_dir = output_dir or Path.cwd()
        self.rotate_daily = rotate_daily
        self.max_buffer_size = max_buffer_size
        self.running = False
        self.socket = None
        self.file_handle = None
        self.log_file = None
        self.current_date = None  # Отслеживаем текущую дату для ротации
        self.smart_buffer = SmartBuffer()  # Умный буфер
        self.stats = {
            'bytes_received': 0,
            'lines_processed': 0,
            'incomplete_packets': 0,
            'buffer_overflows': 0
        }
        
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
        """Чтение данных из Telnet соединения с умной буферизацией"""
        line_count = 0
        last_rotation_check = time.time()
        last_stats_print = time.time()
        
        while self.running:
            try:
                # Проверяем необходимость ротации каждые 60 секунд
                current_time = time.time()
                if current_time - last_rotation_check >= 60:
                    self.check_and_rotate_log()
                    last_rotation_check = current_time
                
                # Выводим статистику каждые 30 секунд
                if current_time - last_stats_print >= 30:
                    self._print_stats()
                    last_stats_print = current_time
                
                data = self.socket.recv(4096)
                if data:
                    self.stats['bytes_received'] += len(data)
                    
                    # Добавляем данные в умный буфер
                    self.smart_buffer.append(data)
                    
                    # Проверяем переполнение буфера
                    if len(self.smart_buffer) > self.max_buffer_size:
                        self.stats['buffer_overflows'] += 1
                        print(f"\n[!] Предупреждение: переполнение буфера ({len(self.smart_buffer)} байт)")
                        # Очищаем буфер, чтобы избежать переполнения памяти
                        self.smart_buffer.clear()
                    
                    # Извлекаем полные строки
                    lines = self.smart_buffer.get_complete_lines()
                    
                    if lines:
                        for line in lines:
                            self.process_line(line)
                            line_count += 1
                            self.stats['lines_processed'] += 1
                    else:
                        # Нет полных строк - возможно, пришёл неполный пакет
                        if len(data) > 0 and len(self.smart_buffer) > 0:
                            self.stats['incomplete_packets'] += 1
                
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
        self._print_stats(final=True)
    
    def _print_stats(self, final=False):
        """Выводит статистику работы"""
        prefix = "[*] " if not final else "\n[*] ФИНАЛЬНАЯ "
        print(f"{prefix}Статистика:")
        print(f"    - Получено байт: {self.stats['bytes_received']:,}")
        print(f"    - Обработано строк: {self.stats['lines_processed']:,}")
        print(f"    - Неполных пакетов: {self.stats['incomplete_packets']:,}")
        print(f"    - Переполнений буфера: {self.stats['buffer_overflows']:,}")
        print(f"    - Размер буфера: {len(self.smart_buffer)} байт")
    
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
        self.stats = {
            'bytes_received': 0,
            'lines_processed': 0,
            'incomplete_packets': 0,
            'buffer_overflows': 0
        }
        
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
        
        print(f"[*] Умный буфер (max {self.max_buffer_size} байт): ВКЛ")
        print(f"[*] Поддержка LF/CR/CRLF: ВКЛ")
        
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
  python rtt_auto_logger.py                    # С умной буферизацией и ротацией
  python rtt_auto_logger.py --no-rotation      # Без ротации (один файл)
  python rtt_auto_logger.py --buffer-size 32768  # Изменить размер буфера
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
    parser.add_argument('--buffer-size', type=int, default=65536,
                       help='Максимальный размер буфера в байтах (по умолчанию: 65536)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("RTT Auto Logger v2.1")
    print("С умной буферизацией и ротацией логов")
    print("="*60)
    print(f"Хост: {args.host}")
    print(f"Порт RTT: {args.port}")
    print(f"Ротация логов: {'ОТКЛ' if args.no_rotation else 'ВКЛ (ежедневно)'}")
    print(f"Размер буфера: {args.buffer_size:,} байт")
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
        rotate_daily=not args.no_rotation,
        max_buffer_size=args.buffer_size
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
                rotate_daily=not args.no_rotation,
                max_buffer_size=args.buffer_size
            )
    else:
        logger.start()

if __name__ == '__main__':
    main()
