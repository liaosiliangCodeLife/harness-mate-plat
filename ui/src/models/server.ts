import type { BaseResponse } from '@/models/base'

// WS 网关信息
export type ServerInfo = {
  id: string
  account_id: string
  gateway_url: string
  gateway_key: string
  updated_at: number
  created_at: number
}

// 获取 WS 网关信息响应
export type GetServerResponse = BaseResponse<ServerInfo>

// 获取网关列表响应
export type GetOpenServersResponse = BaseResponse<{
  list: ServerInfo[]
}>
