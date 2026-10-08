#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/23 22:05:00
@Author  : liaosiliang1234@126.com
@File    : server.py
"""
from sqlalchemy import (
    Column,
    UUID,
    String,
    DateTime,
    text,
    PrimaryKeyConstraint,
)

from internal.extension.database_extension import db
from internal.lib.helper import utc_now


class Server(db.Model):
    """服务器模型"""
    __tablename__ = "server"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_server_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 服务器记录主键，插入时由数据库生成 UUID
    gateway_url = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 网关 WebSocket 地址，客户端据此连接该网关
    gateway_key = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 网关访问密钥，客户端连接网关时用于鉴权
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        onupdate=utc_now,
    )  # 记录最后更新时间，字段变更时自动刷新
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))  # 记录创建时间，插入时由数据库写入当前时间
