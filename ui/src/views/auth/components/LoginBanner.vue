<script setup lang="ts">
import BannerImage from '@/assets/images/login-banner.png'

// 轮播图列表
const carousels = [
  {
    slogan: '开箱即用的端到端智能体平台',
    subSlogan: '丰富的应用组件，覆盖大多数典型业务场景',
    image: BannerImage,
  },
  {
    slogan: '零代码5分钟接入你的本地智能体',
    subSlogan: '高效连接你的本地智能体',
    image: BannerImage,
  },
]
</script>

<template>
  <div class="w-[550px] flex items-center justify-center bg-transparent">
    <div class="flex-1 h-full">
      <a-carousel animation-name="fade" class="h-full login-carousel">
        <a-carousel-item v-for="carousel in carousels" :key="carousel.slogan">
          <div class="flex flex-col items-center justify-center h-full">
            <div class="text-2xl leading-7 font-bold text-gray-900">{{ carousel.slogan }}</div>
            <div class="mt-2 text-gray-500 leading-[22px]">{{ carousel.subSlogan }}</div>
            <img :src="carousel.image" alt="Harness Mate" class="w-[320px] mt-[30px]" />
          </div>
        </a-carousel-item>
      </a-carousel>
    </div>
  </div>
</template>

<style scoped>
.login-carousel :deep(.arco-carousel-arrow > div) {
  color: #1d2129;
  background-color: rgba(255, 255, 255, 0.8);
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.12);
}
.login-carousel :deep(.arco-carousel-arrow > div > svg) {
  color: #1d4ed8;
}
.login-carousel :deep(.arco-carousel-arrow > div:hover) {
  background-color: #fff;
}
</style>
