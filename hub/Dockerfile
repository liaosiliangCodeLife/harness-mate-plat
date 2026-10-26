# syntax=docker/dockerfile:1
# This is the projet for brtc R&D Platform
# @Author Leon-liao <liaosiliang@alltman.com>
# @Description //Hub 服务镜像
# @File: Dockerfile
# @Time: 2026/10/23 10:39:00
# @All Rights Reserve By Brtc

FROM golang:1.25-alpine AS builder

# 国内构建走 GOPROXY 镜像，避免 proxy.golang.org 不可达
ENV GOPROXY=https://goproxy.cn,direct

WORKDIR /src

RUN sed -i 's#dl-cdn.alpinelinux.org#mirrors.aliyun.com#g' /etc/apk/repositories \
    && apk add --no-cache ca-certificates git

COPY go.mod ./
RUN go mod download

COPY . .

# 仓库里未提交 go.sum 时，先 tidy 生成依赖校验文件，保证 go build 可用
RUN go mod tidy

RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags "-s -w" \
    -o /out/hub \
    .

FROM alpine:3.21

RUN sed -i 's#dl-cdn.alpinelinux.org#mirrors.aliyun.com#g' /etc/apk/repositories \
    && apk add --no-cache ca-certificates wget \
    && adduser -D -g '' appuser

WORKDIR /app

COPY --from=builder /out/hub /app/hub

RUN chown -R appuser:appuser /app

ENV HUB_HTTP_ADDR=:8090 \
    REDIS_URL=redis://redis:6379/0 \
    API_BASE_URL=http://api:5001 \
    LOG_LEVEL=info

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -qO- "http://127.0.0.1:8090/healthz" || exit 1

USER appuser

ENTRYPOINT ["/app/hub"]
