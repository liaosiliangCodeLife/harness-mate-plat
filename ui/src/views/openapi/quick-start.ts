/**
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //按当前语言返回业务对接示例报文
 * @File: quick-start.ts
 * @Time: 2026/10/12 09:12:00
 * @All Rights Reserve By Brtc
 */
import { i18n } from '@/locales'
import { openapiExamples, type OpenapiExampleSet } from '@/locales/openapi-examples'

/**
 * @Author Leon-liao
 * @Function: currentOpenapiExamples()
 * @Description //读取当前语言下的阻塞与流式调用示例
 * @Date :2026/10/12 09:12:00
 * @Param: 无
 * @return：当前语言的示例报文
 */
export const currentOpenapiExamples = (): OpenapiExampleSet => {
  const locale = i18n.global.locale.value === 'en-US' ? 'en-US' : 'zh-CN'
  return openapiExamples[locale]
}
