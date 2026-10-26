# docker 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取 `ui/package.json` 的 `version`），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。

## 0.3.0 — 2026-10-26 15:28
- 调整：compose 按服务固定 CPU 亲和（cpuset）—— postgres `0-7`、api `8-19`、hub `20-23`、ui `24-25`、nginx `26-27`、redis `28`、certbot `29`，`30-31` 预留
- 调整：postgres 启动参数 `max_connections=200`、`shared_buffers=4GB`、`effective_cache_size=10GB`、`work_mem=8MB`、`maintenance_work_mem=512MB`
- 调整：redis 增加 `--maxmemory 1gb --maxmemory-policy allkeys-lru`
- 说明：api 的 gunicorn 改为 8 workers × 16 threads（=128 并发槽），`SQLALCHEMY_POOL_SIZE=12`，8×(12+10)=176 连接 < PG 上限 200

## 0.1.1 — 2026-10-08 18:59
- 建立本模块的版本记录（更早的历史暂未补录）
