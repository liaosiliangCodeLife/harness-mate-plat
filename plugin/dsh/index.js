/**
 * HarnessMate —— 把 DSH 接入 HarnessMate 平台（本机 Agent 的手机/浏览器入口）
 *
 * 平台项目：https://github.com/liaosiliangCodeLife/harness-mate-plat
 * 参照对端实现：hermes 的 plugin/adapter.py（harness_mate 平台适配器）
 * 协议规范：hermes_channel_protocol.md v0.5.2
 *
 * 角色定位：本插件 = 网关上的一个「Agent 端」（与 Hermes 对等，不是 Peer）
 *
 *   手机 App (Peer)  ──{to, data:message}──▶  WS Gateway  ──▶  本插件
 *   手机 App (Peer)  ◀──{from, data:reply}──  WS Gateway  ◀──  本插件
 *
 * 网关硬性要求（协议 §9.1）：
 *   - 连接必须带 JWT：ws(s)://<host>:<port>/ws?token=<jwt>
 *   - JWT claims: { ws_session_id: <bot_id>, exp, iat }，HS256，密钥 = bot_key
 *   - bot_key 必须与网关 JWT_SECRET 一致，否则 401
 *   - 回复信封的 to 必须等于入站 from（用 from_device 会被判 target is offline）
 *   - 客户端 ping 间隔 50s；网关读超时 90s
 *
 * 本插件只做两件事 + 一条连接：
 *   1. 连网关（JWT 鉴权、重连、ping）
 *   2. 订阅 agent/assistant-stream → 按 reply 协议流式发出
 *   3. 拦截 approval/request → 推给 App，等用户同意/拒绝
 */

