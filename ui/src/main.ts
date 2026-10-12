import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ArcoVue from '@arco-design/web-vue'
import ArcoVueIcon from '@arco-design/web-vue/es/icon'

import App from '@/App.vue'
import router from '@/router'
import { i18n } from '@/locales'

import '@arco-design/web-vue/dist/arco.css'
import '@/assets/styles/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(ArcoVue)
app.use(ArcoVueIcon)

app.mount('#app')
