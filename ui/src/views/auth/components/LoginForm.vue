<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCredentialStore } from '@/stores/credential'
import { Message, type ValidatedError } from '@arco-design/web-vue'
import { usePasswordLogin } from '@/hooks/use-auth'
import { useProvider } from '@/hooks/use-oauth'
import RegisterModal from '@/views/auth/components/RegisterModal.vue'
import { APP_VERSION } from '@/utils/version'

// 1.定义自定义组件所需数据
const errorMessage = ref('')
const loginForm = ref({ email: '', password: '' })
const registerVisible = ref(false)
const credentialStore = useCredentialStore()
const router = useRouter()
const { loading: passwordLoginLoading, authorization, handlePasswordLogin } = usePasswordLogin()
const { loading: providerLoading, redirect_url, handleProvider } = useProvider()

// 2.定义忘记密码点击事件
const forgetPassword = () => Message.error('忘记密码请联系管理员')

// 3.打开注册弹窗；注册成功后把邮箱回填到登录框
const openRegister = () => {
  registerVisible.value = true
}
const handleRegistered = (email: string) => {
  loginForm.value.email = email
}

// 4.定义github第三方授权认证登录
const githubLogin = async () => {
  // 4.1 调用处理器获取提供者重定向地址
  await handleProvider('github')

  // 4.2 跳转到重定向地址
  window.location.href = redirect_url.value
}

// 5.账号密码登录
const handleSubmit = async ({ errors }: { errors: Record<string, ValidatedError> | undefined }) => {
  // 5.1 判断表单是否校验成功
  if (errors) return

  // 5.2 如果没有出错则发起请求进行登录
  try {
    // 5.3 发起账号密码登录，并且将loading设置为true
    await handlePasswordLogin(loginForm.value.email, loginForm.value.password)
    Message.success('登录成功，正在跳转')
    credentialStore.update(authorization.value)
    await router.replace({ path: '/home' })
  } catch (error: any) {
    // 5.4 添加错误信息并清除密码
    errorMessage.value = error.message
    loginForm.value.password = ''
  }
}
</script>

<template>
  <div class="">
    <!-- 顶部标题 -->
    <div class="text-gray-900 font-bold text-2xl leading-8">Harness Mate</div>
    <div class="mt-1 text-xs text-gray-400">Version {{ APP_VERSION }}</div>
    <p class="text-base leading-6 text-gray-600">高效连接你的本地智能体</p>
    <!-- 错误提示占位符 -->
    <div class="h-8 text-red-700 leading-8 line-clamp-1">{{ errorMessage }}</div>
    <!-- 登录表单 -->
    <a-form
      :model="loginForm"
      @submit="handleSubmit"
      layout="vertical"
      size="large"
      class="flex flex-col w-full"
    >
      <a-form-item
        field="email"
        :rules="[{ type: 'email', required: true, message: '登录账号必须是合法的邮箱' }]"
        :validate-trigger="['change', 'blur']"
        hide-label
      >
        <a-input v-model="loginForm.email" size="large" placeholder="登录账号">
          <template #prefix>
            <icon-user />
          </template>
        </a-input>
      </a-form-item>
      <a-form-item
        field="password"
        :rules="[{ required: true, message: '账号密码不能为空' }]"
        :validate-trigger="['change', 'blur']"
        hide-label
      >
        <a-input-password v-model="loginForm.password" size="large" placeholder="账号密码">
          <template #prefix>
            <icon-lock />
          </template>
        </a-input-password>
      </a-form-item>
      <a-space :size="16" direction="vertical">
        <div class="flex justify-between">
          <a-checkbox>记住密码</a-checkbox>
          <a-link @click="forgetPassword">忘记密码?</a-link>
        </div>
        <a-button
          :loading="passwordLoginLoading"
          size="large"
          type="primary"
          html-type="submit"
          long
        >
          登录
        </a-button>
        <a-button size="large" type="outline" long html-type="button" @click="openRegister">
          注册
        </a-button>
        <a-divider>第三方授权</a-divider>
        <a-button :loading="providerLoading" size="large" type="dashed" long @click="githubLogin">
          <template #icon>
            <icon-github />
          </template>
          Github
        </a-button>
      </a-space>
    </a-form>
    <register-modal v-model:visible="registerVisible" @registered="handleRegistered" />
  </div>
</template>

<style scoped>
:deep(.arco-divider-text) {
  background-color: transparent;
  padding: 0 12px;
}
:deep(.arco-divider-horizontal) {
  border-bottom-color: #d9e3ea;
}
</style>
