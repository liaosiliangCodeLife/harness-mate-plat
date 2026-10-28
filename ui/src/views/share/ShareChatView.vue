<script setup lang="ts">
/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //分享智能体访客免登录聊天页（含附件上传与 DSH 授权卡片）
 * @File: ShareChatView.vue
 * @Time: 2026/10/28 11:22:40
 * @All Rights Reserve By Brtc
 */
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { apiPrefix } from '@/config'
import { t } from '@/locales'
import type { ChatFile, ChatMessage } from '@/models/agent-message'
import type {
  HermesApprovalOption,
  HermesInboundFrame,
  HermesReplyData,
} from '@/models/hermes-channel'
import type { ShareLandingResponse } from '@/models/share-agent'
import {
  useAccessShare,
  useCreateShareConversation,
  useShareLanding,
} from '@/hooks/use-share-agent'
import { postMessage } from '@/services/agent'
import { uploadFile, uploadImage } from '@/services/upload-file'
import {
  classifyUpload,
  MAX_ARCHIVE_UPLOAD_BYTES,
  MAX_ATTACHMENT_COUNT,
  MAX_UPLOAD_BYTES,
  UPLOAD_ACCEPT,
} from '@/utils/chat-upload'
import { genUuid } from '@/utils/uuid'
import ChatBubble from '@/views/space/apps/components/ChatBubble.vue'

type PagePhase = 'loading' | 'need_password' | 'expired' | 'ready'
type ShareMessage = ChatMessage & { failed?: boolean }
type ChatAttachment = {
  name: string
  url: string
  isImage: boolean
  size?: number
}
type PendingApproval = {
  approval_id: string
  title: string
  options: HermesApprovalOption[]
  expires_in_ms: number
  expiresAt: number
}

const route = useRoute()
const shareId = computed(() => String(route.params?.share_id ?? ''))

const { loading: landingLoading, landing, loadLanding } = useShareLanding(() => shareId.value)
const { loading: accessLoading, handleAccess } = useAccessShare()
const { loading: createConvLoading, handleCreate: createConversation } =
  useCreateShareConversation()

const phase = ref<PagePhase>('loading')
const password = ref('')
const passwordError = ref('')
const accessToken = ref('')
const expireAt = ref(0)
const agentId = ref('')
const threadId = ref('')
const accountId = ref('')
const messages = ref<ShareMessage[]>([])
const draft = ref('')
const sending = ref(false)
const draftExpanded = ref(false)
const attachments = ref<ChatAttachment[]>([])
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const chatScrollRef = ref<HTMLElement | null>(null)

const pendingApprovals = ref<PendingApproval[]>([])
const approvalNow = ref(Date.now())
const decidingApprovalId = ref('')
let approvalTickTimer: ReturnType<typeof setInterval> | null = null

let eventSource: EventSource | null = null
let currentAiId: string | null = null

// 纯 thinking 帧（尚无气泡）时也要在输入框上方显示「思考中」
const thinking = ref(false)

const draftAutoSize = computed(() =>
  draftExpanded.value ? { minRows: 6, maxRows: 12 } : { minRows: 1, maxRows: 4 },
)

const generating = computed(
  () =>
    thinking.value ||
    messages.value.some((item) => item.role === 'assistant' && item.status === 0),
)

// 当前 AI 是否已有正文（有则顶部显示「生成中」，否则「思考中」）
const hasReplyContent = computed(() =>
  messages.value.some(
    (item) =>
      item.role === 'assistant' &&
      !item.fromHistory &&
      (item.content || '').trim().length > 0,
  ),
)

// 过滤空气泡：无正文、无附件、status===0 的 AI 占位不渲染
const visibleMessages = computed(() =>
  messages.value.filter((item) => {
    if (item.role !== 'assistant') return true
    const empty =
      !(item.content || '').trim() &&
      !(item.files && item.files.length > 0)
    if (empty && item.status === 0) return false
    return true
  }),
)

const agentInitial = computed(() => {
  const name = landing.value?.agent_name?.trim()
  return name ? name.slice(0, 1) : ''
})

const agentAvatar = computed(() => landing.value?.agent_avatar || '')
const agentDisplayName = computed(() => landing.value?.agent_name || '智能体')
const userAvatar = ''
const userDisplayName = '我'

