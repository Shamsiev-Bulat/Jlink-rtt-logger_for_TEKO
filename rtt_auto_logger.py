#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTT Auto Logger GUI v3.1 - Продвинутый графический интерфейс
С поиском, фильтрацией, паузой и статистикой
"""

import customtkinter as ctk
from tkinter import scrolledtext, messagebox, filedialog
import socket
import threading
import time
import re
import json
from datetime import datetime
from pathlib import Path
import sys
import os

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Файл настроек
SETTINGS_FILE = "rtt_logger_settings.json"


class SearchWindow(ctk.CTkToplevel):
    """Окно поиска по логам"""
    
    def __init__(self, parent, log_text):
        super().__init__(parent)
        self.title("Поиск по логам")
        self.geometry("400x200")
        self.resizable(False, False)
        self.log_text = log_text
        self.search_results = []
        self.current_result_index = -1
        
        # Поле поиска
        ctk.CTkLabel(self, text="Найти:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.search_entry = ctk.CTkEntry(self, width=250)
        self.search_entry.grid(row=0, column=1, padx=10, pady=10)
        self.search_entry.bind("<Return>", lambda e: self.find_next())
        
        # Кнопки
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.find_btn = ctk.CTkButton(btn_frame, text="Найти далее", 
                                       command=self.find_next, width=100)
        self.find_btn.pack(side="left", padx=5)
        
        self.prev_btn = ctk.CTkButton(btn_frame, text="Назад", 
                                       command=self.find_previous, width=100)
        self.prev_btn.pack(side="left", padx=5)
        
        self.close_btn = ctk.CTkButton(btn_frame, text="Закрыть", 
                                        command=self.destroy, width=100,
                                        fg_color="#E74C3C")
        self.close_btn.pack(side="left", padx=5)
        
        # Статус
        self.status_label = ctk.CTkLabel(self, text="", text_color="gray")
        self.status_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        # Опции
        self.case_sensitive_var = ctk.BooleanVar(value=False)
        self.case_check = ctk.CTkCheckBox(self, text="Учитывать регистр", 
                                           variable=self.case_sensitive_var)
        self.case_check.grid(row=3, column=0, columnspan=2, pady=5)
        
        # Горячая клавиша Escape для закрытия
        self.bind("<Escape>", lambda e: self.destroy())
    
    def find_next(self):
        """Найти следующее совпадение"""
        search_text = self.search_entry.get()
        if not search_text:
            return
        
        self.log_text.configure(state='normal')
        content = self.log_text.get('1.0', 'end')
        
        # Настройка поиска
        flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
        
        # Поиск всех совпадений
        self.search_results = [m.start() for m in re.finditer(re.escape(search_text), content, flags)]
        
        if not self.search_results:
            self.status_label.configure(text="Ничего не найдено", text_color="#E74C3C")
            return
        
        # Найти следующее после текущей позиции
        current_pos = self.log_text.index('insert')
        line, col = current_pos.split('.')
        current_index = int(line) * 10000 + int(col)
        
        # Найти первое совпадение после текущей позиции
        for i, pos in enumerate(self.search_results):
            if pos > current_index:
                self.current_result_index = i
                break
        else:
            self.current_result_index = 0
        
        # Перейти к найденному
        pos = self.search_results[self.current_result_index]
        line_num = content[:pos].count('\n') + 1
        col_num = pos - content[:pos].rfind('\n')
        
        self.log_text.mark_set('insert', f"{line_num}.{col_num}")
        self.log_text.see(f"{line_num}.0")
        
        # Выделение найденного текста
        self.log_text.tag_remove('search_highlight', '1.0', 'end')
        self.log_text.tag_add('search_highlight', 
                              f"{line_num}.{col_num}", 
                              f"{line_num}.{col_num + len(search_text)}")
        
        self.status_label.configure(
            text=f"Найдено: {self.current_result_index + 1} из {len(self.search_results)}",
            text_color="#2ECC71"
        )
        
        self.log_text.configure(state='disabled')
    
    def find_previous(self):
        """Найти предыдущее совпадение"""
        if not self.search_results:
            return
        
        self.current_result_index -= 1
        if self.current_result_index < 0:
            self.current_result_index = len(self.search_results) - 1
        
        # Повторить поиск (упрощённо)
        self.find_next()


class RTTLoggerThread(threading.Thread):
    """Поток для подключения к RTT"""
    
    def __init__(self, host, port, callback, stop_event, pause_event):
        super().__init__()
        self.host = host
        self.port = port
        self.callback = callback
        self.stop_event = stop_event
        self.pause_event = pause_event
        self.socket = None
        self.running = False
        self.stats = {
            'bytes_received': 0,
            'lines_processed': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'debug': 0
        }
    
    def run(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(2.0)
            self.socket.connect((self.host, self.port))
            self.socket.setblocking(0)
            self.running = True
            
            buffer = SmartBuffer()
            
            while not self.stop_event.is_set():
                # Проверяем паузу
                if self.pause_event.is_set():
                    time.sleep(0.1)
                    continue
                
                try:
                    data = self.socket.recv(4096)
                    if data:
                        self.stats['bytes_received'] += len(data)
                        buffer.append(data)
                        lines = buffer.get_complete_lines()
                        
                        for line in lines:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            timestamped_line = f"[{timestamp}] {line}"
                            
                            # Определение уровня лога
                            level = 'default'
                            if any(word in line.upper() for word in ['ERROR', 'FATAL', 'CRITICAL', 'PANIC']):
                                level = 'error'
                                self.stats['errors'] += 1
                            elif 'WARN' in line.upper():
                                level = 'warn'
                                self.stats['warnings'] += 1
                            elif any(word in line.upper() for word in ['INFO', 'OK', 'SUCCESS', 'GOOD', 'READY']):
                                level = 'info'
                                self.stats['info'] += 1
                            elif 'DEBUG' in line.upper():
                                level = 'debug'
                                self.stats['debug'] += 1
                            
                            self.callback(timestamped_line, level)
                            self.stats['lines_processed'] += 1
                    
                    time.sleep(0.01)
                except socket.timeout:
                    continue
                except BlockingIOError:
                    time.sleep(0.01)
                except Exception as e:
                    if self.running:
                        self.callback(f"[ERROR] {str(e)}", level='error')
                    break
                    
        except Exception as e:
            self.callback(f"[ERROR] Не удалось подключиться: {str(e)}", level='error')
        finally:
            self.running = False
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
    
    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


class SmartBuffer:
    """Умный буфер для обработки RTT данных"""
    
    def __init__(self):
        self.buffer = bytearray()
        self.line_patterns = [b'\r\n', b'\n', b'\r']
    
    def append(self, data):
        self.buffer.extend(data)
    
    def get_complete_lines(self):
        lines = []
        while len(self.buffer) > 0:
            found_pos = None
            found_pattern = None
            
            for pattern in self.line_patterns:
                pos = self.buffer.find(pattern)
                if pos != -1:
                    if found_pos is None or pos < found_pos:
                        found_pos = pos
                        found_pattern = pattern
            
            if found_pos is not None:
                line_bytes = self.buffer[:found_pos]
                self.buffer = self.buffer[found_pos + len(found_pattern):]
                
                try:
                    line = line_bytes.decode('utf-8', errors='replace')
                    line = self._clean_line(line)
                    if line:
                        lines.append(line)
                except:
                    pass
            else:
                break
        
        return lines
    
    def _clean_line(self, line):
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', line)
        cleaned = cleaned.strip()
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        return cleaned
    
    def clear(self):
        self.buffer.clear()
    
    def __len__(self):
        return len(self.buffer)


class RTTLoggerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Настройка окна
        self.title("J-Link RTT Auto Logger v3.1")
        self.geometry("1400x800")
        
        # Переменные
        self.is_connected = False
        self.is_paused = False
        self.logger_thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.log_file = None
        self.current_date = None
        self.font_size = 10
        self.current_theme = "dark"
        
        # Загрузка настроек
        self.settings = self._load_settings()
        
        # Цвета для уровней логов
        self.level_colors = {
            'error': '#FF6B6B',
            'warn': '#FFD93D',
            'info': '#6BCF7F',
            'debug': '#A0A0A0',
            'default': '#FFFFFF'
        }
        
        # Создание интерфейса
        self._create_widgets()
        self._create_menu()
        self._bind_shortcuts()
        
        # Загрузка сохранённых настроек в поля
        self._load_settings_to_fields()
        
        # Обработчик закрытия
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _load_settings(self):
        """Загрузка настроек из файла"""
        if Path(SETTINGS_FILE).exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'host': 'localhost',
            'port': '19021',
            'folder': str(Path.cwd()),
            'serial_number': '',
            'rotation': True,
            'autosave': True,
            'font_size': 10,
            'theme': 'dark'
        }
    
    def _save_settings(self):
        """Сохранение настроек в файл"""
        self.settings.update({
            'host': self.host_entry.get(),
            'port': self.port_entry.get(),
            'folder': self.folder_entry.get(),
            'serial_number': self.serial_entry.get(),
            'rotation': self.rotation_var.get(),
            'autosave': self.autosave_var.get(),
            'font_size': self.font_size,
            'theme': self.current_theme
        })
        
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
    
    def _load_settings_to_fields(self):
        """Загрузка настроек в поля интерфейса"""
        self.host_entry.delete(0, 'end')
        self.host_entry.insert(0, self.settings.get('host', 'localhost'))
        
        self.port_entry.delete(0, 'end')
        self.port_entry.insert(0, self.settings.get('port', '19021'))
        
        self.folder_entry.delete(0, 'end')
        self.folder_entry.insert(0, self.settings.get('folder', str(Path.cwd())))
        
        self.serial_entry.delete(0, 'end')
        self.serial_entry.insert(0, self.settings.get('serial_number', ''))
        
        self.rotation_var.set(self.settings.get('rotation', True))
        self.autosave_var.set(self.settings.get('autosave', True))
        
        self.font_size = self.settings.get('font_size', 10)
        self._update_font_size()
    
    def _create_widgets(self):
        """Создание виджетов интерфейса"""
        
        # === Панель управления (сверху) ===
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(fill="x", padx=10, pady=10)
        
        # Хост и порт
        ctk.CTkLabel(self.control_frame, text="Хост:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.host_entry = ctk.CTkEntry(self.control_frame, width=150)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(self.control_frame, text="Порт:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.port_entry = ctk.CTkEntry(self.control_frame, width=80)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        
        # Серийный номер
        ctk.CTkLabel(self.control_frame, text="Серийник:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.serial_entry = ctk.CTkEntry(self.control_frame, width=120)
        self.serial_entry.grid(row=0, column=5, padx=5, pady=5)
        self.serial_entry.insert(0, "")
        
        # Папка для логов
        ctk.CTkLabel(self.control_frame, text="Папка:").grid(row=0, column=6, padx=5, pady=5, sticky="e")
        self.folder_entry = ctk.CTkEntry(self.control_frame, width=200)
        self.folder_entry.grid(row=0, column=7, padx=5, pady=5)
        
        self.browse_btn = ctk.CTkButton(self.control_frame, text="...", width=30, command=self._browse_folder)
        self.browse_btn.grid(row=0, column=8, padx=5, pady=5)
        
        # Опции
        self.rotation_var = ctk.BooleanVar(value=True)
        self.rotation_check = ctk.CTkCheckBox(self.control_frame, text="Ротация", 
                                               variable=self.rotation_var)
        self.rotation_check.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        self.autosave_var = ctk.BooleanVar(value=True)
        self.autosave_check = ctk.CTkCheckBox(self.control_frame, text="Автосохранение", 
                                               variable=self.autosave_var)
        self.autosave_check.grid(row=1, column=2, columnspan=2, padx=5, pady=5, sticky="w")
        
        # Кнопки управления
        self.connect_btn = ctk.CTkButton(self.control_frame, text="Подключиться", 
                                          command=self._toggle_connection, 
                                          fg_color="#2ECC71", width=120)
        self.connect_btn.grid(row=1, column=4, columnspan=2, padx=10, pady=5)
        
        self.pause_btn = ctk.CTkButton(self.control_frame, text="Пауза", 
                                        command=self._toggle_pause, 
                                        fg_color="#F39C12", width=100,
                                        state="disabled")
        self.pause_btn.grid(row=1, column=6, padx=5, pady=5)
        
        self.clear_btn = ctk.CTkButton(self.control_frame, text="Очистить", 
                                        command=self._clear_logs, 
                                        fg_color="#E74C3C", width=100)
        self.clear_btn.grid(row=1, column=7, padx=5, pady=5)
        
        # Размер шрифта
        ctk.CTkLabel(self.control_frame, text="Шрифт:").grid(row=1, column=8, padx=5, pady=5, sticky="e")
        self.font_size_var = ctk.StringVar(value=str(self.font_size))
        self.font_size_menu = ctk.CTkOptionMenu(self.control_frame, 
                                                 values=["8", "10", "12", "14", "16", "18", "20"],
                                                 variable=self.font_size_var,
                                                 command=self._on_font_size_change,
                                                 width=60)
        self.font_size_menu.grid(row=1, column=9, padx=5, pady=5)
        
        # === Панель статистики ===
        self.stats_frame = ctk.CTkFrame(self)
        self.stats_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Счётчики
        self.error_count_label = ctk.CTkLabel(self.stats_frame, text="❌ Ошибки: 0", 
                                               text_color="#FF6B6B")
        self.error_count_label.pack(side="left", padx=10, pady=5)
        
        self.warn_count_label = ctk.CTkLabel(self.stats_frame, text="⚠️ Предупреждения: 0", 
                                              text_color="#FFD93D")
        self.warn_count_label.pack(side="left", padx=10, pady=5)
        
        self.info_count_label = ctk.CTkLabel(self.stats_frame, text="ℹ️ Инфо: 0", 
                                              text_color="#6BCF7F")
        self.info_count_label.pack(side="left", padx=10, pady=5)
        
        self.debug_count_label = ctk.CTkLabel(self.stats_frame, text="🔍 Отладка: 0", 
                                               text_color="#A0A0A0")
        self.debug_count_label.pack(side="left", padx=10, pady=5)
        
        # Статус и общая статистика
        self.status_label = ctk.CTkLabel(self.stats_frame, text="Статус: Отключено", 
                                          text_color="#95A5A6")
        self.status_label.pack(side="right", padx=10, pady=5)
        
        self.stats_label = ctk.CTkLabel(self.stats_frame, text="Байт: 0 | Строк: 0", 
                                         text_color="#95A5A6")
        self.stats_label.pack(side="right", padx=10, pady=5)
        
        # === Панель фильтрации ===
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(self.filter_frame, text="Фильтр:").pack(side="left", padx=5)
        self.filter_entry = ctk.CTkEntry(self.filter_frame, width=200)
        self.filter_entry.pack(side="left", padx=5)
        self.filter_entry.insert(0, "")
        self.filter_entry.bind("<Return>", lambda e: self._apply_filter())
        
        self.filter_btn = ctk.CTkButton(self.filter_frame, text="Применить", 
                                         command=self._apply_filter, width=100)
        self.filter_btn.pack(side="left", padx=5)
        
        self.clear_filter_btn = ctk.CTkButton(self.filter_frame, text="Сбросить", 
                                               command=self._clear_filter, width=100,
                                               fg_color="#95A5A6")
        self.clear_filter_btn.pack(side="left", padx=5)
        
        # Поиск
        self.search_btn = ctk.CTkButton(self.filter_frame, text="🔍 Поиск (Ctrl+F)", 
                                         command=self._open_search, width=150)
        self.search_btn.pack(side="right", padx=5)
        
        # Экспорт
        self.export_btn = ctk.CTkButton(self.filter_frame, text="Экспорт", 
                                         command=self._export_logs, width=100)
        self.export_btn.pack(side="right", padx=5)
        
        # === Область логов ===
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Текстовое поле с логами
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap="word", 
                                                   bg="#1E1E1E", fg="#FFFFFF",
                                                   font=("Consolas", self.font_size),
                                                   relief="flat")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Настройка тегов для цветов
        self.log_text.tag_config('error', foreground=self.level_colors['error'])
        self.log_text.tag_config('warn', foreground=self.level_colors['warn'])
        self.log_text.tag_config('info', foreground=self.level_colors['info'])
        self.log_text.tag_config('debug', foreground=self.level_colors['debug'])
        self.log_text.tag_config('timestamp', foreground="#4ECDC4")
        self.log_text.tag_config('search_highlight', background="#FFD700", foreground="#000000")
    
    def _create_menu(self):
        """Создание меню"""
        self.menubar = ctk.CTkFrame(self)
        self.menubar.pack(fill="x")
        
        # Файл
        file_menu = ctk.CTkButton(self.menubar, text="Файл", width=60, 
                                   command=self._show_file_menu)
        file_menu.pack(side="left", padx=5, pady=5)
        
        # Настройки
        settings_menu = ctk.CTkButton(self.menubar, text="Настройки", width=80,
                                       command=self._show_settings)
        settings_menu.pack(side="left", padx=5, pady=5)
        
        # Тема
        theme_menu = ctk.CTkButton(self.menubar, text="Тема", width=60,
                                    command=self._toggle_theme)
        theme_menu.pack(side="left", padx=5, pady=5)
        
        # О программе
        about_menu = ctk.CTkButton(self.menubar, text="О программе", width=100,
                                    command=self._show_about)
        about_menu.pack(side="left", padx=5, pady=5)
    
    def _bind_shortcuts(self):
        """Привязка горячих клавиш"""
        self.bind("<Control-f>", lambda e: self._open_search())
        self.bind("<Control-l>", lambda e: self._clear_logs())
        self.bind("<Control-p>", lambda e: self._toggle_pause())
        self.bind("<Control-s>", lambda e: self._export_logs())
    
    def _browse_folder(self):
        """Выбор папки для сохранения"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, 'end')
            self.folder_entry.insert(0, folder)
    
    def _toggle_connection(self):
        """Подключение/отключение"""
        if not self.is_connected:
            self._connect()
        else:
            self._disconnect()
    
    def _connect(self):
        """Подключение к RTT"""
        host = self.host_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный номер порта!")
            return
        
        self.stop_event.clear()
        self.pause_event.clear()
        self.logger_thread = RTTLoggerThread(host, port, self._log_callback, 
                                              self.stop_event, self.pause_event)
        self.logger_thread.start()
        
        self.is_connected = True
        self.is_paused = False
        self.connect_btn.configure(text="Отключиться", fg_color="#E74C3C")
        self.pause_btn.configure(state="normal", text="Пауза")
        self.status_label.configure(text="Статус: Подключено", text_color="#2ECC71")
        
        # Сброс счётчиков
        self._reset_counters()
        
        # Создание файла лога
        if self.autosave_var.get():
            self._create_log_file()
        
        # Сохранение настроек
        self._save_settings()
    
    def _disconnect(self):
        """Отключение от RTT"""
        self.stop_event.set()
        if self.logger_thread:
            self.logger_thread.join(timeout=2.0)
        
        self.is_connected = False
        self.is_paused = False
        self.connect_btn.configure(text="Подключиться", fg_color="#2ECC71")
        self.pause_btn.configure(state="disabled", text="Пауза")
        self.status_label.configure(text="Статус: Отключено", text_color="#95A5A6")
        
        # Закрытие файла лога
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
            self.log_file = None
        
        # Сохранение настроек
        self._save_settings()
    
    def _toggle_pause(self):
        """Переключение паузы"""
        if not self.is_connected:
            return
        
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.pause_event.set()
            self.pause_btn.configure(text="Продолжить", fg_color="#2ECC71")
            self.status_label.configure(text="Статус: Пауза", text_color="#F39C12")
        else:
            self.pause_event.clear()
            self.pause_btn.configure(text="Пауза", fg_color="#F39C12")
            self.status_label.configure(text="Статус: Подключено", text_color="#2ECC71")
    
    def _create_log_file(self):
        """Создание файла для сохранения логов"""
        try:
            output_dir = Path(self.folder_entry.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            
            serial = self.serial_entry.get().strip()
            serial_prefix = f"_{serial}" if serial else ""
            
            if self.rotation_var.get():
                date_str = datetime.now().strftime("%Y-%m-%d")
                filename = f"RTT_log{serial_prefix}_{date_str}.txt"
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"RTT_log{serial_prefix}_{timestamp}.txt"
            
            self.log_file = open(output_dir / filename, 'a', encoding='utf-8')
            self.current_date = datetime.now().strftime("%Y-%m-%d")
            
        except Exception as e:
            self._log_callback(f"[ERROR] Не удалось создать файл: {str(e)}", level='error')
    
    def _check_rotation(self):
        """Проверка необходимости ротации"""
        if not self.rotation_var.get() or not self.log_file:
            return
        
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.current_date:
            try:
                self.log_file.close()
            except:
                pass
            self._create_log_file()
    
    def _log_callback(self, line, level='default'):
        """Обработка полученной строки лога"""
        self.after(0, lambda: self._update_gui(line, level))
    
    def _update_gui(self, line, level):
        """Обновление GUI"""
        # Применение фильтра
        filter_text = self.filter_entry.get().strip()
        if filter_text:
            # Проверка по серийному номеру
            serial = self.serial_entry.get().strip()
            if serial and serial.lower() not in line.lower():
                # Если серийник указан, но не найден в строке - пропускаем
                # (можно изменить логику по необходимости)
                pass
            
            # Проверка по тексту фильтра
            if filter_text.lower() not in line.lower():
                return
        
        # Добавление в текстовое поле
        self.log_text.configure(state='normal')
        
        # Вставка с временной меткой отдельно для цвета
        if '] ' in line:
            timestamp_part, message_part = line.split('] ', 1)
            timestamp_part += '] '
            self.log_text.insert('end', timestamp_part, 'timestamp')
            self.log_text.insert('end', message_part + '\n', level)
        else:
            self.log_text.insert('end', line + '\n', level)
        
        # Автоскролл (если не на паузе)
        if not self.is_paused:
            self.log_text.see('end')
        
        self.log_text.configure(state='disabled')
        
        # Сохранение в файл
        if self.autosave_var.get() and self.log_file:
            try:
                self.log_file.write(line + '\n')
                self.log_file.flush()
            except:
                pass
        
        # Обновление статистики
        if self.logger_thread:
            stats = self.logger_thread.stats
            self.stats_label.configure(
                text=f"Байт: {stats['bytes_received']:,} | Строк: {stats['lines_processed']:,}"
            )
            
            # Обновление счётчиков
            self.error_count_label.configure(text=f"❌ Ошибки: {stats['errors']}")
            self.warn_count_label.configure(text=f"️ Предупреждения: {stats['warnings']}")
            self.info_count_label.configure(text=f"ℹ️ Инфо: {stats['info']}")
            self.debug_count_label.configure(text=f" Отладка: {stats['debug']}")
        
        # Проверка ротации
        self._check_rotation()
    
    def _reset_counters(self):
        """Сброс счётчиков"""
        self.error_count_label.configure(text="❌ Ошибки: 0")
        self.warn_count_label.configure(text="⚠️ Предупреждения: 0")
        self.info_count_label.configure(text="ℹ️ Инфо: 0")
        self.debug_count_label.configure(text="🔍 Отладка: 0")
    
    def _clear_logs(self):
        """Очистка окна логов"""
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
    
    def _apply_filter(self):
        """Применение фильтра"""
        filter_text = self.filter_entry.get().strip()
        if filter_text:
            self.status_label.configure(
                text=f"Фильтр активен: '{filter_text}'", 
                text_color="#F39C12"
            )
        else:
            self.status_label.configure(
                text="Статус: Подключено" if self.is_connected else "Статус: Отключено",
                text_color="#2ECC71" if self.is_connected else "#95A5A6"
            )
    
    def _clear_filter(self):
        """Сброс фильтра"""
        self.filter_entry.delete(0, 'end')
        self.status_label.configure(
            text="Статус: Подключено" if self.is_connected else "Статус: Отключено",
            text_color="#2ECC71" if self.is_connected else "#95A5A6"
        )
    
    def _open_search(self):
        """Открыть окно поиска"""
        search_window = SearchWindow(self, self.log_text)
        search_window.grab_set()
    
    def _on_font_size_change(self, size):
        """Изменение размера шрифта"""
        self.font_size = int(size)
        self._update_font_size()
        self._save_settings()
    
    def _update_font_size(self):
        """Обновление размера шрифта"""
        self.log_text.configure(font=("Consolas", self.font_size))
    
    def _toggle_theme(self):
        """Переключение темы"""
        if self.current_theme == "dark":
            ctk.set_appearance_mode("light")
            self.current_theme = "light"
            self.log_text.configure(bg="#FFFFFF", fg="#000000")
        else:
            ctk.set_appearance_mode("dark")
            self.current_theme = "dark"
            self.log_text.configure(bg="#1E1E1E", fg="#FFFFFF")
        
        self._save_settings()
    
    def _export_logs(self):
        """Экспорт логов в файл"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    self.log_text.configure(state='normal')
                    content = self.log_text.get('1.0', 'end')
                    f.write(content)
                messagebox.showinfo("Экспорт", f"Логи экспортированы в:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать:\n{str(e)}")
    
    def _show_file_menu(self):
        """Показ меню файла"""
        file_window = ctk.CTkToplevel(self)
        file_window.title("Файл")
        file_window.geometry("300x200")
        
        ctk.CTkButton(file_window, text="Открыть лог", 
                       command=lambda: self._open_log_file(file_window)).pack(pady=10, padx=10, fill="x")
        ctk.CTkButton(file_window, text="Экспорт в CSV", 
                       command=lambda: self._export_csv(file_window)).pack(pady=10, padx=10, fill="x")
        ctk.CTkButton(file_window, text="Закрыть", 
                       command=file_window.destroy).pack(pady=10, padx=10, fill="x")
    
    def _open_log_file(self, parent):
        """Открытие файла лога"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.log_text.configure(state='normal')
                self.log_text.delete('1.0', 'end')
                self.log_text.insert('end', content)
                self.log_text.configure(state='disabled')
                
                parent.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{str(e)}")
    
    def _export_csv(self, parent):
        """Экспорт в CSV"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("Timestamp,Level,Message\n")
                    self.log_text.configure(state='normal')
                    content = self.log_text.get('1.0', 'end')
                    
                    # Простой парсинг
                    for line in content.split('\n'):
                        if '] ' in line:
                            timestamp, message = line.split('] ', 1)
                            timestamp = timestamp.strip('[]')
                            
                            # Определение уровня
                            level = 'INFO'
                            if 'ERROR' in message or 'FATAL' in message:
                                level = 'ERROR'
                            elif 'WARN' in message:
                                level = 'WARNING'
                            elif 'DEBUG' in message:
                                level = 'DEBUG'
                            
                            f.write(f'"{timestamp}","{level}","{message}"\n')
                
                messagebox.showinfo("Экспорт", f"CSV экспортирован в:\n{file_path}")
                parent.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать:\n{str(e)}")
    
    def _show_settings(self):
        """Показ настроек"""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("Настройки")
        settings_window.geometry("500x400")
        
        ctk.CTkLabel(settings_window, text="Настройки приложения", 
                      font=("Arial", 16, "bold")).pack(pady=10)
        
        # Настройки подключения
        conn_frame = ctk.CTkFrame(settings_window)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(conn_frame, text="Настройки подключения:").pack(anchor="w", padx=10, pady=5)
        
        # Автопереподключение
        self.reconnect_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(conn_frame, text="Автопереподключение", 
                         variable=self.reconnect_var).pack(anchor="w", padx=10, pady=5)
        
        # Буфер
        ctk.CTkLabel(conn_frame, text="Размер буфера (байт):").pack(anchor="w", padx=10, pady=5)
        self.buffer_size_entry = ctk.CTkEntry(conn_frame, width=100)
        self.buffer_size_entry.pack(anchor="w", padx=10, pady=5)
        self.buffer_size_entry.insert(0, "65536")
        
        # Кнопки
        btn_frame = ctk.CTkFrame(settings_window)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(btn_frame, text="Сохранить", 
                       command=lambda: self._save_settings_dialog(settings_window)).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Отмена", 
                       command=settings_window.destroy, 
                       fg_color="#95A5A6").pack(side="left", padx=5)
    
    def _save_settings_dialog(self, window):
        """Сохранение настроек из диалога"""
        self._save_settings()
        messagebox.showinfo("Настройки", "Настройки сохранены!")
        window.destroy()
    
    def _show_about(self):
        """Показ информации о программе"""
        about_window = ctk.CTkToplevel(self)
        about_window.title("О программе")
        about_window.geometry("500x350")
        
        ctk.CTkLabel(about_window, text="J-Link RTT Auto Logger", 
                      font=("Arial", 18, "bold")).pack(pady=10)
        
        ctk.CTkLabel(about_window, text="Версия 3.1", 
                      text_color="gray").pack()
        
        info_text = """
Продвинутый графический интерфейс для чтения логов J-Link RTT

Новые возможности v3.1:
• Поиск по логам (Ctrl+F)
• Кнопка паузы (Ctrl+P)
• Счётчики ошибок/предупреждений
• Фильтрация по тексту и серийному номеру
• Регулировка размера шрифта
• Переключение тем (светлая/тёмная)
• Экспорт в CSV
• Сохранение настроек
• Горячие клавиши

Разработано с помощью CustomTkinter
"""
        
        ctk.CTkLabel(about_window, text=info_text, 
                      justify="left").pack(pady=10, padx=10)
        
        ctk.CTkButton(about_window, text="Закрыть", 
                       command=about_window.destroy).pack(pady=10)
    
    def _on_closing(self):
        """Обработчик закрытия окна"""
        if self.is_connected:
            if messagebox.askyesno("Выход", "Подключение активно. Отключиться и выйти?"):
                self._disconnect()
                self._save_settings()
                self.destroy()
        else:
            self._save_settings()
            self.destroy()


def main():
    app = RTTLoggerGUI()
    app.mainloop()


if __name__ == '__main__':
    main()
