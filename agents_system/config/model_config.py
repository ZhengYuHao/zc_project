import json
import os
from typing import Dict, Any


def load_model_config() -> Dict[str, Any]:
    """加载模型配置"""
    config_path = os.path.join(os.path.dirname(__file__), "model_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading model config: {e}")
            return {}
    return {}