const nowSec = () => Math.floor(Date.now() / 1000)

const expireMessage = computed(() => {
  const reason = landing.value?.expire_reason
  if (reason === 'closed') return '该分享已停用'
  if (reason === 'access_exhausted') return '该分享的对话次数已用完'
  return '该分享已失效'
})

const tokenStorageKey = computed(() => `share_token_${shareId.value}`)
const expireStorageKey = computed(() => `share_expire_${shareId.value}`)

const saveToken = (token: string, expire_at: number) => {
  accessToken.value = token
  expireAt.value = expire_at
  try {
    sessionStorage.setItem(tokenStorageKey.value, token)
    sessionStorage.setItem(expireStorageKey.value, String(expire_at))
  } catch {
    // sessionStorage 不可用时仅内存持有
  }
}

const readStoredToken = (): { token: string; expire_at: number } | null => {
  try {
    const token = sessionStorage.getItem(tokenStorageKey.value) || ''
    const expire_at = Number(sessionStorage.getItem(expireStorageKey.value) || 0)
    if (!token || !expire_at) return null
    if (expire_at * 1000 <= Date.now() + 60_000) return null
    return { token, expire_at }
  } catch {
    return null
  }
}

const closeStream = () => {
  if (!eventSource) return
  eventSource.onopen = null
  eventSource.onmessage = null
  eventSource.onerror = null
  eventSource.close()
  eventSource = null
}

const stopApprovalTick = () => {
  if (!approvalTickTimer) return
  clearInterval(approvalTickTimer)
  approvalTickTimer = null
}

const ensureApprovalTick = () => {
  if (approvalTickTimer || pendingApprovals.value.length === 0) return
  approvalTickTimer = setInterval(() => {
    approvalNow.value = Date.now()
  }, 1000)
}

const clearPendingApprovals = () => {
  pendingApprovals.value = []
  decidingApprovalId.value = ''
  stopApprovalTick()
}

const remainingApprovalSeconds = (item: PendingApproval) =>
  Math.max(0, Math.ceil((item.expiresAt - approvalNow.value) / 1000))

const isApprovalExpired = (item: PendingApproval) => remainingApprovalSeconds(item) <= 0

const upsertPendingApproval = (payload: NonNullable<HermesReplyData['approval']>) => {
  const approvalId = String(payload.approval_id ?? '').trim()
  if (!approvalId) return
  const expiresIn = Number(payload.expires_in_ms) > 0 ? Number(payload.expires_in_ms) : 300000
  const options = Array.isArray(payload.options)
    ? payload.options.filter((item) => item && typeof item.option_id === 'string')
    : []
  const next: PendingApproval = {
    approval_id: approvalId,
    title: String(payload.title ?? '').trim() || '需要授权的操作',
    options,
    expires_in_ms: expiresIn,
    expiresAt: Date.now() + expiresIn,
  }
  const idx = pendingApprovals.value.findIndex((item) => item.approval_id === approvalId)
  if (idx >= 0) {
    const copy = pendingApprovals.value.slice()
    copy[idx] = next
    pendingApprovals.value = copy
  } else {
    pendingApprovals.value = [...pendingApprovals.value, next]
  }
  approvalNow.value = Date.now()
  ensureApprovalTick()
}

const decideApproval = async (item: PendingApproval, optionId: string) => {
  if (isApprovalExpired(item) || decidingApprovalId.value) return
  if (!agentId.value || !threadId.value || !accessToken.value) return
  decidingApprovalId.value = item.approval_id
  try {
    await postMessage(
      agentId.value,
      threadId.value,
      {
        text: `#approval ${item.approval_id} ${optionId}`,
        message_id: genUuid(),
        files: [],
      },
      accessToken.value,
    )
    pendingApprovals.value = pendingApprovals.value.filter(
      (entry) => entry.approval_id !== item.approval_id,
    )
    if (pendingApprovals.value.length === 0) {
      stopApprovalTick()
    }
  } catch {
    Message.error(t('conversation.sendFailed'))
  } finally {
    decidingApprovalId.value = ''
  }
}

const stopGeneration = () => {
  messages.value = messages.value.map((item) => {
    if (item.role === 'assistant' && item.status === 0) {
      return { ...item, status: 1, thinking: false }
    }
    return item
  })
  currentAiId = null
  thinking.value = false
  clearPendingApprovals()
  Message.success('已停止')
}

