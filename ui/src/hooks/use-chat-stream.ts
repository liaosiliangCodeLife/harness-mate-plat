/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //整页共用一条 SSE，承接该账号全部会话的下行帧，并用现有请求封装发送消息
 * @File: use-chat-stream.ts
 * @Time: 2026/10/24 00:07:48
 * @All Rights Reserve By Brtc
 */
import { ref, type Ref } from 'vue'
import { apiPrefix } from '@/config'
import type { HermesInboundFrame, HermesReplyData } from '@/models/hermes-channel'
import { useCredentialStore } from '@/stores/credential'

// 整页共用的连接状态。重连等待期间是 disconnected，开始拨号后是 connecting
export type ChatStreamStatus = 'connected' | 'connecting' | 'disconnected'

// 出错后先关掉旧连接，再过这么久重新打开
const RECONNECT_DELAY_MS = 3000

type StreamHandler = (payload: HermesReplyData) => void

export const status: Ref<ChatStreamStatus> = ref('disconnected')

const subscribers = new Map<string, Set<StreamHandler>>()
let source: EventSource | null = null
let retryTimer: number | null = null
// 每次 start / stop 加一，用来丢掉过期连接上的回调和已安排的重连
let generation = 0

/*
 * @Author Leon-liao
 * @Function: readAccessToken()
 * @Description //读取登录 access_token。凭证存在 localStorage 的 credential 里，和请求拦截器读的是同一份
 * @Date :2026/10/24 00:07:48
 * @Param: 无
 * @return：access_token 字符串；未登录或字段不是字符串时为空字符串
 */
const readAccessToken = (): string => {
  const { credential } = useCredentialStore()
  const token = credential.access_token
  return typeof token === 'string' ? token : ''
}

/*
 * @Author Leon-liao
 * @Function: clearRetryTimer()
 * @Description //取消已经安排、尚未执行的重连
 * @Date :2026/10/24 00:07:48
 * @Param: 无
 * @return：无
 */
const clearRetryTimer = (): void => {
  if (retryTimer === null) {
    return
  }
  window.clearTimeout(retryTimer)
  retryTimer = null
}

/*
 * @Author Leon-liao
 * @Function: closeSource()
 * @Description //关掉当前 EventSource，并先卸掉回调，避免 close 再次触发 onerror
 * @Date :2026/10/24 00:07:48
 * @Param: 无
 * @return：无
 */
const closeSource = (): void => {
  const current = source
  source = null
  if (!current) {
    return
  }
  current.onopen = null
  current.onmessage = null
  current.onerror = null
  current.close()
}

/*
 * @Author Leon-liao
 * @Function: deliverFrame(raw: string)
 * @Description //解析网关帧，只把 type 为 reply 的内层 payload 交给对应会话的订阅者
 * @Date :2026/10/24 00:07:48
 * @Param: raw: SSE 的 data 文本，字符串，内容是两层 data 的网关帧 JSON
 * @return：无。解析失败、不是 reply、或没有订阅者时直接返回
 */
const deliverFrame = (raw: string): void => {
  let frame: HermesInboundFrame
  try {
    frame = JSON.parse(raw) as HermesInboundFrame
  } catch {
    return
  }
  const envelope = frame.data
  if (!envelope || envelope.type !== 'reply') {
    return
  }
  const accountId = envelope.account_id
  const threadId = envelope.thread_id
  if (!accountId || !threadId) {
    return
  }
  const handlers = subscribers.get(`${accountId}:${threadId}`)
  if (!handlers || handlers.size === 0) {
    return
  }
  const payload = envelope.data ?? {}
  handlers.forEach((handler) => {
    handler(payload)
  })
}

/*
 * @Author Leon-liao
 * @Function: scheduleReconnect(ticket: number)
 * @Description //3 秒后重新打开 SSE。期间如果又 start 或 stop 过，这一次不再执行
 * @Date :2026/10/24 00:07:48
 * @Param: ticket: 安排重连时的代次，数字。代次变了就放弃
 * @return：无
 */
const scheduleReconnect = (ticket: number): void => {
  clearRetryTimer()
  retryTimer = window.setTimeout(() => {
    retryTimer = null
    if (ticket !== generation) {
      return
    }
    openStream()
  }, RECONNECT_DELAY_MS)
}

