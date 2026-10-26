import { ref } from 'vue'
import { getOpenServer } from '@/services/server'
import type { ServerInfo } from '@/models/server'

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
