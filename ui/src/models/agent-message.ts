import type { BaseResponse } from '@/models/base'

// 智能体会话消息
export type AgentMessage = {
  id: string
  conversation_id: string
  account_id: string
  message_type: string
  message_role: string
  message_content: string
  message_token: number
  message_latency: number
  message_id: string
  message_status: number
  message_reasoning: string
  message_info: Record<string, unknown>
  updated_at: number
  created_at: number
}

// 按最近 N 轮或向上游标获取消息
export type GetAgentMessagesRequest = {
  turns?: number
  limit?: number
  before?: string
}

// 消息列表：正序，并告知前面是否还有更早的消息
export type GetAgentMessagesResponse = BaseResponse<{
  list: AgentMessage[]
  has_more: boolean
  next_cursor: string
}>

// 按 (conversation_id, message_id) 幂等写入一条消息
export type UpsertAgentMessageRequest = {
  message_id: string
  message_role: 'user' | 'assistant'
  message_content: string
  message_type?: string
  message_status?: number
  message_reasoning?: string
  message_info?: {
    tool_events?: unknown[]
    files?: ChatFile[]
  }
  message_token?: number
  message_latency?: number
}

// 消息携带的文件。is_image 为真时按图片渲染，否则按文件卡片渲染
export type ChatFile = {
  name: string
  url: string
  is_image: boolean
  size?: number
}

// 聊天卡片里的一条气泡
export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking: boolean
  // 0 生成中 / 1 完成 / 2 失败。只有本次会话里的非历史消息在 0 时显示「生成中…」
  status?: number
  // 来自历史接口。重进会话时这些消息已经结束，即使 status 为 0 也不再显示「生成中…」
  fromHistory?: boolean
  files?: ChatFile[]
}
