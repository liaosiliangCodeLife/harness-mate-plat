import { upload } from '@/utils/request'
import { type UploadFileResponse, type UploadImageResponse } from '@/models/upload-file'

// 上传图片服务；可选 token 用于分享态访客
export const uploadImage = (image: File, token?: string) => {
  // 1.构建表单并添加图片数据
  const formData = new FormData()
  formData.append('file', image)

  // 2.调用upload服务实现图片上传
  return upload<UploadImageResponse>(`/upload-files/image`, {
    data: formData,
    ...(token ? { token } : {}),
  })
}

// 上传文件服务；可选 token 用于分享态访客
export const uploadFile = (file: File, token?: string) => {
  // 1.构建表单并添加图片数据
  const formData = new FormData()
  formData.append('file', file)

  // 2.调用upload服务实现图片上传
  return upload<UploadFileResponse>(`/upload-files/file`, {
    data: formData,
    ...(token ? { token } : {}),
  })
}
