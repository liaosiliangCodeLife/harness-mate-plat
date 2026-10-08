// Hermes Channel 回复负载
export type HermesReplyData = {
  text?: string
  message_id?: string
  delta?: boolean
  done?: boolean
  status?: string
  reasoning?: string
  tool_events?: unknown[]
  // 与 text 同级的扁平文件字段，结束帧才可能带上
  url?: string
  file_name?: string
  media_type?: string
}

// 网关下发的信封
export type HermesInboundFrame = {
  from?: string
  to?: string
  data?: {
    type?: string
    account_id?: string
    thread_id?: string
    data?: HermesReplyData
  }
}

// 发往网关的消息信封
export type HermesOutboundMessage = {
  to: string
  data: {
    type: 'message'
    account_id: string
    thread_id: string
    from_device: string
    data: {
      type: 'message'
      text: string
    }
  }
}
