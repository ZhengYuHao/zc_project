from typing import Dict, Any, Optional
import asyncio

from config.model_config import load_model_config
from models.model_factory import ModelFactory
from utils.logger import get_logger
from models.model_call_logger import ModelCallLogger

logger = get_logger(__name__)


class ModelManager:
    """模型管理器，负责根据任务类型选择合适的模型"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化模型管理器"""
        if config is None:
            config = load_model_config()
        
        self.config = config
        self.model_factory = ModelFactory()
        self.call_logger = ModelCallLogger()
        self._init_config()
    
    def _init_config(self):
        """初始化配置"""
        models_config = self.config.get("models", {})
        
        # 初始化默认模型
        default_config = models_config.get("default", {})
        if default_config:
            try:
                self._default_model = self.model_factory.get_model("doubao", default_config)
                logger.info("Initialized default model: doubao")
            except Exception as e:
                logger.error(f"Failed to initialize default model: {e}")
                self._default_model = None
        else:
            self._default_model = None
    
    def get_model_for_task(self, task_type: str):
        """根据任务类型获取模型"""
        models_config = self.config.get("models", {})
        
        # 查找特定任务的配置
        model_config_name = self.config.get("task_model_mapping", {}).get(task_type, "default")
        model_config = models_config.get(model_config_name, {})
        
        # 如果没有找到特定配置，使用默认配置
        if not model_config and model_config_name != "default":
            model_config = models_config.get("default", {})
        
        # 获取模型类型
        model_type = model_config.get("type", "doubao") if model_config else "doubao"
        
        # 创建或获取模型实例
        try:
            model = self.model_factory.get_model(model_type, model_config)
            logger.info(f"Using model {model_type} for task {task_type}")
            return model
        except Exception as e:
            logger.error(f"Failed to get model for task {task_type}: {e}")
            # 回退到默认模型
            if self._default_model:
                logger.info(f"Falling back to default model for task {task_type}")
                return self._default_model
            else:
                raise
    
    async def call_model(self, task_type: str, prompt: str, **kwargs) -> str:
        """调用模型生成文本"""
        model = self.get_model_for_task(task_type)
        response = await model.generate_text(prompt, **kwargs)
        
        # 记录模型调用
        await self.call_logger.log_call(task_type, prompt, response, **kwargs)
        
        return response
    
    async def call_model_stream(self, task_type: str, prompt: str, **kwargs):
        """流式调用模型生成文本并记录日志"""
        model = self.get_model_for_task(task_type)
        response_parts = []
        try:
            async for chunk in model.generate_text_stream(prompt, **kwargs):
                yield chunk
                response_parts.append(chunk)
            response = ''.join(response_parts)
        finally:
            # 无论成功与否都尝试记录日志
            try:
                await self.call_logger.log_call(task_type, prompt, ''.join(response_parts), **kwargs)
            except Exception as e:
                logger.error(f"Failed to log stream call: {e}")