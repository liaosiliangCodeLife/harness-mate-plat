<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Agent } from '@/models/agent'
import CreateAgentModal from '@/views/space/apps/components/CreateAgentModal.vue'
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'
import { useAccountStore } from '@/stores/account'
import { t } from '@/locales'

const route = useRoute()
const router = useRouter()
const accountStore = useAccountStore()
const accountAvatarFailed = ref(false)
const isMobile = ref(false)
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

let mobileMedia: MediaQueryList | null = null
const syncIsMobile = () => {
  isMobile.value = Boolean(mobileMedia?.matches)
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
    class="flex h-full min-h-screen w-full min-w-0 max-w-full flex-col overflow-hidden bg-gray-100 bg-cover bg-center bg-no-repeat px-3 sm:px-6"
    :style="{ backgroundImage: `url(${AssistantAgentBackground})` }"
  >
    <div class="sticky top-0 z-20 pt-3 sm:pt-6">
      <!-- 顶层标题 -->
      <div class="mb-4 flex flex-wrap items-center justify-between gap-2 sm:mb-6">
        <!-- 左侧标题 -->
        <div class="flex min-w-0 items-center gap-2">
          <a-avatar
            :size="32"
            class="bg-blue-700"
            :image-url="accountAvatar || undefined"
            @error="accountAvatarFailed = true"
          >
            <span v-if="accountStore.account?.name">{{ accountStore.account.name[0] }}</span>
            <icon-user v-else :size="18" />
          </a-avatar>
          <div class="truncate text-lg font-medium text-gray-900 sm:text-2xl">{{ t('space.title') }}</div>
        </div>
        <!-- 创建按钮 -->
        <a-button
          v-if="isAgentListPage"
          type="primary"
          class="rounded-lg"
          :size="isMobile ? 'small' : 'medium'"
          @click="openCreateAgent"
        >
          {{ t('space.createAgent') }}
        </a-button>
      </div>
      <!-- 导航按钮+搜索框 -->
      <div class="mb-4 flex flex-col gap-2 sm:mb-6 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
        <!-- 左侧导航：窄屏横向滚动 -->
        <div class="max-w-full overflow-x-auto whitespace-nowrap">
          <div class="inline-flex items-center gap-2">
            <router-link
              to="/space/apps"
              class="rounded-lg px-3 h-8 text-xs leading-8 text-gray-700 transition-all hover:bg-gray-200 sm:text-sm"
              active-class="bg-gray-100"
            >
              {{ t('space.hermesAgent') }}
            </router-link>
            <router-link
              to="/space/deepseek-harness"
              class="rounded-lg px-3 h-8 text-xs leading-8 text-gray-700 transition-all hover:bg-gray-200 sm:text-sm"
              active-class="bg-gray-100"
            >
              {{ t('space.deepseekAgent') }}
            </router-link>
          </div>
        </div>
        <!-- 右侧搜索，仅智能体列表需要 -->
        <a-input-search
          v-if="isAgentListPage"
          v-model="searchWord"
          :placeholder="t('space.searchPlaceholder')"
          class="w-full bg-white rounded-lg border-gray-300 sm:w-[240px]"
          @search="search"
        />
      </div>
    </div>
    <!-- 中间内容 -->
    <div class="min-h-0 min-w-0 w-full flex-1 p-0 sm:p-0">
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
