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
        request_data: 请求数据，包含url参数
        
    Returns:
        处理结果
    """
    logger = get_logger("agent.task_processor")
    
    # 获取请求URL
    api_url = request_data.get('blogger_link')
    if not api_url:
        logger.error("Missing URL in request data")
        return {
            "blogger_style": "达人风格分析: 未提供API URL",
            "tone": "professional",
            "expression_style": "图文并茂"
        }
    
    try:
        # 准备POST请求数据
        post_data = {
            "size": 5,
            "publicTimeEnd": "2025-09-01 00:00:00",
            "publicTimeStart": "2025-06-01 00:00:00", 
            "userUuid": "671f2bc6000000001d0224aa"
        }
        
        # 发送POST请求获取达人笔记数据
        logger.info(f"Fetching blogger posts from: {api_url}")
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

        logger.info(f"Extracting blogger style for {len(blogger_posts)} posts")

        # 调用豆包视觉模型，传递内容数组而不是纯文本
        from models.doubao import get_doubao_model
        doubao_model = get_doubao_model()
        
        # 使用特殊的模型配置来调用视觉模型
        visual_model_config = {
            "model": "ep-20250520143333-8ghr9"  # 视觉模型ID
        }
        
        # 创建专门用于视觉分析的模型实例
        visual_doubao_model = doubao_model.__class__(visual_model_config)
        
        logger.info(f"Sending request to Doubao visual model with {len(content)} content items")
        
        # 调用视觉模型
        result = await visual_doubao_model._call_api("", messages=[{"role": "user", "content": content}])
        
        generated_text = result["choices"][0]["message"]["content"]
        logger.info(f"Doubao visual model response: {generated_text}")
        
        # 解析结果
        response = {
            "blogger_style": generated_text,
            "tone": "friendly" if "活泼" in generated_text or "轻松" in generated_text else "professional",
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


async def extract_product_endorsement(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取产品背书
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    from models.doubao import call_doubao
    from utils.logger import get_logger
    
    logger = get_logger("agent.task_processor")
    
    # 获取请求数据
    ProductHighlights = request_data.get('ProductHighlights', '')
    
    # 构建提示词
    prompt = f"""## 角色
你是一名专业的市场分析师，擅长从复杂的文本中提取关键的市场和信誉信息以及硬性产品数据。

## 输入
【卖点信息】：{ProductHighlights}

## 流程1：
请从提供的【卖点信息】中，提取所有与“产品背书”相关的内容。产品背书是指任何能够增加产品可信度、权威性和吸引力的第三方认可或证明。
### 背书信息
名人/专家代言： 任何知名人士、行业专家、KOL、网红的使用推荐或公开称赞。
媒体报道与奖项： 产品被知名媒体、杂志、网站、电视台报道或提及；获得过的行业奖项、认证或排名（如“荣获红点设计奖”、“被《时代》杂志报道”）。
专业机构认证： 来自权威机构的安全认证、质量认证、环保认证等（如“通过FDA认证”、“获得UL安全认证”）。
合作伙伴： 与知名品牌、机构的合作或联名（如“与NASA联合开发”、“迪士尼官方授权”）。

## 流程2
请从提供的【卖点信息】中，提取所有与“产品数据”相关的内容
产品数据是只关于产品本身性能、规格、功能的客观、可量化的硬性指标

