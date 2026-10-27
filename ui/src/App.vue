<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import arcoZhCN from '@arco-design/web-vue/es/locale/lang/zh-cn'
import arcoEnUS from '@arco-design/web-vue/es/locale/lang/en-us'

const { locale } = useI18n()
const arcoLocale = computed(() => (locale.value === 'en-US' ? arcoEnUS : arcoZhCN))
</script>

<template>
  <a-config-provider :locale="arcoLocale" global>
    <div class="min-h-screen w-full max-w-full overflow-x-hidden">
      <router-view />
    </div>
  </a-config-provider>
</template>

<style scoped></style>
