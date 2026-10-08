'''
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description harness_mate 平台适配器，对接 Go WS 网关 /ws 端点（ws_session_id 点对点）
* @File: adapter.py
* @Time: 2026/06/30 18:30:00
* @All Rights Reserve By Brtc
'''

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import url2pathname

import jwt
import websockets
from websockets.exceptions import ConnectionClosed

try:
    from .file_upload import (
        OpenApiUploadError,
        extension_of,
        media_kind_for_name,
        mime_type_for_name,
        resolve_upload_url,
        upload_open_api_file,
    )
except ImportError:  # 插件以单文件方式加载时走同目录导入
    from file_upload import (  # type: ignore
        OpenApiUploadError,
        extension_of,
        media_kind_for_name,
        mime_type_for_name,
        resolve_upload_url,
        upload_open_api_file,
    )

from gateway.config import Platform, PlatformConfig
from gateway.platforms.base import (
    BasePlatformAdapter,
    MessageEvent,
    MessageType,
    SendResult,
)
from gateway.platforms.helpers import MessageDeduplicator

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4000
DEDUP_MAX_SIZE = 1000
RECONNECT_MIN_DELAY = float(os.getenv("HARNESS_MATE_RECONNECT_MIN_DELAY", "1"))
RECONNECT_MAX_DELAY = float(os.getenv("HARNESS_MATE_RECONNECT_MAX_DELAY", "30"))
TYPING_THROTTLE_SECONDS = float(os.getenv("HARNESS_MATE_TYPING_INTERVAL", "8"))
HARNESS_MATE_PING_INTERVAL = float(os.getenv("HARNESS_MATE_PING_INTERVAL", "50"))
HARNESS_MATE_PING_TIMEOUT = float(os.getenv("HARNESS_MATE_PING_TIMEOUT", "90"))

# WS 网关统一点对点 WebSocket 端点（本地开发，token 由 adapter 动态拼接）
WS_GATEWAY_WS_URL = "wss://ws-agent.alltman.com:1443/ws"

# harness_mate 业务层消息类型（放在网关 data 负载内，网关本身不解析）
TYPE_MESSAGE = "message"
TYPE_REPLY = "reply"


def _cfg_get(config, key: str, default: str = "") -> str:
    """
    * @Author Leon-liao
    * @Function: _cfg_get(config, key, default)
    * @Description //从 PlatformConfig 或 dict 配置中读取字符串项
    * @Date :2026/06/30 18:30:00
    * @Param: config: 平台配置对象；key: 配置键名；default: 默认值
    * @return：配置值字符串
    """
    if isinstance(config, dict):
        value = config.get(key, default)
        return str(value) if value is not None else default
    extra = getattr(config, "extra", None) or {}
    if key in extra and extra[key]:
        return str(extra[key])
    top_level = getattr(config, key, None)
    if top_level:
        return str(top_level)
    return default


def _cfg_get_list(config, key: str, env_var: str = "") -> List[str]:
    """
    * @Author Leon-liao
    * @Function: _cfg_get_list(config, key, env_var)
    * @Description //从配置或环境变量读取逗号分隔列表
    * @Date :2026/06/30 18:30:00
    * @Param: config: 平台配置；key: extra 键名；env_var: 环境变量名
    * @return：字符串列表
    """
    extra = getattr(config, "extra", None) or {}
    raw = extra.get(key)
    if raw is None and env_var:
        raw = os.getenv(env_var, "")
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(raw, (list, tuple, set)):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def _entry_matches(entries: List[str], target: str) -> bool:
    """
    * @Author Leon-liao
    * @Function: _entry_matches(entries, target)
    * @Description //判断 target 是否命中白名单（支持 *）
    * @Date :2026/06/30 18:30:00
    * @Param: entries: 白名单条目；target: 待匹配值
    * @return：命中返回 True
    """
    normalized = str(target or "").strip().lower()
    for entry in entries:
        item = str(entry).strip().lower()
        if item in {"*", normalized}:
            return True
    return False


