<script setup lang="ts">
import { computed, ref, watch, type PropType } from 'vue'
import { Message, type FileItem, type RequestOption, type ValidatedError } from '@arco-design/web-vue'
import { useCreateAgent, useUpdateAgent } from '@/hooks/use-agent'
import { useGetOpenServer } from '@/hooks/use-server'
import { useUploadImage } from '@/hooks/use-upload-file'
import type { Agent, CreateAgentRequest, UpdateAgentRequest } from '@/models/agent'
import { generateAgentId } from '@/services/agent'

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
  bot_id: '',
  peer_id: '',
  avatar: '',
  gateway_id: '',
  agent_info: '',
})
const form = ref(buildForm())
const avatarFileList = ref<FileItem[]>([])
const generatingBotId = ref(false)
const generatingPeerId = ref(false)
const { loading: createAgentLoading, handleCreateAgent } = useCreateAgent()
const { loading: updateAgentLoading, handleUpdateAgent } = useUpdateAgent()
const { loading: getServerLoading, server, loadOpenServer } = useGetOpenServer()
const { loading: uploadImageLoading, image_url, handleUploadImage } = useUploadImage()
const isEdit = computed(() => Boolean(props.agent?.id))
const submitLoading = computed(() => createAgentLoading.value || updateAgentLoading.value)
const gatewayKey = computed(() => {
  if (isEdit.value) {
    return props.agent?.gateway_key || ''
  }
  return server.value?.gateway_key || ''
})
const gatewayUrl = computed(() => {
  if (isEdit.value) {
    return props.agent?.gateway_url || ''
  }
  return server.value?.gateway_url || ''
})
const gatewayLoading = computed(() => (isEdit.value ? false : getServerLoading.value))

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
    bot_id: current.bot_id ?? '',
    peer_id: current.peer_id ?? '',
    avatar: current.avatar ?? '',
    gateway_id: '',
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
  server.value = null
}

// 6.拉取免登录网关：只读展示 gateway_key、gateway_url，提交时仍用返回的 id
const loadCurrentGateway = async () => {
  try {
    const current = await loadOpenServer()
    form.value.gateway_id = current?.id ?? ''
  } catch {
    // 账号下没有网关时后端返回 not_found，错误文案已由拦截器提示
    server.value = null
    form.value.gateway_id = ''
  }
}

// 7.调用生成标识接口，把 bot_id 或 peer_id 填进对应输入框
const fillGeneratedId = async (type: 'bot_id' | 'peer_id') => {
  const loading = type === 'bot_id' ? generatingBotId : generatingPeerId
  if (loading.value) {
    return
  }
  try {
    loading.value = true
    const resp = await generateAgentId({ type })
    form.value[type] = resp.data[type] ?? ''
  } catch {
    // 错误文案已由全局拦截器 Message.error 展示
  } finally {
    loading.value = false
  }
}

// 8.选择本地图片后走现有上传接口，成功后把 image_url 写入头像地址
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

// 9.移除图片或上传未完成时，把头像地址清空
const onAvatarChange = (fileList: FileItem[]) => {
  const kept = fileList.some((item) => item.status === 'done' || item.status === 'uploading')
  if (!kept) {
    form.value.avatar = ''
  }
}

// 10.解析 agent_info 文本：空字符串表示不提交；非法 JSON 或非对象则提示并中止
const readAgentInfoInput = (text: string): Record<string, any> | undefined | null => {
  const trimmed = text.trim()
  if (!trimmed) {
    return undefined
  }
  try {
    const parsed = JSON.parse(trimmed) as unknown
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      Message.error('agent_info 必须是合法的 JSON 对象')
      return null
    }
    return parsed as Record<string, any>
  } catch {
    Message.error('agent_info 必须是合法的 JSON 对象')
    return null
  }
}

// 11.编辑时只收集 name、avatar、agent_info 里相对当前智能体有变化的字段
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

