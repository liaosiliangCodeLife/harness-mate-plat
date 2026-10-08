#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 21:35:21
@Author  : liaosiliang1234@126.com
@File    : server_schema.py
"""
from marshmallow import Schema, fields, pre_dump

from internal.lib.helper import datetime_to_timestamp
from internal.model import Server


class GetServerResp(Schema):
    """获取 WS 网关信息响应"""
    id = fields.UUID(dump_default="")
    gateway_url = fields.String(dump_default="")
    gateway_key = fields.String(dump_default="")
    updated_at = fields.Integer(dump_default=0)
    created_at = fields.Integer(dump_default=0)

    @pre_dump
    def process_data(self, data: Server, **kwargs):
        """把网关模型转成接口字段，空值统一返回空字符串，时间转为时间戳"""
        return {
            "id": data.id,
            "gateway_url": data.gateway_url or "",
            "gateway_key": data.gateway_key or "",
            "updated_at": datetime_to_timestamp(data.updated_at),
            "created_at": datetime_to_timestamp(data.created_at),
        }
