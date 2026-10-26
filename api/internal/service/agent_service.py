#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:01:39
@Author  : liaosiliang1234@126.com
@File    : agent_service.py
"""
import logging
from dataclasses import dataclass
from uuid import UUID

import requests
from injector import inject
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from config import Config
from internal.exception import FailException, NotFoundException
from internal.lib.gateway_key import generate_gateway_key
from internal.lib.helper import utc_now
from internal.lib.identifier import generate_agent_identifier
from internal.model import Agent, Conversation, Message, Server
from internal.schema.agent_schema import GetAgentsWithPageReq
from pkg.paginator import Paginator
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService

logger = logging.getLogger(__name__)

# 读接口把 message 表实时统计挂在实例上的键，schema 只读这个值，不读 agent.last_seen_at 列
_LIVE_LAST_SEEN_AT = "live_last_seen_at"

# 删除智能体后通知 Hub 断开上游连接的超时秒数
_HUB_DISCONNECT_TIMEOUT_SECONDS = 2

# 自动生成 bot_id / peer_id 时，查库防唯一索引冲突的最大尝试次数
_AGENT_ID_GENERATE_MAX_ATTEMPTS = 5


@inject
@dataclass
class AgentService(BaseService):
    """智能体服务"""

    db: SQLAlchemy
    config: Config

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
            bot_id: str | None,
            peer_id: str | None,
            name: str,
            avatar: str,
            agent_info: dict,
            gateway_id: str | None,
            agent_type: str = "HERMES",
    ) -> Agent:
        """在当前账号下创建智能体，bot_id 全局唯一（含已软删除记录）。

        bot_id / peer_id 为空时由后端自动生成；有值则沿用（向后兼容）。
        先创建一条专属 Server 网关记录，再把其 id 写入新智能体。
        gateway_id 入参已废弃，保留签名以免调用方报错，实际忽略。
        """
        # 入参已废弃，每个智能体自动分配专属网关，不再复用调用方传入的 gateway_id
        _ = gateway_id

        resolved_bot_id = (bot_id or "").strip()
        if not resolved_bot_id:
            resolved_bot_id = self._generate_unique_agent_identifier(
                account_id=account_id,
                id_type="bot_id",
                column=Agent.bot_id,
            )
        else:
            existed = self.db.session.query(Agent.id).filter(
                Agent.bot_id == resolved_bot_id,
            ).first()
            if existed:
                raise FailException("该智能体业务标识已存在")

        resolved_peer_id = (peer_id or "").strip()
        if not resolved_peer_id:
            resolved_peer_id = self._generate_unique_agent_identifier(
                account_id=account_id,
                id_type="peer_id",
                column=Agent.peer_id,
            )

        # 先落库专属网关，再创建智能体；任一步失败抛出原有异常，不静默吞掉
        server = self.create(
            Server,
            gateway_url=str(self.config.WS_GATEWAY_URL or ""),
            gateway_key=generate_gateway_key(),
        )

        try:
            return self.create(
                Agent,
                account_id=account_id,
                peer_id=resolved_peer_id,
                bot_id=resolved_bot_id,
                name=name,
                avatar=avatar or "",
                agent_type=(agent_type or "HERMES").upper(),
                agent_info=agent_info if isinstance(agent_info, dict) else {},
                gateway_id=server.id,
            )
        except IntegrityError as exc:
            try:
                self.delete(server)
            except Exception:
                logger.warning(
                    "创建智能体失败后清理专属网关失败，server_id=%s",
                    getattr(server, "id", None),
                    exc_info=True,
                )
            if self._is_bot_id_conflict(exc):
                raise FailException("该智能体业务标识已存在") from exc
            raise
        except Exception:
            try:
                self.delete(server)
            except Exception:
                logger.warning(
                    "创建智能体失败后清理专属网关失败，server_id=%s",
                    getattr(server, "id", None),
                    exc_info=True,
                )
            raise

    def _generate_unique_agent_identifier(
            self,
            account_id: UUID,
            id_type: str,
            column,
    ) -> str:
        """
        * @Author Leon-liao
        * @Function: _generate_unique_agent_identifier(account_id, id_type, column)
        * @Description //生成未被占用的 bot_id 或 peer_id；查库含软删除记录，最多尝试 5 次
        * @Date :2026/10/26 23:38:00
        * @Param: account_id: 当前账号 UUID；id_type: bot_id 或 peer_id；column: Agent 上对应唯一列
        * @return：可用的标识字符串；5 次仍冲突则抛 FailException
        """
        for _ in range(_AGENT_ID_GENERATE_MAX_ATTEMPTS):
            candidate = generate_agent_identifier(
                account_id=str(account_id),
                agent_id="",
                id_type=id_type,
            )
            # 唯一索引含软删除行，查询不要带 deleted_at 过滤
            existed = self.db.session.query(Agent.id).filter(
                column == candidate,
            ).first()
            if not existed:
                return candidate
        raise FailException("智能体标识生成失败，请重试")

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
        """软删除智能体，仅写入 deleted_at，不改动已产生的会话与消息；删后 best-effort 通知 Hub 断开上游 WS"""
        agent = self.get_agent(agent_id, account_id)
        updated = self.update(agent, deleted_at=utc_now())
        self._notify_hub_disconnect(str(agent.id))
        return updated

    def _notify_hub_disconnect(self, agent_id: str) -> None:
        """
        * @Author Leon-liao
        * @Function: _notify_hub_disconnect(agent_id: str)
        * @Description //best-effort 通知 Hub 关闭该智能体的上游 WebSocket；失败只记日志，不影响删除结果
        * @Date :2026/10/26 22:43:00
        * @Param: agent_id: 已软删除的智能体 id 字符串
        * @return：无
        """
        base_url = str(self.config.HUB_BASE_URL or "").rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "X-Internal-Token": str(self.config.INTERNAL_TOKEN or ""),
        }
        try:
            response = requests.post(
                f"{base_url}/disconnect",
                json={"agent_id": agent_id},
                headers=headers,
                timeout=_HUB_DISCONNECT_TIMEOUT_SECONDS,
            )
        except requests.RequestException:
            logger.warning("通知 Hub 断开连接失败，agent_id=%s, status_code=%s", agent_id, "none")
            return

        try:
            status_code = response.status_code
        finally:
            response.close()

        # 200 已断开；404 池中本来就没有连接，对删除流程都可接受
        if status_code not in (200, 404):
            logger.warning(
                "通知 Hub 断开连接失败，agent_id=%s, status_code=%s",
                agent_id,
                status_code,
            )

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
