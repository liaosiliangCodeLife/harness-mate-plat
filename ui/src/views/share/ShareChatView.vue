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
import type { ChatMessage } from '@/models/agent-message'
import type { HermesInboundFrame, HermesReplyData } from '@/models/hermes-channel'
import type { ShareLandingResponse } from '@/models/share-agent'
import {
  useAccessShare,
  useCreateShareConversation,
  useShareLanding,
} from '@/hooks/use-share-agent'
import { postMessage } from '@/services/agent'
import { genUuid } from '@/utils/uuid'
import ChatBubble from '@/views/space/apps/components/ChatBubble.vue'

type PagePhase = 'loading' | 'need_password' | 'expired' | 'ready'
type ShareMessage = ChatMessage & { failed?: boolean }

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
const chatScrollRef = ref<HTMLElement | null>(null)

let eventSource: EventSource | null = null
let currentAiId: string | null = null

// 输入框展开/收起行数，与主站聊天卡片一致
const draftAutoSize = computed(() =>
  draftExpanded.value ? { minRows: 6, maxRows: 12 } : { minRows: 1, maxRows: 4 },
)

// 是否有未完成的 AI 气泡（用于显示「思考中…」与停止）
const generating = computed(() =>
  messages.value.some((item) => item.role === 'assistant' && item.status === 0),
)

/*
 * @Author Leon-liao
 * @Function: stopGeneration()
 * @Description //本地结束当前生成中的 AI 气泡（分享页无后端停止接口）
 * @Date :2026/10/28 11:08:00
 * @Param: 无
 * @return：无
 */
const stopGeneration = () => {
  messages.value = messages.value.map((item) => {
    if (item.role === 'assistant' && item.status === 0) {
      return { ...item, status: 1, thinking: false }
    }
    return item
  })
  currentAiId = null
  Message.success('已停止')
}

const agentInitial = computed(() => {
  const name = landing.value?.agent_name?.trim()
  return name ? name.slice(0, 1) : ''
})

// ChatBubble 头像与展示名：AI 用智能体头像，访客无头像
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
  const chunk = typeof payload.text === 'string' ? payload.text : ''
  const done = payload.done === true
  const isDelta = payload.delta === true

  if (!currentAiId) {
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
  messages.value.push({
    id: bubbleId,
    role: 'user',
    content: text,
    thinking: false,
    status: 1,
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
      { text, message_id: messageId, files: [] },
      accessToken.value,
    )
  } catch (err) {
    const idx = messages.value.findIndex((item) => item.id === bubbleId)
    if (idx >= 0) {
      messages.value[idx] = {
        ...messages.value[idx],
        status: 2,
        failed: true,
      }
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

      <div ref="chatScrollRef" class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-4">
        <div class="mx-auto flex w-full max-w-3xl flex-col gap-1">
          <chat-bubble
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
            :avatar="msg.role === 'user' ? userAvatar : agentAvatar"
            :name="msg.role === 'user' ? userDisplayName : agentDisplayName"
          />
          <div v-if="messages.length === 0" class="py-16 text-center text-sm text-gray-400">
            开始对话吧
          </div>
        </div>
      </div>

      <footer
        class="flex-shrink-0 border-t border-gray-200 bg-white px-3 pt-2"
        style="padding-bottom: max(0.5rem, env(safe-area-inset-bottom))"
      >
        <div class="mx-auto flex w-full max-w-3xl flex-col gap-2">
          <!-- 生成中：左侧「思考中…」+ 停止按钮，与聊天卡片一致 -->
          <div v-if="generating" class="relative mb-1.5 flex h-8 justify-center">
            <div class="absolute left-0 top-[50%] translate-y-[-50%] text-[10px] text-[#374151]">
              思考中<span class="thinking-dots"><i>.</i><i>.</i><i>.</i></span>
            </div>
            <a-button type="outline" class="stop-response" @click="stopGeneration">
              <template #icon>
                <icon-poweroff />
              </template>
              停止
            </a-button>
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
                />
              </div>
              <div class="ml-auto flex flex-shrink-0 items-center sm:ml-0">
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
                  :disabled="sending || !draft.trim()"
                  @click="sendDraft"
                >
                  <template #icon>
                    <icon-send />
                  </template>
                </a-button>
              </div>
            </div>
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
