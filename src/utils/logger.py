import logging
from typing import Optional
from pathlib import Path

class AppLogger:
    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger('FolderSyncPro')
        self.logger.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
        # File handler
        if log_file:
            Path(log_file).parent.mkdir(exist_ok=True)
            fh = logging.FileHandler(log_file, encoding='utf-8')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            
    def log(self, message: str, level: str = 'info'):
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message)
        
    # Alias methods
    def info(self, message): self.log(message, 'info')
    def warning(self, message): self.log(message, 'warning')
    def error(self, message): self.log(message, 'error')