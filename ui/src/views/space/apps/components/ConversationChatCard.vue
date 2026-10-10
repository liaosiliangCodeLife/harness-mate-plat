<script setup lang="ts">
import moment from 'moment'
import {
  computed,
  inject,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
  type CSSProperties,
  type PropType,
} from 'vue'
import { Message, Modal, type Form } from '@arco-design/web-vue'
import type { Agent } from '@/models/agent'
import type { AgentConversation } from '@/models/agent-conversation'
import type { AgentMessage, ChatFile, ChatMessage } from '@/models/agent-message'
import type { HermesReplyData } from '@/models/hermes-channel'
import {
  getAgentConversationMessages,
  updateAgentConversation,
  upsertAgentConversationMessage,
} from '@/services/agent'
import { useDeleteAgentConversation, useUpdateAgentConversation } from '@/hooks/use-agent'
import { useHermesChannel } from '@/hooks/use-hermes-channel'
import { updateConversationStatus } from '@/services/conversation'
import { uploadFile, uploadImage } from '@/services/upload-file'
import { useAccountStore } from '@/stores/account'
import { normalizeChatFiles } from '@/utils/chat-files'
import { reduceHermesReply, stripCursorGlyphs, stripStreamCursor } from '@/utils/hermes-channel'
import ChatBubble from '@/views/space/apps/components/ChatBubble.vue'
import { reloadDetailAgentKey } from '@/views/space/apps/detail-agent'

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'])
const DOCUMENT_EXTENSIONS = new Set([
  'txt',
  'markdown',
  'md',
  'pdf',
  'html',
  'htm',
  'xlsx',
  'xls',
  'doc',
  'docx',
  'csv',
])
const ARCHIVE_EXTENSIONS = new Set([
  'zip',
  'rar',
  '7z',
  'tar',
  'gz',
  'tgz',
  'bz2',
  'tbz',
  'tbz2',
  'xz',
  'txz',
  'zst',
  'zipx',
  'cab',
  'jar',
  'war',
])
const UPLOAD_ACCEPT = [...IMAGE_EXTENSIONS, ...DOCUMENT_EXTENSIONS, ...ARCHIVE_EXTENSIONS]
  .map((item) => `.${item}`)
  .join(',')
const MAX_UPLOAD_BYTES = 15 * 1024 * 1024
const MAX_ARCHIVE_UPLOAD_BYTES = 100 * 1024 * 1024
const MAX_ATTACHMENT_COUNT = 5

type ChatAttachment = {
  name: string
  url: string
  isImage: boolean
  size?: number
}
const TITLE_RULES = [
  { required: true, message: '会话标题不能为空' },
  {
    validator: (value: string, callback: (error?: string) => void) => {
      const text = (value ?? '').trim()
      if (!text) {
        callback('会话标题不能为空')
        return
      }
      if (text.length > 255) {
        callback('会话标题长度不能超过255个字符')
        return
      }
      callback()
    },
  },
]

const RECENT_TURNS = 3
const EARLIER_LIMIT = 20
const EARLIER_SCROLL_TOP = 32

// 同一条 Hermes 回复最多写两次：第一条正文，以及 done
type ReplyPersistState = {
  wroteOpening: boolean
  wroteDone: boolean
  reasoning: string
  toolEvents: unknown[]
  chain: Promise<void>
}

// 1.定义自定义组件所需数据
const props = defineProps({
  agent: { type: Object as PropType<Agent>, required: true },
  conversation: { type: Object as PropType<AgentConversation>, required: true },
})
const emits = defineEmits(['refresh'])
const accountStore = useAccountStore()
const { handleUpdateAgentConversation } = useUpdateAgentConversation()
const { handleDeleteAgentConversation } = useDeleteAgentConversation()
const messages = ref<ChatMessage[]>([])
const thinking = ref(false)
const draft = ref('')
const attachments = ref<ChatAttachment[]>([])
const draftExpanded = ref(false)
const uploading = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const editVisible = ref(false)
const editForm = ref({ title: '' })
const editFormRef = ref<InstanceType<typeof Form>>()
const titleOverride = ref<string | null>(null)
const historyLoading = ref(false)
const historyError = ref(false)
const historyReady = ref(false)
const loadingEarlier = ref(false)
const hasMore = ref(false)
const listRef = ref<HTMLElement | null>(null)
const listTrackRef = ref<HTMLElement | null>(null)
const stickToBottom = ref(true)
let listResizeObserver: ResizeObserver | null = null
const replyStates = new Map<string, ReplyPersistState>()
const reloadDetailAgent = inject(reloadDetailAgentKey, null)
let stopRequested = false
// 点停止后先丢掉这一轮的迟到帧，下一次 send 再重新接收
let acceptReplies = true
// 最后一帧之后仍停在生成中，就本地结束。流式中间帧会把这个计时重置
const GENERATION_IDLE_MS = 20_000
let generationIdleTimer: number | undefined
// 思考帧经常不带 message_id，先暂存，等这条回复的正文帧再带上
let carriedReasoning = ''
let carriedToolEvents: unknown[] = []

