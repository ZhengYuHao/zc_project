#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试AC自动机，检查违禁词加载情况
"""

import sys
import os
import re
from collections import deque

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils.ac_automaton import ACAutomaton

class ACAutomatonNode:
    """AC自动机节点"""
    
    def __init__(self):
        self.children = {}  # 子节点
        self.fail = None    # 失败指针
        self.is_end = False # 是否为单词结尾
        self.word = ""      # 完整单词

class DebugACAutomaton(ACAutomaton):
    """带调试功能的AC自动机"""
    
    def __init__(self):
        self.root = ACAutomatonNode()
        self.added_words = []
    
    def add_word(self, word: str):
        """
        添加单词到AC自动机（带调试信息）
        """
        # 过滤掉明显不是违禁词的内容
        if any(keyword in word for keyword in 
               ['说明', '原理', '平替词', '替代词', '禁用原理', 'NaN', 'Unnamed', '违禁词', '改写方案']):
            print(f"过滤掉词: {word}")
            return
            
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = ACAutomatonNode()
            node = node.children[char]
        node.is_end = True
        node.word = word
        self.added_words.append(word)
        # print(f"添加词: {word}")

def debug_build_from_file(ac, file_path: str):
    """
    从文件构建AC自动机（带调试信息）
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件 {file_path} 不存在")
    
    print(f"处理文件: {file_path}")
    added_words = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                # 处理包含多个违禁词的行（用双引号分隔）
                # 先去掉行首行尾的引号（如果有的话）
                if line.startswith('"') and line.endswith('"'):
                    line = line[1:-1]
                            
                # 按双引号分割，提取违禁词
                words = []
                parts = line.split('""')
                for part in parts:
                    part = part.strip('"')
                    if part:
                        # 处理用顿号、逗号等分隔的多个词
                        sub_words = re.split(r'[、,，;；\s]+', part)
                        words.extend(sub_words)
                            
                for word in words:
                    word = word.strip()
                    if word and not any(keyword in word for keyword in 
                                      ['说明', '原理', '平替词', '替代词', '禁用原理', 'NaN', 'Unnamed', '违禁词', '改写方案']):
                        # 特殊处理包含"等"字的词组
                        if word.endswith("等") or word.endswith("等。"):
                            word = word[:-1]  # 去掉末尾的"等"字
                        if word:  # 确保词不为空
                            ac.add_word(word)
                            added_words.append((line_num, word))
    
    # ac.build_fail_pointers()
    print(f"从文件 {os.path.basename(file_path)} 添加了 {len(added_words)} 个词")
    return added_words

def debug_build_from_directory(directory_path: str):
    """
    从目录中的所有文本文件构建AC自动机（带调试信息）
    """
    if not os.path.exists(directory_path):
        raise FileNotFoundError(f"目录 {directory_path} 不存在")
    
    ac = DebugACAutomaton()
    all_added_words = []
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.txt'):
            file_path = os.path.join(directory_path, filename)
            added_words = debug_build_from_file(ac, file_path)
            all_added_words.extend(added_words)
    
    print(f"\n总共添加了 {len(all_added_words)} 个词")
    return ac, all_added_words

def main():
    """主函数"""
    print("开始调试AC自动机...")
    
    # 构建AC自动机
    prohibited_words_dir = os.path.join(current_dir, 'prohibited_words_output_v2')
    ac, all_words = debug_build_from_directory(prohibited_words_dir)
    
    # 检查特定词是否被添加
    test_words = ["7天瘦10斤", "马甲线速成", "躺着也能瘦", "世界级", "极致"]
    print(f"\n=== 检查特定词是否被添加 ===")
    for word in test_words:
        found = any(word == added_word for _, added_word in all_words)
        print(f"词 '{word}' 是否被添加: {found}")
        if not found:
            # 检查是否有相似词
            similar_words = [added_word for _, added_word in all_words if word in added_word or added_word in word]
            if similar_words:
                print(f"  相似词: {similar_words}")
    
    # 测试搜索
    print(f"\n=== 测试搜索 ===")
    test_text = "这个产品可以7天瘦10斤，具有世界级的品质，是极致的体验"
    print(f"测试文本: {test_text}")
    # matches = ac.search(test_text)
    # print(f"匹配结果: {matches}")

if __name__ == "__main__":
    main()