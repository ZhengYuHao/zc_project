from typing import Dict, Any, Optional, Type
from .base_model import BaseModel
from .doubao import DoubaoModel
from .deepseek import DeepSeekModel
from .qwen import QwenModel


class ModelFactory:
    """模型工厂类"""
    
    # 模型类型映射
    _model_classes: Dict[str, Type[BaseModel]] = {
        "doubao": DoubaoModel,
        "deepseek": DeepSeekModel,
        "qwen": QwenModel
    }
    
    # 已创建的模型实例缓存
    _model_instances: Dict[str, BaseModel] = {}
    
    @classmethod
    def register_model_type(cls, model_type: str, model_class: Type[BaseModel]):
        """注册新的模型类型"""
        cls._model_classes[model_type] = model_class
    
    @classmethod
    def create_model(cls, model_type: str, config: Optional[Dict[str, Any]] = None) -> BaseModel:
        """创建模型实例"""
        if model_type not in cls._model_classes:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # 生成实例键
        config_str = str(sorted((config or {}).items()))
        instance_key = f"{model_type}_{config_str}"
        
        # 检查缓存中是否已存在实例
        if instance_key in cls._model_instances:
            return cls._model_instances[instance_key]
        
        # 创建新实例
        model_class = cls._model_classes[model_type]
        model_instance = model_class(config)
        cls._model_instances[instance_key] = model_instance
        
        return model_instance
    
    @classmethod
    def get_model(cls, model_type: str, config: Optional[Dict[str, Any]] = None) -> BaseModel:
        """获取模型实例（带缓存）"""
        return cls.create_model(model_type, config)