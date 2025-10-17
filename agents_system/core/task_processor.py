#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发任务处理器模块
处理图文大纲生成中的多个并发任务
"""

import asyncio
import json
import httpx
from typing import Dict, Any, List, Callable, Optional
from utils.logger import get_logger
from config.model_config import load_model_config
from models.model_manager import ModelManager


# 全局模型管理器实例
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """获取模型管理器单例实例"""
    global _model_manager
    if _model_manager is None:
        config = load_model_config()
        _model_manager = ModelManager(config)
    return _model_manager


# 先定义TaskProcessor类再实例化
class TaskProcessor:
    """任务处理器类"""
    def __init__(self):
        self.tasks = {}
    
    def register_task(self, task_name: str, func: Callable):
        """注册任务"""
        self.tasks[task_name] = func
    
    async def execute_task(self, task_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        if task_name not in self.tasks:
            raise ValueError(f"Unknown task: {task_name}")
        return await self.tasks[task_name](request_data)


# 全局任务处理器实例
task_processor = TaskProcessor()


# 将TaskProcessor类的定义移到所有异步处理函数之前
class TaskProcessor:
    """任务处理器类"""
    def __init__(self):
        self.tasks = {}
    
    def register_task(self, task_name: str, func: Callable):
        """注册任务"""
        self.tasks[task_name] = func
    
    async def execute_task(self, task_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        if task_name not in self.tasks:
            raise ValueError(f"Unknown task: {task_name}")
        return await self.tasks[task_name](request_data)


# 全局任务处理器实例
task_processor = TaskProcessor()


async def extract_blogger_style(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取达人风格理解
    
    Args:
        request_data: 请求数据，包含小红书用户主页URL
        
    Returns:
        处理结果
    """
    logger = get_logger("agent.task_processor")
    
    # 获取请求URL（小红书用户主页URL）
    xhs_profile_url = request_data.get('blogger_link')
    if not xhs_profile_url:
        logger.error("Missing URL in request data")
        return {
            "blogger_style": "达人风格分析: 未提供小红书用户主页URL",
            "tone": "professional",
            "expression_style": "图文并茂"
        }
    
    try:
        # 从URL中提取userUuid（最后一部分）
        # 例如：https://www.xiaohongshu.com/user/Profile/63611642000000001f0162a1
        # 提取：63611642000000001f0162a1
        from urllib.parse import urlparse
        parsed_url = urlparse(xhs_profile_url)
        path_parts = parsed_url.path.strip('/').split('/')
        user_uuid = path_parts[-1] if path_parts else None
        
        if not user_uuid:
            logger.error(f"无法从URL中提取userUuid: {xhs_profile_url}")
            return {
                "blogger_style": "达人风格分析: 无法从URL中提取用户ID",
                "tone": "professional",
                "expression_style": "图文并茂"
            }
        
        logger.info(f"提取到的userUuid: {user_uuid}")
        
        # 从配置中获取API URL
        from config.settings import settings
        api_url = settings.XHS_USER_NOTES_API_URL
        
        # 准备POST请求数据
        post_data = {
            "size": 5,
            "publicTimeEnd": "2025-09-01 00:00:00",
            "publicTimeStart": "2025-06-01 00:00:00", 
            "userUuid": user_uuid  # 使用从URL中提取的userUuid
        }
        
        # 发送POST请求获取达人笔记数据
        logger.info(f"Fetching blogger posts from: {api_url}")
        logger.info(f"Request data: {post_data}")
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=post_data)
            response.raise_for_status()
            result = response.json()
            
        logger.info(f"Received {len(result.get('data', []))} posts from API")
        
        # 检查API响应
        if result.get("code") != "200":
            logger.error(f"API returned error: {result.get('msg', 'Unknown error')}")
            return {
                "blogger_style": "达人风格分析: 获取达人数据失败",
                "tone": "professional",
                "expression_style": "图文并茂"
            }
        
        # 提取笔记数据
        blogger_posts = result.get("data", [])
        if not blogger_posts:
            logger.warning("No posts found in API response")
            return {
                "blogger_style": "达人风格分析: 未获取到达人笔记数据",
                "tone": "professional",
                "expression_style": "图文并茂"
            }
        
        # 构建提示词文本部分
        text_prompt = """## 角色
你是一位专业的内容分析与创作顾问，擅长为品牌合作达人制定定制化商单内容方向。你的任务是基于达人过往的内容风格与表达习惯，为团队提供清晰的内容创作切入点。

**目标说明**：本分析用于商单合作前的内容大纲制定环节，基于达人既有内容风格与表达特征，辅助内容策划人员精准匹配品牌核心信息，明确内容切入角度与表达策略。

### 技能
## 技能 1：达人内容风格分析  
请根据达人多篇笔记的【达人笔记封面图】和【配文】，分析以下要素：
- **笔记视觉风格**：如配色、构图、场景、花字使用等  
- **表达语言风格**：是否口语化/情绪感强/标语化/数据型/故事化等  
- **人设定位、性别**：结合其内容表达方式，描述其在用户心中的角色形象 ；分析该达人的性别
- **风格关键词标签**：如 #吐槽型 #干货控 #生活流 #踩坑党

## 限制  
- 回复仅围绕达人风格分析，不输出脚本、不进行达人选择判断；
- 所有内容必须结构清晰、术语通用、语言自然，便于下游节点直接使用。

请分析以下达人笔记内容：
"""

        # 构建消息内容（包括文本和图片）
        content = [{"type": "text", "text": text_prompt}]
        
        # 添加笔记内容到消息中
        for i, post in enumerate(blogger_posts, 1):
            content.append({"type": "text", "text": f"\n笔记 {i}:\n"})
            
            # 添加图片（如果存在）
            image_url = post.get('imagesList')
            if image_url:
                content.append({
                    "type": "text", 
                    "text": f"【达人笔记封面图】：\n"
                })
                # 添加图片URL到内容中
                image_content = {
                    "type": "image_url",
                    "image_url": {"url": image_url}
                }
                content.append(image_content)
            
            # 添加配文（如果存在）
            caption = post.get('description')
            if caption:
                content.append({
                    "type": "text", 
                    "text": f"\n【配文】：{caption}\n"
                })

        logger.info(f"Extracting blogger style for {(blogger_posts)} posts")

        # 使用模型管理器调用视觉模型（通过支持特殊消息格式的新方法）
        from models.model_manager import ModelManager
        model_manager = ModelManager()
        
        # 构造视觉模型调用的消息格式
        messages = [{"role": "user", "content": content}]
        
        # 调用视觉模型（使用blogger_style_analysis任务类型）
        result = await model_manager.call_model_with_messages("blogger_style_analysis", messages)
        
        # 解析结果
        response = {
            "blogger_style": result,
            "tone": "friendly" if "活泼" in result or "轻松" in result else "professional",
            "expression_style": "图文并茂"
        }
        
        logger.info(f"Extract blogger style result: {response}")
        return response
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error when fetching blogger posts: {str(e)}")
        # 记录异常的详细信息
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # 出现异常时返回默认值
        default_response = {
            "blogger_style": "达人风格分析: 获取达人数据时网络错误",
            "tone": "professional",
            "expression_style": "图文并茂"
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response
    except Exception as e:
        logger.error(f"Error extracting blogger style: {str(e)}")
        # 记录异常的详细信息
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # 出现异常时返回默认值
        default_response = {
            "blogger_style": "达人风格分析: 未分析出具体风格",
            "tone": "professional",
            "expression_style": "图文并茂"
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response
    
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
        """执行所有注册的任务"""
        results = {}
        
        # 并发执行所有任务
        task_list = []
        for task_name, task_func in self.tasks.items():
            self.logger.info(f"Executing task: {task_name}")
            task_list.append((task_name, task_func(request_data)))
        
        # 等待所有任务完成
        for task_name, task_coro in task_list:
            try:
                result = await task_coro
                # 统一结果格式
                if isinstance(result, dict) and "error" in result:
                    # 任务执行出错
                    results[task_name] = {
                        "status": "failed",
                        "error": result["error"]
                    }
                else:
                    # 任务执行成功
                    results[task_name] = {
                        "status": "success",
                        "data": result
                    }
                self.logger.info(f"Task {task_name} completed with status: {results[task_name]['status']}")
            except Exception as e:
                self.logger.error(f"Task {task_name} failed with error: {str(e)}")
                results[task_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        self.logger.info("All tasks completed")
        return results
    
    async def _execute_single_task(self, task_name: str, task_func: Callable, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个任务"""
        try:
            self.logger.info(f"Executing task: {task_name}")
            result = await task_func(request_data)
            self.logger.info(f"Task {task_name} completed successfully")
            return {task_name: result}
        except Exception as e:
            self.logger.error(f"Error executing task {task_name}: {str(e)}")
            # 记录异常的详细信息
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return {task_name: {"error": str(e)}}


# 全局任务处理器实例
task_processor = TaskProcessor()

# 注册所有任务
task_processor.register_task("blogger_style_extractor", extract_blogger_style)  # 注册达人风格理解提取任务
# task_processor.register_task("product_endorsement_extractor", extract_product_endorsement)  # 注册产品背书提取任务
# task_processor.register_task("topic_extractor", extract_topic)  # 注册话题提取任务