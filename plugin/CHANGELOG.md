# plugin 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取 `ui/package.json` 的 `version`），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。**插件自身的发布版本号另见 `plugin/plugin.yaml` 的 `version`**（对 GitHub Release 用的那个），两份不要混。

## 0.1.4 — 2026-10-08 21:29
- 新增：适配器实现 send_video / send_voice，Hermes 侧可直接发送视频与音频（reply 帧 media_type=video/audio）
- 新增：上传支持音频/视频扩展名，大小分级 普通文件 16MB、音视频 1024MB；音视频上传超时 1800 秒
- 优化：multipart 改写临时文件并按块拷贝、带 Content-Length，大文件不再整段读进内存
- 新增：入站按 media_type 映射 PHOTO / VIDEO / AUDIO / DOCUMENT；协议文档同步 media_type 取值

## 0.1.1 — 2026-10-08 18:59
- 建立本模块的版本记录（插件发布版本见 `plugin/plugin.yaml`，当前 0.5.4）
