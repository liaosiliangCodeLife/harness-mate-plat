<script setup lang="ts">
import { ref, watch } from 'vue'
import { Message, type ValidatedError } from '@arco-design/web-vue'
import { useCreateAgentConversation } from '@/hooks/use-agent'
import type { CreateAgentConversationRequest } from '@/models/agent-conversation'
import { generateAgentId } from '@/services/agent'

// 1.定义自定义组件所需数据
const props = defineProps({
  visible: { type: Boolean, default: false, required: true },
  agentId: { type: String, required: true },
  callback: { type: Function, required: false },
})
const emits = defineEmits(['update:visible'])
const form = ref({ title: '' })
const saving = ref(false)
const { loading: createLoading, handleCreateAgentConversation } = useCreateAgentConversation()

// 2.定义隐藏模态窗函数
const hideModal = () => {
  emits('update:visible', false)
}

// 3.先向生成标识接口取 thread_id，再创建会话；标题为空时不传 title
const saveConversation = async ({
  errors,
}: {
  errors: Record<string, ValidatedError> | undefined
}) => {
  if (errors || saving.value || createLoading.value || !props.agentId) return

  try {
    saving.value = true
    const generated = await generateAgentId({ type: 'thread_id' })
    const threadId = generated.data.thread_id
    if (!threadId) {
      Message.error('未获取到会话线程标识')
      return
    }

    const req: CreateAgentConversationRequest = { thread_id: threadId }
    const title = form.value.title.trim()
    if (title) {
      req.title = title
    }

    await handleCreateAgentConversation(props.agentId, req)
    hideModal()
    props.callback && props.callback()
  } catch {
    // 失败文案由全局拦截器 Message.error 展示后端返回的 message
  } finally {
    saving.value = false
  }
}

// 4.每次打开模态窗时清空标题
watch(
  () => props.visible,
  (visible) => {
    if (!visible) {
      return
    }
    form.value = { title: '' }
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
      <div class="text-lg font-bold text-gray-700">新增会话</div>
      <a-button type="text" class="!text-gray-700" size="small" @click="hideModal">
        <template #icon>
          <icon-close />
        </template>
      </a-button>
    </div>
    <!-- 中间表单 -->
    <div class="pt-6">
      <a-form :model="form" layout="vertical" @submit="saveConversation">
        <a-form-item field="title" label="会话标题">
          <a-input
            v-model="form.title"
            placeholder="请输入会话标题"
            :max-length="255"
            show-word-limit
          />
        </a-form-item>
        <!-- 底部按钮 -->
        <div class="flex items-center justify-end">
          <a-space :size="16">
            <a-button class="rounded-lg" @click="hideModal">取消</a-button>
            <a-button
              :loading="saving || createLoading"
              type="primary"
              html-type="submit"
              class="rounded-lg"
            >
              保存
            </a-button>
          </a-space>
        </div>
      </a-form>
    </div>
  </a-modal>
</template>

<style scoped></style>
