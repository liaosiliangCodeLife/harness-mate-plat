#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //分享智能体：创建/列表/修改/停用、落地页、换 token、建访客会话
* @File: share_agent_service.py
* @Time: 2026/10/28 09:36:06
* @All Rights Reserve By Brtc
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from flask import request
from injector import inject
from sqlalchemy import func, select
from werkzeug.security import check_password_hash, generate_password_hash

from internal.exception import ForbiddenException, NotFoundException, ValidateErrorException
from internal.lib.helper import datetime_to_timestamp, utc_now
from internal.model import Account, Agent, Conversation, Message, ShareAgent
from internal.schema.share_agent_schema import (
    CreateShareAgentReq,
    CreateShareConversationReq,
    GetShareAgentsWithPageReq,
    UpdateShareAgentReq,
)
from pkg.paginator import PageModel, Paginator
from pkg.sqlalchemy import SQLAlchemy
from .base_service import BaseService
from .jwt_service import JwtService

# 分享态 token 有效期（小时）
_SHARE_TOKEN_HOURS = 24

# access_pwd 列长 128，使用 pbkdf2 哈希以适配长度
_PWD_HASH_METHOD = "pbkdf2:sha256"


@inject
@dataclass
class ShareAgentService(BaseService):
    """分享智能体服务"""

    db: SQLAlchemy
    jwt_service: JwtService

    def create_share_agent(self, account: Account, agent_id: str, req: CreateShareAgentReq) -> dict:
        """
        * @Author Leon-liao
        * @Function:
        create_share_agent(account, agent_id, req)
        * @Description //校验智能体归属后创建分享记录，密码非空时哈希入库
        * @Date :2026/10/28 09:36:06
        * @Param:
        account: 当前登录账号，Account；agent_id: 智能体主键，字符串；req: 创建分享请求
        * @return：含 id、agent_id、access_num、share_url、created_at 的字典
        """
        agent = self._get_owned_agent(agent_id, account.id)
        plain_pwd = req.access_pwd.data or ""
        access_pwd = (
            generate_password_hash(plain_pwd, method=_PWD_HASH_METHOD) if plain_pwd else ""
        )
        share = self.create(
            ShareAgent,
            agent_id=agent.id,
            account_id=account.id,
            access_prompt=req.access_prompt.data or "",
            access_pwd=access_pwd,
            access_num=req.access_num.data if req.access_num.data is not None else 0,
            shared_info=req.shared_info.data or "",
            pay_url=req.pay_url.data or "",
            deleted_at=None,
        )
        return {
            "id": share.id,
            "agent_id": share.agent_id,
            "access_num": share.access_num,
            "share_url": self._build_share_url(share.id),
            "created_at": datetime_to_timestamp(share.created_at),
        }

    def get_share_agents_with_page(
            self,
            account: Account,
            agent_id: str,
            req: GetShareAgentsWithPageReq,
    ) -> PageModel:
        """
        * @Author Leon-liao
        * @Function:
        get_share_agents_with_page(account, agent_id, req)
        * @Description //分页查询当前账号下某智能体未停用的分享，并实时统计已用对话次数
        * @Date :2026/10/28 09:36:06
        * @Param:
        account: 当前登录账号；agent_id: 智能体主键；req: 分页请求
        * @return：PageModel，list 为字典列表，paginator 为分页信息
        """
        agent = self._get_owned_agent(agent_id, account.id)
        filters = (
            ShareAgent.account_id == account.id,
            ShareAgent.agent_id == agent.id,
            ShareAgent.deleted_at.is_(None),
        )
        statement = (
            select(ShareAgent)
            .where(*filters)
            .order_by(ShareAgent.created_at.desc(), ShareAgent.id.desc())
        )
        paginator = Paginator(db=self.db, req=req)
        shares = paginator.paginate(statement)
        items = []
        for share in shares:
            items.append({
                "id": share.id,
                "share_url": self._build_share_url(share.id),
                "has_password": bool(share.access_pwd),
                "access_num": share.access_num or 0,
                "accessed_num": self._count_user_messages(share.id),
                "shared_info": share.shared_info or "",
                "pay_url": share.pay_url or "",
                "status": 1,
                "created_at": datetime_to_timestamp(share.created_at),
                "updated_at": datetime_to_timestamp(share.updated_at),
            })
        return PageModel(list=items, paginator=paginator)

    def update_share_agent(
            self,
            account: Account,
            agent_id: str,
            share_id: str,
            req: UpdateShareAgentReq,
    ) -> dict:
        """
        * @Author Leon-liao
        * @Function:
        update_share_agent(account, agent_id, share_id, req)
        * @Description //增量更新分享字段；access_pwd 空串表示改为免密，非空则哈希后写入
        * @Date :2026/10/28 09:36:06
        * @Param:
        account: 当前登录账号；agent_id: 智能体主键；share_id: 分享主键；req: 增量更新请求
        * @return：{"updated": True}
        """
        share = self._get_owned_share(account.id, agent_id, share_id)
        updates = req.collect_updates()
        if "access_pwd" in updates:
            plain_pwd = updates["access_pwd"] or ""
            updates["access_pwd"] = (
                generate_password_hash(plain_pwd, method=_PWD_HASH_METHOD) if plain_pwd else ""
            )
        if updates:
            self.update(share, **updates)
        return {"updated": True}

    def delete_share_agent(self, account: Account, agent_id: str, share_id: str) -> dict:
        """
        * @Author Leon-liao
        * @Function:
        delete_share_agent(account, agent_id, share_id)
        * @Description //软删除分享：写入 deleted_at
        * @Date :2026/10/28 09:36:06
        * @Param:
        account: 当前登录账号；agent_id: 智能体主键；share_id: 分享主键
        * @return：{"deleted": True}
        """
        share = self._get_owned_share(account.id, agent_id, share_id)
        self.update(share, deleted_at=utc_now())
        return {"deleted": True}

    def get_share_landing(self, share_id: str) -> dict:
        """
        * @Author Leon-liao
        * @Function:
        get_share_landing(share_id)
        * @Description //免登录返回落地页信息；停用或配额用尽时标记 expired，不返回内部配置
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键，字符串
        * @return：落地页字典（share_id、agent_*、shared_info、need_password、pay_url、expired、expire_reason）
        """
        share = self._get_share_or_none(share_id)
        if share is None:
            raise NotFoundException("分享不存在或已失效")

        agent = self.db.session.query(Agent).filter(
            Agent.id == share.agent_id,
            Agent.deleted_at.is_(None),
        ).one_or_none()
        if agent is None:
            raise NotFoundException("分享不存在或已失效")

        expired = False
        expire_reason = ""
        if share.deleted_at is not None:
            expired = True
            expire_reason = "closed"
        else:
            accessed_num = self._count_user_messages(share.id)
            if share.access_num and share.access_num > 0 and accessed_num >= share.access_num:
                expired = True
                expire_reason = "access_exhausted"

        return {
            "share_id": share.id,
            "agent_name": agent.name or "",
            "agent_avatar": agent.avatar or "",
            "agent_status": 1 if agent.status == 1 else 0,
            "shared_info": share.shared_info or "",
            "need_password": bool(share.access_pwd),
            "pay_url": share.pay_url or "",
            "expired": expired,
            "expire_reason": expire_reason,
        }

    def access_share(self, share_id: str, pwd: str | None) -> dict:
        """
        * @Author Leon-liao
        * @Function:
        access_share(share_id, pwd)
        * @Description //校验分享、配额与密码后新建游客账号并签发 24h 分享态 token
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键；pwd: 访问密码，免密时可为空
        * @return：access_token、expire_at、account_id、share_id、token_type
        """
        share = self._get_active_share(share_id)
        accessed_num = self._count_user_messages(share.id)
        if share.access_num and share.access_num > 0 and accessed_num >= share.access_num:
            raise ForbiddenException("该分享的对话次数已用完")

        if share.access_pwd:
            if not pwd or not check_password_hash(share.access_pwd, pwd):
                raise ValidateErrorException("访问密码错误")

        guest = self.create(
            Account,
            name="访客",
            email=f"guest-{uuid4().hex}@share.local",
            avatar="",
            is_guest=1,
            password="",
            password_salt="",
        )
        expire_at = int((datetime.now() + timedelta(hours=_SHARE_TOKEN_HOURS)).timestamp())
        payload = {
            "sub": str(guest.id),
            "iss": "harnessmate",
            "scope": "share",
            "share_id": str(share.id),
            "exp": expire_at,
        }
        access_token = self.jwt_service.generate_token(payload)
        return {
            "access_token": access_token,
            "expire_at": expire_at,
            "account_id": guest.id,
            "share_id": share.id,
            "token_type": "Bearer",
        }

    def create_share_conversation(
            self,
            share: ShareAgent,
            guest_account: Account,
            req: CreateShareConversationReq,
    ) -> dict:
        """
        * @Author Leon-liao
        * @Function:
        create_share_conversation(share, guest_account, req)
        * @Description //为游客创建 type=2 的分享会话，thread_id 由服务端生成
        * @Date :2026/10/28 09:36:06
        * @Param:
        share: 分享记录；guest_account: 游客账号；req: 可选标题
        * @return：id、agent_id、thread_id、type、created_at
        """
        if share.deleted_at is not None:
            raise NotFoundException("分享不存在或已失效")
        agent = self.db.session.query(Agent).filter(
            Agent.id == share.agent_id,
            Agent.deleted_at.is_(None),
        ).one_or_none()
        if agent is None:
            raise NotFoundException("智能体不存在")

        title = (req.title.data or "").strip() or "访客对话"
        thread_id = f"share-{uuid4().hex[:12]}"
        conversation = self.create(
            Conversation,
            id=uuid4(),
            account_id=guest_account.id,
            agent_id=share.agent_id,
            share_agent_id=share.id,
            thread_id=thread_id,
            type=2,
            title=title,
            conversation_info={},
        )
        return {
            "id": conversation.id,
            "agent_id": conversation.agent_id,
            "thread_id": conversation.thread_id,
            "type": conversation.type,
            "created_at": datetime_to_timestamp(conversation.created_at),
        }

    def get_active_share_for_token(self, share_id: str) -> ShareAgent:
        """
        * @Author Leon-liao
        * @Function:
        get_active_share_for_token(share_id)
        * @Description //按主键取未停用分享，供 handler 校验分享态
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键
        * @return：ShareAgent 实例
        """
        return self._get_active_share(share_id)

    def _count_user_messages(self, share_id: UUID) -> int:
        """
        * @Author Leon-liao
        * @Function:
        _count_user_messages(share_id)
        * @Description //统计该分享下用户消息条数（join conversation.share_agent_id）
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键，UUID
        * @return：用户消息条数，整数
        """
        total = self.db.session.scalar(
            select(func.count(Message.id))
            .select_from(Message)
            .join(Conversation, Conversation.id == Message.conversation_id)
            .where(
                Conversation.share_agent_id == share_id,
                Message.message_role == "user",
            )
        )
        return int(total or 0)

    def _count_conversations(self, share_id: UUID) -> int:
        """
        * @Author Leon-liao
        * @Function:
        _count_conversations(share_id)
        * @Description //统计该分享下会话条数（含软删），列表暂不展示
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键，UUID
        * @return：会话条数，整数
        """
        total = self.db.session.scalar(
            select(func.count(Conversation.id)).where(
                Conversation.share_agent_id == share_id,
            )
        )
        return int(total or 0)

    def _build_share_url(self, share_id: UUID) -> str:
        """
        * @Author Leon-liao
        * @Function:
        _build_share_url(share_id)
        * @Description //用当前请求 host_url 拼分享落地页链接
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键
        * @return：分享 URL 字符串
        """
        base = (request.host_url or "").rstrip("/")
        return f"{base}/s/{share_id}"

    def _get_owned_agent(self, agent_id: str, account_id: UUID) -> Agent:
        """
        * @Author Leon-liao
        * @Function:
        _get_owned_agent(agent_id, account_id)
        * @Description //取当前账号下未软删的智能体，否则 not_found
        * @Date :2026/10/28 09:36:06
        * @Param:
        agent_id: 智能体主键；account_id: 账号主键
        * @return：Agent 实例
        """
        try:
            agent_uuid = UUID(str(agent_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise NotFoundException("智能体不存在") from exc
        agent = self.db.session.query(Agent).filter(
            Agent.id == agent_uuid,
            Agent.account_id == account_id,
            Agent.deleted_at.is_(None),
        ).one_or_none()
        if agent is None:
            raise NotFoundException("智能体不存在")
        return agent

    def _get_owned_share(self, account_id: UUID, agent_id: str, share_id: str) -> ShareAgent:
        """
        * @Author Leon-liao
        * @Function:
        _get_owned_share(account_id, agent_id, share_id)
        * @Description //取属于该账号与智能体且未停用的分享
        * @Date :2026/10/28 09:36:06
        * @Param:
        account_id: 账号主键；agent_id: 智能体主键；share_id: 分享主键
        * @return：ShareAgent 实例
        """
        agent = self._get_owned_agent(agent_id, account_id)
        try:
            share_uuid = UUID(str(share_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise NotFoundException("分享不存在") from exc
        share = self.db.session.query(ShareAgent).filter(
            ShareAgent.id == share_uuid,
            ShareAgent.account_id == account_id,
            ShareAgent.agent_id == agent.id,
            ShareAgent.deleted_at.is_(None),
        ).one_or_none()
        if share is None:
            raise NotFoundException("分享不存在")
        return share

    def _get_share_or_none(self, share_id: str) -> ShareAgent | None:
        """
        * @Author Leon-liao
        * @Function:
        _get_share_or_none(share_id)
        * @Description //按主键查分享，非法 UUID 视为不存在
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键
        * @return：ShareAgent 或 None
        """
        try:
            share_uuid = UUID(str(share_id))
        except (ValueError, TypeError, AttributeError):
            return None
        return self.db.session.query(ShareAgent).filter(
            ShareAgent.id == share_uuid,
        ).one_or_none()

    def _get_active_share(self, share_id: str) -> ShareAgent:
        """
        * @Author Leon-liao
        * @Function:
        _get_active_share(share_id)
        * @Description //取未停用分享，否则 not_found
        * @Date :2026/10/28 09:36:06
        * @Param:
        share_id: 分享主键
        * @return：ShareAgent 实例
        """
        share = self._get_share_or_none(share_id)
        if share is None or share.deleted_at is not None:
            raise NotFoundException("分享不存在或已失效")
        return share
