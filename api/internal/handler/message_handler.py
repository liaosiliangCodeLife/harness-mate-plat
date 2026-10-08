#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:22:49
@Author  : liaosiliang1234@126.com
@File    : message_handler.py
"""
from dataclasses import dataclass

from flask import request
from flask_login import login_required, current_user
from injector import inject

from internal.schema.message_schema import (
    CreateMessageReq,
    CreateMessageResp,
    GetMessagesWithPageReq,
    GetMessagesWithPageResp,
)
from internal.service import AgentService, ConversationService, MessageService
from pkg.response import (
    HttpCode,
    Response,
    json,
    success_json,
    validate_error_json,
)


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
class MessageHandler:
    """消息处理器"""

    agent_service: AgentService
    conversation_service: ConversationService
    message_service: MessageService

    @login_required
    def get_messages_with_page(self, agent_id: str, conversation_id: str):
        """获取指定会话下的消息列表，支持最近 N 轮或向上游标加载"""
        # 1.先确认智能体属于当前账号，再确认会话属于该智能体
        agent = self.agent_service.get_agent(agent_id, current_user.id)
        conversation = self.conversation_service.get_conversation(
            conversation_id,
            current_user.id,
            agent.id,
        )

        # 2.提取查询参数并校验
        req = GetMessagesWithPageReq(request.args)
        if not req.validate():
            return validate_error_json(req.errors)

        # 3.按最近 N 轮或向上游标查询该会话、当前账号下的消息
        before = (req.before.data or "").strip() or None
        page = self.message_service.get_messages_with_page(
            account_id=current_user.id,
            conversation_id=conversation.id,
            turns=req.turns.data,
            limit=req.limit.data or 20,
            before=before,
        )
        resp = GetMessagesWithPageResp()
        return success_json(resp.dump({
            "list": page.messages,
            "has_more": page.has_more,
            "next_cursor": page.next_cursor,
        }))

    @login_required
    def create_message(self, agent_id: str, conversation_id: str):
        """在指定会话下创建消息"""
        # 1.先确认智能体与会话归属，再校验请求体
        agent = self.agent_service.get_agent(agent_id, current_user.id)
        conversation = self.conversation_service.get_conversation(
            conversation_id,
            current_user.id,
            agent.id,
        )
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = CreateMessageReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.按 message_id 幂等写入，账号取当前登录账号
        message = self.message_service.upsert_message(
            conversation=conversation,
            account_id=current_user.id,
            message_id=req.message_id.data,
            message_role=req.message_role.data,
            message_content=req.message_content.data,
            message_type=req.message_type.data or "",
            message_status=1 if req.message_status.data is None else req.message_status.data,
            message_reasoning=req.message_reasoning.data or "",
            message_info=req.message_info.data if isinstance(req.message_info.data, dict) else {},
            message_token=req.message_token.data or 0,
            message_latency=req.message_latency.data or 0,
        )
        return json(Response(
            code=HttpCode.SUCCESS,
            message="创建消息成功",
            data=CreateMessageResp().dump(message),
        ))
