#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2026/9/30 08:40:00
@Author  : liaosiliang1234@126.com
@File    : identifier.py
"""
import base64
import hashlib
import random
import time
import uuid

_ID_PREFIX = {
    "peer_id": "pr-",
    "bot_id": "bt-",
    "ws_session_id": "ws-",
    "thread_id": "td-",
}


def generate_agent_identifier(account_id: str, agent_id: str, id_type: str) -> str:
    """按类型生成智能体标识。

    thread_id 直接拼接毫秒时间戳；其余类型用账号、智能体、时间戳与随机数做 md5，
    将 32 位十六进制散列做 base64 编码后取前 29 位，再加前缀。未提供 agent_id 时，
    用随机 uuid 参与散列。

    Args:
        account_id: 当前登录账号 id 的字符串。
        agent_id: 参与散列的智能体 id；空字符串表示未传，改用随机 uuid。
        id_type: 标识类型，取 peer_id、bot_id、ws_session_id、thread_id。

    Returns:
        带类型前缀的标识字符串。
    """
    timestamp_ms = int(time.time() * 1000)
    prefix = _ID_PREFIX[id_type]
    if id_type == "thread_id":
        return f"{prefix}{timestamp_ms}"

    resolved_agent_id = agent_id or str(uuid.uuid4())
    raw = f"{account_id}{resolved_agent_id}{timestamp_ms}{random.randint(100000, 999999)}"
    digest_hex = hashlib.md5(raw.encode("utf-8")).hexdigest()
    encoded = base64.b64encode(digest_hex.encode("utf-8")).decode("ascii")
    return f"{prefix}{encoded[:29]}"
