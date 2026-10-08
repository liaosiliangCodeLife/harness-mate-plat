import { type BaseResponse } from '@/models/base'

// 账号密码登录响应结构
export type PasswordLoginResponse = BaseResponse<{
  access_token: string
  expire_at: number
}>

// 发送注册验证码请求
export type SendRegisterCodeRequest = {
  email: string
}

// 发送注册验证码响应
export type SendRegisterCodeResponse = BaseResponse<{
  expire_in: number
}>

// 邮箱注册请求
export type RegisterRequest = {
  email: string
  code: string
  password: string
  password_confirm: string
}

// 邮箱注册响应
export type RegisterResponse = BaseResponse<Record<string, never>>