const title = computed(() => {
  const raw = titleOverride.value ?? props.conversation.title
  return raw?.trim() || '未命名会话'
})
const draftAutoSize = computed(() =>
  draftExpanded.value ? { minRows: 6, maxRows: 10 } : { minRows: 1, maxRows: 4 },
)
const bubbleAvatar = (role: ChatMessage['role']) => {
  if (role === 'user') {
    return accountStore.account?.avatar || ''
  }
  return props.agent.avatar || ''
}
const bubbleName = (role: ChatMessage['role']) => {
  if (role === 'user') {
    return accountStore.account?.name || ''
  }
  return props.agent.name || ''
}
const formattedTime = computed(() => {
  const lastMessageAt = props.conversation.last_message_at
  const timestamp = lastMessageAt || props.conversation.created_at
  if (!timestamp) {
    return '-'
  }
  const text = moment(timestamp * 1000).format('YYYY-MM-DD HH:mm')
  return lastMessageAt ? `最后消息 ${text}` : `创建于 ${text}`
})

// 2.把接口消息转成气泡，user 在右侧，其余角色按助手展示
const toChatMessage = (record: AgentMessage): ChatMessage => {
  return {
    id: `history:${record.id}`,
    role: record.message_role === 'user' ? 'user' : 'assistant',
    content: stripCursorGlyphs(stripStreamCursor(record.message_content || '')),
    thinking: false,
    status: record.message_status,
    fromHistory: true,
    files: normalizeChatFiles(record.message_info?.files),
  }
}

// 未完成且没有正文、也没有文件的助手消息不渲染：历史重进的空气泡，以及本轮生成中的占位气泡
const visibleMessages = computed(() =>
  messages.value.filter((item) => {
    if (item.role !== 'assistant' || item.status !== 0) {
      return true
    }
    if (item.fromHistory) {
      return item.content.trim().length > 0 || (item.files?.length || 0) > 0
    }
    const content = (item.content || '').trim()
    const files = item.files || []
    return content.length > 0 || files.length > 0
  }),
)

// 当前列表里最早一条历史消息的服务端 id，用作向上翻页的 before
const earliestHistoryId = () => {
  const earliest = messages.value.find((item) => item.id.startsWith('history:'))
  if (!earliest) {
    return ''
  }
  return earliest.id.slice('history:'.length)
}

// 3.滚动到底部；用户上翻查看历史时不打断
const scrollToBottom = async (force = false) => {
  if (force) {
    stickToBottom.value = true
  }
  await nextTick()
  const list = listRef.value
  if (!list || !stickToBottom.value) {
    return
  }
  list.scrollTop = list.scrollHeight
}

// 图片或延迟渲染把内容撑高后，仍停在底部时再钉一次；用户上翻后不打断
const pinListToBottom = () => {
  const list = listRef.value
  if (!list || !stickToBottom.value) {
    return
  }
  list.scrollTop = list.scrollHeight
}

const onListMediaLoad = () => {
  pinListToBottom()
}

const onListScroll = () => {
  const list = listRef.value
  if (!list) {
    return
  }
  stickToBottom.value = list.scrollHeight - list.scrollTop - list.clientHeight < 48
  if (!historyReady.value || historyLoading.value || loadingEarlier.value || !hasMore.value) {
    return
  }
  if (list.scrollTop < EARLIER_SCROLL_TOP && list.scrollHeight > list.clientHeight) {
    void loadEarlier()
  }
}

// 4.首屏只拉最近 3 轮，正序拼接后滚到底部
const loadHistory = async () => {
  historyLoading.value = true
  historyError.value = false
  try {
    const resp = await getAgentConversationMessages(props.agent.id, props.conversation.id, {
      turns: RECENT_TURNS,
    })
    const history = resp.data.list.map((item) => toChatMessage(item))
    const live = messages.value.filter((item) => !item.id.startsWith('history:'))
    messages.value = [...history, ...live]
    hasMore.value = resp.data.has_more
  } catch {
    historyError.value = true
  } finally {
    historyLoading.value = false
    await scrollToBottom(true)
  }
}

