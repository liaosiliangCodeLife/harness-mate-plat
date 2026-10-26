<script setup lang="ts">
import { computed, ref, watch, type PropType } from 'vue'
import { Message, type FileItem, type RequestOption, type ValidatedError } from '@arco-design/web-vue'
import { useCreateAgent, useUpdateAgent } from '@/hooks/use-agent'
import { useUploadImage } from '@/hooks/use-upload-file'
import type { Agent, CreateAgentRequest, UpdateAgentRequest } from '@/models/agent'
import { t } from '@/locales'

// 1.定义自定义组件所需数据
const props = defineProps({
  visible: { type: Boolean, default: false, required: true },
  callback: { type: Function, required: false },
  // 传入智能体时进入编辑模式，不传则是新建
  agent: { type: Object as PropType<Agent | null>, default: null },
  // 新建时写入当前列表页的接入类型，编辑接口不接收该字段
  agentType: { type: String, default: 'HERMES' },
})
const emits = defineEmits(['update:visible'])
const buildForm = () => ({
  name: '',
  avatar: '',
  agent_info: '',
})
const form = ref(buildForm())
const avatarFileList = ref<FileItem[]>([])
const { loading: createAgentLoading, handleCreateAgent } = useCreateAgent()
const { loading: updateAgentLoading, handleUpdateAgent } = useUpdateAgent()
const { loading: uploadImageLoading, image_url, handleUploadImage } = useUploadImage()
const isEdit = computed(() => Boolean(props.agent?.id))
const submitLoading = computed(() => createAgentLoading.value || updateAgentLoading.value)
const gatewayKey = computed(() => props.agent?.gateway_key || '')
const gatewayUrl = computed(() => props.agent?.gateway_url || '')
const botId = computed(() => props.agent?.bot_id || '')
const peerId = computed(() => props.agent?.peer_id || '')
const agentTypeLabel = computed(() => {
  const value = props.agent?.agent_type?.trim() ?? ''
  if (!value) {
    return '-'
  }
  if (value === 'HERMES') {
    return t('space.hermesAgent')
  }
  if (value === 'DEEPSEEK_HARNESS') {
    return t('space.deepseekAgent')
  }
  return value
})

// 2.定义隐藏模态窗函数
const hideModal = () => {
  emits('update:visible', false)
}

// 3.把 agent_info 格式化成多行 JSON；空对象留空，表示本次不修改
const formatAgentInfoText = (agentInfo: Agent['agent_info']) => {
  if (!agentInfo || typeof agentInfo !== 'object' || Array.isArray(agentInfo)) {
    return ''
  }
  if (Object.keys(agentInfo).length === 0) {
    return ''
  }
  return JSON.stringify(agentInfo, null, 2)
}

