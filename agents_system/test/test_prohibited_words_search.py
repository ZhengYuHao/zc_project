#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试违禁词检索功能
"""

import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils.ac_automaton import ACAutomaton

def test_prohibited_words_search():
    """测试违禁词搜索功能"""
    print("开始测试违禁词搜索功能...")
    
    # 创建AC自动机实例
    ac = ACAutomaton()
    
    # 从目录构建AC自动机
    try:
        prohibited_words_dir = os.path.join(current_dir, 'prohibited_words_output_v2')
        print(f"违禁词目录路径: {prohibited_words_dir}")
        ac.build_from_directory(prohibited_words_dir)
        print("AC自动机构建完成")
    except Exception as e:
        print(f"构建AC自动机时出错: {e}")
        return
    
    # 测试文本搜索
    test_cases = [
        "这是最佳的产品，具有世界级的品质",
        "我们的产品是全球首发，销量第一，品质绝佳",
        "这款减肥产品100%有效，无副作用",
        "使用本产品可以7天瘦10斤",
        "这是全网最便宜的价格，错过就没机会了",
        "国家级产品，填补国内空白"
    ]
    
    for i, test_text in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test_text}")
        matches = ac.search(test_text)
        print(f"匹配结果: {matches}")
        
    # 测试单个违禁词
    print("\n=== 单个违禁词测试 ===")
    single_words = ["最佳", "世界级", "销量第一", "100%有效", "无副作用", "7天瘦10斤"]
    for word in single_words:
        matches = ac.search(word)
        print(f"词 '{word}' 匹配结果: {matches}")

if __name__ == "__main__":
    test_prohibited_words_search()