## 输出格式
**产品背书：** XX
**产品数据：** XX
"""
    
    logger.info(f"Product highlights: {ProductHighlights}")
    logger.info(f"Prompt: {prompt}")
    
    try:
        # 调用豆包模型
        result = await call_doubao(prompt)
        logger.info(f"Doubao model response: {result}")
        
        # 解析结果
        lines = result.strip().split('\n')
        product_endorsement = ""
        product_data = ""
        
        logger.info(f"Parsing lines: {lines}")
        
        # 使用状态跟踪来处理跨多行的内容
        current_section = None  # None, "endorsement", or "data"
        endorsement_lines = []
        data_lines = []
        
        for line in lines:
            logger.debug(f"Processing line: '{line}'")
            logger.debug(f"Line bytes: {repr(line)}")
            
            # 检查是否是新的部分开始
            if line.startswith("**产品背书：**"):
                current_section = "endorsement"
                # 修复：更安全地提取内容，避免字符丢失
                prefix = "**产品背书：**"
                if line.startswith(prefix):
                    content = line[len(prefix):].strip()
                    if content:
                        endorsement_lines.append(content)
            elif line.startswith("**产品数据：**"):
                current_section = "data"
                # 修复：更安全地提取内容，避免字符丢失
                prefix = "**产品数据：**"
                if line.startswith(prefix):
                    content = line[len(prefix):].strip()
                    if content:
                        data_lines.append(content)
            elif line.startswith("- "):
                # 这是内容行
                if current_section == "endorsement":
                    endorsement_lines.append(line.strip())
                elif current_section == "data":
                    data_lines.append(line.strip())
            elif line.strip() == "":
                # 空行，不改变当前部分
                pass
            else:
                # 其他行，根据当前部分添加
                if current_section == "endorsement":
                    endorsement_lines.append(line.strip())
                elif current_section == "data":
                    data_lines.append(line.strip())
        
        # 合并行内容
        product_endorsement = "\n".join(endorsement_lines).strip()
        product_data = "\n".join(data_lines).strip()
        
        logger.info(f"Found product endorsement: {product_endorsement}")
        logger.info(f"Found product data: {product_data}")
        
        # 添加解析结果检查
        logger.debug(f"Parse results - Product endorsement: '{product_endorsement}', "
                    f"Product data: '{product_data}'")
        
        response = {
            "product_endorsement": product_endorsement,
            "product_data": product_data
        }
        
        logger.info(f"Extract product endorsement result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting product endorsement: {str(e)}", exc_info=True)
        # 出现异常时返回默认值
        default_response = {
            
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response


async def extract_topic(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取话题
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    from models.doubao import call_doubao
    from utils.logger import get_logger
    
    logger = get_logger("agent.task_processor")
    
    # 获取请求数据
    topic = request_data.get('topic', '')
    ProductHighlights = request_data.get('ProductHighlights', '')
    
    # 构建提示词
    prompt = f"""## 角色
你是一位资深产品营销策略专家，拥有丰富的市场推广经验，擅长从复杂的产品信息中提炼出话题

## 任务
仔细理解信息{ProductHighlights}提取出该产品的话题

## 输出
话题：XX

## 限制
只提取信息中的话题，不扩展
"""

    try:
        # 调用豆包模型
        result = await call_doubao(prompt)
        logger.info(f"Doubao model response: {result}")
        
        # 解析结果
        lines = result.strip().split('\n')
        extracted_topic = ""
        
        logger.info(f"Parsing lines: {lines}")
        
        # 使用状态跟踪来处理跨多行的内容
        current_section = None  # None, "topic"
        topic_lines = []
        
        for line in lines:
            logger.debug(f"Processing line: '{line}'")
            logger.debug(f"Line bytes: {repr(line)}")
            
            # 检查是否是新的部分开始
            if line.startswith("话题："):
                current_section = "topic"
                # 修复：更安全地提取内容，避免字符丢失
                prefix = "话题："
                if line.startswith(prefix):
                    content = line[len(prefix):].strip()
                    if content:
                        topic_lines.append(content)
            elif line.strip() == "":
                # 空行，不改变当前部分
                pass
            else:
                # 其他行，根据当前部分添加
                if current_section == "topic":
                    topic_lines.append(line.strip())
        
        # 合并行内容
        extracted_topic = "\n".join(topic_lines).strip()
        
        logger.info(f"Found topic: {extracted_topic}")
        
        # 添加解析结果检查
        logger.debug(f"Parse results - Extracted topic: '{extracted_topic}'")
        
        response = {
            "main_topic": extracted_topic 
        }
        
        logger.info(f"Extract topic result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting topic: {str(e)}")
        # 记录异常的详细信息
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        # 出现异常时返回默认值
        default_response = {
            "main_topic": topic
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
                results[task_name] = result
                self.logger.info(f"Task {task_name} completed successfully")
            except Exception as e:
                self.logger.error(f"Task {task_name} failed with error: {str(e)}")
                results[task_name] = {"error": str(e)}
        
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
task_processor.register_task("product_endorsement_extractor", extract_product_endorsement)  # 注册产品背书提取任务
task_processor.register_task("topic_extractor", extract_topic)  # 注册话题提取任务