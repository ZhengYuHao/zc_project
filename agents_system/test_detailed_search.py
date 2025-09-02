#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
详细测试违禁词检索功能
"""

import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils.ac_automaton import ACAutomaton

def test_detailed_search():
    """详细测试违禁词搜索功能"""
    print("开始详细测试违禁词搜索功能...")
    
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
    
    # 测试特定违禁词
    print("\n=== 特定违禁词测试 ===")
    specific_words = [
        "7天瘦10斤",
        "月增肌5kg",
        "马甲线速成",
        "一招告别小肚子",
        "躺着也能瘦",
        "无痛减肥",
        "永不反弹",
        "百分百有效",
        "极致",
        "极品",
        "极佳",
        "终极",
        "国际级",
        "世界级",
        "全球级"
    ]
    
    for word in specific_words:
        matches = ac.search(word)
        print(f"词 '{word}' 匹配结果: {matches}")
        
    # 测试包含违禁词的句子
    print("\n=== 包含违禁词的句子测试 ===")
    sentences = [
        "这个产品可以7天瘦10斤，非常有效",
        "我们的产品具有世界级的品质",
        "这是极致的体验，绝对让你满意",
        "使用这个产品可以躺着也能瘦",
        "百分百有效，无副作用的减肥产品"
    ]
    
    for sentence in sentences:
        matches = ac.search(sentence)
        print(f"句子 '{sentence}' 匹配结果: {matches}")

if __name__ == "__main__":
    test_detailed_search()