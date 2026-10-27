<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useLogout } from '@/hooks/use-auth'
import LayoutSidebar from './components/LayoutSidebar.vue'
import { useGetCurrentUser } from '@/hooks/use-account'
import { useCredentialStore } from '@/stores/credential'
import { useAccountStore } from '@/stores/account'
import SettingModal from '@/views/layouts/components/SettingModal.vue'
import { setLocale, t, type AppLocale } from '@/locales'
import { useI18n } from 'vue-i18n'

// 1.定义页面所需数据
const settingModalVisible = ref(false)
const sidebarDrawerVisible = ref(false)
const isMobile = ref(false)
const { locale } = useI18n()
const router = useRouter()
const credentialStore = useCredentialStore()
const accountStore = useAccountStore()
const { handleLogout: handleLogoutHook } = useLogout()
const { current_user, loadCurrentUser } = useGetCurrentUser()
const avatarLoadFailed = ref(false)
const githubStars = ref<number | null>(null)
const accountAvatar = computed(() => {
  if (avatarLoadFailed.value) {
    return ''
  }
  return String(accountStore.account?.avatar ?? '').trim()
})

watch(
  () => accountStore.account?.avatar,
  () => {
    avatarLoadFailed.value = false
  },
)

const toggleLanguage = () => {
  const next: AppLocale = locale.value === 'en-US' ? 'zh-CN' : 'en-US'
  setLocale(next)
}

// 2.退出登录按钮
const handleLogout = async () => {
  // 2.1 发起请求退出登录
  await handleLogoutHook()

  // 2.2 清空授权凭证+账号信息
  credentialStore.clear()
  accountStore.clear()

  // 2.3 跳转到授权认证页面
  await router.replace({ name: 'auth-login' })
}

const closeSidebarDrawer = () => {
  sidebarDrawerVisible.value = false
}

/** 抽屉内点到导航链接时关闭；账号下拉不走这里，避免抢点击 */
const onDrawerNavClick = (event: MouseEvent) => {
  const target = event.target
  if (!(target instanceof Element)) {
    return
  }
  if (target.closest('a')) {
    closeSidebarDrawer()
  }
}

// 窄屏监听：<768px 折叠侧栏，改用顶栏 + 抽屉
let mobileMedia: MediaQueryList | null = null
const syncIsMobile = () => {
  isMobile.value = Boolean(mobileMedia?.matches)
  if (!isMobile.value) {
    sidebarDrawerVisible.value = false
  }
}

// 3.页面DOM加载完成时获取当前登录账号信息
onMounted(async () => {
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    mobileMedia = window.matchMedia('(max-width: 767px)')
    syncIsMobile()
    mobileMedia.addEventListener('change', syncIsMobile)
  }
  await loadCurrentUser()
  accountStore.update(current_user.value)
})

onUnmounted(() => {
  mobileMedia?.removeEventListener('change', syncIsMobile)
  mobileMedia = null
})

// 4.页面挂载时获取 GitHub 仓库 star 数，失败时不展示
onMounted(async () => {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 5000)
  try {
    const response = await fetch(
      'https://api.github.com/repos/liaosiliangCodeLife/harness-mate-plat',
      { signal: controller.signal },
    )
    if (!response.ok) {
      return
    }
    const data: unknown = await response.json()
    const count =
      data !== null && typeof data === 'object' && 'stargazers_count' in data
        ? (data as { stargazers_count?: unknown }).stargazers_count
        : undefined
    if (typeof count === 'number' && Number.isFinite(count)) {
      githubStars.value = count
    }
  } catch {
    // 请求失败、超时或响应异常时保持原「GitHub」文案
  } finally {
    window.clearTimeout(timer)
  }
})
</script>

