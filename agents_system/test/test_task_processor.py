#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Processor测试模块
用于系统测试task_processor中的七个功能
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents_system.core.task_processor import (
    task_processor,
    extract_target_audience,
    extract_required_content,
    extract_blogger_style,
    extract_product_category,
    extract_selling_points,
    extract_product_endorsement,
    extract_topic
)


async def test_single_task(task_name: str, task_func, request_data: Dict[str, Any]):
    """测试单个任务函数"""
    print(f"\n{'='*50}")
    print(f"测试任务: {task_name}")
    print(f"{'='*50}")
    
    try:
        result = await task_func(request_data)
        print(f"✅ 测试通过")
        print(f"结果: {result}")
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


async def test_all_tasks_individually():
    """单独测试所有任务函数"""
    print("开始单独测试所有任务函数...")
    
    # 测试数据
    test_data = {
        "topic": "夏季护肤",
        "product_highlights": "这是一款具有防晒指数SPF50+的轻薄型防晒霜，含有透明质酸和维生素E，适合敏感肌肤使用。",
        "requirements": "必须提到防晒指数和适用肌肤类型",
        "blogger_link": "https://example.com/blogger-profile",
        "note_style": "活泼、轻松"
    }
    
    results = []
    
    # 测试目标人群提取
    result = await test_single_task(
        "目标人群提取 (extract_target_audience)",
        extract_target_audience,
        test_data
    )
    results.append(result)
    
    # 测试必提内容提取
    result = await test_single_task(
        "必提内容提取 (extract_required_content)",
        extract_required_content,
        test_data
    )
    results.append(result)
    
    # 测试达人风格理解
    result = await test_single_task(
        "达人风格理解 (extract_blogger_style)",
        extract_blogger_style,
        test_data
    )
    results.append(result)
    
    # 测试产品品类提取
    result = await test_single_task(
        "产品品类提取 (extract_product_category)",
        extract_product_category,
        test_data
    )
    results.append(result)
    
    # 测试卖点提取
    result = await test_single_task(
        "卖点提取 (extract_selling_points)",
        extract_selling_points,
        test_data
    )
    results.append(result)
    
    # 测试产品背书提取
    result = await test_single_task(
        "产品背书提取 (extract_product_endorsement)",
        extract_product_endorsement,
        test_data
    )
    results.append(result)
    
    # 测试话题提取
    result = await test_single_task(
        "话题提取 (extract_topic)",
        extract_topic,
        test_data
    )
    results.append(result)
    
    return results


async def test_concurrent_execution():
    """测试并发执行所有任务"""
    print(f"\n{'='*50}")
    print("测试并发执行所有任务")
    print(f"{'='*50}")
    
    # 测试数据
    test_data = {
        "topic": "夏季护肤",
        "product_highlights": "这是一款具有防晒指数SPF50+的轻薄型防晒霜，含有透明质酸和维生素E，适合敏感肌肤使用。",
        "requirements": "必须提到防晒指数和适用肌肤类型",
        "blogger_link": "https://example.com/blogger-profile",
        "note_style": "活泼、轻松"
    }
    
    try:
        print("开始并发执行所有注册的任务...")
        results = await task_processor.execute_tasks(test_data)
        
        print("✅ 并发执行测试通过")
        print(f"执行结果: {results}")
        
        # 检查结果
        success_count = 0
        for task_name, result in results.items():
            if result.get("status") == "success":
                success_count += 1
                print(f"  - {task_name}: 成功")
                # 打印详细数据
                data = result.get("data", {})
                if data:
                    print(f"    数据: {data}")
            else:
                print(f"  - {task_name}: 失败 - {result.get('error', '未知错误')}")
        
        print(f"\n成功执行 {success_count}/{len(results)} 个任务")
        return success_count == len(results)
        
    except Exception as e:
        print(f"❌ 并发执行测试失败: {e}")
        return False


async def test_task_processor_registry():
    """测试任务注册功能"""
    print(f"\n{'='*50}")
    print("测试任务注册功能")
    print(f"{'='*50}")
    
    try:
        # 检查已注册的任务
        registered_tasks = list(task_processor.tasks.keys())
        print(f"已注册的任务: {registered_tasks}")
        
        expected_tasks = [
            "target_audience_extractor",
            "required_content_extractor", 
            "blogger_style_extractor",
            "product_category_extractor",
            "selling_points_extractor",
            "product_endorsement_extractor",
            "topic_extractor"
        ]
        
        # 检查是否所有预期任务都已注册
        missing_tasks = [task for task in expected_tasks if task not in registered_tasks]
        if missing_tasks:
            print(f"❌ 缺少注册任务: {missing_tasks}")
            return False
        else:
            print("✅ 所有任务均已正确注册")
            return True
            
    except Exception as e:
        print(f"❌ 任务注册测试失败: {e}")
        return False


