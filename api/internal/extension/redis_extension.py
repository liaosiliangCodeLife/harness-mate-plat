#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : redis_extension.py
"""
import redis
from flask import Flask
from redis.connection import Connection, SSLConnection

# redis客户端
redis_client = redis.Redis()


def init_app(app: Flask):
    """初始化redis客户端"""
    # 1.检测不同的场景使用不同的连接方式
    connection_class = Connection
    if app.config.get("REDIS_USE_SSL", False):
        connection_class = SSLConnection

    # 2.创建redis连接池
    redis_client.connection_pool = redis.ConnectionPool(**{
        "host": app.config.get("REDIS_HOST", "localhost"),
        "port": app.config.get("REDIS_PORT", 6379),
        "username": app.config.get("REDIS_USERNAME", None),
        "password": app.config.get("REDIS_PASSWORD", None),
        "db": app.config.get("REDIS_DB", 0),
        "encoding": "utf-8",
        "encoding_errors": "strict",
        "decode_responses": False
    }, connection_class=connection_class)

    app.extensions["redis"] = redis_client
