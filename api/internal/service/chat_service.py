#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //把用户聊天文本转发给 Hub，并把 Hub 回写的完成帧落库
* @File: chat_service.py
* @Time: 2026/10/23 23:21:05
* @All Rights Reserve By Brtc
"""
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import requests
from injector import inject

from config import Config
from internal.exception import FailException, NotFoundException
from internal.model import Account, Agent, Conversation, Server
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService
from .message_service import MessageService

logger = logging.getLogger(__name__)

# Hub 转发超时，连接和读取共用这一秒数
_HUB_TIMEOUT_SECONDS = 3


@inject
@dataclass
class ChatService(BaseService):
    """聊天消息转发服务"""

    db: SQLAlchemy
    config: Config
    message_service: MessageService

    def send_message(
            self,
            account: Account,
            agent_id: str,
            thread_id: str,
            text: str,
            message_id: str,
            files: Any = None,
    ) -> dict:
        """
        * @Author Leon-liao
        * @Function: send_message(account, agent_id, thread_id, text, message_id, files=None)
        * @Description //确认智能体和会话归属后先写入用户消息，再转发给 Hub。成功把状态改为已发送，失败改为发送失败后继续抛出原异常
        * @Date :2026/10/25 22:24:33
        * @Param: account: 当前登录账号，Account；agent_id: 智能体主键，字符串；thread_id: 会话线程标识，字符串；text: 去掉首尾空白后的消息正文，字符串；message_id: 客户端消息幂等键，字符串；files: 附件列表，没有时为 None
        * @return：Hub 返回 200 时为 {"sent": True}。智能体或会话不存在抛 NotFoundException；未绑定网关、连接未就绪或发送失败先把该条消息标为失败再抛 FailException
        """
        # 1.查当前账号下未删除的智能体，非法主键与无记录统一视为不存在
        try:
            agent_uuid = UUID(str(agent_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise NotFoundException("智能体不存在") from exc

        agent = self.db.session.query(Agent).filter(
            Agent.id == agent_uuid,
            Agent.account_id == account.id,
            Agent.deleted_at.is_(None),
        ).one_or_none()
        if agent is None:
            raise NotFoundException("智能体不存在")

        # 2.会话必须属于该智能体和当前账号，且未软删除
        conversation = self.db.session.query(Conversation).filter(
            Conversation.agent_id == agent.id,
            Conversation.thread_id == thread_id,
            Conversation.account_id == account.id,
            Conversation.deleted_at.is_(None),
        ).one_or_none()
        if conversation is None:
            raise NotFoundException("会话不存在")

        # 3.先落用户消息。token 传 0，由 message_service 按正文估算
        message_info = {"files": files} if files else {}

        def write_user_message(message_status: int) -> None:
            """
            * @Author Leon-liao
            * @Function: write_user_message(message_status: int)
            * @Description //按同一个幂等键写入或更新这条用户消息，只改状态
            * @Date :2026/10/25 22:24:33
            * @Param: message_status: 0 发送中，1 已发送，2 发送失败
            * @return：无
            """
            self.message_service.upsert_message(
                conversation=conversation,
                account_id=account.id,
                message_id=message_id,
                message_role="user",
                message_content=text,
                message_type="message",
                message_status=message_status,
                message_reasoning="",
                message_info=message_info,
                message_token=0,
                message_latency=0,
            )

        write_user_message(0)

        # 4.网关校验和转发失败时，把同一条消息标为失败后再抛出原来的异常
        try:
            if agent.gateway_id is None:
                raise FailException("智能体未绑定网关")
            server = self.db.session.query(Server).filter(
                Server.id == agent.gateway_id,
            ).one_or_none()
            if server is None:
                raise FailException("智能体未绑定网关")

            # 5.只把网关密钥放进请求体。下面的日志只记状态码，不能带上 payload
            payload = {
                "agent_id": str(agent.id),
                "bot_id": str(agent.bot_id or ""),
                "gateway_url": str(server.gateway_url or ""),
                "gateway_key": str(server.gateway_key or ""),
                "account_id": str(account.id),
                "thread_id": str(thread_id or ""),
                "peer_id": str(agent.peer_id or ""),
                "text": str(text or ""),
            }
            base_url = str(self.config.HUB_BASE_URL or "").rstrip("/")
            headers = {
                "Content-Type": "application/json",
                "X-Internal-Token": str(self.config.INTERNAL_TOKEN or ""),
            }
            try:
                response = requests.post(
                    f"{base_url}/send",
                    json=payload,
                    headers=headers,
                    timeout=_HUB_TIMEOUT_SECONDS,
                )
            except requests.RequestException:
                logger.warning("消息发送失败，status_code=%s", "none")
                raise FailException("消息发送失败，请稍后重试") from None

            try:
                status_code = response.status_code
            finally:
                response.close()

            # 6.上游连接还没就绪
            if status_code == 503:
                raise FailException("智能体连接未就绪，请稍后重试")
            # 7.其它状态码。异常对象里可能夹带请求信息，这里只记状态码
            if status_code != 200:
                logger.warning("消息发送失败，status_code=%s", status_code)
                raise FailException("消息发送失败，请稍后重试")
        except Exception:
            try:
                write_user_message(2)
            except Exception:
                logger.exception("用户消息状态更新为失败时出错")
            raise

        # 8.Hub 已收下，同一幂等键把状态改为已发送
        write_user_message(1)
        return {"sent": True}

    def save_reply(
            self,
            account_id: Any,
            thread_id: Any,
            message_id: Any,
            content: Any,
            files: Any,
    ) -> dict:
        """
        * @Author Leon-liao
        * @Function: save_reply(account_id, thread_id, message_id, content, files)
        * @Description //按账号和线程找到未删除会话，并把助手完成回复幂等写入消息表
        * @Date :2026/10/23 23:50:18
        * @Param: account_id: 帧里的账号标识，字符串或可转为 UUID 的值；thread_id: 会话线程标识；message_id: 对端消息幂等键；content: 回复正文，会去掉首尾空白；files: 帧里的文件列表，没有时为 None
        * @return：写入成功为 {"stored": True}。会话不存在或账号标识非法时为 {"stored": False}，不抛异常
        """
        # 1.账号标识非法时查不到会话。这里吞掉转换错误，避免 Hub 把同一帧反复重试
        try:
            account_uuid = UUID(str(account_id).strip())
        except (ValueError, TypeError, AttributeError):
            logger.warning(
                "内部回写未找到会话，account_id=%s，thread_id=%s",
                account_id,
                thread_id,
            )
            return {"stored": False}

        thread = thread_id.strip() if isinstance(thread_id, str) else str(thread_id or "")
        conversation = self.db.session.query(Conversation).filter(
            Conversation.account_id == account_uuid,
            Conversation.thread_id == thread,
            Conversation.deleted_at.is_(None),
        ).one_or_none()
        if conversation is None:
            logger.warning(
                "内部回写未找到会话，account_id=%s，thread_id=%s",
                account_id,
                thread_id,
            )
            return {"stored": False}

        # 2.正文去掉首尾空白。空字符串也写入，保证同一 message_id 重复回写仍然幂等
        if isinstance(content, str):
            text = content.strip()
        else:
            text = ""
        external_id = message_id.strip() if isinstance(message_id, str) else str(message_id or "")
        message_info = {"files": files} if files is not None else {}
        self.message_service.upsert_message(
            conversation=conversation,
            account_id=conversation.account_id,
            message_id=external_id,
            message_role="assistant",
            message_content=text,
            message_type="reply",
            message_status=1,
            message_reasoning="",
            message_info=message_info,
            message_token=0,
            message_latency=0,
        )
        return {"stored": True}
