#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //按 bot_id 向网关提供该智能体的验签密钥
* @File: gateway_handler.py
* @Time: 2026/10/25 22:42:10
* @All Rights Reserve By Brtc
"""
import hmac
import logging
from dataclasses import dataclass

from flask import jsonify, request
from injector import inject
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from config import Config
from internal.exception import NotFoundException
from internal.model import Agent
from pkg.response import HttpCode, success_json
from pkg.sqlalchemy import SQLAlchemy

logger = logging.getLogger(__name__)


@inject
@dataclass
class GatewayHandler:
    """网关服务间接口。不走用户登录态"""

    db: SQLAlchemy
    config: Config

    def get_bot_key(self):
        """
        * @Author Leon-liao
        * @Function: get_bot_key()
        * @Description //校验服务间令牌，按 bot_id 返回未删除智能体所属网关的 gateway_key
        * @Date :2026/10/25 22:42:10
        * @Param: 无。令牌取请求头 X-Internal-Token，bot_id 取 query
        * @return：令牌不匹配返回 HTTP 403，code=forbidden，message="内部令牌无效"，data={}。bot_id 为空返回 HTTP 400，code=validate_error，message="bot_id 不能为空"，data={}。智能体不存在返回 HTTP 404，code=not_found，message="bot_id 对应的智能体不存在"。未绑定网关返回 HTTP 404，code=not_found，message="智能体未绑定网关"。成功返回 HTTP 200，code=success，data 含 bot_id、key、agent_id、account_id、peer_id。未预期异常返回 HTTP 500，code=fail，message="获取 bot 密钥失败"，data={}
        """
        try:
            # 1.服务间令牌。网关调用，不走用户登录
            provided = request.headers.get("X-Internal-Token", "")
            expected = str(self.config.INTERNAL_TOKEN or "")
            if not isinstance(provided, str):
                provided = ""
            token_ok = hmac.compare_digest(
                provided.encode("utf-8"),
                expected.encode("utf-8"),
            )
            if not token_ok:
                return jsonify({
                    "code": HttpCode.FORBIDDEN,
                    "message": "内部令牌无效",
                    "data": {},
                }), 403

            # 2.ws_session_id 来自 query。插件连接时是 bot_id，Hub 连接时是 peer_id，两种都要认
            session_id = request.args.get("session_id") or request.args.get("bot_id") or ""
            if not isinstance(session_id, str):
                session_id = ""
            session_id = session_id.strip()
            if session_id == "":
                return jsonify({
                    "code": HttpCode.VALIDATE_ERROR,
                    "message": "session_id 不能为空",
                    "data": {},
                }), 400

            # 3.只认未删除的智能体，并带出所属网关。上游身份可能是 bot_id 也可能是 peer_id
            agent = self.db.session.query(Agent).options(
                joinedload(Agent.gateway),
            ).filter(
                or_(Agent.bot_id == session_id, Agent.peer_id == session_id),
                Agent.deleted_at.is_(None),
            ).one_or_none()
            if agent is None:
                raise NotFoundException("session_id 对应的智能体不存在")

            # 4.没有网关，或密钥为空，都不能拿去验签
            gateway = agent.gateway
            raw_key = ""
            if gateway is not None and gateway.gateway_key is not None:
                raw_key = str(gateway.gateway_key)
            if gateway is None or raw_key.strip() == "":
                raise NotFoundException("智能体未绑定网关")

            # 5.把验签材料和归属一起返回。密钥按库里的原值返回
            return success_json({
                "bot_id": str(agent.bot_id or ""),
                "key": raw_key,
                "agent_id": str(agent.id),
                "account_id": str(agent.account_id),
                "peer_id": str(agent.peer_id or ""),
            })
        except NotFoundException as exc:
            return jsonify({
                "code": HttpCode.NOT_FOUND,
                "message": exc.message or "bot_id 对应的智能体不存在",
                "data": {},
            }), 404
        except Exception:
            logger.exception("获取 bot 密钥失败")
            return jsonify({
                "code": HttpCode.FAIL,
                "message": "获取 bot 密钥失败",
                "data": {},
            }), 500
