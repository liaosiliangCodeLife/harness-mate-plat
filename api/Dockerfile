# 使用Debian 12的Python 3.10版本作为基础镜像
FROM python:3.10-slim-bookworm AS base

# 将requirements.txt拷贝到根目录下（单独一层，依赖不变时不必重装）
COPY requirements.txt .

# 构建缓存并使用pip安装严格版本的requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/pkg -r requirements.txt

# 最终镜像从干净的 slim 起，避免 /pkg 和 /usr/local 各留一份依赖
FROM python:3.10-slim-bookworm AS production

# 设置工作目录
WORKDIR /app/api

# 定义环境变量
ENV FLASK_APP=app/http/app.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0
ENV NLTK_DATA=/app/api/internal/core/unstructured/nltk_data
ENV HF_ENDPOINT=https://hf-mirror.com

# 设置容器时区为中国标准时间，避免时区错误
ENV TZ Asia/Shanghai

# 依赖装到 /usr/local；源码只拷运行所需目录
COPY --from=base /pkg /usr/local
COPY app ./app
COPY config ./config
COPY internal ./internal
COPY pkg ./pkg

# 拷贝运行脚本并设置权限
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露5001端口
EXPOSE 5001

# 运行脚本并启动项目
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
