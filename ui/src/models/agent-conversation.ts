import type { BasePaginatorRequest, BasePaginatorResponse, BaseResponse } from '@/models/base'

// 智能体会话基础信息
export type AgentConversation = {
  id: string
  account_id: string
  agent_id: string
  thread_id: string
  ws_session_id: string
  title: string
  pinned: number
  status: number
  message_count: number
  total_token_count: number
  last_message_at: number | null
  last_message_preview: string
  conversation_info: Record<string, any>
  updated_at: number
  created_at: number
}

// 获取智能体会话分页列表请求
export type GetAgentConversationsWithPageRequest = BasePaginatorRequest & {
  search_word: string
}

// 获取智能体会话分页列表响应
export type GetAgentConversationsWithPageResponse = BasePaginatorResponse<AgentConversation>

// 创建智能体会话请求。标题为空时不传 title
export type CreateAgentConversationRequest = {
  thread_id: string
  title?: string
  conversation_info?: Record<string, any>
}

// 创建智能体会话响应
export type CreateAgentConversationResponse = BaseResponse<{ id: string }>

// 修改智能体会话请求，只包含本次要提交的字段
export type UpdateAgentConversationRequest = {
  title?: string
  pinned?: 0 | 1
  status?: number
  conversation_info?: Record<string, any>
}
