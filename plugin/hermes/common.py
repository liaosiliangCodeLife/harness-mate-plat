'''
*
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description //TODO
* @File: common.py
* @Time: 2026/07/01 14:30:00
* @All Rights Reserve By Brtc
'''

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt


DEFAULT_ACCOUNT_ID = "test-account"
DEFAULT_DEVICE_ID = "phone-test-001"
DEFAULT_HERMES_INSTANCE = "hermes-local"
DEFAULT_THREAD_ID = "thread-default"
DEFAULT_APP_WS_SESSION_ID = "app-phone-test-001"
DEFAULT_HERMES_WS_SESSION_ID = "hermes-test-account-hermes-local"
STREAM_CURSOR = " ▉"
# 与 ws_gateway internal/ws 心跳策略一致：客户端主动 Ping，Gateway 仅回复 Pong。
# ping_timeout 须小于 ping_interval（websocket-client 库约束）。
WS_CLIENT_PING_INTERVAL = 50
WS_CLIENT_PING_TIMEOUT = 30


def load_env_file(env_path: Path | None = None) -> dict[str, str]:
    """
    *
    * @Author Leon-liao
    * @Function: load_env_file(env_path: Path | None)
    * @Description //从 .env 文件加载键值对配置
    * @Date :2026/07/01 14:30:00
    * @Param: env_path: .env 文件路径，默认读取 ws_gateway/.env
    * @return：环境变量字典
    """
    if env_path is None:
        env_path = (
            Path(__file__).resolve().parent.parent
            / "ws_gateway"
            / ".env"
        )

    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def get_gateway_config() -> dict[str, str]:
    """
    *
    * @Author Leon-liao
    * @Function: get_gateway_config()
    * @Description //合并 .env 与进程环境变量，得到网关连接配置
    * @Date :2026/07/01 14:30:00
    * @Param: 无
    * @return：包含 host、port、jwt_secret 等字段的配置字典
    """
    env_values = load_env_file()
    host = os.getenv("WS_GATEWAY_HOST", env_values.get("WS_GATEWAY_HOST", "127.0.0.1"))
    port = os.getenv("WS_GATEWAY_PORT", env_values.get("WS_GATEWAY_PORT", "8765"))
    jwt_secret = os.getenv("JWT_SECRET", env_values.get("JWT_SECRET", "gwASVdQIW8vDJJ3Z"))
    if not jwt_secret:
        raise ValueError("未找到 JWT_SECRET，请配置 ws_gateway/.env 或环境变量")
    return {
        "host": host,
        "port": str(port),
        "jwt_secret": jwt_secret,
    }


