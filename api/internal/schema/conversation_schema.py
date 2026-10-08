#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:13:39
@Author  : liaosiliang1234@126.com
@File    : conversation_schema.py
"""
from flask_wtf import FlaskForm
from marshmallow import Schema, fields, pre_dump
from sqlalchemy import inspect
from wtforms import Field, IntegerField, StringField
from wtforms.validators import (
    DataRequired,
    Length,
    NumberRange,
    Optional,
    StopValidation,
    ValidationError,
)

from internal.lib.helper import datetime_to_timestamp
from internal.model import Agent, Conversation, Server
from pkg.paginator import PaginatorReq


class IsString:
    """校验已提交的值必须是字符串，None 留给后续必填校验处理"""

    def __init__(self, message: str):
        """记录类型错误时返回的提示"""
        self.message = message

    def __call__(self, form, field):
        """非字符串输入时中断校验并返回类型错误"""
        if not field.raw_data:
            return
        value = field.raw_data[0]
        if value is None or isinstance(value, str):
            return
        raise ValidationError(self.message)


class IsInt:
    """校验已提交的值必须是整数，布尔值不算整数"""

    def __init__(self, message: str):
        """记录类型错误时返回的提示"""
        self.message = message

    def __call__(self, form, field):
        """非整数输入时中断校验并返回类型错误"""
        if not field.raw_data:
            return
        value = field.raw_data[0]
        if value is None or isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(self.message)


class SkipIfMissing:
    """请求未携带该字段时跳过后续校验，用于增量更新"""

    field_flags = {"optional": True}

    def __call__(self, form, field):
        """字段未出现在请求中时停止后续校验"""
        if not field.raw_data:
            field.errors[:] = []
            raise StopValidation()


class StrictStringField(StringField):
    """字符串字段：None 视为空字符串，字符串会去掉首尾空白"""

    def process_formdata(self, valuelist):
        """把提交值整理成去空白后的字符串"""
        if not valuelist:
            return
        value = valuelist[0]
        if value is None:
            self.data = ""
            return
        if not isinstance(value, str):
            self.data = value
            return
        self.data = value.strip()


class StrictIntegerField(IntegerField):
    """整数字段：只接受 JSON 整数，布尔值和其它类型留给校验器报错"""

    def process_formdata(self, valuelist):
        """保留原始类型，避免把 true 或字符串先转成整数"""
        if not valuelist:
            return
        value = valuelist[0]
        if isinstance(value, bool) or not isinstance(value, int):
            self.data = None
            return
        self.data = value


class DictField(Field):
    """字典字段，用于接收 JSON 对象"""

    def process_formdata(self, valuelist):
        """仅接受字典；空值保持为空，其它类型记为校验错误"""
        if not valuelist:
            return
        value = valuelist[0]
        if value is None or value == "":
            self.data = None
            return
        if not isinstance(value, dict):
            raise ValidationError("会话扩展信息必须是字典")
        self.data = value


class GetConversationResp(Schema):
    """会话信息响应，列表项共用"""

    id = fields.UUID(dump_default="")
    account_id = fields.UUID(dump_default="")
    agent_id = fields.UUID(dump_default="")
    bot_id = fields.String(dump_default="")
    peer_id = fields.String(dump_default="")
    thread_id = fields.String(dump_default="")
    ws_session_id = fields.String(dump_default="")
    gateway_url = fields.String(dump_default="")
    gateway_key = fields.String(dump_default="")
    title = fields.String(dump_default="")
    pinned = fields.Integer(dump_default=0)
    status = fields.Integer(dump_default=0)
    message_count = fields.Integer(dump_default=0)
    total_token_count = fields.Integer(dump_default=0)
    last_message_at = fields.Integer(allow_none=True, dump_default=None)
    last_message_preview = fields.String(dump_default="")
    conversation_info = fields.Dict(dump_default=dict)
    updated_at = fields.Integer(dump_default=0)
    created_at = fields.Integer(dump_default=0)

    @staticmethod
    def _agent_text(agent: Agent | None, column) -> str:
        """读取所属智能体的字符串字段，空值统一返回空字符串"""
        if agent is None:
            return ""
        value = getattr(agent, column.key)
        if value is None:
            return ""
        return value

    @staticmethod
    def _gateway_text(agent: Agent | None, column) -> str:
        """读取所属智能体所挂网关的字符串字段，网关不存在或值为空时返回空字符串"""
        if agent is None or agent.gateway is None:
            return ""
        value = getattr(agent.gateway, column.key, None)
        if value is None:
            return ""
        return value

    @staticmethod
    def _message_fields(data: Conversation):
        """
        * @Author Leon-liao
        * @Function:
        _message_fields(data)
        * @Description //优先取查询挂上的 message 表实时统计，读不到再回落到会话表冗余列
        * @Date :2026/09/30 22:28:00
        * @Param:
        data: 会话模型。info 里没有 live_message_stats 时回落到冗余列
        * @return：消息条数、Token 合计、最后一条消息时间、最后一条正文预览
        """
        stats = inspect(data).info.get("live_message_stats")
        if not isinstance(stats, dict):
            return (
                data.message_count or 0,
                data.total_token_count or 0,
                data.last_message_at,
                data.last_message_preview or "",
            )
        preview = stats.get("last_message_preview") or ""
        return (
            int(stats.get("message_count") or 0),
            int(stats.get("total_token_count") or 0),
            stats.get("last_message_at"),
            preview,
        )

    @pre_dump
    def process_data(self, data: Conversation, **kwargs):
        """把会话模型转成接口字段，时间转为时间戳，网关字段取自智能体关联的 server，消息统计取 message 表实时结果"""
        agent = data.agent
        message_count, total_token_count, last_message_at, last_message_preview = self._message_fields(data)
        return {
            "id": data.id,
            "account_id": data.account_id,
            "agent_id": data.agent_id,
            Agent.bot_id.key: self._agent_text(agent, Agent.bot_id),
            Agent.peer_id.key: self._agent_text(agent, Agent.peer_id),
            "thread_id": data.thread_id,
            "ws_session_id": data.ws_session_id,
            Server.gateway_url.key: self._gateway_text(agent, Server.gateway_url),
            Server.gateway_key.key: self._gateway_text(agent, Server.gateway_key),
            "title": data.title,
            "pinned": data.pinned,
            "status": data.status,
            "message_count": message_count,
            "total_token_count": total_token_count,
            "last_message_at": datetime_to_timestamp(last_message_at) if last_message_at else None,
            "last_message_preview": last_message_preview,
            "conversation_info": data.conversation_info if data.conversation_info is not None else {},
            "updated_at": datetime_to_timestamp(data.updated_at),
            "created_at": datetime_to_timestamp(data.created_at),
        }


class PaginatorResp(Schema):
    """分页信息响应"""

    current_page = fields.Integer(dump_default=0)
    page_size = fields.Integer(dump_default=0)
    total_page = fields.Integer(dump_default=0)
    total_record = fields.Integer(dump_default=0)


class GetConversationsWithPageResp(Schema):
    """获取会话分页列表响应"""

    list = fields.List(fields.Nested(GetConversationResp), dump_default=[])
    paginator = fields.Nested(PaginatorResp)


class CreateConversationResp(Schema):
    """创建会话响应"""

    id = fields.UUID()


class GetConversationsWithPageReq(PaginatorReq):
    """获取会话分页列表请求"""

    search_word = StringField("search_word", default="", validators=[
        Optional(),
        Length(max=255, message="搜索词长度不能超过255个字符"),
    ])
    page_size = IntegerField("page_size", default=20, validators=[
        Optional(),
        NumberRange(min=10, max=50, message="每页数据的条数范围在10-50"),
    ])


class CreateConversationReq(FlaskForm):
    """创建会话请求"""

    thread_id = StrictStringField("thread_id", validators=[
        IsString("会话线程标识必须是字符串"),
        DataRequired("会话线程标识不能为空"),
        Length(min=1, max=255, message="会话线程标识长度在1-255位"),
    ])
    title = StrictStringField("title", validators=[
        Optional(),
        IsString("会话标题必须是字符串"),
        Length(max=255, message="会话标题长度不能超过255个字符"),
    ])
    conversation_info = DictField("conversation_info", validators=[
        Optional(),
    ])


class UpdateConversationReq(FlaskForm):
    """修改会话请求，仅校验本次实际提交的字段"""

    title = StrictStringField("title", validators=[
        SkipIfMissing(),
        IsString("会话标题必须是字符串"),
        Length(max=255, message="会话标题长度不能超过255个字符"),
    ])
    pinned = StrictIntegerField("pinned", validators=[
        SkipIfMissing(),
        IsInt("是否置顶必须是整数"),
        NumberRange(min=0, max=1, message="是否置顶只能是0或1"),
    ])
    status = StrictIntegerField("status", validators=[
        SkipIfMissing(),
        IsInt("会话状态必须是整数"),
        NumberRange(min=-32768, max=32767, message="会话状态超出范围"),
    ])
    conversation_info = DictField("conversation_info", validators=[
        SkipIfMissing(),
    ])

    def collect_updates(self) -> dict:
        """收集本次请求实际提交、且允许修改的字段"""
        update_data = {}
        if self.title.raw_data:
            update_data["title"] = self.title.data or ""
        if self.pinned.raw_data:
            update_data["pinned"] = self.pinned.data
        if self.status.raw_data:
            update_data["status"] = self.status.data
        if self.conversation_info.raw_data:
            conversation_info = self.conversation_info.data
            if not isinstance(conversation_info, dict):
                conversation_info = {}
            update_data["conversation_info"] = conversation_info
        return update_data
