#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RTT Auto Logger GUI - Графический интерфейс для чтения логов J-Link RTT
Современный интерфейс с цветовым выделением и всеми функциями
"""

import customtkinter as ctk
from tkinter import scrolledtext, messagebox
import socket
import threading
import time
import re
from datetime import datetime
from pathlib import Path
import sys
import os

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


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


class RTTLoggerThread(threading.Thread):
    """Поток для подключения к RTT"""
    
    def __init__(self, host, port, callback, stop_event):
        super().__init__()
        self.host = host
        self.port = port
        self.callback = callback
        self.stop_event = stop_event
        self.socket = None
        self.running = False
        self.stats = {
            'bytes_received': 0,
            'lines_processed': 0
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
                try:
                    data = self.socket.recv(4096)
                    if data:
                        self.stats['bytes_received'] += len(data)
                        buffer.append(data)
                        lines = buffer.get_complete_lines()
                        
                        for line in lines:
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                            timestamped_line = f"[{timestamp}] {line}"
                            self.callback(timestamped_line)
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


class RTTLoggerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Настройка окна
        self.title("J-Link RTT Auto Logger v3.0")
        self.geometry("1200x700")
        
        # Переменные
        self.is_connected = False
        self.logger_thread = None
        self.stop_event = threading.Event()
        self.log_file = None
        self.auto_save = True
        self.current_date = None
        
        # Цвета для уровней логов
        self.level_colors = {
            'error': '#FF6B6B',      # Красный
            'warn': '#FFD93D',       # Желтый
            'info': '#6BCF7F',       # Зеленый
            'debug': '#A0A0A0',      # Серый
            'default': '#FFFFFF'     # Белый
        }
        
        # Создание интерфейса
        self._create_widgets()
        self._create_menu()
        
        # Обработчик закрытия
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_widgets(self):
        """Создание виджетов интерфейса"""
        
        # === Панель управления (сверху) ===
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.pack(fill="x", padx=10, pady=10)
        
        # Хост и порт
        ctk.CTkLabel(self.control_frame, text="Хост:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.host_entry = ctk.CTkEntry(self.control_frame, width=150)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5)
        self.host_entry.insert(0, "localhost")
        
        ctk.CTkLabel(self.control_frame, text="Порт:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.port_entry = ctk.CTkEntry(self.control_frame, width=80)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)
        self.port_entry.insert(0, "19021")
        
        # Папка для логов
        ctk.CTkLabel(self.control_frame, text="Папка:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.folder_entry = ctk.CTkEntry(self.control_frame, width=200)
        self.folder_entry.grid(row=0, column=5, padx=5, pady=5)
        self.folder_entry.insert(0, str(Path.cwd()))
        
        self.browse_btn = ctk.CTkButton(self.control_frame, text="...", width=30, command=self._browse_folder)
        self.browse_btn.grid(row=0, column=6, padx=5, pady=5)
        
        # Опции
        self.rotation_var = ctk.BooleanVar(value=True)
        self.rotation_check = ctk.CTkCheckBox(self.control_frame, text="Ротация по дням", 
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
        
        self.clear_btn = ctk.CTkButton(self.control_frame, text="Очистить", 
                                        command=self._clear_logs, 
                                        fg_color="#E74C3C", width=100)
        self.clear_btn.grid(row=1, column=6, padx=5, pady=5)
        
        # === Статус бар ===
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="Статус: Отключено", 
                                          text_color="#95A5A6")
        self.status_label.pack(side="left", padx=10, pady=5)
        
        self.stats_label = ctk.CTkLabel(self.status_frame, text="Байт: 0 | Строк: 0", 
                                         text_color="#95A5A6")
        self.stats_label.pack(side="right", padx=10, pady=5)
        
        # === Область логов ===
        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Текстовое поле с логами
        self.log_text = scrolledtext.ScrolledText(self.log_frame, wrap="word", 
                                                   bg="#1E1E1E", fg="#FFFFFF",
                                                   font=("Consolas", 10),
                                                   relief="flat")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Настройка тегов для цветов
        self.log_text.tag_config('error', foreground=self.level_colors['error'])
        self.log_text.tag_config('warn', foreground=self.level_colors['warn'])
        self.log_text.tag_config('info', foreground=self.level_colors['info'])
        self.log_text.tag_config('debug', foreground=self.level_colors['debug'])
        self.log_text.tag_config('timestamp', foreground="#4ECDC4")
        
        # === Фильтр ===
        self.filter_frame = ctk.CTkFrame(self)
        self.filter_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkLabel(self.filter_frame, text="Фильтр:").pack(side="left", padx=5)
        self.filter_entry = ctk.CTkEntry(self.filter_frame, width=200)
        self.filter_entry.pack(side="left", padx=5)
        self.filter_entry.insert(0, "")
        
        self.filter_btn = ctk.CTkButton(self.filter_frame, text="Применить", 
                                         command=self._apply_filter, width=100)
        self.filter_btn.pack(side="left", padx=5)
        
        self.export_btn = ctk.CTkButton(self.filter_frame, text="Экспорт в файл", 
                                         command=self._export_logs, width=120)
        self.export_btn.pack(side="right", padx=5)
    
    def _create_menu(self):
        """Создание меню"""
        self.menubar = ctk.CTkFrame(self)
        self.menubar.pack(fill="x")
        
        # Файл
        file_menu = ctk.CTkButton(self.menubar, text="Файл", width=60, 
                                   command=lambda: messagebox.showinfo("Файл", "Меню файла"))
        file_menu.pack(side="left", padx=5, pady=5)
        
        # Настройки
        settings_menu = ctk.CTkButton(self.menubar, text="Настройки", width=80,
                                       command=self._show_settings)
        settings_menu.pack(side="left", padx=5, pady=5)
        
        # О программе
        about_menu = ctk.CTkButton(self.menubar, text="О программе", width=100,
                                    command=self._show_about)
        about_menu.pack(side="left", padx=5, pady=5)
    
    def _browse_folder(self):
        """Выбор папки для сохранения"""
        from tkinter import filedialog
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
        self.logger_thread = RTTLoggerThread(host, port, self._log_callback, self.stop_event)
        self.logger_thread.start()
        
        self.is_connected = True
        self.connect_btn.configure(text="Отключиться", fg_color="#E74C3C")
        self.status_label.configure(text="Статус: Подключено", text_color="#2ECC71")
        
        # Создание файла лога
        if self.autosave_var.get():
            self._create_log_file()
    
    def _disconnect(self):
        """Отключение от RTT"""
        self.stop_event.set()
        if self.logger_thread:
            self.logger_thread.join(timeout=2.0)
        
        self.is_connected = False
        self.connect_btn.configure(text="Подключиться", fg_color="#2ECC71")
        self.status_label.configure(text="Статус: Отключено", text_color="#95A5A6")
        
        # Закрытие файла лога
        if self.log_file:
            try:
                self.log_file.close()
            except:
                pass
            self.log_file = None
    
    def _create_log_file(self):
        """Создание файла для сохранения логов"""
        try:
            output_dir = Path(self.folder_entry.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if self.rotation_var.get():
                date_str = datetime.now().strftime("%Y-%m-%d")
                filename = f"RTT_log_{date_str}.txt"
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"RTT_log_{timestamp}.txt"
            
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
            # Закрываем старый файл и создаём новый
            try:
                self.log_file.close()
            except:
                pass
            self._create_log_file()
    
    def _log_callback(self, line, level='default'):
        """Обработка полученной строки лога (вызывается из потока)"""
        # Планируем обновление GUI в главном потоке
        self.after(0, lambda: self._update_gui(line, level))
    
    def _update_gui(self, line, level):
        """Обновление GUI (в главном потоке)"""
        # Применение фильтра
        filter_text = self.filter_entry.get().strip()
        if filter_text and filter_text.lower() not in line.lower():
            return
        
        # Добавление в текстовое поле
        self.log_text.configure(state='normal')
        
        # Определение уровня лога
        if 'ERROR' in line or 'FATAL' in line or 'PANIC' in line:
            tag = 'error'
        elif 'WARN' in line:
            tag = 'warn'
        elif 'INFO' in line or 'OK' in line or 'SUCCESS' in line:
            tag = 'info'
        elif 'DEBUG' in line:
            tag = 'debug'
        else:
            tag = 'default'
        
        # Вставка с временной меткой отдельно для цвета
        if '] ' in line:
            timestamp_part, message_part = line.split('] ', 1)
            timestamp_part += '] '
            self.log_text.insert('end', timestamp_part, 'timestamp')
            self.log_text.insert('end', message_part + '\n', tag)
        else:
            self.log_text.insert('end', line + '\n', tag)
        
        # Автоскролл
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
        
        # Проверка ротации
        self._check_rotation()
    
    def _clear_logs(self):
        """Очистка окна логов"""
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
    
    def _apply_filter(self):
        """Применение фильтра (просто очищает и перечитывает, если бы была история)"""
        messagebox.showinfo("Фильтр", "Фильтр будет применён к новым сообщениям")
    
    def _export_logs(self):
        """Экспорт логов в файл"""
        from tkinter import filedialog
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    self.log_text.configure(state='normal')
                    content = self.log_text.get('1.0', 'end')
                    # Удаление ANSI-кодов если есть
                    content = re.sub(r'\x1b\[[0-9;]*m', '', content)
                    f.write(content)
                messagebox.showinfo("Экспорт", f"Логи экспортированы в:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать:\n{str(e)}")
    
    def _show_settings(self):
        """Показ настроек"""
        settings_window = ctk.CTkToplevel(self)
        settings_window.title("Настройки")
        settings_window.geometry("400x300")
        
        ctk.CTkLabel(settings_window, text="Настройки приложения", 
                      font=("Arial", 16, "bold")).pack(pady=10)
        
        ctk.CTkLabel(settings_window, text="Здесь будут дополнительные настройки",
                      text_color="gray").pack(pady=20)
        
        ctk.CTkButton(settings_window, text="Закрыть", 
                       command=settings_window.destroy).pack(pady=10)
    
    def _show_about(self):
        """Показ информации о программе"""
        about_window = ctk.CTkToplevel(self)
        about_window.title("О программе")
        about_window.geometry("400x250")
        
        ctk.CTkLabel(about_window, text="J-Link RTT Auto Logger", 
                      font=("Arial", 18, "bold")).pack(pady=10)
        
        ctk.CTkLabel(about_window, text="Версия 3.0", 
                      text_color="gray").pack()
        
        info_text = """
Графический интерфейс для чтения логов J-Link RTT

Возможности:
• Автоматическая ротация логов по дням
• Умная буферизация данных
• Цветовое выделение уровней логов
• Автосохранение в файлы
• Фильтрация логов

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
                self.destroy()
        else:
            self.destroy()


def main():
    app = RTTLoggerGUI()
    app.mainloop()


if __name__ == '__main__':
    # Установка темы
    ctk.set_appearance_mode("dark")  # "light" или "dark"
    ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
    
    main()
