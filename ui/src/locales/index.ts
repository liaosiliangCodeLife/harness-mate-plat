/**
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //创建 i18n 实例，并同步文档语言、标题与 dayjs
 * @File: index.ts
 * @Time: 2026/10/12 09:05:00
 * @All Rights Reserve By Brtc
 */
import { createI18n } from 'vue-i18n'
import { addI18nMessages, useLocale } from '@arco-design/web-vue/es/locale'
import arcoZhCN from '@arco-design/web-vue/es/locale/lang/zh-cn'
import arcoEnUS from '@arco-design/web-vue/es/locale/lang/en-us'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import 'dayjs/locale/en'
import zhCN from '@/locales/zh-CN'
import enUS from '@/locales/en-US'

addI18nMessages({
  'zh-CN': arcoZhCN,
  'en-US': arcoEnUS,
})

export const LANGUAGE_STORAGE_KEY = 'harness_mate_language'

export type AppLocale = 'zh-CN' | 'en-US'

/**
 * @Author Leon-liao
 * @Function: getStoredLocale()
 * @Description //读取已保存的界面语言，没有记录时使用中文
 * @Date :2026/10/12 09:05:00
 * @Param: 无
 * @return：zh-CN 或 en-US
 */
export const getStoredLocale = (): AppLocale => {
  if (typeof localStorage === 'undefined') {
    return 'zh-CN'
  }
  const stored = localStorage.getItem(LANGUAGE_STORAGE_KEY)
  if (stored === 'en-US' || stored === 'zh-CN') {
    return stored
  }
  return 'zh-CN'
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: getStoredLocale(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

/**
 * @Author Leon-liao
 * @Function: t(key, params)
 * @Description //在组件之外翻译文案，调用时读取当前语言
 * @Date :2026/10/12 09:05:00
 * @Param: key: 语言包键，字符串；params: 插值参数，对象，可空
 * @return：当前语言下的文案
 */
export const t = (key: string, params?: Record<string, unknown>): string => {
  return i18n.global.t(key, params ?? {})
}

/**
 * @Author Leon-liao
 * @Function: translateAgentInfoKey(key)
 * @Description //把设备上报的 agent_info 键名换成当前语言；没有映射时保留原 key
 * @Date :2026/10/12 09:49:00
 * @Param: key: 后端返回的键名，字符串
 * @return：当前语言下的标签；未知键返回原字符串
 */
export const translateAgentInfoKey = (key: string): string => {
  const locale = i18n.global.locale.value === 'en-US' ? 'en-US' : 'zh-CN'
  const messages = i18n.global.getLocaleMessage(locale) as {
    agent?: { infoKeys?: Record<string, string> }
  }
  const label = messages.agent?.infoKeys?.[key]
  return typeof label === 'string' && label !== '' ? label : key
}

/**
 * @Author Leon-liao
 * @Function: applyDocumentLocale(locale)
 * @Description //把 html 语言、页面标题、描述、dayjs 和 Arco 语言切到指定值
 * @Date :2026/10/12 09:05:00
 * @Param: locale: 目标语言，zh-CN 或 en-US
 * @return：无
 */
export const applyDocumentLocale = (locale: AppLocale): void => {
  dayjs.locale(locale === 'zh-CN' ? 'zh-cn' : 'en')
  useLocale(locale)
  if (typeof document === 'undefined') {
    return
  }
  document.documentElement.lang = locale
  document.title = i18n.global.t('common.documentTitle')
  const description = document.querySelector('meta[name="description"]')
  if (description) {
    description.setAttribute('content', i18n.global.t('common.documentDescription'))
  }
}

/**
 * @Author Leon-liao
 * @Function: setLocale(locale)
 * @Description //切换界面语言，并写入本地存储
 * @Date :2026/10/12 09:05:00
 * @Param: locale: 目标语言，zh-CN 或 en-US
 * @return：无
 */
export const setLocale = (locale: AppLocale): void => {
  i18n.global.locale.value = locale
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, locale)
  }
  applyDocumentLocale(locale)
}

applyDocumentLocale(getStoredLocale())
