import tkinter as tk
from tkinter import ttk

class SyncControls(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Tạo các control đồng bộ
        self.sync_btn = ttk.Button(self, text="Đồng bộ")
        self.pause_btn = ttk.Button(self, text="Tạm dừng")
        self.resume_btn = ttk.Button(self, text="Tiếp tục")
        
        # Sắp xếp layout
        self.sync_btn.pack(side=tk.LEFT, padx=5)
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        self.resume_btn.pack(side=tk.LEFT, padx=5)