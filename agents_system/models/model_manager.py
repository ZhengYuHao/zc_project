from typing import Dict, Any, Optional
from .base_model import BaseModel
from .model_factory import ModelFactory
from utils.logger import get_logger

logger = get_logger(__name__)


class ModelManager:
    """模型管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model_factory = ModelFactory()
        self._default_model: Optional[BaseModel] = None
        self._task_model_mapping: Dict[str, str] = {}
        
        # 初始化配置
        self._init_config()
    
    def _init_config(self):
        """初始化配置"""
        # 获取任务模型映射
        self._task_model_mapping = self.config.get("task_model_mapping", {})
        
        # 获取默认模型配置
        models_config = self.config.get("models", {})
        default_model_config = models_config.get("default", {})
        
        # 创建默认模型
        if default_model_config:
            model_type = default_model_config.get("type", "doubao")
            try:
                self._default_model = self.model_factory.get_model(
                    model_type, 
                    default_model_config
                )
                logger.info(f"Initialized default model: {model_type}")
            except Exception as e:
                logger.error(f"Failed to initialize default model: {e}")
    
    def get_model_for_task(self, task_type: str) -> BaseModel:
        """根据任务类型获取模型"""
        # 获取任务对应的模型配置名称
        model_config_name = self._task_model_mapping.get(
            task_type, 
            self._task_model_mapping.get("default", "default")
        )
        
        # 获取模型配置
        models_config = self.config.get("models", {})
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
        return await model.generate_text(prompt, **kwargs)
    
    async def call_model_stream(self, task_type: str, prompt: str, **kwargs):
        """流式调用模型生成文本"""
        model = self.get_model_for_task(task_type)
        async for chunk in model.generate_text_stream(prompt, **kwargs):
            yield chunk