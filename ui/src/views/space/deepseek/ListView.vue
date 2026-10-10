<script setup lang="ts">
import AgentListView from '@/views/space/apps/components/AgentListView.vue'

const props = defineProps({
  listVersion: { type: Number, default: 0 },
})
const emits = defineEmits(['edit-agent'])
</script>

<template>
  <agent-list-view
    agent-type="DEEPSEEK_HARNESS"
    :list-version="props.listVersion"
    @edit-agent="(agent) => emits('edit-agent', agent)"
  />
</template>
