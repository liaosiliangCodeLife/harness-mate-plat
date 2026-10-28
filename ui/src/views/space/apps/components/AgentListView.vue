<script setup lang="ts">
/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //按接入类型展示智能体列表
 * @File: AgentListView.vue
 * @Time: 2026/10/09 23:24:00
 * @All Rights Reserve By Brtc
 */
import moment from 'moment'
import { Modal } from '@arco-design/web-vue'
import { useDeleteAgent, useGetAgentsWithPage } from '@/hooks/use-agent'
import type { Agent } from '@/models/agent'
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PairHermesModal from '@/views/space/apps/components/PairHermesModal.vue'
import ShareAgentModal from '@/views/space/apps/components/ShareAgentModal.vue'
import { t, translateAgentInfoKey } from '@/locales'

// 1.定义页面所需数据
const route = useRoute()
const router = useRouter()
const props = defineProps({
  listVersion: { type: Number, default: 0 },
  agentType: { type: String, required: true },
})
const emits = defineEmits(['edit-agent'])
const { loading: getAgentsWithPageLoading, agents, paginator, loadAgents } = useGetAgentsWithPage()
const { handleDeleteAgent } = useDeleteAgent()
const pairHermesVisible = ref(false)
const pairingAgent = ref<Agent | null>(null)
const shareVisible = ref(false)
const sharingAgent = ref<Agent | null>(null)

// 打开分享弹窗
const openShare = (agent: Agent) => {
  sharingAgent.value = agent
  shareVisible.value = true
}

// 2.把时间戳格式化成可读时间，空值显示为 -
const formatTimestamp = (timestamp: number | null) => {
  if (!timestamp) {
    return '-'
  }
  return moment(timestamp * 1000).format('YYYY-MM-DD HH:mm')
}

// 3.头像为空时展示名称首字
const agentInitial = (agent: Agent) => {
  const name = agent.name?.trim()
  return name ? name.slice(0, 1) : ''
}

// 4.扩展信息的值转成一行文本：字符串、数字、布尔原样展示，对象和数组压成一行 JSON
const formatAgentInfoValue = (value: unknown) => {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  try {
    const text = JSON.stringify(value)
    return typeof text === 'string' ? text : '-'
  } catch {
    return '-'
  }
}

// 5.按 agent_info 的每个 key 生成展示行，空对象返回空数组
const agentInfoRows = (agent: Agent) => {
  const agentInfo = agent.agent_info
  if (!agentInfo || typeof agentInfo !== 'object' || Array.isArray(agentInfo)) {
    return []
  }
  return Object.entries(agentInfo).map(([key, value]) => ({
    key,
    label: translateAgentInfoKey(key),
    value: formatAgentInfoValue(value),
  }))
}

// 6.点击卡片进入智能体详情
const openAgentDetail = (agent_id: string) => {
  router.push({
    name: 'space-apps-detail',
    params: { agent_id },
  })
}

// 7.打开编辑弹窗，由外层复用创建弹窗
const openEdit = (agent: Agent) => {
  emits('edit-agent', agent)
}

// 8.二次确认后软删除，并重新加载当前搜索条件下的第一页
const confirmRemoveAgent = (agent: Agent) => {
  Modal.warning({
    title: t('space.deleteAgentTitle'),
    content: t('space.deleteAgentContent', { name: agent.name }),
    hideCancel: false,
    okText: t('common.delete'),
    cancelText: t('common.cancel'),
    onOk: async () => {
      await handleDeleteAgent(agent.id)
      await loadAgents(true, String(route.query?.search_word ?? ''), props.agentType)
    },
  })
}

// 9.打开 Hermes 配对弹窗，不进入详情
const openPairHermes = (agent: Agent) => {
  pairingAgent.value = agent
  pairHermesVisible.value = true
}

// 10.定义滚动数据分页处理器
const handleScroll = async (event: UIEvent) => {
  const { scrollTop, scrollHeight, clientHeight } = event.target as HTMLElement

  if (scrollTop + clientHeight >= scrollHeight - 10) {
    if (getAgentsWithPageLoading.value) {
      return
    }
    await loadAgents(false, String(route.query?.search_word ?? ''), props.agentType)
  }
}

// 11.搜索词变化时重新加载第一页
watch(
  () => route.query?.search_word,
  (newValue) => {
    loadAgents(true, String(newValue ?? ''), props.agentType)
  },
  { immediate: true },
)

// 12.创建或编辑智能体成功后刷新列表
watch(
  () => props.listVersion,
  (version) => {
    if (!version) {
      return
    }
    loadAgents(true, String(route.query?.search_word ?? ''), props.agentType)
  },
)

