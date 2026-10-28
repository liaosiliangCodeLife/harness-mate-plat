/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //分享智能体相关请求与响应类型
 * @File: share-agent.ts
 * @Time: 2026/10/28 10:04:41
 * @All Rights Reserve By Brtc
 */
import type { BasePaginatorRequest, BasePaginatorResponse, BaseResponse } from '@/models/base'

// 分享记录（列表项）
export type ShareAgent = {
  id: string
  share_url: string
  has_password: boolean
  access_num: number
  accessed_num: number
  shared_info: string
  pay_url: string
  status: number
  created_at: number
  updated_at: number
}

// 创建分享请求
export type CreateShareAgentRequest = {
  access_prompt?: string
  access_pwd?: string
  access_num?: number
  shared_info?: string
  pay_url?: string
}

// 增量修改分享请求
export type UpdateShareAgentRequest = {
  access_prompt?: string
  access_pwd?: string
  access_num?: number
  shared_info?: string
  pay_url?: string
}

// 创建分享响应 data
export type CreateShareAgentResponse = BaseResponse<{
  id: string
  agent_id: string
  access_num: number
  share_url: string
  created_at: number
}>

// 分享分页列表响应
export type GetShareAgentsWithPageResponse = BasePaginatorResponse<ShareAgent>

// 分享落地页响应 data
export type ShareLandingResponse = BaseResponse<{
  share_id: string
  agent_name: string
  agent_avatar: string
  agent_status: number
  shared_info: string
  need_password: boolean
  pay_url: string
  expired: boolean
  expire_reason: '' | 'closed' | 'access_exhausted'
}>

// 换取分享态 token 响应 data
export type ShareAccessResponse = BaseResponse<{
  access_token: string
  expire_at: number
  account_id: string
  share_id: string
  token_type: string
}>

// 创建访客会话响应 data
export type CreateShareConversationResponse = BaseResponse<{
  id: string
  agent_id: string
  thread_id: string
  type: number
  created_at: number
}>

// 分页查询分享列表请求
export type GetShareAgentsWithPageRequest = BasePaginatorRequest
