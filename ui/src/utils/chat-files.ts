/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //从消息正文和 message_info.files 里取出可渲染的文件
 * @File: chat-files.ts
 * @Time: 2026/10/07 21:10:00
 * @All Rights Reserve By Brtc
 */
import type { ChatFile } from '@/models/agent-message'

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'])
const FILE_EXTENSIONS = new Set([
  ...IMAGE_EXTENSIONS,
  'txt',
  'markdown',
  'md',
  'pdf',
  'html',
  'htm',
  'xlsx',
  'xls',
  'doc',
  'docx',
  'csv',
])

/*
 * @Author Leon-liao
 * @Function: extensionFromUrl(url: string)
 * @Description //从地址路径里取出小写扩展名，忽略查询参数
 * @Date :2026/10/07 21:10:00
 * @Param: url: 文件地址，字符串
 * @return：扩展名；没有扩展名时返回空字符串
 */
const extensionFromUrl = (url: string) => {
  const clean = url.split('?')[0]?.split('#')[0] || ''
  const name = clean.split('/').pop() || ''
  const index = name.lastIndexOf('.')
  if (index < 0 || index === name.length - 1) {
    return ''
  }
  return name.slice(index + 1).toLowerCase()
}

/*
 * @Author Leon-liao
 * @Function: fileNameFromUrl(url: string)
 * @Description //用地址最后一段作为文件名
 * @Date :2026/10/07 21:10:00
 * @Param: url: 文件地址，字符串
 * @return：文件名；解析不到时返回「文件」
 */
const fileNameFromUrl = (url: string) => {
  const clean = url.split('?')[0]?.split('#')[0] || ''
  const name = decodeURIComponent(clean.split('/').pop() || '')
  return name || '文件'
}

/*
 * @Author Leon-liao
 * @Function: unescapeLabel(label: string)
 * @Description //还原 markdown 链接文字里被转义的方括号
 * @Date :2026/10/07 21:10:00
 * @Param: label: 链接文字，字符串
 * @return：还原后的文字
 */
const unescapeLabel = (label: string) => {
  return label.replace(/\\([\\[\]])/g, '$1').trim()
}

/*
 * @Author Leon-liao
 * @Function: normalizeChatFiles(value: unknown)
 * @Description //把 message_info.files 收成可渲染的文件列表，丢掉没有地址的项
 * @Date :2026/10/07 21:10:00
 * @Param: value: 接口里的 files 字段，结构不保证
 * @return：文件列表
 */
/*
 * @Author Leon-liao
 * @Function: chatFileFromReply(payload)
 * @Description //把 Hermes reply 里扁平的 url / file_name / media_type 收成一个 ChatFile
 * @Date :2026/10/07 22:36:30
 * @Param: payload.url: 文件地址；payload.file_name: 文件名，可空；payload.media_type: 类型，image 表示图片，可空
 * @return：可渲染的文件；地址为空或不是 http(s) 时返回 null
 */
export const chatFileFromReply = (payload: {
  url?: unknown
  file_name?: unknown
  media_type?: unknown
}): ChatFile | null => {
  if (typeof payload.url !== 'string') {
    return null
  }
  const url = payload.url.trim()
  if (!url) {
    return null
  }
  try {
    const parsed = new URL(url)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
      return null
    }
  } catch {
    return null
  }
  const rawName = typeof payload.file_name === 'string' ? payload.file_name.trim() : ''
  const name = rawName || fileNameFromUrl(url)
  const mediaType =
    typeof payload.media_type === 'string' ? payload.media_type.trim().toLowerCase() : ''
  const isImage =
    mediaType === 'image' ||
    mediaType.startsWith('image/') ||
    IMAGE_EXTENSIONS.has(extensionFromUrl(url))
  return { name, url, is_image: isImage }
}

export const normalizeChatFiles = (value: unknown): ChatFile[] => {
  if (!Array.isArray(value)) {
    return []
  }
  const files: ChatFile[] = []
  value.forEach((item) => {
    if (!item || typeof item !== 'object') {
      return
    }
    const record = item as Record<string, unknown>
    const url = typeof record.url === 'string' ? record.url.trim() : ''
    if (!url) {
      return
    }
    const name =
      typeof record.name === 'string' && record.name.trim()
        ? record.name.trim()
        : fileNameFromUrl(url)
    const size = typeof record.size === 'number' && record.size >= 0 ? record.size : undefined
    files.push({
      name,
      url,
      is_image: record.is_image === true || IMAGE_EXTENSIONS.has(extensionFromUrl(url)),
      size,
    })
  })
  return files
}

/*
 * @Author Leon-liao
 * @Function: splitMessageFiles(content: string, explicit?: ChatFile[])
 * @Description //合并结构化文件和正文里的文件链接，正文去掉这些链接以免渲染两遍
 * @Date :2026/10/07 21:10:00
 * @Param: content: 消息正文，字符串；explicit: message_info.files 或本地附件，可空
 * @return：files 为要渲染的文件，text 为去掉文件链接后的正文
 */
export const splitMessageFiles = (content: string, explicit?: ChatFile[]) => {
  const files: ChatFile[] = []
  const seen = new Set<string>()
  ;(explicit || []).forEach((file) => {
    const url = file.url?.trim()
    if (!url || seen.has(url)) {
      return
    }
    seen.add(url)
    files.push({ ...file, url, name: file.name?.trim() || fileNameFromUrl(url) })
  })
  const text = (content || '').replace(
    /(!?)\[((?:\\.|[^\]])*)\]\(([^)\s]+)\)/g,
    (full, bang: string, label: string, rawUrl: string) => {
      const url = String(rawUrl || '').trim()
      const extension = extensionFromUrl(url)
      const isImage = bang === '!' || IMAGE_EXTENSIONS.has(extension)
      const isFile = isImage || FILE_EXTENSIONS.has(extension)
      if (!url || !isFile) {
        return full
      }
      if (!seen.has(url)) {
        seen.add(url)
        files.push({
          name: unescapeLabel(label) || fileNameFromUrl(url),
          url,
          is_image: isImage,
        })
      }
      return ''
    },
  )
  return {
    files,
    text: text
      .replace(/[ \t]+\n/g, '\n')
      .replace(/\n{3,}/g, '\n\n')
      .trim(),
  }
}

/*
 * @Author Leon-liao
 * @Function: formatFileSize(size?: number)
 * @Description //把字节数格式化成 B / KB / MB
 * @Date :2026/10/07 21:10:00
 * @Param: size: 字节数，数字，可空
 * @return：展示文案；没有大小时返回空字符串
 */
export const formatFileSize = (size?: number) => {
  if (typeof size !== 'number' || size < 0) {
    return ''
  }
  if (size < 1024) {
    return `${size} B`
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`
  }
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}
