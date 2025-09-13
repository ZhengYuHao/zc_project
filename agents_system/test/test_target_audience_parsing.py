#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试目标人群提取的脚本，用于验证修复字符丢失问题
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents_system.core.task_processor import extract_target_audience
import asyncio


async def test_target_audience_parsing():
    """测试目标人群提取功能"""
    
    # 模拟包含问题的输入数据
    test_data = {
        "topic": "夏季护肤",
        "product_highlights": "这是一款具有防晒指数SPF50+的轻薄型防晒霜，含有透明质酸和维生素E，适合敏感肌肤使用。"
    }
    
    # 模拟大模型返回的结果（包含特殊字符）
    # 注意：这里我们直接测试解析逻辑，而不是调用实际的大模型
    
    # 模拟的模型响应文本（包含可能导致问题的空格）
    model_response = "目标人群：母婴群体、养宠家庭人群、数码 科技爱好者、家居家装关注者"
    
    print("原始模型响应:")
    print(repr(model_response))
    print()
    
    # 模拟解析过程
    lines = model_response.strip().split('\n')
    print("分割后的行:")
    print(lines)
    print()
    
    # 解析逻辑 - 旧方法
    target_audience_old = ""
    for line in lines:
        print(f"处理行: '{line}'")
        print(f"行的字节表示: {repr(line)}")
        
        if line.startswith("目标人群："):
            # 旧方法：使用固定索引
            content = line[6:].strip()
            print(f"旧方法截取后的内容: '{content}'")
            print(f"旧方法截取后内容的字节表示: {repr(content)}")
            target_audience_old = content
    
    print()
    
    # 解析逻辑 - 新方法
    target_audience_new = ""
    for line in lines:
        if line.startswith("目标人群："):
            # 新方法：使用字符串长度计算
            prefix = "目标人群："
            if line.startswith(prefix):
                content = line[len(prefix):].strip()
                print(f"新方法截取后的内容: '{content}'")
                print(f"新方法截取后内容的字节表示: {repr(content)}")
                target_audience_new = content
    
    print(f"\n旧方法提取的目标人群: '{target_audience_old}'")
    print(f"新方法提取的目标人群: '{target_audience_new}'")
    
    # 验证是否有字符丢失
    expected = "母婴群体、养宠家庭人群、数码 科技爱好者、家居家装关注者"
    if target_audience_new == expected:
        print("✅ 新方法解析正确")
    else:
        print("❌ 新方法解析错误")
        print(f"期望: {expected}")
        print(f"实际: {target_audience_new}")


if __name__ == "__main__":
    asyncio.run(test_target_audience_parsing())