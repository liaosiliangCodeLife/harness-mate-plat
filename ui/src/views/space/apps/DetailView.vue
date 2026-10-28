<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useGetAgentConversations } from '@/hooks/use-agent'
import ConversationChatCard from '@/views/space/apps/components/ConversationChatCard.vue'
import {
  conversationListVersionKey,
  detailAgentKey,
  hasConversationsKey,
} from '@/views/space/apps/detail-agent'
import { t } from '@/locales'
import moment from 'moment'

// 1.页面基础数据：会话属于当前详情页的智能体
const route = useRoute()
const {
  loading: getConversationsLoading,
  conversations,
  paginator,
  loadConversations,
} = useGetAgentConversations()
const agent = inject(detailAgentKey, ref(null))
const conversationListVersion = inject(conversationListVersionKey, ref(0))
const hasConversations = inject(hasConversationsKey, ref(false))

const agentId = computed(() => String(route.params?.agent_id ?? ''))
const agentMatched = computed(() => Boolean(agent.value && agent.value.id === agentId.value))
// 首屏转圈；翻页时只在底部提示，避免盖住已经连上的聊天卡片
const pageLoading = computed(
  () =>
    !agentMatched.value ||
    (getConversationsLoading.value && conversations.value.length === 0),
)

const isMobile = ref(false)
const activeConversationId = ref<string | null>(null)
let mobileMedia: MediaQueryList | null = null
const syncIsMobile = () => {
  isMobile.value = Boolean(mobileMedia?.matches)
  if (!isMobile.value) {
    activeConversationId.value = null
  }
}

onMounted(() => {
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    mobileMedia = window.matchMedia('(max-width: 767px)')
    syncIsMobile()
    mobileMedia.addEventListener('change', syncIsMobile)
  }
})

onUnmounted(() => {
  mobileMedia?.removeEventListener('change', syncIsMobile)
  mobileMedia = null
})

// 2.置顶在前，其余按创建时间从早到晚（新建出现在最后）
const sortedConversations = computed(() => {
  return [...conversations.value].sort((left, right) => {
    const pinnedDiff = right.pinned - left.pinned
    if (pinnedDiff !== 0) {
      return pinnedDiff
    }
    const leftCreated = Number(left.created_at) || 0
    const rightCreated = Number(right.created_at) || 0
    if (leftCreated !== rightCreated) {
      return leftCreated - rightCreated
    }
    return String(left.id).localeCompare(String(right.id))
  })
})

const activeConversation = computed(() =>
  sortedConversations.value.find((item) => item.id === activeConversationId.value) ?? null,
)

const formatConversationTime = (conversation: { last_message_at?: number | null; created_at?: number | null }) => {
  const timestamp = conversation.last_message_at || conversation.created_at
  if (!timestamp) {
    return '-'
  }
  return moment(Number(timestamp) * 1000).format('MM-DD HH:mm')
}

const openMobileConversation = (id: string) => {
  activeConversationId.value = id
}

const closeMobileConversation = () => {
  activeConversationId.value = null
}

// 3.滚动到底加载下一页
const handleScroll = async (event: UIEvent) => {
  const { scrollTop, scrollHeight, clientHeight } = event.target as HTMLElement

  if (scrollTop + clientHeight >= scrollHeight - 10) {
    if (getConversationsLoading.value || !agentId.value) {
      return
    }
    await loadConversations(agentId.value, false, String(route.query?.search_word ?? ''))
  }
}

watch(
  agentId,
  (id) => {
    if (!id) {
      return
    }
    // 切换智能体时先清掉上一份会话，避免用新网关参数去连旧会话
    conversations.value = []
    activeConversationId.value = null
    loadConversations(id, true, String(route.query?.search_word ?? ''))
  },
  { immediate: true },
)

// 4.编辑或删除会话后，按当前搜索词重新加载第一页
const refreshConversations = () => {
  if (!agentId.value) {
    return
  }
  loadConversations(agentId.value, true, String(route.query?.search_word ?? ''))
}

// 顶部「新增会话」成功后版本号 +1，这里按当前搜索词重载第一页
watch(conversationListVersion, () => {
  refreshConversations()
})

// 有会话时通知布局页换成浅色底并藏起海报；清空或换智能体时改回白底海报
watch(
  () => conversations.value.length,
  (length) => {
    hasConversations.value = length > 0
  },
  { immediate: true },
)
</script>

<template>
  <a-spin
    :loading="pageLoading"
    class="block h-full w-full min-w-0 max-w-full scrollbar-w-none overflow-scroll"
    @scroll="handleScroll"
  >
    <div class="min-w-0 w-full max-w-full p-3 sm:p-6">
      <!-- 手机：会话列表；点进后全屏聊天 -->
      <div v-if="isMobile && agentMatched && agent" class="min-w-0 w-full">
        <div v-if="!activeConversationId" class="flex flex-col gap-2">
          <button
            v-for="conversation in sortedConversations"
            :key="conversation.id"
            type="button"
            class="flex w-full min-w-0 items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-3 text-left"
            @click="openMobileConversation(conversation.id)"
          >
            <div class="min-w-0 flex-1">
              <div class="flex min-w-0 items-center gap-2">
                <a-tag
                  v-if="conversation.pinned === 1"
                  color="orangered"
                  size="small"
                  class="flex-shrink-0"
                >
                  {{ t('common.pin') }}
                </a-tag>
                <span class="truncate text-sm font-medium text-gray-900">
                  {{ conversation.title || t('space.newConversation') }}
                </span>
              </div>
              <div class="mt-1 truncate text-[11px] text-gray-400">
                {{ t('conversation.messageCount', { count: conversation.message_count }) }}
                · {{ formatConversationTime(conversation) }}
              </div>
            </div>
            <icon-right class="flex-shrink-0 text-gray-400" />
          </button>
          <a-empty
            v-if="!getConversationsLoading && sortedConversations.length === 0"
            :description="t('space.emptyConversations')"
          />
        </div>
        <conversation-chat-card
          v-if="activeConversation"
          :key="activeConversation.id"
          :agent="agent"
          :conversation="activeConversation"
          :start-fullscreen="true"
          @refresh="refreshConversations"
          @exit-fullscreen="closeMobileConversation"
        />
      </div>

      <!-- 桌面：会话聊天卡片网格 -->
      <div
        v-else-if="agentMatched && agent"
        class="grid min-w-0 gap-5 [grid-template-columns:repeat(auto-fill,minmax(min(100%,520px),1fr))]"
      >
        <conversation-chat-card
          v-for="conversation in sortedConversations"
          :key="conversation.id"
          :agent="agent"
          :conversation="conversation"
          @refresh="refreshConversations"
        />
      </div>
      <a-row v-if="paginator.total_page >= 2">
        <a-col
          v-if="paginator.current_page <= paginator.total_page"
          :span="24"
          align="center"
        >
          <a-space class="my-4">
            <a-spin />
            <div class="text-gray-400">{{ t('common.loading') }}</div>
          </a-space>
        </a-col>
        <a-col v-else :span="24" align="center">
          <div class="text-gray-400 my-4">{{ t('common.loaded') }}</div>
        </a-col>
      </a-row>
    </div>
  </a-spin>
</template>

<style scoped></style>
