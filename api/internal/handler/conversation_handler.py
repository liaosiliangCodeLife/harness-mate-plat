#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:13:39
@Author  : liaosiliang1234@126.com
@File    : conversation_handler.py
"""
from dataclasses import dataclass

from flask import current_app, request
from flask_login import login_required, current_user
from injector import inject

from internal.schema.conversation_schema import (
    CreateConversationReq,
    CreateConversationResp,
    GetConversationsWithPageReq,
    GetConversationsWithPageResp,
    UpdateConversationReq,
)
from internal.service import AgentService, ConversationService
from pkg.response import (
    HttpCode,
    Response,
    json,
    success_message,
    validate_error_json,
)


def _ordered_success_json(data):
    """返回成功响应，并保持 data 中的字段顺序"""
    body = {
        "code": HttpCode.SUCCESS,
        "data": data,
        "message": "",
    }
    provider = current_app.json
    dumps_kwargs = {"sort_keys": False}
    if (provider.compact is None and current_app.debug) or provider.compact is False:
        dumps_kwargs["indent"] = 2
        dumps_kwargs["separators"] = (", ", ": ")
    return current_app.response_class(
        provider.dumps(body, **dumps_kwargs),
        mimetype=provider.mimetype,
    ), 200


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
class ConversationHandler:
    """会话处理器"""

    agent_service: AgentService
    conversation_service: ConversationService

    @login_required
    def get_conversations_with_page(self, agent_id: str):
        """获取指定智能体下的会话分页列表"""
        # 1.先确认智能体属于当前账号
        agent = self.agent_service.get_agent(agent_id, current_user.id)

        # 2.提取查询参数并校验
        req = GetConversationsWithPageReq(request.args)
        if not req.validate():
            return validate_error_json(req.errors)

        # 3.只查询该智能体、当前账号下的会话
        conversations, paginator = self.conversation_service.get_conversations_with_page(
            req,
            current_user.id,
            agent.id,
        )
        resp = GetConversationsWithPageResp()
        return _ordered_success_json(resp.dump({
            "list": conversations,
            "paginator": paginator,
        }))

    @login_required
    def create_conversation(self, agent_id: str):
        """在指定智能体下创建会话"""
        # 1.先确认智能体属于当前账号，再校验请求体
        agent = self.agent_service.get_agent(agent_id, current_user.id)
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = CreateConversationReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.账号取当前登录账号，会话归属路径中的智能体；连接标识用该智能体的 peer_id
        conversation = self.conversation_service.create_conversation(
            account_id=current_user.id,
            agent_id=agent.id,
            agent_peer_id=agent.peer_id or "",
            thread_id=req.thread_id.data,
            title=req.title.data or "",
            conversation_info=req.conversation_info.data if isinstance(req.conversation_info.data, dict) else {},
        )
        return json(Response(
            code=HttpCode.SUCCESS,
            message="创建会话成功",
            data=CreateConversationResp().dump(conversation),
        ))

    @login_required
    def update_conversation(self, agent_id: str, conversation_id: str):
        """增量修改指定会话"""
        # 1.先确认智能体属于当前账号，再校验请求体
        agent = self.agent_service.get_agent(agent_id, current_user.id)
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = UpdateConversationReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.会话必须属于该智能体和当前账号
        self.conversation_service.update_conversation(
            conversation_id,
            current_user.id,
            agent.id,
            req.collect_updates(),
        )
        return success_message("修改会话成功")

    @login_required
    def delete_conversation(self, agent_id: str, conversation_id: str):
        """软删除指定会话"""
        agent = self.agent_service.get_agent(agent_id, current_user.id)
        self.conversation_service.delete_conversation(conversation_id, current_user.id, agent.id)
        return success_message("删除会话成功")
