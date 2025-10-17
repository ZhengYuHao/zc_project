#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 graphic_outline/process-request API 接口
发送 spreadsheet_post_data_图文大纲创作_converted.json 文件中的数据项进行测试
"""

import json
import os
import requests
import time
from typing import List, Dict, Any
import uuid
from datetime import datetime

# 尝试导入aiohttp用于异步请求
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    print("警告: 未安装aiohttp包，将使用同步方式发送请求")
    print("可以通过 'pip install aiohttp' 安装以启用并发请求功能")


def load_test_data(json_file_path):
    """
    加载测试数据
    
    Args:
        json_file_path: JSON文件路径
        
    Returns:
        list: 测试数据列表
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


async def send_single_request(session, url: str, data_item: Dict[str, Any], index: int) -> Dict[str, Any]:
    """
    发送单个异步POST请求到指定URL
    
    Args:
        session: aiohttp会话
        url: 目标URL
        data_item: 要发送的数据项
        index: 数据项索引
        
    Returns:
        dict: 包含请求和响应信息的字典
    """
    try:
        # 记录发送时间
        send_time = datetime.now().isoformat()
        
        # 发送POST请求
        async with session.post(url, json=data_item, headers={'Content-Type': 'application/json'}) as response:
            # 记录响应时间
            response_time = datetime.now().isoformat()
            
            result = {
                "index": index,
                "request_id": str(uuid.uuid4()),
                "send_time": send_time,
                "response_time": response_time,
                "request_data": data_item,
                "response_status": response.status,
                "response_headers": dict(response.headers)
            }
            
            try:
                response_data = await response.json()
                result["response_data"] = response_data
            except json.JSONDecodeError as e:
                response_text = await response.text()
                result["response_text"] = response_text
                result["json_parse_error"] = str(e)
            except Exception as e:
                response_text = await response.text()
                result["response_text"] = response_text
                result["error"] = f"Response processing error: {str(e)}"
                
        return result
    except Exception as e:
        error_time = datetime.now().isoformat()
        # 确保即使发生最严重的异常也返回完整结构
        return {
            "index": index,
            "request_id": str(uuid.uuid4()),
            "send_time": error_time,
            "response_time": error_time,
            "request_data": data_item,
            "error": f"Request failed: {str(e)}"
        }