// 13.接入类型变化时重新加载第一页
watch(
  () => props.agentType,
  () => {
    loadAgents(true, String(route.query?.search_word ?? ''), props.agentType)
  },
)
</script>

<template>
  <a-spin
    :loading="getAgentsWithPageLoading"
    class="block h-full w-full scrollbar-w-none overflow-scroll"
    @scroll="handleScroll"
  >
    <!-- 智能体卡片列表：手机单列，桌面多列 -->
    <a-row :gutter="[16, 16]" class="min-w-0 w-full flex-1">
      <a-col v-for="agent in agents" :key="agent.id" :xs="24" :sm="12" :md="8" :lg="6">
        <a-card hoverable class="max-w-full cursor-pointer rounded-lg" @click="openAgentDetail(agent.id)">
          <div class="mb-3 flex items-center gap-3">
            <a-avatar
              :size="40"
              shape="square"
              class="max-w-full flex-shrink-0 rounded-lg bg-blue-700"
              :image-url="agent.avatar || undefined"
            >
              <span v-if="agentInitial(agent)">{{ agentInitial(agent) }}</span>
              <icon-robot v-else />
            </a-avatar>
            <div class="flex min-w-0 flex-1 flex-col gap-0.5">
              <div class="flex min-w-0 items-center justify-between gap-2">
                <span class="truncate text-base font-bold text-gray-900">{{ agent.name }}</span>
                <a-tag v-if="agent.status === 1" color="green" size="small" class="flex-shrink-0">
                  {{ t('common.online') }}
                </a-tag>
                <a-tag v-else color="gray" size="small" class="flex-shrink-0">{{ t('common.offline') }}</a-tag>
              </div>
              <span class="truncate text-sm font-semibold text-[#165DFF]">@{{ agent.agent_type }}</span>
            </div>
          </div>
          <div class="flex flex-col gap-1 text-xs text-gray-500">
            <div v-if="agentInfoRows(agent).length" class="hidden md:block">
              <div
                v-for="item in agentInfoRows(agent)"
                :key="item.key"
                class="truncate"
                :title="`${item.label}: ${item.value}`"
              >
                {{ item.label }}: {{ item.value }}
              </div>
            </div>
            <div v-else class="hidden md:block">-</div>
            <div class="truncate">{{ t('space.conversationCount', { count: agent.conversation_count }) }}</div>
            <div class="truncate">Token: {{ agent.total_token_count }}</div>
            <div class="truncate">{{ t('space.lastActive', { time: formatTimestamp(agent.last_seen_at) }) }}</div>
          </div>
          <div class="mt-3 flex items-center justify-between gap-2" @click.stop>
            <a-button
              type="text"
              size="mini"
              class="!px-1 !text-gray-600"
              @click.stop="openShare(agent)"
            >
              <template #icon>
                <icon-share-alt />
              </template>
              <span class="text-xs">分享</span>
            </a-button>
            <a-dropdown position="br" trigger="click">
              <a-button type="text" size="mini" class="!text-gray-700 w-6 !px-0" @click.stop>
                ...
              </a-button>
              <template #content>
                <a-doption @click.stop="openShare(agent)">分享</a-doption>
                <a-doption @click.stop="openPairHermes(agent)">{{
                  agent.agent_type === 'DEEPSEEK_HARNESS'
                    ? t('space.pairDeepseek')
                    : t('space.pairHermes')
                }}</a-doption>
                <a-doption @click.stop="openEdit(agent)">{{ t('common.edit') }}</a-doption>
                <a-doption class="!text-red-700" @click.stop="confirmRemoveAgent(agent)">
                  {{ t('common.delete') }}
                </a-doption>
              </template>
            </a-dropdown>
          </div>
        </a-card>
      </a-col>
      <a-col v-if="!getAgentsWithPageLoading && agents.length === 0" :span="24">
        <a-empty
          :description="t('space.emptyAgents')"
          class="h-[400px] flex flex-col items-center justify-center"
        />
      </a-col>
    </a-row>
    <!-- 加载器 -->
    <a-row v-if="paginator.total_page >= 2">
      <a-col v-if="paginator.current_page <= paginator.total_page" :span="24" align="center">
        <a-space class="my-4">
          <a-spin />
          <div class="text-gray-400">{{ t('common.loading') }}</div>
        </a-space>
      </a-col>
      <a-col v-else :span="24" align="center">
        <div class="text-gray-400 my-4">{{ t('common.loaded') }}</div>
      </a-col>
    </a-row>
  </a-spin>
  <pair-hermes-modal v-model:visible="pairHermesVisible" :agent="pairingAgent" />
  <share-agent-modal v-model:visible="shareVisible" :agent="sharingAgent" />
</template>

<style scoped></style>
