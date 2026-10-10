#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:01:39
@Author  : liaosiliang1234@126.com
@File    : agent_schema.py
"""
from uuid import UUID

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
    URL,
    ValidationError,
)

from internal.lib.helper import datetime_to_timestamp
from internal.model import Agent, Server
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


class IsUuid:
    """校验已提交的值必须是 UUID 字符串"""

    def __init__(self, message: str):
        """记录格式错误时返回的提示"""
        self.message = message

    def __call__(self, form, field):
        """非 UUID 字符串时中断校验并返回格式错误"""
        if not field.raw_data:
            return
        value = field.raw_data[0]
        if not isinstance(value, str):
            raise ValidationError(self.message)
        text = value.strip()
        if not text:
            raise ValidationError(self.message)
        try:
            UUID(text)
        except ValueError:
            raise ValidationError(self.message)


class IsAgentIdType:
    """校验标识类型只能是 peer_id、bot_id、ws_session_id、thread_id"""

    def __call__(self, form, field):
        """类型不在允许范围内时返回参数错误"""
        allowed = ("peer_id", "bot_id", "ws_session_id", "thread_id")
        if not field.raw_data:
            return
        if field.data in allowed:
            return
        raise ValidationError("标识类型只能是peer_id、bot_id、ws_session_id、thread_id")


AGENT_TYPES = ("HERMES", "DEEPSEEK_HARNESS", "OTHER")


class IsAgentType:
    """校验智能体类型只能是 HERMES、DEEPSEEK_HARNESS、OTHER"""

    def __call__(self, form, field):
        """空值交给 Optional；已填写的值转大写后必须在允许列表里"""
        if not field.raw_data:
            return
        value = field.data
        if value is None or (isinstance(value, str) and not value.strip()):
            return
        if not isinstance(value, str) or value.strip().upper() not in AGENT_TYPES:
            raise ValidationError("智能体类型只能是HERMES、DEEPSEEK_HARNESS、OTHER")


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
            raise ValidationError("智能体扩展信息必须是字典")
        self.data = value


class GetAgentResp(Schema):
    """智能体信息响应，列表项与详情共用"""

    id = fields.UUID(dump_default="")
    account_id = fields.UUID(dump_default="")
    peer_id = fields.String(dump_default="")
    bot_id = fields.String(dump_default="")
    name = fields.String(dump_default="")
    avatar = fields.String(dump_default="")
    agent_type = fields.String(dump_default="HERMES")
    agent_info = fields.Dict(dump_default=dict)
    status = fields.Integer(dump_default=0)
    conversation_count = fields.Integer(dump_default=0)
    total_token_count = fields.Integer(dump_default=0)
    last_seen_at = fields.Integer(allow_none=True, dump_default=None)
    gateway_url = fields.String(dump_default="")
    gateway_key = fields.String(dump_default="")
    updated_at = fields.Integer(dump_default=0)
    created_at = fields.Integer(dump_default=0)

    @staticmethod
    def _gateway_text(agent: Agent, column) -> str:
        """读取智能体所挂网关的字符串字段，网关不存在或值为空时返回空字符串"""
        gateway = agent.gateway if agent is not None else None
        if gateway is None:
            return ""
        value = getattr(gateway, column.key, None)
        if value is None:
            return ""
        return value

    @pre_dump
    def process_data(self, data: Agent, **kwargs):
        """把智能体模型转成接口字段，网关地址与密钥取自关联的 server，时间转为时间戳。

        last_seen_at 只取查询挂上的 message 表实时统计，不读 agent.last_seen_at 列。
        status 直接读 agent.status 列，不做时间窗计算。
        """
        last_seen_at = inspect(data).info.get("live_last_seen_at")
        return {
            "id": data.id,
            "account_id": data.account_id,
            "peer_id": data.peer_id,
            "bot_id": data.bot_id,
            "name": data.name,
            "avatar": data.avatar,
            "agent_type": data.agent_type or "HERMES",
            "agent_info": data.agent_info if data.agent_info is not None else {},
            "status": 1 if data.status == 1 else 0,
            "conversation_count": data.conversation_count,
            "total_token_count": data.total_token_count,
            "last_seen_at": datetime_to_timestamp(last_seen_at) if last_seen_at else None,
            "gateway_url": self._gateway_text(data, Server.gateway_url),
            "gateway_key": self._gateway_text(data, Server.gateway_key),
            "updated_at": datetime_to_timestamp(data.updated_at),
            "created_at": datetime_to_timestamp(data.created_at),
        }


class PaginatorResp(Schema):
    """分页信息响应"""

    current_page = fields.Integer(dump_default=0)
    page_size = fields.Integer(dump_default=0)
    total_page = fields.Integer(dump_default=0)
    total_record = fields.Integer(dump_default=0)


class GetAgentsWithPageResp(Schema):
    """获取智能体分页列表响应"""

    list = fields.List(fields.Nested(GetAgentResp), dump_default=[])
    paginator = fields.Nested(PaginatorResp)


class CreateAgentResp(Schema):
    """创建智能体响应"""

    id = fields.UUID()


class GetAgentsWithPageReq(PaginatorReq):
    """获取智能体分页列表请求"""

    search_word = StringField("search_word", default="", validators=[
        Optional(),
        Length(max=255, message="搜索词长度不能超过255个字符"),
    ])
    agent_type = StrictStringField("agent_type", validators=[
        Optional(),
        IsString("智能体类型必须是字符串"),
        Length(max=255, message="智能体类型长度不能超过255个字符"),
        IsAgentType(),
    ])
    page_size = IntegerField("page_size", default=20, validators=[
        Optional(),
        NumberRange(min=10, max=50, message="每页数据的条数范围在10-50"),
    ])


class CreateAgentReq(FlaskForm):
    """创建智能体请求"""

    bot_id = StrictStringField("bot_id", validators=[
        IsString("智能体业务标识必须是字符串"),
        DataRequired("智能体业务标识不能为空"),
        Length(min=1, max=255, message="智能体业务标识长度在1-255位"),
    ])
    peer_id = StrictStringField("peer_id", validators=[
        IsString("对端设备标识必须是字符串"),
        DataRequired("对端设备标识不能为空"),
        Length(min=1, max=255, message="对端设备标识长度在1-255位"),
    ])
    name = StrictStringField("name", validators=[
        IsString("智能体名称必须是字符串"),
        DataRequired("智能体名称不能为空"),
        Length(min=1, max=255, message="智能体名称长度在1-255位"),
    ])
    avatar = StrictStringField("avatar", validators=[
        Optional(),
        IsString("智能体头像必须是字符串"),
        Length(max=255, message="智能体头像长度不能超过255个字符"),
        URL(message="智能体头像必须是URL地址"),
    ])
    agent_type = StrictStringField("agent_type", validators=[
        Optional(),
        IsString("智能体类型必须是字符串"),
        Length(max=255, message="智能体类型长度不能超过255个字符"),
        IsAgentType(),
    ])
    agent_info = DictField("agent_info", validators=[
        Optional(),
    ])
    gateway_id = StrictStringField("gateway_id", validators=[
        IsString("网关标识必须是字符串"),
        IsUuid("网关标识格式不正确"),
    ])


class UpdateAgentReq(FlaskForm):
    """修改智能体请求，仅校验本次实际提交的字段"""

    name = StrictStringField("name", validators=[
        SkipIfMissing(),
        IsString("智能体名称必须是字符串"),
        DataRequired("智能体名称不能为空"),
        Length(min=1, max=255, message="智能体名称长度在1-255位"),
    ])
    avatar = StrictStringField("avatar", validators=[
        SkipIfMissing(),
        IsString("智能体头像必须是字符串"),
        DataRequired("智能体头像不能为空"),
        Length(max=255, message="智能体头像长度不能超过255个字符"),
        URL(message="智能体头像必须是URL地址"),
    ])
    agent_info = DictField("agent_info", validators=[
        SkipIfMissing(),
    ])
    gateway_id = StrictStringField("gateway_id", validators=[
        SkipIfMissing(),
        IsString("网关标识必须是字符串"),
        IsUuid("网关标识格式不正确"),
    ])

    def collect_updates(self) -> dict:
        """收集本次请求实际提交、且允许修改的字段"""
        update_data = {}
        if self.name.raw_data:
            update_data["name"] = self.name.data
        if self.avatar.raw_data:
            update_data["avatar"] = self.avatar.data
        if self.gateway_id.raw_data:
            update_data["gateway_id"] = self.gateway_id.data
        # 字段出现才更新。提交 {} 时 raw_data 为 [{}]，缺席时为 []，因此同时要求列表非空。
        submitted_agent_info = self.agent_info.raw_data
        if submitted_agent_info is not None and len(submitted_agent_info) > 0:
            agent_info = self.agent_info.data if isinstance(self.agent_info.data, dict) else {}
            update_data["agent_info"] = agent_info
        return update_data


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


class IsOnlineStatus:
    """校验在线状态只能是整数 0 或 1。0 不能交给 DataRequired，否则会被当成空值"""

    def __call__(self, form, field):
        """缺字段、非整数、以及 0/1 以外的值分别返回中文校验错误"""
        if not field.raw_data:
            raise ValidationError("在线状态不能为空")
        value = field.raw_data[0]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError("在线状态必须是整数")
        if value not in (0, 1):
            raise ValidationError("在线状态只能是0或1")


class UpdateAgentOnlineStatusReq(FlaskForm):
    """更新智能体在线状态请求"""

    status = StrictIntegerField("status", validators=[
        IsOnlineStatus(),
    ])


class GenerateAgentIdReq(FlaskForm):
    """生成智能体标识请求"""

    type = StrictStringField("type", validators=[
        DataRequired("标识类型不能为空"),
        IsAgentIdType(),
    ])
    agent_id = StrictStringField("agent_id", validators=[
        Optional(),
        IsUuid("智能体标识格式不正确"),
    ])
