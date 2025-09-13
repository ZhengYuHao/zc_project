#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：在图文大纲模块中使用直接调用接口的方式
"""

import asyncio
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graphic_outline_agent import GraphicOutlineAgent


async def test_direct_api_call():
    """测试直接调用接口的方式"""
    print("测试在图文大纲模块中使用直接调用接口的方式")
    print("=" * 50)
    
    try:
        # 创建图文大纲智能体实例
        agent = GraphicOutlineAgent()
        
        # 创建电子表格（不自动填充大纲数据）
        create_request = {
            "topic": "测试直接调用接口",
            "fill_outline_data": False  # 关键：不自动填充大纲数据
        }
        
        print("1. 创建测试用的电子表格...")
        create_result = await agent.create_feishu_sheet(create_request)
        
        if create_result.get("status") != "success":
            print(f"创建电子表格失败: {create_result.get('error')}")
            return
            
        spreadsheet_token = create_result["spreadsheet_token"]
        sheet_id = create_result["sheet_id"]
        
        print(f"   成功创建电子表格: {spreadsheet_token}")
        print(f"   工作表ID: {sheet_id}")
        print("   注意: 由于fill_outline_data=False，不会自动填充大纲数据")
        
        # # 准备要填充的单元格数据（标题和作者信息）
        # header_data = {
        #     "A1": "人工智能发展现状分析报告",
        #     "B1": "2025年度",
        #     "A2": "报告作者：AI研究团队"
        # }
        
        # print("\n2. 准备填充标题和作者信息:")
        # for cell_ref, value in header_data.items():
        #     print(f"   {cell_ref}: {value}")
        
        # # 直接调用接口填充标题和作者信息
        # print("\n3. 执行标题和作者信息填充...")
        # header_fill_result = await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, header_data)
        
        # if header_fill_result.get("status") == "success":
        #     print("   ✅ 标题和作者信息填充成功!")
        # else:
        #     print(f"   ❌ 标题和作者信息填充失败: {header_fill_result.get('error')}")
        
        # 准备章节数据
        section_data = {
            "B1": "1",
            "B2": "引言",
            "B3": "人工智能作为当今科技发展的前沿领域，正深刻改变着我们的生活和工作方式。",
        }
        
        print("\n4. 准备填充章节数据:")
        for cell_ref, value in section_data.items():
            print(f"   {cell_ref}: {value}")
        
        # 直接调用接口填充章节数据
        print("\n5. 执行章节数据填充...")
        section_fill_result = await agent.fill_cells_in_sheet(spreadsheet_token, sheet_id, section_data)
        
        if section_fill_result.get("status") == "success":
            print("   ✅ 章节数据填充成功!")
        else:
            print(f"   ❌ 章节数据填充失败: {section_fill_result.get('error')}")
            
        # 验证部分单元格未被修改
        print("\n6. 验证未指定的单元格保持原状...")
        print("   例如A3单元格应该保持空白状态（未被自动填充为大纲数据）")
        
        print("\n测试完成!")
        print("\n说明:")
        print("1. 通过设置fill_outline_data=False，避免了自动填充大纲数据")
        print("2. 使用fill_cells_in_sheet方法直接按单元格引用填充数据")
        print("3. 只有明确指定的单元格被修改，其他单元格保持原状")
        print("4. 可以分多次调用接口填充不同部分的数据")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    print("飞书电子表格直接调用接口测试")
    print("=" * 50)
    
    await test_direct_api_call()


if __name__ == "__main__":
    asyncio.run(main())