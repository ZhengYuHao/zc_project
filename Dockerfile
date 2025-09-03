# 使用清华大学镜像源的Python 3.13作为基础镜像
FROM registry.docker.com.cn/python:3.13-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 配置pip使用清华大学镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements.txt文件
COPY agents_system/requirements.txt .

# 安装Python依赖（使用清华大学镜像源加速）
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY agents_system /app

# 创建日志目录（使用绝对路径确保正确性）
RUN mkdir -p /app/logs

# 创建卷目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8847

# 启动命令
CMD ["python", "main.py"]