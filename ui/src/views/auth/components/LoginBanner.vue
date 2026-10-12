<script setup lang="ts">
import { computed } from 'vue'
import BannerImage from '@/assets/images/login-banner.png'
import { t } from '@/locales'

// 轮播图列表
const carousels = computed(() => [
  {
    slogan: t('auth.bannerReady'),
    subSlogan: t('auth.bannerReadySub'),
    image: BannerImage,
  },
  {
    slogan: t('auth.bannerFast'),
    subSlogan: t('auth.bannerFastSub'),
    image: BannerImage,
  },
])
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
