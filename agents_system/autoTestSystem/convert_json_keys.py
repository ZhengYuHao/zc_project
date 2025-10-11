#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将JSON数据中的列字母键替换为对应的英文变量名
"""

import json
import os


def convert_column_keys_to_variable_names(data):
    """
    将JSON数据中的列字母键替换为对应的英文变量名
    
    Args:
        data: 包含列字母键的JSON数据
        
    Returns:
        转换后的JSON数据，键为英文变量名
    """
    # 定义列字母到英文变量名的映射关系
    column_mapping = {
        # 图文大纲
        # "row": 1,
        # "D": "product_name",
        # "E": "ProductHighlights",
        # "F": "direction",
        # "G": "blogger_link",
        # "H": "requirements",
        # "I": "notice",
        # "J": "outline_direction",
        # "K": "picture_number"
        #视频大纲
        # "row": 1,
        # "D": "product_name",
        # "E": "ProductHighlights",
        # "F": "direction",
        # "G": "xhs_link",
        # "H": "outline_advice",
        # "I": "requirements",
        # "J": "notice",
        # "K": "name"
        #视频脚本
        "row": 1,
        "D": "brand_name",
        "E": "ProductHighlights",
        "F": "direction",
        "G": "xhs_link",
        "H": "outline_direction",
        "I": "requirements",
        "J": "notice",
        "K": "video_outline_link"
    }
    
    # 递归处理字典
    if isinstance(data, dict):
        converted_data = {}
        for key, value in data.items():
            # 如果是行号键，保持不变
            if key == "row":
                converted_key = key
            # 如果是列字母键，替换为英文变量名
            if key in column_mapping:
                converted_key = column_mapping[key]
            # 处理带数字后缀的键（如D1, E1等）
            elif len(key) > 1 and key[:-1] in column_mapping and key[-1].isdigit():  # 检查去掉最后一个字符后是否在映射中，且最后一个字符是数字
                converted_key = column_mapping[key[:-1]]
            else:
                converted_key = key
            
            # 递归处理值
            converted_value = convert_column_keys_to_variable_names(value)
            converted_data[converted_key] = converted_value
        return converted_data
    
    # 递归处理列表
    elif isinstance(data, list):
        converted_data = []
        for item in data:
            converted_data.append(convert_column_keys_to_variable_names(item))
        return converted_data
    
    # 其他类型直接返回
    else:
        return data


def process_json_file(input_file_path, output_file_path=None):
    """
    处理JSON文件，将列字母键替换为英文变量名
    
    Args:
        input_file_path: 输入JSON文件路径
        output_file_path: 输出JSON文件路径（可选，默认为输入文件名加'_converted'后缀）
    """
    # 读取JSON文件
    with open(input_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 转换键名
    converted_data = convert_column_keys_to_variable_names(data)
    
    # 确定输出文件路径
    if output_file_path is None:
        file_name, file_ext = os.path.splitext(input_file_path)
        output_file_path = f"{file_name}_converted{file_ext}"
    
    # 写入转换后的数据到新文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    
    print(f"转换完成，结果已保存到: {output_file_path}")
    return output_file_path


def main():
    """
    主函数 - 转换JSON数据中的键
    """
    # 输入和输出文件名
    input_filename = "spreadsheet_post_data_视频脚本创作.json"
    output_filename = "spreadsheet_post_data_视频脚本创作_converted.json"
    
    # 检查输入文件是否存在
    if not os.path.exists(input_filename):
        print(f"错误: 文件 {input_filename} 不存在")
        return
    
    try:
        # 加载JSON数据
        print(f"正在加载 {input_filename}...")
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"成功加载数据")
        
        # 转换键名
        print("正在转换键名...")
        converted_data = convert_column_keys_to_variable_names(data)
        
        # 保存转换后的数据
        print(f"正在保存到 {output_filename}...")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(converted_data, f, ensure_ascii=False, indent=2)
        print("转换完成!")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()