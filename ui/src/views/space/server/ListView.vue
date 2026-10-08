<script setup lang="ts">
import moment from 'moment'
import { Message } from '@arco-design/web-vue'
import { useGetServer } from '@/hooks/use-server'

// 1.拉取当前账号的 WS 网关
const { loading: getServerLoading, server, loadServer } = useGetServer()

// 2.把时间戳格式化成可读时间，空值显示为 -
const formatTimestamp = (timestamp: number | null) => {
  if (!timestamp) {
    return '-'
  }
  return moment(timestamp * 1000).format('YYYY-MM-DD HH:mm')
}

// 3.把网关地址或密钥写入剪贴板
const copyValue = async (value: string) => {
  try {
    await navigator.clipboard.writeText(value)
    Message.success('已复制')
  } catch (err) {
    Message.error(String(err))
  }
}

// 4.进入页面后加载网关；账号下没有网关时请求层已提示，这里保持空状态
loadServer().catch(() => undefined)
</script>

<template>
  <a-spin :loading="getServerLoading" class="block h-full w-full">
    <a-card v-if="server" class="rounded-lg">
      <a-descriptions :column="1" bordered>
        <a-descriptions-item label="网关地址">
          <div class="flex items-center gap-1 min-w-0">
            <div class="break-all min-w-0 flex-1" :title="server.gateway_url">
              {{ server.gateway_url }}
            </div>
            <a-button
              type="text"
              size="mini"
              class="flex-shrink-0 !text-gray-400 !w-5 !h-5"
              title="复制"
              @click="copyValue(server.gateway_url)"
            >
              <template #icon>
                <icon-copy />
              </template>
            </a-button>
          </div>
        </a-descriptions-item>
        <a-descriptions-item label="网关密钥">
          <div class="flex items-center gap-1 min-w-0">
            <div class="break-all min-w-0 flex-1" :title="server.gateway_key">
              {{ server.gateway_key }}
            </div>
            <a-button
              type="text"
              size="mini"
              class="flex-shrink-0 !text-gray-400 !w-5 !h-5"
              title="复制"
              @click="copyValue(server.gateway_key)"
            >
              <template #icon>
                <icon-copy />
              </template>
            </a-button>
          </div>
        </a-descriptions-item>
        <a-descriptions-item label="更新时间">
          {{ formatTimestamp(server.updated_at) }}
        </a-descriptions-item>
        <a-descriptions-item label="创建时间">
          {{ formatTimestamp(server.created_at) }}
        </a-descriptions-item>
      </a-descriptions>
    </a-card>
    <a-empty
      v-else-if="!getServerLoading"
      description="暂无频道服务"
      class="h-[400px] flex flex-col items-center justify-center"
    />
  </a-spin>
</template>

<style scoped></style>
