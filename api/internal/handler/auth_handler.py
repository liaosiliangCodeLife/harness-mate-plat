#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : auth_handler.py
"""
from dataclasses import dataclass

from flask import request
from flask_login import logout_user, login_required, current_user
from injector import inject

from internal.schema.auth_schema import PasswordLoginReq, PasswordLoginResp, RegisterReq, SendRegisterCodeReq
from internal.service import AccountService
from pkg.response import success_message, validate_error_json, success_json



def _validate_json_object():
    """POST 携带请求体时必须是 JSON 对象，否则返回参数校验错误"""
    if not request.data and not request.is_json:
        return None
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return validate_error_json({"body": ["请求体必须是JSON对象"]})
    return None


@inject
@dataclass
class AuthHandler:
    """LLMOps平台自有授权认证处理器"""
    account_service: AccountService

    def password_login(self):
        """账号密码登录"""
        # 1.提取请求并校验数据
        req = PasswordLoginReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.调用服务登录账号
        credential = self.account_service.password_login(req.email.data, req.password.data)

        # 3.创建响应结构并返回
        resp = PasswordLoginResp()

        return success_json(resp.dump(credential))

    @login_required
    def logout(self):
        """退出登录，清除服务端会话并提示前端清除授权凭证"""
        self.account_service.clear_login_session(current_user.get_id())
        logout_user()
        return success_message("退出登陆成功")

    def send_register_code(self):
        """
        * @Author Leon-liao
        * @Function: send_register_code()
        * @Description //免登录发送注册验证码
        * @Date :2026/10/07 12:01:30
        * @Param: 无。JSON 入参 email 为注册邮箱
        * @return：成功时 data.expire_in 为 900
        """
        # 1.请求体必须是 JSON 对象，再按字段校验
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = SendRegisterCodeReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.生成验证码、写入 Redis 并发送邮件
        expire_in = self.account_service.send_register_code(req.email.data)
        return success_json({"expire_in": expire_in})

    def register(self):
        """
        * @Author Leon-liao
        * @Function: register()
        * @Description //免登录用邮箱验证码注册账号
        * @Date :2026/10/07 12:01:30
        * @Param: 无。JSON 入参 email、code、password、password_confirm
        * @return：注册成功提示，不返回 token
        """
        # 1.请求体必须是 JSON 对象，再按字段校验
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = RegisterReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.核对验证码并创建账号
        self.account_service.register_by_email(req.email.data, req.code.data, req.password.data)
        return success_message("注册成功")