// 5.滚到顶部时向前插入更早的一页，并用高度差把视口留在原处
const loadEarlier = async () => {
  if (loadingEarlier.value || historyLoading.value || !hasMore.value || !historyReady.value) {
    return
  }
  const beforeId = earliestHistoryId()
  const list = listRef.value
  if (!beforeId || !list) {
    return
  }
  loadingEarlier.value = true
  try {
    const resp = await getAgentConversationMessages(props.agent.id, props.conversation.id, {
      limit: EARLIER_LIMIT,
      before: beforeId,
    })
    const known = new Set(messages.value.map((item) => item.id))
    const fresh = resp.data.list
      .map((item) => toChatMessage(item))
      .filter((item) => !known.has(item.id))
    hasMore.value = Boolean(resp.data.has_more) && fresh.length > 0
    if (fresh.length === 0 || !list.isConnected) {
      return
    }
    const prevHeight = list.scrollHeight
    const prevTop = list.scrollTop
    messages.value = [...fresh, ...messages.value]
    await nextTick()
    if (!list.isConnected) {
      return
    }
    list.scrollTop = prevTop + (list.scrollHeight - prevHeight)
  } catch {
    // 向上加载失败时保留当前列表，请求层会提示错误
  } finally {
    loadingEarlier.value = false
  }
}

// 6.同一条回复的写入串行执行，避免 done 先落库后又被「生成中」覆盖
const ensureReplyState = (messageId: string): ReplyPersistState => {
  const current = replyStates.get(messageId)
  if (current) {
    return current
  }
  const created: ReplyPersistState = {
    wroteOpening: false,
    wroteDone: false,
    reasoning: '',
    toolEvents: [],
    chain: Promise.resolve(),
  }
  replyStates.set(messageId, created)
  return created
}

const appendToolEvents = (bucket: unknown[], incoming: unknown[]) => {
  const seen = new Set(
    bucket.map((item) => {
      try {
        return JSON.stringify(item)
      } catch {
        return ''
      }
    }),
  )
  incoming.forEach((item) => {
    let key = ''
    try {
      key = JSON.stringify(item)
    } catch {
      key = ''
    }
    if (seen.has(key)) {
      return
    }
    seen.add(key)
    bucket.push(item)
  })
}

const rememberToolEvents = (state: ReplyPersistState, payload: HermesReplyData) => {
  if (!Array.isArray(payload.tool_events)) {
    return
  }
  appendToolEvents(state.toolEvents, payload.tool_events)
}

const frameReasoning = (payload: HermesReplyData) => {
  return typeof payload.reasoning === 'string' ? payload.reasoning : ''
}

const persistAssistantMessage = async (
  messageId: string,
  content: string,
  messageStatus: number,
  messageReasoning: string,
  toolEvents: unknown[],
  files: ChatFile[] = [],
) => {
  const messageInfo: { tool_events: unknown[]; files?: ChatFile[] } = {
    tool_events: toolEvents,
  }
  if (files.length > 0) {
    messageInfo.files = files
  }
  try {
    await upsertAgentConversationMessage(props.agent.id, props.conversation.id, {
      message_id: messageId,
      message_role: 'assistant',
      message_content: stripCursorGlyphs(stripStreamCursor(content)),
      message_status: messageStatus,
      message_type: 'reply',
      message_reasoning: messageReasoning,
      message_info: messageInfo,
    })
  } catch {
    // 拦截器已经弹出错误提示
  }
}

// 接口要求正文非空。只有文件时落一份 markdown，回读会被拆成文件，不会和 files 重复显示
const contentForPersist = (content: string, files: ChatFile[]) => {
  if (content.trim() || files.length === 0) {
    return content
  }
  return files
    .map((file) => {
      const label = file.name.replace(/[\[\]]/g, '') || '文件'
      return file.is_image ? `![${label}](${file.url})` : `[${label}](${file.url})`
    })
    .join('\n')
}

const enqueueReplyWrite = (state: ReplyPersistState, task: () => Promise<void>) => {
  state.chain = state.chain.then(task, task)
}

// 7.思考帧不写库；第一条正文写一次生成中，done 再写一次完成
const persistHermesReply = (payload: HermesReplyData) => {
  const reasoning = frameReasoning(payload)
  const messageId = payload.message_id?.trim() || ''
  if (!messageId) {
    if (reasoning) {
      carriedReasoning = reasoning
    }
    if (Array.isArray(payload.tool_events)) {
      appendToolEvents(carriedToolEvents, payload.tool_events)
    }
    return
  }
  const state = ensureReplyState(messageId)
  if (carriedReasoning) {
    state.reasoning = carriedReasoning
    carriedReasoning = ''
  }
  if (carriedToolEvents.length > 0) {
    appendToolEvents(state.toolEvents, carriedToolEvents)
    carriedToolEvents = []
  }
  if (reasoning) {
    state.reasoning = reasoning
  }
  rememberToolEvents(state, payload)
  if (payload.status === 'thinking' && payload.done !== true) {
    return
  }
  const bubble = messages.value.find((item) => item.id === `ws:${messageId}`)
  const content = stripStreamCursor(bubble?.content || '')
  const files = (bubble?.files || []).filter((item) => item.url)
  if (!content.trim() && files.length === 0) {
    return
  }
  const storedContent = contentForPersist(content, files)
  if (payload.done === true) {
    if (state.wroteDone) {
      return
    }
    state.wroteDone = true
    const finalReasoning = state.reasoning
    const toolEvents = state.toolEvents.slice()
    enqueueReplyWrite(state, () =>
      persistAssistantMessage(messageId, storedContent, 1, finalReasoning, toolEvents, files),
    )
    return
  }
  if (state.wroteOpening) {
    return
  }
  state.wroteOpening = true
  const toolEvents = state.toolEvents.slice()
  enqueueReplyWrite(state, () =>
    persistAssistantMessage(messageId, storedContent, 0, reasoning, toolEvents, files),
  )
}

