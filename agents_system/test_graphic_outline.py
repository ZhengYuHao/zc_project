#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试图文大纲生成智能体
"""

import sys
import os
import asyncio

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.graphic_outline_agent import GraphicOutlineAgent, GraphicOutlineRequest


async def test_graphic_outline_agent():
    """测试图文大纲生成智能体"""
    print("Testing Graphic Outline Agent...")
    
    # 创建智能体实例
    agent = GraphicOutlineAgent()
    
    # 创建测试请求
    request = GraphicOutlineRequest(
        topic="人工智能的发展与应用",
        requirements="重点关注最近5年的发展",
        style="科技风格"
    )
    
    try:
        # 测试大纲生成
        print(f"Generating outline for topic: {request.topic}")
        response = await agent.process(request)
        
        print("Outline generation successful!")
        print(f"Spreadsheet Token: {response.spreadsheet_token}")
        print(f"Document ID: {response.document_id}")
        print("Outline Data:")
        print(f"  Topic: {response.outline_data.get('topic')}")
        print(f"  Total Words: {response.outline_data.get('total_words')}")
        print(f"  Estimated Time: {response.outline_data.get('estimated_time')}")
        
        sections = response.outline_data.get('sections', [])
        print(f"  Sections ({len(sections)}):")
        for i, section in enumerate(sections):
            print(f"    {i+1}. {section.get('title')}")
            print(f"       Content: {section.get('content')}")
            print(f"       Images: {section.get('images')}")
            print(f"       Word Count: {section.get('word_count')}")
        
        # 测试飞书电子表格创建
        print("\nTesting Feishu spreadsheet creation...")
        sheet_request = {
            "topic": "测试主题",
            "outline_data": response.outline_data
        }
        sheet_result = await agent.create_feishu_sheet(sheet_request)
        print(f"Sheet creation result: {sheet_result}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_graphic_outline_agent())