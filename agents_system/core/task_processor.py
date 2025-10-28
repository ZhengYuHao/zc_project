#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并发任务处理器模块
处理图文大纲生成中的多个并发任务
"""

import asyncio
import json
import httpx
import uuid
import os
from typing import Dict, Any, List, Callable, Optional
from utils.logger import get_logger
from config.model_config import load_model_config
from models.model_manager import ModelManager
# 引入request_context模块来处理request_id
from core.request_context import get_request_id

# 全局模型管理器实例
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """获取模型管理器单例实例"""
    global _model_manager
    if _model_manager is None:
        config = load_model_config()
        _model_manager = ModelManager(config)
    return _model_manager


# 存储异步任务状态的字典和等待事件
# 修改async_tasks结构，增加request_id字段
async_tasks: Dict[str, Dict[str, Any]] = {}
task_events: Dict[str, asyncio.Event] = {}


# 先定义TaskProcessor类再实例化
class TaskProcessor:
    """任务处理器类"""
    def __init__(self):
        self.tasks = {}
        # 加载提示词
        self._load_prompts()
    
    def _load_prompts(self):
        """加载提示词"""
        prompts_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prompts', 'prompts.json')
        try:
            with open(prompts_path, 'r', encoding='utf-8') as f:
                self.prompts = json.load(f)
        except Exception as e:
            logger = get_logger("agent.task_processor")
            logger.error(f"Failed to load prompts from {prompts_path}: {str(e)}")
            self.prompts = {}
    
    def register_task(self, task_name: str, func: Callable):
        """注册任务"""
        self.tasks[task_name] = func
    
    async def execute_task(self, task_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务"""
        if task_name not in self.tasks:
            raise ValueError(f"Unknown task: {task_name}")
        return await self.tasks[task_name](request_data)

    async def execute_tasks(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """并发执行所有注册的任务"""
        results = {}
        
        # 创建任务列表
        tasks = []
        task_names = []
        
        # 为每个注册的任务创建异步任务
        for task_name, task_func in self.tasks.items():
            task = asyncio.create_task(self._execute_single_task(task_name, task_func, request_data))
            tasks.append(task)
            task_names.append(task_name)
        
        if not tasks:
            return {}
        
        # 并发执行所有任务
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for task_name, result in zip(task_names, task_results):
            if isinstance(result, Exception):
                results[task_name] = {
                    "status": "error",
                    "error": str(result)
                }
            else:
                results[task_name] = {
                    "status": "success",
                    "data": result
                }
        
        return results
    
    async def _execute_single_task(self, task_name: str, task_func: Callable, request_data: Dict[str, Any]) -> Any:
        """执行单个任务"""
        try:
            return await task_func(request_data)
        except Exception as e:
            # 重新抛出异常，让execute_tasks方法捕获并处理
            raise e


# 全局任务处理器实例
task_processor = TaskProcessor()


async def extract_product_category(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取产品品类
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果，包含产品品类信息
    """
    logger = get_logger("agent.task_processor")
    
    try:
        # 获取请求数据
        product_highlights = request_data.get('ProductHighlights', '')
        
        logger.info(f"Extracting product category with highlights: {product_highlights}")
        
        # 构建提示词
        role = task_processor.prompts.get("product_category", {}).get("analyze_category", {}).get("role", "")
        skills = task_processor.prompts.get("product_category", {}).get("analyze_category", {}).get("skills", {}).get("skill_1", "")
        restrictions = task_processor.prompts.get("product_category", {}).get("analyze_category", {}).get("restrictions", [])
        
        # 构建完整的提示词
        prompt = f"""{role}

## 技能
{skills}

## 限制
{chr(10).join('- ' + r for r in restrictions)}

产品卖点：{product_highlights}
"""
        
        # 使用模型管理器调用模型进行品类分析
        model_manager = get_model_manager()
        
        # 调用模型进行品类分析
        result = await model_manager.call_model("product_category", prompt)
        
        # 返回结果
        response = {
            "product_category": result
        }
        
        logger.info(f"Extract product category result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting product category: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 出现异常时返回默认值
        default_response = {
            "product_category": "未识别到品类"
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response


async def extract_blogger_style(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取达人风格理解（异步回调阻塞版本）
    
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
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 获取当前请求的request_id并保存
        request_id = get_request_id()
        
        # 创建事件用于等待回调
        task_event = asyncio.Event()
        task_events[task_id] = task_event
        
        # 从配置中获取API URL
        from config.settings import settings
        api_url = settings.XHS_USER_NOTES_API_URL
        
        # 准备回调URL - 这是外部服务处理完成后推送数据的地址
        callback_url = f"http://124.221.155.224:8847/callback/blogger_style/{task_id}"
        
        # 准备POST请求数据，包含回调URL
        post_data = {
            "size": 5,
            "publicTimeEnd": "2025-09-01 00:00:00",
            "publicTimeStart": "2025-06-01 00:00:00", 
            "userUuid": user_uuid,
            "callbackUrl": callback_url  # 提供给外部服务的回调地址
        }
        
        # 发送POST请求启动异步任务
        logger.info(f"Sending async request to: {api_url}")
        logger.info(f"Request data: {post_data}")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=post_data)
            response.raise_for_status()
            result = response.json()
            
        logger.info(f"Async task initiated, response: {result}")
        
        # 存储任务状态，同时保存原始的request_id
        async_tasks[task_id] = {
            "status": "processing",
            "created_at": asyncio.get_event_loop().time(),
            "request_id": request_id  # 保存原始请求ID
        }
        
        # 等待外部服务回调（阻塞等待，但不阻塞事件循环）
        logger.info(f"Waiting for callback for task_id: {task_id}")
        await task_event.wait()
        
        # 获取回调数据
        callback_data = async_tasks[task_id].get("data")
        if not callback_data:
            logger.error(f"No callback data received for task_id: {task_id}")
            return {
                "blogger_style": "达人风格分析: 未收到回调数据",
                "tone": "professional",
                "expression_style": "图文并茂"
            }
        
        # 处理回调数据
        return await _process_blogger_data(task_id, callback_data)
        
    except httpx.HTTPError as e:
        logger.error(f"HTTP error when initiating async blogger analysis: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "blogger_style": "达人风格分析: 启动异步任务时网络错误",
            "tone": "professional",
            "expression_style": "图文并茂"
        }
    except Exception as e:
        logger.error(f"Error initiating async blogger style analysis: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "blogger_style": "达人风格分析: 启动异步任务失败",
            "tone": "professional",
            "expression_style": "图文并茂"
        }


async def process_blogger_style_callback(task_id: str, blogger_data: Dict[str, Any]) -> bool:
    """
    处理达人风格分析完成后的回调数据
    
    Args:
        task_id: 任务ID
        blogger_data: 从外部服务回调的数据
        
    Returns:
        处理是否成功
    """
    # 导入request_context模块来处理request_id
    from core.request_context import set_request_id
    logger = get_logger("agent.task_processor")
    
    try:
        logger.info(f"Processing callback for task_id: {task_id}")
        
        # 更新任务状态
        if task_id in async_tasks:
            # 在处理回调时恢复原始的request_id
            original_request_id = async_tasks[task_id].get("request_id")
            if original_request_id:
                set_request_id(original_request_id)
                logger.info(f"Restored original request_id: {original_request_id} for task_id: {task_id}")
            
            async_tasks[task_id]["status"] = "completed"
            async_tasks[task_id]["data"] = blogger_data
            # 设置事件，唤醒等待的协程
            if task_id in task_events:
                task_events[task_id].set()
                logger.info(f"Event set for task_id: {task_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing blogger style callback: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 更新任务状态为失败
        if task_id in async_tasks:
            # 在处理回调时恢复原始的request_id
            original_request_id = async_tasks[task_id].get("request_id")
            if original_request_id:
                set_request_id(original_request_id)
                logger.info(f"Restored original request_id: {original_request_id} for task_id: {task_id}")
            
            async_tasks[task_id]["status"] = "failed"
            async_tasks[task_id]["error"] = str(e)
            # 设置事件，唤醒等待的协程
            if task_id in task_events:
                task_events[task_id].set()
        
        return False


async def _process_blogger_data(task_id: str, blogger_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    处理达人数据并生成风格分析结果
    
    Args:
        task_id: 任务ID
        blogger_data: 达人数据
        
    Returns:
        处理结果
    """
    logger = get_logger("agent.task_processor")
    
    try:
        # 提取笔记数据 - 根据新的数据格式调整
        note_info_list = blogger_data.get("noteInfoList", [])
        if not note_info_list:
            logger.warning("No posts found in callback data")
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
        for i, post in enumerate(note_info_list, 1):
            content.append({"type": "text", "text": f"\n笔记 {i}:\n"})
            
            # 添加图片（如果存在）
            # 根据新的数据格式，图片URL可能在不同的字段中
            image_urls = post.get('pictureUrlList', [])
            if image_urls and isinstance(image_urls, list) and len(image_urls) > 0:
                # 过滤掉可能无法被外部API访问的图片URL
                valid_image_urls = []
                for image_url in image_urls:
                    # 检查URL是否包含可能引起访问问题的路径
                    if "notes_pre_post" not in image_url:
                        valid_image_urls.append(image_url)
                    else:
                        logger.warning(f"Skipping potentially inaccessible image URL: {image_url}")
                
                # 处理所有有效的图片
                for j, image_url in enumerate(valid_image_urls):
                    content.append({
                        "type": "text", 
                        "text": f"【达人笔记图片{j+1}】：\n"
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

        logger.info(f"Extracting blogger style for {len(note_info_list)} posts from callback")

        # 使用模型管理器调用视觉模型（通过支持特殊消息格式的新方法）
        model_manager = get_model_manager()
        
        # 构造视觉模型调用的消息格式
        messages = [{"role": "user", "content": content}]
        
        # 调用视觉模型（使用blogger_style_analysis任务类型）
        result = await model_manager.call_model_with_messages("blogger_style_analysis", messages)
        
        # 解析结果
        response = {
            "task_id": task_id,
            "blogger_style": result,
            "tone": "friendly" if "活泼" in result or "轻松" in result else "professional",
            "expression_style": "图文并茂"
        }
        
        logger.info(f"Extract blogger style result from callback: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing blogger data: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return {
            "task_id": task_id,
            "blogger_style": "达人风格分析: 处理数据时发生错误",
            "tone": "professional",
            "expression_style": "图文并茂"
        }


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取任务状态
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务状态信息
    """
    logger = get_logger("agent.task_processor")
    logger.info(f"Getting task status for task_id: {task_id}")
    
    if task_id in async_tasks:
        return async_tasks[task_id]
    else:
        return {
            "status": "not_found",
            "message": "任务不存在"
        }


# 注册所有任务
# task_processor.register_task("blogger_style_extractor", extract_blogger_style)  # 注册达人风格理解提取任务
task_processor.register_task("product_category_extractor", extract_product_category)  # 注册产品品类提取任务