// 12.定义表单提交函数
const saveAgent = async ({ errors }: { errors: Record<string, ValidatedError> | undefined }) => {
  if (errors) return

  if (isEdit.value && props.agent) {
    const req = buildUpdateRequest(props.agent)
    if (!req) return
    if (Object.keys(req).length === 0) {
      Message.warning('没有需要保存的修改')
      return
    }
    await handleUpdateAgent(props.agent.id, req)
    hideModal()
    props.callback && props.callback()
    return
  }

  const req: CreateAgentRequest = {
    name: form.value.name.trim(),
    bot_id: form.value.bot_id.trim(),
    peer_id: form.value.peer_id.trim(),
    agent_type: props.agentType,
  }
  const avatar = form.value.avatar.trim()
  const gatewayId = `${form.value.gateway_id ?? ''}`.trim()
  if (avatar) {
    req.avatar = avatar
  }
  if (gatewayId) {
    req.gateway_id = gatewayId
  }

  await handleCreateAgent(req)
  hideModal()
  props.callback && props.callback()
}

// 13.每次打开模态窗时，编辑回填当前智能体，新建则重置并拉取免登录网关
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
    server.value = null
    void loadCurrentGateway()
  },
)
</script>

<template>
  <a-modal
    :visible="props.visible"
    hide-title
    :footer="false"
    @update:visible="(value) => emits('update:visible', value)"
  >
    <!-- 顶部标题 -->
    <div class="flex items-center justify-between">
      <div class="text-lg font-bold text-gray-700">{{ isEdit ? '编辑智能体' : '创建智能体' }}</div>
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
          label="智能体名称"
          :rules="[{ required: true, message: '请输入智能体名称' }]"
        >
          <a-input v-model="form.name" placeholder="请输入智能体名称" />
        </a-form-item>
        <a-form-item v-if="isEdit" field="agent_info" label="agent_info">
          <a-textarea
            v-model="form.agent_info"
            placeholder='可选，请填写 JSON 对象，例如 {"role":"assistant"}'
            :auto-size="{ minRows: 4, maxRows: 8 }"
          />
        </a-form-item>
        <a-form-item
          field="bot_id"
          label="智能体业务标识"
          :rules="isEdit ? [] : [{ required: true, message: '请输入智能体业务标识' }]"
        >
          <div class="flex w-full items-center gap-2">
            <a-input
              v-model="form.bot_id"
              :disabled="isEdit"
              placeholder="请输入 bot_id，全局唯一"
              class="flex-1"
            />
            <a-button
              v-if="!isEdit"
              html-type="button"
              :loading="generatingBotId"
              @click="fillGeneratedId('bot_id')"
            >
              生成
            </a-button>
          </div>
        </a-form-item>
        <a-form-item
          field="peer_id"
          label="对端设备标识"
          :rules="isEdit ? [] : [{ required: true, message: '请输入对端设备标识' }]"
        >
          <div class="flex w-full items-center gap-2">
            <a-input
              v-model="form.peer_id"
              :disabled="isEdit"
              placeholder="请输入 peer_id"
              class="flex-1"
            />
            <a-button
              v-if="!isEdit"
              html-type="button"
              :loading="generatingPeerId"
              @click="fillGeneratedId('peer_id')"
            >
              生成
            </a-button>
          </div>
        </a-form-item>
        <a-form-item label="智能体密钥">
          <div class="flex w-full min-w-0 items-center gap-1 min-h-[32px]">
            <a-spin :loading="gatewayLoading" class="min-w-0 flex-1">
              <div class="break-all text-gray-700" :title="gatewayKey || '-'">
                {{ gatewayLoading ? '' : (gatewayKey || '-') }}
              </div>
            </a-spin>
          </div>
        </a-form-item>
        <a-form-item label="网关地址">
          <div class="flex w-full min-w-0 items-center gap-1 min-h-[32px]">
            <a-spin :loading="gatewayLoading" class="min-w-0 flex-1">
              <div class="break-all text-gray-700" :title="gatewayUrl || '-'">
                {{ gatewayLoading ? '' : (gatewayUrl || '-') }}
              </div>
            </a-spin>
          </div>
        </a-form-item>
        <!-- 底部按钮 -->
        <div class="flex items-center justify-end">
          <a-space :size="16">
            <a-button class="rounded-lg" @click="hideModal">取消</a-button>
            <a-button :loading="submitLoading" type="primary" html-type="submit" class="rounded-lg">
              保存
            </a-button>
          </a-space>
        </div>
      </a-form>
    </div>
  </a-modal>
</template>

<style scoped>
.avatar-form-item :deep(.arco-form-item-content-wrapper),
.avatar-form-item :deep(.arco-form-item-content-flex),
.avatar-form-item :deep(.arco-upload-wrapper) {
  justify-content: center;
}
</style>
