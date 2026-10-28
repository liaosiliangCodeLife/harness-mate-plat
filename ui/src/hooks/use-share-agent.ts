/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //分享智能体相关 hooks
 * @File: use-share-agent.ts
 * @Time: 2026/10/28 10:04:41
 * @All Rights Reserve By Brtc
 */
import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  accessShare,
  createShareAgent,
  createShareConversation,
  deleteShareAgent,
  getShareAgentsWithPage,
  getShareLanding,
  updateShareAgent,
} from '@/services/share-agent'
import type {
  CreateShareAgentRequest,
  GetShareAgentsWithPageResponse,
  ShareLandingResponse,
  UpdateShareAgentRequest,
} from '@/models/share-agent'

const buildDefaultPaginator = () => ({
  current_page: 1,
  page_size: 20,
  total_page: 0,
  total_record: 0,
})

export const useGetShareAgentsWithPage = (agent_id: () => string) => {
  const loading = ref(false)
  const shares = ref<GetShareAgentsWithPageResponse['data']['list']>([])
  const paginator = ref(buildDefaultPaginator())

  const loadShares = async (init: boolean = false) => {
    const id = agent_id()
    if (!id) {
      return
    }
    if (init) {
      paginator.value = buildDefaultPaginator()
    } else if (paginator.value.current_page > paginator.value.total_page) {
      return
    }
    try {
      loading.value = true
      const resp = await getShareAgentsWithPage(id, {
        current_page: paginator.value.current_page,
        page_size: paginator.value.page_size,
      })
      const data = resp.data
      paginator.value = data.paginator
      if (paginator.value.current_page <= paginator.value.total_page) {
        paginator.value.current_page += 1
      }
      if (init) {
        shares.value = data.list
      } else {
        shares.value.push(...data.list)
      }
    } finally {
      loading.value = false
    }
  }

  return { loading, shares, paginator, loadShares }
}

export const useCreateShareAgent = () => {
  const loading = ref(false)
  const handleCreate = async (agent_id: string, req: CreateShareAgentRequest) => {
    try {
      loading.value = true
      const resp = await createShareAgent(agent_id, req)
      Message.success(resp.message || '创建分享成功')
      return resp.data
    } finally {
      loading.value = false
    }
  }
  return { loading, handleCreate }
}

export const useUpdateShareAgent = () => {
  const loading = ref(false)
  const handleUpdate = async (
    agent_id: string,
    share_id: string,
    req: UpdateShareAgentRequest,
  ) => {
    try {
      loading.value = true
      const resp = await updateShareAgent(agent_id, share_id, req)
      Message.success(resp.message || '保存成功')
      return resp.data
    } finally {
      loading.value = false
    }
  }
  return { loading, handleUpdate }
}

export const useDeleteShareAgent = () => {
  const loading = ref(false)
  const handleDelete = async (agent_id: string, share_id: string) => {
    try {
      loading.value = true
      const resp = await deleteShareAgent(agent_id, share_id)
      Message.success(resp.message || '已停用分享')
      return resp.data
    } finally {
      loading.value = false
    }
  }
  return { loading, handleDelete }
}

export const useShareLanding = (share_id: () => string) => {
  const loading = ref(false)
  const landing = ref<ShareLandingResponse['data'] | null>(null)

  const loadLanding = async () => {
    const id = share_id()
    if (!id) {
      return
    }
    try {
      loading.value = true
      const resp = await getShareLanding(id)
      landing.value = resp.data
    } finally {
      loading.value = false
    }
  }

  return { loading, landing, loadLanding }
}

export const useAccessShare = () => {
  const loading = ref(false)
  const handleAccess = async (share_id: string, pwd?: string) => {
    try {
      loading.value = true
      const resp = await accessShare(share_id, pwd)
      return resp.data
    } finally {
      loading.value = false
    }
  }
  return { loading, handleAccess }
}

export const useCreateShareConversation = () => {
  const loading = ref(false)
  const handleCreate = async (share_id: string, token: string, title?: string) => {
    try {
      loading.value = true
      const body = title ? { title } : {}
      const resp = await createShareConversation(share_id, body, token)
      return resp.data
    } finally {
      loading.value = false
    }
  }
  return { loading, handleCreate }
}
