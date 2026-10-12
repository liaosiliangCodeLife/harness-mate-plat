<script setup lang="ts">
import { type PropType, ref } from 'vue'
import { QueueEvent } from '@/config'
import { t } from '@/locales'

// 1.定义自定义组件所需数据
const props = defineProps({
  loading: { type: Boolean, default: false, required: true },
  agent_thoughts: {
    type: Array as PropType<Record<string, any>[]>,
    default: () => [],
    required: true,
  },
})
const visible = ref(false)
</script>

<template>
  <!-- 智能体推理步骤 -->
  <div :class="`flex flex-col rounded-2xl border ${visible ? 'w-[320px]' : 'w-[180px]'}`">
    <div
      :class="`flex items-center justify-between h-10 rounded-2xl bg-gray-100 px-4 text-gray-700 cursor-pointer w-auto ${visible ? 'rounded-bl-none rounded-br-none' : ''}`"
      @click="visible = !visible"
    >
      <!-- 左侧图标与标题 -->
      <div class="flex items-center gap-2">
        <icon-list />
        {{ t('agentThought.toggle', { action: visible ? t('agentThought.hide') : t('agentThought.show') }) }}
      </div>
      <!-- 右侧图标 -->
      <div class="">
        <template v-if="props.loading">
          <icon-loading />
        </template>
        <template v-else>
          <icon-up v-if="visible" />
          <icon-down v-else />
        </template>
      </div>
    </div>
    <!-- 底部内容 -->
    <a-collapse class="agent-thought" v-if="visible" destroy-on-hide :bordered="false">
      <a-collapse-item
        v-for="agent_thought in props.agent_thoughts.filter((item: any) =>
          [
            QueueEvent.longTermMemoryRecall,
            QueueEvent.agentThought,
            QueueEvent.datasetRetrieval,
            QueueEvent.agentAction,
            QueueEvent.agentMessage,
          ].includes(item.event),
        )"
        :key="agent_thought.id"
      >
        <template #expand-icon>
          <icon-file v-if="agent_thought.event === QueueEvent.longTermMemoryRecall" />
          <icon-language v-else-if="agent_thought.event === QueueEvent.agentThought" />
          <icon-storage v-else-if="agent_thought.event === QueueEvent.datasetRetrieval" />
          <icon-tool v-else-if="agent_thought.event === QueueEvent.agentAction" />
          <icon-message v-else-if="agent_thought.event === QueueEvent.agentMessage" />
        </template>
        <template #header>
          <div class="text-gray-700" v-if="agent_thought.event === QueueEvent.longTermMemoryRecall">
            {{ t('agentThought.memory') }}
          </div>
          <div class="text-gray-700" v-if="agent_thought.event === QueueEvent.agentThought">
            {{ t('agentThought.reasoning') }}
          </div>
          <div class="text-gray-700" v-if="agent_thought.event === QueueEvent.datasetRetrieval">
            {{ t('agentThought.retrieval') }}
          </div>
          <div class="text-gray-700" v-if="agent_thought.event === QueueEvent.agentAction">
            {{ t('agentThought.tool') }}
          </div>
          <div class="text-gray-700" v-if="agent_thought.event === QueueEvent.agentMessage">
            {{ t('agentThought.message') }}
          </div>
        </template>
        <template #extra>
          <div class="text-gray-500">{{ agent_thought.latency.toFixed(2) }}s</div>
        </template>
        <div
          v-if="['agent_thought', 'agent_message'].includes(agent_thought.event)"
          class="text-xs text-gray-500 line-clamp-4 break-all"
        >
          {{ agent_thought.thought || '-' }}
        </div>
        <div v-else class="text-xs text-gray-500 line-clamp-4 break-all">
          {{ agent_thought.observation || '-' }}
        </div>
      </a-collapse-item>
    </a-collapse>
  </div>
</template>

<style>
.agent-thought {
  .arco-collapse-item-content {
    padding: 0 16px;
  }
}
</style>
