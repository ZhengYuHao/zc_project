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
        "D": "product_name",
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
            elif key in column_mapping:
                converted_key = column_mapping[key]
            # 处理带数字后缀的键（如D1, E1等）
            elif key[:-1] in column_mapping:  # 检查去掉最后一个字符后是否在映射中
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
    主函数 - 示例用法
    """
    # 如果存在实际的JSON文件，处理它
    input_file = "spreadsheet_post_data_视频脚本创作.json"
    # 查找文件的可能路径
    possible_paths = [
        input_file,  # 当前目录
        os.path.join("..", input_file),  # 上级目录
        os.path.join("..", "..", input_file),  # 上上级目录
        os.path.join("e:\\pyProject\\zc_project", input_file)  # 项目根目录
    ]
    
    file_found = False
    for path in possible_paths:
        if os.path.exists(path):
            try:
                print(f"找到文件: {path}")
                process_json_file(path)
                file_found = True
                break
            except Exception as e:
                print(f"处理文件 {path} 时出错: {e}")
    
    if not file_found:
        print(f"文件 {input_file} 不存在，使用示例数据演示:")
        # 示例数据
        sample_data = [
            {
                "row": 2,
                "D": "示例产品",
                "E": "产品亮点内容",
                "F": "创作方向",
                "G": "https://example.com/blogger",
                "H": "内容要求",
                "I": "备注信息",
                "J": "大纲方向",
                "K": "5"
            },
            {
                "row": 3,
                "D": "另一个产品",
                "E": "另一个产品亮点",
                "F": "另一个创作方向",
                "G": "https://example.com/another_blogger",
                "H": "另一个内容要求",
                "I": "另一个备注",
                "J": "另一个大纲方向",
                "K": "3"
            }
        ]
        
        # 转换示例数据
        converted_sample = convert_column_keys_to_variable_names(sample_data)
        print("示例数据转换结果:")
        print(json.dumps(converted_sample, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()