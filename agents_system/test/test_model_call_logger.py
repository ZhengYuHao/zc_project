"""
测试模型调用日志记录功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.model_config import load_model_config
from models.model_manager import ModelManager
from models.model_call_logger import ModelCallLogger


async def test_model_call_logging():
    """测试模型调用日志记录功能"""
    print("Testing model call logging...")
    
    # 加载配置
    config = load_model_config()
    
    # 创建模型管理器
    model_manager = ModelManager(config)
    
    # 显示日志记录配置信息
    logging_config = config.get("model_call_logging", {})
    print(f"Model call logging enabled: {logging_config.get('enabled', False)}")
    
    # 清空之前的记录
    ModelCallLogger.clear_current_calls()
    
    # 测试通过模型管理器调用
    print("\n=== 通过模型管理器调用 ===")
    try:
        result = await model_manager.call_model("default", "请写一句关于技术的名言")
        print(f"模型响应: {result[:100]}...")
    except Exception as e:
        print(f"通过模型管理器调用出错: {e}")
    
    # 获取当前记录
    current_calls = ModelCallLogger.get_current_calls()
    print(f"\n当前请求中共有 {len(current_calls)} 条模型调用记录")
    
    for i, call in enumerate(current_calls):
        print(f"记录 {i+1}:")
        print(f"  任务类型: {call['task_type']}")
        print(f"  提示词: {call['prompt'][:50]}...")
        print(f"  响应: {call['response'][:100]}...")
        print(f"  时间戳: {call['timestamp']}")
    
    print("\nModel calls logged successfully!")


if __name__ == "__main__":
    asyncio.run(test_model_call_logging())