const persistUserMessage = (messageId: string, content: string, files: ChatFile[]) => {
  void upsertAgentConversationMessage(props.agent.id, props.conversation.id, {
    message_id: messageId,
    message_role: 'user',
    message_content: content,
    message_status: 1,
    message_type: 'message',
    message_info: files.length > 0 ? { files } : undefined,
  }).catch(() => undefined)
}

// 8.合并网关 reply：增量更新同一条气泡，思考中单独提示，并按帧落库
const handleReply = (payload: HermesReplyData) => {
  if (!acceptReplies) {
    return
  }
  const result = reduceHermesReply(messages.value, thinking.value, payload)
  let nextMessages = result.messages.filter((item) => !item.id.startsWith('ws:pending:'))
  let nextThinking = result.thinking
  const done = payload.done === true
  if (done) {
    nextThinking = false
    nextMessages = nextMessages.flatMap((item) => {
      if (item.role !== 'assistant' || item.fromHistory || item.status !== 0) {
        return [item]
      }
      const content = stripStreamCursor(item.content).trim()
      if (!content && !(item.files && item.files.length > 0)) {
        return []
      }
      return [{ ...item, content, status: 1 as const, thinking: false }]
    })
    stopRequested = false
  } else if (stopRequested) {
    nextThinking = false
    nextMessages = nextMessages.map((item) => {
      if (item.role === 'assistant' && !item.fromHistory && item.status === 0) {
        return { ...item, status: 2, thinking: false }
      }
      return item
    })
  }
  messages.value = nextMessages
  thinking.value = nextThinking
  if (!stopRequested) {
    persistHermesReply(payload)
  }
  if (
    thinking.value ||
    messages.value.some(
      (item) => item.role === 'assistant' && !item.fromHistory && item.status === 0,
    )
  ) {
    armGenerationIdle()
  } else {
    clearGenerationIdle()
  }
  void scrollToBottom()
}

const isGenerating = computed(
  () =>
    thinking.value ||
    messages.value.some(
      (item) => item.role === 'assistant' && !item.fromHistory && item.status === 0,
    ),
)

/*
 * @Author Leon-liao
 * @Function: hasReplyContent
 * @Description //本轮是否已产出助手正文：非历史、role 为 assistant 且 content 去空白后非空
 * @Date :2026/10/08 19:15:00
 * @Param: 无
 * @return：boolean，已有正文为 true
 */
const hasReplyContent = computed(() =>
  messages.value.some(
    (item) => item.role === 'assistant' && !item.fromHistory && item.content.trim().length > 0,
  ),
)

/*
 * @Author Leon-liao
 * @Function: clearGenerationIdle()
 * @Description //清掉「长时间没有新帧就结束生成」的计时
 * @Date :2026/10/07 22:40:00
 * @Param: 无
 * @return：无
 */
const clearGenerationIdle = () => {
  if (generationIdleTimer === undefined) {
    return
  }
  window.clearTimeout(generationIdleTimer)
  generationIdleTimer = undefined
}

/*
 * @Author Leon-liao
 * @Function: armGenerationIdle()
 * @Description //收到帧或刚把消息发出去时重新计时，超时仍在生成就本地收尾
 * @Date :2026/10/07 22:40:00
 * @Param: 无
 * @return：无
 */
const armGenerationIdle = () => {
  clearGenerationIdle()
  generationIdleTimer = window.setTimeout(() => {
    generationIdleTimer = undefined
    if (!isGenerating.value) {
      return
    }
    releaseGeneration(1)
  }, GENERATION_IDLE_MS)
}

/*
 * @Author Leon-liao
 * @Function: releaseGeneration(finalStatus)
 * @Description //结束本地生成中：空占位直接丢掉，已有正文按给定状态收尾
 * @Date :2026/10/07 22:40:00
 * @Param: finalStatus: 1 表示正常结束，2 表示手动停止或失败
 * @return：无
 */
