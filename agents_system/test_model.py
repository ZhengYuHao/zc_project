import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.model_config import load_model_config
from models.model_manager import ModelManager

async def test_model_call():
    # 加载配置
    config = load_model_config()
    
    # 创建模型管理器
    model_manager = ModelManager(config)
    
    # 显示模型配置信息
    print("Model configuration:")
    print(f"  Task model mapping: {model_manager._task_model_mapping}")
    
    # 测试调用 - 使用正确的任务类型
    test_prompt = "请生成一个简单的文本"
    task_type = "_generate_planting_content_cp"  # 使用配置文件中定义的任务类型
    
    print(f"\nTesting model call for task: {task_type}")
    print(f"Prompt: {test_prompt}")
    
    result = await model_manager.call_model(task_type, test_prompt)
    
    print(f"\nModel response: {result}")

if __name__ == "__main__":
    asyncio.run(test_model_call())