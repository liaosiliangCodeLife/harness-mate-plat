<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { Agent } from '@/models/agent'

// 1.定义弹窗所需数据：bot_key 取智能体的 gateway_key
const props = defineProps({
  visible: { type: Boolean, default: false, required: true },
  agent: { type: Object as PropType<Agent | null>, default: null },
})
const emits = defineEmits(['update:visible'])
const rows = computed(() => [
  { label: 'bot_id', value: props.agent?.bot_id?.trim() ?? '' },
  { label: 'bot_key', value: props.agent?.gateway_key?.trim() ?? '' },
])

// 2.关闭弹窗
const hideModal = () => {
  emits('update:visible', false)
}

// 3.复制 bot_id 或 bot_key
const copyValue = async (value: string) => {
  try {
    await navigator.clipboard.writeText(value)
    Message.success('已复制')
  } catch (err) {
    Message.error(String(err))
  }
}
</script>

<template>
  <a-modal
    :visible="props.visible"
    :width="480"
    hide-title
    align-center
    modal-class="pair-hermes-modal"
    @cancel="hideModal"
  >
    <div class="mb-6 flex items-start justify-between gap-3">
      <div>
        <div class="pair-hermes-title">
          配对 <span class="pair-hermes-accent">Hermes</span>
        </div>
        <p class="pair-hermes-subtitle">把这组标识填进 Hermes 端即可完成配对</p>
      </div>
      <a-button type="text" size="small" class="!text-gray-400" @click="hideModal">
        <template #icon>
          <icon-close />
        </template>
      </a-button>
    </div>
    <div class="flex flex-col gap-5">
      <div v-for="row in rows" :key="row.label" class="flex items-center gap-4">
        <div class="w-20 flex-shrink-0 text-sm leading-5 text-gray-500">{{ row.label }}</div>
        <div
          class="min-w-0 flex-1 truncate select-text text-sm leading-5 text-gray-800"
          :title="row.value || '-'"
        >
          {{ row.value || '-' }}
        </div>
        <a-button
          size="small"
          type="outline"
          class="pair-copy-btn flex-shrink-0"
          :disabled="!row.value"
          @click="copyValue(row.value)"
        >
          复制
        </a-button>
      </div>
    </div>
    <template #footer>
      <a-button class="pair-close-btn" @click="hideModal">关闭</a-button>
    </template>
  </a-modal>
</template>

<style scoped>
:deep(.arco-modal) {
  border-radius: 22px;
  overflow: hidden;
}
:global(.pair-hermes-modal.arco-modal) {
  border-radius: 22px;
  overflow: hidden;
}
.pair-hermes-title {
  font-size: 23px;
  font-weight: 700;
  line-height: 1.3;
  color: #1d2129;
  letter-spacing: 0.4px;
}
.pair-hermes-accent {
  color: #165dff;
}
.pair-hermes-subtitle {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.5;
  color: #86909c;
}
.pair-copy-btn,
.pair-close-btn {
  border-radius: 10px;
}
</style>
