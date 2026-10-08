#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 21:35:21
@Author  : liaosiliang1234@126.com
@File    : server_handler.py
"""
from dataclasses import dataclass

from flask_login import login_required
from injector import inject

from internal.schema.server_schema import GetServerResp
from internal.service import ServerService
from pkg.response import success_json


@inject
@dataclass
class ServerHandler:
    """WS 网关处理器"""
    server_service: ServerService

    @login_required
    def get_open_server(self):
        """
        * @Author Leon-liao
        * @Function: get_open_server()
        * @Description //需要登录后返回全局最近更新的一条 WS 网关，不按当前账号过滤
        * @Date :2026/10/07 14:21:00
        * @Param: 无。请求头需要有效的 Authorization
        * @return：有记录时结构与 GetServerResp 相同；没有记录时 data 为空对象
        """
        server = self.server_service.get_global_latest_server()
        if server is None:
            return success_json({})
        return success_json(GetServerResp().dump(server))

    @login_required
    def get_open_servers(self):
        """
        * @Author Leon-liao
        * @Function: get_open_servers()
        * @Description //需要登录后返回全部 WS 网关，不按当前账号过滤
        * @Date :2026/10/07 14:30:00
        * @Param: 无。请求头需要有效的 Authorization
        * @return：data.list 为 GetServerResp 数组，没有记录时 list 为空数组
        """
        servers = self.server_service.get_all_servers()
        return success_json({
            "list": GetServerResp(many=True).dump(servers),
        })