const applyReply = (payload: HermesReplyData) => {
  if (payload.approval?.approval_id) {
    upsertPendingApproval(payload.approval)
  }
  const chunk = typeof payload.text === 'string' ? payload.text : ''
  const done = payload.done === true
  const isDelta = payload.delta === true

  // 纯 thinking 帧：只点亮顶部「思考中」，不建空气泡
  if (payload.status === 'thinking' && done !== true) {
    thinking.value = true
    return
  }

  // 带正文或结束帧时结束 thinking 态
  if (chunk || done) {
    thinking.value = false
  }

  // 只有纯授权帧且无正文时，不必开 AI 气泡
  if (!chunk && !done && !currentAiId) {
    return
  }

  if (!currentAiId) {
    if (!chunk && done) return
    currentAiId = `ai-${genUuid()}`
    messages.value.push({
      id: currentAiId,
      role: 'assistant',
      content: chunk,
      thinking: false,
      status: done ? 1 : 0,
      createdAt: nowSec(),
    })
  } else {
    const idx = messages.value.findIndex((item) => item.id === currentAiId)
    if (idx >= 0) {
      const prev = messages.value[idx]
      messages.value[idx] = {
        ...prev,
        content: isDelta ? `${prev.content || ''}${chunk}` : chunk || prev.content,
        thinking: false,
        status: done ? 1 : 0,
      }
    }
  }
  if (done) {
    currentAiId = null
  }
  void scrollToBottom()
}

const handleStreamData = (raw: string) => {
  let frame: HermesInboundFrame
  try {
    frame = JSON.parse(raw) as HermesInboundFrame
  } catch {
    return
  }
  const envelope = frame.data
  if (!envelope || envelope.type !== 'reply') return
  if (envelope.thread_id && envelope.thread_id !== threadId.value) return
  applyReply(envelope.data ?? {})
}

const openStream = (token: string) => {
  closeStream()
  const source = new EventSource(
    `${apiPrefix}/chat/stream?token=${encodeURIComponent(token)}`,
  )
  eventSource = source
  source.onmessage = (event: MessageEvent) => {
    if (typeof event.data === 'string') {
      handleStreamData(event.data)
    }
  }
  source.onerror = () => {
    closeStream()
    window.setTimeout(() => {
      if (accessToken.value && phase.value === 'ready') {
        openStream(accessToken.value)
      }
    }, 3000)
  }
}

const scrollToBottom = async () => {
  await nextTick()
  const el = chatScrollRef.value
  if (el) {
    el.scrollTop = el.scrollHeight
  }
}

const enterChat = async (token: string, expire_at: number, account_id: string) => {
  saveToken(token, expire_at)
  accountId.value = account_id
  openStream(token)
  const conv = await createConversation(shareId.value, token, '访客对话')
  agentId.value = conv.agent_id
  threadId.value = conv.thread_id
  phase.value = 'ready'
  await scrollToBottom()
}

const submitPassword = async () => {
  passwordError.value = ''
  try {
    const data = await handleAccess(shareId.value, password.value || undefined)
    await enterChat(data.access_token, data.expire_at, data.account_id)
  } catch (err) {
    passwordError.value = err instanceof Error ? err.message : '访问密码错误'
  }
}

const bootstrap = async () => {
  phase.value = 'loading'
  try {
    await loadLanding()
  } catch (err) {
    phase.value = 'expired'
    landing.value = {
      share_id: shareId.value,
      agent_name: '',
      agent_avatar: '',
      agent_status: 0,
      shared_info: '',
      need_password: false,
      pay_url: '',
      expired: true,
      expire_reason: 'closed',
    } as ShareLandingResponse['data']
    Message.error(err instanceof Error ? err.message : '分享不存在或已失效')
    return
  }

  const info = landing.value
  if (!info) {
    phase.value = 'expired'
    return
  }
  if (info.expired) {
    phase.value = 'expired'
    return
  }
  if (info.need_password) {
    const cached = readStoredToken()
    if (cached) {
      try {
        accessToken.value = cached.token
        expireAt.value = cached.expire_at
        openStream(cached.token)
        const conv = await createConversation(shareId.value, cached.token, '访客对话')
        agentId.value = conv.agent_id
        threadId.value = conv.thread_id
        phase.value = 'ready'
        return
      } catch {
        closeStream()
        accessToken.value = ''
      }
    }
    phase.value = 'need_password'
    return
  }

  try {
    const cached = readStoredToken()
    if (cached) {
      accessToken.value = cached.token
      expireAt.value = cached.expire_at
      openStream(cached.token)
      const conv = await createConversation(shareId.value, cached.token, '访客对话')
      agentId.value = conv.agent_id
      threadId.value = conv.thread_id
      phase.value = 'ready'
      return
    }
    const data = await handleAccess(shareId.value)
    await enterChat(data.access_token, data.expire_at, data.account_id)
  } catch (err) {
    phase.value = 'expired'
    Message.error(err instanceof Error ? err.message : '无法进入分享对话')
  }
}

