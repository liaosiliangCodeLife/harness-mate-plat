#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:01:39
@Author  : liaosiliang1234@126.com
@File    : agent_service.py
"""
from dataclasses import dataclass
from uuid import UUID

from injector import inject
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from internal.exception import FailException, NotFoundException
from internal.lib.helper import utc_now
from internal.model import Agent, Conversation, Message, Server
from internal.schema.agent_schema import GetAgentsWithPageReq
from pkg.paginator import Paginator
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService

# 读接口把 message 表实时统计挂在实例上的键，schema 只读这个值，不读 agent.last_seen_at 列
_LIVE_LAST_SEEN_AT = "live_last_seen_at"


@inject
@dataclass
class AgentService(BaseService):
    """智能体服务"""

    db: SQLAlchemy

    def get_agents_with_page(
            self,
            req: GetAgentsWithPageReq,
            account_id: UUID,
    ) -> tuple[list[Agent], Paginator]:
        """分页查询当前账号下未删除的智能体，名称支持模糊搜索，并关联所属网关"""
        statement = select(Agent).options(joinedload(Agent.gateway)).where(
            Agent.account_id == account_id,
            Agent.deleted_at.is_(None),
        )
        search_word = (req.search_word.data or "").strip()
        if search_word:
            escaped = (
                search_word.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            statement = statement.where(Agent.name.ilike(f"%{escaped}%", escape="\\"))
        if req.agent_type.data:
            statement = statement.where(Agent.agent_type == req.agent_type.data.strip().upper())
        statement = statement.order_by(Agent.created_at.desc(), Agent.id.desc())

        paginator = Paginator(db=self.db, req=req)
        agents = paginator.paginate(statement)
        self._attach_live_last_seen(agents)
        return agents, paginator

    def get_agent(self, agent_id: str, account_id: UUID) -> Agent:
        """按智能体 id 与当前账号查询未删除记录，并关联所属网关，不存在或无权限统一视为不存在"""
        try:
            agent_uuid = UUID(str(agent_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise NotFoundException("智能体不存在") from exc

        agent = self.db.session.query(Agent).options(joinedload(Agent.gateway)).filter(
            Agent.id == agent_uuid,
            Agent.account_id == account_id,
            Agent.deleted_at.is_(None),
        ).one_or_none()
        if agent is None:
            raise NotFoundException("智能体不存在")
        self._attach_live_last_seen([agent])
        return agent

    def create_agent(
            self,
            account_id: UUID,
            bot_id: str,
            peer_id: str,
            name: str,
            avatar: str,
            agent_info: dict,
            gateway_id: str | None,
            agent_type: str = "HERMES",
    ) -> Agent:
        """在当前账号下创建智能体，bot_id 全局唯一（含已软删除记录）"""
        existed = self.db.session.query(Agent.id).filter(
            Agent.bot_id == bot_id,
        ).first()
        if existed:
            raise FailException("该智能体业务标识已存在")

        resolved_gateway_id = None
        if gateway_id:
            resolved_gateway_id = self._require_owned_gateway(gateway_id)

        try:
            return self.create(
                Agent,
                account_id=account_id,
                peer_id=peer_id,
                bot_id=bot_id,
                name=name,
                avatar=avatar or "",
                agent_type=(agent_type or "HERMES").upper(),
                agent_info=agent_info if isinstance(agent_info, dict) else {},
                gateway_id=resolved_gateway_id,
            )
        except IntegrityError as exc:
            if self._is_bot_id_conflict(exc):
                raise FailException("该智能体业务标识已存在") from exc
            raise

    def update_agent(self, agent_id: str, account_id: UUID, update_data: dict) -> Agent:
        """增量更新智能体；本次提交的 agent_info 整体替换为最终值，未提交则保持原值"""
        agent = self.get_agent(agent_id, account_id)
        if not update_data:
            return agent

        payload = dict(update_data)
        if "gateway_id" in payload:
            payload["gateway_id"] = self._require_owned_gateway(payload["gateway_id"])
        return self.update(agent, **payload)

    def delete_agent(self, agent_id: str, account_id: UUID) -> Agent:
        """软删除智能体，仅写入 deleted_at，不改动已产生的会话与消息"""
        agent = self.get_agent(agent_id, account_id)
        return self.update(agent, deleted_at=utc_now())

    def update_online_status(self, agent_id: str, account_id: UUID, status: int) -> Agent:
        """
        * @Author Leon-liao
        * @Function: update_online_status(agent_id, account_id, status)
        * @Description //把智能体在线状态写入 agent.status。不存在或已删除时沿用 get_agent 的未找到错误
        * @Date :2026/10/10 11:28:00
        * @Param: agent_id: 智能体 id，字符串；account_id: 当前登录账号 UUID；status: 整数，0 表示离线，1 表示在线
        * @return：更新后的智能体
        """
        agent = self.get_agent(agent_id, account_id)
        return self.update(agent, status=status)

    def _attach_live_last_seen(self, agents: list[Agent]) -> None:
        """按 message 表统计每个智能体最近一条消息时间，挂到实例上供 schema 读取。

        统计口径：未删除会话里 max(message.created_at)。没有消息时为 None，
        不回落到 agent.last_seen_at 列。
        """
        if not agents:
            return
        rows = self.db.session.execute(
            select(Conversation.agent_id, func.max(Message.created_at))
            .join(Message, Message.conversation_id == Conversation.id)
            .where(
                Conversation.agent_id.in_([agent.id for agent in agents]),
                Conversation.deleted_at.is_(None),
            )
            .group_by(Conversation.agent_id)
        ).all()
        last_seen_by_agent = {agent_id: last_seen_at for agent_id, last_seen_at in rows}
        for agent in agents:
            inspect(agent).info[_LIVE_LAST_SEEN_AT] = last_seen_by_agent.get(agent.id)

    def _require_owned_gateway(self, gateway_id: str) -> UUID:
        """确认网关存在。网关是全局数据，不按账号过滤；记录不存在时视为网关不存在"""
        try:
            gateway_uuid = UUID(str(gateway_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise FailException("网关标识格式不正确") from exc

        owned = self.db.session.query(Server.id).filter(
            Server.id == gateway_uuid,
        ).one_or_none()
        if owned is None:
            raise FailException("网关不存在")
        return gateway_uuid

    @staticmethod
    def _is_bot_id_conflict(exc: IntegrityError) -> bool:
        """判断完整性错误是否由 bot_id 唯一约束引起"""
        orig = getattr(exc, "orig", None)
        diag = getattr(orig, "diag", None)
        constraint_name = getattr(diag, "constraint_name", None)
        if constraint_name == "uk_agent_bot_id":
            return True
        return "uk_agent_bot_id" in str(orig)
