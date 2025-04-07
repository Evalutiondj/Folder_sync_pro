import os
import shutil
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import subprocess
import json
import hashlib
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
import winreg
import sys
from typing import Optional, Tuple, List, Dict

# Constants
CONFIG_FILE = "config.json"
LOG_FILE = "sync.log"
DEFAULT_INTERVAL = 5  # minutes

class SyncHandler(FileSystemEventHandler):
    """Xử lý sự kiện thay đổi file real-time"""
    def __init__(self, app):
        self.app = app
        
    def on_modified(self, event):
        if not event.is_directory:
            self.app.file_queue.put(('modified', event.src_path))
            
    def on_created(self, event):
        if not event.is_directory:
            self.app.file_queue.put(('created', event.src_path))
            
    def on_deleted(self, event):
        self.app.file_queue.put(('deleted', event.src_path))

class FolderSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FolderSync Pro")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Khởi tạo các biến
        self.sync_thread = None
        self.sync_running = False
        self.auto_sync = False
        self.paused = False
        self.file_queue = Queue()
        self.observer = None
        
        # Biến giao diện
        self.progress_value = tk.DoubleVar(value=0)
        self.sync_mode = tk.StringVar(value="mirror")
        self.interval = tk.IntVar(value=DEFAULT_INTERVAL)
        self.bidirectional = tk.BooleanVar(value=False)
        self.current_filter = tk.StringVar(value='all')
        self.encryption_enabled = tk.BooleanVar(value=False)
        
        # Cấu hình filter
        self.file_filters = {
            'all': [],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
            'documents': ['.doc', '.docx', '.pdf', '.txt', '.xlsx'],
            'custom': []
        }
        
        # Khởi tạo hệ thống
        self.setup_logging()
        self.load_config()
        self.load_icons()
        self.build_ui()
        self.log("Ứng dụng đã khởi động", level="info")
        
        # Bắt đầu các dịch vụ nền
        self.start_auto_sync()
        if self.config.get('realtime', False):
            self.start_realtime_sync()

    def setup_logging(self):
        """Cấu hình hệ thống logging chuyên nghiệp"""
        logging.basicConfig(
            filename=LOG_FILE,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )
        self.logger = logging.getLogger('FolderSyncPro')

    def load_config(self):
        """Đọc cấu hình từ file"""
        self.config = {
            "src": "",
            "dst": "",
            "mode": "mirror",
            "interval": DEFAULT_INTERVAL,
            "filters": {},
            "realtime": False,
            "bidirectional": False,
            "encryption": False
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except Exception as e:
                self.log(f"Lỗi đọc cấu hình: {str(e)}", level="error")
                
        # Cập nhật biến giao diện
        self.sync_mode.set(self.config["mode"])
        self.interval.set(self.config["interval"])
        self.bidirectional.set(self.config["bidirectional"])
        self.encryption_enabled.set(self.config["encryption"])
        if "filters" in self.config:
            self.file_filters.update(self.config["filters"])

    def save_config(self):
        """Lưu cấu hình vào file"""
        self.config.update({
            "src": self.src_entry.get(),
            "dst": self.dst_entry.get(),
            "mode": self.sync_mode.get(),
            "interval": self.interval.get(),
            "bidirectional": self.bidirectional.get(),
            "encryption": self.encryption_enabled.get(),
            "filters": self.file_filters,
            "realtime": self.realtime_var.get() if hasattr(self, 'realtime_var') else False
        })
        
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.log(f"Lỗi lưu cấu hình: {str(e)}", level="error")

    def load_icons(self):
        """Tải các icon cho giao diện"""
        icons = {
            'log': 'log.png',
            'settings': 'settings.png',
            'sync': 'sync.png',
            'folder': 'folder.png',
            'pause': 'pause.png',
            'resume': 'resume.png',
            'add': 'add.png',
            'remove': 'remove.png'
        }
        
        self.icons = {}
        for name, filename in icons.items():
            try:
                path = os.path.join("icons", filename)
                img = Image.open(path)
                img = img.resize((20, 20), Image.Resampling.LANCZOS)
                self.icons[name] = ImageTk.PhotoImage(img)
            except Exception as e:
                self.log(f"Không tải được icon {name}: {str(e)}", level="warning")
                self.icons[name] = None

    def build_ui(self):
        """Xây dựng giao diện người dùng"""
        self.setup_menu()
        self.setup_notebook()
        self.setup_main_tab()
        self.setup_advanced_tab()
        self.setup_status_bar()

    def setup_menu(self):
        """Tạo menu chính"""
        menubar = tk.Menu(self.root)
        
        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Lưu cấu hình", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Menu Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Xem log", command=self.open_log_file)
        tools_menu.add_command(label="Mở thư mục đích", command=self.open_dest_folder)
        menubar.add_cascade(label="Công cụ", menu=tools_menu)
        
        self.root.config(menu=menubar)

    def setup_notebook(self):
        """Tạo notebook (tab)"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Tab chính
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Đồng bộ chính")
        
        # Tab nâng cao
        self.advanced_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.advanced_tab, text="Nâng cao")

    def setup_main_tab(self):
        """Xây dựng nội dung tab chính"""
        # Frame thư mục
        dir_frame = ttk.LabelFrame(self.main_tab, text="Thư mục")
        dir_frame.pack(fill='x', padx=5, pady=5)
        
        # Thư mục nguồn
        ttk.Label(dir_frame, text="Nguồn:").grid(row=0, column=0, sticky='w')
        self.src_entry = ttk.Entry(dir_frame, width=50)
        self.src_entry.insert(0, self.config["src"])
        self.src_entry.grid(row=0, column=1, padx=5, sticky='we')
        ttk.Button(dir_frame, image=self.icons['folder'], command=self.browse_src).grid(row=0, column=2)
        
        # Thư mục đích
        ttk.Label(dir_frame, text="Đích:").grid(row=1, column=0, sticky='w')
        self.dst_entry = ttk.Entry(dir_frame, width=50)
        self.dst_entry.insert(0, self.config["dst"])
        self.dst_entry.grid(row=1, column=1, padx=5, sticky='we')
        ttk.Button(dir_frame, image=self.icons['folder'], command=self.browse_dst).grid(row=1, column=2)
        
        # Frame chế độ
        mode_frame = ttk.LabelFrame(self.main_tab, text="Chế độ đồng bộ")
        mode_frame.pack(fill='x', padx=5, pady=5)
        
        # Radio buttons
        modes = [
            ("Gương (Xóa và thay thế)", "mirror"),
            ("Cập nhật (Ghi đè nếu mới hơn)", "update"),
            ("Thêm mới (Không ghi đè)", "add"),
            ("Strict (Kiểm tra hash)", "strict")
        ]
        
        for text, mode in modes:
            ttk.Radiobutton(
                mode_frame, 
                text=text, 
                variable=self.sync_mode, 
                value=mode
            ).pack(anchor='w', padx=10)
        
        # Frame tùy chọn
        opt_frame = ttk.LabelFrame(self.main_tab, text="Tùy chọn")
        opt_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Checkbutton(
            opt_frame, 
            text="Đồng bộ 2 chiều", 
            variable=self.bidirectional
        ).pack(anchor='w', padx=10)
        
        ttk.Checkbutton(
            opt_frame, 
            text="Mã hóa file", 
            variable=self.encryption_enabled
        ).pack(anchor='w', padx=10)
        
        # Frame filter
        filter_frame = ttk.LabelFrame(self.main_tab, text="Lọc file")
        filter_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Combobox(
            filter_frame, 
            textvariable=self.current_filter, 
            values=list(self.file_filters.keys())
        ).pack(padx=10, pady=5, fill='x')
        
        # Frame nút điều khiển
        btn_frame = ttk.Frame(self.main_tab)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        buttons = [
            ("Đồng bộ", self.icons['sync'], self.start_sync),
            ("Tạm dừng", self.icons['pause'], self.pause_sync),
            ("Tiếp tục", self.icons['resume'], self.resume_sync),
            ("Log", self.icons['log'], self.toggle_log),
            ("Cài đặt", self.icons['settings'], self.open_settings)
        ]
        
        for i, (text, icon, cmd) in enumerate(buttons):
            ttk.Button(
                btn_frame, 
                text=text, 
                image=icon, 
                compound='left', 
                command=cmd
            ).grid(row=0, column=i, padx=5)
        
        # Thanh tiến trình
        self.progress_frame = ttk.Frame(self.main_tab)
        self.progress_frame.pack(fill='x', padx=5, pady=5)
        
        self.progress_label = ttk.Label(
            self.progress_frame, 
            text="Tiến trình: 0%", 
            anchor='w'
        )
        self.progress_label.pack(fill='x')
        
        self.progress = ttk.Progressbar(
            self.progress_frame, 
            variable=self.progress_value, 
            maximum=100
        )
        self.progress.pack(fill='x')
        
        # Console log
        self.log_frame = ttk.LabelFrame(self.main_tab, text="Nhật ký")
        self.log_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.log_text = tk.Text(
            self.log_frame, 
            wrap='word', 
            state='disabled'
        )
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.log_text)
        scrollbar.pack(side='right', fill='y')
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)

    def setup_advanced_tab(self):
        """Xây dựng tab nâng cao"""
        # Frame real-time
        rt_frame = ttk.LabelFrame(self.advanced_tab, text="Đồng bộ real-time")
        rt_frame.pack(fill='x', padx=5, pady=5)
        
        self.realtime_var = tk.BooleanVar(value=self.config.get('realtime', False))
        ttk.Checkbutton(
            rt_frame, 
            text="Bật đồng bộ real-time", 
            variable=self.realtime_var,
            command=self.toggle_realtime_sync
        ).pack(anchor='w', padx=10)
        
        # Frame tự động
        auto_frame = ttk.LabelFrame(self.advanced_tab, text="Tự động đồng bộ")
        auto_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(auto_frame, text="Khoảng thời gian (phút):").pack(anchor='w', padx=10)
        ttk.Entry(auto_frame, textvariable=self.interval).pack(anchor='w', padx=10, pady=5, fill='x')
        
        # Frame filter tùy chỉnh
        custom_filter_frame = ttk.LabelFrame(self.advanced_tab, text="Bộ lọc tùy chỉnh")
        custom_filter_frame.pack(fill='x', padx=5, pady=5)
        
        self.custom_filter_entry = ttk.Entry(custom_filter_frame)
        self.custom_filter_entry.pack(side='left', padx=5, pady=5, expand=True, fill='x')
        
        ttk.Button(
            custom_filter_frame, 
            text="Thêm", 
            image=self.icons['add'], 
            compound='left',
            command=self.add_custom_filter
        ).pack(side='left', padx=5)
        
        ttk.Button(
            custom_filter_frame, 
            text="Xóa", 
            image=self.icons['remove'], 
            compound='left',
            command=self.remove_custom_filter
        ).pack(side='left', padx=5)
        
        # Frame khởi động cùng hệ thống
        startup_frame = ttk.LabelFrame(self.advanced_tab, text="Khởi động")
        startup_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(
            startup_frame, 
            text="Thêm vào khởi động", 
            command=self.enable_autostart
        ).pack(padx=10, pady=5, anchor='w')
        
        # Frame mã hóa
        encrypt_frame = ttk.LabelFrame(self.advanced_tab, text="Bảo mật")
        encrypt_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(
            encrypt_frame, 
            text="Tạo khóa mã hóa", 
            command=self.generate_encryption_key
        ).pack(padx=10, pady=5, anchor='w')

    def setup_status_bar(self):
        """Tạo thanh trạng thái"""
        self.status_bar = ttk.Label(
            self.root, 
            text="Sẵn sàng", 
            relief='sunken', 
            anchor='w'
        )
        self.status_bar.pack(side='bottom', fill='x')

    def browse_src(self):
        """Chọn thư mục nguồn"""
        path = filedialog.askdirectory()
        if path:
            self.src_entry.delete(0, tk.END)
            self.src_entry.insert(0, path)
            self.save_config()

    def browse_dst(self):
        """Chọn thư mục đích"""
        path = filedialog.askdirectory()
        if path:
            self.dst_entry.delete(0, tk.END)
            self.dst_entry.insert(0, path)
            self.save_config()

    def toggle_log(self):
        """Ẩn/hiện log"""
        if self.log_frame.winfo_ismapped():
            self.log_frame.pack_forget()
        else:
            self.log_frame.pack(fill='both', expand=True, padx=5, pady=5)

    def open_settings(self):
        """Mở cửa sổ cài đặt (đã tích hợp vào tab nâng cao)"""
        self.notebook.select(self.advanced_tab)

    def enable_autostart(self):
        """Thêm vào khởi động cùng Windows"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(
                key, 
                "FolderSyncPro", 
                0, 
                winreg.REG_SZ, 
                sys.executable + ' "' + os.path.abspath(__file__) + '"'
            )
            winreg.CloseKey(key)
            self.log("Đã thêm vào khởi động cùng Windows", level="info")
            messagebox.showinfo("Thành công", "Đã thêm vào khởi động cùng Windows")
        except Exception as e:
            self.log(f"Lỗi khi thêm vào khởi động: {str(e)}", level="error")
            messagebox.showerror("Lỗi", f"Không thể thêm vào khởi động: {str(e)}")

    def open_log_file(self):
        """Mở file log bằng ứng dụng mặc định"""
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)
        else:
            messagebox.showerror("Lỗi", "Không tìm thấy file log")

    def open_dest_folder(self):
        """Mở thư mục đích"""
        dst = self.dst_entry.get()
        if dst and os.path.exists(dst):
            os.startfile(dst)
        else:
            messagebox.showerror("Lỗi", "Thư mục đích không tồn tại")

    def add_custom_filter(self):
        """Thêm extension vào bộ lọc tùy chỉnh"""
        ext = self.custom_filter_entry.get().strip()
        if ext and not ext.startswith('.'):
            ext = '.' + ext
            
        if ext and ext not in self.file_filters['custom']:
            self.file_filters['custom'].append(ext)
            self.log(f"Đã thêm bộ lọc: {ext}", level="info")
            self.save_config()
            self.custom_filter_entry.delete(0, tk.END)

    def remove_custom_filter(self):
        """Xóa extension khỏi bộ lọc tùy chỉnh"""
        ext = self.custom_filter_entry.get().strip()
        if ext and not ext.startswith('.'):
            ext = '.' + ext
            
        if ext in self.file_filters['custom']:
            self.file_filters['custom'].remove(ext)
            self.log(f"Đã xóa bộ lọc: {ext}", level="info")
            self.save_config()
            self.custom_filter_entry.delete(0, tk.END)

    def generate_encryption_key(self):
        """Tạo khóa mã hóa (ví dụ đơn giản)"""
        # Trong thực tế nên dùng thư viện chuyên dụng
        key = os.urandom(32).hex()
        with open("encryption.key", "w") as f:
            f.write(key)
        self.log("Đã tạo khóa mã hóa", level="info")
        messagebox.showinfo("Thành công", "Đã tạo khóa mã hóa trong file encryption.key")

    def toggle_realtime_sync(self):
        """Bật/tắt đồng bộ real-time"""
        if self.realtime_var.get():
            self.start_realtime_sync()
        else:
            self.stop_realtime_sync()
        self.save_config()

    def start_realtime_sync(self):
        """Bắt đầu theo dõi thay đổi real-time"""
        if hasattr(self, 'observer') and self.observer.is_alive():
            return
            
        src = self.src_entry.get()
        if not src or not os.path.exists(src):
            self.log("Không thể bật real-time: Thư mục nguồn không hợp lệ", level="error")
            self.realtime_var.set(False)
            return
            
        try:
            event_handler = SyncHandler(self)
            self.observer = Observer()
            self.observer.schedule(event_handler, src, recursive=True)
            self.observer.start()
            threading.Thread(target=self.process_queue, daemon=True).start()
            self.log("Đã bật đồng bộ real-time", level="info")
        except Exception as e:
            self.log(f"Lỗi khi bật real-time: {str(e)}", level="error")
            self.realtime_var.set(False)

    def stop_realtime_sync(self):
        """Dừng đồng bộ real-time"""
        if hasattr(self, 'observer'):
            self.observer.stop()
            self.observer.join()
            self.log("Đã tắt đồng bộ real-time", level="info")

    def process_queue(self):
        """Xử lý hàng đợi thay đổi file (real-time)"""
        while True:
            action, file_path = self.file_queue.get()
            if not all([self.src_entry.get(), self.dst_entry.get()]):
                continue
                
            rel_path = os.path.relpath(file_path, self.src_entry.get())
            dst_path = os.path.join(self.dst_entry.get(), rel_path)
            
            try:
                if action in ('modified', 'created'):
                    if self.should_sync_file(file_path, dst_path):
                        if self.encryption_enabled.get():
                            self.encrypt_file(file_path, dst_path)
                        else:
                            shutil.copy2(file_path, dst_path)
                        self.log(f"Real-time: Đã cập nhật {rel_path}", level="info")
                elif action == 'deleted':
                    if os.path.exists(dst_path):
                        os.remove(dst_path)
                        self.log(f"Real-time: Đã xóa {rel_path}", level="info")
            except Exception as e:
                self.log(f"Lỗi real-time {action} {rel_path}: {str(e)}", level="error")

    def start_sync(self):
        """Bắt đầu quá trình đồng bộ"""
        if self.sync_running:
            messagebox.showinfo("Thông báo", "Đồng bộ đang chạy")
            return
            
        src = self.src_entry.get()
        dst = self.dst_entry.get()
        
        if not src or not dst:
            messagebox.showerror("Lỗi", "Vui lòng chọn cả thư mục nguồn và đích")
            return
            
        if not os.path.exists(src) or not os.path.exists(dst):
            messagebox.showerror("Lỗi", "Thư mục nguồn hoặc đích không tồn tại")
            return
            
        self.sync_running = True
        self.paused = False
        self.progress_value.set(0)
        self.progress_label.config(text="Tiến trình: 0%")
        self.log(f"Bắt đầu đồng bộ từ {src} đến {dst}", level="info")
        
        self.sync_thread = threading.Thread(
            target=self.sync_folders,
            args=(src, dst, self.sync_mode.get(), self.bidirectional.get()),
            daemon=True
        )
        self.sync_thread.start()
        self.save_config()

    def pause_sync(self):
        """Tạm dừng đồng bộ"""
        if self.sync_running and not self.paused:
            self.paused = True
            self.log("Đã tạm dừng đồng bộ", level="info")

    def resume_sync(self):
        """Tiếp tục đồng bộ sau khi tạm dừng"""
        if self.sync_running and self.paused:
            self.paused = False
            self.log("Đã tiếp tục đồng bộ", level="info")

    def sync_folders(self, src: str, dst: str, mode: str, bidirectional: bool = False):
        """Đồng bộ thư mục chính"""
        try:
            # Đồng bộ chiều chính (src -> dst)
            self._sync_one_way(src, dst, mode)
            
            # Đồng bộ chiều ngược lại nếu được chọn
            if bidirectional:
                self.log("Bắt đầu đồng bộ chiều ngược lại...", level="info")
                self._sync_one_way(dst, src, mode)
                
            self.log("Đồng bộ hoàn tất!", level="info")
            messagebox.showinfo("Thành công", "Đồng bộ hoàn tất")
        except Exception as e:
            self.log(f"Lỗi đồng bộ: {str(e)}", level="error")
            messagebox.showerror("Lỗi", f"Đồng bộ thất bại: {str(e)}")
        finally:
            self.sync_running = False
            self.progress_value.set(100)
            self.progress_label.config(text="Tiến trình: 100%")

    def _sync_one_way(self, src: str, dst: str, mode: str):
        """Đồng bộ một chiều"""
        total_files = 0
        copied_files = 0
        
        # Tính tổng số file cần xử lý
        for root, _, files in os.walk(src):
            for file in files:
                if self.should_include_file(file):
                    total_files += 1
        
        if total_files == 0:
            self.log("Không có file nào để đồng bộ", level="warning")
            return
            
        # Bắt đầu đồng bộ
        for root, dirs, files in os.walk(src):
            # Tạo thư mục tương ứng ở đích
            rel_path = os.path.relpath(root, src)
            dest_dir = os.path.join(dst, rel_path)
            os.makedirs(dest_dir, exist_ok=True)
            
            for file in files:
                while self.paused:
                    time.sleep(0.5)
                
                if not self.should_include_file(file):
                    continue
                    
                src_file = os.path.join(root, file)
                dst_file = os.path.join(dest_dir, file)
                
                if self.should_sync_file(src_file, dst_file, mode):
                    try:
                        if self.encryption_enabled.get():
                            self.encrypt_file(src_file, dst_file)
                        else:
                            shutil.copy2(src_file, dst_file)
                            
                        copied_files += 1
                        progress = (copied_files / total_files) * 100
                        self.update_progress(progress, file)
                    except Exception as e:
                        self.log(f"Lỗi khi copy {file}: {str(e)}", level="error")

    def should_include_file(self, filename: str) -> bool:
        """Kiểm tra file có phù hợp với bộ lọc không"""
        current_filter = self.current_filter.get()
        if current_filter == 'all':
            return True
            
        ext = os.path.splitext(filename)[1].lower()
        return ext in self.file_filters.get(current_filter, [])

    def should_sync_file(self, src: str, dst: str, mode: str = None) -> bool:
        """Xác định có cần đồng bộ file không"""
        if mode is None:
            mode = self.sync_mode.get()
            
        if not os.path.exists(dst):
            return True
            
        if mode == "mirror":
            return True
        elif mode == "update":
            return os.path.getmtime(src) > os.path.getmtime(dst)
        elif mode == "add":
            return False
        elif mode == "strict":
            return self.get_file_hash(src) != self.get_file_hash(dst)
        return False

    def get_file_hash(self, filepath: str) -> str:
        """Tính toán hash MD5 của file"""
        hash_md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.log(f"Lỗi khi tính hash {filepath}: {str(e)}", level="error")
            return ""

    def encrypt_file(self, src: str, dst: str):
        """Mã hóa file (ví dụ đơn giản)"""
        # Trong thực tế nên dùng thư viện như cryptography
        try:
            with open(src, 'rb') as f_src, open(dst, 'wb') as f_dst:
                key = 0x55  # Trong thực tế nên dùng key từ file
                for byte in f_src.read():
                    f_dst.write(bytes([byte ^ key]))
        except Exception as e:
            self.log(f"Lỗi mã hóa {src}: {str(e)}", level="error")
            raise

    def update_progress(self, progress: float, filename: str = ""):
        """Cập nhật tiến trình đồng bộ"""
        self.progress_value.set(progress)
        self.progress_label.config(text=f"Tiến trình: {int(progress)}% - {filename}")
        self.root.update_idletasks()

    def start_auto_sync(self):
        """Tự động đồng bộ theo chu kỳ"""
        def sync_loop():
            while True:
                if self.auto_sync and not self.sync_running:
                    self.start_sync()
                time.sleep(self.interval.get() * 60)
                
        threading.Thread(target=sync_loop, daemon=True).start()

    def log(self, message: str, level: str = "info"):
        """Ghi log vào cả giao diện và file"""
        timestamp = time.strftime("[%H:%M:%S] ")
        full_msg = timestamp + message
        
        # Ghi vào console trong GUI
        self.log_text.config(state='normal')
        self.log_text.insert('end', full_msg + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        
        # Ghi vào file log qua logging
        if level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)
        
        # Cập nhật status bar
        self.status_bar.config(text=message)

    def on_closing(self):
        """Xử lý khi đóng ứng dụng"""
        self.stop_realtime_sync()
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FolderSyncApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()