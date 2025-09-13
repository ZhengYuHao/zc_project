#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的单元格填充功能测试脚本
演示如何使用fill_cells_in_sheet方法按单元格引用填充数据
"""

import asyncio
import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graphic_outline_agent import GraphicOutlineAgent


async def test_simple_cell_fill():
    """测试简单的单元格填充功能"""
    print("测试简单的单元格填充功能")
    print("=" * 50)
    
    try:
        # 创建图文大纲智能体实例
        agent = GraphicOutlineAgent()
        
        # 首先创建一个电子表格用于测试（不填充大纲数据）
        create_request = {
            "topic": "测试单元格填充功能",
            "outline_data": {
                "topic": "测试单元格填充功能",
                "sections": [
                    {
                        "title": "引言",
                        "content": "这是一个测试内容",
                        "images": ["test.jpg"],
                        "word_count": 100
                    }
                ],
                "total_words": 100,
                "estimated_time": "1分钟"
            },
            "fill_outline_data": False  # 不填充大纲数据
        }
        
        print("1. 创建测试用的电子表格(不填充大纲数据)...")
        create_result = await agent.create_feishu_sheet(create_request)
        
        if create_result.get("status") != "success":
            print(f"创建电子表格失败: {create_result.get('error')}")
            return
            
        spreadsheet_token = create_result["spreadsheet_token"]
        sheet_id = create_result["sheet_id"]
        
        print(f"   成功创建电子表格: {spreadsheet_token}")
        print(f"   工作表ID: {sheet_id}")
        print("   注意: 由于fill_outline_data=False，不会自动填充大纲数据到A3等单元格")
        
        # 准备要填充的单元格数据
        cell_data = {
            "B1": "这是A1单元格",
            "B2": "这是B1单元格",
            "B3": "这是A2单元格",
            "B4": "这是C3单元格"
        }
        
        print("\n2. 准备填充数据:")
        for cell_ref, value in cell_data.items():
            print(f"   {cell_ref}: {value}")
        
        # 调用简单的单元格填充接口
        print("\n3. 执行单元格填充...")
        fill_result = await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, cell_data)
        
        if fill_result.get("status") == "success":
            print("   ✅ 单元格填充成功!")
        else:
            print(f"   ❌ 单元格填充失败: {fill_result.get('error')}")
            
        # 额外测试：修改A3单元格(明确要求修改)
        print("\n4. 测试修改A3单元格(明确要求修改)...")
        a3_cell_data = {
            "A3": "修改后的内容"
        }
        print("   准备将A3单元格修改为: '修改后的内容'")
        a3_fill_result = await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, a3_cell_data)
        
        if a3_fill_result.get("status") == "success":
            print("   ✅ A3单元格修改成功!")
        else:
            print(f"   ❌ A3单元格修改失败: {a3_fill_result.get('error')}")
            
        print("\n测试完成!")
        print("\n说明:")
        print("1. 通过设置fill_outline_data=False，可以避免自动填充大纲数据")
        print("2. 只有明确指定要修改的单元格才会被修改")
        print("3. 未指定的单元格(如A3)保持原始模板状态，不会被自动修改")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    print("飞书电子表格简单单元格填充功能测试")
    print("=" * 50)
    
    await test_simple_cell_fill()


if __name__ == "__main__":
    asyncio.run(main())