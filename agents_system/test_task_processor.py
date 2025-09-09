#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务处理器单元测试
"""

import asyncio
import sys
import os

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


async def test_task_processor():
    """测试任务处理器"""
    # logger.info("Testing Task Processor...")
    
    # # 测试数据
    # test_request = {
    #     "topic": "夏季护肤指南",
    #     "product_highlights": "防晒、保湿、温和配方",
    #     "note_style": "种草",
    #     "product_name": "水润防晒霜",
    #     "direction": "重点介绍防晒效果和使用感受",
    #     "blogger_link": "https://xiaohongshu.com/user/12345",
    #     "requirements": "需要包含使用前后对比，适合敏感肌",
    #     "style": "活泼"
    # }
    
    # logger.info("Test request data:")
    # for key, value in test_request.items():
    #     logger.info(f"  {key}: {value}")
    
    # logger.info("="*50)
    
    # # 测试单个任务处理函数
    # logger.info("Testing individual task functions...")
    
    # logger.info("="*50)
    
    # # 测试并发任务执行
    # logger.info("Testing concurrent task execution...")
    
    # try:
    #     results = await task_processor.execute_tasks(test_request)
    #     logger.info(f"Concurrent task execution results:{results}")
    #     for task_name, result in results.items():
    #         logger.info(f"  {task_name}: {result['status']}")
    #         if result['status'] == 'success':
    #             logger.info(f"    Data: {result['data']}")
    #         else:
    #             logger.error(f"    Error: {result['error']}")
    # except Exception as e:
    #     logger.error(f"Error in concurrent task execution: {e}")
    
    # logger.info("="*50)
    
    # # 测试数据聚合和处理
    # logger.info("Testing data aggregation and processing...")
    
    # try:
    #     # 创建GraphicOutlineAgent实例以访问_aggregate_and_process方法
    #     agent = GraphicOutlineAgent()
    #     # 使用真实的_aggregate_and_process方法
    #     aggregated_result = await agent._aggregate_and_process(results, test_request)
    #     logger.info(f"Aggregated result: {aggregated_result}")
    #     logger.info(f"Total sections: {len(aggregated_result.get('sections', {}))}")
    #     if 'sections' in aggregated_result and isinstance(aggregated_result['sections'], dict):
    #         sections = aggregated_result['sections']
    #         for section_name, section_content in sections.items():
    #             logger.info(f"  Section '{section_name}': {section_content}")
    # except Exception as e:
    #     logger.error(f"Error in data aggregation and processing: {e}")
    #     import traceback
    #     logger.error(traceback.format_exc())
    
    # logger.info("="*50)
    
    # # 测试图文规划生成逻辑
    # logger.info("Testing planting content generation...")
    
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
        
        # # 测试种草图文规划生成
        # planting_content = await agent._generate_planting_content(processed_data)
        # logger.info("Generated planting content:")
        # logger.info(planting_content[:-1])

        
        # # 测试图文规划(测试)模式下的配文生成
        # planting_captions_test = await agent._generate_planting_captions(processed_data, planting_content)
        # logger.info("\nGenerated planting captions (test mode):")
        # logger.info(planting_captions_test[:-1])
        
        # # 测试图文规划(测试)模式下的格式统一输出生成
        # planting_content_test = await agent._generate_planting_content(processed_data)
        # formatted_output_test = await agent._generate_formatted_output(processed_data, planting_content_test, planting_captions_test)
        # logger.info("\nGenerated formatted output (test mode):")
        # logger.info(formatted_output_test[:1000] + "..." if len(formatted_output_test) > 1000 else formatted_output_test)
        
        # # 完整流程测试 - 从图文规划到配文再到格式化输出
        # logger.info("\n" + "="*50)
        # logger.info("Testing complete workflow: planting content -> captions -> formatted output")
        
        # 使用"种草"模式进行完整流程测试
        processed_data["note_style"] = "种草"
        complete_planting_content = await agent._generate_planting_content(processed_data)
        complete_planting_captions = await agent._generate_planting_captions(processed_data, complete_planting_content)
        complete_formatted_output = await agent._generate_formatted_output(processed_data, complete_planting_content, complete_planting_captions)
        
        logger.info("Complete workflow test results:")
        logger.info(f"1. Planting content generated: {len(complete_planting_content) > 0}")
        logger.info(f"2. Planting captions generated: {len(complete_planting_captions) > 0}")
        logger.info(f"3. Formatted output generated: {len(complete_formatted_output) > 0}")
        
        if len(complete_formatted_output) > 0:
            logger.info("Sample of formatted output:")
            logger.info(complete_formatted_output[:-1])
        
    except Exception as e:
        logger.error(f"Error in planting content generation: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_task_processor())