<script setup lang="ts">
/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //分享智能体访客免登录聊天页
 * @File: ShareChatView.vue
 * @Time: 2026/10/28 10:04:41
 * @All Rights Reserve By Brtc
 */
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Message } from '@arco-design/web-vue'
import { apiPrefix } from '@/config'
import type { HermesInboundFrame, HermesReplyData } from '@/models/hermes-channel'
import type { ShareLandingResponse } from '@/models/share-agent'
import {
  useAccessShare,
  useCreateShareConversation,
  useShareLanding,
} from '@/hooks/use-share-agent'
import { postMessage } from '@/services/agent'
import { genUuid } from '@/utils/uuid'

type PagePhase = 'loading' | 'need_password' | 'expired' | 'ready'
type ChatBubble = {
  id: string
  role: 'user' | 'ai'
  content: string
  failed?: boolean
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
const messages = ref<ChatBubble[]>([])
const draft = ref('')
const sending = ref(false)
const chatScrollRef = ref<HTMLElement | null>(null)

let eventSource: EventSource | null = null
let currentAiId: string | null = null

const agentInitial = computed(() => {
  const name = landing.value?.agent_name?.trim()
  return name ? name.slice(0, 1) : ''
})

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
    // 提前 60 秒视为过期，避免边界失效
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

/*
 * @Author Leon-liao
 * @Function: applyReply(payload)
 * @Description //按 HermesReplyData 增量拼到当前 AI 气泡；done 时结束该气泡
 * @Date :2026/10/28 10:04:41
 * @Param: payload: 网关 reply 内层 HermesReplyData
 * @return：无
 */
const applyReply = (payload: HermesReplyData) => {
  const text = typeof payload.text === 'string' ? payload.text : ''
  const done = payload.done === true
  const isDelta = payload.delta === true

  if (!currentAiId) {
    currentAiId = `ai-${genUuid()}`
    messages.value.push({ id: currentAiId, role: 'ai', content: text })
  } else {
    const idx = messages.value.findIndex((item) => item.id === currentAiId)
    if (idx >= 0) {
      const prev = messages.value[idx]
      messages.value[idx] = {
        ...prev,
        content: isDelta ? `${prev.content || ''}${text}` : text || prev.content,
      }
    }
  }
  if (done) {
    currentAiId = null
  }
  void scrollToBottom()
}

/*
 * @Author Leon-liao
 * @Function: handleStreamData(raw)
 * @Description //解析 SSE 网关帧，仅处理当前 thread_id 的 reply
 * @Date :2026/10/28 10:04:41
 * @Param: raw: SSE data 文本
 * @return：无
 */
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
    // 访客页简单重连：关掉后 3 秒再开
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
    // 有缓存 token 时直接进入，省去再输密码
    const cached = readStoredToken()
    if (cached) {
      try {
        // 用缓存 token 建会话；失败再回密码页
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

const sendDraft = async () => {
  const text = draft.value.trim()
  if (!text || sending.value || !agentId.value || !threadId.value || !accessToken.value) {
    return
  }
  const messageId = genUuid()
  const bubbleId = `user-${messageId}`
  messages.value.push({ id: bubbleId, role: 'user', content: text })
  draft.value = ''
  sending.value = true
  currentAiId = null
  await scrollToBottom()
  try {
    await postMessage(
      agentId.value,
      threadId.value,
      { text, message_id: messageId, files: [] },
      accessToken.value,
    )
  } catch (err) {
    const idx = messages.value.findIndex((item) => item.id === bubbleId)
    if (idx >= 0) {
      messages.value[idx] = { ...messages.value[idx], failed: true }
    }
    Message.error(err instanceof Error ? err.message : '发送失败')
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
})
</script>

<template>
  <div class="share-chat-page flex h-[100dvh] max-h-[100dvh] w-full max-w-full flex-col overflow-hidden bg-gray-50">
    <!-- loading -->
    <div v-if="phase === 'loading' || landingLoading" class="flex flex-1 items-center justify-center">
      <a-spin tip="加载中..." />
    </div>

    <!-- expired -->
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

    <!-- need password -->
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

    <!-- ready chat -->
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

      <main ref="chatScrollRef" class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        <div class="mx-auto flex w-full max-w-3xl flex-col gap-3">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'"
          >
            <div
              :class="[
                'max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-3 py-2 text-sm',
                msg.role === 'user'
                  ? msg.failed
                    ? 'border border-red-300 bg-red-50 text-red-700'
                    : 'bg-blue-100 text-gray-800'
                  : 'border border-gray-200 bg-white text-gray-800',
              ]"
            >
              {{ msg.content || (msg.role === 'ai' ? '…' : '') }}
            </div>
          </div>
          <div v-if="messages.length === 0" class="py-16 text-center text-sm text-gray-400">
            开始对话吧
          </div>
        </div>
      </main>

      <footer
        class="flex-shrink-0 border-t border-gray-200 bg-white px-3 pt-2"
        style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom))"
      >
        <div class="mx-auto flex w-full max-w-3xl items-end gap-2">
          <a-textarea
            v-model="draft"
            class="min-w-0 flex-1"
            :auto-size="{ minRows: 1, maxRows: 4 }"
            :disabled="sending"
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            @keydown="onComposerKeydown"
          />
          <a-button
            type="primary"
            class="flex-shrink-0"
            :loading="sending"
            :disabled="!draft.trim()"
            @click="sendDraft"
          >
            发送
          </a-button>
        </div>
      </footer>
    </template>
  </div>
</template>

<style scoped>
.share-chat-page {
  overscroll-behavior: none;
}
</style>
