<script setup lang="ts">
import NotFound from '@/assets/images/not-found.png'
</script>

<template>
  <div class="h-full flex flex-col items-center justify-center">
    <!-- 页面背景 -->
    <img :src="NotFound" alt="NotFound" class="w-[300px] mb-6" />
    <div class="text-base text-gray-700 font-semibold mb-3">对不起，您访问的页面找不到啦！</div>
    <div class="text-gray-500 mb-6">
      <div class="">· 页面不存在或者已失效</div>
      <div class="">· 输入的地址不正确</div>
    </div>
    <router-link :to="{ name: 'pages-home' }">
      <a-button type="primary">前往首页</a-button>
    </router-link>
  </div>
</template>

<style scoped></style>
