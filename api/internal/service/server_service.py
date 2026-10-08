#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 21:35:21
@Author  : liaosiliang1234@126.com
@File    : server_service.py
"""
from dataclasses import dataclass

from injector import inject

from internal.model import Server
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService


@inject
@dataclass
class ServerService(BaseService):
    """WS 网关服务"""
    db: SQLAlchemy

    def get_global_latest_server(self) -> Server | None:
        """
        * @Author Leon-liao
        * @Function: get_global_latest_server()
        * @Description //按 updated_at 倒序取全库最近一条网关，不按账号过滤
        * @Date :2026/10/07 14:05:00
        * @Param: 无
        * @return：有记录时返回 Server，一条都没有时返回 None
        """
        return self.db.session.query(Server).order_by(
            Server.updated_at.desc(),
        ).first()

    def get_all_servers(self) -> list[Server]:
        """
        * @Author Leon-liao
        * @Function: get_all_servers()
        * @Description //返回全部 WS 网关，不按账号过滤；按 created_at 升序、id 升序，顺序稳定
        * @Date :2026/10/07 14:30:00
        * @Param: 无
        * @return：Server 列表，没有记录时为空列表
        """
        return self.db.session.query(Server).order_by(
            Server.created_at.asc(),
            Server.id.asc(),
        ).all()
