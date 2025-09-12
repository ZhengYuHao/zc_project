#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试GraphicOutlineAgent的process_request RESTful API接口
"""

import asyncio
import sys
import os
import httpx

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.logger import get_logger

# 获取logger实例
logger = get_logger("test.process_request_api")


async def test_process_request_api():
    """测试process_request RESTful API接口"""
    logger.info("Testing GraphicOutlineAgent process_request API")
    
    # API端点
    api_url = "http://localhost:8000/graphic_outline/process-request"
    
    # 准备测试数据
    test_data = {
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
    for key, value in test_data.items():
        logger.info(f"  {key}: {value}")
    
    try:
        # 发送POST请求到API
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=test_data, timeout=300.0)
            
        # 输出响应
        logger.info("API Response:")
        logger.info(f"  Status Code: {response.status_code}")
        logger.info(f"  Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"  Status: {response_data.get('status')}")
            logger.info(f"  Has spreadsheet: {'spreadsheet' in response_data}")
            logger.info(f"  Has processed_data: {'processed_data' in response_data}")
            
            if response_data.get('status') == 'success':
                processed_data = response_data.get('processed_data', {})
                logger.info(f"  Note style: {processed_data.get('note_style')}")
                logger.info(f"  Has planting_content: {'planting_content' in processed_data}")
                logger.info(f"  Has planting_captions: {'planting_captions' in processed_data}")
                
                spreadsheet = response_data.get('spreadsheet', {})
                logger.info(f"  Spreadsheet status: {spreadsheet.get('status')}")
                if spreadsheet.get('status') == 'success':
                    logger.info(f"  Spreadsheet token: {spreadsheet.get('spreadsheet_token')}")
                    logger.info(f"  Sheet ID: {spreadsheet.get('sheet_id')}")
            else:
                logger.error(f"  Error: {response_data.get('error')}")
        else:
            logger.error(f"  Error Response: {response.text}")
            
    except Exception as e:
        logger.error(f"Error during API test: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    logger.info("Starting GraphicOutlineAgent process_request API test")
    
    # 运行测试
    asyncio.run(test_process_request_api())
    
    logger.info("API test completed!")