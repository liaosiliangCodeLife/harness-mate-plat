#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/19 15:38
@Author  : liaosiliang1234@126.com
@File    : upload_file_handler.py
"""
from dataclasses import dataclass

from flask_login import login_required, current_user
from injector import inject
from sqlalchemy.orm import joinedload

from internal.exception import FailException, NotFoundException
from internal.model import Agent, Conversation
from internal.schema.upload_file_schema import (
    OpenUploadFileReq,
    UploadFileReq,
    UploadFileResp,
    UploadImageReq,
)
from internal.service import AccountService, CosService
from pkg.response import validate_error_json, success_json
from pkg.sqlalchemy import SQLAlchemy


@inject
@dataclass
class UploadFileHandler:
    """上传文件处理器"""
    cos_service: CosService
    account_service: AccountService
    db: SQLAlchemy

    @login_required
    def upload_file(self):
        """上传文件/文档"""
        # 1.构建请求并校验
        req = UploadFileReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.调用服务上传文件并获取记录
        upload_file = self.cos_service.upload_file(req.file.data, False, current_user)

        # 3.构建响应并返回，补上文件可访问 URL
        resp = UploadFileResp()
        data = resp.dump(upload_file)
        data["url"] = self.cos_service.get_file_url(upload_file.key)
        return success_json(data)

    @login_required
    def upload_image(self):
        """上传图片"""
        # 1.构建请求并校验
        req = UploadImageReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.调用服务并上传文件
        upload_file = self.cos_service.upload_file(req.file.data, True, current_user)

        # 3.获取图片的实际URL地址
        image_url = self.cos_service.get_file_url(upload_file.key)

        return success_json({"image_url": image_url})

    def upload_open_file(self):
        """
        * @Author Leon-liao
        * @Function: upload_open_file()
        * @Description //免登录上传文件。用 bot_id、bot_key、session_id 校验后，把文件挂到智能体所属账号
        * @Date :2026/10/07 10:25:00
        * @Param: 无。参数来自 multipart/form-data：file 为上传文件，bot_id 为智能体业务标识，bot_key 为网关密钥，session_id 为会话网关连接标识
        * @return：成功时只返回文件可访问 url
        """
        # 1.校验文件和三个身份字段，任一为空时走参数校验失败
        req = OpenUploadFileReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.按 bot_id 查未删除智能体，并带出所属网关
        agent = self.db.session.query(Agent).options(
            joinedload(Agent.gateway),
        ).filter(
            Agent.bot_id == req.bot_id.data,
            Agent.deleted_at.is_(None),
        ).one_or_none()
        if agent is None:
            raise NotFoundException("bot_id 对应的智能体不存在")

        # 3.必须挂了网关，且网关密钥与传入 bot_key 完全一致
        gateway_key = agent.gateway.gateway_key if agent.gateway is not None else None
        if agent.gateway_id is None or gateway_key != req.bot_key.data:
            raise FailException("bot_key 校验失败")

        # 4.会话必须未删除，且属于当前智能体
        conversation = self.db.session.query(Conversation.id).filter(
            Conversation.ws_session_id == req.session_id.data,
            Conversation.agent_id == agent.id,
            Conversation.deleted_at.is_(None),
        ).first()
        if conversation is None:
            raise NotFoundException("session_id 对应的会话不存在或不属于该智能体")

        # 5.文件挂到智能体所属账号，图片和文档都允许
        account = self.account_service.get_account(agent.account_id)
        if account is None:
            raise FailException("上传文件失败，请稍后重试")
        upload_file = self.cos_service.upload_file(req.file.data, False, account)

        # 6.免登录接口只返回可访问 URL
        return success_json({"url": self.cos_service.get_file_url(upload_file.key)})