import { createHmac } from 'node:crypto';
import { appendFileSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { basename, isAbsolute, join } from 'node:path';
// ★ 官方姿势（dsh-headless 同款）：Agent 的模型选择必须通过 installModelSelection
// 安装到 agent 作用域；它负责在 system-prompt/assemble 时注入 {{provider}}/{{model}}
// 变量（否则整轮 prompt 组装报 "prompt variable {{model}} has no value"），
// 并在 agent/request 时带上 provider/model。不加它会得到空回复。
import { installModelSelection } from '@deepseek-ai/dsh-agent';

export const name = 'harness-mate';

// ⚠️ 刻意不声明 inject。
// 实测（探针 v3）：`agents` 服务在插件加载后约 500ms 才可用，
// 声明 inject 会让 apply() 一直等待而不执行（实测 apply 从未运行）。
// 因此改为「apply 先跑，服务就绪后再初始化」——见下方 waitForService。
// 若未来需要严格顺序，可加回 inject，但要先确认服务在本插件加载时已激活。

/**
 * 启动自证：把加载痕迹写到工作区文件。
 * 原因：DSH 不往磁盘写运行日志，在 GUI 外看不到插件日志，无法判断插件是否被加载。
 * 落盘位置在 apply() 时确定：CFG.traceFile ?? <workspace>/.harness-mate-trace.log（HOME 兜底）。
 * 模块加载 → apply 之间的日志先缓冲，写入点就绪后一并刷出（写失败时保留，最多 500 条）。
 */
let tracePath = null;
const traceBuffer = [];
function trace(msg) {
  traceBuffer.push(`${new Date().toISOString()} ${msg}\n`);
  if (tracePath === null) return;
  try {
    appendFileSync(tracePath, traceBuffer.join(''));
    traceBuffer.length = 0;
  } catch { /* 忽略；缓冲保留 */
    if (traceBuffer.length > 500) traceBuffer.splice(0, traceBuffer.length - 500);
  }
}

// 模块被 import 时就留痕 —— 能区分「bundle 没加载」和「插件 apply 没跑」
trace('module imported (bundle 已被加载)');

// ⚠️ 刻意不声明 Config。
// 实测教训：Config 必须是 z.object({...}) 或 Schema.object({...}) 这类真实 schema 校验器。
// 直接写普通对象字面量会让插件挂载失败 —— apply() 永远不被调用，且无任何报错，
// 表现为「模块已加载但插件不工作」，极难排查（本次就是这么卡住的）。
// 本插件所有配置项都有默认值，所以不声明 Config，改在 apply 内读参数并兜底。
// 将来若需 schema 校验：用 Schema.object（Cordis 自带）或从 zod 导入 z。

const TYPE_MESSAGE = 'message';
const TYPE_REPLY = 'reply';
const RECONNECT_MIN = 1000;
const RECONNECT_MAX = 30000;

// ── 文件传输（协议 §5.3 入站 / §6.3 出站）──
// 出站：本地文件先 POST 上传到网关 open-api（multipart: bot_id/bot_key/session_id/file），
//       再把返回的可访问 url + file_name + media_type 作为 reply 发出，手机端即可下载/预览。
// 入站：消息可能带 url（协议字段）或文本里的文件链接（App 会把文件拼成 markdown 链接），
//       下载到本地后把路径告诉 agent（agent 用 read/read_image 等工具处理）。
const DEFAULT_UPLOAD_URL = 'https://harness.alltman.com/api/open-api/upload-file';
const IMAGE_EXT = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']);
const DOC_EXT = new Set(['txt', 'markdown', 'md', 'pdf', 'html', 'htm', 'xlsx', 'xls', 'doc', 'docx', 'csv']);
const AUDIO_EXT = new Set(['mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'oga', 'opus', 'amr', 'wma', 'aiff', 'mka']);
const VIDEO_EXT = new Set(['mp4', 'mov', 'm4v', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'mpeg', 'mpg', 'ts', '3gp']);
const UPLOAD_ALLOWED_EXT = new Set([...IMAGE_EXT, ...DOC_EXT, ...AUDIO_EXT, ...VIDEO_EXT]);
const UPLOAD_MAX_PLAIN_BYTES = 16 * 1024 * 1024;      // 普通文件上限（协议）
const UPLOAD_MAX_MEDIA_BYTES = 1024 * 1024 * 1024;    // 音视频上限（协议）
const DOWNLOAD_MAX_BYTES = 200 * 1024 * 1024;
const MAX_FILES_PER_ROUND = 4;

export function apply(ctx, config) {
  const CFG = config ?? {};
  // trace 落盘位置：显式配置优先，否则 workspace 下（与 state/inbox 同址；HOME 兜底）
  tracePath = CFG.traceFile ?? join(CFG.workspace ?? process.env.HOME ?? process.env.USERPROFILE ?? process.cwd(), '.harness-mate-trace.log');
  // ⚠️ 教训(实测事故):cordis 的 LoggerService 的 info/warn 方法内部是 `this()[type](...)`,
  // 依赖 this 指向 logger 本身。写成 `(ctx.logger?.info ?? console.log)(...)` 把方法取出来
  // 裸调用会丢 this → 抛 "TypeError: this is not a function" → apply() 直接崩、插件不激活。
  // 正确写法:保持 `ctx.logger.info(...)` 方法调用形式。
  const log = (...a) => {
    trace('LOG ' + a.join(' '));
    if (ctx.logger?.info) { try { ctx.logger.info(...a); return; } catch (e) { trace('ctx.logger.info 调用失败: ' + (e?.message ?? e)); } }
    try { console.log('[HarnessMate]', ...a); } catch { /* 忽略 */ }
  };
  const warn = (...a) => {
    trace('WARN ' + a.join(' '));
    if (ctx.logger?.warn) { try { ctx.logger.warn(...a); return; } catch (e) { trace('ctx.logger.warn 调用失败: ' + (e?.message ?? e)); } }
    try { console.warn('[HarnessMate]', ...a); } catch { /* 忽略 */ }
  };

  trace(`apply() 已执行；配置: gatewayUrl=${CFG.gatewayUrl ?? '(缺)'} botId=${CFG.botId ?? '(缺)'} botKey=${CFG.botKey ? '(有)' : '(缺)'}`);

  // ───────────────────────── 状态 ─────────────────────────
  let ws = null;
  let attempt = 0;
  let pingTimer = null;
  let disposed = false;
  // ⚠️ 教训(实测事故):agents 服务句柄必须缓存在闭包变量里,不能写 `ctx.agents = ...`。
  // cordis 的 context 代理禁止向 ctx 写别的 fiber 已注册的服务名,否则抛
  // "cannot set property \"agents\" in multiple fibers";若发生在异步回调里还会
  // 升级为 fatal load failure(整棵树加载失败)。ctx.get('agents') 随时可取,这里只是做单点缓存。
  let agentsService = null;

  // ★ 会话连续性(原设计"每条消息新建会话"会导致:连续消息没有上下文、聊天记录被切碎)。
  //   同一个「对话线程」(accountId:threadId) 复用同一个 DSH 会话:
  //   live(进程内活跃) → resume(持久化会话恢复,DSH 重启后上下文不丢) → create(首次) 三级回退。
  //   thread → sessionId 的映射持久化到磁盘,重启后仍能找到旧会话。
  const statePath = CFG.stateFile ?? join(CFG.workspace ?? '.', '.harness-mate-state.json');
  let bridgeState = { threads: {} };
  try {
    const parsed = JSON.parse(readFileSync(statePath, 'utf8'));
    if (parsed && typeof parsed === 'object' && parsed.threads && typeof parsed.threads === 'object') bridgeState = parsed;
  } catch { /* 首次运行或文件损坏 → 从空状态开始 */ }
  function saveState() {
    try { writeFileSync(statePath, JSON.stringify(bridgeState, null, 2)); }
    catch (e) { trace('saveState 失败: ' + (e?.message ?? e)); }
  }

  // 同一线程的消息串行处理:快速连发时避免同一 agent 上多轮并发把输出流搅乱
  const threadQueues = new Map();   // key → Promise
  function enqueueThreadTask(key, task) {
    const prev = threadQueues.get(key) ?? Promise.resolve();
    const next = prev.then(task, task).catch(() => {});
    threadQueues.set(key, next);
    return next;
  }

  /**
   * 取一个可用的 agent：优先复用进程内仍活跃的会话，其次恢复持久化的会话
   * （DSH 重启后聊天记录与上下文不丢），最后才新建。
   *
   * 创建/恢复的 setup 必须做两件事（对照 dsh-api-session-controller 的 composeAgent，GUI 同款）：
   *   ① installModelSelection —— 提供 {{model}} 变量与请求路由（否则整轮报错/空回复）；
   *   ② agentPresets.mount —— 给 agent 挂上预设（默认 standard）的插件组合。
   *      不挂预设的 agent 只有 1 个桌面工具（load_workspace_dependencies），
   *      没有 bash/read/write/web/read_image/present 等任何实用工具。
   * preset 选择记入 state，恢复会话时沿用同一个预设。
   */
  async function acquireAgent({ agents, key, cwd }) {
    const defaultModel = ctx.get?.('agentDefaultModel');
    const selection = defaultModel?.currentSelection?.();
    const agentOptions = CFG.agentOptions
      ?? (selection ? { provider: selection.provider, model: selection.model } : undefined);
    const presets = ctx.get?.('agentPresets');

    /** setup：模型选择 + 预设挂载（⚠️ 无返回值，工厂会调用返回值?.commit()） */
    const setupFor = (presetId) => async (agentCtx) => {
      if (selection) installModelSelection(agentCtx, { current: selection, assembled: void 0 });
      if (presets) {
        try { await presets.mount(agentCtx, presetId ?? undefined); }
        catch (e) { warn(`挂载 agent 预设失败（agent 将缺少工具）: ${e?.message ?? e}`); }
      }
    };
    const opts = agentOptions ? { agentOptions } : {};
    const sessionId = bridgeState.threads[key]?.sessionId;

    // 1) 会话在进程内仍然活跃（首选）
    if (sessionId && typeof agents.get === 'function') {
      try {
        const live = agents.get(sessionId);
        if (live && typeof live.followup === 'function') return { agent: live, sessionId, mode: 'live' };
      } catch (e) { trace('agents.get 查询失败: ' + (e?.message ?? e)); }
    }

    // 2) 恢复持久化会话（DSH 重启后继续接上旧会话）
    if (sessionId) {
      try {
        const resumed = await agents.resume({
          resumeSessionId: sessionId,
          ...opts,
          setup: setupFor(bridgeState.threads[key]?.presetId),
        });
        const agent = resumed?.agent ?? resumed;
        if (agent && typeof agent.followup === 'function') {
          log(`恢复会话 ${sessionId}（线程 ${key}）`);
          return { agent, sessionId, mode: 'resumed' };
        }
      } catch (e) {
        warn(`恢复会话 ${sessionId} 失败，将新建: ${e?.message ?? e}`);
      }
    }

    // 3) 新建会话
    let presetId;
    if (presets) {
      try { presetId = (await presets.resolve(CFG.presetId ?? undefined)).id; }
      catch (e) { warn(`解析 agent 预设失败: ${e?.message ?? e}`); }
    }
    const newId = `session-${cryptoRandomId()}`;
    const created = await agents.create({
      sessionId: newId,
      meta: { cwd, ...(presetId ? { agentPreset: presetId } : {}) },
      ...opts,
      setup: setupFor(presetId),
    });
    const agent = created?.agent ?? created;
    if (!agent || typeof agent.followup !== 'function') {
      throw new Error('agents.create 未返回可用的 agent（无 followup 方法）');
    }
    bridgeState.threads[key] = { sessionId: newId, presetId, updatedAt: Date.now() };
    saveState();
    log(`新建会话 ${newId}（线程 ${key}${presetId ? `, 预设 ${presetId}` : ''}）`);
    return { agent, sessionId: newId, mode: 'created' };
  }

  // ───────────────────────── 文件传输（入站下载 / 出站上传）─────────────────────────
  const fileExtOf = (name) => {
    const n = String(name || '').split(/[\\/]/).pop() ?? '';
    const i = n.lastIndexOf('.');
    return i > 0 ? n.slice(i + 1).toLowerCase() : '';
  };
  const mediaKindFor = (name) => {
    const ext = fileExtOf(name);
    if (IMAGE_EXT.has(ext)) return 'image';
    if (VIDEO_EXT.has(ext)) return 'video';
    if (AUDIO_EXT.has(ext)) return 'audio';
    return 'file';
  };
  const safeFileName = (name) => {
    let n = String(name || '').split(/[\\/]/).pop().replace(/[\u0000-\u001f]/g, '').trim().slice(0, 120);
    if (process.platform === 'win32') n = n.replace(/[<>:"|?*]/g, '_');   // Windows 文件名非法字符
    return n || 'file.bin';
  };
  /** 下载/本地文件名的展示形态（去掉入站下载时加的时间戳前缀） */
  const cleanLocalName = (localPath) => safeFileName(basename(localPath).replace(/^\d{13}-/, ''));

  function inboxDir() {
    const dir = CFG.inboxDir ?? join(CFG.workspace ?? process.cwd(), '.harness-mate-inbox');
    mkdirSync(dir, { recursive: true });
    return dir;
  }

  /** 下载一个文件到收件目录，返回本地绝对路径 */
  async function downloadToInbox(url, nameHint) {
    const res = await fetch(url, { signal: AbortSignal.timeout(120000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = Buffer.from(await res.arrayBuffer());
    if (buf.length === 0) throw new Error('文件内容为空');
    if (buf.length > DOWNLOAD_MAX_BYTES) throw new Error(`文件过大（${(buf.length / 1048576).toFixed(1)}MB > 200MB）`);
    let name = safeFileName(nameHint || '');
    if (name === 'file.bin') {
      try { name = safeFileName(decodeURIComponent(new URL(url).pathname.split('/').pop() || '')); } catch { /* 保持默认名 */ }
    }
    const local = join(inboxDir(), `${Date.now()}-${name}`);
    writeFileSync(local, buf);
    trace(`已下载入站文件 → ${local}（${buf.length} bytes）`);
    return local;
  }

  /** 消息文本里可能带文件链接（App 会把上传的文件拼成 markdown 链接），下载后把本地路径替换进去 */
  const MD_LINK_RE = /!?\[([^\]]*)\]\(\s*<?([^)\s<>]+)>?\s*\)/g;
  function isOurFileHost(url) {
    const pattern = CFG.fileHostPattern ?? 'myqcloud\\.com|alltman\\.com';
    try { return new RegExp(pattern, 'i').test(new URL(url).host); } catch { return false; }
  }
  async function inlineInboundFiles(text, inboundFile) {
    let out = text;
    const jobs = [];
    const protoUrl = String(inboundFile?.url ?? '').trim();
    if (protoUrl) jobs.push({ url: protoUrl, name: inboundFile?.name ?? '' });
    for (const m of String(text ?? '').matchAll(MD_LINK_RE)) {
      const url = m[2];
      if (!/^https?:\/\//i.test(url)) continue;      // 只处理上传回来的文件链接
      if (!isOurFileHost(url)) continue;             // 普通网页链接不下载
      jobs.push({ url, name: m[1] || '' });
    }
    if (!jobs.length) return out;
    const seen = new Set();
    for (const job of jobs) {
      if (seen.has(job.url)) continue;
      seen.add(job.url);
      try {
        const local = await downloadToInbox(job.url, job.name);
        const display = cleanLocalName(local);
        // 文本里的链接 → 替换为本地路径（agent 可直接按路径读取）
        if (out.includes(job.url)) {
          out = out.split(`(${job.url})`).join(`(${local})`).split(`(<${job.url}>)`).join(`(${local})`);
        }
        out += `\n\n（用户通过手机发来了文件「${display}」，已下载到本地：${local}）`;
      } catch (e) {
        warn(`下载入站文件失败 ${job.url}: ${e?.message ?? e}`);
        out += `\n\n（用户通过手机发来了一个文件，但下载失败：${e?.message ?? e}）`;
      }
    }
    return out;
  }

  /** 上传本地文件到网关 open-api（免授权接口，协议 §6.3），返回可访问 url */
  async function uploadToGateway(filePath, peer) {
    const name = cleanLocalName(filePath);
    const ext = fileExtOf(name);
    if (!UPLOAD_ALLOWED_EXT.has(ext)) throw new Error(`扩展名 .${ext || '(无)'} 不在网关允许列表`);
    const buf = readFileSync(filePath);
    if (buf.length === 0) throw new Error('文件为空');
    const limit = (AUDIO_EXT.has(ext) || VIDEO_EXT.has(ext)) ? UPLOAD_MAX_MEDIA_BYTES : UPLOAD_MAX_PLAIN_BYTES;
    if (buf.length > limit) throw new Error(`超过大小上限（${(buf.length / 1048576).toFixed(1)}MB）`);
    const form = new FormData();
    form.append('bot_id', String(CFG.botId ?? ''));
    form.append('bot_key', String(CFG.botKey ?? ''));
    form.append('session_id', String(peer ?? ''));       // 协议：上传 session_id 用当前对端 ws_session_id
    form.append('file', new Blob([buf]), name);
    const res = await fetch(CFG.uploadUrl ?? DEFAULT_UPLOAD_URL, {
      method: 'POST',
      body: form,
      signal: AbortSignal.timeout(180000),
    });
    const raw = await res.text();
    let parsed;
    try { parsed = JSON.parse(raw); } catch { throw new Error(`上传接口返回非 JSON：${raw.slice(0, 120)}`); }
    if (String(parsed?.code) !== 'success') throw new Error(parsed?.message || '上传失败');
    const url = parsed?.data?.url;
    if (!url) throw new Error('上传成功但未返回 url');
    return url;
  }

  /**
   * 每轮结束后把本轮的交付文件发给手机：
   *   ① session 事件里的 deliverables/presented（present 工具显式声明的交付物，主通道）；
   *   ② 回复文本里指向本地文件的 markdown 链接（兜底，仅收录本轮新写入/修改的文件）。
   */
  async function deliverRoundFiles({ agent, peer, threadId, startSeq, roundStartMs, roundText }) {
    try {
      const cwd = agent.session?.header?.cwd ?? CFG.workspace ?? process.cwd();
      const found = new Map();   // absPath → { description, explicit }
      const addFile = (p, description, explicit) => {
        if (!p || typeof p !== 'string' || !p.trim()) return;
        const abs = isAbsolute(p) ? p : join(cwd, p);
        const prev = found.get(abs);
        if (!prev) { found.set(abs, { description: description || '', explicit }); return; }
        if (explicit && !prev.explicit) found.set(abs, { description: description || prev.description || '', explicit: true });
      };

      // ① present 事件（本轮新增）
      try {
        const events = agent.session?.snapshotEvents?.(startSeq) ?? [];
        for (const ev of events) {
          if (ev?.type !== 'deliverables/presented') continue;
          for (const f of ev.data?.files ?? []) addFile(f?.path, f?.description, true);
        }
      } catch (e) { trace('读取 session 事件失败: ' + (e?.message ?? e)); }

      // ② 文本里的本地文件链接
      if (roundText) {
        for (const m of roundText.matchAll(MD_LINK_RE)) {
          const target = m[2];
          if (/^https?:\/\//i.test(target)) continue;
          let t = target;
          try { t = decodeURIComponent(target); } catch { /* 保留原样 */ }
          t = t.replace(/^<|>$/g, '').replace(/#L\d+(-L\d+)?$/, '').replace(/:\d+(-\d+)?$/, '');
          if (!/\.[a-z0-9]{1,8}$/i.test(t)) continue;
          addFile(t, m[1] || '', false);
        }
      }

      if (!found.size) return;
      let sent = 0;
      for (const [abs, meta] of found) {
        if (sent >= MAX_FILES_PER_ROUND) { trace(`本轮文件超过 ${MAX_FILES_PER_ROUND} 个，其余跳过`); break; }
        try {
          const st = statSync(abs, { throwIfNoEntry: false });
          if (!st?.isFile()) continue;
          if (!meta.explicit && st.mtimeMs < roundStartMs - 1000) continue;   // 兜底通道只发本轮新文件
          const url = await uploadToGateway(abs, peer);
          const name = cleanLocalName(abs);
          sendReply(peer, threadId, {
            text: meta.description || '',
            message_id: cryptoRandomId(),
            url,
            file_name: name,
            media_type: mediaKindFor(name),
            delta: true,
            done: true,
          });
          sent++;
          log(`已发送文件到手机：${name}`);
          trace(`出站文件 ${abs} → ${url}`);
        } catch (e) {
          warn(`发送文件失败 ${abs}: ${e?.message ?? e}`);
        }
      }
    } catch (e) {
      trace('deliverRoundFiles 异常: ' + (e?.message ?? e));
    }
  }

  /** ws_session_id(peer) → 该 peer 最近的业务身份，用于回信路由（§7.1） */
  const replyTargets = new Map();   // `${accountId}:${threadId}` → peerSession
  const peerByDevice = new Map();   // from_device → peerSession
  let lastPeer = '';

  /** 去重（§9.2：重复 msg_id 忽略） */
  const seen = new Set();

  /** agent → 当前这一轮的回复上下文 */
  const ownedAgents = new Map();    // agent → { peerSession, accountId, threadId, messageId, mux }
  /** approvalId → resolver */
  const approvals = new Map();
  let approvalSeq = 1;

  /**
   * 等待用户回答的 agent 提问（ask_user_question）：
   *   threadKey → { callId, questions, finish(answers), cancel(reason), timer }
   * 提问到达时（waterfall 拦截）推送手机；用户在等待期内回复即作为答案注入；
   * 超时后抛 ASK_TIMED_OUT 形态错误 → 工具返回 pending，agent 继续（官方语义：
   * "the user can still answer"，后续普通消息 agent 会自行按上下文理解）。
   */
  const openQuestions = new Map();

  // ───────────────────────── JWT（§3.3）─────────────────────────
  function buildToken() {
    const now = Math.floor(Date.now() / 1000);
    const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
    const head = b64({ alg: 'HS256', typ: 'JWT' });
    const body = b64({ ws_session_id: CFG.botId, iat: now, exp: now + 86400 * 30 });
    const sig = createHmac('sha256', CFG.botKey).update(`${head}.${body}`).digest('base64url');
    return `${head}.${body}.${sig}`;
  }

  // ───────────────────────── 发送 ─────────────────────────
  function sendEnvelope(to, data) {
    if (!ws || ws.readyState !== 1) { warn('网关未连接，丢弃:', data?.type); return false; }
    ws.send(JSON.stringify({ to, data }));   // 信封只有 to + data（§4.1）
    return true;
  }

  /** 发 reply（§6） */
  function sendReply(peer, threadId, payload) {
    return sendEnvelope(peer, {
      type: TYPE_REPLY,
      account_id: CFG.accountId,
      thread_id: threadId ?? '',
      data: payload,
    });
  }

  // ───────────────────────── 流式分片 ─────────────────────────
  /**
   * 协议 §6.3：message_id 流式多帧共用；delta=true 为增量，done=true 为最终帧。
   * 这里累积全文 —— adapter.py 的 edit_message 语义是"当前累计正文"，
   * 所以每帧发累计文本，最后一帧 done=true。
   */
  function makeStream(peer, threadId, messageId) {
    let acc = '';
    let timer = null;
    let finished = false;

    const flush = (final = false) => {
      if (timer) { clearTimeout(timer); timer = null; }
      if (finished) return;
      if (!acc && !final) return;
      const text = acc.slice(0, CFG.maxReplyChars ?? 4000);
      const trimmed = final && text.length > (CFG.maxReplyChars ?? 4000)
        ? text.slice(0, CFG.maxReplyChars) + '…（已截断）'
        : text;
      sendReply(peer, threadId, {
        text: trimmed,
        message_id: messageId,
        delta: true,
        ...(final ? { done: true } : {}),
      });
      if (final) finished = true;
    };

    return {
      push(t) {
        if (finished) return;
        acc += t;
        if (acc.length >= (CFG.flushChars ?? 1200)) return flush(false);
        if (!timer) timer = setTimeout(() => flush(false), CFG.flushIntervalMs ?? 700);
      },
      /** 立即冲刷当前累积文本（非最终帧） */
      flush() { flush(false); },
      /** 发送最终帧 done=true */
      finish() { flush(true); },
      /** 本轮累计的完整文本（出站文件解析用） */
      getText: () => acc,
    };
  }

  const typingLast = new Map();   // `${peer}:${threadId}` → ts
  function sendTyping(peer, threadId) {
    const key = `${peer}:${threadId}`;
    const now = Date.now();
    if (now - (typingLast.get(key) ?? 0) < (CFG.typingThrottleMs ?? 8000)) return;
    typingLast.set(key, now);
    sendReply(peer, threadId, { status: 'thinking', text: '思考中...' });
  }

  // ───────────────────────── 访问控制（§3.1）─────────────────────────
  function peerAllowed(peer) {
    if (CFG.dmPolicy === 'disabled') return false;
    if (CFG.dmPolicy === 'open') return true;
    const list = (CFG.allowFrom ?? []).map((s) => String(s).toLowerCase());
    if (!list.length) return CFG.dmPolicy !== 'allowlist';
    return list.includes('*') || list.includes(String(peer).toLowerCase());
  }

  // ───────────────────────── 回复路由（§7）─────────────────────────
  function resolveTarget(accountId, threadId) {
    return (
      replyTargets.get(`${accountId}:${threadId}`)
      ?? [...replyTargets.entries()].find(([k]) => k.startsWith(`${accountId}:`))?.[1]
      ?? lastPeer
      ?? ''
    );
  }

  // ───────────────────────── ① 订阅输出 ─────────────────────────
  ctx.on('agent/assistant-stream', ({ agent, frame }) => {
    const round = ownedAgents.get(agent);
    if (!round) return;                                  // 不是本插件发起的会话 → 放行

    if (frame.type === 'start' || frame.type === 'end') { round.stream?.flush?.(); return; }

    const chunk = frame.chunk;
    if (!chunk) return;
    switch (chunk.type) {
      case 'text-delta':                                 // ★ 正文
        round.stream.push(chunk.text ?? '');
        return;
      case 'reasoning-delta':                            // 推理：默认不发（协议支持 reasoning 字段）
        if (CFG.forwardReasoning) round.stream.push(chunk.text ?? '');
        return;
      case 'block-start':
      case 'block-end':
        return;
      case 'tool-call-delta':
        return;
      case 'usage':
      case 'finish':
        return;
      default:
        return;                                          // 闭集合兜底
    }
  });

  // ───────────────────────── ② 拦截提问（ask_user_question → 手机）─────────────────────────
  //
  // dsh-tool-ask-user 的工具实现：agent 调 ask_user_question → 走 scope-filtered waterfall
  // "user-questions/request"（default 120 秒前台等待；无 UI 认领时本应永久挂起或等超时）。
  // 桌面 GUI 的转发器（dsh-api-remotes）注册在树加载期，且"有 Client 认领但无人操作"时会
  // 一直挂着——所以这里用 { prepend: true } 抢先接住：只要是本插件发起的会话，
  // 就由插件接管：推送手机 → 等用户回答 → resolve；超时 → 抛 ASK_TIMED_OUT → agent 转 pending 继续。
  // （代价：该问题不再出现在桌面 GUI 的问题卡片里——手机是主交互面，接受。）
  //
  // 返回值契约：resolve({ answers: [{ id, selected: [...], custom? }] })（见工具内 answerResult）。
  /** 把一批问题渲染成给手机看的文本 */
  function formatQuestionsForUser(questions) {
    const lines = ['❓ Agent 想请你确认（直接回复本条消息即可作答）：'];
    questions.forEach((q, qi) => {
      if (q.header) lines.push('', questions.length > 1 ? `【问题 ${qi + 1}/${questions.length}・${q.header}】` : `【${q.header}】`);
      else if (questions.length > 1) lines.push('', `【问题 ${qi + 1}/${questions.length}】`);
      else lines.push('');
      lines.push(q.question);
      for (const [oi, opt] of (q.options ?? []).entries()) {
        lines.push(`${oi + 1}. ${opt.label}${opt.description ? ` —— ${opt.description}` : ''}`);
      }
    });
    if (questions.length > 1) lines.push('', '（多个问题请按顺序分行回复，一行一个答案）');
    else if ((questions[0]?.options ?? []).length) lines.push('', '（回复选项序号，或直接输入你的回答）');
    return lines.join('\n');
  }
  /** 单个问题：文本 → { selected, custom }（数字序号/选项名 → 选中；其余 → 自定义回答） */
  function parseOneAnswer(question, text) {
    const t = String(text ?? '').trim();
    const options = question.options ?? [];
    const m = t.match(/^\d+$/);
    if (m && options.length) {
      const idx = Number(t) - 1;
      if (idx >= 0 && idx < options.length) return { selected: [options[idx].label] };
    }
    const norm = (s) => String(s ?? '').replace(/\s+/g, '').toLowerCase();
    const hit = options.find((o) => norm(o.label) === norm(t));
    if (hit) return { selected: [hit.label] };
    return { selected: [], custom: t };
  }
  /** 整段文本 → 答案批次（多问题按行对应；行数不匹配时缺的行按跳过处理） */
  function parseAnswerBatch(questions, text) {
    if (questions.length === 1) {
      return { answers: [{ id: questions[0].id, ...parseOneAnswer(questions[0], text) }] };
    }
    const lines = String(text ?? '').split(/\n+/).map((s) => s.trim()).filter((s) => s.length > 0);
    return { answers: questions.map((q, i) => ({ id: q.id, ...parseOneAnswer(q, lines[i] ?? '') })) };
  }
  ctx.on('user-questions/request', (request, next) => {
    const agent = request?.agent;
    const round = agent ? ownedAgents.get(agent) : undefined;
    if (!round) return next();                          // 不是本插件的会话 → 交给下游（桌面 GUI 等）
    const key = `${round.accountId}:${round.threadId}`;
    if (openQuestions.has(key)) { trace('同一会话已有等待中的问题，放行给下游'); return next(); }

    const questions = request.questions ?? [];
    const callId = request.wait?.callId ?? request.callId ?? null;
    const text = formatQuestionsForUser(questions);
    log(`收到 agent 提问（${questions.length} 个问题），推送到手机等待回答…`);
    trace('提问推送: ' + JSON.stringify(questions).slice(0, 400));
    sendReply(round.peerSession, round.threadId, {
      text,
      message_id: cryptoRandomId(),
      // 自定义载荷：手机 App 认识时可渲染成问题卡片，不认识则忽略（文本里已有全部信息）
      question: { call_id: callId, questions },
      delta: true,
      done: true,
    });

    return new Promise((resolve, reject) => {
      // 超时/取消不自己造：官方 TimedQuestionWait 在"无 Client 认领"时自带 deadline 定时器
      // （deadline = 工具的 timeout 参数，默认 120s），到点 close() 并 abort request.signal，
      // reason 即官方构造的 UserQuestionError(ASK_TIMED_OUT)。官方 answerer 的职责 =
      // 监听 signal、把 abort 转成 reject(signal.reason)：经 ask() → askTimed 的
      // `if (wait.signal.aborted) throw wait.signal.reason` → 命中 ASK_TIMED_OUT →
      // 工具返回 { pending: true }（agent 继续，用户之后仍可回答）。turn 被取消时同理透传。
      const signal = request.signal;
      let settled = false;
      const onAbort = () => {
        if (settled) return;
        settled = true;
        openQuestions.delete(key);
        warn(`提问等待被中断（${signal?.reason?.code ?? signal?.reason?.name ?? 'abort'}），透传官方机制`);
        reject(signal?.reason);                      // 官方 ASK_TIMED_OUT 真类 / 取消原因，原样透传
      };
      openQuestions.set(key, {
        callId,
        questions,
        finish(batch) {
          settled = true;
          signal?.removeEventListener('abort', onAbort);
          openQuestions.delete(key);
          resolve(batch);                            // batch 已是 { answers: [...] }（answerResult 直接取 .answers）
        },
      });
      if (signal?.aborted) onAbort();
      else signal?.addEventListener('abort', onAbort, { once: true });
    });
  }, { prepend: true });

  // ───────────────────────── ③ 拦截审批 ─────────────────────────
  ctx.on('approval/request', (request, next) => {
    const agent = request?.agent;
    const round = agent ? ownedAgents.get(agent) : undefined;
    if (!round) return next();                           // 非本插件会话 → 交给下游（GUI 弹窗）

    const approvalId = `a-${approvalSeq++}`;
    const title = request.title ?? request.toolName ?? request.callId ?? '需要授权的操作';
    log(`审批 ${approvalId}: ${title}`);

    round.stream.push(`\n⚠️ 需要授权：${title}\n`);

    // 用 reply 协议推给 App（status 之外的自定义载荷，客户端可识别 approval 字段）
    sendReply(round.peerSession, round.threadId, {
      text: `需要授权：${title}`,
      message_id: round.messageId,
      approval: {
        approval_id: approvalId,
        title,
        options: [
          { option_id: 'allow-once', kind: 'allow_once', name: '允许一次' },
          { option_id: 'reject-once', kind: 'reject_once', name: '拒绝' },
        ],
        expires_in_ms: CFG.approvalTimeoutMs ?? 300000,
      },
    });

    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        approvals.delete(approvalId);
        warn(`审批 ${approvalId} 超时 → 拒绝`);
        resolve('rejected');
      }, CFG.approvalTimeoutMs ?? 300000);
      approvals.set(approvalId, (decision) => {
        clearTimeout(timer);
        approvals.delete(approvalId);
        log(`审批 ${approvalId} → ${decision}`);
        // 合法决策只有三个：allowed-once / rejected / cancelled（源码核对过，没有 allowed-always）
        resolve(decision === 'approve' ? 'allowed-once' : 'rejected');
      });
    });
  });

  // ───────────────────────── ③ 连网关 ─────────────────────────
  function connect() {
    if (disposed) return;
    const url = `${CFG.gatewayUrl}${CFG.gatewayUrl.includes('?') ? '&' : '?'}token=${encodeURIComponent(buildToken())}`;
    log('连接网关', CFG.gatewayUrl.replace(/\/\/[^@]*@/, '//'));

    trace(`WebSocket 构造前: typeof WebSocket=${typeof WebSocket}`);
    try {
      ws = new WebSocket(url);
    } catch (e) {
      trace('WebSocket 构造抛错: ' + e?.message);
      warn('WebSocket 构造失败:', e?.message);
      return;
    }
    trace(`WebSocket 已构造: readyState=${ws.readyState} (0=CONNECTING,1=OPEN)`);

    // 状态轮询：若一直停在 CONNECTING，说明握手没完成（网络/代理/证书）
    let polls = 0;
    const poll = setInterval(() => {
      polls++;
      if (!ws || ws.readyState !== 0) { clearInterval(poll); return; }
      trace(`握手仍挂起 ${polls * 2}s (readyState=0)`);
      if (polls >= 15) { clearInterval(poll); trace('握手超时 30s，放弃本次'); try { ws.close(); } catch {} }
    }, 2000);

    ws.onopen = () => {
      attempt = 0;
      log(`已连接网关 bot_id=${CFG.botId}`);
      trace('WS onopen —— 网关握手成功');
      // 协议 §10：客户端 ping 间隔 50s
      pingTimer = setInterval(() => {
        if (ws?.readyState === 1) { try { ws.send(JSON.stringify({ type: 'ping' })); } catch {} }
      }, 50000);
    };

    ws.onmessage = (e) => {
      trace('WS 收到原始帧: ' + String(e.data).slice(0, 300));
      let raw; try { raw = JSON.parse(e.data); } catch { return warn('网关发来非 JSON'); }
      void onGatewayMessage(raw);
    };

    ws.onclose = (ev) => {
      trace(`WS onclose code=${ev?.code} reason=${ev?.reason || '(空)'}`);
      if (pingTimer) { clearInterval(pingTimer); pingTimer = null; }
      if (disposed) return;
      const delay = Math.min(RECONNECT_MAX, RECONNECT_MIN * 2 ** attempt) * (0.5 + Math.random() / 2);
      attempt++;
      warn(`网关断开 code=${ev?.code}，${Math.round(delay)}ms 后重连`);
      setTimeout(connect, delay);
    };
    ws.onerror = () => { trace('WS onerror'); warn('网关连接错误'); };
  }

  // ───────────────────────── 入站处理 ─────────────────────────
  async function onGatewayMessage(raw) {
    const from = String(raw?.from ?? '').trim();
    trace('入站: from=' + JSON.stringify(raw?.from) + ' dataType=' + JSON.stringify(raw?.data?.type));
    if (!from) { trace('丢弃: 缺 from'); return; }          // §9.2：缺 from 忽略
    const data = typeof raw.data === 'string' ? safeJson(raw.data) : (raw.data ?? {});
    if (data.type !== TYPE_MESSAGE) { trace('丢弃: type 不是 message，实际=' + data.type); return; }  // §9.2

    const nested = typeof data.data === 'string' ? safeJson(data.data) : (data.data ?? {});
    const text = String(nested.text ?? data.text ?? '').trim();
    // 文件消息：协议字段 url/file_name（App 也可能把文件拼进文本的 markdown 链接）
    const inboundFile = {
      url: String(nested.url ?? nested.file_url ?? data.url ?? '').trim(),
      name: String(nested.file_name ?? nested.name ?? '').trim(),
    };
    if (!text && !inboundFile.url) { trace('丢弃: 无文本内容'); return; }   // §9.2：无文本且无文件时忽略

    const msgId = String(data.msg_id ?? nested.message_id ?? nested.msg_id ?? '').trim();
    if (msgId) {
      if (seen.has(msgId)) return;                       // §9.2：重复忽略
      seen.add(msgId);
      if (seen.size > 1000) seen.delete(seen.values().next().value);
    }

    if (!peerAllowed(from)) { trace('丢弃: 对端未授权 ' + from); log(`对端未授权，忽略: ${from}`); return; }

    const accountId = String(data.account_id ?? CFG.accountId);
    const threadId = String(data.thread_id ?? '');
    const deviceId = String(data.from_device ?? data.device_id ?? from);

    // §7：记录回复目标
    replyTargets.set(`${accountId}:${threadId}`, from);
    peerByDevice.set(deviceId, from);
    lastPeer = from;

    log(`收到消息 peer=${from} thread=${threadId}: ${JSON.stringify(text.slice(0, 60))}${inboundFile.url ? ' [含文件]' : ''}`);

    // ★ 若该会话有等待中的提问（ask_user_question），本条文本消息优先作为回答注入（不进对话队列，
    //   避免与"挂起等待回答中的轮次"在串行队列中相互死锁）。
    const openQ = openQuestions.get(`${accountId}:${threadId}`);
    if (openQ && text) {
      const answers = parseAnswerBatch(openQ.questions, text);
      log(`检测到等待中的提问 → 本条消息作为回答注入: ${JSON.stringify(answers).slice(0, 200)}`);
      trace('回答注入: ' + JSON.stringify(answers));
      openQ.finish(answers);
      return;                                          // 已消费
    }

    // 同一线程串行处理（快速连发时保持顺序与上下文）；不阻塞 WS 消息循环
    void enqueueThreadTask(`${accountId}:${threadId}`, () => handlePrompt({ peer: from, accountId, threadId, text, inboundFile }));
  }

  /**
   * 把 prompt 交给 agent。
   *
   * 接线依据：dsh-headless/lib/index.js:316-336 的官方写法（已核对源码）：
   *   const { agent } = await agents.create({ sessionId, meta: { cwd }, agentOptions, setup });
   *   await agent.whenIdle();
   *   agent.followup(createUserMessage({ content: [{ type: 'text', text }], source: { kind: 'user' } }));
   *   await agent.whenIdle();
   *
   * createUserMessage 只是 createMessage({...input, role:'user'})，而 createMessage 做的是
   *   deepFreeze(structuredClone({ ...input, id: randomUUID() }))
   * 所以本插件直接构造等价对象，不 import 内部包（保持零依赖）。
   */
  async function handlePrompt({ peer, accountId, threadId, text, inboundFile }) {
    const messageId = cryptoRandomId();
    const stream = makeStream(peer, threadId, messageId);
    sendTyping(peer, threadId);

    // ★ 入站文件：协议字段 url 或 App 拼进文本的文件链接 → 下载到本地，路径交给 agent
    let agentText = text;
    try { agentText = await inlineInboundFiles(text, inboundFile); }
    catch (e) { warn('处理入站文件失败: ' + (e?.message ?? e)); }

    let round = null;
    try {
      // 优先用就绪门控拿到的实例；若还没就绪则现场再试一次
      let agents = agentsService;
      if (!agents) { try { agents = ctx.get?.('agents'); } catch { agents = undefined; } }
      if (typeof agents?.create !== 'function') {
        throw new Error('agents 服务尚未就绪（插件的服务门控还没完成）');
      }

      const cwd = CFG.workspace ?? process.cwd();

      // 会话获取（含 agentOptions/setup/preset 挂载，详见 acquireAgent）
      const key = `${accountId}:${threadId}`;
      const { agent, sessionId, mode } = await acquireAgent({ agents, key, cwd });
      trace(`线程 ${key} → 会话 ${sessionId}（${mode}）`);

      round = { peerSession: peer, accountId, threadId, messageId, stream, agent };
      ownedAgents.set(agent, round);                // ★ 让 assistant-stream / approval 认得出这是我们的会话

      await agent.whenIdle?.();

      // 构造用户消息（等价于 createUserMessage）
      const message = Object.freeze({
        id: cryptoRandomId(),
        role: 'user',
        content: Object.freeze([{ type: 'text', text: agentText }]),
        source: Object.freeze({ kind: 'user' }),
      });

      const startSeq = agent.session?.seq ?? 0;     // 本轮事件起点（出站文件收集用）
      const roundStartMs = Date.now();
      agent.followup(message);                      // ★ 就是这一步：投递并触发一轮
      log(`已投递 prompt 给 agent，等待完成…`);

      await agent.whenIdle?.();                     // 等本轮结束
      stream.finish();
      // ★ 把本轮的交付文件发给手机（present 事件 + 文本链接），失败不影响主流程
      await deliverRoundFiles({ agent, peer, threadId, startSeq, roundStartMs, roundText: stream.getText() });
      // 立即把会话刷盘，保证聊天记录可靠落盘（headless 同款做法）
      try { await ctx.get?.('sessions')?.flush?.(agent.session); } catch (e) { trace('sessions.flush 失败: ' + (e?.message ?? e)); }
      log(`本轮完成 peer=${peer} thread=${threadId}`);
    } catch (err) {
      warn('处理 prompt 失败:', err?.message);
      stream.finish();
      sendReply(peer, threadId, {
        text: `[DSH 插件错误] ${err?.message ?? err}`,
        message_id: messageId,
        delta: true,
        done: true,
      });
    } finally {
      if (round?.agent && ownedAgents.get(round.agent) === round) ownedAgents.delete(round.agent);
    }
  }

  const safeJson = (s) => { try { const v = JSON.parse(s); return v && typeof v === 'object' ? v : {}; } catch { return {}; } };
  const cryptoRandomId = () => globalThis.crypto?.randomUUID?.() ?? `m-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  // ───────────────────────── 启动 / 清理 ─────────────────────────
  //
  // 实测：`agents` 服务在插件加载后需等一会儿才激活（探针显示 +500ms）。
  // 因此这里不阻塞 apply()，而是轮询等待服务就绪后再初始化。
  function waitForService(name, timeoutMs = 30000) {
    return new Promise((resolve) => {
      const t0 = Date.now();
      const tick = () => {
        if (disposed) return resolve(null);
        let svc;
        try { svc = ctx.get?.(name); } catch { svc = undefined; }
        if (svc) { trace(`服务 ${name} 已就绪（等待 ${Date.now() - t0}ms）`); return resolve(svc); }
        if (Date.now() - t0 > timeoutMs) { warn(`等待服务 ${name} 超时（${timeoutMs}ms）`); return resolve(null); }
        setTimeout(tick, 200);
      };
      tick();
    });
  }

  if (!CFG.gatewayUrl || !CFG.botId || !CFG.botKey) {
    warn('缺少配置：gatewayUrl / botId / botKey 三者必填，插件不会连接');
  } else {
    // 先连网关（不依赖 DSH 服务），再做服务就绪门控
    connect();
    log('插件已加载，正在等待 agents 服务就绪…');

    void waitForService('agents').then((agents) => {
      if (!agents) { warn('agents 服务始终未就绪，收消息后将无法调用 agent'); return; }
      agentsService = agents;                  // 供 handlePrompt 使用（闭包变量，勿写 ctx.agents）
      log('agents 服务已就绪，插件完全可用');
      trace('初始化完成：网关已连 + agents 服务已就绪');
    });
  }

  ctx.on('dispose', () => {
    disposed = true;
    if (pingTimer) clearInterval(pingTimer);
    try { ws?.close(); } catch {}
  });
}
