# ui 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取本模块 `package.json` 的 `version`，页面上展示的 Version 与它同源），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。

## 0.1.12 — 2026-10-10 12:11
- 新增：聊天卡片按对话结果上报智能体在线状态 —— 收到助手回复结束即写「在线」；连不上网关、发出后 90 秒无任何回复、发送报错则写「离线」
- 调整：去掉 60 秒在线心跳与「WS 一连上就算在线」的逻辑；列表/详情直接读接口返回的库值，不再实时计算

## 0.1.11 — 2026-10-10 11:09
- 新增：智能体卡片名称旁展示接入类型（形如 `名字@HERMES`，类型用主色蓝 #165DFF）；名称下方不再单独显示类型行
- 新增：「配对」入口与弹窗按接入类型区分——DEEPSEEK_HARNESS 智能体显示「配对 DeepSeek Harness」并复制 DSH（`plugin/dsh`）的安装指令；Hermes 智能体保持「配对 Hermes」与其原有指令
- 优化：主页 DeepSeek 教程里提到的入口名同步改为「配对 DeepSeek Harness」

## 0.1.10 — 2026-10-10 10:24
- 新增：主页把 Hermes 与 DeepSeek Harness 两套教程做成内嵌标签页（位于平台介绍下方，默认「Hermes 教程」）
- 新增：补齐 DeepSeek Harness 的安装教程与插件安装教程（含命令、链接与 `<bot_id>` / `<bot_key>` 占位符，结构与 Hermes 两块一致）
- 优化：教程块由左右并排改为整宽上下排列，长命令不再折行

## 0.1.9 — 2026-10-10 09:21
- 新增：编辑智能体弹窗展示只读的「智能体接入类型」（HERMES→Hermes智能体、DEEPSEEK_HARNESS→DeepSeekHarness智能体，其它值原样显示，空值 `-`）；创建弹窗布局与提交逻辑不变

## 0.1.8 — 2026-10-10 08:35
- 新增：个人空间按智能体接入类型分栏（Hermes智能体 / DeepSeekHarness智能体）—— 创建时自动带上当前分栏的类型、列表按类型过滤、卡片名称下显示类型
- 新增：对话上传支持主流压缩包（zip/rar/7z/tar.gz 等，上限 100MB）
- 优化：插件安装指引与文档链接改到 plugin/hermes

## 0.1.7 — 2026-10-09 08:28
- 新增：聊天气泡支持音频、视频内联播放（`<audio>` / `<video>` 带 controls、playsinline），收到音视频不用再下载成文件卡片
- 优化：文件类型判定统一为 media_kind（image / audio / video / file），按 reply 的 media_type、MIME 前缀与扩展名识别；is_image 与 media_kind 保持一致

## 0.1.6 — 2026-10-09 07:51
- 新增：换上 HarnessMate 品牌图标（八爪鱼）——网站 favicon（favicon.ico / favicon.svg）、Apple Touch Icon、仓库 logo 全部替换，移除 Vue 默认的 favicon.webp
- 新增：assets/ 增加矢量版 logo.svg（透明底，可随文字换色）与 icon.svg（圆角渐变底）

## 0.1.2 — 2026-10-08 19:33
- 修复：AI 助手气泡不再跟随系统深色模式（改为只引入 github-markdown-css 浅色版，并强制灰底/深字）
- 修复：等待回复时的提示文案统一为「思考中」，只有开始输出正文后才显示「生成中」

## 0.1.1 — 2026-10-08 18:59
- 修复：进入会话时消息列表没定位到最新一条（会话末尾是图片时会停在上面、图片被截断）
- 新增：登录页与主页展示版本号（Version 0.1.1），版本号由 vite `define` 注入（取值 `ui/package.json` 的 `version`）