def build_session_token(
    jwt_secret: str,
    ws_session_id: str,
    expire_hours: int = 24,
) -> str:
    """
    *
    * @Author Leon-liao
    * @Function: build_session_token(jwt_secret, ws_session_id, expire_hours)
    * @Description //生成 WS 网关连接使用的 JWT（仅含 ws_session_id）
    * @Date :2026/07/02 10:00:00
    * @Param: jwt_secret: 签名密钥; ws_session_id: 会话唯一 ID; expire_hours: 过期小时数
    * @return：JWT 字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        "ws_session_id": ws_session_id,
        "exp": now + timedelta(hours=expire_hours),
        "iat": now,
    }
    return jwt.encode(payload, jwt_secret, algorithm="HS256")


def build_p2p_envelope(to: str, data: dict[str, object]) -> dict[str, object]:
    """
    *
    * @Author Leon-liao
    * @Function: build_p2p_envelope(to, data)
    * @Description //构造网关点对点消息信封
    * @Date :2026/07/02 10:00:00
    * @Param: to: 目标 ws_session_id; data: 业务负载
    * @return：网关 WSMessage 字典
    """
    return {"to": to, "data": data}


def build_hermes_token(
    jwt_secret: str,
    account_id: str = DEFAULT_ACCOUNT_ID,
    instance: str = DEFAULT_HERMES_INSTANCE,
    expire_hours: int = 24,
) -> str:
    """
    *
    * @Author Leon-liao
    * @Function: build_hermes_token(jwt_secret, account_id, instance, expire_hours)
    * @Description //生成 Hermes 测试端连接 JWT（兼容旧脚本参数，映射为 ws_session_id）
    * @Date :2026/07/01 14:30:00
    * @Param: jwt_secret: 签名密钥; account_id: 账号 ID; instance: Hermes 实例 ID; expire_hours: 过期小时数
    * @return：JWT 字符串
    """
    del account_id
    return build_session_token(
        jwt_secret,
        ws_session_id=DEFAULT_HERMES_WS_SESSION_ID,
        expire_hours=expire_hours,
    )


def build_device_token(
    jwt_secret: str,
    account_id: str = DEFAULT_ACCOUNT_ID,
    device_id: str = DEFAULT_DEVICE_ID,
    expire_hours: int = 24,
) -> str:
    """
    *
    * @Author Leon-liao
    * @Function: build_device_token(jwt_secret, account_id, device_id, expire_hours)
    * @Description //生成 App 测试端连接 JWT（兼容旧脚本参数，默认 ws_session_id 与 device_id 对齐）
    * @Date :2026/07/01 14:30:00
    * @Param: jwt_secret: 签名密钥; account_id: 账号 ID; device_id: 设备 ID; expire_hours: 过期小时数
    * @return：JWT 字符串
    """
    del account_id
    ws_session_id = device_id if device_id.startswith("app-") else f"app-{device_id}"
    return build_session_token(
        jwt_secret,
        ws_session_id=ws_session_id,
        expire_hours=expire_hours,
    )


def pretty_json(data: object) -> str:
    """
    *
    * @Author Leon-liao
    * @Function: pretty_json(data)
    * @Description //将对象格式化为易读 JSON 字符串
    * @Date :2026/07/01 14:30:00
    * @Param: data: 任意可 JSON 序列化对象
    * @return：格式化后的 JSON 文本
    """
    return json.dumps(data, ensure_ascii=False, indent=2)


def now_text() -> str:
    """
    *
    * @Author Leon-liao
    * @Function: now_text()
    * @Description //返回当前本地时间文本
    * @Date :2026/07/01 14:30:00
    * @Param: 无
    * @return：时间字符串
    """
    return time.strftime("%H:%M:%S")


def parse_data_field(raw_data: object) -> dict[str, object]:
    """
    *
    * @Author Leon-liao
    * @Function: parse_data_field(raw_data)
    * @Description //解析 reply.data（支持 dict 或 JSON 字符串）
    * @Date :2026/07/01 15:30:00
    * @Param: raw_data: reply 消息的 data 字段
    * @return：解析后的字典
    """
    if isinstance(raw_data, dict):
        return raw_data
    if isinstance(raw_data, str) and raw_data.strip():
        try:
            parsed = json.loads(raw_data)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {"text": raw_data}
    return {}


def extract_reply_text(data: dict[str, object]) -> str:
    """
    *
    * @Author Leon-liao
    * @Function: extract_reply_text(data)
    * @Description //从 reply.data 中提取正文，兼容多种字段名
    * @Date :2026/07/01 15:30:00
    * @Param: data: 已解析的 data 字典
    * @return：消息正文
    """
    for key in ("text", "content", "message", "body"):
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def extract_reply_reasoning(data: dict[str, object]) -> str:
    """
    *
    * @Author Leon-liao
    * @Function: extract_reply_reasoning(data)
    * @Description //从 reply.data 中提取思考过程文本
    * @Date :2026/07/01 15:30:00
    * @Param: data: 已解析的 data 字典
    * @return：思考过程文本
    """
    for key in ("reasoning", "thinking", "thought", "reasoning_content"):
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def strip_stream_cursor(text: str) -> str:
    """
    *
    * @Author Leon-liao
    * @Function: strip_stream_cursor(text)
    * @Description //去掉 Hermes 流式光标字符，便于增量比对与展示
    * @Date :2026/07/01 20:50:00
    * @Param: text: 原始流式文本
    * @return：去掉尾部光标后的文本
    """
    if text.endswith(STREAM_CURSOR):
        return text[: -len(STREAM_CURSOR)]
    return text


def extract_reply_fields(data: object) -> dict[str, object]:
    """
    *
    * @Author Leon-liao
    * @Function: extract_reply_fields(data)
    * @Description //从 Hermes reply.data 中提取状态、正文与思考内容
    * @Date :2026/07/01 15:10:00
    * @Param: data: reply 消息的 data 字段
    * @return：包含 status/text/reasoning/delta/message_id 的字典
    """
    parsed = parse_data_field(data)
    if not parsed and data is not None and not isinstance(data, dict):
        return {
            "status": "",
            "text": pretty_json(data),
            "reasoning": "",
            "delta": False,
            "message_id": "",
            "done": False,
        }

    return {
        "status": str(parsed.get("status") or ""),
        "text": extract_reply_text(parsed),
        "reasoning": extract_reply_reasoning(parsed),
        "delta": bool(parsed.get("delta")),
        "message_id": str(parsed.get("message_id") or parsed.get("msg_id") or ""),
        "done": bool(parsed.get("done")),
    }
