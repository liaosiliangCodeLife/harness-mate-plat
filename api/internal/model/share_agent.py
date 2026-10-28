#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/10/27 21:55:50
@Author  : liaosiliang1234@126.com
@File    : share_agent.py
"""
from sqlalchemy import (
    Column,
    UUID,
    String,
    Integer,
    DateTime,
    text,
    ForeignKey,
    PrimaryKeyConstraint,
    Index,
)

from internal.extension.database_extension import db
from internal.lib.helper import utc_now


class ShareAgent(db.Model):
    """分享智能体模型"""
    __tablename__ = "share_agent"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_share_agent_id"),
        Index("share_agent_agent_id_idx", "agent_id"),
        Index("share_agent_account_id_idx", "account_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 分享记录主键，插入时由数据库生成 UUID
    agent_id = Column(UUID, ForeignKey("agent.id", name="fk_share_agent_agent_id"), nullable=False)  # 被分享的智能体主键，外键关联 agent.id
    account_id = Column(UUID, nullable=False)  # 发起分享的账号 ID，关联 account.id，按账号隔离和查询分享
    access_prompt = Column(String(4096), nullable=False, server_default=text("''::character varying"))  # 访问提示词，落地页或访问前展示
    access_pwd = Column(String(128), nullable=False, server_default=text("''::character varying"))  # 访问密码，空串表示免密访问
    access_num = Column(Integer, nullable=False, server_default=text("0"))  # 限制对话次数（对话次数上限），0 表示不限制；访客累计对话达到上限后分享即失效
    shared_info = Column(String(4096), nullable=False, server_default=text("''::character varying"))  # 分享说明/落地页信息
    pay_url = Column(String(1024), nullable=False, server_default=text("''::character varying"))  # 付费链接，需要付费时跳转
    deleted_at = Column(DateTime, nullable=True)  # 软删除时间（停用分享），NULL=未删除；有值表示分享已停用，链接与访客 token 均失效
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        onupdate=utc_now,
    )  # 记录最后更新时间，字段变更时自动刷新
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))  # 记录创建时间，插入时由数据库写入当前时间
