#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发任务处理器模块
处理图文大纲生成中的多个并发任务
"""

import asyncio
from typing import Dict, Any, List, Callable, Optional
from utils.logger import get_logger


class TaskProcessor:
    """并发任务处理器"""
    
    def __init__(self):
        self.logger = get_logger("agent.task_processor")
        self.tasks = {}
    
    def register_task(self, task_name: str, task_func: Callable):
        """
        注册任务处理函数
        
        Args:
            task_name: 任务名称
            task_func: 任务处理函数
        """
        self.tasks[task_name] = task_func
        self.logger.info(f"Registered task: {task_name}")
    
    async def execute_tasks(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        并发执行注册的任务
        
        Args:
            request_data: 请求数据
            
        Returns:
            所有任务的执行结果
        """
        self.logger.info("Starting concurrent task execution")
        
        # 创建任务列表
        tasks = []
        task_names = []
        
        # 为每个注册的任务创建异步任务
        for task_name, task_func in self.tasks.items():
            # 检查请求数据中是否有该任务需要的数据
            if self._should_execute_task(task_name, request_data):
                task = asyncio.create_task(self._execute_single_task(task_name, task_func, request_data))
                tasks.append(task)
                task_names.append(task_name)
        
        if not tasks:
            self.logger.info("No tasks to execute")
            return {}
        
        self.logger.info(f"Executing {len(tasks)} tasks concurrently: {task_names}")
        
        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        processed_results = {}
        for task_name, result in zip(task_names, results):
            if isinstance(result, Exception):
                self.logger.error(f"Task {task_name} failed with error: {str(result)}")
                processed_results[task_name] = {
                    "status": "error",
                    "error": str(result)
                }
            else:
                self.logger.info(f"Task {task_name} completed successfully")
                processed_results[task_name] = {
                    "status": "success",
                    "data": result
                }
        
        self.logger.info("All tasks completed")
        return processed_results
    
    async def _execute_single_task(self, task_name: str, task_func: Callable, request_data: Dict[str, Any]) -> Any:
        """
        执行单个任务
        
        Args:
            task_name: 任务名称
            task_func: 任务处理函数
            request_data: 请求数据
            
        Returns:
            任务执行结果
        """
        try:
            self.logger.info(f"Executing task: {task_name}")
            # 调用任务函数，传入请求数据
            result = await task_func(request_data)
            return result
        except Exception as e:
            self.logger.error(f"Error executing task {task_name}: {str(e)}")
            raise
    
    def _should_execute_task(self, task_name: str, request_data: Dict[str, Any]) -> bool:
        """
        判断是否应该执行某个任务
        
        Args:
            task_name: 任务名称
            request_data: 请求数据
            
        Returns:
            是否应该执行任务
        """
        # 根据任务名称和请求数据判断是否需要执行
        task_data_mapping = {
            "target_audience_extractor": "topic",
            "required_content_extractor": "requirements",
            "blogger_style_extractor": "note_style",
            "product_category_extractor": "product_name",
            "selling_points_extractor": "product_highlights",
            "product_endorsement_extractor": "blogger_link",
            "topic_extractor": "topic"
        }
        
        required_field = task_data_mapping.get(task_name)
        if required_field and required_field in request_data and request_data[required_field]:
            return True
        
        return False


# 全局任务处理器实例
task_processor = TaskProcessor()


# 七个新的任务处理函数
async def extract_target_audience(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取目标人群
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    # 这里应该调用实际的豆包模型处理逻辑
    # 暂时返回模拟数据
    topic = request_data.get('topic', '')
    return {
        "target_audience": f"根据'{topic}'分析的目标人群",
        "age_group": "20-35岁",
        "interest_tags": ["美妆", "护肤", "生活方式"]
    }


async def extract_required_content(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取必提内容
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    # 这里应该调用实际的豆包模型处理逻辑
    # 暂时返回模拟数据
    requirements = request_data.get('requirements', '')
    return {
        "required_content": f"必须包含的内容点: {requirements}",
        "content_type": "核心要点",
        "priority": "high"
    }


async def extract_blogger_style(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取达人风格理解
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    # 这里应该调用实际的豆包模型处理逻辑
    # 暂时返回模拟数据
    note_style = request_data.get('note_style', '')
    return {
        "blogger_style": f"达人风格分析: {note_style}",
        "tone": "friendly" if "活泼" in note_style or "轻松" in note_style else "professional",
        "expression_style": "图文并茂"
    }


async def extract_product_category(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取产品品类
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    # 这里应该调用实际的豆包模型处理逻辑
    # 暂时返回模拟数据
    product_name = request_data.get('product_name', '')
    return {
        "product_category": f"根据'{product_name}'识别的品类",
        "category_tags": ["美妆", "护肤"],
        "market_segment": "大众市场"
    }


async def extract_selling_points(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取卖点
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    # 这里应该调用实际的豆包模型处理逻辑
    # 暂时返回模拟数据
    product_highlights = request_data.get('product_highlights', '')
    return {
        "selling_points": f"核心卖点: {product_highlights}",
        "unique_selling_proposition": "差异化优势",
        "consumer_benefits": ["功效", "安全性", "易用性"]
    }


async def extract_product_endorsement(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取产品背书
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    # 这里应该调用实际的豆包模型处理逻辑
    # 暂时返回模拟数据
    blogger_link = request_data.get('blogger_link', '')
    return {
        "endorsement_type": "达人推荐" if blogger_link else "无背书",
        "endorser_level": "专业博主" if "professional" in blogger_link else "普通博主",
        "credibility_factors": ["使用体验", "专业知识"]
    }


async def extract_topic(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取话题
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    # 这里应该调用实际的豆包模型处理逻辑
    # 暂时返回模拟数据
    topic = request_data.get('topic', '')
    return {
        "main_topic": topic,
        "subtopics": [f"{topic}相关要点1", f"{topic}相关要点2"],
        "trending_status": "热门" if "热门" in topic else "普通",
        "content_angle": "科普型"
    }


# 注册所有任务
task_processor.register_task("target_audience_extractor", extract_target_audience)  # 注册目标人群提取任务
task_processor.register_task("required_content_extractor", extract_required_content)  # 注册必提内容提取任务
task_processor.register_task("blogger_style_extractor", extract_blogger_style)  # 注册达人风格理解提取任务
task_processor.register_task("product_category_extractor", extract_product_category)  # 注册产品品类提取任务
task_processor.register_task("selling_points_extractor", extract_selling_points)  # 注册卖点提取任务
task_processor.register_task("product_endorsement_extractor", extract_product_endorsement)  # 注册产品背书提取任务
task_processor.register_task("topic_extractor", extract_topic)  # 注册话题提取任务