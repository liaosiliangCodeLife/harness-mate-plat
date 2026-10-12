<script setup lang="ts">
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'
import { t } from '@/locales'
</script>

<template>
  <!-- 业务对接展示页 -->
  <div
    class="px-6 flex flex-col overflow-hidden h-full w-full min-h-screen bg-gray-100 bg-cover bg-no-repeat bg-center"
    :style="{ backgroundImage: `url(${AssistantAgentBackground})` }"
  >
    <div class="pt-6 sticky top-0 z-20">
      <!-- 顶层标题 -->
      <div class="flex items-center mb-6">
        <div class="flex items-center gap-2">
          <a-avatar :size="32" class="bg-blue-700">
            <icon-user :size="18" />
          </a-avatar>
          <div>
            <div class="text-lg font-medium text-gray-900">{{ t('openapi.title') }}</div>
            <div class="text-xs text-gray-500">{{ t('openapi.subtitle') }}</div>
          </div>
        </div>
      </div>
    </div>
    <!-- 联系方式与企业微信 -->
    <div class="flex-1 overflow-y-auto pb-6 flex flex-col gap-4">
      <div class="rounded-lg bg-white p-6">
        <div class="mb-4 text-base font-medium text-gray-900">{{ t('openapi.contact') }}</div>
        <div class="flex flex-col gap-2 text-sm">
          <div>
            <span class="text-gray-500">{{ t('openapi.email') }}</span>
            <span class="select-text text-gray-900">liaosiliang1234@126.com</span>
          </div>
          <div>
            <span class="text-gray-500">{{ t('openapi.phone') }}</span>
            <span class="select-text text-gray-900">13417329207</span>
          </div>
        </div>
      </div>
      <div class="rounded-lg bg-white p-6">
        <div class="mb-4 text-base font-medium text-gray-900">{{ t('openapi.wecom') }}</div>
        <img
          src="/wechat-card.png"
          :alt="t('openapi.wecomAlt')"
          class="h-80 w-auto rounded-lg border border-gray-200"
        />
        <div class="mt-3 text-xs text-gray-500">{{ t('openapi.wecomHint') }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
