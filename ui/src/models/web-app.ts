import type { BaseResponse } from '@/models/base'

// 获取WebApp基础信息响应结构
export type GetWebAppResponse = BaseResponse<{
  id: string
  icon: string
  name: string
  description: string
  app_config: {
    opening_statement: string
    opening_questions: string[]
    suggested_after_answer: {
      enable: boolean
    },
    features: string[],
    speech_to_text: Record<string, any>,
    text_to_speech: Record<string, any>,
  }
}>

// 获取WebApp会话消息列表响应结构
export type GetWebAppConversationsResponse = BaseResponse<
  {
    id: string
    name: string
    summary: string
    created_at: number
  }[]
>

// 与WebApp对话请求结构
export type WebAppChatRequest = {
  conversation_id?: string
  query: string
  image_urls?: string[]
}