async def send_concurrent_requests(api_url: str, test_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    并发发送所有测试请求
    
    Args:
        api_url: API地址
        test_data: 测试数据列表
        
    Returns:
        list: 所有请求的结果列表
    """
    if not ASYNC_AVAILABLE:
        # 如果异步不可用，使用同步方式
        return send_sequential_requests(api_url, test_data)
    
    # 限制并发数量，避免对服务器造成过大压力
    connector = aiohttp.TCPConnector(limit=10)
    # 将超时时间从30秒增加到600秒（10分钟），以适应可能较长的API处理时间
    timeout = aiohttp.ClientTimeout(total=600)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # 创建所有任务
        tasks = [
            send_single_request(session, api_url, data_item, i) 
            for i, data_item in enumerate(test_data)
        ]
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 正常情况下不应进入此分支，因为 send_single_request 已处理所有异常
                error_time = datetime.now().isoformat()
                print(f"警告: 请求任务 {i} 抛出未捕获异常: {result}")
                processed_results.append({
                    "index": i,
                    "request_id": str(uuid.uuid4()),
                    "send_time": error_time,
                    "response_time": error_time,
                    "error": f"Unhandled task exception: {str(result)}",
                    "request_data": test_data[i] if i < len(test_data) else None
                })
            else:
                processed_results.append(result)
                
        return processed_results


def send_sequential_requests(api_url: str, test_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    顺序发送所有测试请求（同步方式）
    
    Args:
        api_url: API地址
        test_data: 测试数据列表
        
    Returns:
        list: 所有请求的结果列表
    """
    results = []
    
    for i, data_item in enumerate(test_data):
        try:
            # 记录发送时间
            send_time = datetime.now().isoformat()
            
            # 发送POST请求
            response = requests.post(api_url, json=data_item, headers={'Content-Type': 'application/json'})
            
            # 记录响应时间
            response_time = datetime.now().isoformat()
            
            result = {
                "index": i,
                "request_id": str(uuid.uuid4()),
                "send_time": send_time,
                "response_time": response_time,
                "request_data": data_item,
                "response_status": response.status_code,
                "response_headers": dict(response.headers)
            }
            
            # 尝试解析JSON响应，若失败则保存原始文本
            try:
                if response.text and response.text.strip():
                    response_data = response.json()
                    result["response_data"] = response_data
                else:
                    result["response_text"] = ""  # 明确表示空响应
            except json.JSONDecodeError as e:
                result["response_text"] = response.text
                result["json_parse_error"] = str(e)
                
            results.append(result)
            
            # 添加小延时避免请求过于频繁
            time.sleep(0.1)
            
        except Exception as e:
            error_time = datetime.now().isoformat()
            results.append({
                "index": i,
                "request_id": str(uuid.uuid4()),
                "send_time": error_time,
                "response_time": error_time,
                "request_data": data_item,
                "error": str(e)
            })
    
    return results


def save_results_to_json(results: List[Dict[str, Any]], output_file: str):
    """
    将结果保存到JSON文件
    
    Args:
        results: 请求结果列表
        output_file: 输出文件路径
    """
    output_data = {
        "test_run_time": datetime.now().isoformat(),
        "total_requests": len(results),
        "results": results
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"结果已保存到: {output_file}")


def test_all_data_items(json_file_path, api_url):
    """
    测试所有数据项（并发版本）
    
    Args:
        json_file_path: JSON文件路径
        api_url: API地址
    """
    # 加载测试数据
    test_data = load_test_data(json_file_path)
    
    print(f"加载了 {len(test_data)} 条测试数据")
    
    # 创建输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"test_results_{timestamp}.json"
    
    # 发送请求
    print("开始发送请求...")
    if ASYNC_AVAILABLE:
        print("使用并发方式发送请求")
    else:
        print("使用顺序方式发送请求")
    
    start_time = time.time()
    
    try:
        if ASYNC_AVAILABLE:
            # 确保正确导入asyncio
            import asyncio
            results = asyncio.run(send_concurrent_requests(api_url, test_data))
        else:
            results = send_sequential_requests(api_url, test_data)
    except Exception as e:
        print(f"请求执行出错: {e}")
        return
    
    end_time = time.time()
    
    # 保存结果
    save_results_to_json(results, output_file)
    
    # 打印统计信息
    successful_requests = sum(1 for r in results if "response_status" in r and r["response_status"] == 200)
    failed_requests = len(results) - successful_requests
    
    print(f"\n测试完成!")
    print(f"总请求数: {len(results)}")
    print(f"成功请求数: {successful_requests}")
    print(f"失败请求数: {failed_requests}")
    print(f"总耗时: {end_time - start_time:.2f} 秒")
    
    # 显示每个请求的简要结果
    print("\n详细结果:")
    for result in results:
        index = result["index"]
        if "response_status" in result:
            status = result["response_status"]
            print(f"  请求 {index+1}: 状态码 {status}")
        elif "error" in result:
            print(f"  请求 {index+1}: 错误 - {result['error']}")


def main():
    """
    主函数
    """
    # 配置参数
    # #视频大纲
    # api_url = "http://124.221.155.224:8843/api/video-outline-create"
    # #视频脚本
    # api_url = "http://124.221.155.224:8844/api/video-demo-create"
    # #图文大纲
    api_url = "http://124.221.155.224:8857/graphic_outline/process-request"
    
    # 查找JSON文件
    json_file_name = "spreadsheet_post_data_图文大纲创作_converted.json"
    possible_paths = [
        json_file_name,
        os.path.join("..", json_file_name),
        os.path.join("..", "..", json_file_name),
        os.path.join("e:\\pyProject\\zc_project", json_file_name)
    ]
    
    json_file_path = None
    for path in possible_paths:
        if os.path.exists(path):
            json_file_path = path
            print(f"找到测试数据文件: {path}")
            break
    
    if not json_file_path:
        print(f"未找到测试数据文件: {json_file_name}")
        return
    
    # 测试所有数据项
    test_all_data_items(json_file_path, api_url)


if __name__ == "__main__":
    # 如果支持异步，需要引入asyncio
    if ASYNC_AVAILABLE:
        import asyncio
    main()