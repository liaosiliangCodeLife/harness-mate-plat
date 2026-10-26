# ui 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取本模块 `package.json` 的 `version`，页面上展示的 Version 与它同源），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。

## 0.3.5 — 2026-10-26 23:57
- 调整：创建/编辑智能体弹窗标题改分色 —— 「创建」黑色 + 「Hermes」蓝色 `#165dff`，字号 23px/700，与「配对 Hermes」弹窗一致
- 调整：弹窗底部改为带上分隔线的 footer 区，取消/保存按钮统一 10px 圆角，视觉对齐「配对 Hermes」弹窗
- 新增：locales `agent.createTitle` / `agent.editTitle`（中英文）

## 0.3.4 — 2026-10-26 23:49
- 调整：创建智能体弹窗改为圆润风格 —— 弹窗圆角 22px、宽度 480，与「连接 Hermes」弹窗一致
- 调整：弹窗标题字号 23px / 字重 700 / 颜色改为蓝色 `#165dff`；底部按钮圆角 10px

## 0.3.3 — 2026-10-26 23:38
- 调整：新建智能体弹窗不再暴露 bot_id / peer_id，表单只保留头像上传 + 名称；创建请求不再携带这两个字段，改由后端自动生成
- 调整：编辑模式 bot_id / peer_id 改为纯文本只读展示（与 agent_type / secret 同风格）
- 移除：`generateAgentId` 服务方法及配套类型；下线前端对 `GET /agent/generate-id` 的调用
- 调整：新建会话的 `thread_id` 改为前端本地生成（`td-` + 毫秒时间戳），不再依赖已下线的生成标识接口
- 移除：locales `agent.businessId` / `businessIdRequired` / `peerId` / `peerIdRequired` / `botIdPlaceholder` / `peerIdPlaceholder` 与 `common.generate`


## 0.3.2 — 2026-10-26 23:23
- 调整：新建智能体弹窗不再拉取共享网关 —— 创建模式改为提示「创建后自动分配专属网关与密钥」，编辑模式仍展示该智能体自己的 `gateway_url` / `gateway_key`
- 新增：locales `agent.gatewayAutoAssigned`（中英文）


## 0.3.1 — 2026-10-26 23:02
- 移除：侧边栏「频道服务」菜单项与 `/server` 路由、页面 `views/server/ListView.vue`
- 移除：无路由引用的孤儿页面 `views/space/server/ListView.vue`
- 调整：`hooks/use-server.ts` 只保留 `useGetOpenServer`（创建智能体仍用它拉网关），删掉无引用的 `useGetServer` / `useGetOpenServers`
- 调整：locales 删除 `layout.channelService` 与整段 `server`（zh-CN / en-US 结构保持一致）


## 0.3.0 — 2026-10-26 15:28
- 新增：智能体详情页背景改为品牌海报 —— 白底 + 居中的类型大字（`HERMES AGENT` / `DEEPSEEK AGENT`，无 @）+ 一行灰色说明，按 agent_type 自动切换
- 新增：新建会话还没有任何消息时，聊天区也显示同一套海报；全屏查看该卡片时海报自动放大约 10 倍
- 调整：会话有内容后，详情页背景切换为该类型浅色底（Hermes 浅蓝 `#EFF6FF` / DeepSeekHarness 浅紫 `#F5F3FF`），海报自动隐藏
- 调整：消息改为左右分栏 —— 自己发的整行靠右（头像、气泡、名称右对齐），AI 回复靠左
- 新增：每条消息在名称旁显示时间戳 `YYYY-MM-DD HH:mm:ss`（用户消息时间在名称左侧，AI 消息在右侧）
- 调整：移除「暂无消息 / 暂无会话」空态，空状态统一由海报承接
- 新增：抽出 `components/AgentPoster.vue` 公共组件，详情页（`clamp(56px, 9vw, 150px)`）与会话卡片（60px 小号）共用

