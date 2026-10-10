import { get, post } from '@/utils/request'
import type { BaseResponse } from '@/models/base'
import type {
  CreateAgentRequest,
  GenerateAgentIdRequest,
  GenerateAgentIdResponse,
  GenerateAgentIdType,
  GetAgentResponse,
  GetAgentsWithPageRequest,
  GetAgentsWithPageResponse,
  UpdateAgentRequest,
} from '@/models/agent'
import type {
  CreateAgentConversationRequest,
  CreateAgentConversationResponse,
  GetAgentConversationsWithPageRequest,
  GetAgentConversationsWithPageResponse,
  UpdateAgentConversationRequest,
} from '@/models/agent-conversation'
import type {
  GetAgentMessagesRequest,
  GetAgentMessagesResponse,
  UpsertAgentMessageRequest,
} from '@/models/agent-message'

// 分页获取当前账号下的智能体列表
export const getAgentsWithPage = (req: GetAgentsWithPageRequest) => {
  return get<GetAgentsWithPageResponse>(`/agents`, { params: req })
}

// 创建智能体
export const createAgent = (req: CreateAgentRequest) => {
  return post<BaseResponse<{ id: string }>>(`/agents`, { body: req })
}

// 增量更新智能体，只提交本次有变化的字段
export const updateAgent = (agent_id: string, req: UpdateAgentRequest) => {
  return post<BaseResponse<any>>(`/agents/${agent_id}`, { body: req })
}

// 软删除智能体
export const deleteAgent = (agent_id: string) => {
  return post<BaseResponse<any>>(`/agents/${agent_id}/delete`)
}

// 把智能体在线状态写入数据库。1 为在线，0 为离线。失败由调用方自行忽略
export const updateAgentOnlineStatus = (agent_id: string, status: 0 | 1) => {
  return post<BaseResponse<{ status: number }>>(`/agents/${agent_id}/online-status`, {
    body: { status },
    silent: true,
  })
}

// 获取指定智能体详情
export const getAgent = (agent_id: string) => {
  return get<GetAgentResponse>(`/agents/${agent_id}`)
}

// 按 type 生成智能体标识，data 的键名与 type 一致
export const generateAgentId = <T extends GenerateAgentIdType>(
  req: Omit<GenerateAgentIdRequest, 'type'> & { type: T },
) => {
  return get<GenerateAgentIdResponse<T>>(`/agent/generate-id`, { params: req })
}

// 在指定智能体下创建会话。thread_id 必填，标题为空时不要带 title
export const createAgentConversation = (agent_id: string, req: CreateAgentConversationRequest) => {
  return post<CreateAgentConversationResponse>(`/agents/${agent_id}/conversations`, { body: req })
}

// 分页获取指定智能体下的会话列表
export const getConversationsWithPage = (
  agent_id: string,
  req: GetAgentConversationsWithPageRequest,
) => {
  return get<GetAgentConversationsWithPageResponse>(`/agents/${agent_id}/conversations`, {
    params: req,
  })
}

// 获取指定会话下的消息。turns 取最近 N 轮；before + limit 取更早的一页
export const getAgentConversationMessages = (
  agent_id: string,
  conversation_id: string,
  req: GetAgentMessagesRequest,
) => {
  const params: Record<string, string | number> = {}
  if (req.turns !== undefined) {
    params.turns = req.turns
  }
  if (req.limit !== undefined) {
    params.limit = req.limit
  }
  if (req.before) {
    params.before = req.before
  }
  return get<GetAgentMessagesResponse>(
    `/agents/${agent_id}/conversations/${conversation_id}/messages`,
    { params, messageOnNotFound: true },
  )
}

// 按 message_id 幂等写入一条消息，重复提交只覆盖内容
export const upsertAgentConversationMessage = (
  agent_id: string,
  conversation_id: string,
  req: UpsertAgentMessageRequest,
) => {
  return post<BaseResponse<{ id: string }>>(
    `/agents/${agent_id}/conversations/${conversation_id}/messages`,
    { body: req },
  )
}

// 增量修改指定会话，只提交本次要改的字段
export const updateAgentConversation = (
  agent_id: string,
  conversation_id: string,
  req: UpdateAgentConversationRequest,
) => {
  return post<BaseResponse<any>>(`/agents/${agent_id}/conversations/${conversation_id}`, {
    body: req,
  })
}

// 软删除指定会话
export const deleteAgentConversation = (agent_id: string, conversation_id: string) => {
  return post<BaseResponse<any>>(
    `/agents/${agent_id}/conversations/${conversation_id}/delete`,
  )
}
