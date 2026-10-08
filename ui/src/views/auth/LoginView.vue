<script setup lang="ts">
import LoginBanner from './components/LoginBanner.vue'
import LoginForm from './components/LoginForm.vue'
import loginBackground from '@/assets/images/login-background.png'
</script>

<template>
  <!-- 页面容器 -->
  <div
    class="flex h-screen bg-cover bg-center bg-no-repeat"
    :style="{ backgroundImage: `url(${loginBackground})` }"
  >
    <!-- 顶部站点Logo -->
    <div class="fixed top-6 left-[22px] inline-flex items-center">
      <div class="bg-white/80 text-gray-800 rounded-md px-3 h-8 leading-8 z-50 shadow-sm">
        Harness-Mate 端到端智能体平台
      </div>
    </div>
    <!-- 左侧banner -->
    <login-banner />
    <!-- 右侧表单 -->
    <div class="relative flex flex-1 items-center justify-center pb-10">
      <!-- 登录表单 -->
      <login-form />
      <!-- 底部footer -->
      <div class="absolute right-0 bottom-0 w-full">
        <footer class="flex items-center justify-center h-10 text-gray-600 text-center">
          Harness-Mate 端到端智能体平台
        </footer>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
