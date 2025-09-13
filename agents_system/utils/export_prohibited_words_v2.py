#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将Excel文件中的违禁词按工作表导出到文本文件，格式适合后续作为set和文本进行匹配
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.xlsx_parser import XLSXParser




def main():
    """
    主函数：解析Excel文件并将违禁词导出到文本文件
    """
    # 创建XLSX解析器实例
    parser = XLSXParser()
    
    # Excel文件路径
    file_path = os.path.join(os.path.dirname(__file__), "2025.xlsx")
    
    print(f"开始解析Excel文件: {file_path}")
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return
    
    try:
        # 解析所有工作表
        parsed_data = parser.parse_all_sheets(file_path)
        
        print(f"解析完成，共处理 {len(parsed_data)} 个工作表")
        
        # 导出到按工作表分类的文本文件
        output_dir = os.path.join(os.path.dirname(__file__), "prohibited_words_output_v2")
        parser.export_to_text_files(parsed_data, output_dir)
        
        print(f"违禁词已按工作表分类导出到目录: {output_dir}")
        
        # 导出到单个文件（所有违禁词）
        all_words_file = os.path.join(os.path.dirname(__file__), "all_prohibited_words.txt")
        parser.export_all_to_single_file(parsed_data, all_words_file)
        
        print(f"所有唯一违禁词已导出到文件: {all_words_file}")
        
        # 显示统计信息
        total_words = sum(len(words) for words in parsed_data.values())
        unique_words = set()
        for sheet_name, words in parsed_data.items():
            for word_info in words:
                unique_words.add(word_info['sensitive_word'])
        
        print(f"\n统计信息:")
        print(f"工作表数量: {len(parsed_data)}")
        print(f"违禁词总数: {total_words}")
        print(f"唯一违禁词数量: {len(unique_words)}")
        
        print("\n各工作表违禁词数量:")
        for sheet_name, words in parsed_data.items():
            print(f"  {sheet_name}: {len(words)} 个违禁词")
            
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()