const releaseGeneration = (finalStatus: 1 | 2) => {
  clearGenerationIdle()
  thinking.value = false
  const next: ChatMessage[] = []
  messages.value.forEach((item) => {
    if (item.role !== 'assistant' || item.fromHistory || item.status !== 0) {
      next.push(item)
      return
    }
    const content = stripStreamCursor(item.content).trim()
    const files = (item.files || []).filter((file) => file.url)
    if (!content && files.length === 0) {
      return
    }
    next.push({ ...item, content, files, status: finalStatus, thinking: false })
    const messageId = item.id.startsWith('ws:') ? item.id.slice('ws:'.length) : ''
    if (!messageId || messageId.startsWith('pending:')) {
      return
    }
    const state = ensureReplyState(messageId)
    state.wroteDone = true
    enqueueReplyWrite(state, () =>
      persistAssistantMessage(messageId, contentForPersist(content, files), finalStatus, '', [], files),
    )
  })
  messages.value = next
}

/*
 * @Author Leon-liao
 * @Function: stopGeneration()
 * @Description //向 Hermes 发送 /stop，并立刻结束本地生成中状态
 * @Date :2026/10/07 21:10:00
 * @Param: 无
 * @return：无
 */
const stopGeneration = () => {
  const sent = sendText('/stop')
  if (!sent) {
    Message.error('停止指令发送失败')
  }
  acceptReplies = false
  stopRequested = false
  replyStates.forEach((state) => {
    state.wroteDone = true
  })
  releaseGeneration(2)
}

const { status, gatewayReady, start, sendText } = useHermesChannel({
  agent: () => props.agent,
  conversation: () => props.conversation,
  onReply: handleReply,
})

const ONLINE_HEARTBEAT_MS = 60_000
let onlineHeartbeatTimer: number | undefined

const reportConversationOnline = async (online: boolean) => {
  const agentId = props.agent?.id
  const conversationId = props.conversation?.id
  if (!agentId || !conversationId) {
    return
  }
  try {
    await updateConversationStatus(agentId, conversationId, online ? 1 : 0)
  } catch {
    // 心跳失败不影响当前会话
  }
}

const stopOnlineHeartbeat = () => {
  if (onlineHeartbeatTimer === undefined) {
    return
  }
  window.clearInterval(onlineHeartbeatTimer)
  onlineHeartbeatTimer = undefined
}

const startOnlineHeartbeat = () => {
  stopOnlineHeartbeat()
  onlineHeartbeatTimer = window.setInterval(() => {
    if (status.value === 'connected') {
      reportConversationOnline(true)
    }
  }, ONLINE_HEARTBEAT_MS)
}

watch(status, (value) => {
  if (value === 'connected') {
    void reportConversationOnline(true).then(() => {
      reloadDetailAgent?.()
    })
    startOnlineHeartbeat()
    return
  }
  stopOnlineHeartbeat()
})

const inputDisabled = computed(() => !gatewayReady.value || status.value !== 'connected')

// 9.先把用户消息上屏并落库，再只把当前文本发给 Hermes，不携带历史
// 附件在发送时按一行一个 markdown 链接接在正文末尾，URL 原样保留
const send = () => {
  const text = buildOutgoingText()
  if (!text || inputDisabled.value) {
    return
  }
  const clientMsgId = crypto.randomUUID()
  const pendingId = `ws:pending:${clientMsgId}`
  const files: ChatFile[] = attachments.value.map((item) => ({
    name: item.name,
    url: item.url,
    media_kind: item.isImage ? 'image' : 'file',
    is_image: item.isImage,
    size: item.size,
  }))
  acceptReplies = true
  stopRequested = false
  draft.value = ''
  attachments.value = []
  messages.value = [
    ...messages.value,
    {
      id: `local:${clientMsgId}`,
      role: 'user',
      content: text,
      thinking: false,
      files,
    },
    {
      id: pendingId,
      role: 'assistant',
      content: '',
      thinking: false,
      status: 0,
    },
  ]
  void scrollToBottom(true)
  armGenerationIdle()
  persistUserMessage(clientMsgId, text, files)
  const sent = sendText(text)
  if (!sent) {
    clearGenerationIdle()
    Message.error('消息发送失败')
    const failId = crypto.randomUUID()
    messages.value = [
      ...messages.value.filter((item) => item.id !== pendingId),
      {
        id: `ws:${failId}`,
        role: 'assistant',
        content: '消息发送失败',
        thinking: false,
        status: 2,
      },
    ]
    void scrollToBottom(true)
    void persistAssistantMessage(failId, '消息发送失败', 2, '', [])
  }
}

const onInputKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) {
    return
  }
  event.preventDefault()
  send()
}

// 8.接口标题跟上本地修改后，改回用列表里的标题
watch(
  () => props.conversation.title,
  (value) => {
    if (titleOverride.value !== null && (value ?? '') === titleOverride.value) {
      titleOverride.value = null
    }
  },
)

