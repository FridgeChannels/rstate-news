# rstate-news 采集服务 - 服务器运行用
# 基于 Playwright 官方 Python 镜像（已含 Chromium 及系统依赖）
# 构建: docker build -t rstate-news .
# 运行: docker run --rm -it --env-file .env --ipc=host rstate-news
#       --ipc=host 为 Chromium 在容器内稳定运行所必需，见 README「Docker 与 Playwright」

# 使用 jammy (Ubuntu 22.04)；v1.40.0-noble 可能不存在，与 requirements.txt 中 playwright==1.40.0 对应
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 使用非 root 用户运行（可选，如需 root 可注释掉相关行）
ARG APP_USER=app
ARG APP_HOME=/app

# 安装 xvfb，供 Realtor 等使用 headless=False 时使用虚拟显示
RUN apt-get update \
    && apt-get install -y --no-install-recommends xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

# 先复制依赖，利用层缓存
COPY requirements.txt .

# 安装 Python 依赖（镜像内已含 Playwright 浏览器，无需再 playwright install）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY config/ ./config/
COPY database/ ./database/
COPY notifications/ ./notifications/
COPY scrapers/ ./scrapers/
COPY scheduler/ ./scheduler/
COPY utils/ ./utils/
COPY main.py .

# 创建日志目录（配置里会写 logs/scraper.log）
RUN mkdir -p logs

# 使用 xvfb 提供虚拟显示，避免 Realtor 等 headed 模式在无界面环境下报错
# 启动前清理可能存在的旧锁文件，避免容器重启时报 display 99 already active
ENV DISPLAY=:99
CMD ["sh", "-c", "rm -f /tmp/.X99-lock 2>/dev/null; Xvfb :99 -screen 0 1920x1080x24 & sleep 2 && exec python main.py"]
