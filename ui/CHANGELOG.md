# ui 版本记录

> 约定：每次提交前，先在本文件顶部新增一条 `## <版本号> — <YYYY-MM-DD HH:MM>`，列出这次提交里本模块的改动。版本号是平台级的（取本模块 `package.json` 的 `version`，页面上展示的 Version 与它同源），每次提交 +1；改动落在哪个模块，就写进哪个模块的记录。

## 0.1.6 — 2026-10-09 07:51
- 新增：换上 HarnessMate 品牌图标（八爪鱼）——网站 favicon（favicon.ico / favicon.svg）、Apple Touch Icon、仓库 logo 全部替换，移除 Vue 默认的 favicon.webp
- 新增：assets/ 增加矢量版 logo.svg（透明底，可随文字换色）与 icon.svg（圆角渐变底）

## 0.1.2 — 2026-10-08 19:33
- 修复：AI 助手气泡不再跟随系统深色模式（改为只引入 github-markdown-css 浅色版，并强制灰底/深字）
- 修复：等待回复时的提示文案统一为「思考中」，只有开始输出正文后才显示「生成中」

## 0.1.1 — 2026-10-08 18:59
- 修复：进入会话时消息列表没定位到最新一条（会话末尾是图片时会停在上面、图片被截断）
- 新增：登录页与主页展示版本号（Version 0.1.1），版本号由 vite `define` 注入（取值 `ui/package.json` 的 `version`）
