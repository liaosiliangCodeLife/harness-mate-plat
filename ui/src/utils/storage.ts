export default {
  // 获取localStorage中的值
  get: (key: string, defaultValue: any = ''): any => {
    const value = localStorage.getItem(key)
    if (value) {
      try {
        return JSON.parse(value)
      } catch {
        return value
      }
    }
    return defaultValue
  },
  // 设置localStorage中的值
  set: (key: string, value: any): void => {
    if (typeof value === 'string') {
      localStorage.setItem(key, value)
    } else {
      localStorage.setItem(key, JSON.stringify(value))
    }
  },
  // 移除localStorage中的值
  remove: (key: string): void => {
    localStorage.removeItem(key)
  },
  // 清除localStorage中的所有值，保留界面语言
  clear: (): void => {
    const language = localStorage.getItem('harness_mate_language')
    localStorage.clear()
    if (language === 'zh-CN' || language === 'en-US') {
      localStorage.setItem('harness_mate_language', language)
    }
  },
}
