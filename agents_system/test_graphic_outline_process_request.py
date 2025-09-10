#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GraphicOutlineAgent.process_request函数测试模块
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.graphic_outline_agent import GraphicOutlineAgent
from utils.logger import get_logger

# 获取logger实例
logger = get_logger("test.graphic_outline_process_request")


async def test_process_request():
    """测试process_request函数"""
    logger.info("Testing GraphicOutlineAgent.process_request function")
    
    # 创建GraphicOutlineAgent实例
    agent = GraphicOutlineAgent()
    
    # 准备测试数据
    test_request = {
        "topic": "夏季护肤指南",
        "product_highlights": "防晒、保湿、温和配方",
        "note_style": "种草",
        "product_name": "水润防晒霜",
        "direction": "重点介绍防晒效果和使用感受",
        "blogger_link": "https://xiaohongshu.com/user/12345",
        "requirements": "需要包含使用前后对比，适合敏感肌",
        "style": "活泼"
    }
    
    logger.info("Test request data:")
    for key, value in test_request.items():
        logger.info(f"  {key}: {value}")
    
    try:
        # 调用process_request函数
        result = await agent.process_request(test_request)
        
        # 输出结果
        logger.info("Test result:")
        logger.info(f"  Status: {result.get('status')}")
        logger.info(f"  Has spreadsheet: {'spreadsheet' in result}")
        logger.info(f"  Has processed_data: {'processed_data' in result}")
        
        if result.get('status') == 'success':
            processed_data = result.get('processed_data', {})
            logger.info(f"  Note style: {processed_data.get('note_style')}")
            logger.info(f"  Has planting_content: {'planting_content' in processed_data}")
            logger.info(f"  Has planting_captions: {'planting_captions' in processed_data}")
            
            spreadsheet = result.get('spreadsheet', {})
            logger.info(f"  Spreadsheet status: {spreadsheet.get('status')}")
            if spreadsheet.get('status') == 'success':
                logger.info(f"  Spreadsheet token: {spreadsheet.get('spreadsheet_token')}")
                logger.info(f"  Sheet ID: {spreadsheet.get('sheet_id')}")
        else:
            logger.error(f"  Error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def test_process_request_tuwen_mode():
    """测试process_request函数的图文规划模式"""
    logger.info("Testing GraphicOutlineAgent.process_request function (图文规划模式)")
    
    # 创建GraphicOutlineAgent实例
    agent = GraphicOutlineAgent()
    
    # 准备测试数据
    test_request = {
        "topic": "夏季护肤指南",
        "product_highlights": "防晒、保湿、温和配方",
        "note_style": "图文规划(测试)",
        "product_name": "水润防晒霜",
        "direction": "重点介绍防晒效果和使用感受",
        "blogger_link": "https://xiaohongshu.com/user/12345",
        "requirements": "需要包含使用前后对比，适合敏感肌",
        "style": "活泼"
    }
    
    logger.info("Test request data (图文规划模式):")
    for key, value in test_request.items():
        logger.info(f"  {key}: {value}")
    
    try:
        # 调用process_request函数
        result = await agent.process_request(test_request)
        
        # 输出结果
        logger.info("Test result (图文规划模式):")
        logger.info(f"  Status: {result.get('status')}")
        logger.info(f"  Has spreadsheet: {'spreadsheet' in result}")
        logger.info(f"  Has processed_data: {'processed_data' in result}")
        
        if result.get('status') == 'success':
            processed_data = result.get('processed_data', {})
            logger.info(f"  Note style: {processed_data.get('note_style')}")
            logger.info(f"  Has planting_content: {'planting_content' in processed_data}")
            logger.info(f"  Has planting_captions: {'planting_captions' in processed_data}")
            
            spreadsheet = result.get('spreadsheet', {})
            logger.info(f"  Spreadsheet status: {spreadsheet.get('status')}")
            if spreadsheet.get('status') == 'success':
                logger.info(f"  Spreadsheet token: {spreadsheet.get('spreadsheet_token')}")
                logger.info(f"  Sheet ID: {spreadsheet.get('sheet_id')}")
        else:
            logger.error(f"  Error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    logger.info("Starting GraphicOutlineAgent.process_request tests")
    
    # 运行测试
    asyncio.run(test_process_request())
    # logger.info("="*50)
    # asyncio.run(test_process_request_tuwen_mode())
    
    logger.info("Tests completed!")