<script setup lang="ts">
/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //分享智能体管理弹窗：列表、新建、编辑、停用、复制链接
 * @File: ShareAgentModal.vue
 * @Time: 2026/10/28 10:04:41
 * @All Rights Reserve By Brtc
 */
import { computed, reactive, ref, watch, type PropType } from 'vue'
import { Message, Modal } from '@arco-design/web-vue'
import moment from 'moment'
import type { Agent } from '@/models/agent'
import type { ShareAgent } from '@/models/share-agent'
import {
  useCreateShareAgent,
  useDeleteShareAgent,
  useGetShareAgentsWithPage,
  useUpdateShareAgent,
} from '@/hooks/use-share-agent'

const props = defineProps({
  visible: { type: Boolean, default: false, required: true },
  agent: { type: Object as PropType<Agent | null>, default: null },
})
const emits = defineEmits(['update:visible'])

const agentId = computed(() => props.agent?.id ?? '')
const agentInitial = computed(() => {
  const name = props.agent?.name?.trim()
  return name ? name.slice(0, 1) : ''
})
const modalTitle = computed(() => `分享「${props.agent?.name?.trim() || '智能体'}」`)

const { loading: listLoading, shares, loadShares } = useGetShareAgentsWithPage(() => agentId.value)
const { loading: createLoading, handleCreate } = useCreateShareAgent()
const { loading: updateLoading, handleUpdate } = useUpdateShareAgent()
const { loading: deleteLoading, handleDelete } = useDeleteShareAgent()

const editingShareId = ref<string | null>(null)
const form = reactive({
  shared_info: '',
  access_pwd: '',
  access_num: 0,
  pay_url: '',
})

const resetForm = () => {
  editingShareId.value = null
  form.shared_info = ''
  form.access_pwd = ''
  form.access_num = 0
  form.pay_url = ''
}

const hideModal = () => {
  emits('update:visible', false)
}

const shareStatusLabel = (share: ShareAgent) => {
  if (share.status !== 1) {
    return { text: '已停用', color: 'gray' as const }
  }
  if (share.access_num > 0 && share.accessed_num >= share.access_num) {
    return { text: '额度用尽', color: 'orangered' as const }
  }
  return { text: '生效中', color: 'green' as const }
}

const usageText = (share: ShareAgent) => {
  if (!share.access_num) {
    return `已用 ${share.accessed_num} 次 · 不限次数`
  }
  return `已用 ${share.accessed_num}/${share.access_num} 次`
}

const formatCreatedAt = (ts: number) => {
  if (!ts) return '-'
  return moment(Number(ts) * 1000).format('YYYY-MM-DD HH:mm')
}

/*
 * @Author Leon-liao
 * @Function: copyShareUrl(url)
 * @Description //复制分享链接：优先 clipboard API，失败降级 textarea，再失败弹窗展示
 * @Date :2026/10/28 10:04:41
 * @Param: url: 分享链接字符串
 * @return：Promise<void>
 */
const copyShareUrl = async (url: string) => {
  const text = (url || '').trim()
  if (!text) {
    Message.warning('链接为空')
    return
  }
  try {
    await navigator.clipboard.writeText(text)
    Message.success('链接已复制')
    return
  } catch {
    // 降级
  }
  try {
    const el = document.createElement('textarea')
    el.value = text
    el.setAttribute('readonly', 'readonly')
    el.style.position = 'fixed'
    el.style.left = '-9999px'
    document.body.appendChild(el)
    el.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(el)
    if (ok) {
      Message.success('链接已复制')
      return
    }
  } catch {
    // 再降级
  }
  Modal.info({
    title: '复制链接',
    content: text,
    okText: '知道了',
  })
}

const startEdit = (share: ShareAgent) => {
  editingShareId.value = share.id
  form.shared_info = share.shared_info || ''
  form.access_pwd = ''
  form.access_num = share.access_num || 0
  form.pay_url = share.pay_url || ''
}

const cancelEdit = () => {
  resetForm()
}

const submitForm = async () => {
  const id = agentId.value
  if (!id) return
  const req = {
    shared_info: form.shared_info || '',
    access_num: Number(form.access_num) || 0,
    pay_url: form.pay_url || '',
    ...(form.access_pwd !== '' || !editingShareId.value
      ? { access_pwd: form.access_pwd || '' }
      : {}),
  }
  // 编辑时若密码框留空，不改密码；新建时留空即免密
  if (editingShareId.value) {
    const body: Record<string, unknown> = {
      shared_info: req.shared_info,
      access_num: req.access_num,
      pay_url: req.pay_url,
    }
    if (form.access_pwd !== '') {
      body.access_pwd = form.access_pwd
    }
    await handleUpdate(id, editingShareId.value, body)
  } else {
    await handleCreate(id, {
      shared_info: req.shared_info,
      access_pwd: form.access_pwd || '',
      access_num: req.access_num,
      pay_url: req.pay_url,
    })
  }
  resetForm()
  await loadShares(true)
}