// 4.按键名稳定序列化，用来判断 agent_info 是否真的变了
const stableStringify = (value: unknown): string => {
  if (value === null || typeof value !== 'object') {
    return JSON.stringify(value) ?? 'null'
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(',')}]`
  }
  const record = value as Record<string, unknown>
  const keys = Object.keys(record).sort()
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`).join(',')}}`
}

// 5.编辑态回填表单；bot_id、peer_id、网关只展示，不作为可改项
const fillEditForm = (current: Agent) => {
  form.value = {
    name: current.name ?? '',
    avatar: current.avatar ?? '',
    agent_info: formatAgentInfoText(current.agent_info),
  }
  avatarFileList.value = current.avatar
    ? [
        {
          uid: current.id,
          name: 'avatar',
          url: current.avatar,
          status: 'done',
        },
      ]
    : []
}

// 6.选择本地图片后走现有上传接口，成功后把 image_url 写入头像地址
const uploadAvatar = (option: RequestOption) => {
  let aborted = false
  const uploadTask = async () => {
    const { fileItem, onSuccess, onError } = option
    const file = fileItem.file
    if (!file) {
      onError()
      return
    }
    try {
      await handleUploadImage(file)
      if (aborted) {
        return
      }
      form.value.avatar = image_url.value
      onSuccess(image_url.value)
    } catch (err) {
      // 不在这里另弹提示，只结束上传状态并清空头像
      form.value.avatar = ''
      if (!aborted) {
        onError(err)
      }
    }
  }

  uploadTask()

  return {
    abort() {
      aborted = true
      form.value.avatar = ''
    },
  }
}

// 7.移除图片或上传未完成时，把头像地址清空
const onAvatarChange = (fileList: FileItem[]) => {
  const kept = fileList.some((item) => item.status === 'done' || item.status === 'uploading')
  if (!kept) {
    form.value.avatar = ''
  }
}

// 8.解析 agent_info 文本：空字符串表示不提交；非法 JSON 或非对象则提示并中止
const readAgentInfoInput = (text: string): Record<string, any> | undefined | null => {
  const trimmed = text.trim()
  if (!trimmed) {
    return undefined
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      Message.error(t('agent.jsonInvalid'))
      return null
    }
    return parsed as Record<string, any>
  } catch {
    Message.error(t('agent.jsonInvalid'))
    return null
  }
}

// 9.编辑时只收集 name、avatar、agent_info 里相对当前智能体有变化的字段
const buildUpdateRequest = (current: Agent): UpdateAgentRequest | null => {
  const agentInfo = readAgentInfoInput(form.value.agent_info)
  if (agentInfo === null) {
    return null
  }

  const req: UpdateAgentRequest = {}
  const name = form.value.name.trim()
  if (name !== current.name) {
    req.name = name
  }
  const avatar = form.value.avatar.trim()
  if (avatar && avatar !== (current.avatar || '')) {
    req.avatar = avatar
  }
  if (agentInfo) {
    const currentInfo =
      current.agent_info && typeof current.agent_info === 'object' && !Array.isArray(current.agent_info)
        ? current.agent_info
        : {}
    if (stableStringify(agentInfo) !== stableStringify(currentInfo)) {
      req.agent_info = agentInfo
    }
  }
  return req
}

// 10.定义表单提交函数
const saveAgent = async ({ errors }: { errors: Record<string, ValidatedError> | undefined }) => {
  if (errors) return

  if (isEdit.value && props.agent) {
    const req = buildUpdateRequest(props.agent)
    if (!req) return
    if (Object.keys(req).length === 0) {
      Message.warning(t('agent.noChanges'))
      return
    }
    await handleUpdateAgent(props.agent.id, req)
    hideModal()
    props.callback && props.callback()
    return
  }

  const req: CreateAgentRequest = {
    name: form.value.name.trim(),
    agent_type: props.agentType,
  }
  const avatar = form.value.avatar.trim()
  if (avatar) {
    req.avatar = avatar
  }

  await handleCreateAgent(req)
  hideModal()
  props.callback && props.callback()
}

// 11.每次打开模态窗时，编辑回填当前智能体，新建则重置表单（网关由后端自动分配）
watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return
    }
    if (props.agent?.id) {
      fillEditForm(props.agent)
      return
    }
    form.value = buildForm()
    avatarFileList.value = []
  },
)
</script>

<template>
  <a-modal
    :visible="props.visible"
    :width="480"
    hide-title
    :footer="false"
    modal-class="create-agent-modal"
    @update:visible="(value) => emits('update:visible', value)"
  >
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between">
      <div class="create-agent-title">{{ isEdit ? t('agent.editTitle') : t('agent.createTitle') }} <span class="create-agent-accent">Hermes</span></div>
      <a-button type="text" class="!text-gray-700" size="small" @click="hideModal">
        <template #icon>
          <icon-close />
        </template>
      </a-button>
    </div>
    <!-- 中间表单 -->
    <div class="pt-6">
      <a-form :model="form" layout="vertical" @submit="saveAgent">
        <a-form-item field="avatar" hide-label class="avatar-form-item">
          <a-upload
            v-model:file-list="avatarFileList"
            list-type="picture-card"
            :limit="1"
            accept="image/*"
            image-preview
            :disabled="uploadImageLoading"
            :custom-request="uploadAvatar"
            @change="onAvatarChange"
          />
        </a-form-item>
        <a-form-item
          field="name"
          :label="t('agent.name')"
          :rules="[{ required: true, message: t('agent.nameRequired') }]"
        >
          <a-input v-model="form.name" :placeholder="t('agent.namePlaceholder')" />
        </a-form-item>
        <a-form-item v-if="isEdit" :label="t('agent.type')">
          <div class="flex w-full min-w-0 items-center gap-1 min-h-[32px]">
            <div class="break-all text-gray-700" :title="agentTypeLabel">
              {{ agentTypeLabel }}
            </div>
          </div>
        </a-form-item>
        <a-form-item v-if="isEdit" field="agent_info" label="agent_info">
          <a-textarea
            v-model="form.agent_info"
            :placeholder="t('agent.infoPlaceholder')"
            :auto-size="{ minRows: 4, maxRows: 8 }"
          />
        </a-form-item>
        <a-form-item v-if="isEdit" label="bot_id">
          <div class="flex w-full min-w-0 items-center gap-1 min-h-[32px]">
            <div class="break-all text-gray-700" :title="botId || '-'">
              {{ botId || '-' }}
            </div>
          </div>
        </a-form-item>
        <a-form-item v-if="isEdit" label="peer_id">
          <div class="flex w-full min-w-0 items-center gap-1 min-h-[32px]">
            <div class="break-all text-gray-700" :title="peerId || '-'">
              {{ peerId || '-' }}
            </div>
          </div>
        </a-form-item>
        <a-form-item v-if="!isEdit">
          <div class="text-gray-500">{{ t('agent.gatewayAutoAssigned') }}</div>
        </a-form-item>
        <a-form-item v-if="isEdit" :label="t('agent.secret')">
          <div class="flex w-full min-w-0 items-center gap-1 min-h-[32px]">
            <div class="break-all text-gray-700" :title="gatewayKey || '-'">
              {{ gatewayKey || '-' }}
            </div>
          </div>
        </a-form-item>
        <a-form-item v-if="isEdit" :label="t('agent.gatewayUrl')">
          <div class="flex w-full min-w-0 items-center gap-1 min-h-[32px]">
            <div class="break-all text-gray-700" :title="gatewayUrl || '-'">
              {{ gatewayUrl || '-' }}
            </div>
          </div>
        </a-form-item>
        <!-- 底部按钮：带上分隔线，视觉对齐「配对 Hermes」弹窗 footer -->
        <div class="create-agent-footer">
          <a-button class="create-agent-cancel" @click="hideModal">{{ t('common.cancel') }}</a-button>
          <a-button
            :loading="submitLoading"
            type="primary"
            html-type="submit"
            class="create-agent-footer-btn"
          >
            {{ t('common.save') }}
          </a-button>
        </div>
      </a-form>
    </div>
  </a-modal>
</template>

<style scoped>
:deep(.arco-modal) {
  border-radius: 22px;
  overflow: hidden;
}
.create-agent-title {
  font-size: 23px;
  font-weight: 700;
  line-height: 1.3;
  color: #1d2129;
  letter-spacing: 0.4px;
}
.create-agent-accent {
  color: #165dff;
}
.create-agent-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 16px;
  margin: 8px -20px -20px;
  padding: 14px 20px;
  border-top: 1px solid #e5e6eb;
}
.create-agent-cancel,
.create-agent-footer-btn {
  border-radius: 10px;
}
.avatar-form-item :deep(.arco-form-item-content-wrapper),
.avatar-form-item :deep(.arco-form-item-content-flex),
.avatar-form-item :deep(.arco-upload-wrapper) {
  justify-content: center;
}
</style>
