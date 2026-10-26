#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : middleware.py
"""
from dataclasses import dataclass
from typing import Optional

from flask import Request
from injector import inject

from internal.exception import UnauthorizedException
from internal.model import Account
from internal.service import JwtService, AccountService


@inject
@dataclass
class Middleware:
    """应用中间件，可以重写request_loader与unauthorized_handler"""
    jwt_service: JwtService
    account_service: AccountService

    def request_loader(self, request: Request) -> Optional[Account]:
        """登录管理器的请求加载器"""
        # 1.单独为llmops路由蓝图创建请求加载器
        if request.blueprint == "llmops":
            # 2.校验获取access_token
            access_token = self._validate_credential(request)

            # 3.解析token信息
            payload = self.jwt_service.parse_token(access_token)
            account_id = payload.get("sub")
            account = self.account_service.get_account(account_id)
            if not account:
                raise UnauthorizedException("当前账户不存在，请重新登录")
            return account
        else:
            return None

    @classmethod
    def _validate_credential(cls, request: Request) -> str:
        """
        * @Author Leon-liao
        * @Function: _validate_credential(request: Request) -> str
        * @Description //校验凭证：优先从 Authorization 头取 Bearer token，没有头时再读 query 参数 token
        * @Date :2026/10/24 00:07:48
        * @Param: request: Flask 请求对象，Request。从请求头 Authorization 或查询参数 token 读取登录凭证
        * @return：access_token 字符串。请求头格式不对，或头和 query 都没有凭证时抛出 UnauthorizedException
        """
        # 1.提取请求头headers中的信息
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            # 1.1 EventSource 不能带自定义头，没有 Authorization 时用 query token 兜底
            token = request.args.get("token")
            if token:
                return token
            raise UnauthorizedException("该接口需要授权才能访问，请登录后尝试")

        # 2.请求信息中没有空格分隔符，则验证失败，Authorization: Bearer access_token
        if " " not in auth_header:
            raise UnauthorizedException("该接口需要授权才能访问，验证格式失败")

        # 3.分割授权信息，必须符合Bearer access_token
        auth_schema, credential = auth_header.split(None, 1)
        if auth_schema.lower() != "bearer":
            raise UnauthorizedException("该接口需要授权才能访问，验证格式失败")

        return credential