// 9.打开编辑弹窗，输入框预填当前标题
const openEdit = () => {
  editForm.value = { title: props.conversation.title ?? '' }
  editVisible.value = true
  void nextTick(() => {
    editFormRef.value?.clearValidate()
  })
}

// 10.校验通过后只提交 title，成功后立刻改卡片标题并通知父组件刷新
const submitEdit = async () => {
  const errors = await editFormRef.value?.validate()
  if (errors) {
    return false
  }
  const nextTitle = editForm.value.title.trim()
  try {
    await handleUpdateAgentConversation(props.agent.id, props.conversation.id, {
      title: nextTitle,
    })
    titleOverride.value = nextTitle
    emits('refresh')
    return true
  } catch {
    return false
  }
}

// 11.二次确认后删除会话，成功后通知父组件刷新列表
const confirmDelete = () => {
  Modal.warning({
    title: '删除会话',
    content: `确认删除会话「${title.value}」吗？`,
    hideCancel: false,
    okText: '删除',
    cancelText: '取消',
    onOk: async () => {
      await handleDeleteAgentConversation(props.agent.id, props.conversation.id)
      emits('refresh')
    },
  })
}

// 按当前状态置顶或取消置顶，只提交 pinned，成功后刷新列表
const pinning = ref(false)
const togglePin = async () => {
  if (pinning.value) {
    return
  }
  const nextPinned = props.conversation.pinned === 1 ? 0 : 1
  pinning.value = true
  try {
    await updateAgentConversation(props.agent.id, props.conversation.id, {
      pinned: nextPinned,
    })
    Message.success(nextPinned === 1 ? '已置顶' : '已取消置顶')
    emits('refresh')
  } catch {
    // 失败时请求层已用后端 message 弹出 Message.error
  } finally {
    pinning.value = false
  }
}

// 12.取出文件扩展名，用来区分图片和文档
const fileExtension = (name: string) => {
  const index = name.lastIndexOf('.')
  if (index < 0 || index === name.length - 1) {
    return ''
  }
  return name.slice(index + 1).toLowerCase()
}

// 13.把上传接口的失败信息转成提示文案
const readUploadError = (error: unknown) => {
  if (typeof error === 'string' && error.trim()) {
    return error
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  if (error && typeof error === 'object') {
    const body = error as { message?: unknown; response?: { message?: unknown } }
    if (typeof body.message === 'string' && body.message.trim()) {
      return body.message
    }
    if (typeof body.response?.message === 'string' && body.response.message.trim()) {
      return body.response.message
    }
  }
  return '上传失败'
}

// 14.点击回形针，打开文件选择框；附件达到 5 个时不再继续添加
const openFilePicker = () => {
  if (uploading.value) {
    return
  }
  if (attachments.value.length >= MAX_ATTACHMENT_COUNT) {
    Message.error('对话上传图片数量不能超过5张')
    return
  }
  fileInputRef.value?.click()
}

// 把文件名里的反斜杠和方括号转义，避免写坏 markdown 链接
const escapeMarkdownLinkLabel = (name: string) => {
  return name.replace(/[\\[\]]/g, (char) => `\\${char}`)
}

// 正文与附件一起发送：有正文时附件接在末尾，只有附件时不留空行
const buildOutgoingText = () => {
  const text = draft.value.trim()
  const links = attachments.value.map(
    (item) => `[${escapeMarkdownLinkLabel(item.name)}](${item.url})`,
  )
  if (links.length === 0) {
    return text
  }
  if (!text) {
    return links.join('\n')
  }
  return `${text}\n${links.join('\n')}`
}

// 15.图片走图片接口，其它允许的文件走文件接口，成功后放进附件列表，不写入输入框
const onFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || uploading.value) {
    return
  }
  if (attachments.value.length >= MAX_ATTACHMENT_COUNT) {
    Message.error('对话上传图片数量不能超过5张')
    return
  }
  const extension = fileExtension(file.name)
  const isImage = IMAGE_EXTENSIONS.has(extension)
  const isArchive = ARCHIVE_EXTENSIONS.has(extension)
  if (!isImage && !DOCUMENT_EXTENSIONS.has(extension) && !isArchive) {
    Message.error(
      '仅支持上传 jpg、jpeg、png、webp、gif、svg、txt、markdown、md、pdf、html、htm、xlsx、xls、doc、docx、csv、zip、rar、7z、tar、gz、tgz、bz2、tbz、tbz2、xz、txz、zst、zipx、cab、jar、war 文件',
    )
    return
  }
  const maxBytes = isArchive ? MAX_ARCHIVE_UPLOAD_BYTES : MAX_UPLOAD_BYTES
  if (file.size > maxBytes) {
    Message.error(isArchive ? '压缩包最大不能超过100MB' : '单个文件不能超过 15MB')
    return
  }
  uploading.value = true
  try {
    let url = ''
    let fileName = file.name
    if (isImage) {
      url = (await uploadImage(file)).data.image_url
    } else {
      const uploaded = (await uploadFile(file)).data
      url = uploaded.url
      const returnedName = uploaded.name?.trim()
      if (returnedName) {
        fileName = returnedName
      }
    }
    if (!url) {
      Message.error('上传失败')
      return
    }
    attachments.value.push({
      name: fileName,
      url,
      isImage,
      size: file.size,
    })
  } catch (error: unknown) {
    Message.error(readUploadError(error))
  } finally {
    uploading.value = false
  }
}

