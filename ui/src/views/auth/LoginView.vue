<script setup lang="ts">
import LoginBanner from './components/LoginBanner.vue'
import LoginForm from './components/LoginForm.vue'
import loginBackground from '@/assets/images/login-background.png'
import { t } from '@/locales'
</script>

<template>
  <!-- 页面容器：手机竖排（只留表单），桌面左右分栏 -->
  <div
    class="flex h-screen flex-col md:flex-row bg-cover bg-center bg-no-repeat"
    :style="{ backgroundImage: `url(${loginBackground})` }"
  >
    <!-- 顶部站点Logo -->
    <div class="fixed top-4 left-4 md:top-6 md:left-[22px] inline-flex items-center z-50">
      <div class="bg-white/80 text-gray-800 rounded-md px-3 h-8 leading-8 shadow-sm">
        {{ t('auth.brand') }}
      </div>
    </div>
    <!-- 左侧banner（手机隐藏，桌面保留） -->
    <div class="hidden md:flex">
      <login-banner />
    </div>
    <!-- 右侧表单 -->
    <div class="relative flex w-full flex-1 items-center justify-center px-5 pb-10 md:px-0">
      <!-- 登录表单 -->
      <div class="w-full max-w-[360px] md:max-w-none">
        <login-form />
      </div>
      <!-- 底部footer -->
      <div class="absolute right-0 bottom-0 w-full">
        <footer class="flex items-center justify-center h-10 text-gray-600 text-center">
          {{ t('auth.brand') }}
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