def _parse_data_field(raw_data: Any) -> Dict[str, Any]:
    """
    * @Author Leon-liao
    * @Function: _parse_data_field(raw_data)
    * @Description //解析网关消息中的 data 字段（dict 或 JSON 字符串）
    * @Date :2026/06/30 18:30:00
    * @Param: raw_data: 网关 WSMessage.data
    * @return：解析后的 dict
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


def _extract_inbound_text(raw: Dict[str, Any], data: Dict[str, Any]) -> str:
    """
    * @Author Leon-liao
    * @Function: _extract_inbound_text(raw, data)
    * @Description //从网关入站消息中提取用户文本
    * @Date :2026/06/30 18:30:00
    * @Param: raw: 完整 WS 消息；data: 已解析的 data 字段
    * @return：用户消息文本
    """
    for candidate in (
        data.get("text"),
        data.get("content"),
        raw.get("text"),
        raw.get("content"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def _extract_inbound_file(data: Dict[str, Any], nested: Dict[str, Any]) -> Dict[str, str]:
    """
    * @Author Leon-liao
    * @Function: _extract_inbound_file(data, nested)
    * @Description //从入站 message 中提取已上传文件的 URL、名称和类型
    * @Date :2026/10/07 20:12:00
    * @Param: data: 业务 data；nested: data.data
    * @return：包含 url、file_name、media_type、mime_type 的字典；没有文件时为空字典
    """
    candidates: List[Dict[str, Any]] = []
    for source in (nested, data):
        if not isinstance(source, dict):
            continue
        url = str(source.get("url") or source.get("file_url") or "").strip()
        if url:
            candidates.append(source)
            break
        files = source.get("files")
        if isinstance(files, list):
            for item in files:
                if isinstance(item, dict) and str(item.get("url") or "").strip():
                    candidates.append(item)
                    break
            if candidates:
                break
    if not candidates:
        return {}

    source = candidates[0]
    url = str(source.get("url") or source.get("file_url") or "").strip()
    file_name = str(source.get("file_name") or source.get("name") or "").strip()
    hinted = str(source.get("media_type") or "").strip().lower()
    if hinted in {"image", "file"}:
        media_type = hinted
    else:
        media_type = media_kind_for_name(file_name or url)
    mime_type = str(source.get("mime_type") or "").strip() or mime_type_for_name(file_name or url)
    if media_type == "image" and not mime_type.startswith("image/"):
        mime_type = mime_type_for_name(file_name or url)
        if not mime_type.startswith("image/"):
            mime_type = "image/jpeg"
    return {
        "url": url,
        "file_name": file_name,
        "media_type": media_type,
        "mime_type": mime_type,
    }


class HarnessMateAdapter(BasePlatformAdapter):
    """Go WS 网关 Hermes 端平台适配器。"""

    PLATFORM = "harness_mate"
    MAX_MESSAGE_LENGTH = MAX_MESSAGE_LENGTH
    SUPPORTS_MESSAGE_EDITING = True

    def __init__(self, config):
        """
        * @Author Leon-liao
        * @Function: HarnessMateAdapter.__init__(config)
        * @Description //初始化 harness_mate 适配器，读取 bot_id（ws_session_id）与 bot_key（JWT 鉴权）
        * @Date :2026/07/02 12:00:00
        * @Param: config: 平台配置，需包含 bot_id、bot_key
        """
        platform = Platform("harness_mate")
        super().__init__(config=config, platform=platform)
        self.bot_id = (
            _cfg_get(config, "bot_id", "")
            or _cfg_get(config, "ws_session_id", "")
            or os.getenv("HARNESS_MATE_BOT_ID", "").strip()
            or os.getenv("HARNESS_MATE_WS_SESSION_ID", "").strip()
        ).strip()
        self.bot_key = (
            _cfg_get(config, "bot_key", "")
            or _cfg_get(config, "jwt_secret", "")
            or os.getenv("HARNESS_MATE_BOT_KEY", "").strip()
            or os.getenv("HARNESS_MATE_JWT_SECRET", "").strip()
        ).strip()
        self.ws_session_id = self.bot_id
        self.gateway_url = WS_GATEWAY_WS_URL.rstrip("/")
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._read_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._should_reconnect = False
        self._reconnect_delay = RECONNECT_MIN_DELAY
        self._send_lock = asyncio.Lock()
        self._dedup = MessageDeduplicator(max_size=DEDUP_MAX_SIZE)
        self._reply_targets: Dict[Tuple[str, str], str] = {}
        self._peer_by_device: Dict[str, str] = {}
        self._last_peer_session: str = ""
        self._reply_fingerprints: Dict[str, str] = {}
        self._typing_last_sent: Dict[Tuple[str, str], float] = {}
        self._typing_lock = asyncio.Lock()
        self.upload_url = resolve_upload_url(_cfg_get(config, "upload_url", ""))

        extra = getattr(config, "extra", None) or {}
        self._dm_policy = str(
            extra.get("dm_policy") or os.getenv("HARNESS_MATE_DM_POLICY", "open")
        ).strip().lower()
        self._allow_from = _cfg_get_list(
            config, "allow_from", "HARNESS_MATE_ALLOWED_PEERS"
        )
        if not self._allow_from:
            self._allow_from = _cfg_get_list(
                config, "allow_from", "HARNESS_MATE_ALLOWED_DEVICES"
            )

    def _is_peer_allowed(self, peer_session_id: str) -> bool:
        """
        * @Author Leon-liao
        * @Function: _is_peer_allowed(peer_session_id)
        * @Description //判断对端 ws_session_id 是否允许向 Hermes 发消息
        * @Date :2026/07/02 10:00:00
        * @Param: peer_session_id: str，对端 ws_session_id
        * @return：允许返回 True
        """
        if self._dm_policy == "disabled":
            return False
        if self._dm_policy == "open" or os.getenv(
            "HARNESS_MATE_ALLOW_ALL_DEVICES", ""
        ).lower() in {"1", "true", "yes", "on"}:
            return True
        if not self._allow_from:
            return self._dm_policy != "allowlist"
        return _entry_matches(self._allow_from, peer_session_id)

    def _build_session_token(self) -> str:
        """
        * @Author Leon-liao
        * @Function: _build_session_token()
        * @Description //生成 ws_gateway 握手 JWT（仅含 ws_session_id）
        * @Date :2026/07/02 10:00:00
        * @Param: 无
        * @return：JWT 字符串
        """
        now = int(time.time())
        return jwt.encode(
            {
                "ws_session_id": self.ws_session_id,
                "exp": now + 86400 * 30,
                "iat": now,
            },
            self.bot_key,
            algorithm="HS256",
        )

    def _build_connect_url(self) -> str:
        """
        * @Author Leon-liao
        * @Function: _build_connect_url()
        * @Description //拼接带 token 的 WebSocket 连接 URL
        * @Date :2026/07/02 10:00:00
        * @Param: 无
        * @return：完整 ws://.../ws?token=... URL
        """
        token = self._build_session_token()
        return f"{self.gateway_url}?token={token}"

    async def connect(self, is_reconnect: bool = False, **kwargs) -> bool:
        """
        * @Author Leon-liao
        * @Function: connect(is_reconnect, **kwargs)
        * @Description //连接 ws_gateway /ws 并启动读循环；重连由 Gateway 调度
        * @Date :2026/07/09 10:20:00
        * @Param: is_reconnect: bool，Gateway 重连时为 True；kwargs: 兼容未来扩展参数
        * @return：连接成功返回 True，否则 False
        """
        if not self.bot_id or not self.bot_key:
            message = "harness_mate 缺少 bot_id 或 bot_key"
            self._set_fatal_error("harness_mate_missing_config", message, retryable=False)
            logger.error(message)
            return False

        self._should_reconnect = True
        self._reconnect_delay = RECONNECT_MIN_DELAY
        if await self._establish_connection():
            logger.info(
                "harness_mate 已连接 WS 网关: bot_id=%s%s",
                self.bot_id,
                " (reconnect)" if is_reconnect else "",
            )
            return True

        if is_reconnect:
            message = "harness_mate 重连 WS 网关失败，等待 Gateway 下次重试"
        else:
            message = "harness_mate 首次连接 WS 网关失败，等待 Gateway 重连调度"
        self._set_fatal_error("harness_mate_connect_error", message, retryable=True)
        logger.warning(message)
        self._mark_disconnected()
        return False

    async def _establish_connection(self) -> bool:
        """
        * @Author Leon-liao
        * @Function: _establish_connection()
        * @Description //建立 WebSocket 连接并启动读循环
        * @Date :2026/07/01 16:00:00
        * @Param: 无
        * @return：连接成功返回 True
        """
        try:
            url = self._build_connect_url()
            self._ws = await websockets.connect(
                url,
                ping_interval=HARNESS_MATE_PING_INTERVAL,
                ping_timeout=HARNESS_MATE_PING_TIMEOUT,
                close_timeout=5,
                max_size=1024 * 1024,
            )
            self._read_task = asyncio.create_task(self._read_loop())
            self._mark_connected()
            return True
        except Exception as exc:
            logger.warning("harness_mate 连接 WS 网关失败: %s", exc)
            await self._cleanup_ws()
            return False

    async def _handle_connection_lost(self) -> None:
        """
        * @Author Leon-liao
        * @Function: _handle_connection_lost()
        * @Description //连接断开后标记状态并启动后台重连任务
        * @Date :2026/07/01 16:00:00
        * @Param: 无
        """
        self._mark_disconnected()
        if not self._should_reconnect:
            return
        if self._reconnect_task and not self._reconnect_task.done():
            return
        self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """
        * @Author Leon-liao
        * @Function: _reconnect_loop()
        * @Description //指数退避重连 WS 网关，直到成功或主动 disconnect
        * @Date :2026/07/01 16:00:00
        * @Param: 无
        """
        delay = self._reconnect_delay
        while self._should_reconnect:
            logger.warning(
                "harness_mate Gateway 断线，%.1fs 后重连 (bot_id=%s)...",
                delay,
                self.bot_id,
            )
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return
            if not self._should_reconnect:
                return
            if await self._establish_connection():
                self._reconnect_delay = RECONNECT_MIN_DELAY
                logger.info(
                    "harness_mate 已重连 WS 网关: bot_id=%s",
                    self.bot_id,
                )
                return
            delay = min(delay * 2, RECONNECT_MAX_DELAY)
            self._reconnect_delay = delay

    async def _cleanup_ws(self) -> None:
        """
        * @Author Leon-liao
        * @Function: _cleanup_ws()
        * @Description //取消读循环并关闭 WebSocket 连接
        * @Date :2026/06/30 18:30:00
        * @Param: 无
        """
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("harness_mate 读循环退出异常")
        self._read_task = None

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                logger.exception("harness_mate 关闭 WebSocket 失败")
        self._ws = None

    async def disconnect(self) -> None:
        """
        * @Author Leon-liao
        * @Function: disconnect()
        * @Description //主动断开与 WS 网关的连接，停止自动重连
        * @Date :2026/07/01 16:00:00
        * @Param: 无
        """
        self._should_reconnect = False
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        self._reconnect_task = None
        try:
            await self._cleanup_ws()
            self._dedup.clear()
            self._reply_targets.clear()
            self._peer_by_device.clear()
            self._typing_last_sent.clear()
            self._mark_disconnected()
            logger.info("harness_mate 已断开: bot_id=%s", self.bot_id)
        except Exception:
            logger.exception("harness_mate 断开失败")

    async def get_chat_info(self, chat_id: str) -> dict:
        """
        * @Author Leon-liao
        * @Function: get_chat_info(chat_id)
        * @Description //返回账号会话的基本信息
        * @Date :2026/06/30 18:30:00
        * @Param: chat_id: str，账号/会话标识
        * @return：包含 name 与 type 的字典
        """
        return {"name": chat_id, "type": "dm"}

    async def _read_loop(self) -> None:
        """
        * @Author Leon-liao
        * @Function: _read_loop()
        * @Description //持续读取网关推送的消息并分发处理
        * @Date :2026/06/30 18:30:00
        * @Param: 无
        """
        ws = self._ws
        if ws is None:
            return
        try:
            async for raw_text in ws:
                try:
                    payload = json.loads(raw_text)
                except json.JSONDecodeError:
                    logger.warning("harness_mate 收到非 JSON 消息，已忽略")
                    continue
                if not isinstance(payload, dict):
                    continue
                await self._on_gateway_message(payload)
        except asyncio.CancelledError:
            raise
        except ConnectionClosed as exc:
            logger.warning(
                "harness_mate WS 连接已关闭: code=%s reason=%s",
                exc.code,
                exc.reason,
            )
        except Exception:
            logger.exception("harness_mate 读循环异常")
        finally:
            self._ws = None
            if not self._should_reconnect:
                self._mark_disconnected()
                return
            await self._handle_connection_lost()

    async def _on_gateway_message(self, raw: Dict[str, Any]) -> None:
        """
        * @Author Leon-liao
        * @Function: _on_gateway_message(raw)
        * @Description //处理网关点对点入站消息，解析 data 中的业务负载
        * @Date :2026/07/02 10:00:00
        * @Param: raw: dict，含 from/to/data
        """
        peer_session = str(raw.get("from") or "").strip()
        if not peer_session:
            logger.debug("harness_mate 入站消息缺少 from，已忽略")
            return

        data = _parse_data_field(raw.get("data"))
        msg_type = str(data.get("type") or "").strip()
        if msg_type == TYPE_MESSAGE:
            await self._on_peer_message(peer_session, data, raw)
            return
        logger.debug("harness_mate 忽略业务消息类型: %s", msg_type)

    async def _on_peer_message(
        self,
        peer_session: str,
        data: Dict[str, Any],
        raw: Dict[str, Any],
    ) -> None:
        """
        * @Author Leon-liao
        * @Function: _on_peer_message(peer_session, data, raw)
        * @Description //处理对端经网关转发的 message，转换为 MessageEvent
        * @Date :2026/07/02 10:00:00
        * @Param: peer_session: 对端 ws_session_id；data: 业务 data；raw: 完整网关消息
        """
        try:
            nested = _parse_data_field(data.get("data"))
            text = _extract_inbound_text(data, nested)
            inbound_file = _extract_inbound_file(data, nested)
            if inbound_file and inbound_file["url"] not in text:
                text = f"{text}\n{inbound_file['url']}".strip() if text else inbound_file["url"]
            if not text:
                logger.debug("harness_mate 入站消息无文本内容，已忽略")
                return

            msg_id = str(
                data.get("msg_id")
                or nested.get("msg_id")
                or nested.get("message_id")
                or raw.get("msg_id")
                or ""
            ).strip()
            if msg_id and self._dedup.is_duplicate(msg_id):
                logger.debug("harness_mate 重复消息已忽略: %s", msg_id)
                return

            if not self._is_peer_allowed(peer_session):
                logger.debug("harness_mate 对端未授权: %s", peer_session)
                return

            account_id = str(data.get("account_id") or self.bot_id).strip()
            thread_id = str(data.get("thread_id") or "").strip()
            device_id = str(
                data.get("from_device") or data.get("device_id") or peer_session
            ).strip()
            self._reply_targets[(account_id, thread_id)] = peer_session
            self._peer_by_device[device_id] = peer_session
            self._last_peer_session = peer_session

            message_type = MessageType.TEXT
            media_urls: List[str] = []
            media_types: List[str] = []
            if inbound_file:
                media_urls = [inbound_file["url"]]
                media_types = [inbound_file["mime_type"]]
                message_type = (
                    MessageType.PHOTO
                    if inbound_file["media_type"] == "image"
                    else MessageType.DOCUMENT
                )

            event = MessageEvent(
                source=self.build_source(
                    chat_id=account_id,
                    chat_type="dm",
                    user_id=device_id,
                    user_name=device_id,
                    thread_id=thread_id or None,
                ),
                text=text,
                message_type=message_type,
                media_urls=media_urls,
                media_types=media_types,
                raw_message=raw,
                message_id=msg_id or None,
            )
            await self.handle_message(event)
        except Exception:
            logger.exception("harness_mate 处理对端消息失败")

    def _resolve_target(
        self,
        chat_id: str,
        metadata: Optional[Dict[str, Any]],
    ) -> Tuple[str, str]:
        """
        * @Author Leon-liao
        * @Function: _resolve_target(chat_id, metadata)
        * @Description //解析 thread_id 与目标 ws_session_id（路由层与业务 from_device 分离）
        * @Date :2026/07/02 11:30:00
        * @Param: chat_id: 账号 ID；metadata: 发送元数据
        * @return：(thread_id, to_ws_session) 元组
        """
        metadata = metadata or {}
        thread_id = str(metadata.get("thread_id") or "")

        to_ws_session = str(self._reply_targets.get((chat_id, thread_id), "")).strip()
        if not to_ws_session:
            for (acct, _tid), peer in self._reply_targets.items():
                if acct == chat_id and peer:
                    to_ws_session = str(peer).strip()
                    break
        if not to_ws_session:
            to_ws_session = str(self._last_peer_session or "").strip()
        if not to_ws_session:
            device_hint = str(
                metadata.get("to_device") or metadata.get("user_id") or ""
            ).strip()
            if device_hint:
                to_ws_session = str(self._peer_by_device.get(device_hint, "")).strip()
        if not to_ws_session:
            to_ws_session = str(
                metadata.get("to_ws_session") or metadata.get("to") or ""
            ).strip()
        return thread_id, to_ws_session

    def _typing_key(self, to_ws_session: str, thread_id: str) -> Tuple[str, str]:
        """
        * @Author Leon-liao
        * @Function: _typing_key(to_ws_session, thread_id)
        * @Description //构造思考状态节流键
        * @Date :2026/07/02 10:00:00
        * @Param: to_ws_session: 目标 ws_session_id；thread_id: 会话线程
        * @return：(to_ws_session, thread_id) 元组
        """
        return to_ws_session, thread_id

    def _reset_typing_throttle(self, to_ws_session: str, thread_id: str) -> None:
        """
        * @Author Leon-liao
        * @Function: _reset_typing_throttle(to_ws_session, thread_id)
        * @Description //正文回复后重置思考节流，便于下一轮立即显示思考中
        * @Date :2026/07/02 10:00:00
        * @Param: to_ws_session: 目标 ws_session_id；thread_id: 会话线程
        """
        self._typing_last_sent.pop(self._typing_key(to_ws_session, thread_id), None)

    def _build_reply_data(
        self,
        content: str,
        message_id: str,
        metadata: Optional[Dict[str, Any]],
        *,
        finalize: bool = False,
    ) -> Dict[str, Any]:
        """
        * @Author Leon-liao
        * @Function: _build_reply_data(content, message_id, metadata, finalize)
        * @Description //构造发往 App 的 reply.data，支持流式 delta 与思考过程
        * @Date :2026/07/01 18:00:00
        * @Param: content: 回复正文；message_id: 消息 ID；metadata: 发送元数据；finalize: 是否为流式最终帧
        * @return：reply.data 字典
        """
        metadata = metadata or {}
        reply_data: Dict[str, Any] = {
            "text": content[: self.MAX_MESSAGE_LENGTH],
            "message_id": message_id,
        }
        is_streaming = bool(
            metadata.get("delta")
            or metadata.get("expect_edits")
            or metadata.get("stream")
        )
        is_final = bool(
            finalize
            or metadata.get("done")
            or metadata.get("final")
            or metadata.get("notify")
        )
        if is_streaming and not is_final:
            reply_data["delta"] = True
        elif metadata.get("stream_finalize"):
            reply_data["delta"] = True
        if is_final:
            reply_data["done"] = True
        reasoning = metadata.get("reasoning")
        if reasoning:
            reply_data["reasoning"] = reasoning
        return reply_data

    async def _send_reply(
        self,
        chat_id: str,
        to_ws_session: str,
        thread_id: str,
        content: str,
        message_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        *,
        finalize: bool = False,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: _send_reply(...)
        * @Description //向目标 ws_session_id 发送 type=reply 业务消息（支持流式）
        * @Date :2026/07/02 10:00:00
        * @Param: chat_id: 账号 ID；to_ws_session: 目标 ws_session_id；thread_id: 会话线程；content: 正文；message_id: 消息 ID；metadata: 元数据；finalize: 是否最终帧
        * @return：SendResult 发送结果
        """
        if not to_ws_session:
            logger.warning(
                "harness_mate 无法解析 to_ws_session: chat=%s thread=%s metadata=%s",
                chat_id,
                thread_id,
                metadata,
            )
            return SendResult(success=False, error="to_ws_session not resolved")
        if self._ws is None:
            return SendResult(success=False, error="WebSocket not connected")

        reply_data = self._build_reply_data(
            content,
            message_id,
            metadata,
            finalize=finalize,
        )
        fingerprint = json.dumps(reply_data, ensure_ascii=False, sort_keys=True)
        cache_key = f"{to_ws_session}:{thread_id}:{message_id}"
        if self._reply_fingerprints.get(cache_key) == fingerprint:
            logger.debug(
                "harness_mate 跳过重复 reply 帧: peer=%s msg=%s",
                to_ws_session,
                message_id,
            )
            return SendResult(success=True, message_id=message_id)
        self._reply_fingerprints[cache_key] = fingerprint
        if reply_data.get("done"):
            self._reply_fingerprints.pop(cache_key, None)

        business_payload = {
            "type": TYPE_REPLY,
            "account_id": chat_id,
            "thread_id": thread_id,
            "data": reply_data,
        }
        ok = await self._send_ws(to_ws_session, business_payload)
        if not ok:
            return SendResult(success=False, error="ws send failed")
        self._reset_typing_throttle(to_ws_session, thread_id)
        logger.debug(
            "harness_mate 已发送 reply: peer=%s thread=%s msg=%s delta=%s done=%s len=%d",
            to_ws_session,
            thread_id,
            message_id,
            reply_data.get("delta"),
            reply_data.get("done"),
            len(str(reply_data.get("text") or "")),
        )
        return SendResult(success=True, message_id=message_id)

    async def _send_ws(self, to: str, data: Dict[str, Any]) -> bool:
        """
        * @Author Leon-liao
        * @Function: _send_ws(to, data)
        * @Description //向 ws_gateway 发送点对点 WSMessage
        * @Date :2026/07/02 10:00:00
        * @Param: to: 目标 ws_session_id；data: 业务负载
        * @return：发送成功返回 True
        """
        if self._ws is None:
            return False
        payload = {"to": to, "data": data}
        try:
            async with self._send_lock:
                await self._ws.send(json.dumps(payload, ensure_ascii=False))
            return True
        except Exception:
            logger.exception("harness_mate WS 发送失败")
            return False

    def _file_name_from_url(self, url: str) -> str:
        """
        * @Author Leon-liao
        * @Function: _file_name_from_url(url)
        * @Description //从 URL 路径中取出文件名
        * @Date :2026/10/07 20:12:00
        * @Param: url: 文件地址
        * @return：文件名；无法解析时返回空字符串
        """
        path = str(url or "").split("?", 1)[0].rstrip("/")
        name = path.rsplit("/", 1)[-1]
        if not name or "." not in name:
            return ""
        return name

    async def _send_file_message(
        self,
        chat_id: str,
        to_ws_session: str,
        thread_id: str,
        url: str,
        file_name: str,
        media_type: str,
        caption: str,
        message_id: str,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: _send_file_message(...)
        * @Description //把文件 URL 作为 reply 发给当前会话，供对端直接打开
        * @Date :2026/10/07 20:12:00
        * @Param: chat_id: 账号 ID；to_ws_session: 目标会话；thread_id: 线程；url: 文件地址；file_name: 文件名；media_type: image 或 file；caption: 说明文字；message_id: 消息 ID
        * @return：SendResult 发送结果
        """
        if not to_ws_session:
            return SendResult(success=False, error="to_ws_session not resolved")
        if self._ws is None:
            return SendResult(success=False, error="WebSocket not connected", retryable=True)

        reply_data = {
            "text": (caption or "")[: self.MAX_MESSAGE_LENGTH],
            "message_id": message_id,
            "done": True,
            "url": url,
            "file_name": file_name,
            "media_type": media_type,
        }
        fingerprint = json.dumps(reply_data, ensure_ascii=False, sort_keys=True)
        cache_key = f"{to_ws_session}:{thread_id}:{message_id}:file"
        if self._reply_fingerprints.get(cache_key) == fingerprint:
            return SendResult(success=True, message_id=message_id)
        self._reply_fingerprints[cache_key] = fingerprint

        ok = await self._send_ws(
            to_ws_session,
            {
                "type": TYPE_REPLY,
                "account_id": chat_id,
                "thread_id": thread_id,
                "data": reply_data,
            },
        )
        if not ok:
            return SendResult(success=False, error="ws send failed", retryable=True)
        self._reset_typing_throttle(to_ws_session, thread_id)
        logger.info(
            "harness_mate 已发送文件: peer=%s kind=%s name=%s",
            to_ws_session,
            media_type,
            file_name or url,
        )
        return SendResult(success=True, message_id=message_id, raw_response={"url": url})

    async def _deliver_local_file(
        self,
        chat_id: str,
        file_path: str,
        caption: Optional[str],
        metadata: Optional[Dict[str, Any]],
        media_type: str,
        file_name: Optional[str] = None,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: _deliver_local_file(...)
        * @Description //先调用免授权上传接口，再把返回的 URL 发给当前会话
        * @Date :2026/10/07 20:12:00
        * @Param: chat_id: 账号 ID；file_path: 本地文件；caption: 说明；metadata: 路由元数据；media_type: image 或 file；file_name: 展示文件名
        * @return：SendResult 发送结果
        """
        metadata = metadata or {}
        thread_id, to_ws_session = self._resolve_target(chat_id, metadata)
        session_id = str(metadata.get("session_id") or to_ws_session or "").strip()
        if not to_ws_session:
            return SendResult(success=False, error="to_ws_session not resolved")
        if self._ws is None:
            return SendResult(success=False, error="WebSocket not connected", retryable=True)
        display_name = str(file_name or "").strip() or os.path.basename(str(file_path or ""))
        kind = media_type if media_type in {"image", "file"} else media_kind_for_name(display_name)
        message_id = str(metadata.get("message_id") or uuid.uuid4())
        try:
            url = await asyncio.to_thread(
                upload_open_api_file,
                file_path,
                self.bot_id,
                self.bot_key,
                session_id,
                self.upload_url,
            )
        except OpenApiUploadError as exc:
            logger.warning("harness_mate 文件上传失败: %s", exc.message)
            return SendResult(success=False, error=exc.message, retryable=exc.retryable)
        except Exception as exc:
            logger.exception("harness_mate 文件上传异常")
            return SendResult(success=False, error=str(exc), retryable=True)
        return await self._send_file_message(
            chat_id,
            to_ws_session,
            thread_id,
            url,
            display_name,
            kind,
            caption or "",
            message_id,
        )

    async def send_image(
        self,
        chat_id: str,
        image_url: str,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: send_image(chat_id, image_url, caption, reply_to, metadata)
        * @Description //发送图片。本地 file:// 先上传，远程地址直接随 reply 下发
        * @Date :2026/10/07 20:12:00
        * @Param: chat_id: 账号 ID；image_url: 图片地址；caption: 说明；reply_to: 兼容参数；metadata: 路由元数据
        * @return：SendResult 发送结果
        """
        del reply_to
        image_url = str(image_url or "").strip()
        if image_url.startswith("file://"):
            return await self.send_image_file(
                chat_id,
                url2pathname(image_url[7:]),
                caption=caption,
                metadata=metadata,
            )
        if not image_url.startswith(("http://", "https://")):
            return SendResult(success=False, error="图片地址无效")
        metadata = metadata or {}
        thread_id, to_ws_session = self._resolve_target(chat_id, metadata)
        file_name = self._file_name_from_url(image_url)
        message_id = str(metadata.get("message_id") or uuid.uuid4())
        return await self._send_file_message(
            chat_id,
            to_ws_session,
            thread_id,
            image_url,
            file_name,
            "image",
            caption or "",
            message_id,
        )

    async def send_image_file(
        self,
        chat_id: str,
        image_path: str,
        caption: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: send_image_file(chat_id, image_path, caption, reply_to, metadata, **kwargs)
        * @Description //上传本地图片并发送给当前会话
        * @Date :2026/10/07 20:12:00
        * @Param: chat_id: 账号 ID；image_path: 本地图片路径；caption: 说明；metadata: 路由元数据
        * @return：SendResult 发送结果
        """
        del reply_to, kwargs
        if extension_of(image_path) and media_kind_for_name(image_path) != "image":
            return SendResult(success=False, error=f"该.{extension_of(image_path)}扩展的文件不允许作为图片上传")
        return await self._deliver_local_file(
            chat_id,
            image_path,
            caption,
            metadata,
            "image",
        )

    async def send_document(
        self,
        chat_id: str,
        file_path: str,
        caption: Optional[str] = None,
        file_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: send_document(chat_id, file_path, caption, file_name, reply_to, metadata, **kwargs)
        * @Description //上传本地文档或图片并发送给当前会话
        * @Date :2026/10/07 20:12:00
        * @Param: chat_id: 账号 ID；file_path: 本地文件路径；caption: 说明；file_name: 展示名；metadata: 路由元数据
        * @return：SendResult 发送结果
        """
        del reply_to
        if not file_name:
            file_name = str(kwargs.get("filename") or kwargs.get("file_name") or "").strip() or None
        kind = "file"
        shown = file_name or file_path
        if media_kind_for_name(shown) == "image":
            kind = "image"
        return await self._deliver_local_file(
            chat_id,
            file_path,
            caption,
            metadata,
            kind,
            file_name=file_name,
        )

    async def send_typing(self, chat_id: str, metadata=None) -> None:
        """
        * @Author Leon-liao
        * @Function: send_typing(chat_id, metadata)
        * @Description //向设备推送「思考中」状态（节流，避免每 2s 刷屏）
        * @Date :2026/07/01 21:10:00
        * @Param: chat_id: 账号 ID；metadata: 含 thread_id / to_device
        """
        metadata = metadata or {}
        thread_id, to_ws_session = self._resolve_target(chat_id, metadata)
        if not to_ws_session:
            return

        typing_key = self._typing_key(to_ws_session, thread_id)
        async with self._typing_lock:
            now = time.monotonic()
            last_sent = self._typing_last_sent.get(typing_key, 0.0)
            if now - last_sent < TYPING_THROTTLE_SECONDS:
                logger.debug(
                    "harness_mate 跳过重复思考状态: peer=%s thread=%s",
                    to_ws_session,
                    thread_id,
                )
                return
            self._typing_last_sent[typing_key] = now

        await self._send_ws(
            to_ws_session,
            {
                "type": TYPE_REPLY,
                "account_id": chat_id,
                "thread_id": thread_id,
                "data": {
                    "status": "thinking",
                    "text": "思考中...",
                },
            },
        )

    async def send(
        self,
        chat_id: str,
        content: str,
        reply_to: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: send(chat_id, content, reply_to, metadata)
        * @Description //经 WS 网关向目标设备发送 type=reply 消息（支持流式首帧）
        * @Date :2026/07/01 18:00:00
        * @Param: chat_id: 账号 ID；content: 消息文本；metadata: 含 thread_id / to_device / delta / expect_edits
        * @return：SendResult 发送结果
        """
        del reply_to
        metadata = metadata or {}
        thread_id, to_ws_session = self._resolve_target(chat_id, metadata)
        msg_id = str(metadata.get("message_id") or uuid.uuid4())
        try:
            return await self._send_reply(
                chat_id,
                to_ws_session,
                thread_id,
                content,
                msg_id,
                metadata,
                finalize=bool(metadata.get("notify")),
            )
        except Exception as exc:
            logger.exception("harness_mate 发送消息失败")
            return SendResult(success=False, error=str(exc), retryable=True)

    async def edit_message(
        self,
        chat_id: str,
        message_id: str,
        content: str,
        *,
        finalize: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """
        * @Author Leon-liao
        * @Function: edit_message(chat_id, message_id, content, finalize, metadata)
        * @Description //流式更新已发送消息，供 GatewayStreamConsumer 增量推送
        * @Date :2026/07/01 18:00:00
        * @Param: chat_id: 账号 ID；message_id: 首帧消息 ID；content: 当前累计正文；finalize: 是否最终帧；metadata: 路由元数据
        * @return：SendResult 发送结果
        """
        metadata = metadata or {}
        metadata = {**metadata, "stream": True}
        if finalize:
            metadata = {**metadata, "stream_finalize": True}
        thread_id, to_ws_session = self._resolve_target(chat_id, metadata)
        try:
            return await self._send_reply(
                chat_id,
                to_ws_session,
                thread_id,
                content,
                message_id,
                metadata,
                finalize=finalize,
            )
        except Exception as exc:
            logger.exception("harness_mate 流式编辑失败")
            return SendResult(success=False, error=str(exc), retryable=True)


def _check_deps() -> bool:
    """
    * @Author Leon-liao
    * @Function: _check_deps()
    * @Description //检查 harness_mate 所需 Python 依赖是否已安装
    * @Date :2026/06/30 18:30:00
    * @Param: 无
    * @return：依赖齐全返回 True，否则 False
    """
    try:
        import jwt  # noqa: F401
        import websockets  # noqa: F401
        return True
    except ImportError:
        return False


def _validate_config(config) -> bool:
    """
    * @Author Leon-liao
    * @Function: _validate_config(config)
    * @Description //校验 harness_mate 最小配置是否完整
    * @Date :2026/06/30 18:30:00
    * @Param: config: PlatformConfig
    * @return：配置完整返回 True
    """
    extra = getattr(config, "extra", {}) or {}
    bot_id = str(
        extra.get("bot_id")
        or extra.get("ws_session_id")
        or ""
    ).strip()
    bot_key = str(
        extra.get("bot_key")
        or extra.get("jwt_secret")
        or ""
    ).strip()
    if bot_id and bot_key:
        return True
    return _env_enablement() is not None


def _is_connected(config=None) -> bool:
    """
    * @Author Leon-liao
    * @Function: _is_connected(config)
    * @Description //判断 harness_mate 是否已配置或已建立连接
    * @Date :2026/06/30 18:30:00
    * @Param: config: PlatformConfig 或适配器实例
    * @return：已连接或已配置返回 True，否则 False
    """
    if config is None:
        return False
    if isinstance(config, PlatformConfig):
        return _validate_config(config)
    ws = getattr(config, "_ws", None)
    return ws is not None and not getattr(ws, "closed", True)


def _env_enablement() -> Optional[dict]:
    """
    * @Author Leon-liao
    * @Function: _env_enablement()
    * @Description //从环境变量种子化 PlatformConfig.extra
    * @Date :2026/06/30 18:30:00
    * @Param: 无
    * @return：配置 dict 或 None
    """
    bot_id = os.getenv("HARNESS_MATE_BOT_ID", "").strip()
    bot_key = os.getenv("HARNESS_MATE_BOT_KEY", "").strip()
    if not bot_id:
        bot_id = os.getenv("HARNESS_MATE_WS_SESSION_ID", "").strip()
    if not bot_key:
        bot_key = os.getenv("HARNESS_MATE_JWT_SECRET", "").strip()
    if not bot_id or not bot_key:
        return None

    seed: Dict[str, Any] = {
        "bot_id": bot_id,
        "bot_key": bot_key,
    }
    allowed = os.getenv("HARNESS_MATE_ALLOWED_DEVICES", "").strip()
    if allowed:
        seed["allow_from"] = allowed
    dm_policy = os.getenv("HARNESS_MATE_DM_POLICY", "").strip()
    if dm_policy:
        seed["dm_policy"] = dm_policy
    return seed


async def _standalone_send(pconfig, chat_id, message, *, thread_id=None, **kwargs):
    """
    * @Author Leon-liao
    * @Function: _standalone_send(...)
    * @Description //无 Gateway 进程时独立发送消息（Cron 等场景）
    * @Date :2026/06/30 18:30:00
    * @Param: pconfig: PlatformConfig；chat_id: 账号 ID；message: 文本
    * @return：发送结果 dict
    """
    del kwargs
    if not _check_deps():
        return {"error": "harness_mate 依赖未安装"}
    try:
        adapter = HarnessMateAdapter(pconfig)
        connected = await adapter.connect()
        if not connected:
            err = getattr(adapter, "fatal_error_message", None) or "connect failed"
            return {"error": f"harness_mate: {err}"}
        try:
            metadata = {"thread_id": thread_id} if thread_id else None
            result = await adapter.send(chat_id, message, metadata=metadata)
            if not result.success:
                return {"error": f"harness_mate send failed: {result.error}"}
            return {
                "success": True,
                "platform": "harness_mate",
                "chat_id": chat_id,
                "message_id": result.message_id,
            }
        finally:
            await adapter.disconnect()
    except Exception as exc:
        return {"error": f"harness_mate send failed: {exc}"}


def _build_adapter(config) -> HarnessMateAdapter:
    """
    * @Author Leon-liao
    * @Function: _build_adapter(config)
    * @Description //工厂函数，创建 HarnessMateAdapter 实例
    * @Date :2026/06/30 18:30:00
    * @Param: config: 平台配置对象
    * @return：HarnessMateAdapter 实例
    """
    return HarnessMateAdapter(config)


def _patch_harness_mate_thread_metadata() -> None:
    """
    * @Author Leon-liao
    * @Function: _patch_harness_mate_thread_metadata()
    * @Description //为 harness_mate 注入业务层 to_device/user_id，路由 ws_session_id 由适配器 _reply_targets 解析
    * @Date :2026/07/02 11:30:00
    * @Param: 无
    * @return：无
    """
    if globals().get("_HARNESS_MATE_THREAD_METADATA_PATCHED"):
        return

    def _enrich(metadata: Optional[Dict[str, Any]], source: Any) -> Optional[Dict[str, Any]]:
        if metadata is None:
            return None
        platform = getattr(source, "platform", None)
        platform_name = str(getattr(platform, "value", platform) or "")
        if platform_name != "harness_mate":
            return metadata
        user_id = getattr(source, "user_id", None)
        if not user_id:
            return metadata
        enriched = dict(metadata)
        enriched.setdefault("to_device", str(user_id))
        enriched.setdefault("user_id", str(user_id))
        return enriched

    try:
        import gateway.platforms.base as base_module

        _orig_base = base_module._thread_metadata_for_source

        def _base_patched(source, reply_to_message_id=None):
            return _enrich(_orig_base(source, reply_to_message_id), source)

        base_module._thread_metadata_for_source = _base_patched
    except Exception:
        logger.debug("harness_mate 跳过 base 线程元数据补丁", exc_info=True)

    try:
        # 修复（v0.5.3 在新版 Hermes 上的加载超时问题）：原实现直接
        # `from gateway.run import GatewayRunner`，在部分 Hermes 进程
        # （gateway 启动/重载窗口）中会触发 bootstrap relaunch 并长时间
        # 阻塞插件加载线程（表现为 "load timed out ... import + register()
        # never returned"，平台注册被丢弃）。改为仅在 gateway.run 已被
        # 宿主进程加载时打补丁 —— gateway 进程本身必然已加载 gateway.run，
        # 补丁照常生效；其他场景跳过，不再阻塞注册。
        import sys as _sys

        _gw_run_module = _sys.modules.get("gateway.run")
        _GatewayRunner = (
            getattr(_gw_run_module, "GatewayRunner", None) if _gw_run_module else None
        )
        if _GatewayRunner is None:
            logger.debug(
                "harness_mate 跳过 GatewayRunner 线程元数据补丁 (gateway.run 未加载)"
            )
        else:
            _orig_runner = _GatewayRunner._thread_metadata_for_source

            def _runner_patched(self, source, reply_to_message_id=None):
                return _enrich(
                    _orig_runner(self, source, reply_to_message_id),
                    source,
                )

            _GatewayRunner._thread_metadata_for_source = _runner_patched
    except Exception:
        logger.debug("harness_mate 跳过 GatewayRunner 线程元数据补丁", exc_info=True)

    globals()["_HARNESS_MATE_THREAD_METADATA_PATCHED"] = True


def register(ctx) -> None:
    """
    * @Author Leon-liao
    * @Function: register(ctx)
    * @Description //Hermes 插件入口，注册 harness_mate 平台
    * @Date :2026/06/30 18:30:00
    * @Param: ctx: Hermes 插件注册上下文
    """
    _patch_harness_mate_thread_metadata()
    ctx.register_platform(
        name="harness_mate",
        label="HarnessMate",
        adapter_factory=_build_adapter,
        check_fn=_check_deps,
        validate_config=_validate_config,
        is_connected=_is_connected,
        required_env=["HARNESS_MATE_BOT_ID", "HARNESS_MATE_BOT_KEY"],
        env_enablement_fn=_env_enablement,
        allowed_users_env="HARNESS_MATE_ALLOWED_DEVICES",
        allow_all_env="HARNESS_MATE_ALLOW_ALL_DEVICES",
        cron_deliver_env_var="HARNESS_MATE_BOT_ID",
        standalone_sender_fn=_standalone_send,
        max_message_length=MAX_MESSAGE_LENGTH,
        install_hint="pip install websockets PyJWT",
        emoji="🔗",
        allow_update_command=True,
    )