/*
 * @Author Leon-liao
 * @Function: openStream()
 * @Description //用当前登录凭证打开 /chat/stream。打开后标记已连接，收到帧就分发，出错则关掉并安排重连
 * @Date :2026/10/24 00:07:48
 * @Param: 无
 * @return：无
 */
const openStream = (): void => {
  closeSource()
  const ticket = generation
  const token = readAccessToken()
  status.value = 'connecting'
  const current = new EventSource(
    `${apiPrefix}/chat/stream?token=${encodeURIComponent(token)}`,
  )
  source = current

  current.onopen = () => {
    if (ticket !== generation || source !== current) {
      return
    }
    status.value = 'connected'
  }
  current.onmessage = (event: MessageEvent) => {
    if (ticket !== generation || source !== current || typeof event.data !== 'string') {
      return
    }
    deliverFrame(event.data)
  }
  current.onerror = () => {
    if (ticket !== generation || source !== current) {
      return
    }
    status.value = 'disconnected'
    closeSource()
    scheduleReconnect(ticket)
  }
}

/*
 * @Author Leon-liao
 * @Function: start()
 * @Description //打开整页唯一的聊天 SSE。已经在连接或已连通时不重复拨号
 * @Date :2026/10/24 00:07:48
 * @Param: 无
 * @return：无
 */
export const start = (): void => {
  if (source && source.readyState !== EventSource.CLOSED) {
    return
  }
  clearRetryTimer()
  generation += 1
  openStream()
}

/*
 * @Author Leon-liao
 * @Function: stop()
 * @Description //关掉聊天 SSE 并取消重连。登出和未授权跳转时调用
 * @Date :2026/10/24 00:07:48
 * @Param: 无
 * @return：无
 */
export const stop = (): void => {
  generation += 1
  clearRetryTimer()
  closeSource()
  status.value = 'disconnected'
}

/*
 * @Author Leon-liao
 * @Function: subscribe(key: string, handler: StreamHandler)
 * @Description //按账号和线程订阅该会话的 reply payload。同一个 key 可以有多个回调
 * @Date :2026/10/24 00:07:48
 * @Param: key: 订阅键，字符串，格式为 account_id:thread_id；handler: 收到内层 payload 时调用的函数
 * @return：无
 */
export const subscribe = (key: string, handler: StreamHandler): void => {
  const current = subscribers.get(key)
  if (current) {
    current.add(handler)
    return
  }
  subscribers.set(key, new Set([handler]))
}

/*
 * @Author Leon-liao
 * @Function: unsubscribe(key: string)
 * @Description //移除这个订阅键下的全部回调
 * @Date :2026/10/24 00:07:48
 * @Param: key: 订阅键，字符串，格式为 account_id:thread_id
 * @return：无
 */
export const unsubscribe = (key: string): void => {
  subscribers.delete(key)
}

/*
 * @Author Leon-liao
 * @Function: send(agentId: string, threadId: string, text: string, messageId: string, files?: unknown[])
 * @Description //把一条文本发给指定智能体的会话。agentId 与 threadId 放在 URL 路径里，请求体带 text 和 messageId，有附件时再带 files。失败时由请求层弹出后端返回的原因
 * @Date :2026/10/25 22:24:33
 * @Param: agentId: 智能体 id，字符串，拼进 URL；threadId: 会话线程 id，字符串，拼进 URL；text: 要发送的正文，字符串；messageId: 客户端消息标识，字符串；files: 附件列表，没有时省略
 * @return：Promise<void>。接口失败时拒绝
 */
export const send = async (
  agentId: string,
  threadId: string,
  text: string,
  messageId: string,
  files?: unknown[],
): Promise<void> => {
  // 放到函数里再引用，避免和 request.ts 里的 stop 形成循环依赖
  const { post } = await import('@/utils/request')
  await post(`/agents/${encodeURIComponent(agentId)}/conversations/${encodeURIComponent(threadId)}/chat/send`, {
    body: {
      text,
      message_id: messageId,
      ...(files && files.length > 0 ? { files } : {}),
    },
  })
}
