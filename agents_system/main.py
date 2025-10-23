import os
import sys
import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import importlib

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from utils.logger import setup_logger, get_logger
from models.feishu import get_feishu_client
from models.model_manager import ModelManager
from config.model_config import load_model_config
from core.request_middleware import RequestIDMiddleware
from core.task_processor import process_blogger_style_callback, get_task_status

# 设置日志
setup_logger()
logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    debug=settings.DEBUG
)

# 添加请求ID中间件
app.add_middleware(RequestIDMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化模型管理器
model_config = load_model_config()
model_manager = ModelManager(model_config)

async def register_agents():
    """注册智能体"""
    try:
        # 动态导入并注册图文大纲生成智能体
        from agents.graphic_outline_agent import GraphicOutlineAgent
        graphic_agent = GraphicOutlineAgent(model_manager)
        # 保持原有路由路径，不添加前缀
        app.include_router(graphic_agent.router)
        logger.info("Registered GraphicOutlineAgent")
        
        # 动态导入并注册文本审核智能体
        from agents.text_reviewer import TextReviewerAgent
        text_reviewer = TextReviewerAgent(model_manager)
        # 保持原有路由路径，不添加前缀
        app.include_router(text_reviewer.router)
        logger.info("Registered TextReviewerAgent")
        
    except Exception as e:
        logger.error(f"Error registering agents: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Starting up application...")
    
    try:
        # 注册智能体
        await register_agents()
        
        # 初始化飞书客户端
        feishu_client = get_feishu_client()
        # 注意：FeishuClient没有initialize方法，所以不需要调用
        
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down application...")

@app.get("/")
async def root():
    """根路径"""
    return {"message": "Welcome to Agents System API"}

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

@app.post("/callback/blogger_style/{task_id}")
async def blogger_style_callback(task_id: str, request: Request):
    """处理达人风格分析的回调请求"""
    # 导入request_context模块来获取当前request_id
    from core.request_context import get_request_id
    try:
        # 获取回调数据
        callback_data = await request.json()
        current_request_id = get_request_id()
        logger.info(f"Received callback for task_id: {task_id}, current request_id: {current_request_id}")
        logger.info(f"Callback data: {callback_data}")
        
        # 处理回调数据
        result = await process_blogger_style_callback(task_id, callback_data)
        
        if result:
            return {"status": "success", "message": "Callback processed successfully"}
        else:
            return {"status": "error", "message": "Failed to process callback"}
    except Exception as e:
        logger.error(f"Error processing blogger style callback: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/task/status/{task_id}")
async def task_status(task_id: str):
    """查询任务状态"""
    status = get_task_status(task_id)
    return {"task_id": task_id, "status": status}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )