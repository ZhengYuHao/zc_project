#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试文本审核模块的违禁词标记功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.text_reviewer import TextReviewerAgent

def main():
    """测试文本审核模块功能"""
    print("开始测试文本审核模块...")
    
    # 创建文本审核模块实例
    reviewer = TextReviewerAgent()
    print("文本审核模块初始化完成")
    
    # 测试违禁词标记功能
    test_text = "这是最佳的产品，具有世界级的品质"
    marked_text = reviewer._mark_prohibited_words(test_text)
    print(f"原始文本: {test_text}")
    print(f"标记后文本: {marked_text}")
    
    # 更复杂的测试
    test_text2 = "我们的产品是全球首发，销量第一，品质绝佳"
    marked_text2 = reviewer._mark_prohibited_words(test_text2)
    print(f"\n原始文本: {test_text2}")
    print(f"标记后文本: {marked_text2}")

if __name__ == "__main__":
    main()