const readUploadError = (error: unknown) => {
  if (typeof error === 'string' && error.trim()) return error
  if (error instanceof Error && error.message.trim()) return error.message
  if (error && typeof error === 'object') {
    const body = error as { message?: unknown; response?: { message?: unknown } }
    if (typeof body.message === 'string' && body.message.trim()) return body.message
    if (typeof body.response?.message === 'string' && body.response.message.trim()) {
      return body.response.message
    }
  }
  return t('conversation.uploadFailed')
}

const openFilePicker = () => {
  if (uploading.value) return
  if (attachments.value.length >= MAX_ATTACHMENT_COUNT) {
    Message.error(t('conversation.imageLimit'))
    return
  }
  fileInputRef.value?.click()
}

const escapeMarkdownLinkLabel = (name: string) => {
  return name.replace(/[\\[\]]/g, (char) => `\\${char}`)
}

const buildOutgoingText = () => {
  const text = draft.value.trim()
  const links = attachments.value.map(
    (item) => `[${escapeMarkdownLinkLabel(item.name)}](${item.url})`,
  )
  if (links.length === 0) return text
  if (!text) return links.join('\n')
  return `${text}\n${links.join('\n')}`
}

const uploadOneFile = async (file: File): Promise<boolean> => {
  if (uploading.value) return false
  if (attachments.value.length >= MAX_ATTACHMENT_COUNT) {
    Message.error(t('conversation.imageLimit'))
    return false
  }
  const { isImage, isArchive, allowed } = classifyUpload(file)
  if (!allowed) {
    Message.error(t('conversation.fileTypes'))
    return false
  }
  const maxBytes = isArchive ? MAX_ARCHIVE_UPLOAD_BYTES : MAX_UPLOAD_BYTES
  if (file.size > maxBytes) {
    Message.error(isArchive ? t('conversation.archiveTooLarge') : t('conversation.fileTooLarge'))
    return false
  }
  const token = accessToken.value
  if (!token) {
    Message.error(t('conversation.uploadFailed'))
    return false
  }
  uploading.value = true
  try {
    let url = ''
    let fileName = file.name
    if (isImage) {
      url = (await uploadImage(file, token)).data.image_url
    } else {
      const uploaded = (await uploadFile(file, token)).data
      url = uploaded.url
      const returnedName = uploaded.name?.trim()
      if (returnedName) fileName = returnedName
    }
    if (!url) {
      Message.error(t('conversation.uploadFailed'))
      return false
    }
    attachments.value.push({ name: fileName, url, isImage, size: file.size })
    return true
  } catch (error: unknown) {
    Message.error(readUploadError(error))
    return false
  } finally {
    uploading.value = false
  }
}

const onFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  await uploadOneFile(file)
}

const onPaste = async (event: ClipboardEvent) => {
  try {
    const data = event.clipboardData
    if (!data) return
    const seen = new Set<string>()
    const files: File[] = []
    const pushUnique = (file: File | null) => {
      if (!file) return
      const key = `${file.name}:${file.size}`
      if (seen.has(key)) return
      seen.add(key)
      files.push(file)
    }
    if (data.files?.length) {
      for (const file of Array.from(data.files)) pushUnique(file)
    }
    if (data.items?.length) {
      for (const item of Array.from(data.items)) {
        if (item.kind !== 'file') continue
        pushUnique(item.getAsFile())
      }
    }
    if (files.length === 0) return
    event.preventDefault()
    for (const file of files) {
      if (attachments.value.length >= MAX_ATTACHMENT_COUNT) {
        Message.error(t('conversation.imageLimit'))
        break
      }
      if (uploading.value) break
      await uploadOneFile(file)
    }
  } catch {
    /* 粘贴上传失败不抛出 */
  }
}