async def test_edge_cases():
    """测试边界情况"""
    print(f"\n{'='*50}")
    print("测试边界情况")
    print(f"{'='*50}")
    
    # 空数据测试
    print("1. 测试空数据:")
    empty_data = {}
    try:
        results = await task_processor.execute_tasks(empty_data)
        print(f"✅ 空数据测试通过，结果: {results}")
        empty_test_passed = True
    except Exception as e:
        print(f"❌ 空数据测试失败: {e}")
        empty_test_passed = False
    
    # 部分数据测试
    print("\n2. 测试部分数据:")
    partial_data = {
        "product_highlights": "这是一款具有防晒指数SPF50+的轻薄型防晒霜",
        "note_style": "专业、权威"
    }
    try:
        results = await task_processor.execute_tasks(partial_data)
        print(f"✅ 部分数据测试通过，结果: {results}")
        partial_test_passed = True
    except Exception as e:
        print(f"❌ 部分数据测试失败: {e}")
        partial_test_passed = False
    
    return empty_test_passed and partial_test_passed


async def test_text_parsing_edge_cases():
    """测试文本解析边界情况"""
    print(f"\n{'='*50}")
    print("测试文本解析边界情况")
    print(f"{'='*50}")
    
    # 模拟大模型返回的边界情况
    
    # 测试数据包含各种边界情况
    test_cases = [
        {
            "name": "正常情况",
            "data": {
                "topic": "护肤",
                "product_highlights": "防晒霜SPF50+"
            }
        },
        {
            "name": "空内容",
            "data": {
                "topic": "护肤",
                "product_highlights": ""
            }
        },
        {
            "name": "无匹配标签",
            "data": {
                "topic": "护肤",
                "product_highlights": "这是一段没有标准标签的文本"
            }
        }
    ]
    
    parsing_tests_passed = True
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            result = await extract_target_audience(test_case['data'])
            print(f"  结果: {result}")
        except Exception as e:
            print(f"  错误: {e}")
            parsing_tests_passed = False
    
    # 添加特殊测试：测试包含特殊字符的情况
    print(f"\n测试特殊字符处理:")
    special_char_test_data = {
        "topic": "测试",
        "product_highlights": "测试产品"
    }
    try:
        result = await extract_selling_points(special_char_test_data)
        print(f"  特殊字符测试结果: {result}")
    except Exception as e:
        print(f"  特殊字符测试错误: {e}")
        parsing_tests_passed = False
    
    return parsing_tests_passed


async def main():
    """主测试函数"""
    print("开始Task Processor模块测试")
    print("=" * 60)
    
    # 测试任务注册
    registry_test_passed = await test_task_processor_registry()
    
    # 测试单独执行各任务
    individual_results = await test_all_tasks_individually()
    individual_test_passed = all(individual_results)
    
    # 测试并发执行
    concurrent_test_passed = await test_concurrent_execution()
    
    # 测试边界情况
    edge_test_passed = await test_edge_cases()
    
    # 测试文本解析边界情况
    parsing_test_passed = await test_text_parsing_edge_cases()
    
    # 汇总结果
    print(f"\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}")
    print(f"任务注册测试: {'✅ 通过' if registry_test_passed else '❌ 失败'}")
    print(f"单独任务测试: {'✅ 通过' if individual_test_passed else '❌ 失败'}")
    print(f"并发执行测试: {'✅ 通过' if concurrent_test_passed else '❌ 失败'}")
    print(f"边界情况测试: {'✅ 通过' if edge_test_passed else '❌ 失败'}")
    print(f"文本解析测试: {'✅ 通过' if parsing_test_passed else '❌ 失败'}")
    
    all_tests_passed = (
        registry_test_passed and 
        individual_test_passed and 
        concurrent_test_passed and 
        edge_test_passed and
        parsing_test_passed
    )
    
    print(f"\n总体测试结果: {'✅ 全部通过' if all_tests_passed else '❌ 存在失败'}")
    
    return all_tests_passed


if __name__ == "__main__":
    test_result = asyncio.run(main())
    sys.exit(0 if test_result else 1)