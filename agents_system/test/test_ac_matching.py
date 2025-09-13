#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试AC自动机的匹配逻辑
"""

import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils.ac_automaton import ACAutomaton

def test_ac_matching():
    """测试AC自动机的匹配逻辑"""
    print("开始测试AC自动机的匹配逻辑...")
    
    # 创建AC自动机实例
    ac = ACAutomaton()
    
    # 添加测试词
    test_words = ["7天瘦10斤", "瘦10斤", "有效", "世界级", "极致", "绝对"]
    for word in test_words:
        ac.add_word(word)
    ac.build_fail_pointers()
    
    # 测试匹配
    test_cases = [
        "这个产品可以7天瘦10斤，非常有效",
        "我们的产品具有世界级的品质",
        "这是极致的体验，绝对让你满意"
    ]
    
    for i, test_text in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test_text}")
        matches = ac.search(test_text)
        print(f"匹配结果: {matches}")

if __name__ == "__main__":
    test_ac_matching()