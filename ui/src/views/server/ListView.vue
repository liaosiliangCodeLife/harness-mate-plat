<script setup lang="ts">
import moment from 'moment'
import { Message } from '@arco-design/web-vue'
import { useGetOpenServers } from '@/hooks/use-server'
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'
import { i18n, t } from '@/locales'

const { loading: getServersLoading, servers, loadOpenServers } = useGetOpenServers()

const toChineseNumber = (value: number) => {
  const digits = t('server.digits')
  const ten = t('server.ten')
  if (value <= 0 || value >= 100) {
    return String(value)
  }
  if (value < 10) {
    return digits[value]
  }
  if (value === 10) {
    return ten
  }
  if (value < 20) {
    return `${ten}${digits[value % 10]}`
  }
  const tens = Math.floor(value / 10)
  const ones = value % 10
  return `${digits[tens]}${ten}${ones === 0 ? '' : digits[ones]}`
}

const gatewayTitle = (index: number) => {
  const value = index + 1
  const n = i18n.global.locale.value === 'zh-CN' ? toChineseNumber(value) : String(value)
  return t('server.gatewayTitle', { n })
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
    Message.success(t('common.copied'))
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
      <div class="text-lg font-medium text-gray-900">{{ t('server.title') }}</div>
    </div>
    <a-spin :loading="getServersLoading" class="block min-h-0 w-full flex-1 overflow-auto">
      <div v-if="servers.length" class="flex flex-col gap-5 pb-6">
        <a-card
          v-for="(item, index) in servers"
          :key="item.id"
          class="rounded-lg"
          :title="gatewayTitle(index)"
        >
          <a-descriptions :column="1" bordered>
            <a-descriptions-item :label="t('server.gatewayAddress')">
              <div class="flex min-w-0 items-center gap-1">
                <div class="min-w-0 flex-1 break-all" :title="item.gateway_url">
                  {{ item.gateway_url }}
                </div>
                <a-button
                  type="text"
                  size="mini"
                  class="!h-5 !w-5 flex-shrink-0 !text-gray-400"
                  :title="t('common.copy')"
                  :disabled="!item.gateway_url"
                  @click="copyValue(item.gateway_url)"
                >
                  <template #icon>
                    <icon-copy />
                  </template>
                </a-button>
              </div>
            </a-descriptions-item>
            <a-descriptions-item :label="t('server.gatewaySecret')">
              <div class="flex min-w-0 items-center gap-1">
                <div class="min-w-0 flex-1 break-all" :title="item.gateway_key">
                  {{ item.gateway_key }}
                </div>
                <a-button
                  type="text"
                  size="mini"
                  class="!h-5 !w-5 flex-shrink-0 !text-gray-400"
                  :title="t('common.copy')"
                  :disabled="!item.gateway_key"
                  @click="copyValue(item.gateway_key)"
                >
                  <template #icon>
                    <icon-copy />
                  </template>
                </a-button>
              </div>
            </a-descriptions-item>
            <a-descriptions-item :label="t('server.updatedAt')">
              {{ formatTimestamp(item.updated_at) }}
            </a-descriptions-item>
            <a-descriptions-item :label="t('server.createdAt')">
              {{ formatTimestamp(item.created_at) }}
            </a-descriptions-item>
          </a-descriptions>
        </a-card>
      </div>
      <a-empty
        v-else-if="!getServersLoading"
        :description="t('server.emptyGateway')"
        class="flex h-[400px] flex-col items-center justify-center"
      />
    </a-spin>
  </div>
</template>

<style scoped></style>
