"""日志工具模块"""

import logging
import sys
from pathlib import Path
from typing import Optional

class Logger:
    """日志管理器"""
    _instance = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # 在创建实例时初始化日志器
            cls._instance._logger = logging.getLogger("ComicsUpscaler")
            cls._instance._logger.setLevel(logging.INFO)
            
            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # 添加控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            cls._instance._logger.addHandler(console_handler)
        return cls._instance
    
    @property
    def logger(self) -> logging.Logger:
        """获取日志器"""
        return self._logger
    
    def add_file_handler(self, log_path: Path) -> None:
        """添加文件处理器
        
        Args:
            log_path: 日志文件路径
        """
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_path, encoding='utf-8')
            file_handler.setFormatter(self._logger.handlers[0].formatter)
            self._logger.addHandler(file_handler)

# 创建全局日志器实例
logger = Logger().logger 