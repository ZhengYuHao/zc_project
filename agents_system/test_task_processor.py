#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务处理器单元测试
"""

import asyncio
import sys
import os
import re
from typing import List, Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 修改为项目根目录的上一级目录
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 使用相对导入或绝对导入
try:
    from agents.task_processor import (
        task_processor, 
        extract_target_audience,
        extract_required_content,
        extract_blogger_style,
        extract_product_category,
        extract_selling_points,
        extract_product_endorsement,
        extract_topic
    )
    from agents.graphic_outline_agent import GraphicOutlineAgent
    from utils.logger import get_logger
except ImportError as e:
    print(f"ImportError: {e}")
    raise

# 获取logger实例
logger = get_logger("test.task_processor")


def parse_planting_content(content: str) -> List[Dict[str, str]]:
    """
    解析图文规划内容
    
    Args:
        content: 大模型返回的图文规划文本
        
    Returns:
        解析后的图文规划数据列表
    """
    # 使用正则表达式匹配图文规划内容
    pattern = r'图片类型：(.*?)\n图文规划：\n(.*?)\n图片的文字内容：(.*?)\n备注：(.*?)(?=\n\n图片类型：|$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    result = []
    for match in matches:
        image_info = {
            "image_type": match[0].strip(),
            "planning": match[1].strip(),
            "caption": match[2].strip(),
            "remark": match[3].strip()
        }
        result.append(image_info)
    
    return result


def parse_planting_captions(content: str) -> Dict[str, Any]:
    """
    解析配文内容
    
    Args:
        content: 大模型返回的配文文本
        
    Returns:
        解析后的配文数据
    """
    captions_data = {
        "titles": [],
        "body": "",
        "hashtags": []
    }
    
    # 解析标题部分
    title_match = re.search(r'- \*\*标题\*\*：((?:\n\s*- [^\n]+)+)', content)
    if title_match:
        titles_text = title_match.group(1)
        titles = re.findall(r'- ([^\n]+)', titles_text)
        captions_data["titles"] = [title.strip() for title in titles]
    
    # 解析正文部分
    body_match = re.search(r'- \*\*正文\*\*：(.*?)(?=\n- \*\*标签|\Z)', content, re.DOTALL)
    if body_match:
        captions_data["body"] = body_match.group(1).strip()
    
    # 解析标签部分
    hashtag_match = re.search(r'- \*\*标签\*\*：(.*?)(?=\Z)', content, re.DOTALL)
    if hashtag_match:
        hashtags_text = hashtag_match.group(1).strip()
        hashtags = re.findall(r'#\S+', hashtags_text)
        captions_data["hashtags"] = hashtags
    
    return captions_data


async def test_task_processor():
    
    try:
        # 创建GraphicOutlineAgent实例以访问_generate_planting_content方法
        agent = GraphicOutlineAgent()
        
        # 准备测试数据
        processed_data = {
            "topic": "夏季护肤指南",
            "product_name": "水润防晒霜",
            "product_highlights": "防晒、保湿、温和配方",
            "note_style": "种草",
            "requirements": "需要包含使用前后对比，适合敏感肌",
            "direction": "重点介绍防晒效果和使用感受",
            "blogger_link": "https://xiaohongshu.com/user/12345",
            "sections": {
                "target_audience": "适合户外活动较多的年轻女性",
                "required_content": "需要展示防晒效果和使用感受",
                "blogger_style": "小红书风格，轻松活泼",
                "product_category": "护肤品",
                "selling_points": "防晒指数高，温和不刺激，保湿效果好",
                "product_endorsement": "专业护肤品牌",
                "main_topic": "夏季防晒的重要性"
            },
            "total_words": 1000,
            "estimated_time": "5分钟"
        }
        
        # 测试种草图文规划生成
        planting_content = await agent._generate_planting_content(processed_data)
        logger.info("Generated planting content:")
        logger.info(planting_content[:-1])
        
        # 解析图文规划内容
        planting_data = parse_planting_content(planting_content)
        logger.info("Parsed planting data:")
        for i, data in enumerate(planting_data):
            logger.info(f"  Image {i+1}:")
            logger.info(f"    Type: {data['image_type']}")
            logger.info(f"    Planning: {data['planning'][:100]}...")
            logger.info(f"    Caption: {data['caption']}")
            logger.info(f"    Remark: {data['remark']}")
        
        # 测试种草配文生成
        planting_captions = await agent._generate_planting_captions(processed_data, planting_content)
        logger.info("\nGenerated planting captions:")
        logger.info(planting_captions[:-1])
        
        # 解析配文内容
        captions_data = parse_planting_captions(planting_captions)
        logger.info("Parsed captions data:")
        logger.info(f"  Titles: {captions_data['titles']}")
        logger.info(f"  Body length: {captions_data['body']}")
        logger.info(f"  Hashtags: {captions_data['hashtags']}")
        
    except Exception as e:
        logger.error(f"Error in planting content generation: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_task_processor())