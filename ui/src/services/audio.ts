import { ssePost, upload } from '@/utils/request'
import type { BaseResponse } from '@/models/base'

// 语音转文本输入接口
export const audioToText = (file: Blob) => {
  // 1.构建表单并添加图片数据
  const formData = new FormData()
  formData.append('file', file, 'recording.wav')

  // 2.调用upload服务实现图片上传
  return upload<BaseResponse<{ text: string }>>(`/audio/audio-to-text`, {
    data: formData,
  })
}

// 消息转语音服务接口
export const messageToAudio = (
  message_id: string,
  onData: (event_response: Record<string, any>) => void,
) => {
  return ssePost(`/audio/message-to-audio`, { body: { message_id } }, onData)
}