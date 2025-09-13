#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
完整测试违禁词检测和标记功能
"""

import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from agents.text_reviewer import TextReviewerAgent
from utils.ac_automaton import ACAutomaton

def test_full_prohibited_words_functionality():
    """测试完整的违禁词检测和标记功能"""
    print("开始测试完整的违禁词检测和标记功能...")
    
    # 创建TextReviewerAgent实例
    agent = TextReviewerAgent()
    
    # 检查AC自动机是否正确初始化
    if not agent.ac_automaton:
        print("AC自动机未正确初始化")
        return
    
    print("AC自动机已正确初始化")
    
    # 测试违禁词检测
    test_cases = [
        "这个产品可以7天瘦10斤，非常有效",
        "我们的产品具有世界级的品质",
        "这是极致的体验，绝对让你满意",
        "使用这个产品可以躺着也能瘦",
        "百分百有效，无副作用的减肥产品",
        "没有任何违禁词的正常文本"
    ]
    
    print("\n=== 违禁词检测和标记测试 ===")
    for i, test_text in enumerate(test_cases):
        print(f"\n测试用例 {i+1}: {test_text}")
        marked_text = agent._mark_prohibited_words(test_text)
        print(f"标记后文本: {marked_text}")
        
        # 检查是否有变化
        if marked_text != test_text:
            print("  检测到违禁词并已标记")
        else:
            print("  未检测到违禁词")

if __name__ == "__main__":
    test_full_prohibited_words_functionality()