const sendDraft = async () => {
  const outgoing = buildOutgoingText()
  if (
    !outgoing ||
    sending.value ||
    !agentId.value ||
    !threadId.value ||
    !accessToken.value
  ) {
    return
  }
  const messageId = genUuid()
  const bubbleId = `user-${messageId}`
  const files: ChatFile[] = attachments.value.map((item) => ({
    name: item.name,
    url: item.url,
    media_kind: item.isImage ? 'image' : 'file',
    is_image: item.isImage,
    size: item.size,
  }))
  const filesPayload = attachments.value.map((item) => ({
    name: item.name,
    url: item.url,
    is_image: item.isImage,
    media_kind: item.isImage ? 'image' : 'file',
  }))
  messages.value.push({
    id: bubbleId,
    role: 'user',
    content: outgoing,
    thinking: false,
    status: 1,
    files,
    createdAt: nowSec(),
  })
  draft.value = ''
  sending.value = true
  currentAiId = null
  await scrollToBottom()
  try {
    await postMessage(
      agentId.value,
      threadId.value,
      { text: outgoing, message_id: messageId, files: filesPayload },
      accessToken.value,
    )
    attachments.value = []
  } catch (err) {
    const idx = messages.value.findIndex((item) => item.id === bubbleId)
    if (idx >= 0) {
      messages.value[idx] = {
        ...messages.value[idx],
        status: 2,
        failed: true,
      }
    }
    Message.error(err instanceof Error ? err.message : t('conversation.sendFailed'))
  } finally {
    sending.value = false
  }
}

const onComposerKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    void sendDraft()
  }
}

onMounted(() => {
  void bootstrap()
})

onUnmounted(() => {
  closeStream()
  clearPendingApprovals()
})
</script>

