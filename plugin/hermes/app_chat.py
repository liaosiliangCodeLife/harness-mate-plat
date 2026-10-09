'''
*
* This is the projet for brtc R&D Platform
* @Author Leon-liao <liaosiliang@alltman.com>
* @Description App 端 WS Gateway 测试客户端（v0.5 点对点架构）
* @File: app_chat.py
* @Time: 2026/07/02 09:30:00
* @All Rights Reserve By Brtc
'''

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any

try:
    import websockets
except ImportError:
    print("请先安装依赖: pip install websockets PyJWT")
    sys.exit(1)

from common import (
    DEFAULT_ACCOUNT_ID,
    DEFAULT_APP_WS_SESSION_ID,
    DEFAULT_DEVICE_ID,
    DEFAULT_HERMES_WS_SESSION_ID,
    DEFAULT_THREAD_ID,
    WS_CLIENT_PING_INTERVAL,
    WS_CLIENT_PING_TIMEOUT,
    build_p2p_envelope,
    build_session_token,
    extract_reply_fields,
    now_text,
    pretty_json,
    strip_stream_cursor,
)

TOOL_STATUS_MARKERS = ("🔍", "📄", "⏳", "🛠", "🔧")
PROMPT = "App> "
DEFAULT_GATEWAY_HOST = "ws-agent.alltman.com"
DEFAULT_GATEWAY_PORT = "1443"
DEFAULT_GATEWAY_SCHEME = "wss"
DEFAULT_JWT_SECRET = os.environ.get("WS_GATEWAY_JWT_SECRET", "")
DEFAULT_GATEWAY_WS_PATH = "/ws"


def build_app_message_payload(
    account_id: str,
    thread_id: str,
    from_device: str,
    text: str,
) -> dict[str, Any]:
    """
    * @Author Leon-liao
    * @Function: build_app_message_payload(account_id, thread_id, from_device, text)
    * @Description //构造 App→Hermes 业务 message 负载（协议 7.3）
    * @Date :2026/07/02 09:30:00
    * @Param: account_id: Hermes 账号 ID；thread_id: 会话线程；from_device: 逻辑设备 ID；text: 用户输入
    * @return：业务层 data 字典
    """
    return {
        "type": "message",
        "account_id": account_id,
        "thread_id": thread_id,
        "from_device": from_device,
        "data": {
            "type": "message",
            "text": text,
        },
    }


def parse_gateway_envelope(raw: str) -> dict[str, Any] | None:
    """
    * @Author Leon-liao
    * @Function: parse_gateway_envelope(raw)
    * @Description //解析网关转发信封 {from, to, data}
    * @Date :2026/07/02 09:30:00
    * @Param: raw: WebSocket 文本帧
    * @return：解析成功返回字典，失败返回 None
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def extract_business_payload(envelope: dict[str, Any]) -> dict[str, Any]:
    """
    * @Author Leon-liao
    * @Function: extract_business_payload(envelope)
    * @Description //从网关信封中提取业务 data 层
    * @Date :2026/07/02 09:30:00
    * @Param: envelope: 网关消息 {from, to, data}
    * @return：业务 data 字典
    """
    data = envelope.get("data")
    if isinstance(data, dict):
        return data
    return {}


class StreamRenderer:
    """Hermes 流式 reply 终端渲染器。"""

    def __init__(self) -> None:
        """
        * @Author Leon-liao
        * @Function: StreamRenderer.__init__()
        * @Description //初始化流式输出状态
        * @Date :2026/07/02 09:30:00
        * @Param: 无
        * @return：无
        """
        self._thinking_active = False
        self._text_streams: dict[str, str] = {}
        self._active_stream_id = ""

    def reset(self) -> None:
        """
        * @Author Leon-liao
        * @Function: reset()
        * @Description //重置流式输出状态
        * @Date :2026/07/02 09:30:00
        * @Param: 无
        * @return：无
        """
        self._finish_active_stream_line()
        self._thinking_active = False
        self._text_streams.clear()

    def _finish_active_stream_line(self) -> None:
        """
        * @Author Leon-liao
        * @Function: _finish_active_stream_line()
        * @Description //结束当前流式行
        * @Date :2026/07/02 09:30:00
        * @Param: 无
        * @return：无
        """
        if not self._active_stream_id:
            return
        print()
        self._text_streams.pop(self._active_stream_id, None)
        self._active_stream_id = ""

    def _is_tool_status_text(self, text: str) -> bool:
        """
        * @Author Leon-liao
        * @Function: _is_tool_status_text(text)
        * @Description //判断是否为工具执行进度文本
        * @Date :2026/07/02 09:30:00
        * @Param: text: 消息正文
        * @return：是工具进度返回 True
        """
        stripped = text.strip()
        if not stripped:
            return False
        first_line = stripped.splitlines()[0].strip()
        return first_line.startswith(TOOL_STATUS_MARKERS)

    def _append_stream_chunk(self, message_id: str, text: str, *, header: str) -> bool:
        """
        * @Author Leon-liao
        * @Function: _append_stream_chunk(message_id, text, header)
        * @Description //按累计正文增量输出
        * @Date :2026/07/02 09:30:00
        * @Param: message_id: 消息 ID；text: 累计正文；header: 首次输出标题
        * @return：有新增内容返回 True
        """
        visible = strip_stream_cursor(text)
        previous = self._text_streams.get(message_id, "")
        if visible == previous:
            return False

        if not previous:
            if self._active_stream_id and self._active_stream_id != message_id:
                print()
                self._text_streams.pop(self._active_stream_id, None)
            print(f"\n[{now_text()}] {header}", end="", flush=True)
            self._active_stream_id = message_id

        if visible.startswith(previous):
            print(visible[len(previous):], end="", flush=True)
        elif not previous.startswith(visible):
            common = 0
            limit = min(len(previous), len(visible))
            while common < limit and previous[common] == visible[common]:
                common += 1
            if common > 0:
                print(visible[common:], end="", flush=True)
            else:
                print(visible, end="", flush=True)

        self._text_streams[message_id] = visible
        return True

    def render_reply(self, reply_data: Any, *, verbose: bool = False) -> bool:
        """
        * @Author Leon-liao
        * @Function: render_reply(reply_data, verbose)
        * @Description //渲染 Hermes reply.data，支持流式/思考/工具进度
        * @Date :2026/07/02 09:30:00
        * @Param: reply_data: reply 内层 data；verbose: 是否打印原始 JSON
        * @return：是否需要重新显示输入提示符
        """
        if verbose:
            print(f"\n[{now_text()}] Hermes 原始 reply.data:")
            print(pretty_json(reply_data))
            return True

        fields = extract_reply_fields(reply_data)
        status = str(fields["status"])
        text = str(fields["text"])
        reasoning = str(fields["reasoning"])
        is_delta = bool(fields["delta"])
        is_done = bool(fields["done"])
        message_id = str(fields["message_id"]) or "default"

        is_typing = status == "thinking" or text == "思考中..."
        if is_typing and not reasoning:
            if not self._thinking_active:
                self._finish_active_stream_line()
                print(f"[{now_text()}] Hermes 思考中...")
                self._thinking_active = True
            return False

        self._thinking_active = False
        stream_updated = False
        need_prompt = True

        if reasoning:
            if is_delta:
                updated = self._append_stream_chunk(
                    f"reasoning:{message_id}",
                    reasoning,
                    header="Hermes 思考过程: ",
                )
                if updated:
                    stream_updated = True
                    need_prompt = False
            else:
                self._finish_active_stream_line()
                print(f"\n[{now_text()}] Hermes 思考过程:\n{reasoning}")

        if text and text != "思考中...":
            if is_delta or (is_done and message_id in self._text_streams):
                updated = self._append_stream_chunk(
                    message_id,
                    text,
                    header="Hermes 回复: ",
                )
                stream_updated = stream_updated or updated
                if updated:
                    need_prompt = False
                if is_done:
                    self._finish_active_stream_line()
            elif self._is_tool_status_text(text):
                self._finish_active_stream_line()
                for line in text.strip().splitlines():
                    line = line.strip()
                    if line:
                        print(f"[{now_text()}] Hermes 进度: {line}")
            else:
                self._finish_active_stream_line()
                print(f"\n[{now_text()}] Hermes 回复: {text}")
                self._text_streams.pop(message_id, None)

        if is_done and self._active_stream_id == message_id:
            self._finish_active_stream_line()

        if need_prompt and (not stream_updated or is_done):
            return True
        return False


class AppChatClient:
    """App 端 WS Gateway 测试客户端。"""

    def __init__(
        self,
        gateway_host: str,
        gateway_port: str,
        jwt_secret: str,
        ws_session_id: str,
        hermes_ws_session_id: str,
        account_id: str,
        from_device: str,
        thread_id: str,
        gateway_scheme: str = DEFAULT_GATEWAY_SCHEME,
        gateway_ws_path: str = DEFAULT_GATEWAY_WS_PATH,
        verbose: bool = False,
    ) -> None:
        """
        * @Author Leon-liao
        * @Function: AppChatClient.__init__(...)
        * @Description //初始化 App 测试客户端
        * @Date :2026/07/02 09:30:00
        * @Param: gateway_host/port/scheme: 网关地址；jwt_secret: JWT 密钥；ws_session_id: 本端会话 ID；hermes_ws_session_id: Hermes 对端 ID；account_id/from_device/thread_id: 业务身份；verbose: 原始 JSON 模式
        * @return：无
        """
        self.gateway_host = gateway_host
        self.gateway_port = gateway_port
        self.gateway_scheme = gateway_scheme
        self.gateway_ws_path = gateway_ws_path
        self.jwt_secret = jwt_secret
        self.ws_session_id = ws_session_id
        self.hermes_ws_session_id = hermes_ws_session_id
        self.account_id = account_id
        self.from_device = from_device
        self.thread_id = thread_id
        self.verbose = verbose

        self._renderer = StreamRenderer()
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._connected = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._send_lock = asyncio.Lock()

    def _build_ws_url(self) -> str:
        """
        * @Author Leon-liao
        * @Function: _build_ws_url()
        * @Description //构造 /ws?token= 连接地址
        * @Date :2026/07/02 09:30:00
        * @Param: 无
        * @return：WebSocket URL
        """
        token = build_session_token(
            jwt_secret=self.jwt_secret,
            ws_session_id=self.ws_session_id,
        )
        return (
            f"{self.gateway_scheme}://{self.gateway_host}:{self.gateway_port}"
            f"{self.gateway_ws_path}?token={token}"
        )

    async def _handle_gateway_message(self, raw: str) -> None:
        """
        * @Author Leon-liao
        * @Function: _handle_gateway_message(raw)
        * @Description //处理网关转发消息 {from, to, data}
        * @Date :2026/07/02 09:30:00
        * @Param: raw: WebSocket 文本帧
        * @return：无
        """
        envelope = parse_gateway_envelope(raw)
        if envelope is None:
            print(f"[{now_text()}] 收到非 JSON 消息: {raw}")
            return

        sender = str(envelope.get("from") or "?")
        business = extract_business_payload(envelope)
        biz_type = str(business.get("type") or "unknown")

        if biz_type == "reply":
            need_prompt = self._renderer.render_reply(
                business.get("data"),
                verbose=self.verbose,
            )
            if need_prompt:
                print(PROMPT, end="", flush=True)
            return

        if self.verbose:
            print(f"\n[{now_text()}] 收到来自 {sender} 的 {biz_type}:")
            print(pretty_json(envelope))
            print(PROMPT, end="", flush=True)
            return

        print(f"\n[{now_text()}] 收到来自 {sender} 的消息 ({biz_type}):")
        print(pretty_json(business))
        print(PROMPT, end="", flush=True)

    async def _reader_loop(self) -> None:
        """
        * @Author Leon-liao
        * @Function: _reader_loop()
        * @Description //后台读取 WebSocket 入站消息
        * @Date :2026/07/02 09:30:00
        * @Param: 无
        * @return：无
        """
        assert self._ws is not None
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")
                await self._handle_gateway_message(message)
        except websockets.ConnectionClosed as exc:
            print(f"\n[{now_text()}] 连接已关闭 code={exc.code} reason={exc.reason or ''}")
        except Exception as exc:
            print(f"\n[{now_text()}] 读循环异常: {exc}")
        finally:
            self._connected.clear()
            self._stop_event.set()

    async def _send_message(self, text: str) -> None:
        """
        * @Author Leon-liao
        * @Function: _send_message(text)
        * @Description //向 Hermes 发送点对点 message
        * @Date :2026/07/02 09:30:00
        * @Param: text: 用户输入文本
        * @return：无
        """
        if not self._ws or not self._connected.is_set():
            print("尚未连接，无法发送")
            return

        self._renderer.reset()

        business = build_app_message_payload(
            account_id=self.account_id,
            thread_id=self.thread_id,
            from_device=self.from_device,
            text=text,
        )
        envelope = build_p2p_envelope(self.hermes_ws_session_id, business)
        raw = json.dumps(envelope, ensure_ascii=False)

        async with self._send_lock:
            await self._ws.send(raw)

        print(f"[{now_text()}] 已发送 → {self.hermes_ws_session_id}: {text}")

    async def run(self) -> None:
        """
        * @Author Leon-liao
        * @Function: run()
        * @Description //连接网关并进入交互主循环
        * @Date :2026/07/02 09:30:00
        * @Param: 无
        * @return：无
        """
        url = self._build_ws_url()
        print(
            f"正在连接: {self.gateway_scheme}://{self.gateway_host}:"
            f"{self.gateway_port}{self.gateway_ws_path}?token=***"
        )

        try:
            async with websockets.connect(
                url,
                ping_interval=WS_CLIENT_PING_INTERVAL,
                ping_timeout=WS_CLIENT_PING_TIMEOUT,
                close_timeout=5,
            ) as ws:
                self._ws = ws
                self._connected.set()

                print(f"[{now_text()}] 已连接 WS Gateway")
                print(f"  ws_session_id  = {self.ws_session_id}")
                print(f"  hermes_peer    = {self.hermes_ws_session_id}")
                print(f"  account_id     = {self.account_id}")
                print(f"  from_device    = {self.from_device}")
                print(f"  thread_id      = {self.thread_id}")
                print("输入内容回车发送，/quit 退出，/raw 切换原始 JSON，/info 查看配置")
                print("-" * 60)

                reader_task = asyncio.create_task(self._reader_loop())
                print(PROMPT, end="", flush=True)

                while not self._stop_event.is_set():
                    try:
                        line = await asyncio.to_thread(input)
                    except (EOFError, KeyboardInterrupt):
                        print("\n退出中...")
                        break

                    command = line.strip()
                    if not command:
                        print(PROMPT, end="", flush=True)
                        continue

                    lower = command.lower()
                    if lower in ("/quit", "/exit", "/q"):
                        break

                    if lower == "/raw":
                        self.verbose = not self.verbose
                        mode = "开启" if self.verbose else "关闭"
                        print(f"[{now_text()}] 原始 JSON 显示已{mode}")
                        print(PROMPT, end="", flush=True)
                        continue

                    if lower == "/info":
                        print(f"[{now_text()}] 当前配置:")
                        print(
                            f"  gateway        = {self.gateway_scheme}://"
                            f"{self.gateway_host}:{self.gateway_port}{self.gateway_ws_path}"
                        )
                        print(f"  jwt_secret     = {self.jwt_secret[:4]}***")
                        print(f"  ws_session_id  = {self.ws_session_id}")
                        print(f"  hermes_peer    = {self.hermes_ws_session_id}")
                        print(f"  account_id     = {self.account_id}")
                        print(f"  from_device    = {self.from_device}")
                        print(f"  thread_id      = {self.thread_id}")
                        print(PROMPT, end="", flush=True)
                        continue

                    await self._send_message(command)
                    print(PROMPT, end="", flush=True)

                reader_task.cancel()
                try:
                    await reader_task
                except asyncio.CancelledError:
                    pass
        except Exception as exc:
            print(f"连接失败: {exc}")
            print("请确认网关可访问，且 JWT_SECRET 与 ws_session_id 配置正确")


def parse_args() -> argparse.Namespace:
    """
    * @Author Leon-liao
    * @Function: parse_args()
    * @Description //解析命令行参数
    * @Date :2026/07/02 09:30:00
    * @Param: 无
    * @return：argparse.Namespace
    """
    parser = argparse.ArgumentParser(
        description="WS Gateway App 端连续对话测试（v0.5 点对点协议）",
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_GATEWAY_HOST,
        help=f"网关地址（默认 {DEFAULT_GATEWAY_HOST}）",
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_GATEWAY_PORT,
        help=f"网关端口（默认 {DEFAULT_GATEWAY_PORT}）",
    )
    parser.add_argument(
        "--jwt-secret",
        default=DEFAULT_JWT_SECRET,
        help="JWT 签名密钥",
    )
    parser.add_argument(
        "--ws-session-id",
        default=DEFAULT_APP_WS_SESSION_ID,
        help="本端 ws_session_id（路由层）",
    )
    parser.add_argument(
        "--hermes-session-id",
        default=DEFAULT_HERMES_WS_SESSION_ID,
        help="Hermes 对端 ws_session_id",
    )
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID, help="业务 account_id")
    parser.add_argument(
        "--from-device",
        default=DEFAULT_DEVICE_ID,
        help="业务 from_device（逻辑设备 ID）",
    )
    parser.add_argument("--thread-id", default=DEFAULT_THREAD_ID, help="业务 thread_id")
    parser.add_argument("--verbose", action="store_true", help="打印 Hermes 原始 reply JSON")
    return parser.parse_args()


async def async_main() -> int:
    """
    * @Author Leon-liao
    * @Function: async_main()
    * @Description //异步入口
    * @Date :2026/07/02 09:30:00
    * @Param: 无
    * @return：进程退出码
    """
    args = parse_args()

    client = AppChatClient(
        gateway_host=args.host,
        gateway_port=args.port,
        jwt_secret=args.jwt_secret,
        ws_session_id=args.ws_session_id,
        hermes_ws_session_id=args.hermes_session_id,
        account_id=args.account_id,
        from_device=args.from_device,
        thread_id=args.thread_id,
        verbose=args.verbose,
    )
    await client.run()
    return 0


def main() -> int:
    """
    * @Author Leon-liao
    * @Function: main()
    * @Description //脚本入口
    * @Date :2026/07/02 09:30:00
    * @Param: 无
    * @return：进程退出码
    """
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
