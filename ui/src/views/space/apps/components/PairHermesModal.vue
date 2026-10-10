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

/*
 * @Author Leon-liao
 * @Function: installCommand
 * @Description //拼出可直接粘贴到终端执行的插件安装指令，身份已填入当前智能体，网关地址仍用占位符
 * @Date :2026/10/08 11:30:00
 * @Param: 无。凭据取自 props.agent：bot_id 用 agent.bot_id，bot_key 用 agent.gateway_key
 * @return：多行安装指令；任一凭据为空时返回空字符串
 */
const installCommand = computed(() => {
  const botId = props.agent?.bot_id?.trim() ?? ''
  const botKey = props.agent?.gateway_key?.trim() ?? ''
  if (!botId || !botKey) {
    return ''
  }
  return [
    '# 1) 装插件（一条命令，插件在仓库 plugin/hermes 子目录）：',
    'hermes plugins install liaosiliangCodeLife/harness-mate-plat/plugin/hermes --yes-deps --enable',
    '',
    '# 2) 写入身份到 ~/.hermes/.env：',
    "cat >> ~/.hermes/.env <<'EOF'",
    `HARNESS_MATE_BOT_ID=${botId}`,
    `HARNESS_MATE_BOT_KEY=${botKey}`,
    '# 默认放行所有 peer（如需收紧再配 HARNESS_MATE_ALLOWED_PEERS）',
    'HARNESS_MATE_DM_POLICY=open',
    'HARNESS_MATE_ALLOW_ALL_DEVICES=1',
    'EOF',
    '',
    '# 3) 确认网关地址：打开 ~/.hermes/plugins/HarnessMate/adapter.py 第 62 行 WS_GATEWAY_WS_URL，应为平台自己的网关地址（形如 wss://<平台域名>:<端口>/ws）。',
    '',
    '# 4) 重启并验证：hermes gateway restart；日志出现「harness_mate 已连接 WS 网关」即成功，回平台进智能体发一条消息能收到回复即端到端打通。',
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
    Message.success('已复制')
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
    Message.success('已复制')
  } catch {
    return
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
        <p class="pair-hermes-subtitle">点下方按钮复制安装指令，粘贴到本机终端执行即可完成配对</p>
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
      <a-button
        size="small"
        type="outline"
        long
        class="pair-copy-btn"
        :disabled="!installCommand"
        @click="copyInstallCommand"
      >
        一键复制安装指令
      </a-button>
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
