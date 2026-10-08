<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { Message, type FieldRule, type Form, type ValidatedError } from '@arco-design/web-vue'
import { register, sendRegisterCode } from '@/services/auth'

// 1.弹窗开关由登录页控制，注册成功后把邮箱交回登录表单
const props = defineProps({
  visible: { type: Boolean, default: false, required: true },
})
const emits = defineEmits(['update:visible', 'registered'])

const PASSWORD_PATTERN = /^(?=.*[a-zA-Z])(?=.*\d).{8,16}$/
const PASSWORD_MESSAGE = '密码长度为8-16位，且必须同时包含字母和数字'
const COUNTDOWN_SECONDS = 60
const emailRules: FieldRule[] = [
  { type: 'email', required: true, message: '登录账号必须是合法的邮箱' },
]
const codeRules: FieldRule[] = [{ required: true, message: '验证码不能为空' }]
const passwordRules: FieldRule[] = [
  { required: true, message: '密码不能为空' },
  { match: PASSWORD_PATTERN, message: PASSWORD_MESSAGE },
]
const confirmPasswordRules: FieldRule[] = [
  { required: true, message: '确认密码不能为空' },
  {
    validator: (value: string, callback: (error?: string) => void) => {
      if (value && value !== form.value.password) {
        callback('两次输入的密码不一致')
        return
      }
      callback()
    },
  },
]

const formRef = ref<InstanceType<typeof Form>>()
const form = ref({
  email: '',
  code: '',
  password: '',
  password_confirm: '',
})
const sendingCode = ref(false)
const countdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

// 2.关闭弹窗
const hideModal = () => {
  emits('update:visible', false)
}

// 3.清空倒计时
const stopCountdown = () => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
  countdown.value = 0
}

// 4.验证码发送成功后禁用按钮 60 秒
const startCountdown = () => {
  stopCountdown()
  countdown.value = COUNTDOWN_SECONDS
  countdownTimer = setInterval(() => {
    countdown.value -= 1
    if (countdown.value <= 0) {
      stopCountdown()
    }
  }, 1000)
}

// 5.先校验邮箱，通过后再请求验证码；失败文案由全局拦截器弹出
const sendCode = async () => {
  if (sendingCode.value || countdown.value > 0) return
  const errors = await formRef.value?.validateField('email')
  if (errors) return

  sendingCode.value = true
  try {
    await sendRegisterCode({ email: form.value.email })
    startCountdown()
  } catch {
    // 拦截器已 Message.error(后端 message)
  } finally {
    sendingCode.value = false
  }
}

// 6.提交注册。返回 false 时弹窗保持打开
const submitRegister = async () => {
  const errors = (await formRef.value?.validate()) as
    | Record<string, ValidatedError>
    | undefined
  if (errors) return false

  const email = form.value.email
  try {
    await register({
      email,
      code: form.value.code,
      password: form.value.password,
      password_confirm: form.value.password_confirm,
    })
    Message.success('注册成功，请登录')
    emits('registered', email)
    stopCountdown()
    return true
  } catch {
    return false
  }
}

// 7.关闭时清掉已填内容，避免密码留在弹窗里
watch(
  () => props.visible,
  (visible) => {
    if (visible) return
    form.value = { email: '', code: '', password: '', password_confirm: '' }
    formRef.value?.clearValidate()
  },
)

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
</script>

<template>
  <a-modal
    :visible="props.visible"
    :width="480"
    hide-title
    align-center
    modal-class="register-modal"
    ok-text="注册"
    cancel-text="取消"
    :on-before-ok="submitRegister"
    @cancel="hideModal"
    @update:visible="(value: boolean) => emits('update:visible', value)"
  >
    <div class="mb-5 flex items-start justify-between gap-3">
      <div>
        <div class="register-title">
          注册 <span class="register-accent">Harness Mate</span>
        </div>
        <p class="register-subtitle">用邮箱验证码注册，几秒即可完成</p>
      </div>
      <a-button type="text" size="small" class="!text-gray-400" @click="hideModal">
        <template #icon>
          <icon-close />
        </template>
      </a-button>
    </div>
    <a-form ref="formRef" :model="form" layout="vertical" class="register-form">
      <a-form-item
        field="email"
        label="邮箱"
        :rules="emailRules"
        :validate-trigger="['change', 'blur']"
      >
        <a-input v-model="form.email" placeholder="请输入邮箱" />
      </a-form-item>
      <a-form-item
        field="code"
        label="验证码"
        :rules="codeRules"
        :validate-trigger="['change', 'blur']"
      >
        <div class="flex w-full gap-2">
          <a-input v-model="form.code" placeholder="请输入验证码" class="flex-1" />
          <a-button
            type="outline"
            html-type="button"
            class="register-code-btn"
            :loading="sendingCode"
            :disabled="countdown > 0"
            @click="sendCode"
          >
            {{ countdown > 0 ? `${countdown}s 后重新获取` : '获取验证码' }}
          </a-button>
        </div>
      </a-form-item>
      <a-form-item
        field="password"
        label="密码"
        :rules="passwordRules"
        :validate-trigger="['change', 'blur']"
      >
        <a-input-password v-model="form.password" placeholder="8-16位，需同时包含字母和数字" />
      </a-form-item>
      <a-form-item
        field="password_confirm"
        label="确认密码"
        :rules="confirmPasswordRules"
        :validate-trigger="['change', 'blur']"
      >
        <a-input-password v-model="form.password_confirm" placeholder="请再次输入密码" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<style scoped>
:deep(.arco-modal) {
  border-radius: 22px;
  overflow: hidden;
}
:global(.register-modal.arco-modal) {
  border-radius: 22px;
  overflow: hidden;
}
.register-title {
  font-size: 23px;
  font-weight: 700;
  line-height: 1.3;
  color: #1d2129;
  letter-spacing: 0.4px;
}
.register-accent {
  color: #165dff;
}
.register-subtitle {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.5;
  color: #86909c;
}
.register-form :deep(.arco-form-item) {
  margin-bottom: 16px;
}
.register-form :deep(.arco-form-item:last-child) {
  margin-bottom: 0;
}
.register-code-btn,
:global(.register-modal .arco-modal-footer .arco-btn) {
  border-radius: 10px;
}
</style>
