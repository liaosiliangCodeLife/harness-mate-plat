# Hub

> **状态：开发中** —— 暂不同步到 GitHub 副本（`harness-mate-plat-github`），只留在 gitee 主库。

后端 WebSocket 汇聚层。前端**既不直连网关，也不直连 Hub**——WS 全部由 Hub 持有，前端只保留一条到 API 的 SSE 连接。

## 链路

```
① 上行
浏览器 ─POST /api/chat/send─> API(Flask) ─POST http://hub:8090/send─> Hub ─WS─> 网关 ─WS─> Hermes
                              （带 agent_id/bot_id/gateway_url/key）  （身份 agent.peer_id，缺失时回退 hub-<bot_id>）

② 下行
Hermes ─WS─> 网关 ─WS─> Hub ─PUBLISH─> Redis ─pubsub 订阅─> API(SSE) ─> 浏览器

③ 回写
Hub ─POST /internal/messages（done 帧原样）─> API ─> message_service ─> PostgreSQL
```

三条路互相独立：上行失败不影响下行；回写失败不影响实时推送（只是历史里可能缺一条）。

## 协议与鉴权

| 跳 | 协议 | 鉴权 | 说明 |
|---|---|---|---|
| 浏览器 → API | HTTP / SSE | 用户 `access_token` | 前端只认 API，不知道 Hub 存在 |
| API → Hub | docker 内网 HTTP | `X-Internal-Token` | 超时 3 秒，失败直接返回错误，不重试 |
| Hub → 网关 | WS | `gateway_key` 签的 JWT | 身份使用 `agent.peer_id`，缺失时回退 `hub-<bot_id>`，常连不断 |
| Hub → Redis | Redis pub/sub | 内网 | `PUBLISH stream:<account_id>` |
| Redis → API | Redis pub/sub 订阅 | 内网 | SSE 生成器订阅频道（空闲 20s 发心跳） |
| Hub → API | docker 内网 HTTP | `X-Internal-Token` | 只转发 `done=true` 的帧，原样不动 |

## 职责（只有三条）

1. **持连接**：每个智能体一条 WS 连到网关，身份使用 `agent.peer_id`，缺失时回退 `hub-<bot_id>`，常连不断。
2. **转发帧**：收到 Hermes 的 reply 帧 → 按 `(account_id, thread_id)` 发布到 Redis 频道，供 Flask 的 SSE 端点取走。
3. **回写消息**：`done=true` 的帧**原样** POST 给 `POST /internal/messages`，由 API 完成落库。

没有第四条。业务逻辑（帧→message 字段映射、seq、`conversation` 冗余字段）全部留在 API 侧，Go 里零业务。

## 为什么必须常连

- 网关在目标不在线时**直接 drop、不重试**（`gateway/internal/router/router.go:68`）。
- 用户关页面、退出登录后，Hermes 仍会跑完并推送；Hub 一旦断开，这条回复永久丢失。

## 关键约定

- 上游连接身份使用 `agent.peer_id`，缺失时回退 `hub-<bot_id>`，重连不换 id —— Hermes 的 `_reply_targets` / `_last_peer_session` 才认得住它（`plugin/hermes/adapter.py:597`）。
- 回写走服务间令牌 `X-Internal-Token`，**不能用用户的 access_token**：用户退出登录后 token 失效，而这里恰恰要覆盖"用户不在线"的场景。
- 内部接口**不能使用 `current_user`**，`account_id` 只能从帧的 payload 里取。
- 只监听 docker 内网，不对外暴露；Nginx 对 `/api/internal/` 一律 deny。
- 上游没有 `type: "hello"` 帧的约定，Hub 不需要握手，只要发过一条真实消息，Hermes 就会记住它。

## 内部接口契约（POST /internal/messages）

| 情况 | HTTP | body |
|---|---|---|
| X-Internal-Token 不匹配 | 403 | code=FORBIDDEN，message="内部令牌无效"，data={} |
| body 不是 JSON 对象 | 400 | code=VALIDATE_ERROR，message="请求体必须是JSON对象"，data={} |
| 不是 done 帧（无需落库） | 200 | code=SUCCESS，data={"stored": false} |
| 会话不存在 / account_id 非法（save_reply 返回 stored=false） | 200 | code=SUCCESS，data={"stored": false} |
| 落库成功 | 200 | code=SUCCESS，data={"stored": true} |
| 任何未预期异常 | 500 | code=FAIL，message="内部消息写入失败"，data={} |

Hub 只把 `code == "success" && data.stored == true` 当成功；`stored == false` 记 warn 不重试；4xx 不重试；5xx / 网络错误重试 3 次。

## 实现要点

1. **API → Hub 必须带超时**（3s），Hub 挂了不能把 API 拖死；失败直接向前端返回"服务暂时不可用"。
2. **Redis 这一跳省不掉**：Flask 有 4 个 worker 不共享内存，Hub 直接 POST 回 Flask 会落到随机 worker，SSE 连接在别的 worker 上收不到。
3. **两条回路（API→Hub、Hub→API）方向相反、互不相关**，共用同一个 `INTERNAL_TOKEN` 即可，别复用用户 token。
4. **SSE 生成器绝不能 `return`**：`done` 是帧的属性，不是连接结束信号；返回就断了下一轮推送。

## 下发推送（SSE）

API 提供 `GET /chat/stream`，一条流承载该账号**所有会话**的帧：

- 鉴权：普通 `Authorization: Bearer`，EventSource 场景可用 `?token=` 兜底
- 数据源：`SUBSCRIBE stream:<account_id>`（Hub 把下行帧 PUBLISH 到该频道）
- 帧格式：`data: <完整网关帧 JSON>\n\n`，客户端按 `data.account_id + data.thread_id` 分发
- 空闲每 20 秒发一次 `: ping`，**生成器永不 return**（只有客户端断开才结束）
- 落库由 `POST /internal/messages` 负责，与推送互不依赖

## 订阅与缓存

- 权威存储是 PostgreSQL 的 `message` 表，实时帧只走 pub/sub，不保留待补队列。用户回来时走历史接口。

## 技术栈

Go，与 `gateway/` 同栈，复用 `gateway/internal/model`（帧结构）与 `gateway/internal/jwt`（HS256 签名）。

部署为独立二进制，docker compose 里一个 `hub` 服务，`restart: always`。
