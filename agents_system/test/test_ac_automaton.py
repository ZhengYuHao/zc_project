#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试AC自动机模块
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.ac_automaton import ACAutomaton

def main():
    """测试AC自动机功能"""
    print("开始测试AC自动机...")
    
    # 创建AC自动机实例
    ac = ACAutomaton()
    
    # 从目录构建AC自动机
    ac.build_from_directory('prohibited_words_output_v2')
    print("AC自动机构建完成")
    
    # 测试文本搜索
    test_text = "这是最佳的产品，具有世界级的品质"
    matches = ac.search(test_text)
    print(f"测试文本: {test_text}")
    print(f"匹配结果: {matches}")
    
    # 更复杂的测试
    test_text2 = "我们的产品是全球首发，销量第一，品质绝佳"
    matches2 = ac.search(test_text2)
    print(f"\n测试文本: {test_text2}")
    print(f"匹配结果: {matches2}")

if __name__ == "__main__":
    main()