// 16.在普通高度和放大高度之间切换
const toggleDraftExpanded = () => {
  draftExpanded.value = !draftExpanded.value
}

// 全屏只移动当前卡片，不卸载组件，消息、草稿和 WebSocket 都留在原实例上
const isFullscreen = ref(false)
let bodyOverflowBeforeFullscreen = ''

const cardBodyStyle = computed((): CSSProperties => {
  const style: CSSProperties = {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px',
    overflow: 'hidden',
  }
  if (isFullscreen.value) {
    style.minHeight = 0
  }
  return style
})

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

const exitFullscreen = () => {
  isFullscreen.value = false
}

const onFullscreenKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Escape' || !isFullscreen.value) {
    return
  }
  exitFullscreen()
}

watch(isFullscreen, (locked) => {
  if (locked) {
    bodyOverflowBeforeFullscreen = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return
  }
  document.body.style.overflow = bodyOverflowBeforeFullscreen
})

// 7.历史加载完成后再连网关；只在密钥、地址或对端标识真正变化时重连。
// 详情页刷新智能体对象时这四项经常原样换一个引用，不能据此把已连上的通道掐掉。
watch(
  () =>
    [props.agent.gateway_key, props.agent.gateway_url, props.agent.peer_id, props.agent.bot_id].join(
      '\0',
    ),
  () => {
    if (historyReady.value) {
      start()
    }
  },
)

onMounted(async () => {
  window.addEventListener('keydown', onFullscreenKeydown)
  const list = listRef.value
  if (list) {
    list.addEventListener('load', onListMediaLoad, true)
  }
  if (listTrackRef.value) {
    listResizeObserver = new ResizeObserver(() => {
      pinListToBottom()
    })
    listResizeObserver.observe(listTrackRef.value)
  }
  await loadHistory()
  historyReady.value = true
  start()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onFullscreenKeydown)
  listResizeObserver?.disconnect()
  listResizeObserver = null
  listRef.value?.removeEventListener('load', onListMediaLoad, true)
  clearGenerationIdle()
  stopOnlineHeartbeat()
  if (isFullscreen.value) {
    document.body.style.overflow = bodyOverflowBeforeFullscreen
  }
})
</script>