<template>
  <a-layout :has-sider="!isMobile" class="h-full w-full min-w-0">
    <!-- 手机顶栏：汉堡 + 头像 -->
    <div
      v-if="isMobile"
      class="flex h-12 flex-shrink-0 items-center justify-between border-b border-gray-200 bg-white px-3"
    >
      <a-button type="text" class="!text-gray-700" @click="sidebarDrawerVisible = true">
        <template #icon>
          <icon-menu />
        </template>
      </a-button>
      <a-avatar
        :size="28"
        class="text-sm bg-blue-700"
        :image-url="accountAvatar || undefined"
        @error="avatarLoadFailed = true"
        @click="sidebarDrawerVisible = true"
      >
        {{ accountStore.account.name?.[0] }}
      </a-avatar>
    </div>

    <!-- 桌面侧边栏 -->
    <a-layout-sider
      v-if="!isMobile"
      :width="240"
      class="min-h-screen bg-gray-50 p-2 shadow-none"
    >
      <div class="bg-white h-full rounded-lg px-2 py-4 flex flex-col justify-between">
        <div class="">
          <a
            href="https://github.com/liaosiliangCodeLife/harness-mate-plat"
            target="_blank"
            rel="noopener noreferrer"
            :title="t('layout.githubRepo')"
            class="mb-5 flex h-9 w-[128px] items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-gray-200 text-sm text-gray-600 transition-all hover:bg-gray-300 hover:text-gray-800"
          >
            <icon-github :size="16" />
            GitHub<template v-if="githubStars !== null"> ★ {{ githubStars }}</template>
          </a>
          <layout-sidebar />
        </div>
        <a-dropdown position="tl">
          <div
            class="flex items-center p-2 gap-2 transition-all cursor-pointer rounded-lg hover:bg-gray-100"
          >
            <a-avatar
              :size="32"
              class="text-sm bg-blue-700"
              :image-url="accountAvatar || undefined"
              @error="avatarLoadFailed = true"
            >
              {{ accountStore.account.name?.[0] }}
            </a-avatar>
            <div class="flex flex-col">
              <div class="text-sm text-gray-900">{{ accountStore.account.name }}</div>
              <div class="text-xs text-gray-500">{{ accountStore.account.email }}</div>
            </div>
          </div>
          <template #content>
            <a-doption @click="settingModalVisible = true">
              <template #icon>
                <icon-settings />
              </template>
              {{ t('layout.accountSettings') }}
            </a-doption>
            <a-doption @click="toggleLanguage">
              <template #icon>
                <icon-language />
              </template>
              {{ t('layout.switchLanguage') }}
            </a-doption>
            <a-doption @click="handleLogout">
              <template #icon>
                <icon-poweroff />
              </template>
              {{ t('layout.signOut') }}
            </a-doption>
          </template>
        </a-dropdown>
      </div>
    </a-layout-sider>

    <!-- 手机侧栏抽屉 -->
    <a-drawer
      v-model:visible="sidebarDrawerVisible"
      placement="left"
      :width="260"
      :footer="false"
      unmount-on-close
    >
      <div class="flex h-full flex-col justify-between py-2" @click="onDrawerNavClick">
        <div>
          <a
            href="https://github.com/liaosiliangCodeLife/harness-mate-plat"
            target="_blank"
            rel="noopener noreferrer"
            :title="t('layout.githubRepo')"
            class="mb-5 flex h-9 w-[128px] items-center justify-center gap-2 whitespace-nowrap rounded-lg bg-gray-200 text-sm text-gray-600 transition-all hover:bg-gray-300 hover:text-gray-800"
          >
            <icon-github :size="16" />
            GitHub<template v-if="githubStars !== null"> ★ {{ githubStars }}</template>
          </a>
          <layout-sidebar />
        </div>
        <a-dropdown position="tl">
          <div
            class="flex items-center p-2 gap-2 transition-all cursor-pointer rounded-lg hover:bg-gray-100"
          >
            <a-avatar
              :size="32"
              class="text-sm bg-blue-700"
              :image-url="accountAvatar || undefined"
              @error="avatarLoadFailed = true"
            >
              {{ accountStore.account.name?.[0] }}
            </a-avatar>
            <div class="flex min-w-0 flex-col">
              <div class="truncate text-sm text-gray-900">{{ accountStore.account.name }}</div>
              <div class="truncate text-xs text-gray-500">{{ accountStore.account.email }}</div>
            </div>
          </div>
          <template #content>
            <a-doption
              @click="
                () => {
                  settingModalVisible = true
                  closeSidebarDrawer()
                }
              "
            >
              <template #icon>
                <icon-settings />
              </template>
              {{ t('layout.accountSettings') }}
            </a-doption>
            <a-doption @click="toggleLanguage">
              <template #icon>
                <icon-language />
              </template>
              {{ t('layout.switchLanguage') }}
            </a-doption>
            <a-doption @click="handleLogout">
              <template #icon>
                <icon-poweroff />
              </template>
              {{ t('layout.signOut') }}
            </a-doption>
          </template>
        </a-dropdown>
      </div>
    </a-drawer>

    <!-- 右侧内容 -->
    <a-layout-content class="min-w-0 w-full">
      <router-view />
    </a-layout-content>
    <!-- 设置模态窗 -->
    <setting-modal v-model:visible="settingModalVisible" />
  </a-layout>
</template>

<style scoped></style>
