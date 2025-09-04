# 使用清华大学镜像源的Python 3.13作为基础镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 配置pip使用清华大学镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple




# 删除所有现有的 sources.list.d 配置文件
RUN rm -f /etc/apt/sources.list.d/*.list && \
    rm -f /etc/apt/sources.list.d/*.sources && \
    # 设置适用于 Debian Trixie 的阿里云镜像源
    echo "deb http://mirrors.aliyun.com/debian trixie main non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian trixie-updates main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian trixie-backports main non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security trixie-security main non-free non-free-firmware" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential && \
    rm -rf /var/lib/apt/lists/*





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