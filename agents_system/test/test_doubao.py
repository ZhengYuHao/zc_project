import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.doubao import call_doubao, call_doubao_stream, get_doubao_model


async def test_doubao_model():
    """测试豆包模型功能"""
    print("测试豆包模型...")
    
    # 测试便捷函数调用
    try:
        print("1. 测试便捷函数调用:")
        result = await call_doubao("你好，请简单介绍一下自己")
        print(f"结果: {result}\n")
    except Exception as e:
        print(f"便捷函数调用出错: {e}\n")
    
    
    # 测试模型类调用
    try:
        print("3. 测试模型类调用:")
        model = get_doubao_model()
        result = await model.generate_text("什么是人工智能？")
        print(f"结果: {result}\n")
    except Exception as e:
        print(f"模型类调用出错: {e}\n")


if __name__ == "__main__":
    asyncio.run(test_doubao_model())