<template>
  <Teleport to="body" :disabled="!isFullscreen">
    <div
      :class="
        isFullscreen
          ? 'fixed inset-0 z-[1000] box-border flex h-screen w-screen flex-col overflow-hidden bg-white p-4'
          : 'contents'
      "
    >
      <a-card
        class="rounded-lg"
        :class="isFullscreen ? 'h-full min-h-0 flex-1' : 'h-[560px]'"
        :body-style="cardBodyStyle"
      >
    <!-- 头部：会话标题旁是连接状态，右上角是更多操作 -->
    <div class="flex items-start justify-between gap-3 mb-3">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 min-w-0">
          <a-tag
            v-if="conversation.pinned === 1"
            color="orangered"
            size="small"
            class="flex-shrink-0"
          >
            置顶
          </a-tag>
          <div class="text-base text-gray-900 font-bold truncate">{{ title }}</div>
          <a-tag v-if="agent.status === 1" color="green" size="small" class="flex-shrink-0">
            在线
          </a-tag>
          <a-tag v-else color="gray" size="small" class="flex-shrink-0">离线</a-tag>
        </div>
        <div class="flex items-center gap-3 text-xs text-gray-400 mt-2">
          <span class="flex-shrink-0">消息 {{ conversation.message_count }}</span>
          <span class="flex-shrink-0">Token {{ conversation.total_token_count }}</span>
          <span class="truncate">{{ formattedTime }}</span>
        </div>
      </div>
      <div class="flex flex-shrink-0 items-center gap-1">
        <a-button
          type="text"
          size="mini"
          class="!text-gray-700 flex-shrink-0"
          :aria-label="isFullscreen ? '退出全屏' : '全屏'"
          :title="isFullscreen ? '退出全屏' : '全屏'"
          @click.stop="toggleFullscreen"
        >
          <template #icon>
            <icon-fullscreen-exit v-if="isFullscreen" />
            <icon-fullscreen v-else />
          </template>
        </a-button>
        <a-dropdown position="br" trigger="click">
          <a-button type="text" size="mini" class="!text-gray-700 flex-shrink-0" @click.stop>
            <template #icon>
              <icon-more />
            </template>
          </a-button>
          <template #content>
            <a-doption @click.stop="openEdit">编辑</a-doption>
            <a-doption @click.stop="togglePin">
              {{ conversation.pinned === 1 ? '取消置顶' : '置顶' }}
            </a-doption>
            <a-doption class="!text-red-700" @click.stop="confirmDelete">删除</a-doption>
          </template>
        </a-dropdown>
      </div>
    </div>
    <div
      v-if="!gatewayReady"
      class="mb-3 rounded-lg bg-orange-50 text-orange-700 text-xs px-3 py-2"
    >
      未配置 gateway_key，无法连接网关
    </div>
    <!-- 消息流 -->
    <div class="relative flex-1 min-h-0">
      <div
        v-if="historyLoading"
        class="absolute inset-0 z-10 flex items-center justify-center bg-white/70"
      >
        <a-spin />
      </div>
      <div
        v-if="loadingEarlier"
        class="pointer-events-none absolute inset-x-0 top-1 z-10 text-center text-xs text-gray-400"
      >
        加载中
      </div>
      <div
        ref="listRef"
        class="h-full overflow-y-auto pr-1"
        @scroll="onListScroll"
      >
        <div ref="listTrackRef" class="flex flex-col gap-3">
          <div v-if="historyError" class="text-center text-xs text-gray-500">
            历史消息加载失败
            <a-button type="text" size="mini" @click="loadHistory">重试</a-button>
          </div>
          <a-empty
            v-else-if="!historyLoading && messages.length === 0 && !thinking"
            description="暂无消息"
            class="my-8"
          />
          <chat-bubble
            v-for="item in visibleMessages"
            :key="item.id"
            :message="item"
            :avatar="bubbleAvatar(item.role)"
            :name="bubbleName(item.role)"
          />
        </div>
      </div>
    </div>
    <!-- 输入区：停止按钮和附件预览在胶囊上方；胶囊内右侧是上传、展开和发送 -->
    <div class="mt-3 flex flex-shrink-0 flex-col gap-2">
      <div v-if="isGenerating" class="relative mb-1.5 flex h-8 justify-center">
        <div class="absolute left-0 top-[50%] translate-y-[-50%] text-[14px] text-[#374151]">
          {{ thinking || !hasReplyContent ? '思考中' : '生成中' }}<span class="thinking-dots"><i>.</i><i>.</i><i>.</i></span>
        </div>
        <a-button type="outline" class="stop-response" @click="stopGeneration">
          <template #icon>
            <icon-poweroff />
          </template>
          停止响应
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
              aria-label="移除图片"
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
            <span class="min-w-0 truncate text-xs">{{ item.name }}</span>
            <icon-close
              class="flex-shrink-0 cursor-pointer text-gray-400 hover:text-gray-700"
              :size="12"
              @click="() => attachments.splice(idx, 1)"
            />
          </div>
        </template>
      </div>
      <div
        class="flex flex-col justify-center gap-2 rounded-[24px] border border-gray-200 bg-white px-4 py-2"
      >
        <div class="flex items-center gap-2">
          <div class="draft-input min-w-0 flex-1">
            <a-textarea
              :key="draftExpanded ? 'expanded' : 'normal'"
              v-model="draft"
              :auto-size="draftAutoSize"
              placeholder="输入消息，Enter 发送，Shift+Enter 换行"
              :disabled="inputDisabled"
              @keydown="onInputKeydown"
            />
          </div>
          <div class="flex flex-shrink-0 items-center">
            <a-button
              type="text"
              shape="circle"
              size="mini"
              class="!text-gray-700"
              :loading="uploading"
              :disabled="uploading"
              aria-label="上传文件"
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
              @click="toggleDraftExpanded"
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
              :disabled="inputDisabled || (!draft.trim() && attachments.length === 0)"
              @click="send"
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
    <a-modal
      v-model:visible="editVisible"
      title="编辑会话"
      :width="480"
      ok-text="保存"
      cancel-text="取消"
      :on-before-ok="submitEdit"
    >
      <a-form ref="editFormRef" :model="editForm" layout="vertical">
        <a-form-item field="title" label="会话标题" :rules="TITLE_RULES" asterisk-position="end">
          <a-input
            v-model="editForm.title"
            :max-length="255"
            show-word-limit
            placeholder="请输入会话标题"
          />
        </a-form-item>
      </a-form>
    </a-modal>
      </a-card>
    </div>
  </Teleport>
</template>

<style scoped>
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
  line-height: 22px;
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
