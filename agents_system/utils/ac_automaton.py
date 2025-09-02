#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AC自动机实现，用于高效检索文本中的违禁词
"""

from typing import List, Dict, Set, Tuple
import os
import sys
import re
from collections import deque

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ACAutomatonNode:
    """AC自动机节点"""
    
    def __init__(self):
        self.children = {}  # 子节点
        self.fail = None    # 失败指针
        self.is_end = False # 是否为单词结尾
        self.word = ""      # 完整单词


class ACAutomaton:
    """AC自动机实现"""
    
    def __init__(self):
        self.root = ACAutomatonNode()
    
    def add_word(self, word: str):
        """
        添加单词到AC自动机
        
        Args:
            word: 要添加的单词
        """
        # 过滤掉明显不是违禁词的内容
        if any(keyword in word for keyword in 
               ['说明', '原理', '平替词', '替代词', '禁用原理', 'NaN', 'Unnamed', '违禁词', '改写方案']):
            return
            
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = ACAutomatonNode()
            node = node.children[char]
        node.is_end = True
        node.word = word
    
    def build_fail_pointers(self):
        """构建失败指针"""
        queue = deque()
        
        # 初始化根节点的子节点的失败指针
        for char, child in self.root.children.items():
            child.fail = self.root
            queue.append(child)
        
        # BFS构建失败指针
        while queue:
            current = queue.popleft()
            
            for char, child in current.children.items():
                queue.append(child)
                fail_node = current.fail
                
                while fail_node and char not in fail_node.children:
                    fail_node = fail_node.fail
                
                if fail_node:
                    child.fail = fail_node.children.get(char, self.root)
                else:
                    child.fail = self.root
                
                # 如果失败节点是单词结尾，则当前节点也是单词结尾
                if child.fail.is_end:
                    child.is_end = True
                    if not child.word:
                        child.word = child.fail.word
    
    def search(self, text: str) -> List[Tuple[str, int, int]]:
        """
        在文本中搜索所有匹配的单词
        
        Args:
            text: 要搜索的文本
            
        Returns:
            匹配结果列表，每个元素为(单词, 起始位置, 结束位置)
        """
        result = []
        node = self.root
        
        for i, char in enumerate(text):
            # 如果当前字符不在子节点中，则沿着失败指针移动
            while node != self.root and char not in node.children:
                node = node.fail
            
            # 如果当前字符在子节点中，则移动到对应子节点
            if char in node.children:
                node = node.children[char]
            
            # 检查当前节点及其失败指针链上的所有单词
            temp = node
            while temp != self.root:
                if temp.is_end:
                    start_pos = i - len(temp.word) + 1
                    result.append((temp.word, start_pos, i + 1))
                temp = temp.fail
        
        # 按起始位置排序
        result.sort(key=lambda x: x[1])
        
        # 去除重叠匹配（保留最长的匹配）
        if not result:
            return result
            
        filtered_result = [result[0]]
        for i in range(1, len(result)):
            current_word, current_start, current_end = result[i]
            prev_word, prev_start, prev_end = filtered_result[-1]
            
            # 如果当前匹配与前一个匹配重叠
            if current_start < prev_end:
                # 选择较长的匹配
                if (current_end - current_start) > (prev_end - prev_start):
                    filtered_result[-1] = (current_word, current_start, current_end)
            else:
                # 不重叠，直接添加
                filtered_result.append((current_word, current_start, current_end))
        
        return filtered_result
    
    def build_from_file(self, file_path: str):
        """
        从文件构建AC自动机
        
        Args:
            file_path: 包含违禁词的文件路径
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件 {file_path} 不存在")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
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
                            self.add_word(word)
        
        self.build_fail_pointers()
    
    def build_from_directory(self, directory_path: str):
        """
        从目录中的所有文本文件构建AC自动机
        
        Args:
            directory_path: 包含违禁词文件的目录路径
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录 {directory_path} 不存在")
        
        for filename in os.listdir(directory_path):
            if filename.endswith('.txt'):
                file_path = os.path.join(directory_path, filename)
                self.build_from_file(file_path)