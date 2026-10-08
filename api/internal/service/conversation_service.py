#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:13:39
@Author  : liaosiliang1234@126.com
@File    : conversation_service.py
"""
import math
from dataclasses import dataclass
from uuid import UUID, uuid4

from injector import inject
from sqlalchemy import func, inspect, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, lazyload

from internal.exception import FailException, NotFoundException
from internal.lib.helper import utc_now
from internal.model import Agent, Conversation, Message
from internal.schema.conversation_schema import GetConversationsWithPageReq
from pkg.paginator import Paginator
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService

_PREVIEW_MAX_LENGTH = 255
_LIVE_MESSAGE_STATS = "live_message_stats"


def _with_live_message_stats(statement):
    """
    * @Author Leon-liao
    * @Function:
    _with_live_message_stats(statement)
    * @Description //在会话查询上用两条 LATERAL 一次算出消息条数、Token 合计，以及 seq 最大那条的时间与正文预览
    * @Date :2026/09/30 22:28:00
    * @Param:
    statement: 已经带有 Conversation 实体与过滤、排序条件的 SQLAlchemy Select
    * @return：追加实时统计列后的 Select。结果行第 0 列仍是会话，后面四列依次是条数、Token 合计、最后消息时间、预览
    """
    message_agg = (
        select(
            func.count(Message.id).label("message_count"),
            func.coalesce(func.sum(Message.message_token), 0).label("total_token_count"),
        )
        .where(Message.conversation_id == Conversation.id)
        .lateral("message_agg")
    )
    last_message = (
        select(
            Message.created_at.label("last_message_at"),
            func.left(Message.message_content, _PREVIEW_MAX_LENGTH).label("last_message_preview"),
        )
        .where(Message.conversation_id == Conversation.id)
        .order_by(Message.seq.desc())
        .limit(1)
        .lateral("last_message")
    )
    return (
        statement.select_from(Conversation)
        .outerjoin(message_agg, true())
        .outerjoin(last_message, true())
        .add_columns(
            func.coalesce(message_agg.c.message_count, 0).label("live_message_count"),
            func.coalesce(message_agg.c.total_token_count, 0).label("live_total_token_count"),
            last_message.c.last_message_at.label("live_last_message_at"),
            func.coalesce(last_message.c.last_message_preview, "").label("live_last_message_preview"),
        )
    )


def _bind_live_message_stats(row):
    """
    * @Author Leon-liao
    * @Function:
    _bind_live_message_stats(row)
    * @Description //把查询结果里的实时统计挂到会话对象上，供 schema 读取；读不到时 schema 回落到冗余列
    * @Date :2026/09/30 22:28:00
    * @Param:
    row: 会话查询结果行，第 0 列是 Conversation，其后依次为条数、Token 合计、最后消息时间、预览
    * @return：挂好统计后的会话对象
    """
    conversation = row[0]
    preview = row[4] or ""
    inspect(conversation).info[_LIVE_MESSAGE_STATS] = {
        "message_count": int(row[1] or 0),
        "total_token_count": int(row[2] or 0),
        "last_message_at": row[3],
        "last_message_preview": preview,
    }
    return conversation



@inject
@dataclass
class ConversationService(BaseService):
    """会话服务"""

    db: SQLAlchemy

    def get_conversations_with_page(
            self,
            req: GetConversationsWithPageReq,
            account_id: UUID,
            agent_id: UUID,
    ) -> tuple[list[Conversation], Paginator]:
        """分页查询指定智能体下、当前账号的未删除会话，标题支持模糊搜索，并一次性关联所属智能体及其网关"""
        statement = select(Conversation).options(
            joinedload(Conversation.agent).joinedload(Agent.gateway),
        ).where(
            Conversation.account_id == account_id,
            Conversation.agent_id == agent_id,
            Conversation.deleted_at.is_(None),
        )
        search_word = (req.search_word.data or "").strip()
        if search_word:
            escaped = (
                search_word.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            statement = statement.where(Conversation.title.ilike(f"%{escaped}%", escape="\\"))
        statement = statement.order_by(
            Conversation.pinned.desc(),
            Conversation.created_at.desc(),
            Conversation.id.desc(),
        )

        paginator = Paginator(db=self.db, req=req)
        page_size = paginator.page_size or 20
        current_page = paginator.current_page or 1
        # 条数按过滤后的会话算，不把 LATERAL 和网关关联算进行数
        count_source = (
            statement.options(lazyload("*"))
            .order_by(None)
            .with_only_columns(Conversation.id)
            .subquery()
        )
        total = self.db.session.scalar(select(func.count()).select_from(count_source)) or 0
        paginator.total_record = total
        paginator.total_page = math.ceil(total / page_size) if page_size else 0
        rows = self.db.session.execute(
            _with_live_message_stats(statement)
            .limit(page_size)
            .offset((current_page - 1) * page_size)
        ).unique().all()
        return [_bind_live_message_stats(row) for row in rows], paginator

    def get_conversation(self, conversation_id: str, account_id: UUID, agent_id: UUID) -> Conversation:
        """按会话 id、智能体 agent_id 与当前账号查询未删除记录，不存在或无权限统一视为不存在"""
        try:
            conversation_uuid = UUID(str(conversation_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise NotFoundException("会话不存在") from exc

        statement = _with_live_message_stats(select(Conversation).where(
            Conversation.id == conversation_uuid,
            Conversation.agent_id == agent_id,
            Conversation.account_id == account_id,
            Conversation.deleted_at.is_(None),
        ))
        row = self.db.session.execute(statement).unique().one_or_none()
        if row is None:
            raise NotFoundException("会话不存在")
        return _bind_live_message_stats(row)

    def create_conversation(
            self,
            account_id: UUID,
            agent_id: UUID,
            agent_peer_id: str,
            thread_id: str,
            title: str,
            conversation_info: dict,
    ) -> Conversation:
        """在指定智能体下创建会话。主键由服务端生成，ws_session_id 为 peer_id 加会话 id 十六进制前 16 位；thread_id 在同一账号下唯一（含已软删除记录）"""
        existed = self.db.session.query(Conversation.id).filter(
            Conversation.account_id == account_id,
            Conversation.thread_id == thread_id,
        ).first()
        if existed:
            raise FailException("该会话线程标识已存在")

        cid = uuid4()
        try:
            return self.create(
                Conversation,
                id=cid,
                account_id=account_id,
                agent_id=agent_id,
                thread_id=thread_id,
                ws_session_id=f"{agent_peer_id or ''}-{cid.hex[:16]}",
                title=title or "",
                conversation_info=conversation_info if isinstance(conversation_info, dict) else {},
            )
        except IntegrityError as exc:
            if self._is_thread_conflict(exc):
                raise FailException("该会话线程标识已存在") from exc
            raise

    def update_conversation(
            self,
            conversation_id: str,
            account_id: UUID,
            agent_id: UUID,
            update_data: dict,
    ) -> Conversation:
        """增量更新会话；conversation_info 与已有扩展信息按顶层键合并"""
        conversation = self.get_conversation(conversation_id, account_id, agent_id)
        if not update_data:
            return conversation

        payload = dict(update_data)
        # 请求带了 status 时，同时刷新会话在线心跳。时间使用 UTC naive
        if "status" in payload:
            payload["online_at"] = utc_now()
        if "conversation_info" in payload:
            current_info = conversation.conversation_info if isinstance(conversation.conversation_info, dict) else {}
            incoming_info = payload["conversation_info"]
            if not isinstance(incoming_info, dict):
                incoming_info = {}
            payload["conversation_info"] = {**current_info, **incoming_info}
        return self.update(conversation, **payload)

    def delete_conversation(self, conversation_id: str, account_id: UUID, agent_id: UUID) -> Conversation:
        """软删除会话，仅写入 deleted_at，不改动已产生的消息"""
        conversation = self.get_conversation(conversation_id, account_id, agent_id)
        return self.update(conversation, deleted_at=utc_now())

    @staticmethod
    def _is_thread_conflict(exc: IntegrityError) -> bool:
        """判断完整性错误是否由账号下 thread_id 唯一约束引起"""
        orig = getattr(exc, "orig", None)
        diag = getattr(orig, "diag", None)
        constraint_name = getattr(diag, "constraint_name", None)
        if constraint_name == "uk_conversation_account_thread":
            return True
        return "uk_conversation_account_thread" in str(orig)
