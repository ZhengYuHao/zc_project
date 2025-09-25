#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试提示词加载功能
"""

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.graphic_outline_agent import GraphicOutlineAgent


def test_prompt_loading():
    """测试提示词加载功能"""
    print("Testing prompt loading...")
    
    # 创建GraphicOutlineAgent实例
    agent = GraphicOutlineAgent()
    
    # 检查提示词是否成功加载
    if hasattr(agent, 'prompts') and agent.prompts:
        print("✓ Prompts loaded successfully")
        
        # 检查graphic_outline部分是否存在
        if "graphic_outline" in agent.prompts:
            print("✓ Graphic outline prompts found")
            
            # 检查各个子部分
            sections = ["planting_content", "planting_content_cp", "planting_captions", "planting_captions_cp"]
            for section in sections:
                if section in agent.prompts["graphic_outline"]:
                    print(f"✓ {section} section found")
                else:
                    print(f"✗ {section} section missing")
        else:
            print("✗ Graphic outline prompts not found")
    else:
        print("✗ Failed to load prompts")


def test_prompt_structure():
    """测试提示词结构"""
    print("\nTesting prompt structure...")
    
    # 创建GraphicOutlineAgent实例
    agent = GraphicOutlineAgent()
    
    # 检查提示词结构
    prompts = agent.prompts.get("graphic_outline", {})
    
    # 检查planting_content结构
    planting_content = prompts.get("planting_content", {})
    required_keys = ["role", "input_description", "skills", "output_format", "restrictions"]
    for key in required_keys:
        if key in planting_content:
            print(f"✓ planting_content.{key} found")
        else:
            print(f"✗ planting_content.{key} missing")
    
    # 检查skills子结构
    skills = planting_content.get("skills", {})
    skill_keys = ["skill_1", "skill_2", "skill_3", "skill_4", "skill_5"]
    for key in skill_keys:
        if key in skills:
            print(f"✓ planting_content.skills.{key} found")
        else:
            print(f"✗ planting_content.skills.{key} missing")


if __name__ == "__main__":
    test_prompt_loading()
    test_prompt_structure()