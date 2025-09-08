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
            "target_audience_extractor": "product_highlights",
            "required_content_extractor": "product_highlights",
            "blogger_style_extractor": "blogger_link",
            "product_category_extractor": "product_highlights",
            "selling_points_extractor": "product_highlights",
            "product_endorsement_extractor": "product_highlights",
            "topic_extractor": "product_highlights"
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
    from models.doubao import call_doubao
    from utils.logger import get_logger
    
    logger = get_logger("agent.task_processor")
    
    # 构建提示词
    topic = request_data.get('topic', '')
    product_highlights = request_data.get('product_highlights', '')
    
    prompt = f"""# 角色
你是一位资深产品营销策略专家，拥有丰富的市场推广经验，擅长从复杂的产品信息中提炼出目标人群

## 技能
理解{product_highlights}提取出产品的目标人群

## 输出
目标人群：XX
"""
    
    logger.info(f"Extracting target audience for topic: {topic}")
    logger.info(f"Product highlights: {product_highlights}")
    logger.info(f"Prompt: {prompt}")
    
    try:
        # 调用豆包模型
        result = await call_doubao(prompt)
        logger.info(f"Doubao model response: {result}")
        
        # 解析结果
        lines = result.strip().split('\n')
        target_audience = ""
        logger.info(f"Parsing lines: {lines}")
        
        for line in lines:
            if line.startswith("目标人群："):
                target_audience = line[6:].strip()
                logger.info(f"Found target audience: {target_audience}")
        
        response = {
            "target_audience": target_audience if target_audience else f"根据'{topic}'和'{product_highlights}'分析的目标人群",
        }
        
        logger.info(f"Extract target audience result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting target audience: {str(e)}", exc_info=True)
        # 出现异常时返回默认值
        default_response = {
            "target_audience": f"根据'{topic}'和'{product_highlights}'分析的目标人群",
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response


async def extract_required_content(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取必提内容
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    from models.doubao import call_doubao
    from utils.logger import get_logger
    
    logger = get_logger("agent.task_processor")
    
    # 获取请求数据
    requirements = request_data.get('requirements', '')
    product_highlights = request_data.get('product_highlights', '')
    topic = request_data.get('topic', '')
    
    # 构建提示词
    prompt = f"""# 角色
你是一位资深产品营销策略专家，拥有丰富的市场推广经验，擅长从复杂的产品信息{product_highlights}中提炼出必提内容、目标人群和注意事项

# 内容方向
背景：在brief里面会有创作的必提内容内容方向，这些作为要求确保创作出图文大纲
必提内容包括关键词（可能是核心IP，比如联名信息、活动信息）等


# 输出结构
必提内容：XX
目标人群：XX
注意事项：XX
"""
    
    logger.info(f"Product highlights: {product_highlights}")
    logger.info(f"Prompt: {prompt}")
    
    try:
        # 调用豆包模型
        result = await call_doubao(prompt)
        logger.info(f"Doubao model response: {result}")
        
        # 解析结果
        lines = result.strip().split('\n')
        required_content = ""
        
        logger.info(f"Parsing lines: {lines}")
        
        for line in lines:
            if line.startswith("必提内容："):
                required_content = line[6:].strip()
                logger.info(f"Found required content: {required_content}")
            elif line.startswith("目标人群："):
                target_audience = line[6:].strip()
                logger.info(f"Found target audience: {target_audience}")
            elif line.startswith("注意事项："):
                notices = line[6:].strip()
                logger.info(f"Found notices: {notices}")
        
        response = {
            "required_content": required_content if required_content else f"必须包含的内容点: {requirements}",
            
        }
        
        logger.info(f"Extract required content result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting required content: {str(e)}", exc_info=True)
        # 出现异常时返回默认值
        default_response = {
            "required_content": f"必须包含的内容点: {requirements}",
            "content_type": "核心要点",
            "priority": "high"
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response


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
    from models.doubao import call_doubao
    from utils.logger import get_logger
    
    logger = get_logger("agent.task_processor")
    
    # 获取请求数据
    product_highlights = request_data.get('product_highlights', '')
    
    # 构建提示词
    prompt = f"""# 角色
你是一位资深产品营销策略专家，拥有丰富的市场推广经验，擅长从复杂的产品信息中提炼产品品类。

读取文件ProductHighlights，准确识别并深入理解种草产品信息，从中精准提炼出产品所处的二级或三级分类。
- 产品类目：着重提取产品所处的二级或三级分类。提取完成后，直接返回产品的二级或三级，甚至到四级分类（例如，制冰净水器属于厨卫家电 - 厨房家电 - 台式净饮机，只需返回最深一层的分类给我，台式净饮机）。

产品亮点：{product_highlights}

# 输出格式
产品品类：XX

## 限制
1. 读取数据时要精确提取关键信息，重点聚焦产品二级或三级分类。
2. 输出内容仅呈现产品的二级或三级分类，务必简洁明了。
3. 内容必须严格基于文件中的真实信息，严禁自行创作。
"""
    
    
    try:
        # 调用豆包模型
        result = await call_doubao(prompt)
        logger.info(f"Doubao model response: {result}")
        
        # 解析结果
        lines = result.strip().split('\n')
        product_category = ""
        
        logger.info(f"Parsing lines: {lines}")
        
        for line in lines:
            if line.startswith("产品品类："):
                product_category = line[6:].strip()
                logger.info(f"Found product category: {product_category}")
        
        response = {
            "product_category": product_category 
        }
        
        logger.info(f"Extract product category result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting product category: {str(e)}", exc_info=True)
        # 出现异常时返回默认值
        default_response = {
            "product_category": ""
            
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response


async def extract_selling_points(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    提取卖点信息
    
    Args:
        request_data: 请求数据
        
    Returns:
        处理结果
    """
    from models.doubao import call_doubao
    from utils.logger import get_logger
    
    logger = get_logger("agent.task_processor")
    
    # 获取请求数据
    product_highlights = request_data.get('product_highlights', '')
    topic = request_data.get('topic', '')
    
    # 构建提示词
    prompt = f"""# 角色
你是一位资深产品营销策略专家，拥有丰富的市场推广经验，擅长从复杂的产品信息{product_highlights}中提炼与卖点（利益点）有关的信息

# 卖点（利益点）
背景：在不同的业务场景下，博主需要在视频或图文笔记中植入介绍产品，产品会有一些功能（卖点）。
主打的产品功能＝卖点
必提的产品功能＝核心卖点
产品功能+对应使用场景（或者能解决的痛点）＝利益点
卖点是品牌视角的叫法，利益点是用户视角的叫法

# 流程
1. 识别卖点
理解卖点信息，提取出所有与卖点有关的信息

2. 区分卖点类型
结合卖点信息，理解卖点及卖点话术，区分卖点的类型，例如硬件参数型卖点、核心卖点、次要卖点。
特别的，次要卖点可能会有多个，卖点信息会要求创作时提到的数量或提到哪个，在输出次要卖点的时候要提及
 
* 注意：任务是从卖点信息中**提取**卖点（利益点），并且确认卖点的类型。不要自己理解出卖点，并且卖点的类型不是完全的，不要自己理解出来并没有的卖点
类型：核心卖点（利益点）、次要卖点

产品信息{product_highlights}

# 输出结构
卖点类型对应的卖点

===示例开始===
核心卖点：在神抢手怎么点都好。大牌、精选、好价。用心选品 只为省心。品质精选一口价。神抢手是精选、物超所值的品质外卖。
===示例结束===
"""
    

    logger.info(f"Product highlights: {product_highlights}")
    logger.info(f"Prompt: {prompt}")
    
    try:
        # 调用豆包模型
        result = await call_doubao(prompt)
        logger.info(f"Doubao model response: {result}")
        
        # 解析结果
        lines = result.strip().split('\n')
        core_selling_points = ""
        secondary_selling_points = ""
        
        logger.info(f"Parsing lines: {lines}")
        
        for line in lines:
            if line.startswith("核心卖点："):
                core_selling_points = line[6:].strip()
                logger.info(f"Found core selling points: {core_selling_points}")
            elif line.startswith("次要卖点："):
                secondary_selling_points = line[6:].strip()
                logger.info(f"Found secondary selling points: {secondary_selling_points}")
        
        response = {
            "selling_points": f"核心卖点: {core_selling_points}",
            "core_selling_points": core_selling_points,
            "secondary_selling_points": secondary_selling_points
        }
        
        logger.info(f"Extract selling points result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting selling points: {str(e)}", exc_info=True)
        # 出现异常时返回默认值
        default_response = {
            "selling_points": f"核心卖点: {product_highlights}",
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
    product_highlights = request_data.get('product_highlights', '')
    
    # 构建提示词
    prompt = f"""## 角色
你是一名专业的市场分析师，擅长从复杂的文本中提取关键的市场和信誉信息以及硬性产品数据。

## 指令 1
请从提供的产品信息{product_highlights}中，提取所有与"产品背书"相关的内容。产品背书是指任何能够增加产品可信度、权威性和吸引力的第三方认可或证明。

# 背书信息
名人/专家代言： 任何知名人士、行业专家、KOL、网红的使用推荐或公开称赞。
媒体报道与奖项： 产品被知名媒体、杂志、网站、电视台报道或提及；获得过的行业奖项、认证或排名（如"荣获红点设计奖"、"被《时代》杂志报道"）。
专业机构认证： 来自权威机构的安全认证、质量认证、环保认证等（如"通过FDA认证"、"获得UL安全认证"）。
合作伙伴： 与知名品牌、机构的合作或联名（如"与NASA联合开发"、"迪士尼官方授权"）。

## 指令2
请从提供的产品信息{product_highlights}中，提取所有与"产品数据"相关的内容
产品数据是只关于产品本身性能、规格、功能的客观、可量化的硬性指标


## 输出格式
**产品背书：** XX
**产品数据：** XX
"""
    
    logger.info(f"Product highlights: {product_highlights}")
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
        
        for line in lines:
            if line.startswith("**产品背书：**"):
                product_endorsement = line[8:].strip()
                logger.info(f"Found product endorsement: {product_endorsement}")
            elif line.startswith("**产品数据：**"):
                product_data = line[8:].strip()
                logger.info(f"Found product data: {product_data}")
        
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
    product_highlights = request_data.get('product_highlights', '')
    
    # 构建提示词
    prompt = f"""# 角色
你是一位资深产品营销策略专家，拥有丰富的市场推广经验，擅长从复杂的产品信息{product_highlights}中提炼出话题

# 任务
仔细理解信息ProductHighlights提取出该产品的话题
产品亮点：{product_highlights}

# 输出
话题：XX

# 限制
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
        
        for line in lines:
            if line.startswith("话题："):
                extracted_topic = line[3:].strip()
                logger.info(f"Found topic: {extracted_topic}")
        
        response = {
            "main_topic": extracted_topic 
        }
        
        logger.info(f"Extract topic result: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error extracting topic: {str(e)}", exc_info=True)
        # 出现异常时返回默认值
        default_response = {
            "main_topic": topic
        }
        logger.info(f"Returning default response: {default_response}")
        return default_response


# 注册所有任务
task_processor.register_task("target_audience_extractor", extract_target_audience)  # 注册目标人群提取任务
task_processor.register_task("required_content_extractor", extract_required_content)  # 注册必提内容提取任务
task_processor.register_task("blogger_style_extractor", extract_blogger_style)  # 注册达人风格理解提取任务
task_processor.register_task("product_category_extractor", extract_product_category)  # 注册产品品类提取任务
task_processor.register_task("selling_points_extractor", extract_selling_points)  # 注册卖点提取任务
task_processor.register_task("product_endorsement_extractor", extract_product_endorsement)  # 注册产品背书提取任务
task_processor.register_task("topic_extractor", extract_topic)  # 注册话题提取任务