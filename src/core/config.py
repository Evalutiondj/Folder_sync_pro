import json
import os
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = self._load_default_config()
        self.load_config()

    def _load_default_config(self) -> Dict[str, Any]:
        """Trả về cấu hình mặc định"""
        return {
            "src": "",
            "dst": "",
            "mode": "mirror",
            "interval": 5,
            "filters": {},
            "realtime": False,
            "bidirectional": False,
            "encryption": False
        }

    def load_config(self) -> None:
        """Đọc cấu hình từ file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config.update(json.load(f))
            except json.JSONDecodeError:
                self._create_default_config()

    def save_config(self) -> None:
        """Lưu cấu hình vào file"""
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def _create_default_config(self) -> None:
        """Tạo file cấu hình mới với giá trị mặc định"""
        self.save_config()

    def get(self, key: str, default=None):
        """Lấy giá trị cấu hình"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Thiết lập giá trị cấu hình"""
        self.config[key] = value