<script setup lang="ts">
import { computed, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useGetAgent } from '@/hooks/use-agent'
import AgentPoster from '@/views/space/apps/components/AgentPoster.vue'
import CreateConversationModal from '@/views/space/apps/components/CreateConversationModal.vue'
import { getAgent } from '@/services/agent'
import {
  conversationListVersionKey,
  detailAgentKey,
  hasConversationsKey,
  reloadDetailAgentKey,
} from '@/views/space/apps/detail-agent'
import { t, translateAgentInfoKey } from '@/locales'
import { agentTypeTheme } from '@/utils/agent-theme'

const route = useRoute()
const { loading, agent, loadAgent } = useGetAgent()
const agentId = computed(() => String(route.params?.agent_id ?? ''))
const createConversationVisible = ref(false)
const conversationListVersion = ref(0)
const isConversationList = computed(() => route.name === 'space-apps-detail')
const hasConversations = ref(false)
const posterAgent = computed(() => {
  const current = agent.value
  if (!current || current.id !== agentId.value) {
    return null
  }
  return current
})
const pageBg = computed(() => {
  if (!hasConversations.value || !posterAgent.value) {
    return '#FFFFFF'
  }
  return agentTypeTheme(posterAgent.value.agent_type).bg
})

provide(detailAgentKey, agent)
provide(conversationListVersionKey, conversationListVersion)
provide(hasConversationsKey, hasConversations)

let reloadTimer: number | undefined
provide(reloadDetailAgentKey, () => {
  window.clearTimeout(reloadTimer)
  reloadTimer = window.setTimeout(() => {
    const id = agentId.value
    if (!id || !agent.value) {
      return
    }
    void getAgent(id)
      .then((resp) => {
        if (agent.value && resp.data?.id === id) {
          agent.value = resp.data
        }
      })
      .catch(() => undefined)
  }, 300)
})

// 新建成功后只递增版本号，列表页按当前搜索词自己重载第一页
const onConversationCreated = () => {
  conversationListVersion.value += 1
}

// 头像为空时展示名称首字
const agentInitial = computed(() => {
  const name = agent.value?.name?.trim()
  return name ? name.slice(0, 1) : ''
})

// 扩展信息的值转成一行文本：字符串、数字、布尔原样展示，对象和数组压成一行 JSON
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

// 按 agent_info 的每个 key 生成展示行，空对象返回空数组
const agentInfoRows = computed(() => {
  const agentInfo = agent.value?.agent_info
  if (!agentInfo || typeof agentInfo !== 'object' || Array.isArray(agentInfo)) {
    return []
  }
  return Object.entries(agentInfo).map(([key, value]) => ({
    key,
    label: translateAgentInfoKey(key),
    value: formatAgentInfoValue(value),
  }))
})

watch(
  agentId,
  (id) => {
    hasConversations.value = false
    if (id) {
      loadAgent(id)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div
    class="min-h-screen flex flex-col h-full overflow-hidden"
    :style="{ backgroundColor: pageBg }"
  >
    <agent-poster
      v-if="posterAgent && !hasConversations"
      :agent-type="posterAgent.agent_type"
      class="detail-poster-bg"
    />
    <!-- 顶部智能体信息 -->
    <div class="relative z-[1] flex-shrink-0 bg-white px-4 py-3 flex items-center gap-3 border-b">
      <router-link :to="{ name: 'space-apps-list' }">
        <a-button size="mini">
          <template #icon>
            <icon-left />
          </template>
        </a-button>
      </router-link>
      <template v-if="loading || !agent">
        <a-skeleton :animation="true" class="flex-1">
          <div class="flex items-center gap-3">
            <a-skeleton-shape shape="square" size="40" />
            <div class="flex flex-col gap-2">
              <a-skeleton-line :widths="[120]" />
              <a-skeleton-line :widths="[280]" :line-height="18" />
            </div>
          </div>
        </a-skeleton>
      </template>
      <template v-else>
        <a-avatar
          :size="40"
          shape="square"
          class="rounded-lg bg-blue-700 flex-shrink-0"
          :image-url="agent.avatar || undefined"
        >
          <span v-if="agentInitial">{{ agentInitial }}</span>
          <icon-robot v-else />
        </a-avatar>
        <div class="flex flex-1 flex-col justify-center min-w-0 gap-1">
          <div class="flex items-center gap-2">
            <div class="text-gray-700 font-bold truncate">{{ agent.name }}</div>
            <a-tag v-if="agent.status === 1" color="green" size="small">{{ t('common.online') }}</a-tag>
            <a-tag v-else color="gray" size="small">{{ t('common.offline') }}</a-tag>
          </div>
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500 min-w-0">
            <template v-if="agentInfoRows.length">
              <span
                v-for="item in agentInfoRows"
                :key="item.key"
                class="max-w-full truncate"
                :title="`${item.label}: ${item.value}`"
              >
                {{ item.label }}: {{ item.value }}
              </span>
            </template>
            <span v-else>-</span>
          </div>
        </div>
      </template>
      <a-button
        v-if="isConversationList"
        type="primary"
        class="rounded-lg flex-shrink-0"
        @click="createConversationVisible = true"
      >
        <template #icon>
          <icon-plus />
        </template>
        {{ t('space.newConversation') }}
      </a-button>
    </div>
    <!-- 会话列表 -->
    <div class="relative z-[1] flex-1 min-h-0">
      <router-view />
    </div>
  </div>
  <create-conversation-modal
    v-model:visible="createConversationVisible"
    :agent-id="agentId"
    :callback="onConversationCreated"
  />
</template>

<style scoped>
.detail-poster-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}
</style>
