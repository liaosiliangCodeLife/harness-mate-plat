#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : auth_schema.py
"""
from flask_wtf import FlaskForm
from marshmallow import Schema, fields
from wtforms import StringField
from wtforms.validators import DataRequired, Email, EqualTo, Length, regexp

from pkg.password import password_pattern


class PasswordLoginReq(FlaskForm):
    """账号密码登录请求结构"""
    email = StringField("email", validators=[
        DataRequired("登录邮箱不能为空"),
        Email("登录邮箱格式错误"),
        Length(min=5, max=254, message="登录邮箱长度在5-254个字符"),
    ])
    password = StringField("password", validators=[
        DataRequired("账号密码不能为空"),
        regexp(regex=password_pattern, message="密码最少包含一个字母，一个数字，并且长度为8-16")
    ])


class PasswordLoginResp(Schema):
    """账号密码授权认证响应结构"""
    access_token = fields.String()
    expire_at = fields.Integer()


class SendRegisterCodeReq(FlaskForm):
    """发送注册验证码请求"""
    email = StringField("email", validators=[
        DataRequired("邮箱不能为空"),
        Email("邮箱格式错误"),
        Length(min=5, max=254, message="邮箱长度在5-254个字符"),
    ])


class RegisterReq(FlaskForm):
    """邮箱注册请求"""
    email = StringField("email", validators=[
        DataRequired("邮箱不能为空"),
        Email("邮箱格式错误"),
        Length(min=5, max=254, message="邮箱长度在5-254个字符"),
    ])
    code = StringField("code", validators=[
        DataRequired("验证码不能为空"),
    ])
    password = StringField("password", validators=[
        DataRequired("密码不能为空"),
        regexp(regex=password_pattern, message="密码长度为8-16位，且必须同时包含字母和数字"),
    ])
    password_confirm = StringField("password_confirm", validators=[
        DataRequired("确认密码不能为空"),
        EqualTo("password", message="两次输入的密码不一致"),
    ])