<template>
  <div class="share-chat-page flex h-[100dvh] max-h-[100dvh] w-full max-w-full flex-col overflow-hidden bg-gray-50">
    <div v-if="phase === 'loading' || landingLoading" class="flex flex-1 items-center justify-center">
      <a-spin tip="加载中..." />
    </div>

    <div v-else-if="phase === 'expired'" class="flex flex-1 items-center justify-center p-6">
      <div class="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm">
        <a-avatar
          :size="56"
          shape="circle"
          class="mx-auto mb-3 bg-blue-700"
          :image-url="landing?.agent_avatar || undefined"
        >
          <span v-if="agentInitial">{{ agentInitial }}</span>
          <icon-robot v-else />
        </a-avatar>
        <div class="mb-1 text-lg font-bold text-gray-900">{{ landing?.agent_name || '分享对话' }}</div>
        <div class="text-sm text-gray-500">{{ expireMessage }}</div>
        <a-link
          v-if="landing?.pay_url"
          :href="landing.pay_url"
          target="_blank"
          class="mt-4 inline-block"
        >
          了解更多
        </a-link>
      </div>
    </div>

    <div v-else-if="phase === 'need_password'" class="flex flex-1 items-center justify-center p-6">
      <div class="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div class="mb-4 flex flex-col items-center text-center">
          <a-avatar
            :size="56"
            shape="circle"
            class="mb-3 bg-blue-700"
            :image-url="landing?.agent_avatar || undefined"
          >
            <span v-if="agentInitial">{{ agentInitial }}</span>
            <icon-robot v-else />
          </a-avatar>
          <div class="text-lg font-bold text-gray-900">{{ landing?.agent_name }}</div>
          <div v-if="landing?.shared_info" class="mt-1 text-sm text-gray-500">
            {{ landing.shared_info }}
          </div>
        </div>
        <div class="flex flex-col gap-3">
          <a-form-item
            hide-label
            :validate-status="passwordError ? 'error' : undefined"
            :help="passwordError"
          >
            <a-input-password
              v-model="password"
              placeholder="请输入访问密码"
              allow-clear
              @press-enter="submitPassword"
            />
          </a-form-item>
          <a-button
            type="primary"
            long
            :loading="accessLoading || createConvLoading"
            @click="submitPassword"
          >
            进入对话
          </a-button>
        </div>
      </div>
    </div>

    <template v-else-if="phase === 'ready'">
      <header class="flex h-14 flex-shrink-0 items-center gap-3 border-b border-gray-200 bg-white px-4">
        <a-avatar
          :size="36"
          shape="circle"
          class="flex-shrink-0 bg-blue-700"
          :image-url="landing?.agent_avatar || undefined"
        >
          <span v-if="agentInitial">{{ agentInitial }}</span>
          <icon-robot v-else />
        </a-avatar>
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-bold text-gray-900">{{ landing?.agent_name }}</div>
          <div v-if="landing?.shared_info" class="truncate text-xs text-gray-500">
            {{ landing.shared_info }}
          </div>
        </div>
      </header>

      <div
        v-if="landing && landing.agent_status === 0"
        class="flex-shrink-0 bg-amber-50 px-4 py-2 text-center text-xs text-amber-700"
      >
        智能体暂未连接，可能无法回复
      </div>

      <div ref="chatScrollRef" class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        <div class="mx-auto flex w-full max-w-3xl flex-col gap-1">
          <chat-bubble
            v-for="msg in visibleMessages"
            :key="msg.id"
            :message="msg"
            :avatar="msg.role === 'user' ? userAvatar : agentAvatar"
            :name="msg.role === 'user' ? userDisplayName : agentDisplayName"
            :status-visible="false"
          />
          <div v-if="visibleMessages.length === 0" class="py-16 text-center text-sm text-gray-400">
            开始对话吧
          </div>
        </div>
      </div>

      <footer
        class="flex-shrink-0 border-t border-gray-200 bg-white px-3 pt-2"
        style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom))"
      >
        <div class="mx-auto flex w-full max-w-3xl flex-col gap-2">
          <div v-if="pendingApprovals.length > 0" class="flex flex-col gap-2">
            <div
              v-for="item in pendingApprovals"
              :key="item.approval_id"
              class="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2"
            >
              <div class="text-sm font-medium text-orange-800">
                ⚠️ {{ item.title }}
              </div>
              <div class="mt-1 text-[11px] text-orange-600">
                <template v-if="isApprovalExpired(item)">已过期</template>
                <template v-else>剩余 {{ remainingApprovalSeconds(item) }} 秒</template>
              </div>
              <div class="mt-2 flex flex-wrap gap-2">
                <a-button
                  v-for="option in item.options"
                  :key="option.option_id"
                  size="mini"
                  :type="option.option_id === 'allow-once' ? 'primary' : 'outline'"
                  :status="option.option_id === 'reject-once' ? 'danger' : undefined"
                  :disabled="isApprovalExpired(item) || decidingApprovalId === item.approval_id"
                  :loading="decidingApprovalId === item.approval_id"
                  @click="decideApproval(item, option.option_id)"
                >
                  {{ option.name || option.option_id }}
                </a-button>
              </div>
            </div>
          </div>

          <div v-if="generating" class="relative mb-1.5 flex h-8 justify-center">
            <div class="absolute left-0 top-[50%] translate-y-[-50%] text-[10px] text-[#374151]">
              {{ hasReplyContent ? t('common.generatingNow') : t('common.thinking')
              }}<span class="thinking-dots"><i>.</i><i>.</i><i>.</i></span>
            </div>
            <a-button type="outline" class="stop-response" @click="stopGeneration">
              <template #icon>
                <icon-poweroff />
              </template>
              停止
            </a-button>
          </div>

          <div v-if="attachments.length > 0" class="flex flex-wrap items-center gap-2">
            <template v-for="(item, idx) in attachments" :key="`${item.url}-${idx}`">
              <div
                v-if="item.isImage"
                class="group relative h-10 w-10 cursor-pointer overflow-hidden rounded-lg"
              >
                <a-avatar shape="square" :size="40" :image-url="item.url" />
                <div
                  class="pointer-events-none absolute inset-0 hidden items-center justify-center bg-gray-700/40 group-hover:flex"
                />
                <button
                  type="button"
                  class="absolute right-0 top-0 z-10 flex h-4 w-4 items-center justify-center rounded-full bg-gray-900/70 text-white"
                  :aria-label="t('common.removeImage')"
                  @click.stop="attachments.splice(idx, 1)"
                >
                  <icon-close :size="10" />
                </button>
              </div>
              <div
                v-else
                class="flex h-10 max-w-[200px] items-center gap-1 rounded-lg border border-gray-200 bg-gray-50 px-2 text-gray-700"
                :title="item.name"
              >
                <icon-file class="flex-shrink-0 text-gray-500" :size="14" />
                <span class="min-w-0 truncate text-[10px]">{{ item.name }}</span>
                <icon-close
                  class="flex-shrink-0 cursor-pointer text-gray-400 hover:text-gray-700"
                  :size="12"
                  @click="() => attachments.splice(idx, 1)"
                />
              </div>
            </template>
          </div>

          <div
            class="flex flex-col justify-center gap-2 rounded-[24px] border border-gray-200 bg-white px-3 py-2 sm:px-4"
          >
            <div class="flex flex-wrap items-end gap-1 sm:flex-nowrap sm:items-center sm:gap-2">
              <div class="draft-input min-w-0 flex-1 basis-[min(100%,12rem)] sm:basis-auto">
                <a-textarea
                  :key="draftExpanded ? 'expanded' : 'normal'"
                  v-model="draft"
                  :auto-size="draftAutoSize"
                  :disabled="sending"
                  placeholder="输入消息，Enter 发送，Shift+Enter 换行"
                  @keydown="onComposerKeydown"
                  @paste="onPaste"
                />
              </div>
              <div class="ml-auto flex flex-shrink-0 items-center sm:ml-0">
                <a-button
                  type="text"
                  shape="circle"
                  size="mini"
                  class="!text-gray-700"
                  :loading="uploading"
                  :disabled="uploading"
                  :aria-label="t('common.uploadFile')"
                  @click="openFilePicker"
                >
                  <template #icon>
                    <icon-plus />
                  </template>
                </a-button>
                <a-button
                  type="text"
                  shape="circle"
                  size="mini"
                  class="!text-gray-700"
                  :aria-label="draftExpanded ? '收起输入框' : '展开输入框'"
                  @click="draftExpanded = !draftExpanded"
                >
                  <template #icon>
                    <icon-down v-if="draftExpanded" />
                    <icon-up v-else />
                  </template>
                </a-button>
                <a-button
                  type="text"
                  shape="circle"
                  size="mini"
                  class="!text-gray-700"
                  aria-label="发送"
                  :disabled="sending || (!draft.trim() && attachments.length === 0)"
                  @click="sendDraft"
                >
                  <template #icon>
                    <icon-send />
                  </template>
                </a-button>
              </div>
            </div>
            <input
              ref="fileInputRef"
              type="file"
              class="hidden"
              :accept="UPLOAD_ACCEPT"
              @change="onFileChange"
            />
          </div>
        </div>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.share-chat-page {
  overscroll-behavior: none;
}

