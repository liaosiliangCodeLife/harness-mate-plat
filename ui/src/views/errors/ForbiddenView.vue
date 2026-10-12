<script setup lang="ts">
import Forbidden from '@/assets/images/forbidden.png'
import { t } from '@/locales'
</script>

<template>
  <div class="h-full flex flex-col items-center justify-center">
    <!-- 页面背景 -->
    <img :src="Forbidden" alt="NotFound" class="w-[300px] mb-6" />
    <div class="text-base text-gray-700 font-semibold mb-3">{{ t('errors.forbiddenTitle') }}</div>
    <div class="text-gray-500 mb-6">
      <div class="">{{ t('errors.forbiddenPermission') }}</div>
      <div class="">{{ t('errors.forbiddenMissing') }}</div>
    </div>
    <router-link :to="{ name: 'pages-home' }">
      <a-button type="primary">{{ t('errors.goHome') }}</a-button>
    </router-link>
  </div>
</template>

<style scoped></style>
