import { post } from '@/utils/request'
import { type BaseResponse } from '@/models/base'
import {
  type PasswordLoginResponse,
  type RegisterRequest,
  type RegisterResponse,
  type SendRegisterCodeRequest,
  type SendRegisterCodeResponse,
} from '@/models/auth'

// 账号密码登录请求
export const passwordLogin = (email: string, password: string) => {
  return post<PasswordLoginResponse>(`/auth/password-login`, {
    body: { email, password },
  })
}

// 发送注册验证码
export const sendRegisterCode = (req: SendRegisterCodeRequest) => {
  return post<SendRegisterCodeResponse>(`/auth/register-code`, {
    body: req,
  })
}

// 邮箱注册
export const register = (req: RegisterRequest) => {
  return post<RegisterResponse>(`/auth/register`, {
    body: req,
  })
}

// 退出登录请求
export const logout = () => {
  return post<BaseResponse<any>>(`/auth/logout`)
}