.draft-input {
  display: block;
  width: 100%;
}

.draft-input :deep(.arco-textarea-wrapper),
.draft-input :deep(.arco-textarea-wrapper:hover),
.draft-input :deep(.arco-textarea-wrapper:focus-within),
.draft-input :deep(.arco-textarea-wrapper.arco-textarea-focus),
.draft-input :deep(.arco-textarea-wrapper.arco-textarea-disabled),
.draft-input :deep(.arco-textarea-wrapper.arco-textarea-disabled:hover) {
  display: block;
  border: none;
  background: transparent;
  box-shadow: none;
}

.draft-input :deep(.arco-textarea) {
  border: none;
  background: transparent;
  box-shadow: none;
  padding: 5px 0;
  font-size: 11px;
  line-height: 20px;
  outline: none;
}

.stop-response {
  height: 32px;
  border-radius: 8px;
  border-color: #e5e7eb;
  background-color: #fff;
  color: #374151;
}

.stop-response:hover {
  border-color: #d1d5db;
  background-color: #fff;
  color: #1f2937;
}

.thinking-dots {
  display: inline-flex;
  align-items: flex-end;
  height: 1em;
  margin-left: 1px;
}

.thinking-dots i {
  display: inline-block;
  font-style: normal;
  line-height: 1;
  animation: thinking-dot-wave 1.2s ease-in-out infinite;
}

.thinking-dots i:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots i:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-dot-wave {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.25;
  }

  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}
</style>
