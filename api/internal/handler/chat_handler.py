#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //发送聊天消息，并把该账号的下行帧以 SSE 推给浏览器
* @File: chat_handler.py
* @Time: 2026/10/23 23:36:12
* @All Rights Reserve By Brtc
"""
import hmac
import logging
from dataclasses import dataclass

from flask import Response, jsonify, request
from flask_login import login_required, current_user
from injector import inject
from redis import Redis

from internal.schema.chat_schema import SendMessageReq
from internal.service import ChatService
from pkg.response import HttpCode, success_json, validate_error_json

logger = logging.getLogger(__name__)


def _validate_json_object():
    """
    * @Author Leon-liao
    * @Function: _validate_json_object()
    * @Description //POST 携带请求体时必须是 JSON 对象，否则返回参数校验错误
    * @Date :2026/10/23 23:21:05
    * @Param: 无。读取当前请求的 body
    * @return：合法或缺省时返回 None；不是 JSON 对象时返回校验错误响应
    """
    if not request.data and not request.is_json:
        return None
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return validate_error_json({"body": ["请求体必须是JSON对象"]})
    return None


@inject
@dataclass
class ChatHandler:
    """聊天消息处理器"""

    chat_service: ChatService
    redis_client: Redis

    @login_required
    def send_message(self, agent_id: str, thread_id: str):
        """
        * @Author Leon-liao
        * @Function: send_message(agent_id: str, thread_id: str)
        * @Description //校验当前用户的发送请求，并交给 ChatService 先落库再转发到 Hub。agent_id / thread_id 来自 URL 路径，body 带 text、message_id，files 可选
        * @Date :2026/10/25 22:24:33
        * @Param: agent_id: URL 路径中的智能体标识，字符串；thread_id: URL 路径中的会话线程标识，字符串。账号取当前登录用户，text、message_id、files 取 JSON 请求体
        * @return：success_json，data 为 {"sent": true}。校验失败返回 validate_error_json
        """
        invalid_body = _validate_json_object()
        if invalid_body is not None:
            return invalid_body
        req = SendMessageReq()
        if not req.validate():
            return validate_error_json(req.errors)

        data = self.chat_service.send_message(
            current_user,
            agent_id,
            thread_id,
            req.text.data,
            req.message_id.data,
            req.files.data,
        )
        return success_json(data)

    @login_required
    def stream(self):
        """
        * @Author Leon-liao
        * @Function: stream()
        * @Description //订阅当前账号的 Redis 频道，把下行帧以 SSE 持续推给浏览器
        * @Date :2026/10/23 23:36:12
        * @Param: 无。账号取当前登录用户的 id
        * @return：text/event-stream 响应。有帧时输出 data 行，空闲时输出心跳注释
        """
        # 1.进入生成器前取好账号。生成器里不再碰请求上下文
        account_id = str(current_user.id)
        conn = self.redis_client

        def generate():
            """
            * @Author Leon-liao
            * @Function: generate()
            * @Description //从账号频道读取帧并产出 SSE 文本，直到客户端断开
            * @Date :2026/10/23 23:36:12
            * @Param: 无。频道名和 Redis 客户端由外层闭包传入
            * @return：逐条产出 SSE 事件。客户端断开时由生成器退出触发 finally
            """
            # 2.pubsub 从现有连接池借一条连接，不另建连接池
            pubsub = conn.pubsub()
            try:
                pubsub.subscribe(f"stream:{account_id}")
                # 3.这条流覆盖该账号全部会话。超时只发心跳，不能 return
                while True:
                    msg = pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=20,
                    )
                    if msg is None:
                        yield ": ping\n\n"
                        continue
                    payload = msg["data"]
                    if isinstance(payload, bytes):
                        payload = payload.decode("utf-8")
                    yield f"data: {payload}\n\n"
            finally:
                pubsub.close()

        response = Response(generate(), mimetype="text/event-stream")
        response.headers["Cache-Control"] = "no-cache"
        response.headers["X-Accel-Buffering"] = "no"
        response.headers["Connection"] = "keep-alive"
        return response

    def internal_create_message(self):
        """
        * @Author Leon-liao
        * @Function: internal_create_message()
        * @Description //校验服务间令牌，并把 Hub 回写的 done 帧交给 ChatService 落库
        * @Date :2026/10/25 20:50:44
        * @Param: 无。令牌取请求头 X-Internal-Token，帧取 JSON 请求体
        * @return：令牌不匹配返回 HTTP 403，code=FORBIDDEN，message="内部令牌无效"，data={}。请求体不是 JSON 对象返回 HTTP 400，code=VALIDATE_ERROR，message="请求体必须是JSON对象"，data={}。不是 done 帧，或会话不存在 / account_id 非法（save_reply 返回 stored=false）返回 HTTP 200，code=SUCCESS，data={"stored": false}。落库成功返回 HTTP 200，code=SUCCESS，data={"stored": true}。未预期异常返回 HTTP 500，code=FAIL，message="内部消息写入失败"，data={}
        """
        try:
            # 1.服务间令牌。这里不能走用户登录：用户离线后 Hub 仍要回写
            provided = request.headers.get("X-Internal-Token", "")
            expected = str(self.chat_service.config.INTERNAL_TOKEN or "")
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

            # 2.请求体必须是 JSON 对象。结构不对的完成帧才落到下面的 stored=false
            body = request.get_json(silent=True)
            if not isinstance(body, dict):
                return jsonify({
                    "code": HttpCode.VALIDATE_ERROR,
                    "message": "请求体必须是JSON对象",
                    "data": {},
                }), 400

            # 3.只认完整网关下行帧。结构不对或尚未完成，都不落库
            envelope = body.get("data")
            inner = envelope.get("data") if isinstance(envelope, dict) else None
            if not isinstance(inner, dict) or inner.get("done") is not True:
                return jsonify({
                    "code": HttpCode.SUCCESS,
                    "message": "",
                    "data": {"stored": False},
                }), 200

            # 4.账号、线程在业务信封上，正文和幂等键在内层 data
            result = self.chat_service.save_reply(
                account_id=envelope.get("account_id"),
                thread_id=envelope.get("thread_id"),
                message_id=inner.get("message_id"),
                content=inner.get("text"),
                files=inner.get("files"),
            )
            return jsonify({
                "code": HttpCode.SUCCESS,
                "message": "",
                "data": result,
            }), 200
        except Exception:
            logger.exception("内部消息写入失败")
            return jsonify({
                "code": HttpCode.FAIL,
                "message": "内部消息写入失败",
                "data": {},
            }), 500
