<script setup lang="ts">
import { computed } from 'vue'
import CodeHighLight from '@/components/CodeHighLight.vue'
import { currentOpenapiExamples } from '@/views/openapi/quick-start'
import { useI18n } from 'vue-i18n'
import { t } from '@/locales'

const { locale } = useI18n()
const examples = computed(() => {
  locale.value
  return currentOpenapiExamples()
})
</script>

<template>
  <div class="pb-6">
    <div class="bg-white p-6 rounded-lg h-[calc(100vh-160px)] overflow-scroll scrollbar-w-none">
      <h2 class="text-base text-gray-700 font-bold mb-4">{{ t('openapi.overview') }}</h2>
      <p class="text-gray-700 mb-4">{{ t('openapi.overviewBody') }}</p>
      <h2 class="text-base text-gray-900 font-bold mb-4">{{ t('openapi.preparation') }}</h2>
      <p class="text-gray-700 mb-4">{{ t('openapi.preparationBody') }}</p>
      <h2 class="text-base text-gray-900 font-bold mb-4">{{ t('openapi.basicUsage') }}</h2>
      <a-tabs type="text">
        <a-tab-pane key="block" :title="t('openapi.blockingChat')">
          <p class="text-gray-700 mb-4">{{ t('openapi.curl') }}</p>
          <code-high-light language="shell">{{ examples.blockShell }}</code-high-light>
          <p class="text-gray-700 mb-4">{{ t('openapi.sampleResult') }}</p>
          <code-high-light language="json">{{ examples.blockOutput }}</code-high-light>
        </a-tab-pane>
        <a-tab-pane key="stream" :title="t('openapi.streamingChat')">
          <p class="text-gray-700 mb-4">{{ t('openapi.curl') }}</p>
          <code-high-light language="shell">{{ examples.streamShell }}</code-high-light>
          <p class="text-gray-700 mb-4">{{ t('openapi.sampleResult') }}</p>
          <code-high-light language="json">{{ examples.streamOutput }}</code-high-light>
        </a-tab-pane>
      </a-tabs>
    </div>
  </div>
</template>

<style scoped></style>
