import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.model_config import load_model_config
from models.model_manager import ModelManager
from core.task_processor import extract_blogger_style

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

async def test_blogger_style_extraction():
    """测试达人风格提取功能"""
    print("\n" + "="*50)
    print("测试达人风格提取功能")
    print("="*50)
    
    # 构造测试请求数据
    test_request_data = {
        "url": "https://zongsing.com/prod-api/platform/agent/homepage/listNoteByUserUuid"
    }
    
    print(f"测试URL: {test_request_data['url']}")
    print("注意：此测试需要有效的豆包视觉模型端点配置")
    print("当前配置的视觉模型端点: ep-20250925153000-mlvvp")
    print("如果该端点不存在或无法访问，将返回默认响应")
    
    try:
        # 调用函数
        result = await extract_blogger_style(test_request_data)
        
        print("\n达人风格分析结果:")
        print("-" * 30)
        print(f"风格分析: {result.get('blogger_style', 'N/A')}")
        print(f"语调: {result.get('tone', 'N/A')}")
        print(f"表达风格: {result.get('expression_style', 'N/A')}")
        
        # 判断是否使用了默认响应
        if "未分析出具体风格" in result.get('blogger_style', ''):
            print("\n注意：由于视觉模型端点配置问题，返回了默认响应")
            print("请检查并更新config/model_config.json中的blogger_style_analysis模型配置")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行模型测试
    # asyncio.run(test_model_call())
    
    # 运行达人风格提取测试
    asyncio.run(test_blogger_style_extraction())