const confirmDisable = (share: ShareAgent) => {
  Modal.warning({
    title: '停用分享',
    content: '停用后访客将无法再通过该链接进入对话，确定停用吗？',
    hideCancel: false,
    onOk: async () => {
      const id = agentId.value
      if (!id) return
      await handleDelete(id, share.id)
      if (editingShareId.value === share.id) {
        resetForm()
      }
      await loadShares(true)
    },
  })
}

watch(
  () => [props.visible, agentId.value] as const,
  ([visible, id]) => {
    if (visible && id) {
      resetForm()
      void loadShares(true)
    }
  },
)
</script>

<template>
  <a-modal
    :visible="visible"
    :width="640"
    :title="modalTitle"
    :footer="false"
    unmount-on-close
    @cancel="hideModal"
    @update:visible="(v: boolean) => emits('update:visible', v)"
  >
    <div v-if="agent" class="mb-4 flex items-center gap-3">
      <a-avatar
        :size="40"
        shape="square"
        class="flex-shrink-0 rounded-lg bg-blue-700"
        :image-url="agent.avatar || undefined"
      >
        <span v-if="agentInitial">{{ agentInitial }}</span>
        <icon-robot v-else />
      </a-avatar>
      <div class="min-w-0 flex-1">
        <div class="truncate text-base font-bold text-gray-900">{{ agent.name }}</div>
        <a-tag size="small" color="arcoblue" class="mt-1">{{ agent.agent_type }}</a-tag>
      </div>
    </div>

    <div class="mb-2 text-sm font-medium text-gray-800">已创建的分享</div>
    <a-spin :loading="listLoading" class="mb-4 block w-full">
      <a-empty v-if="!listLoading && shares.length === 0" description="还没有分享链接" />
      <div v-else class="flex max-h-56 flex-col gap-3 overflow-y-auto pr-1">
        <div
          v-for="share in shares"
          :key="share.id"
          class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2"
        >
          <div class="flex min-w-0 items-start gap-2">
            <div class="min-w-0 flex-1">
              <div class="flex min-w-0 items-center gap-2">
                <a-input
                  :model-value="share.share_url"
                  readonly
                  size="small"
                  class="min-w-0 flex-1"
                  @click="($event.target as HTMLInputElement).select()"
                />
                <a-tag :color="shareStatusLabel(share).color" size="small" class="flex-shrink-0">
                  {{ shareStatusLabel(share).text }}
                </a-tag>
              </div>
              <div class="mt-1 text-xs text-gray-500">
                {{ usageText(share) }} · 创建于 {{ formatCreatedAt(share.created_at) }}
                <span v-if="share.has_password" class="ml-1">· 有密码</span>
              </div>
            </div>
            <div class="flex flex-shrink-0 items-center gap-1">
              <a-button size="mini" type="outline" @click="copyShareUrl(share.share_url)">
                复制
              </a-button>
              <a-dropdown trigger="click" position="br">
                <a-button size="mini" type="text">...</a-button>
                <template #content>
                  <a-doption @click="startEdit(share)">编辑</a-doption>
                  <a-doption class="!text-red-700" @click="confirmDisable(share)">停用</a-doption>
                </template>
              </a-dropdown>
            </div>
          </div>
        </div>
      </div>
    </a-spin>

    <a-divider class="!my-3" />

    <div class="mb-2 flex items-center justify-between">
      <div class="text-sm font-medium text-gray-800">
        {{ editingShareId ? '编辑分享' : '新建分享' }}
      </div>
      <a-button v-if="editingShareId" type="text" size="mini" @click="cancelEdit">取消编辑</a-button>
    </div>
    <a-form :model="form" layout="vertical" class="share-form">
      <a-form-item label="分享说明">
        <a-textarea
          v-model="form.shared_info"
          :max-length="4096"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          placeholder="AI 学习助手，欢迎提问"
        />
      </a-form-item>
      <a-form-item :label="editingShareId ? '访问密码（留空不修改）' : '访问密码'">
        <a-input-password
          v-model="form.access_pwd"
          :max-length="128"
          :placeholder="editingShareId ? '留空则不修改密码' : '留空即免密'"
          allow-clear
        />
      </a-form-item>
      <a-form-item label="次数上限" extra="0 = 不限制">
        <a-input-number v-model="form.access_num" :min="0" :precision="0" class="w-full" />
      </a-form-item>
      <a-form-item label="付费链接">
        <a-input v-model="form.pay_url" :max-length="1024" placeholder="可选" allow-clear />
      </a-form-item>
      <div class="flex justify-end">
        <a-button
          type="primary"
          :loading="createLoading || updateLoading || deleteLoading"
          @click="submitForm"
        >
          {{ editingShareId ? '保存修改' : '创建分享' }}
        </a-button>
      </div>
    </a-form>
  </a-modal>
</template>

<style scoped>
.share-form :deep(.arco-form-item) {
  margin-bottom: 12px;
}
</style>
