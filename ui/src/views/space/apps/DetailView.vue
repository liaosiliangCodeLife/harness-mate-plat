<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useGetAgentConversations } from '@/hooks/use-agent'
import ConversationChatCard from '@/views/space/apps/components/ConversationChatCard.vue'
import {
  conversationListVersionKey,
  detailAgentKey,
} from '@/views/space/apps/detail-agent'

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

const agentId = computed(() => String(route.params?.agent_id ?? ''))
const agentMatched = computed(() => Boolean(agent.value && agent.value.id === agentId.value))
// 首屏转圈；翻页时只在底部提示，避免盖住已经连上的聊天卡片
const pageLoading = computed(
  () =>
    !agentMatched.value ||
    (getConversationsLoading.value && conversations.value.length === 0),
)

// 2.置顶会话排在前面，同组内保持接口返回顺序
const sortedConversations = computed(() => {
  return [...conversations.value].sort((left, right) => right.pinned - left.pinned)
})

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
</script>

<template>
  <a-spin
    :loading="pageLoading"
    class="block h-full w-full scrollbar-w-none overflow-scroll"
    @scroll="handleScroll"
  >
    <div class="p-6">
      <!-- 会话聊天卡片，宽度足够时每行 2 个 -->
      <div
        v-if="agentMatched && agent"
        class="grid gap-5 [grid-template-columns:repeat(auto-fill,minmax(min(100%,520px),1fr))]"
      >
        <conversation-chat-card
          v-for="conversation in sortedConversations"
          :key="conversation.id"
          :agent="agent"
          :conversation="conversation"
          @refresh="refreshConversations"
        />
      </div>
      <a-empty
        v-if="agentMatched && !getConversationsLoading && conversations.length === 0"
        description="暂无会话"
        class="h-[400px] flex flex-col items-center justify-center"
      />
      <a-row v-if="paginator.total_page >= 2">
        <a-col
          v-if="paginator.current_page <= paginator.total_page"
          :span="24"
          align="center"
        >
          <a-space class="my-4">
            <a-spin />
            <div class="text-gray-400">加载中</div>
          </a-space>
        </a-col>
        <a-col v-else :span="24" align="center">
          <div class="text-gray-400 my-4">数据已加载完成</div>
        </a-col>
      </a-row>
    </div>
  </a-spin>
</template>

<style scoped></style>
