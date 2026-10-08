import type { Agent } from '@/models/agent'
import type { AgentConversation } from '@/models/agent-conversation'
import type { ChatFile, ChatMessage } from '@/models/agent-message'
import type { HermesOutboundMessage, HermesReplyData } from '@/models/hermes-channel'
import { chatFileFromReply } from '@/utils/chat-files'

// 组装 Peer → Hermes 的发送信封
export const buildOutboundMessage = (
  agent: Agent,
  conversation: AgentConversation,
  text: string,
): HermesOutboundMessage => {
  return {
    to: agent.bot_id,
    data: {
      type: 'message',
      account_id: conversation.account_id,
      thread_id: conversation.thread_id,
      from_device: agent.peer_id,
      data: {
        type: 'message',
        text,
      },
    },
  }
}

// 按 message_id 找到已有气泡，没有则新建一条助手消息
const ensureAssistantMessage = (messages: ChatMessage[], id: string, thinking: boolean): number => {
  const index = messages.findIndex((item) => item.id === id)
  if (index !== -1) {
    return index
  }
  messages.push({
    id,
    role: 'assistant',
    content: '',
    thinking,
  })
  return messages.length - 1
}

// 不同 Hermes 版本挂在正文末尾的流式光标，字形不完全一样
const STREAM_CURSOR_GLYPHS = new Set([
  '\u2589', // ▉
  '\u258A', // ▊
  '\u258B', // ▋
  '\u258C', // ▌
  '\u258D', // ▍
  '\u2588', // █
  '\u2026', // …
])

// 去掉结尾的空格和换行，用来判断光标；正文中间的空白不动
const trimTrailingWhitespace = (text: string): string => text.replace(/[ \r\n]+$/, '')

// 去掉正文结尾的流式光标。先忽略结尾空白，再删掉一个光标字形，最后再去一次结尾空白。
// 结尾不是光标时原文原样返回；正文中间的相同字符一律保留。
export const stripStreamCursor = (text: string): string => {
  const trimmed = trimTrailingWhitespace(text)
  const glyph = trimmed.slice(-1)
  if (!STREAM_CURSOR_GLYPHS.has(glyph)) {
    return text
  }
  return trimTrailingWhitespace(trimmed.slice(0, -1))
}

// delta 的 text 是截至当前的累计正文。新文本能接上现有正文时直接覆盖；
// 现有正文已以新文本结尾时保留原文，避免缩短丢字；两边都对不上才按增量追加。
const mergeReplyContent = (current: string, incoming: string, delta: boolean): string => {
  const visible = stripStreamCursor(incoming)
  if (!delta) {
    return visible || current
  }
  if (visible.startsWith(current)) {
    return visible
  }
  if (current.endsWith(visible)) {
    return current
  }
  return `${current}${visible}`
}

// 同一条气泡上合并文件，相同地址只留一份
const mergeReplyFile = (current: ChatFile[] | undefined, incoming: ChatFile | null): ChatFile[] | undefined => {
  if (!incoming) {
    return current
  }
  const next = (current || []).filter((item) => item.url && item.url !== incoming.url)
  next.push(incoming)
  return next
}

// 结束帧可能只有文件、没有正文。这种气泡要留着，文件跟着原对象一起保留
const finishMessage = (messages: ChatMessage[], id: string) => {
  const index = messages.findIndex((item) => item.id === id)
  if (index === -1) {
    return
  }
  const current = messages[index]
  const hasFiles = (current.files?.length || 0) > 0
  if (!current.content.trim() && !hasFiles) {
    messages.splice(index, 1)
    return
  }
  messages[index] = { ...current, thinking: false, status: 1 }
}

// 没有 message_id 时，文件挂到当前这条正在生成的助手气泡上，不另起一条
const liveAssistantId = (messages: ChatMessage[]): string => {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const item = messages[index]
    if (item.role === 'assistant' && !item.fromHistory && !item.id.startsWith('ws:pending')) {
      return item.id
    }
  }
  return ''
}

// 把一帧 reply 合并进消息列表：delta 按累计正文覆盖，思考中单独标记，done 结束
export const reduceHermesReply = (
  messages: ChatMessage[],
  thinking: boolean,
  payload: HermesReplyData,
): { messages: ChatMessage[]; thinking: boolean } => {
  const next = messages.slice()
  const messageId = payload.message_id?.trim() || ''
  const text = payload.text || ''
  const delta = payload.delta === true
  const done = payload.done === true
  const isThinking = payload.status === 'thinking'
  const bubbleId = messageId ? `ws:${messageId}` : ''
  const incomingFile = chatFileFromReply(payload)

  if (isThinking && !done) {
    if (bubbleId) {
      const index = ensureAssistantMessage(next, bubbleId, true)
      next[index] = { ...next[index], thinking: true, status: 0 }
    }
    return { messages: next, thinking: true }
  }

  let nextThinking = thinking
  // 有 message_id 就更新这一条；结束帧只带文件时也挂到已有气泡，不新建
  const targetId = bubbleId || (incomingFile ? liveAssistantId(next) : '') || (text ? 'ws:pending' : '')
  if (targetId) {
    const index = ensureAssistantMessage(next, targetId, false)
    const current = next[index]
    const content = mergeReplyContent(current.content, text, delta)
    next[index] = {
      ...current,
      content,
      files: mergeReplyFile(current.files, incomingFile),
      thinking: false,
      // 没有 delta 的正文是一整段回复，即使没带 done 也不该继续停在生成中
      status: done || !delta ? 1 : 0,
    }
    nextThinking = false
  }

  if (done) {
    nextThinking = false
    for (let index = next.length - 1; index >= 0; index -= 1) {
      const item = next[index]
      if (item.role !== 'assistant' || item.fromHistory) {
        continue
      }
      // 本帧新建的气泡可能已经是完成态；没有正文也没有文件时同样清掉
      if (item.status !== 0 && item.id !== bubbleId) {
        continue
      }
      finishMessage(next, item.id)
    }
  }

  return { messages: next, thinking: nextThinking }
}
