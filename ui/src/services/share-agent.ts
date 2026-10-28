/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //分享智能体接口封装
 * @File: share-agent.ts
 * @Time: 2026/10/28 10:04:41
 * @All Rights Reserve By Brtc
 */
import { get, post } from '@/utils/request'
import type { BaseResponse } from '@/models/base'
import type {
  CreateShareAgentRequest,
  CreateShareAgentResponse,
  CreateShareConversationResponse,
  GetShareAgentsWithPageRequest,
  GetShareAgentsWithPageResponse,
  ShareAccessResponse,
  ShareLandingResponse,
  UpdateShareAgentRequest,
} from '@/models/share-agent'

// 创建分享
export const createShareAgent = (agent_id: string, req: CreateShareAgentRequest) => {
  return post<CreateShareAgentResponse>(`/agents/${encodeURIComponent(agent_id)}/shares`, {
    body: req,
  })
}

// 分页获取指定智能体下的分享列表
export const getShareAgentsWithPage = (agent_id: string, req: GetShareAgentsWithPageRequest) => {
  return get<GetShareAgentsWithPageResponse>(`/agents/${encodeURIComponent(agent_id)}/shares`, {
    params: req,
  })
}

// 增量修改分享
export const updateShareAgent = (
  agent_id: string,
  share_id: string,
  req: UpdateShareAgentRequest,
) => {
  return post<BaseResponse<{ updated: boolean }>>(
    `/agents/${encodeURIComponent(agent_id)}/shares/${encodeURIComponent(share_id)}`,
    { body: req },
  )
}

// 停用（软删）分享
export const deleteShareAgent = (agent_id: string, share_id: string) => {
  return post<BaseResponse<{ deleted: boolean }>>(
    `/agents/${encodeURIComponent(agent_id)}/shares/${encodeURIComponent(share_id)}/delete`,
  )
}

// 免登录获取落地页信息
export const getShareLanding = (share_id: string) => {
  return get<ShareLandingResponse>(`/shares/${encodeURIComponent(share_id)}`, {
    silent: true,
  })
}

// 免登录换取分享态 token
export const accessShare = (share_id: string, pwd?: string) => {
  return post<ShareAccessResponse>(`/shares/${encodeURIComponent(share_id)}/access`, {
    body: pwd ? { pwd } : {},
    silent: true,
  })
}

// 分享态创建访客会话
export const createShareConversation = (
  share_id: string,
  req: { title?: string },
  token: string,
) => {
  return post<CreateShareConversationResponse>(
    `/shares/${encodeURIComponent(share_id)}/conversations`,
    { body: req, token, silent: true },
  )
}
