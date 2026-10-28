#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //分享智能体接口处理器
* @File: share_agent_handler.py
* @Time: 2026/10/28 09:36:06
* @All Rights Reserve By Brtc
"""
from dataclasses import dataclass

from flask import g, request
from flask_login import current_user, login_required
from injector import inject

from internal.exception import ForbiddenException, UnauthorizedException
from internal.schema.share_agent_schema import (
    CreateShareAgentReq,
    CreateShareConversationReq,
    GetShareAgentsWithPageListResp,
    GetShareAgentsWithPageReq,
    ShareAccessReq,
    UpdateShareAgentReq,
)
from internal.service import ShareAgentService
from pkg.response import success_json, validate_error_json


def _validate_json_object():
    """
    * @Author Leon-liao
    * @Function:
    _validate_json_object()
    * @Description //POST 携带请求体时必须是 JSON 对象，否则返回参数校验错误
    * @Date :2026/10/28 09:36:06
    * @Param:
    无
    * @return：合法或缺省时返回 None；不是 JSON 对象时返回校验错误响应
    """
    if not request.data and not request.is_json:
        return None
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return validate_error_json({"body": ["请求体必须是JSON对象"]})
    return None


@inject
@dataclass
class ShareAgentHandler:
    """分享智能体处理器"""

    share_agent_service: ShareAgentService

    @login_required
    def create(self, agent_id: str):
        """
        * @Author Leon-liao
        * @Function:
        create(agent_id)
        * @Description //登录态创建分享
        * @Date :2026/10/28 09:36:06
        * @Param:
        agent_id: 路径中的智能体主键
        * @return：success_json，data 为新建分享信息
        """
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = CreateShareAgentReq()
        if not req.validate():
            return validate_error_json(req.errors)
        data = self.share_agent_service.create_share_agent(current_user, agent_id, req)
        return success_json(data)

    @login_required
    def list(self, agent_id: str):
        """
        * @Author Leon-liao
        * @Function:
        list(agent_id)
        * @Description //登录态分页查询分享列表
        * @Date :2026/10/28 09:36:06
        * @Param:
        agent_id: 路径中的智能体主键
        * @return：success_json，data 含 list 与 paginator
        """
        req = GetShareAgentsWithPageReq(request.args)
        if not req.validate():
            return validate_error_json(req.errors)
        page = self.share_agent_service.get_share_agents_with_page(current_user, agent_id, req)
        resp = GetShareAgentsWithPageListResp()
        return success_json(resp.dump({
            "list": page.list,
            "paginator": page.paginator,
        }))

    @login_required
    def update(self, agent_id: str, share_id: str):
        """
        * @Author Leon-liao
        * @Function:
        update(agent_id, share_id)
        * @Description //登录态增量修改分享
        * @Date :2026/10/28 09:36:06
        * @Param:
        agent_id: 智能体主键；share_id: 分享主键
        * @return：success_json，data 为 {"updated": true}
        """
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = UpdateShareAgentReq()
        if not req.validate():
            return validate_error_json(req.errors)
        data = self.share_agent_service.update_share_agent(
            current_user, agent_id, share_id, req,
        )
        return success_json(data)

    @login_required
    def delete(self, agent_id: str, share_id: str):
        """
        * @Author Leon-liao
        * @Function:
        delete(agent_id, share_id)
        * @Description //登录态停用（软删）分享
        * @Date :2026/10/28 09:36:06
        * @Param:
        agent_id: 智能体主键；share_id: 分享主键
        * @return：success_json，data 为 {"deleted": true}
        """
        data = self.share_agent_service.delete_share_agent(current_user, agent_id, share_id)
        return success_json(data)

    def landing(self, share_id: str):
        """
        * @Author Leon-liao
        * @Function:
        landing(share_id)
        * @Description //免登录返回分享落地页信息
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键
        * @return：success_json，落地页字段
        """
        data = self.share_agent_service.get_share_landing(share_id)
        return success_json(data)

    def access(self, share_id: str):
        """
        * @Author Leon-liao
        * @Function:
        access(share_id)
        * @Description //免登录校验密码与配额，换取分享态 token
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键
        * @return：success_json，含 access_token 等
        """
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = ShareAccessReq()
        if not req.validate():
            return validate_error_json(req.errors)
        data = self.share_agent_service.access_share(share_id, req.pwd.data)
        return success_json(data)

    def create_conversation(self, share_id: str):
        """
        * @Author Leon-liao
        * @Function:
        create_conversation(share_id)
        * @Description //分享态创建访客会话；校验 g 中 scope/share_id 与路径一致
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 路径中的分享主键
        * @return：success_json，新建会话信息
        """
        # 访问 current_user 触发 request_loader，写入 g.token_scope / g.share_id
        account = current_user
        if account is None or not getattr(account, "is_authenticated", False):
            raise UnauthorizedException("该接口需要授权才能访问，请登录后尝试")
        token_scope = getattr(g, "token_scope", None)
        token_share_id = getattr(g, "share_id", None)
        if token_scope != "share" or str(token_share_id or "") != str(share_id):
            raise ForbiddenException("无权访问该分享")

        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = CreateShareConversationReq()
        if not req.validate():
            return validate_error_json(req.errors)

        share = self.share_agent_service.get_active_share_for_token(share_id)
        data = self.share_agent_service.create_share_conversation(share, account, req)
        return success_json(data)
