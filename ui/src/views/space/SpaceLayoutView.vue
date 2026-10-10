<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Agent } from '@/models/agent'
import CreateAgentModal from '@/views/space/apps/components/CreateAgentModal.vue'
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'
import { useAccountStore } from '@/stores/account'

const route = useRoute()
const router = useRouter()
const accountStore = useAccountStore()
const accountAvatarFailed = ref(false)
const accountAvatar = computed(() => {
  if (accountAvatarFailed.value) {
    return ''
  }
  return String(accountStore.account?.avatar ?? '').trim()
})

watch(
  () => accountStore.account?.avatar,
  () => {
    accountAvatarFailed.value = false
  },
)
const searchWord = ref(route.query?.search_word || '')
const createAgentModalVisible = ref(false)
const editingAgent = ref<Agent | null>(null)
const agentListVersion = ref(0)

// 打开新建弹窗前清掉编辑对象，避免沿用上一次的编辑态
const openCreateAgent = () => {
  editingAgent.value = null
  createAgentModalVisible.value = true
}

// 列表卡片的编辑入口：带上智能体后复用同一个弹窗
const openEditAgent = (agent: Agent) => {
  editingAgent.value = agent
  createAgentModalVisible.value = true
}

const isAgentListPage = computed(
  () => route.path.startsWith('/space/apps') || route.path.startsWith('/space/deepseek-harness'),
)
const currentAgentType = computed(() =>
  route.path.startsWith('/space/deepseek-harness') ? 'DEEPSEEK_HARNESS' : 'HERMES',
)

// 只在智能体列表页监听编辑事件
const listListeners = computed(() => {
  if (route.name !== 'space-apps-list' && route.name !== 'space-deepseek-harness') {
    return {}
  }
  return {
    'edit-agent': openEditAgent,
  }
})

// 绑定输入框的搜索事件
const search = (value: string) => {
  router.push({
    path: route.path,
    query: {
      search_word: value,
    },
  })
}

// 监听路由里的search_word变化
watch(
  () => route.query?.search_word,
  () => {
    searchWord.value = route.query?.search_word || ''
  },
)
</script>

<template>
  <!-- 调整边距+隐藏 -->
  <div
    class="px-6 flex flex-col overflow-hidden h-full w-full min-h-screen bg-gray-100 bg-cover bg-no-repeat bg-center"
    :style="{ backgroundImage: `url(${AssistantAgentBackground})` }"
  >
    <div class="pt-6 sticky top-0 z-20">
      <!-- 顶层标题 -->
      <div class="flex items-center justify-between mb-6">
        <!-- 左侧标题 -->
        <div class="flex items-center gap-2">
          <a-avatar
            :size="32"
            class="bg-blue-700"
            :image-url="accountAvatar || undefined"
            @error="accountAvatarFailed = true"
          >
            <span v-if="accountStore.account?.name">{{ accountStore.account.name[0] }}</span>
            <icon-user v-else :size="18" />
          </a-avatar>
          <div class="text-lg font-medium text-gray-900">个人空间</div>
        </div>
        <!-- 创建按钮 -->
        <a-button
          v-if="isAgentListPage"
          type="primary"
          class="rounded-lg"
          @click="openCreateAgent"
        >
          创建智能体
        </a-button>
      </div>
      <!-- 导航按钮+搜索框 -->
      <div class="flex items-center justify-between mb-6">
        <!-- 左侧导航 -->
        <div class="flex items-center gap-2">
          <router-link
            to="/space/apps"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            Hermes智能体
          </router-link>
          <router-link
            to="/space/deepseek-harness"
            class="rounded-lg text-gray-700 px-3 h-8 leading-8 hover:bg-gray-200 transition-all"
            active-class="bg-gray-100"
          >
            DeepSeekHarness智能体
          </router-link>
        </div>
        <!-- 右侧搜索，仅智能体列表需要 -->
        <a-input-search
          v-if="isAgentListPage"
          v-model="searchWord"
          placeholder="输入关键词进行搜索"
          class="w-[240px] bg-white rounded-lg border-gray-300"
          @search="search"
        />
      </div>
    </div>
    <!-- 中间内容 -->
    <div class="flex-1 min-h-0">
      <router-view v-slot="{ Component }">
        <component
          :is="Component"
          :key="route.path"
          :list-version="agentListVersion"
          v-on="listListeners"
        />
      </router-view>
    </div>
    <!-- 创建智能体模态窗 -->
    <create-agent-modal
      v-model:visible="createAgentModalVisible"
      :agent="editingAgent"
      :agent-type="currentAgentType"
      :callback="() => (agentListVersion += 1)"
    />
  </div>
</template>

<style scoped></style>
