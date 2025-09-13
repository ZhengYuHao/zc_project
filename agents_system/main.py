import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from core.registry import registry
from agents.text_reviewer import TextReviewerAgent
from agents.graphic_outline_agent import GraphicOutlineAgent
from core.feishu_callback import router as feishu_router
from utils.logger import get_logger
from core.request_middleware import RequestIDMiddleware

logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    debug=settings.DEBUG
)

# 添加请求ID中间件（放在最外层）
app.add_middleware(RequestIDMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册智能体
text_reviewer = TextReviewerAgent()
graphic_outline = GraphicOutlineAgent()
registry.register("text_reviewer", TextReviewerAgent)
registry.register("graphic_outline", GraphicOutlineAgent)

# 将智能体路由添加到应用
app.include_router(text_reviewer.router)
app.include_router(graphic_outline.router)
# 添加飞书回调路由
app.include_router(feishu_router)

# 添加根路径
@app.get("/")
async def root():
    return {
        "message": "Welcome to Agents System",
        "version": settings.PROJECT_VERSION,
        "agents": registry.list_agents()
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )