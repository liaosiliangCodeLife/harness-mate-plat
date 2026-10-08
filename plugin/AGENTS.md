# AGENTS.md — harness_mate 插件 (Go WS Gateway 方案)

> 部署: ~/.hermes/hermes-agent/plugins/platforms/harness_mate/
> 最后更新: 2026/07/02

---

## 一、BasePlatformAdapter 接口（不可改）

适配器**必须**实现以下抽象方法，签名**不能改**：

```python
class BasePlatformAdapter(ABC):
    async def connect(self) -> bool:          # 连接并认证
    async def disconnect(self) -> None:       # 断开清理
    async def send(self, chat_id, content,    # 发送消息
                   reply_to=None, metadata=None) -> SendResult:
    async def get_chat_info(self, chat_id) -> dict:  # 获取会话信息
```

还有两个非抽象但**必须实现**的：
```python
    async def handle_message(self, event: MessageEvent):  # 收到消息后调这个
    def build_source(self, chat_id, thread_id, ...):       # 构建 SessionSource
```

---

## 二、文件结构

```
harness_mate/
├── plugin.yaml              ← 用户配置 bot_id + bot_key
├── adapter.py               ← 主逻辑（继承 BasePlatformAdapter）
├── requirements.txt
├── ws_client_p2p_example.py ← 点对点测试客户端示例
└── __init__.py              ← from .adapter import register
```

---

## 三、plugin.yaml（用户配置）

```yaml
name: harness_mate
kind: platform
version: 0.5.2
config:
  bot_id: ""        # Bot ID，连接 ws_gateway 时作为 ws_session_id
  bot_key: ""       # Bot key，用于 WS JWT HMAC 签名（与 ws_gateway JWT_SECRET 共用）
  dm_policy: open
  allow_from: []
```

环境变量（可选）：
- `HARNESS_MATE_BOT_ID` / `HARNESS_MATE_BOT_KEY`
- `HARNESS_MATE_ALLOWED_PEERS` / `HARNESS_MATE_DM_POLICY`

---

## 四、adapter.py 约束

- ✅ 方法名 `connect()` / `disconnect()`（不是 start/stop）
- ✅ 消息上报用 `await self.handle_message(event)`（不是 self.emit）
- ✅ `send(chat_id, content, reply_to, metadata)` 签名不能改
- ✅ thread_id 从 metadata 拿
- ✅ 必须实现 `get_chat_info(chat_id) -> dict`
- ✅ 文件底部必须有 `def register(ctx)` 函数
- ✅ 必须有 `_build_adapter(config)` 工厂函数
- ✅ 用 websockets 库直连 Go WS Gateway `/ws` 端点
- ✅ 错误用 logging.exception，不吞异常

---

## 五、测试

使用 `ws_client_p2p_example.py` 连接本地 ws_gateway 进行点对点消息测试。
