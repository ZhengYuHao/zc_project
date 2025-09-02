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
    QWEN_MODEL_NAME: str = Field(default="qwen-plus", alias="QWEN_MODEL_NAME")
    QWEN_API_BASE: str = Field(default="https://dashscope.aliyuncs.com/api/v1", alias="QWEN_API_BASE")
    
    # 豆包大模型配置
    DOUBAO_API_KEY: Optional[str] = Field(default=None, alias="DOUBAO_API_KEY")
    DOUBAO_MODEL_NAME: Optional[str] = Field(default=None, alias="DOUBAO_MODEL_NAME")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", alias="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default="logs/agents_system.log", alias="LOG_FILE")
    
    # 飞书配置
    FEISHU_APP_ID: Optional[str] = Field(default=None, alias="FEISHU_APP_ID")
    FEISHU_APP_SECRET: Optional[str] = Field(default=None, alias="FEISHU_APP_SECRET")
    FEISHU_VERIFY_TOKEN: Optional[str] = Field(default=None, alias="FEISHU_VERIFY_TOKEN")
    FEISHU_ENCRYPT_KEY: Optional[str] = Field(default=None, alias="FEISHU_ENCRYPT_KEY")
    
    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        env_file_encoding = "utf-8"


settings = Settings()