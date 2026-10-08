import { onUnmounted, ref } from 'vue'
import type { Agent } from '@/models/agent'
import type { AgentConversation } from '@/models/agent-conversation'
import type { HermesInboundFrame, HermesReplyData } from '@/models/hermes-channel'
import { buildOutboundMessage } from '@/utils/hermes-channel'
import { buildGatewayUrl, signGatewayJwt } from '@/utils/gateway-jwt'

// 卡片上的网关连接状态
export type ChannelStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

const RETRY_DELAYS = [1000, 2000, 5000, 10000]
// 网关约 61 秒无帧会断开；每 40 秒向自身发一条 to，网关丢弃且不进业务
const HEARTBEAT_INTERVAL = 40000

type HermesChannelOptions = {
  agent: () => Agent
  conversation: () => AgentConversation
  onReply: (payload: HermesReplyData) => void
}

// 为单张会话卡片维护一条 WebSocket，断线按 1s→2s→5s→10s 退避重连
export const useHermesChannel = (options: HermesChannelOptions) => {
  const status = ref<ChannelStatus>('disconnected')
  const gatewayReady = ref(false)
  let stopped = true
  let connectSeq = 0
  let retryIndex = 0
  let retryTimer: number | null = null
  let heartbeatTimer: number | null = null
  let currentSocket: WebSocket | null = null

  // gateway_key 和网关地址都有值才允许连接
  const canConnect = () => {
    const agent = options.agent()
    return Boolean(agent.gateway_key?.trim() && agent.gateway_url?.trim())
  }

  const clearRetryTimer = () => {
    if (retryTimer !== null) {
      window.clearTimeout(retryTimer)
      retryTimer = null
    }
  }

  // 关掉当前连接的保活定时器
  const clearHeartbeat = () => {
    if (heartbeatTimer !== null) {
      window.clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // 连接打开后按固定间隔发送保活帧，to 等于本连接的 ws_session_id
  const startHeartbeat = (socket: WebSocket, wsSessionId: string) => {
    clearHeartbeat()
    heartbeatTimer = window.setInterval(() => {
      if (socket.readyState !== WebSocket.OPEN) {
        return
      }
      socket.send(JSON.stringify({ to: wsSessionId }))
    }, HEARTBEAT_INTERVAL)
  }

  // 安排下一次重连，延迟封顶 10 秒
  const scheduleReconnect = () => {
    if (stopped) {
      status.value = 'disconnected'
      return
    }
    status.value = 'reconnecting'
    const delay = RETRY_DELAYS[Math.min(retryIndex, RETRY_DELAYS.length - 1)]
    retryIndex += 1
    clearRetryTimer()
    retryTimer = window.setTimeout(() => {
      retryTimer = null
      void openSocket()
    }, delay)
  }

  // 只处理 reply，并且 thread_id 必须对上当前会话
  const handleFrame = (raw: string) => {
    let frame: HermesInboundFrame
    try {
      frame = JSON.parse(raw) as HermesInboundFrame
    } catch {
      return
    }
    if (frame.data?.type !== 'reply') {
      return
    }
    const threadId = String(frame.data.thread_id || '')
    if (!threadId || threadId !== options.conversation().thread_id) {
      return
    }
    options.onReply(frame.data.data || {})
  }

  // 签发 JWT 后建立连接；期间若卡片已卸载或又发起了新连接，则放弃这一次
  const openSocket = async () => {
    if (stopped || !canConnect()) {
      return
    }
    const seq = ++connectSeq
    if (status.value !== 'reconnecting') {
      status.value = 'connecting'
    }
    const agent = options.agent()
    const conversation = options.conversation()
    const wsSessionId = conversation.ws_session_id
    let url = ''
    try {
      const token = await signGatewayJwt(agent.gateway_key, wsSessionId)
      url = buildGatewayUrl(agent.gateway_url, token)
    } catch {
      if (seq !== connectSeq || stopped) {
        return
      }
      scheduleReconnect()
      return
    }
    if (seq !== connectSeq || stopped) {
      return
    }

    let socket: WebSocket
    try {
      socket = new WebSocket(url)
    } catch {
      scheduleReconnect()
      return
    }
    currentSocket = socket

    socket.onopen = () => {
      if (seq !== connectSeq) {
        socket.close()
        return
      }
      retryIndex = 0
      status.value = 'connected'
      startHeartbeat(socket, wsSessionId)
    }
    socket.onmessage = (event: MessageEvent) => {
      if (seq !== connectSeq || typeof event.data !== 'string') {
        return
      }
      handleFrame(event.data)
    }
    socket.onclose = () => {
      if (seq !== connectSeq) {
        return
      }
      clearHeartbeat()
      if (currentSocket === socket) {
        currentSocket = null
      }
      scheduleReconnect()
    }
  }

  // 关掉当前连接和重连定时器，供卸载或重新发起连接时使用
  const stop = () => {
    stopped = true
    connectSeq += 1
    clearRetryTimer()
    clearHeartbeat()
    currentSocket?.close()
    currentSocket = null
  }

  // 按当前智能体配置重新连接；密钥为空时保持断开且不重试
  const start = () => {
    stop()
    gatewayReady.value = Boolean(options.agent().gateway_key?.trim())
    if (!canConnect()) {
      status.value = 'disconnected'
      retryIndex = 0
      return
    }
    stopped = false
    retryIndex = 0
    status.value = 'connecting'
    void openSocket()
  }

  // 连接已建立时把文本发到网关
  const sendText = (text: string): boolean => {
    if (!currentSocket || currentSocket.readyState !== WebSocket.OPEN) {
      return false
    }
    const envelope = buildOutboundMessage(options.agent(), options.conversation(), text)
    currentSocket.send(JSON.stringify(envelope))
    return true
  }

  onUnmounted(() => {
    stop()
    status.value = 'disconnected'
  })

  return { status, gatewayReady, start, sendText }
}
