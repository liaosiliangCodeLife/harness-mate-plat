# hub 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取 `ui/package.json` 的 `version`）。

## 0.2.0 — 2026-10-26 08:47
- 调整：下行实时帧只走 Redis pub/sub（`PUBLISH stream:<account_id>`），删除只写不读的 `inbox:<account_id>:<thread_id>` List
- 调整：内部消息落库改为先读响应体再判 `code`，`stored:false` 只告警不重试；4xx 不重试，5xx/429/网络错误重试 3 次
- 新增：`hub/docs/API.md`（Hub 对外接口文档）与架构说明

