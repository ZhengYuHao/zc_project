#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 graphic_outline/process-request API 接口
发送 spreadsheet_post_data_图文大纲创作_converted.json 文件中的数据项进行测试
"""

import json
import os
import requests
import time


def load_test_data(json_file_path):
    """
    加载测试数据
    
    Args:
        json_file_path: JSON文件路径
        
    Returns:
        list: 测试数据列表
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def send_post_request(url, data_item):
    """
    发送POST请求到指定URL
    
    Args:
        url: 目标URL
        data_item: 要发送的数据项
        
    Returns:
        response: 请求响应对象
    """
    try:
        # 发送POST请求
        response = requests.post(
            url,
            json=data_item,
            headers={'Content-Type': 'application/json'}
        )
        return response
    except Exception as e:
        print(f"发送请求时出错: {e}")
        return None


def test_all_data_items(json_file_path, api_url):
    """
    测试所有数据项
    
    Args:
        json_file_path: JSON文件路径
        api_url: API地址
    """
    # 加载测试数据
    test_data = load_test_data(json_file_path)
    
    print(f"加载了 {len(test_data)} 条测试数据")
    
    # 遍历所有数据项并发送请求
    for i, data_item in enumerate(test_data):
        print(f"\n正在测试第 {i+1} 条数据:")
        print(f"数据内容: {json.dumps(data_item, ensure_ascii=False, indent=2)}")
        
        # 发送POST请求
        response = send_post_request(api_url, data_item)
        
        if response:
            print(f"响应状态码: {response.status_code}")
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"响应内容: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
                except:
                    print(f"响应内容: {response.text}")
            else:
                print(f"请求失败: {response.text}")
        else:
            print("请求发送失败")
        
        # 添加延时避免请求过于频繁
        if i < len(test_data) - 1:  # 最后一条数据不需要延时
            time.sleep(1)


def main():
    """
    主函数
    """
    # 配置参数
    # #视频大纲
    # api_url = "http://124.221.155.224:8857/api/video-outline-create"
    # #视频脚本
    # api_url = "http://124.221.155.224:8844/api/video-demo-create"
    # #图文大纲
    api_url = "http://124.221.155.224:8847/graphic_outline/process-request"
    
    # 查找JSON文件
    json_file_name = "spreadsheet_post_data_图文大纲创作_converted.json"
    possible_paths = [
        json_file_name,
        os.path.join("..", json_file_name),
        os.path.join("..", "..", json_file_name),
        os.path.join("e:\\pyProject\\zc_project", json_file_name)
    ]
    
    json_file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            json_file_path = path
            print(f"找到测试数据文件: {path}")
            break
    
    if not json_file_path:
        print(f"未找到测试数据文件: {json_file_name}")
        return
    
    # 测试所有数据项
    test_all_data_items(json_file_path, api_url)


if __name__ == "__main__":
    main()