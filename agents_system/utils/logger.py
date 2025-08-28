import logging
import os
import sys
from typing import Optional


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings


class AgentLogger:
    """统一的日志模块，包含模块名、行号、时间戳等属性"""
    
    def __init__(self, name: str, log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            # 创建日志格式，包含时间戳、模块名、行号等信息
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            
            # 控制台处理器
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # 文件处理器
            if log_file or settings.LOG_FILE:
                log_path = log_file or settings.LOG_FILE
                if log_path:
                    # 确保日志目录存在
                    log_dir = os.path.dirname(log_path)
                    if log_dir and not os.path.exists(log_dir):
                        os.makedirs(log_dir)
                    
                    file_handler = logging.FileHandler(log_path)
                    file_handler.setFormatter(formatter)
                    self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def critical(self, message: str):
        self.logger.critical(message)


def get_logger(name: str) -> AgentLogger:
    """获取日志记录器的工厂方法"""
    return AgentLogger(name)