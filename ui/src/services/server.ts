import { get } from '@/utils/request'
import type { GetOpenServersResponse, GetServerResponse } from '@/models/server'

// 获取当前登录账号的 WS 网关信息
export const getServer = () => {
  // 账号下暂无网关时后端返回 not_found，这里改为消息提示，避免整页跳到 404
  return get<GetServerResponse>(`/server`, { messageOnNotFound: true })
}

// 获取全局最近更新的网关，免登录
export const getOpenServer = () => {
  return get<GetServerResponse>(`/open-api/server`, { messageOnNotFound: true })
}

// 获取网关列表，需要登录
export const getOpenServers = () => {
  return get<GetOpenServersResponse>(`/open-api/servers`)
}
