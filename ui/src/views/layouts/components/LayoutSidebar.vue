<script setup lang="ts">
import { useRoute } from 'vue-router'
import IconHomeFull from '@/components/icons/IconHomeFull.vue'
import IconHome from '@/components/icons/IconHome.vue'
import IconSpaceFull from '@/components/icons/IconSpaceFull.vue'
import IconSpace from '@/components/icons/IconSpace.vue'

// 1.定义自定义组件所需数据
const route = useRoute()
</script>

<template>
  <div class="flex flex-col gap-2">
    <router-link
      to="/home"
      class="flex items-center gap-2 h-8 leading-8 rounded-lg transition-all px-2 text-gray-700 hover:text-gray-900 hover:bg-gray-200"
      active-class="bg-gray-100"
    >
      <icon-home-full v-if="route.path.startsWith('/home')" />
      <icon-home v-else />
      主页
    </router-link>
    <router-link
      to="/space/apps"
      :class="`flex items-center gap-2 h-8 leading-8 rounded-lg transition-all px-2 text-gray-700 hover:text-gray-900 hover:bg-gray-200 ${route.path.startsWith('/space') ? 'bg-gray-100' : ''}`"
    >
      <icon-space-full v-if="route.path.startsWith('/space')" />
      <icon-space v-else />
      个人空间
    </router-link>
    <router-link
      to="/server"
      :class="`flex items-center gap-2 h-8 leading-8 rounded-lg transition-all px-2 text-gray-700 hover:text-gray-900 hover:bg-gray-200 ${route.path.startsWith('/server') ? 'bg-gray-100' : ''}`"
    >
      <icon-link />
      频道服务
    </router-link>
    <router-link
      to="/openapi"
      class="flex items-center gap-2 h-8 leading-8 rounded-lg transition-all px-2 text-gray-700 hover:text-gray-900 hover:bg-gray-200"
      active-class="bg-gray-100"
    >
      <icon-email />
      业务对接
    </router-link>
  </div>
</template>

<style scoped></style>
