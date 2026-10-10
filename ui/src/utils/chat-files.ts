/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //从消息正文和 message_info.files 里取出可渲染的文件
 * @File: chat-files.ts
 * @Time: 2026/10/07 21:10:00
 * @All Rights Reserve By Brtc
 */
import type { ChatFile, ChatMediaKind } from '@/models/agent-message'

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'])
const AUDIO_EXTENSIONS = new Set(['mp3', 'm4a', 'wav', 'ogg', 'opus', 'flac', 'aac'])
const VIDEO_EXTENSIONS = new Set(['mp4', 'mov', 'webm', 'mkv', 'avi'])
const FILE_EXTENSIONS = new Set([
  ...IMAGE_EXTENSIONS,
  ...AUDIO_EXTENSIONS,
  ...VIDEO_EXTENSIONS,
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
  'zip',
  'rar',
  '7z',
  'tar',
  'gz',
  'tgz',
  'bz2',
  'tbz',
  'tbz2',
  'xz',
  'txz',
  'zst',
  'zipx',
  'cab',
  'jar',
  'war',
])
const MEDIA_KINDS = new Set<ChatMediaKind>(['image', 'audio', 'video', 'file'])

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
 * @Function: mediaKindFor(url, mediaType, isImage)
 * @Description //按 media_type、MIME 前缀和扩展名决定渲染类型，图片、音频、视频优先于普通文件
 * @Date :2026/10/09 08:05:00
 * @Param: url: 文件地址，字符串；mediaType: reply 里的 media_type 或 MIME，可空；isImage: 历史数据里的图片标记，可空
 * @return：image、audio、video 或 file
 */
const mediaKindFor = (url: string, mediaType = '', isImage = false): ChatMediaKind => {
  const kind = mediaType.trim().toLowerCase()
  if (kind === 'audio' || kind.startsWith('audio/')) {
    return 'audio'
  }
  if (kind === 'video' || kind.startsWith('video/')) {
    return 'video'
  }
  if (kind === 'image' || kind.startsWith('image/') || isImage) {
    return 'image'
  }
  const extension = extensionFromUrl(url)
  if (IMAGE_EXTENSIONS.has(extension)) {
    return 'image'
  }
  if (VIDEO_EXTENSIONS.has(extension)) {
    return 'video'
  }
  if (AUDIO_EXTENSIONS.has(extension)) {
    return 'audio'
  }
  return 'file'
}

/*
 * @Author Leon-liao
 * @Function: asChatFile(file)
 * @Description //补齐 media_kind，并让 is_image 与它保持一致
 * @Date :2026/10/09 08:05:00
 * @Param: file: 名称、地址，以及可选的类型、图片标记和大小
 * @return：可渲染的 ChatFile
 */
const asChatFile = (file: {
  name: string
  url: string
  media_kind?: ChatMediaKind
  media_type?: string
  is_image?: boolean
  size?: number
}): ChatFile => {
  const mediaKind = file.media_kind || mediaKindFor(file.url, file.media_type || '', file.is_image === true)
  return {
    name: file.name,
    url: file.url,
    media_kind: mediaKind,
    is_image: mediaKind === 'image',
    size: file.size,
  }
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
 * @Param: payload.url: 文件地址；payload.file_name: 文件名，可空；payload.media_type: image、audio、video、file 或 MIME，可空
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
  return asChatFile({ name, url, media_type: mediaType })
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
    const storedKind = typeof record.media_kind === 'string' ? record.media_kind : ''
    const mediaType = typeof record.media_type === 'string' ? record.media_type : ''
    files.push(
      asChatFile({
        name,
        url,
        media_kind: MEDIA_KINDS.has(storedKind as ChatMediaKind)
          ? (storedKind as ChatMediaKind)
          : undefined,
        media_type: mediaType,
        is_image: record.is_image === true,
        size,
      }),
    )
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
    files.push(
      asChatFile({
        ...file,
        url,
        name: file.name?.trim() || fileNameFromUrl(url),
      }),
    )
  })
  const text = (content || '').replace(
    /(!?)\[((?:\\.|[^\]])*)\]\(([^)\s]+)\)/g,
    (full, bang: string, label: string, rawUrl: string) => {
      const url = String(rawUrl || '').trim()
      const extension = extensionFromUrl(url)
      if (!url || !(bang === '!' || FILE_EXTENSIONS.has(extension))) {
        return full
      }
      if (!seen.has(url)) {
        seen.add(url)
        files.push(
          asChatFile({
            name: unescapeLabel(label) || fileNameFromUrl(url),
            url,
            media_kind: bang === '!' ? 'image' : mediaKindFor(url),
          }),
        )
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
