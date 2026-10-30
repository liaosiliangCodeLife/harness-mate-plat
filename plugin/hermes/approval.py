'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //Hermes 插件审批载荷：action / risk_level / payload_digest（与平台、DSH 对齐）
* @File: approval.py
* @Time: 2026/10/29 19:35:00
* @All Rights Reserve By Brtc
'''

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, Optional, Tuple


# 未命中一律 L3（fail-closed），与 api/internal/lib/risk.py 语义一致
DEFAULT_RISK = 3

# 工具名启发式 → (action, risk_level)
_TOOL_RULES: Tuple[Tuple[re.Pattern, str, int], ...] = (
    (re.compile(r"(^|[._-])(shell|terminal|bash|exec|command)([._-]|$)", re.I), "exec.shell", 2),
    (re.compile(r"(^|[._-])(delete|remove|rm|unlink|trash)([._-]|$)", re.I), "fs.delete", 3),
    (re.compile(r"(^|[._-])(write|edit|create|patch|mkdir|append)([._-]|$)", re.I), "fs.write", 1),
    (re.compile(r"(^|[._-])(install|package|npm|pip|yarn|pnpm)([._-]|$)", re.I), "package.install", 2),
    (re.compile(r"(^|[._-])(send|message|reply|post|publish|email)([._-]|$)", re.I), "message.send", 3),
    (re.compile(r"(^|[._-])(fetch|http|request|curl|wget|browse)([._-]|$)", re.I), "http.request", 2),
    (re.compile(r"(^|[._-])(deploy|release)([._-]|$)", re.I), "deploy.production", 3),
    (re.compile(r"(^|[._-])(read|list|cat|ls|grep|search|view)([._-]|$)", re.I), "fs.read", 0),
)

# App ↔ Hermes 选择映射（与 DSH #approval 协议一致）
OPTION_TO_CHOICE = {
    "allow-once": "once",
    "reject-once": "deny",
}
CHOICE_TO_OPTION = {
    "once": "allow-once",
    "deny": "reject-once",
    "session": "allow-once",
    "always": "allow-once",
}

DEFAULT_APPROVAL_TIMEOUT_MS = 300000


def canonical_json(value: Any) -> str:
    """
    * @Author Leon-liao
    * @Function:
    canonical_json(value)
    * @Description //键排序 + 不转义非 ASCII + 分隔符无空格，与平台/DSH 一致
    * @Date :2026/10/29 19:35:00
    * @Param:
    value: 任意可 JSON 化对象
    * @return：规范化 JSON 字符串
    """
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_payload_digest(payload: Optional[dict]) -> str:
    """
    * @Author Leon-liao
    * @Function:
    compute_payload_digest(payload)
    * @Description //对 payload 做规范化 JSON 后的 sha256 hex
    * @Date :2026/10/29 19:35:00
    * @Param:
    payload: 参数字典，None 视为空对象
    * @return：64 位 hex 摘要
    """
    raw = canonical_json(payload or {})
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha256_hex(text: Any) -> str:
    """
    * @Author Leon-liao
    * @Function:
    _sha256_hex(text)
    * @Description //对任意文本做 sha256 hex
    * @Date :2026/10/29 19:35:00
    * @Param:
    text: 任意值，转字符串后哈希
    * @return：64 位 hex
    """
    return hashlib.sha256(str(text or "").encode("utf-8")).hexdigest()


def _short_text(text: Any, max_len: int = 60) -> str:
    """
    * @Author Leon-liao
    * @Function:
    _short_text(text, max_len)
    * @Description //压缩空白并截断，用于人话标题
    * @Date :2026/10/29 19:35:00
    * @Param:
    text: 原文；max_len: 最大长度
    * @return：截断后的短文本
    """
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(cleaned) > max_len:
        return cleaned[:max_len] + "…"
    return cleaned


def resolve_action(tool_name: str) -> Tuple[str, int]:
    """
    * @Author Leon-liao
    * @Function:
    resolve_action(tool_name)
    * @Description //按工具名启发式映射 action 与 risk_level，未命中 L3
    * @Date :2026/10/29 19:35:00
    * @Param:
    tool_name: 工具名或动作名
    * @return：(action, risk_level)
    """
    name = str(tool_name or "").strip()
    for pattern, action, risk in _TOOL_RULES:
        if pattern.search(name):
            return action, risk
    if name:
        return f"tool.{name}", DEFAULT_RISK
    return "tool.unknown", DEFAULT_RISK


def build_payload(action: str, args: Optional[dict]) -> dict:
    """
    * @Author Leon-liao
    * @Function:
    build_payload(action, args)
    * @Description //按 action 抽取决定危险程度的字段（不放全文）
    * @Date :2026/10/29 19:35:00
    * @Param:
    action: 动作名；args: 原始参数字典
    * @return：摘要 payload
    """
    raw = args or {}
    path = raw.get("path") or raw.get("file") or raw.get("filePath") or raw.get("target") or ""
    if action == "exec.shell":
        return {
            "cmd": str(raw.get("command") or raw.get("cmd") or raw.get("script") or ""),
            "cwd": str(raw.get("cwd") or raw.get("workdir") or ""),
        }
    if action == "fs.delete":
        return {"path": str(path), "recursive": bool(raw.get("recursive"))}
    if action == "fs.write":
        return {"path": str(path), "bytes": int(raw.get("bytes") or raw.get("size") or 0)}
    if action == "package.install":
        packages = raw.get("packages")
        if not isinstance(packages, list):
            packages = [str(raw.get("package") or raw.get("name") or "")]
        return {
            "manager": str(raw.get("manager") or raw.get("packageManager") or ""),
            "packages": packages,
        }
    if action == "message.send":
        return {
            "platform": str(raw.get("platform") or raw.get("channel") or ""),
            "to": str(raw.get("to") or raw.get("chatId") or raw.get("target") or ""),
            "text_digest": _sha256_hex(raw.get("text") or raw.get("content") or raw.get("message") or ""),
        }
    if action == "http.request":
        return {
            "method": str(raw.get("method") or "GET").upper(),
            "url_digest": _sha256_hex(raw.get("url") or ""),
        }
    return {"tool": action, "args_digest": _sha256_hex(canonical_json(raw))}


def build_title(action: str, payload: dict, fallback: str = "") -> str:
    """
    * @Author Leon-liao
    * @Function:
    build_title(action, payload, fallback)
    * @Description //生成含参数的人话审批标题
    * @Date :2026/10/29 19:35:00
    * @Param:
    action: 动作名；payload: 摘要；fallback: 兜底文案
    * @return：人话标题
    """
    if action == "exec.shell":
        cmd = payload.get("cmd") or ""
        return f"执行命令 {_short_text(cmd, 80)}" if cmd else "执行命令"
    if action == "fs.delete":
        path = payload.get("path") or ""
        return f"删除 {path}" if path else "删除文件"
    if action == "fs.write":
        path = payload.get("path") or ""
        return f"写入 {path}" if path else "写入文件"
    if action == "package.install":
        pkgs = " ".join(str(p) for p in (payload.get("packages") or []))
        return f"安装依赖 {_short_text(pkgs, 60)}".strip()
    if action == "message.send":
        target = payload.get("to") or payload.get("platform") or "目标会话"
        return f"向 {target} 发送消息"
    if action == "http.request":
        return f"发起 {payload.get('method') or 'HTTP'} 请求"
    return fallback or f"执行 {action}"


def build_approval_meta(
    *,
    command: str = "",
    description: str = "",
    tool_name: str = "",
    args: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    * @Author Leon-liao
    * @Function:
    build_approval_meta(command, description, tool_name, args)
    * @Description //从 Hermes ExecApprovalPrompt 字段拼装平台审批元数据
    * @Date :2026/10/29 19:35:00
    * @Param:
    command: 待执行命令；description: 审批说明；tool_name: 可选工具名；args: 可选参数
    * @return：含 action/risk_level/payload/payload_digest/title 的字典
    """
    name = (tool_name or "").strip() or ("shell" if command else "unknown")
    merged: Dict[str, Any] = dict(args or {})
    if command and not (merged.get("command") or merged.get("cmd") or merged.get("script")):
        merged["command"] = command
    action, risk_level = resolve_action(name if not command else "exec.shell")
    # Hermes 的 exec 审批入口本质是 shell 命令
    if command:
        action, risk_level = "exec.shell", 2
    payload = build_payload(action, merged)
    digest = compute_payload_digest(payload)
    title = build_title(action, payload, description or name)
    return {
        "action": action,
        "risk_level": risk_level,
        "payload": payload,
        "payload_digest": digest,
        "title": title,
    }


def default_approval_options() -> list:
    """
    * @Author Leon-liao
    * @Function:
    default_approval_options()
    * @Description //返回 App 侧标准审批选项（与 DSH 一致）
    * @Date :2026/10/29 19:35:00
    * @Param:
    无
    * @return：options 列表
    """
    return [
        {"option_id": "allow-once", "kind": "allow_once", "name": "允许一次"},
        {"option_id": "reject-once", "kind": "reject_once", "name": "拒绝"},
    ]
