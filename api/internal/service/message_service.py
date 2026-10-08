#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/09/27 22:22:49
@Author  : liaosiliang1234@126.com
@File    : message_service.py
"""
from dataclasses import dataclass
from uuid import UUID

from injector import inject
from sqlalchemy import literal_column, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from internal.exception import FailException, NotFoundException
from internal.lib.token_estimate import estimate_message_token
from internal.model import Conversation, Message
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService

_PREVIEW_MAX_LENGTH = 255


@dataclass
class MessageCursorPage:
    """消息游标分页结果"""

    messages: list[Message]
    has_more: bool
    next_cursor: str


@inject
@dataclass
class MessageService(BaseService):
    """消息服务"""

    db: SQLAlchemy

    def get_messages_with_page(
            self,
            account_id: UUID,
            conversation_id: UUID,
            turns: int | None,
            limit: int,
            before: str | None,
    ) -> MessageCursorPage:
        """按最近 N 轮或向上游标返回消息，结果按写入顺序"""
        if turns is not None:
            return self._list_recent_turns(account_id, conversation_id, turns)
        if before:
            return self._list_before(account_id, conversation_id, before, limit)
        return self._list_latest(account_id, conversation_id, limit)

    def upsert_message(
            self,
            conversation: Conversation,
            account_id: UUID,
            message_id: str,
            message_role: str,
            message_content: str,
            message_type: str,
            message_status: int,
            message_reasoning: str,
            message_info: dict,
            message_token: int,
            message_latency: int,
    ) -> Message:
        """按 (conversation_id, message_id) 幂等写入消息。

        不存在则插入，并在同一事务里把会话 message_count 加 1、total_token_count 加上本条 token。
        已存在则只更新正文、状态、推理、扩展信息、token、耗时和 updated_at，不再改计数。
        两种情况都更新 last_message_at 与 last_message_preview（预览最多 255 字符）。
        未传或传入 0/None 的 message_token 时，按正文长度估算；显式正数则尊重调用方。
        """
        if message_token is None or message_token == 0:
            token_count = estimate_message_token(message_content or "")
        else:
            token_count = int(message_token)
        info = message_info if isinstance(message_info, dict) else {}
        status = 1 if message_status is None else message_status
        insert_stmt = pg_insert(Message).values(
            conversation_id=conversation.id,
            account_id=account_id,
            message_id=message_id,
            message_role=message_role,
            message_content=message_content,
            message_type=message_type or "",
            message_status=status,
            message_reasoning=message_reasoning or "",
            message_info=info,
            message_token=token_count,
            message_latency=message_latency or 0,
        )
        # xmax = 0 表示本次是插入；冲突更新时 xmax 为当前事务号，用来区分要不要加计数
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["conversation_id", "message_id"],
            set_={
                "message_content": insert_stmt.excluded.message_content,
                "message_status": insert_stmt.excluded.message_status,
                "message_reasoning": insert_stmt.excluded.message_reasoning,
                "message_info": insert_stmt.excluded.message_info,
                "message_token": insert_stmt.excluded.message_token,
                "message_latency": insert_stmt.excluded.message_latency,
                "updated_at": text("clock_timestamp()"),
            },
        ).returning(
            Message.id,
            literal_column("(xmax = 0)").label("inserted"),
        )
        with self.db.auto_commit():
            row = self.db.session.execute(upsert_stmt).one()
            mapping = row._mapping
            inserted = mapping["inserted"] is True or mapping["inserted"] == 1
            message = self.db.session.get(Message, mapping["id"])
            if message is None:
                raise FailException("写入消息失败")
            if inserted:
                conversation.message_count = (conversation.message_count or 0) + 1
                conversation.total_token_count = (conversation.total_token_count or 0) + token_count
            preview = message_content or ""
            if len(preview) > _PREVIEW_MAX_LENGTH:
                preview = preview[:_PREVIEW_MAX_LENGTH]
            conversation.last_message_at = message.updated_at
            conversation.last_message_preview = preview
        return message

    def create_message(
            self,
            conversation: Conversation,
            account_id: UUID,
            message_role: str,
            message_content: str,
            message_type: str,
            message_token: int,
            message_latency: int,
    ) -> Message:
        """创建消息，并在同一事务内维护会话的条数、Token、最后消息时间与预览"""
        token_count = message_token or 0
        with self.db.auto_commit():
            message = Message(
                conversation_id=conversation.id,
                account_id=account_id,
                message_role=message_role,
                message_content=message_content,
                message_type=message_type or "",
                message_token=token_count,
                message_latency=message_latency or 0,
            )
            self.db.session.add(message)
            self.db.session.flush()
            self.db.session.refresh(message)

            preview = message.message_content or ""
            if len(preview) > _PREVIEW_MAX_LENGTH:
                preview = preview[:_PREVIEW_MAX_LENGTH]
            conversation.message_count = (conversation.message_count or 0) + 1
            conversation.total_token_count = (conversation.total_token_count or 0) + token_count
            conversation.last_message_at = message.created_at
            conversation.last_message_preview = preview
        return message

    def _list_recent_turns(
            self,
            account_id: UUID,
            conversation_id: UUID,
            turns: int,
    ) -> MessageCursorPage:
        """从倒数第 N 条 user 消息起到最新一条，按写入顺序返回"""
        anchor_seq = self.db.session.scalar(
            select(Message.seq).where(
                Message.conversation_id == conversation_id,
                Message.account_id == account_id,
                Message.message_role == "user",
            ).order_by(Message.seq.desc()).offset(turns - 1).limit(1)
        )

        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.account_id == account_id,
        )
        if anchor_seq is not None:
            statement = statement.where(Message.seq >= anchor_seq)
        statement = statement.order_by(Message.seq.asc())
        messages = list(self.db.session.scalars(statement).all())
        if not messages:
            return MessageCursorPage(messages=[], has_more=False, next_cursor="")
        has_more = self._has_earlier(account_id, conversation_id, messages[0])
        return MessageCursorPage(
            messages=messages,
            has_more=has_more,
            next_cursor=str(messages[0].id) if has_more else "",
        )

    def _list_latest(
            self,
            account_id: UUID,
            conversation_id: UUID,
            limit: int,
    ) -> MessageCursorPage:
        """返回最新 limit 条，再按写入顺序交给调用方"""
        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.account_id == account_id,
        ).order_by(Message.seq.desc()).limit(limit + 1)
        rows = list(self.db.session.scalars(statement).all())
        return self._to_cursor_page(rows, limit)

    def _list_before(
            self,
            account_id: UUID,
            conversation_id: UUID,
            before: str,
            limit: int,
    ) -> MessageCursorPage:
        """返回比 before 这条更早的 limit 条，正序"""
        try:
            before_id = UUID(str(before).strip())
        except (ValueError, TypeError, AttributeError) as exc:
            raise NotFoundException("消息不存在") from exc

        anchor = self.db.session.scalar(
            select(Message).where(
                Message.id == before_id,
                Message.conversation_id == conversation_id,
                Message.account_id == account_id,
            )
        )
        if anchor is None:
            raise NotFoundException("消息不存在")

        statement = select(Message).where(
            Message.conversation_id == conversation_id,
            Message.account_id == account_id,
            Message.seq < anchor.seq,
        ).order_by(Message.seq.desc()).limit(limit + 1)
        rows = list(self.db.session.scalars(statement).all())
        return self._to_cursor_page(rows, limit)

    def _has_earlier(self, account_id: UUID, conversation_id: UUID, earliest: Message) -> bool:
        """判断最早这条之前是否还有消息，比较键是写入序号"""
        earlier_id = self.db.session.scalar(
            select(Message.id).where(
                Message.conversation_id == conversation_id,
                Message.account_id == account_id,
                Message.seq < earliest.seq,
            ).limit(1)
        )
        return earlier_id is not None

    @staticmethod
    def _to_cursor_page(rows_desc: list[Message], limit: int) -> MessageCursorPage:
        """把倒序多取的一条换成正序页，并给出下一次 before"""
        has_more = len(rows_desc) > limit
        page = list(rows_desc[:limit])
        page.reverse()
        if not page or not has_more:
            return MessageCursorPage(messages=page, has_more=False, next_cursor="")
        return MessageCursorPage(
            messages=page,
            has_more=True,
            next_cursor=str(page[0].id),
        )
