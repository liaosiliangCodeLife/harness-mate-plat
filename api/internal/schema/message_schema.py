#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:22:49
@Author  : liaosiliang1234@126.com
@File    : message_schema.py
"""
from uuid import UUID

from flask_wtf import FlaskForm
from marshmallow import Schema, fields, pre_dump
from wtforms import Field, IntegerField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from internal.lib.helper import datetime_to_timestamp
from internal.model import Message


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


class IsUuid:
    """校验已提交的值必须是 UUID 字符串，空值留给可选校验处理"""

    def __init__(self, message: str):
        """记录格式错误时返回的提示"""
        self.message = message

    def __call__(self, form, field):
        """非 UUID 字符串时中断校验并返回格式错误"""
        if not field.raw_data:
            return
        value = field.raw_data[0]
        if value is None:
            return
        if not isinstance(value, str):
            raise ValidationError(self.message)
        text = value.strip()
        if not text:
            return
        try:
            UUID(text)
        except ValueError:
            raise ValidationError(self.message) from None


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
            raise ValidationError("消息扩展信息必须是字典")
        self.data = value


class GetMessageResp(Schema):
    """消息信息响应"""

    id = fields.UUID(dump_default="")
    conversation_id = fields.UUID(dump_default="")
    account_id = fields.UUID(dump_default="")
    message_type = fields.String(dump_default="")
    message_role = fields.String(dump_default="")
    message_content = fields.String(dump_default="")
    message_token = fields.Integer(dump_default=0)
    message_latency = fields.Integer(dump_default=0)
    message_id = fields.String(dump_default="")
    message_status = fields.Integer(dump_default=1)
    message_reasoning = fields.String(dump_default="")
    message_info = fields.Dict(dump_default=dict)
    updated_at = fields.Integer(dump_default=0)
    created_at = fields.Integer(dump_default=0)

    @pre_dump
    def process_data(self, data: Message, **kwargs):
        """把消息模型转成接口字段，时间转为时间戳"""
        return {
            "id": data.id,
            "conversation_id": data.conversation_id,
            "account_id": data.account_id,
            "message_type": data.message_type,
            "message_role": data.message_role,
            "message_content": data.message_content,
            "message_token": data.message_token,
            "message_latency": data.message_latency,
            "message_id": data.message_id or "",
            "message_status": data.message_status if data.message_status is not None else 1,
            "message_reasoning": data.message_reasoning or "",
            "message_info": data.message_info if isinstance(data.message_info, dict) else {},
            "updated_at": datetime_to_timestamp(data.updated_at),
            "created_at": datetime_to_timestamp(data.created_at),
        }


class GetMessagesWithPageResp(Schema):
    """获取消息列表响应"""

    list = fields.List(fields.Nested(GetMessageResp), dump_default=[])
    has_more = fields.Boolean(dump_default=False)
    next_cursor = fields.String(dump_default="")


class CreateMessageResp(Schema):
    """创建消息响应"""

    id = fields.UUID()


class GetMessagesWithPageReq(FlaskForm):
    """获取消息列表请求，支持最近 N 轮或从某条消息向上加载"""

    turns = IntegerField("turns", validators=[
        Optional(),
        NumberRange(min=1, max=50, message="最近轮数范围在1-50"),
    ])
    limit = IntegerField("limit", default=20, validators=[
        Optional(),
        NumberRange(min=1, max=50, message="每次加载条数范围在1-50"),
    ])
    before = StringField("before", validators=[
        Optional(),
        IsUuid("before必须是消息id"),
    ])


class CreateMessageReq(FlaskForm):
    """创建消息请求，message_id 作为会话内幂等键"""

    message_id = StrictStringField("message_id", validators=[
        IsString("消息标识必须是字符串"),
        DataRequired("消息标识不能为空"),
        Length(min=1, max=64, message="消息标识长度在1-64位"),
    ])
    message_role = StrictStringField("message_role", validators=[
        IsString("消息角色必须是字符串"),
        DataRequired("消息角色不能为空"),
        Length(min=1, max=255, message="消息角色长度在1-255位"),
    ])
    message_content = StrictStringField("message_content", validators=[
        IsString("消息正文必须是字符串"),
        DataRequired("消息正文不能为空"),
    ])
    message_type = StrictStringField("message_type", validators=[
        Optional(),
        IsString("消息类型必须是字符串"),
        Length(max=255, message="消息类型长度不能超过255个字符"),
    ])
    message_token = StrictIntegerField("message_token", default=0, validators=[
        Optional(),
        IsInt("消息Token数量必须是整数"),
        NumberRange(min=0, max=2147483647, message="消息Token数量超出范围"),
    ])
    message_latency = StrictIntegerField("message_latency", default=0, validators=[
        Optional(),
        IsInt("消息耗时必须是整数"),
        NumberRange(min=0, max=2147483647, message="消息耗时超出范围"),
    ])
    message_status = StrictIntegerField("message_status", default=1, validators=[
        Optional(),
        IsInt("消息状态必须是整数"),
        NumberRange(min=0, max=2, message="消息状态只能是0、1或2"),
    ])
    message_reasoning = StrictStringField("message_reasoning", validators=[
        Optional(),
        IsString("消息推理内容必须是字符串"),
    ])
    message_info = DictField("message_info", validators=[
        Optional(),
    ])
