import type { BasePaginatorRequest, BasePaginatorResponse, BaseResponse } from '@/models/base'

// 智能体基础信息
export type Agent = {
  id: string
  account_id: string
  peer_id: string
  bot_id: string
  name: string
  avatar: string
  agent_info: Record<string, any>
  status: number
  conversation_count: number
  total_token_count: number
  last_seen_at: number | null
  gateway_url: string
  gateway_key: string
  updated_at: number
  created_at: number
}

// 获取智能体分页列表请求
export type GetAgentsWithPageRequest = BasePaginatorRequest & { search_word: string }

// 获取智能体分页列表响应
export type GetAgentsWithPageResponse = BasePaginatorResponse<Agent>

// 获取智能体详情响应
export type GetAgentResponse = BaseResponse<Agent>

// 创建智能体请求
export type CreateAgentRequest = {
  name: string
  bot_id: string
  peer_id: string
  avatar?: string
  gateway_id?: string
}

// 更新智能体请求，仅包含本次发生变化的字段
export type UpdateAgentRequest = {
  name?: string
  avatar?: string
  agent_info?: Record<string, any>
}

// 可生成的智能体标识类型
export type GenerateAgentIdType = 'peer_id' | 'bot_id' | 'ws_session_id' | 'thread_id'

// 生成智能体标识请求
export type GenerateAgentIdRequest = {
  type: GenerateAgentIdType
  agent_id?: string
}

// 生成智能体标识响应，data 的键名与请求的 type 一致
export type GenerateAgentIdResponse<T extends GenerateAgentIdType = GenerateAgentIdType> =
  BaseResponse<Record<T, string>>
