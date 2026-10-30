# plugin 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取 `ui/package.json` 的 `version`），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。**插件自身的发布版本号另见 `plugin/plugin.yaml` 的 `version`**（对 GitHub Release 用的那个），两份不要混。


## 0.6.7 — 2026-10-30 09:10
- 新增：采集 GatewayAgent 工具事件，随 done 帧上报 agent_thoughts（供平台侧 AgentThought 展示执行过程）
- 发布版本：插件 `0.6.6` → `0.6.7`
- 文档：安装/更新命令改用独立插件仓库 `liaosiliangCodeLife/harness-mate-hermes`（原路径指向平台仓库 GitHub 冻结副本，停在 0.6.2）；README 版本号同步 `0.6.5` → `0.6.7`

## 0.6.6 — 2026-10-29 21:16
- 修复：房间里 agent 发图片/文件失败 —— 房间消息的 `thread_id` 是 `room:<id>`，平台没有对应 conversation，免登录上传接口按 `Conversation.thread_id` 查会话必定 404（`thread_id 对应的会话不存在或不属于该智能体`）。`upload_open_api_file` 新增可选 `room_id` 形参并写入 multipart；`_deliver_local_file` 从 `_room_fields(thread_id)` 取出 room_id 透传，后端据此按「该 agent 是该房间已加入成员」兜底放行
- 配套服务端：`/open-api/upload-file` 接受可选 `room_id`（平台 0.3.37+），仅在 thread_id 查不到会话时启用兜底，越权仍拒
- 发布版本：插件 `0.6.5` → `0.6.6`

## 0.6.5 — 2026-10-29 21:02
- 新增：风险审批 —— 覆写 `_send_exec_approval_prompt`，发 `data.approval` 帧到网关（由网关上报平台 `/internal/approvals`），并发送文本兜底；后台轮询 `GET /internal/approvals/lookup`，决策后调用 `tools.approval.resolve_gateway_approval` 解阻塞
- 新增可选环境变量：`HARNESS_MATE_INTERNAL_TOKEN`（审批轮询）、`HARNESS_MATE_API_BASE`（缺省 `https://harness.alltman.com/api`）
- 发布版本：插件 `0.6.4` → `0.6.5`

## 0.6.4 — 2026-10-29 19:10
- 修复：插件发送图片/文件时平台前端显示空白气泡 —— reply 帧补 `files` 数组（`{url, name, media_kind, is_image}`），与平台 `save_reply` 的 `inner["files"]` 契约对齐；原来只发 `url`/`file_name`/`media_type`，平台不读这三个字段，导致 `message_info` 为空、附件丢失（保留旧字段兼容老平台）

## 0.6.3 — 2026-10-29 16:30
- 新增（P3）：Hermes 插件支持房间 —— 入站带 `room_id` 时用 `room:<room_id>` 作为独立会话键（房间与私聊上下文隔离），出站 reply / 文件帧原样带回 `room_id` + `reply_to` + `bot_id`
- 调整：房间会话不写「最近线程」`_last_thread_by_chat`，避免顶掉私聊的线程兜底
- DSH 插件：出站信封增加 `bot_id`（平台据此在房间里定位是哪个 agent 回的话），发布版本 `0.2.7`

## 0.3.6 — 2026-10-27 00:05
- 修复：DSH 插件上传文件时只传 `session_id`、没传必填的 `thread_id`，线上报「thread_id 不能为空」，手机端收不到文件
- 调整：`uploadToGateway` 改为传 `thread_id`（与 Hermes 插件 0.6.1 对齐）；新增 `resolveThreadId()` 兜底（入参 → `ownedAgents` 同 peer 的 threadId → `replyTargets` 反查），对齐 Hermes 插件 0.6.2 的出站兜底策略
- 发布版本：DSH 插件 `0.2.0` → `0.2.1`

## 0.6.2 — 2026-10-26 17:05
- 修复：主动出站（cron 推送、非回复触发）时 `_resolve_target()` 取不到 `thread_id`（只读 `metadata["thread_id"]`），导致上传接口报「thread_id 不能为空」，图片/文件发不出去
- 调整：`thread_id` 兜底顺序改为 `metadata.thread_id` → `metadata.session_id` → 该账号最近一次收消息的 `thread_id`（新增 `_last_thread_by_chat`）→ 从 `_reply_targets` 反查
- 发布版本：插件 `0.6.1` → `0.6.2`

## 0.6.1 — 2026-10-26 11:45
- 修复：发送本地图片/文件时，上传接口传错参数（把 peer 的 `ws_session_id` 当成了 `thread_id`），线上报「thread_id 对应的会话不存在或不属于该智能体」，图片发不出去；改为传真实会话 `thread_id`（`td-...`）
- 发布版本：插件 `0.6.0` → `0.6.1`

## 0.2.0 — 2026-10-26 09:06
- 调整：上传表单同时带 `session_id` 与 `thread_id`，兼容 Hub 架构（WS 连接下沉到后端后不再有 `ws_session_id`），修复发图片报「session_id 不能为空」
- 新增：`plugin/README.md`、`plugin/hermes/README.md`、`plugin/dsh/README.md` 三份文档（架构、安装、协议索引）
- 发布版本：插件发布版本 `0.5.5` → `0.6.0`（`plugin.yaml`）

## 0.1.8 — 2026-10-10 08:35
- 新增：插件在 Hermes 里的渠道图标从 🔗 换成 🧩
- 新增：上传白名单支持主流压缩包（zip、rar、7z、tar、gz、tgz、bz2、tbz、tbz2、xz、txz、zst、zipx、cab、jar、war），压缩包上限 100MB，其它文档仍 16MB、音视频 1024MB
- 优化：安装指引与文档路径统一到 plugin/hermes

## 0.1.5 — 2026-10-08 22:14
- 修复：上传接口偶发失败（连接被对端 reset，实测失败率 12%-25%）时不再直接放弃，改为自动重试最多 4 次（退避 0.5s / 1.5s / 3s）
- 优化：服务端业务错误（session_id 不存在、bot_key 校验失败等）仍只请求一次，不重试
- 优化：重试耗尽后的报错带上最后一次底层原因，便于定位

## 0.1.4 — 2026-10-08 21:29
- 新增：适配器实现 send_video / send_voice，Hermes 侧可直接发送视频与音频（reply 帧 media_type=video/audio）
- 新增：上传支持音频/视频扩展名，大小分级 普通文件 16MB、音视频 1024MB；音视频上传超时 1800 秒
- 优化：multipart 改写临时文件并按块拷贝、带 Content-Length，大文件不再整段读进内存
- 新增：入站按 media_type 映射 PHOTO / VIDEO / AUDIO / DOCUMENT；协议文档同步 media_type 取值

## 0.1.1 — 2026-10-08 18:59
- 建立本模块的版本记录（插件发布版本见 `plugin/plugin.yaml`，当前 0.5.4）
