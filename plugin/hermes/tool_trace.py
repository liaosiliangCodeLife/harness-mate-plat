'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //工具调用轨迹缓冲：采集 GatewayAgent 的 tool 事件，供 reply 帧附带 agent_thoughts
* @File: tool_trace.py
* @Time: 2026/10/30 09:10:00
* @All Rights Reserve By Brtc
'''

from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Any

MAX_STEPS = 30
TTL_SECONDS = 600
MAX_OBSERVATION = 300
MAX_TOOL_INPUT = 500

_lock = threading.Lock()
_inflight: dict[str, dict] = {}
_steps: list[dict] = []


def _truncate(text: str, limit: int) -> str:
    """
    * @Author Leon-liao
    * @Function:
    _truncate(text, limit)
    * @Description //按字符长度截断字符串
    * @Date :2026/10/30 09:10:00
    * @Param:
    text: 原文；limit: 最大长度
    * @return：截断后的字符串
    """
    value = text or ""
    if len(value) <= limit:
        return value
    return value[:limit]


def _serialize_tool_input(args: Any) -> str:
    """
    * @Author Leon-liao
    * @Function:
    _serialize_tool_input(args)
    * @Description //将工具入参序列化为截断后的 JSON 字符串
    * @Date :2026/10/30 09:10:00
    * @Param:
    args: 工具参数（通常是 dict）
    * @return：截断后的字符串
    """
    try:
        if isinstance(args, dict):
            raw = json.dumps(args, ensure_ascii=False, default=str)
        else:
            raw = json.dumps(args if args is not None else {}, ensure_ascii=False, default=str)
    except Exception:
        raw = str(args)
    return _truncate(raw, MAX_TOOL_INPUT)


def _serialize_observation(result: Any, is_error: bool) -> str:
    """
    * @Author Leon-liao
    * @Function:
    _serialize_observation(result, is_error)
    * @Description //将工具结果序列化为 observation，错误时加前缀
    * @Date :2026/10/30 09:10:00
    * @Param:
    result: 工具返回；is_error: 是否失败
    * @return：截断后的 observation
    """
    try:
        if isinstance(result, str):
            raw = result
        else:
            raw = json.dumps(result, ensure_ascii=False, default=str)
    except Exception:
        raw = str(result)
    if is_error:
        raw = f"错误：{raw}"
    return _truncate(raw, MAX_OBSERVATION)


def record_start(call_id: str, name: str, args: dict | None) -> None:
    """
    * @Author Leon-liao
    * @Function:
    record_start(call_id, name, args)
    * @Description //记录工具调用开始
    * @Date :2026/10/30 09:10:00
    * @Param:
    call_id: 调用 id；name: 工具名；args: 入参
    * @return：无
    """
    with _lock:
        _inflight[str(call_id or "")] = {
            "name": name or "tool",
            "args": args if isinstance(args, dict) else {},
            "started": time.time(),
        }


def record_complete(
        call_id: str,
        name: str,
        duration: float,
        is_error: bool,
        result: Any,
) -> None:
    """
    * @Author Leon-liao
    * @Function:
    record_complete(call_id, name, duration, is_error, result)
    * @Description //记录工具调用完成，写入待 drain 的步骤列表
    * @Date :2026/10/30 09:10:00
    * @Param:
    call_id: 调用 id；name: 工具名；duration: 耗时秒；is_error: 是否失败；result: 返回值
    * @return：无
    """
    key = str(call_id or "")
    with _lock:
        started_meta = _inflight.pop(key, None)
        args = {}
        if isinstance(started_meta, dict):
            maybe_args = started_meta.get("args")
            if isinstance(maybe_args, dict):
                args = maybe_args
            if not name:
                name = str(started_meta.get("name") or "tool")
        step = {
            "id": key or str(uuid.uuid4()),
            "event": "agent_action",
            "thought": "",
            "tool": name or "tool",
            "tool_input": _serialize_tool_input(args),
            "observation": _serialize_observation(result, bool(is_error)),
            "latency": round(float(duration or 0), 2),
            "created_at": int(time.time()),
        }
        _steps.append(step)
        overflow = len(_steps) - MAX_STEPS
        if overflow > 0:
            del _steps[:overflow]


def drain() -> list[dict]:
    """
    * @Author Leon-liao
    * @Function:
    drain()
    * @Description //取出并清空待上报步骤；顺带丢弃超时残留
    * @Date :2026/10/30 09:10:00
    * @Param:
    无
    * @return：步骤列表
    """
    now = int(time.time())
    cutoff = now - TTL_SECONDS
    with _lock:
        kept = [
            item for item in _steps
            if int(item.get("created_at") or 0) >= cutoff
        ]
        _steps.clear()
        return kept


def clear() -> None:
    """
    * @Author Leon-liao
    * @Function:
    clear()
    * @Description //清空 inflight 与待上报步骤
    * @Date :2026/10/30 09:10:00
    * @Param:
    无
    * @return：无
    """
    with _lock:
        _inflight.clear()
        _steps.clear()
