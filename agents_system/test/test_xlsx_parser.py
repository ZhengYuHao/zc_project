#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
XLSX解析器测试模块
用于测试xlsx_parser模块的功能
"""

import os
import sys
from pprint import pprint

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.xlsx_parser import XLSXParser


def test_xlsx_parser():
    """
    测试XLSX解析器功能
    """
    # 创建XLSX解析器实例
    parser = XLSXParser()
    
    # XLSX文件路径
    file_path = os.path.join(os.path.dirname(__file__), "2025.xlsx")
    
    print(f"开始测试XLSX解析器...")
    print(f"测试文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return
    
    try:
        # 解析所有工作表
        result = parser.parse_all_sheets(file_path)
        
        print(f"\n解析结果:")
        print(f"工作表数量: {len(result)}")
        
        # 打印每个工作表的解析结果
        for sheet_name, words in result.items():
            print(f"\n工作表 '{sheet_name}':")
            print(f"  违禁词数量: {len(words)}")
            if words:
                print(f"  前3个违禁词:")
                for i, word in enumerate(words[:3]):
                    print(f"    {i+1}. 敏感词: {word['sensitive_word']}, "
                          f"替换词: {word['replacement']}, "
                          f"级别: {word['level']}, "
                          f"备注: {word['comment']}")
            else:
                print("  无违禁词数据")
                
    except Exception as e:
        print(f"解析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


def test_parse_specific_sheets():
    """
    测试解析指定工作表的功能
    """
    # 创建XLSX解析器实例
    parser = XLSXParser()
    
    # XLSX文件路径
    file_path = os.path.join(os.path.dirname(__file__), "2025.xlsx")
    
    print(f"\n开始测试解析指定工作表功能...")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return
    
    try:
        # 获取所有工作表名称
        import pandas as pd
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        if sheet_names:
            # 选择第一个工作表进行测试
            target_sheet = sheet_names[0]
            print(f"解析工作表: {target_sheet}")
            
            # 解析指定工作表
            result = parser.parse_specific_sheets(file_path, [target_sheet])
            
            print(f"解析结果:")
            for sheet_name, words in result.items():
                print(f"工作表 '{sheet_name}':")
                print(f"  违禁词数量: {len(words)}")
                if words:
                    print(f"  前3个违禁词:")
                    for i, word in enumerate(words[:3]):
                        print(f"    {i+1}. 敏感词: {word['sensitive_word']}, "
                              f"替换词: {word['replacement']}, "
                              f"级别: {word['level']}, "
                              f"备注: {word['comment']}")
        else:
            print("Excel文件中没有工作表")
                
    except Exception as e:
        print(f"解析过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行测试
    test_xlsx_parser()
    test_parse_specific_sheets()