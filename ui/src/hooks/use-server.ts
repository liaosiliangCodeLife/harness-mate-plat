import { ref } from 'vue'
import { getOpenServer, getOpenServers, getServer } from '@/services/server'
import type { ServerInfo } from '@/models/server'

export const useGetServer = () => {
  // 1.定义 hooks 所需数据
  const loading = ref(false)
  const server = ref<ServerInfo | null>(null)

  // 2.拉取当前账号的 WS 网关信息，失败提示由请求拦截器统一弹出
  const loadServer = async () => {
    try {
      loading.value = true
      const resp = await getServer()
      server.value = resp.data
      return resp.data
    } finally {
      loading.value = false
    }
  }

  return { loading, server, loadServer }
}

export const useGetOpenServer = () => {
  // 1.定义 hooks 所需数据
  const loading = ref(false)
  const server = ref<ServerInfo | null>(null)

  // 2.拉取全局最近更新的网关，失败提示由请求拦截器统一弹出
  const loadOpenServer = async () => {
    try {
      loading.value = true
      const resp = await getOpenServer()
      server.value = resp.data
      return resp.data
    } finally {
      loading.value = false
    }
  }

  return { loading, server, loadOpenServer }
}

export const useGetOpenServers = () => {
  // 1.定义 hooks 所需数据
  const loading = ref(false)
  const servers = ref<ServerInfo[]>([])

  // 2.拉取网关列表，失败提示由请求拦截器统一弹出
  const loadOpenServers = async () => {
    try {
      loading.value = true
      const resp = await getOpenServers()
      servers.value = resp.data?.list ?? []
      return servers.value
    } finally {
      loading.value = false
    }
  }

  return { loading, servers, loadOpenServers }
}