## 0.2.2 — 2026-10-26 10:49
- 调整：智能体详情页**整页**背景按类型着色（Hermes 浅蓝 `#EFF6FF`、DeepSeekHarness 浅紫 `#F5F3FF`、未知浅灰），顶部信息栏一起着色，不再是只有中间一块
- 调整：聊天卡片在**没有任何消息**时整卡使用该类型的底色，一旦有对话恢复白底；移除上一版加在标题旁的类型标签
- 调整：智能体卡片操作菜单文案 —— 「配对 Hermes / 配对 DeepSeek Harness」改为「连接 Hermes / 连接 DeepSeekHarness」，英文改为 Connect Hermes / Connect DeepSeek Harness

## 0.2.1 — 2026-10-26 10:30
- 新增：智能体详情页背景按智能体类型着色 —— Hermes 浅蓝 `#EFF6FF`、DeepSeekHarness 浅紫 `#F5F3FF`、其它或未知浅灰 `#FAFAFA`，切换智能体时颜色跟着变
- 新增：聊天卡片在**没有任何消息**时，标题旁显示智能体类型小标签（浅底 + 同色系文字，Hermes 蓝字、DeepSeek 紫字）；一旦有对话该标签自动隐藏
- 新增：`ui/src/utils/agent-theme.ts` 统一管理类型配色与文案 key，详情页与聊天卡片共用

## 0.2.0 — 2026-10-26 08:47
- 调整：聊天发送改为 RESTful 路径 `POST /agents/:agent_id/conversations/:thread_id/chat/send`，请求体带 `text` 与 `messageId`，有附件时再带 `files`
- 调整：用户消息不再由前端补写落库（删除 `persistUserMessage`），改由服务端在发送接口内同步落库，刷新页面即可看到自己的提问
- 说明：接收仍走全局 `GET /chat/stream?token=`（一个账号一条 SSE，承载该账号下全部会话）

## 0.1.17 — 2026-10-12 22:05
- 优化：前端 WebSocket 通道的关闭方式——页面真正卸载（pagehide，进出往返缓存时不关）、退出登录、以及收到 401 跳登录页之前，都会以正常关闭码断开连接，不再留下僵尸连接
- 新增：同一会话被其他设备或页面占用时，连续 3 次「连上即断」（存活不足 5 秒）后停止自动重连，并提示「该会话已在其他设备或页面打开」

## 0.1.16 — 2026-10-12 19:29
- 新增：主页新增「操作视频」区块并放在页面内容最上方（标题与简介之后、教程标签页之前），内嵌 Hermes 版完整操作视频（5 分 45 秒，托管在 GitHub）；中文界面用中文讲解版、英文界面用英文讲解版；DeepSeek Harness 版视频稍后补充

## 0.1.15 — 2026-10-12 18:51
- 优化：聊天卡片内的文字整体调小 —— 消息气泡正文 14px→11px，markdown 内的代码/表格 12px→10px，发送者名字 14px→11px，时间与状态提示、附件名与文件大小 12~14px→10px，输入框文字与 placeholder 14px→11px（行高 22px→20px 同步调整）；卡片外面的列表、导航与按钮字号保持不变

## 0.1.14 — 2026-10-12 10:04
- 新增：中英文切换（基于 vue-i18n@9）—— 侧边栏账号下拉与设置弹窗新增「语言 / Language」，切换后界面全部文案立即变英文/中文，无需刷新，选择记在 localStorage 刷新后保持；Arco 组件内置文案（弹窗按钮、分页、日期、空状态）随语言切换，页面标题与 `<html lang>` 同步
- 新增：智能体卡片上设备上报信息的字段名支持翻译（内存→Memory、硬盘→Disk、系统→System 等，未收录的键名原样显示）
- 依赖：新增 vue-i18n@9

## 0.1.13 — 2026-10-11 17:06
- 新增：侧边栏顶部 GitHub 入口展示仓库当前 star 数（打开页面时请求 GitHub API 的 stargazers_count，形如 GitHub ★ 11；请求失败或超时不展示，按钮宽度 110px→128px 避免溢出）

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
