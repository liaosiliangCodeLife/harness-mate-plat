# api 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取 `ui/package.json` 的 `version`，页面上展示的 Version 同源），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。

## 0.3.3 — 2026-10-26 23:38
- 调整：创建智能体时 `bot_id` / `peer_id` 改为可选；为空则由 `generate_agent_identifier` 自动生成，有值仍沿用（向后兼容）
- 新增：自动生成标识时查库防 `uk_agent_bot_id` / `uk_agent_peer_id` 冲突（含软删除记录），最多重试 5 次，仍冲突抛「智能体标识生成失败，请重试」
- 移除：下线 `GET /agent/generate-id` 及 `GenerateAgentIdReq` / `AgentHandler.generate_agent_id`


## 0.3.2 — 2026-10-26 23:23
- 新增：新建智能体时自动创建专属 `server` 网关记录 —— `gateway_url` 取自新增配置项 `WS_GATEWAY_URL`（默认 `wss://ws-agent.alltman.com:1443/ws`），`gateway_key` 由 `internal/lib/gateway_key.py::generate_gateway_key()` 随机生成（32 位 base62，大小写字母+数字）
- 调整：`create_agent` 忽略入参 `gateway_id`，改为先建专属网关再建智能体，一个智能体对应一条网关记录，不再复用共享网关
- 修复：智能体创建失败（如 `peer_id` 唯一键冲突）时回滚刚创建的网关记录，避免留下孤儿数据


## 0.3.1 — 2026-10-26 23:02
- 新增：删除智能体后通知 Hub 关闭其上游 WebSocket —— `AgentService.delete_agent()` 软删成功后调 `POST {HUB_BASE_URL}/disconnect`（`_notify_hub_disconnect`，带 `X-Internal-Token`，超时 2s，失败只记 warning 不影响删除）
- 说明：`AgentService` 注入 `Config`，与 `ChatService` 同模式


## 0.2.0 — 2026-10-26 08:47
- 新增：`GET /internal/bot-key`（服务间接口，`X-Internal-Token` 校验）—— 按 `session_id` 返回智能体所属网关的 `gateway_key`；`session_id` 取 `bot_id` 或 `peer_id` 均可命中（Hermes 插件报 bot_id、Hub 报 peer_id），已删除智能体统一 404
- 调整：聊天发送改为 `POST /agents/:agent_id/conversations/:thread_id/chat/send`（agent/thread 放路径，body 只带聊天内容），旧 `/chat/send` 下线；用户提问在同一请求内同步落库，不再依赖前端补写
- 调整：删除 JWT 的 `jti` 单点登录机制，改为无状态 JWT，同一账号可多端同时在线
- 调整：`/internal/messages` 返回真实 HTTP 状态码（403 / 400 / 200），并用 `stored` 区分落库成功与业务跳过，供 Hub 判断是否需要重试
- 安全：`INTERNAL_TOKEN` 为空时拒绝一切内部请求；Nginx 对 `/api/internal/` 只放行 WS 网关所在 IP 与容器内网

## 0.1.12 — 2026-10-10 12:11
- 新增：`POST /agents/:agent_id/online-status`（请求体 `{"status": 0|1}`，需登录）—— 把智能体在线状态写入 `agent.status`
- 调整：智能体列表/详情接口的 `status` 改为直接读 `agent.status` 列；删除 90 秒时间窗在线判定（`internal/lib/agent_online.py` 已删除）
- 文档：`api/docs/HermesMate-Api文档.md` 已补充该接口说明

## 0.1.3 — 2026-10-08 20:18
- 新增：免登录上传接口支持音频 / 视频（扩展名白名单新增 mp3/wav/m4a/aac/flac/ogg/oga/opus/amr/wma/aiff/mka 与 mp4/mov/m4v/avi/mkv/webm/flv/wmv/mpeg/mpg/ts/3gp）
- 调整：免登录上传大小分级 —— 普通文件（图片 / 文档）16MB，音频 / 视频 1024MB
- 优化：上传改为流式（分块算 sha3_256、文件对象直接交 COS SDK），大文件不再整段读进内存
- 调整：部署内 nginx client_max_body_size 50M → 1100M
- 文档：API 文档第 1.3 节同步新的类型与大小限制

## 0.1.1 — 2026-10-08 18:59
- 建立本模块的版本记录（更早的历史暂未补录）
