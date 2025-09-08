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
except ImportError as e:
    print(f"ImportError: {e}")
    raise


async def test_task_processor():
    """测试任务处理器"""
    print("Testing Task Processor...")
    
    # 测试数据
    test_request = {
        "topic": "夏季护肤指南",
        "product_highlights": "防晒、保湿、温和配方",
        "note_style": "小红书风格，轻松活泼",
        "product_name": "水润防晒霜",
        "direction": "重点介绍防晒效果和使用感受",
        "blogger_link": "https://xiaohongshu.com/user/12345",
        "requirements": "需要包含使用前后对比，适合敏感肌",
        "style": "活泼"
    }
    
    print("Test request data:")
    for key, value in test_request.items():
        print(f"  {key}: {value}")
    
    print("\n" + "="*50)
    
    # 测试单个任务处理函数
    print("Testing individual task functions...")
    
    # try:
    #     target_audience_result = await extract_target_audience(test_request)
    #     print(f"Target audience result: {target_audience_result}")
    # except Exception as e:
    #     print(f"Error in extract_target_audience: {e}")
    
    # try:
    #     required_content_result = await extract_required_content(test_request)
    #     print(f"Required content result: {required_content_result}")
    # except Exception as e:
    #     print(f"Error in extract_required_content: {e}")
    
    # try:
    #     blogger_style_result = await extract_blogger_style(test_request)
    #     print(f"Blogger style result: {blogger_style_result}")
    # except Exception as e:
    #     print(f"Error in extract_blogger_style: {e}")
    
    # try:
    #     product_category_result = await extract_product_category(test_request)
    #     print(f"Product category result: {product_category_result}")
    # except Exception as e:
    #     print(f"Error in extract_product_category: {e}")
    
    # try:
    #     selling_points_result = await extract_selling_points(test_request)
    #     print(f"Selling points result: {selling_points_result}")
    # except Exception as e:
    #     print(f"Error in extract_selling_points: {e}")
    
    # try:
    #     product_endorsement_result = await extract_product_endorsement(test_request)
    #     print(f"Product endorsement result: {product_endorsement_result}")
    # except Exception as e:
    #     print(f"Error in extract_product_endorsement: {e}")
    
    # try:
    #     topic_result = await extract_topic(test_request)
    #     print(f"Topic result: {topic_result}")
    # except Exception as e:
    #     print(f"Error in extract_topic: {e}")
    
    print("\n" + "="*50)
    
    # 测试并发任务执行
    print("Testing concurrent task execution...")
    
    try:
        results = await task_processor.execute_tasks(test_request)
        print(f"Concurrent task execution results:{results}")
        for task_name, result in results.items():
            print(f"  {task_name}: {result['status']}")
            if result['status'] == 'success':
                print(f"    Data: {result['data']}")
            else:
                print(f"    Error: {result['error']}")
    except Exception as e:
        print(f"Error in concurrent task execution: {e}")
    
    print("\n" + "="*50)
    
    # 测试数据聚合和处理
    print("Testing data aggregation and processing...")
    
    # try:
    #     # 创建GraphicOutlineAgent实例以访问_aggregate_and_process方法
    #     agent = GraphicOutlineAgent()
    #     # 使用真实的_aggregate_and_process方法
    #     aggregated_result = await agent._aggregate_and_process(results, test_request)
    #     print(f"Aggregated result: {aggregated_result}")
    #     print(f"Total sections: {len(aggregated_result.get('sections', {}))}")
    #     if 'sections' in aggregated_result and isinstance(aggregated_result['sections'], dict):
    #         sections = aggregated_result['sections']
    #         for section_name, section_content in sections.items():
    #             print(f"  Section '{section_name}': {section_content}")
    # except Exception as e:
    #     print(f"Error in data aggregation and processing: {e}")
    #     import traceback
    #     traceback.print_exc()
    
    # print("\n" + "="*50)
    
    # # 测试图文规划生成逻辑
    # print("Testing planting content generation...")
    
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
        print("Generated planting content:")
        print(planting_content[:-1] + "..." if len(planting_content) > 500 else planting_content)
        
        # 测试图文规划(测试)模式
        processed_data["note_style"] = "图文规划(测试)"
        planting_content_test = await agent._generate_planting_content(processed_data)
        print("\nGenerated planting content (test mode):")
        print(planting_content_test[:-1])
        
    except Exception as e:
        print(f"Error in planting content generation: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest completed!")


if __name__ == "__main__":
    asyncio.run(test_task_processor())