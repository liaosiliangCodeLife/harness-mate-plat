#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/10/28 09:36:06
@Author  : liaosiliang1234@126.com
@File    : share_agent_schema.py
"""
from flask_wtf import FlaskForm
from marshmallow import Schema, fields
from wtforms import IntegerField, StringField
from wtforms.validators import Length, NumberRange, Optional, StopValidation, ValidationError

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


class CreateShareAgentReq(FlaskForm):
    """创建分享请求，字段全部可选"""

    access_prompt = StrictStringField("access_prompt", validators=[
        Optional(),
        IsString("访问提示词必须是字符串"),
        Length(max=4096, message="访问提示词长度不能超过4096个字符"),
    ])
    access_pwd = StrictStringField("access_pwd", validators=[
        Optional(),
        IsString("访问密码必须是字符串"),
        Length(max=128, message="访问密码长度不能超过128个字符"),
    ])
    access_num = StrictIntegerField("access_num", validators=[
        Optional(),
        IsInt("对话次数上限必须是整数"),
        NumberRange(min=0, message="对话次数上限不能为负数"),
    ])
    shared_info = StrictStringField("shared_info", validators=[
        Optional(),
        IsString("分享说明必须是字符串"),
        Length(max=4096, message="分享说明长度不能超过4096个字符"),
    ])
    pay_url = StrictStringField("pay_url", validators=[
        Optional(),
        IsString("付费链接必须是字符串"),
        Length(max=1024, message="付费链接长度不能超过1024个字符"),
    ])


class UpdateShareAgentReq(FlaskForm):
    """修改分享请求，仅校验本次实际提交的字段"""

    access_prompt = StrictStringField("access_prompt", validators=[
        SkipIfMissing(),
        IsString("访问提示词必须是字符串"),
        Length(max=4096, message="访问提示词长度不能超过4096个字符"),
    ])
    access_pwd = StrictStringField("access_pwd", validators=[
        SkipIfMissing(),
        IsString("访问密码必须是字符串"),
        Length(max=128, message="访问密码长度不能超过128个字符"),
    ])
    access_num = StrictIntegerField("access_num", validators=[
        SkipIfMissing(),
        IsInt("对话次数上限必须是整数"),
        NumberRange(min=0, message="对话次数上限不能为负数"),
    ])
    shared_info = StrictStringField("shared_info", validators=[
        SkipIfMissing(),
        IsString("分享说明必须是字符串"),
        Length(max=4096, message="分享说明长度不能超过4096个字符"),
    ])
    pay_url = StrictStringField("pay_url", validators=[
        SkipIfMissing(),
        IsString("付费链接必须是字符串"),
        Length(max=1024, message="付费链接长度不能超过1024个字符"),
    ])

    def collect_updates(self) -> dict:
        """
        * @Author Leon-liao
        * @Function:
        collect_updates()
        * @Description //收集本次请求实际提交、且允许修改的分享字段
        * @Date :2026/10/28 09:36:06
        * @Param:
        无
        * @return：字段名到新值的字典；access_pwd 原样保留（空串表示改为免密）
        """
        update_data = {}
        if self.access_prompt.raw_data:
            update_data["access_prompt"] = self.access_prompt.data or ""
        if self.access_pwd.raw_data:
            update_data["access_pwd"] = self.access_pwd.data or ""
        if self.access_num.raw_data:
            update_data["access_num"] = self.access_num.data if self.access_num.data is not None else 0
        if self.shared_info.raw_data:
            update_data["shared_info"] = self.shared_info.data or ""
        if self.pay_url.raw_data:
            update_data["pay_url"] = self.pay_url.data or ""
        return update_data


class GetShareAgentsWithPageReq(PaginatorReq):
    """获取分享分页列表请求"""

    current_page = IntegerField("current_page", default=1, validators=[
        Optional(),
        NumberRange(min=1, max=9999, message="当前页数的范围在1-9999"),
    ])
    page_size = IntegerField("page_size", default=20, validators=[
        Optional(),
        NumberRange(min=1, max=50, message="每页数据的条数范围在1-50"),
    ])


class PaginatorResp(Schema):
    """分页信息响应"""

    current_page = fields.Integer(dump_default=0)
    page_size = fields.Integer(dump_default=0)
    total_page = fields.Integer(dump_default=0)
    total_record = fields.Integer(dump_default=0)


class GetShareAgentsWithPageResp(Schema):
    """获取分享分页列表响应"""

    id = fields.UUID(dump_default="")
    share_url = fields.String(dump_default="")
    has_password = fields.Boolean(dump_default=False)
    access_num = fields.Integer(dump_default=0)
    accessed_num = fields.Integer(dump_default=0)
    shared_info = fields.String(dump_default="")
    pay_url = fields.String(dump_default="")
    status = fields.Integer(dump_default=1)
    created_at = fields.Integer(dump_default=0)
    updated_at = fields.Integer(dump_default=0)


class GetShareAgentsWithPageListResp(Schema):
    """分享分页列表外壳"""

    list = fields.List(fields.Nested(GetShareAgentsWithPageResp), dump_default=[])
    paginator = fields.Nested(PaginatorResp)


class ShareAccessReq(FlaskForm):
    """换取分享态 token 请求"""

    pwd = StrictStringField("pwd", validators=[
        Optional(),
        IsString("访问密码必须是字符串"),
        Length(max=128, message="访问密码长度不能超过128个字符"),
    ])


class CreateShareConversationReq(FlaskForm):
    """创建访客会话请求"""

    title = StrictStringField("title", validators=[
        Optional(),
        IsString("会话标题必须是字符串"),
        Length(max=255, message="会话标题长度不能超过255个字符"),
    ])
