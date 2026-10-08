<script setup lang="ts">
import moment from 'moment'
import { Message } from '@arco-design/web-vue'
import { useGetOpenServers } from '@/hooks/use-server'
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'

const CHINESE_DIGITS = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']

// 1.拉取网关列表
const { loading: getServersLoading, servers, loadOpenServers } = useGetOpenServers()

// 2.把 1 开始的序号转成中文，用于「网关一」「网关二」
const toChineseNumber = (value: number) => {
  if (value <= 0 || value >= 100) {
    return String(value)
  }
  if (value < 10) {
    return CHINESE_DIGITS[value]
  }
  if (value === 10) {
    return '十'
  }
  if (value < 20) {
    return `十${CHINESE_DIGITS[value % 10]}`
  }
  const tens = Math.floor(value / 10)
  const ones = value % 10
  return `${CHINESE_DIGITS[tens]}十${ones === 0 ? '' : CHINESE_DIGITS[ones]}`
}

// 3.把时间戳格式化成可读时间，空值显示为 -
const formatTimestamp = (timestamp: number | null) => {
  if (!timestamp) {
    return '-'
  }
  return moment(timestamp * 1000).format('YYYY-MM-DD HH:mm')
}

// 4.把网关地址或密钥写入剪贴板
const copyValue = async (value: string) => {
  try {
    await navigator.clipboard.writeText(value)
    Message.success('已复制')
  } catch (err) {
    Message.error(String(err))
  }
}

// 5.进入页面后加载网关列表
loadOpenServers().catch(() => undefined)
</script>

<template>
  <div
    class="flex h-full min-h-screen w-full flex-col overflow-hidden bg-gray-100 bg-cover bg-center bg-no-repeat px-6"
    :style="{ backgroundImage: `url(${AssistantAgentBackground})` }"
  >
    <div class="mb-6 pt-6">
      <div class="text-lg font-medium text-gray-900">频道服务</div>
    </div>
    <a-spin :loading="getServersLoading" class="block min-h-0 w-full flex-1 overflow-auto">
      <div v-if="servers.length" class="flex flex-col gap-5 pb-6">
        <a-card
          v-for="(item, index) in servers"
          :key="item.id"
          class="rounded-lg"
          :title="`网关${toChineseNumber(index + 1)}`"
        >
          <a-descriptions :column="1" bordered>
            <a-descriptions-item label="网关地址">
              <div class="flex min-w-0 items-center gap-1">
                <div class="min-w-0 flex-1 break-all" :title="item.gateway_url">
                  {{ item.gateway_url }}
                </div>
                <a-button
                  type="text"
                  size="mini"
                  class="!h-5 !w-5 flex-shrink-0 !text-gray-400"
                  title="复制"
                  :disabled="!item.gateway_url"
                  @click="copyValue(item.gateway_url)"
                >
                  <template #icon>
                    <icon-copy />
                  </template>
                </a-button>
              </div>
            </a-descriptions-item>
            <a-descriptions-item label="网关密钥">
              <div class="flex min-w-0 items-center gap-1">
                <div class="min-w-0 flex-1 break-all" :title="item.gateway_key">
                  {{ item.gateway_key }}
                </div>
                <a-button
                  type="text"
                  size="mini"
                  class="!h-5 !w-5 flex-shrink-0 !text-gray-400"
                  title="复制"
                  :disabled="!item.gateway_key"
                  @click="copyValue(item.gateway_key)"
                >
                  <template #icon>
                    <icon-copy />
                  </template>
                </a-button>
              </div>
            </a-descriptions-item>
            <a-descriptions-item label="更新时间">
              {{ formatTimestamp(item.updated_at) }}
            </a-descriptions-item>
            <a-descriptions-item label="创建时间">
              {{ formatTimestamp(item.created_at) }}
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
      </div>
      <a-empty
        v-else-if="!getServersLoading"
        description="暂无网关"
        class="flex h-[400px] flex-col items-center justify-center"
      />
    </a-spin>
  </div>
</template>

<style scoped></style>
