#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //发送聊天消息的请求校验
* @File: chat_schema.py
* @Time: 2026/10/23 23:21:05
* @All Rights Reserve By Brtc
"""
from flask_wtf import FlaskForm
from wtforms import Field, StringField
from wtforms.validators import DataRequired, Length, StopValidation


class IsString:
    """
    * @Author Leon-liao
    * @Function: IsString(message: str)
    * @Description //校验已提交的值必须是字符串，None 留给后续必填校验处理
    * @Date :2026/10/23 23:21:05
    * @Param: message: 类型错误时返回的提示，字符串
    * @return：校验器实例
    """

    def __init__(self, message: str):
        """
        * @Author Leon-liao
        * @Function: __init__(message: str)
        * @Description //记录类型错误时返回的提示
        * @Date :2026/10/23 23:21:05
        * @Param: message: 类型错误提示，字符串
        * @return：无
        """
        self.message = message

    def __call__(self, form, field):
        """
        * @Author Leon-liao
        * @Function: __call__(form, field)
        * @Description //非字符串输入时中断后续校验并返回类型错误
        * @Date :2026/10/23 23:21:05
        * @Param: form: 当前 FlaskForm；field: 正在校验的字段
        * @return：无。类型不符时抛出 StopValidation
        """
        if not field.raw_data:
            return
        value = field.raw_data[0]
        if value is None or isinstance(value, str):
            return
        raise StopValidation(self.message)


class StrictStringField(StringField):
    """
    * @Author Leon-liao
    * @Function: StrictStringField
    * @Description //字符串字段：None 视为空字符串，字符串会去掉首尾空白
    * @Date :2026/10/23 23:21:05
    * @Param: 无
    * @return：字段类
    """

    def process_formdata(self, valuelist):
        """
        * @Author Leon-liao
        * @Function: process_formdata(valuelist)
        * @Description //把提交值整理成去空白后的字符串
        * @Date :2026/10/23 23:21:05
        * @Param: valuelist: 表单提交的原始值列表
        * @return：无。结果写入 self.data
        """
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


class OptionalListField(Field):
    """
    * @Author Leon-liao
    * @Function: OptionalListField
    * @Description //可选列表。缺失、空列表和 null 都视为没有值，有元素时按原样收下
    * @Date :2026/10/25 22:24:33
    * @Param: 无
    * @return：字段类
    """

    def process_formdata(self, valuelist):
        """
        * @Author Leon-liao
        * @Function: process_formdata(valuelist)
        * @Description //JSON 数组会被拆成多项，这里再拼回列表。不做元素类型校验
        * @Date :2026/10/25 22:24:33
        * @Param: valuelist: 表单提交的原始值列表
        * @return：无。结果写入 self.data，没有值时为 None
        """
        if not valuelist or (len(valuelist) == 1 and valuelist[0] in (None, "")):
            self.data = None
            return
        self.data = list(valuelist)


class SendMessageReq(FlaskForm):
    """发送聊天消息请求。agent_id 与 thread_id 来自 URL，正文和消息标识必填，附件可选"""

    text = StrictStringField("text", validators=[
        IsString("消息内容必须是字符串"),
        DataRequired("消息内容不能为空"),
        Length(max=4000, message="消息内容长度不能超过4000个字符"),
    ])
    message_id = StrictStringField("message_id", validators=[
        IsString("消息标识必须是字符串"),
        DataRequired("消息标识不能为空"),
        Length(min=1, max=64, message="消息标识长度不能超过64个字符"),
    ])
    files = OptionalListField("files")
