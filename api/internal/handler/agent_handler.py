#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:01:39
@Author  : liaosiliang1234@126.com
@File    : agent_handler.py
"""
from dataclasses import dataclass

from flask import request
from flask_login import login_required, current_user
from injector import inject

from internal.lib.identifier import generate_agent_identifier
from internal.schema.agent_schema import (
    CreateAgentReq,
    CreateAgentResp,
    GenerateAgentIdReq,
    GetAgentResp,
    GetAgentsWithPageReq,
    GetAgentsWithPageResp,
    UpdateAgentOnlineStatusReq,
    UpdateAgentReq,
)
from internal.service import AgentService
from pkg.response import (
    HttpCode,
    Response,
    json,
    success_json,
    success_message,
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
class AgentHandler:
    """智能体处理器"""

    agent_service: AgentService

    @login_required
    def get_agents_with_page(self):
        """获取当前登录账号下的智能体分页列表"""
        # 1.提取查询参数并校验
        req = GetAgentsWithPageReq(request.args)
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.查询当前账号的智能体分页数据
        agents, paginator = self.agent_service.get_agents_with_page(req, current_user.id)

        # 3.构建响应并返回
        resp = GetAgentsWithPageResp()
        return success_json(resp.dump({
            "list": agents,
            "paginator": paginator,
        }))

    @login_required
    def get_agent(self, agent_id: str):
        """获取指定智能体详情"""
        agent = self.agent_service.get_agent(agent_id, current_user.id)
        return success_json(GetAgentResp().dump(agent))

    @login_required
    def create_agent(self):
        """在当前登录账号下创建智能体"""
        # 1.校验请求体并提取字段
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = CreateAgentReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.创建智能体，归属账号取当前登录账号
        agent = self.agent_service.create_agent(
            account_id=current_user.id,
            bot_id=req.bot_id.data,
            peer_id=req.peer_id.data,
            name=req.name.data,
            avatar=req.avatar.data or "",
            agent_info=req.agent_info.data if isinstance(req.agent_info.data, dict) else {},
            gateway_id=req.gateway_id.data or None,
            agent_type=(req.agent_type.data or "HERMES").upper(),
        )

        # 3.返回新建智能体 id
        return json(Response(
            code=HttpCode.SUCCESS,
            message="创建智能体成功",
            data=CreateAgentResp().dump(agent),
        ))

    @login_required
    def update_agent(self, agent_id: str):
        """增量修改指定智能体"""
        # 1.校验请求体，只接受本次提交的字段
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = UpdateAgentReq()
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.按当前账号归属更新智能体
        self.agent_service.update_agent(agent_id, current_user.id, req.collect_updates())
        return success_message("修改智能体成功")

    @login_required
    def delete_agent(self, agent_id: str):
        """软删除指定智能体"""
        self.agent_service.delete_agent(agent_id, current_user.id)
        return success_message("删除智能体成功")

    @login_required
    def update_online_status(self, agent_id: str):
        """
        * @Author Leon-liao
        * @Function: update_online_status(agent_id)
        * @Description //把当前账号下指定智能体的在线状态写成请求体里的 0 或 1
        * @Date :2026/10/10 11:28:00
        * @Param: agent_id: 路由里的智能体 id，字符串
        * @return：success_json，data 为写入后的 status
        """
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = UpdateAgentOnlineStatusReq()
        if not req.validate():
            return validate_error_json(req.errors)
        agent = self.agent_service.update_online_status(
            agent_id,
            current_user.id,
            req.status.data,
        )
        return success_json({"status": agent.status})

    @login_required
    def generate_agent_id(self):
        """按类型生成当前登录账号下的智能体标识"""
        # 1.提取查询参数并校验
        req = GenerateAgentIdReq(request.args)
        if not req.validate():
            return validate_error_json(req.errors)

        # 2.用当前账号与可选智能体 id 生成标识
        id_type = req.type.data
        value = generate_agent_identifier(
            account_id=str(current_user.id),
            agent_id=req.agent_id.data or "",
            id_type=id_type,
        )
        return success_json({id_type: value})
