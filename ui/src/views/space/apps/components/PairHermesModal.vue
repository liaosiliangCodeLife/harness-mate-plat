<script setup lang="ts">
import { computed, type PropType } from 'vue'
import { Message } from '@arco-design/web-vue'
import type { Agent } from '@/models/agent'
import { t } from '@/locales'

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

/*
 * @Author Leon-liao
 * @Function: installCommand
 * @Description //拼出可直接粘贴到终端执行的插件安装指令，身份已填入当前智能体，网关地址仍用占位符
 * @Date :2026/10/08 11:30:00
 * @Param: 无。凭据取自 props.agent：bot_id 用 agent.bot_id，bot_key 用 agent.gateway_key
 * @return：多行安装指令；任一凭据为空时返回空字符串
 */
const isDeepSeekHarness = computed(() => props.agent?.agent_type === 'DEEPSEEK_HARNESS')
const installCommand = computed(() => {
  const botId = props.agent?.bot_id?.trim() ?? ''
  const botKey = props.agent?.gateway_key?.trim() ?? ''
  if (!botId || !botKey) {
    return ''
  }
  if (isDeepSeekHarness.value) {
    return [
      t('home.pairDshStep1'),
      'git clone --depth 1 https://github.com/liaosiliangCodeLife/harness-mate-plat.git',
      'mkdir -p ~/Documents && mv harness-mate-plat/plugin/dsh ~/Documents/harness-mate',
      '',
      t('home.pairDshStep2'),
      `cd ~/Documents/harness-mate && chmod +x install.sh && ./install.sh ${botId} ${botKey}`,
      '',
      t('home.pairDshStep3'),
      '',
      t('home.pairDshStep4'),
      '',
    ].join('\n')
  }
  return [
    t('home.pairHermesStep1'),
    'hermes plugins install liaosiliangCodeLife/harness-mate-plat/plugin/hermes --yes-deps --enable',
    '',
    t('home.pairHermesStep2'),
    "cat >> ~/.hermes/.env <<'EOF'",
    `HARNESS_MATE_BOT_ID=${botId}`,
    `HARNESS_MATE_BOT_KEY=${botKey}`,
    t('home.pairHermesPeers'),
    'HARNESS_MATE_DM_POLICY=open',
    'HARNESS_MATE_ALLOW_ALL_DEVICES=1',
    'EOF',
    '',
    t('home.pairHermesStep3'),
    '',
    t('home.pairHermesStep4'),
    'hermes gateway restart',
    '',
  ].join('\n')
})

// 2.关闭弹窗
const hideModal = () => {
  emits('update:visible', false)
}

// 3.复制 bot_id 或 bot_key
const copyValue = async (value: string) => {
  try {
    await navigator.clipboard.writeText(value)
    Message.success(t('common.copied'))
  } catch (err) {
    Message.error(String(err))
  }
}

/*
 * @Author Leon-liao
 * @Function: copyInstallCommand()
 * @Description //把已填好当前智能体凭据的完整安装指令写入剪贴板
 * @Date :2026/10/08 11:30:00
 * @Param: 无。指令文本来自 installCommand
 * @return：成功时提示「已复制」；剪贴板失败时静默返回，不把异常抛到界面上
 */
const copyInstallCommand = async () => {
  const text = installCommand.value
  if (!text) {
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    Message.success(t('common.copied'))
  } catch {
    return
  }
}
</script>

<template>
  <a-modal
    :visible="props.visible"
    :width="'min(480px, calc(100vw - 32px))'"
    hide-title
    align-center
    modal-class="pair-hermes-modal"
    @cancel="hideModal"
  >
    <div class="mb-6 flex items-start justify-between gap-3">
      <div>
        <div class="pair-hermes-title">
          {{ t('home.pairTitle') }} <span class="pair-hermes-accent">{{ isDeepSeekHarness ? 'DeepSeek Harness' : 'Hermes' }}</span>
        </div>
        <p class="pair-hermes-subtitle">{{ t('home.pairSubtitle') }}</p>
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
          {{ t('common.copy') }}
        </a-button>
      </div>
      <a-button
        size="small"
        type="outline"
        long
        class="pair-copy-btn"
        :disabled="!installCommand"
        @click="copyInstallCommand"
      >
        {{ t('home.pairCopyAll') }}
      </a-button>
    </div>
    <template #footer>
      <a-button class="pair-close-btn" @click="hideModal">{{ t('common.close') }}</a-button>
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
