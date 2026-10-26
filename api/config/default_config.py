#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : default_config.py
"""
# 应用默认配置项
DEFAULT_CONFIG = {
    # wft配置
    "WTF_CSRF_ENABLED": "False",

    # SQLAlchemy数据库配置
    "SQLALCHEMY_DATABASE_URI": "",
    "SQLALCHEMY_POOL_SIZE": 30,
    "SQLALCHEMY_POOL_RECYCLE": 3600,
    "SQLALCHEMY_ECHO": "True",

    # Redis数据库配置
    "REDIS_HOST": "localhost",
    "REDIS_PORT": 6379,
    "REDIS_USERNAME": "",
    "REDIS_PASSWORD": "",
    "REDIS_DB": 0,
    "REDIS_USE_SSL": "False",

    # Hub 转发配置
    "HUB_BASE_URL": "http://hub:8090",
    "INTERNAL_TOKEN": "",

    # 网关配置：新建智能体时写入专属 Server 记录的 WebSocket 地址
    "WS_GATEWAY_URL": "wss://ws-agent.alltman.com:1443/ws",
}
