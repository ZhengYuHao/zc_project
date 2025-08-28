from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    # 项目基本信息
    PROJECT_NAME: str = Field(default="Agents System", alias="PROJECT_NAME")
    PROJECT_VERSION: str = Field(default="1.0.0", alias="PROJECT_VERSION")
    DEBUG: bool = Field(default=False, alias="DEBUG")
    
    # Qwen大模型配置
    QWEN_API_KEY: Optional[str] = Field(default=None, alias="QWEN_API_KEY")
    QWEN_MODEL_NAME: str = Field(default="qwen-turbo", alias="QWEN_MODEL_NAME")
    QWEN_API_BASE: str = Field(default="https://dashscope.aliyuncs.com/api/v1", alias="QWEN_API_BASE")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default="logs/agents_system.log", alias="LOG_FILE")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


settings = Settings()