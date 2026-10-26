# gateway 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取 `ui/package.json` 的 `version`），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。

## 0.2.0 — 2026-10-26 08:47
- 新增：按 `bot_id`（或 `peer_id`）向平台 `GET /internal/bot-key` 取 `gateway_key`，再本地 HMAC-SHA256 验签；密钥缓存 60 秒，平台不可达时**直接拒绝**，不回退共享密钥
- 新增：配置项 `PLATFORM_API_BASE_URL`、`PLATFORM_INTERNAL_TOKEN`、`PLATFORM_BOT_KEY_CACHE_TTL`
- 调整：`JWT_SECRET` 降级为「未配置平台地址」时的回退方案，启动打 WARN

## 0.1.1 — 2026-10-08 18:59
- 建立本模块的版本记录（更早的历史暂未补录）
