#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 23:01:51
@Author  : liaosiliang1234@126.com
@File    : agent.py
"""
from sqlalchemy import (
    Column,
    UUID,
    String,
    Text,
    DateTime,
    text,
    ForeignKey,
    PrimaryKeyConstraint,
    UniqueConstraint,
    Index,
    Identity,
    SmallInteger,
    Integer,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from internal.extension.database_extension import db
from internal.lib.helper import utc_now


class Agent(db.Model):
    """智能体模型"""
    __tablename__ = "agent"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_agent_id"),
        UniqueConstraint("bot_id", name="uk_agent_bot_id"),
        Index("agent_account_id_idx", "account_id"),
        Index("agent_peer_id_idx", "peer_id"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 智能体记录主键，插入时由数据库生成 UUID
    account_id = Column(UUID, nullable=False)  # 所属账号 ID，关联 account.id，按账号隔离和查询智能体
    peer_id = Column(String(255), nullable=False)  # 对端设备标识，标记智能体挂在哪台网关或设备上，可按设备检索
    bot_id = Column(String(255), nullable=False)  # 智能体业务标识，全局唯一（uk_agent_bot_id），由对端上报
    name = Column(String(255), nullable=False)  # 智能体名称，用于列表和详情展示
    avatar = Column(String(255), nullable=False)  # 头像地址，前端展示智能体头像时使用
    agent_type = Column(String(255), nullable=False, server_default=text("'HERMES'::character varying"))  # 智能体接入类型：HERMES=Hermes Agent 插件接入，DEEPSEEK_HARNESS=DeepSeek harness 接入，OTHER=其它；默认 HERMES
    agent_info = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 智能体详细信息，JSON 扩展配置，默认空对象 {}
    status = Column(SmallInteger, nullable=False, server_default=text("0"))  # 在线状态：0=离线 1=在线，由对话结果写入，读取时直接用这一列
    conversation_count = Column(Integer, nullable=False, server_default=text("0"))  # 该智能体的会话数量，会话增减时维护的冗余计数
    total_token_count = Column(BigInteger, nullable=False, server_default=text("0"))  # 累计 Token 消耗，汇总该智能体下全部会话的用量
    last_seen_at = Column(DateTime, nullable=True)  # 列保留，读取接口不再使用。最后活跃按该智能体未删除会话中 max(message.created_at) 实时统计，没有消息则为空
    deleted_at = Column(DateTime, nullable=True)  # 软删除时间，NULL=未删除；有值表示已删除，列表查询需过滤
    gateway_id = Column(UUID, ForeignKey("server.id", name="fk_agent_gateway_id"), nullable=True)  # 所属网关主键，外键关联 server.id；NULL 表示尚未挂到网关
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        onupdate=utc_now,
    )  # 记录最后更新时间，字段变更时自动刷新
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))  # 记录创建时间，插入时由数据库写入当前时间
    gateway = relationship("Server", foreign_keys=[gateway_id], viewonly=True)  # 所属网关，按 gateway_id 只读关联 server 表


class Conversation(db.Model):
    """会话模型"""
    __tablename__ = "conversation"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_conversation_id"),
        UniqueConstraint("account_id", "thread_id", name="uk_conversation_account_thread"),
        Index("conversation_account_id_idx", "account_id"),
        Index("conversation_agent_id_idx", "agent_id"),
        Index("conversation_last_message_at_idx", "last_message_at"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 会话主键；创建接口由服务端写入 uuid4，未传入时才由数据库生成
    account_id = Column(UUID, nullable=False)  # 所属账号 ID，关联 account.id；与 thread_id 组成唯一约束 uk_conversation_account_thread
    agent_id = Column(UUID, ForeignKey("agent.id", name="fk_conversation_agent_id"), nullable=False)  # 所属智能体主键，外键关联 agent.id，按智能体查询会话
    thread_id = Column(String(255), nullable=False)  # 会话线程标识，同一账号下唯一，用于把消息归到同一条会话
    ws_session_id = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 网关连接会话标识，由所属智能体 peer_id 与会话 id 十六进制前 16 位拼接，客户端连接网关时写入 JWT
    status = Column(SmallInteger, nullable=False, server_default=text("0"))  # 会话状态，默认 0，用于筛选和流程控制
    online_at = Column(DateTime, nullable=True)  # 会话最近一次在线心跳时间；在线判定 = status=1 且该时间在 90 秒内
    title = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 会话标题，会话列表展示用，默认空字符串
    pinned = Column(SmallInteger, nullable=False, server_default=text("0"))  # 是否置顶：0=否 1=是，置顶的会话在列表中优先展示
    message_count = Column(Integer, nullable=False, server_default=text("0"))  # 冗余消息条数，写消息时维护；读取接口按 message 表实时统计
    total_token_count = Column(BigInteger, nullable=False, server_default=text("0"))  # 冗余 Token 合计，写消息时维护；读取接口按 message 表实时统计
    last_message_at = Column(DateTime, nullable=True)  # 冗余最后消息时间；读取接口按 message 表 seq 最大的一条实时统计，NULL 表示尚无消息
    last_message_preview = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 冗余最后消息预览；读取接口按 message 表 seq 最大的一条正文前 255 字实时统计
    conversation_info = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 会话详细信息，JSON 扩展数据，默认空对象 {}
    deleted_at = Column(DateTime, nullable=True)  # 软删除时间，NULL=未删除；有值表示已删除，列表查询需过滤
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        onupdate=utc_now,
    )  # 记录最后更新时间，字段变更时自动刷新
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))  # 记录创建时间，插入时由数据库写入当前时间
    agent = relationship(Agent, foreign_keys=[agent_id], viewonly=True)  # 所属智能体，按 agent_id 只读关联 agent 表


class Message(db.Model):
    """消息模型"""
    __tablename__ = "message"
    __table_args__ = (
        PrimaryKeyConstraint("id", name="pk_message_id"),
        UniqueConstraint(
            "conversation_id",
            "message_id",
            name="uk_message_conversation_message_id",
        ),
        Index("message_conversation_id_idx", "conversation_id"),
        Index("message_account_id_idx", "account_id"),
        Index("message_conversation_seq_idx", "conversation_id", "seq"),
    )

    id = Column(UUID, nullable=False, server_default=text("uuid_generate_v4()"))  # 消息记录主键，插入时由数据库生成 UUID
    conversation_id = Column(UUID, nullable=False)  # 所属会话 ID，关联 conversation.id，按会话查询消息
    account_id = Column(UUID, nullable=False)  # 所属账号 ID，关联 account.id，按账号隔离和查询消息
    message_type = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 消息类型，默认空字符串
    message_role = Column(String(255), nullable=False, server_default=text("''::character varying"))  # 消息角色，例如 user/assistant，默认空字符串
    message_content = Column(Text, nullable=False, server_default=text("''::text"))  # 消息正文内容，默认空字符串
    message_token = Column(Integer, nullable=False, server_default=text("0"))  # 本条消息消耗的 Token 数量，默认 0
    message_latency = Column(Integer, nullable=False, server_default=text("0"))  # 本条消息耗时，单位毫秒，默认 0
    message_id = Column(String(64), nullable=False, server_default=text("''::character varying"))  # 对端消息 ID，与 conversation_id 组成唯一约束，用于按消息幂等写入，默认空字符串
    message_status = Column(SmallInteger, nullable=False, server_default=text("1"))  # 消息状态：0=生成中 1=完成 2=失败，默认 1
    message_reasoning = Column(Text, nullable=False, server_default=text("''::text"))  # 模型推理过程，默认空字符串
    message_info = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))  # 消息扩展信息，JSON 对象，默认空对象 {}
    seq = Column(BigInteger, Identity(always=False), nullable=False)  # 写入序号，插入时由数据库生成，同一会话内用它确定消息先后；覆盖写入不改变该序号
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(0)"),
        onupdate=utc_now,
    )  # 记录最后更新时间，字段变更时自动刷新
    created_at = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP(0)"))  # 记录创建时间，插入时由数据库写入当前时间
