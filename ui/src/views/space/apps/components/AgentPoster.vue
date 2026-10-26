<script setup lang="ts">
/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //智能体海报：居中的衬线大字和一行灰色说明
 * @File: AgentPoster.vue
 * @Time: 2026/10/26 12:48:00
 * @All Rights Reserve By Brtc
 */
import { computed } from 'vue'

const props = defineProps({
  agentType: { type: String, default: '' },
  size: { type: String, default: 'large' },
})

/*
 * @Author Leon-liao
 * @Function: posterTitle
 * @Description //按智能体类型生成海报大字，不带 @ 前缀
 * @Date :2026/10/26 12:48:00
 * @Param: 无。类型取自 props.agentType
 * @return：HERMES 为 HERMES AGENT，DEEPSEEK_HARNESS 为 DEEPSEEK AGENT，其它为类型原值
 */
const posterTitle = computed(() => {
  const agentType = props.agentType ?? ''
  if (agentType === 'HERMES') {
    return 'HERMES AGENT'
  }
  if (agentType === 'DEEPSEEK_HARNESS') {
    return 'DEEPSEEK AGENT'
  }
  return agentType
})

/*
 * @Author Leon-liao
 * @Function: posterSubtitle
 * @Description //按智能体类型生成海报说明，未知类型不显示
 * @Date :2026/10/26 12:48:00
 * @Param: 无。类型取自 props.agentType
 * @return：两种已知类型的中文说明；其它类型返回空字符串
 */
const posterSubtitle = computed(() => {
  const agentType = props.agentType ?? ''
  if (agentType === 'HERMES') {
    return '提个问题、贴出错误，或指向仓库。我能读代码、运行工具，帮你完成交付。'
  }
  if (agentType === 'DEEPSEEK_HARNESS') {
    return '提出需求、贴出报错，或描述目标。我会拆解步骤、编写代码、运行工具，帮你完成任务。'
  }
  return ''
})
</script>

<template>
  <div class="agent-poster" :class="{ 'agent-poster--small': size === 'small' }">
    <div class="agent-poster-word">{{ posterTitle }}</div>
    <div v-if="posterSubtitle" class="agent-poster-note">{{ posterSubtitle }}</div>
  </div>
</template>

<style scoped>
.agent-poster {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  padding: 0 40px;
  text-align: center;
  pointer-events: none;
}

.agent-poster-word {
  max-width: 100%;
  color: #1b4df5;
  font-family: 'Didot', 'Bodoni MT', 'Playfair Display', 'Times New Roman', Georgia, serif;
  font-size: clamp(56px, 9vw, 150px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 0.95;
  word-break: break-word;
  text-transform: uppercase;
  opacity: 1;
}

.agent-poster-note {
  max-width: 100%;
  color: #94a3b8;
  font-size: 15px;
  line-height: 1.6;
}

.agent-poster--small {
  gap: 6px;
  padding: 0 12px;
}

.agent-poster--small .agent-poster-word {
  font-size: 60px;
  letter-spacing: 0;
  line-height: 1.4;
  opacity: 1;
}

.agent-poster--small .agent-poster-note {
  font-size: 11px;
  line-height: 1.5;
}
</style>
