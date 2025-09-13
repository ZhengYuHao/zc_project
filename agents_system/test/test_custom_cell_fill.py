#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试自定义单元格填充功能
"""

import asyncio
import os
import sys
import json
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graphic_outline_agent import GraphicOutlineAgent

# 加载环境变量
load_dotenv()


async def test_custom_cell_fill():
    """测试自定义单元格填充功能"""
    print("测试自定义单元格填充功能")
    print("=" * 50)
    
    try:
        # 创建图文大纲智能体实例
        agent = GraphicOutlineAgent()
        
        # 准备测试数据
        test_request = {
            "topic": "人工智能发展现状",
            "outline_data": {
                "topic": "人工智能发展现状",
                "sections": [
                    {
                        "title": "引言",
                        "content": "人工智能作为当今科技发展的前沿领域，正深刻改变着我们的生活和工作方式。",
                        "images": ["ai_intro.jpg"],
                        "word_count": 150
                    },
                    {
                        "title": "技术发展",
                        "content": "从机器学习到深度学习，人工智能技术不断突破，应用领域日益广泛。",
                        "images": ["ai_tech.jpg", "ml_chart.png"],
                        "word_count": 300
                    },
                    {
                        "title": "未来展望",
                        "content": "随着算力提升和数据积累，人工智能将在更多领域发挥重要作用。",
                        "images": ["ai_future.jpg"],
                        "word_count": 200
                    }
                ],
                "total_words": 650,
                "estimated_time": "8分钟"
            },
            "custom_fill_data": {
                "cells": {
                    "A1": "人工智能发展现状分析报告",
                    "B1": "2025年度",
                    "A2": "报告作者：AI研究团队",
                    "A3": "报告日期：2025-09-07",
                    "D1": "机密等级：内部参考"
                }
            }
        }
        
        print("发送测试请求...")
        print(f"请求数据: {json.dumps(test_request, ensure_ascii=False, indent=2)}")
        
        # 调用创建电子表格的方法
        result = await agent.create_feishu_sheet(test_request)
        
        print("\n响应结果:")
        print("=" * 30)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("status") == "success":
            print(f"\n✅ 成功创建电子表格!")
            print(f"   电子表格Token: {result.get('spreadsheet_token')}")
            print(f"   工作表ID: {result.get('sheet_id')}")
        else:
            print(f"\n❌ 创建电子表格失败: {result.get('error')}")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


async def test_only_outline_data():
    """测试仅填充大纲数据，不使用自定义填充"""
    print("\n\n测试仅填充大纲数据")
    print("=" * 50)
    
    try:
        # 创建图文大纲智能体实例
        agent = GraphicOutlineAgent()
        
        # 准备测试数据（不包含自定义填充数据）
        test_request = {
            "topic": "机器学习基础概念",
            "outline_data": {
                "topic": "机器学习基础概念",
                "sections": [
                    {
                        "title": "什么是机器学习",
                        "content": "机器学习是人工智能的一个分支，使计算机能够从数据中学习并做出预测或决策。",
                        "images": ["ml_definition.jpg"],
                        "word_count": 180
                    },
                    {
                        "title": "主要算法类型",
                        "content": "包括监督学习、无监督学习和强化学习等主要类型。",
                        "images": ["ml_types.png"],
                        "word_count": 150
                    }
                ],
                "total_words": 330,
                "estimated_time": "5分钟"
            }
        }
        
        print("发送测试请求...")
        print(f"请求数据: {json.dumps(test_request, ensure_ascii=False, indent=2)}")
        
        # 调用创建电子表格的方法
        result = await agent.create_feishu_sheet(test_request)
        
        print("\n响应结果:")
        print("=" * 30)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("status") == "success":
            print(f"\n✅ 成功创建电子表格!")
            print(f"   电子表格Token: {result.get('spreadsheet_token')}")
            print(f"   工作表ID: {result.get('sheet_id')}")
        else:
            print(f"\n❌ 创建电子表格失败: {result.get('error')}")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


async def test_empty_custom_data():
    """测试空的自定义填充数据"""
    print("\n\n测试空的自定义填充数据")
    print("=" * 50)
    
    try:
        # 创建图文大纲智能体实例
        agent = GraphicOutlineAgent()
        
        # 准备测试数据（包含空的自定义填充数据）
        test_request = {
            "topic": "深度学习应用",
            "outline_data": {
                "topic": "深度学习应用",
                "sections": [
                    {
                        "title": "图像识别",
                        "content": "深度学习在图像识别领域取得了显著成果。",
                        "images": ["image_recognition.jpg"],
                        "word_count": 120
                    }
                ],
                "total_words": 120,
                "estimated_time": "2分钟"
            },
            "custom_fill_data": {}
        }
        
        print("发送测试请求...")
        print(f"请求数据: {json.dumps(test_request, ensure_ascii=False, indent=2)}")
        
        # 调用创建电子表格的方法
        result = await agent.create_feishu_sheet(test_request)
        
        print("\n响应结果:")
        print("=" * 30)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("status") == "success":
            print(f"\n✅ 成功创建电子表格!")
            print(f"   电子表格Token: {result.get('spreadsheet_token')}")
            print(f"   工作表ID: {result.get('sheet_id')}")
        else:
            print(f"\n❌ 创建电子表格失败: {result.get('error')}")
            
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    print("飞书电子表格自定义单元格填充功能测试")
    print("=" * 50)
    
    # 测试完整的自定义填充功能
    await test_custom_cell_fill()
    
    # # 测试仅填充大纲数据
    # await test_only_outline_data()
    
    # # 测试空的自定义填充数据
    # await test_empty_custom_data()
    
    print("\n\n所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())