/*
 * This is the projet for brtc R&D Platform
 * @Author Leon-liao <liaosiliang@alltman.com>
 * @Description //聊天附件上传：扩展名白名单、大小上限与分类判定（主站与分享页共用）
 * @File: chat-upload.ts
 * @Time: 2026/10/28 11:22:40
 * @All Rights Reserve By Brtc
 */

export const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg'])

export const DOCUMENT_EXTENSIONS = new Set([
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

export const ARCHIVE_EXTENSIONS = new Set([
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

export const UPLOAD_ACCEPT = [...IMAGE_EXTENSIONS, ...DOCUMENT_EXTENSIONS, ...ARCHIVE_EXTENSIONS]
  .map((item) => `.${item}`)
  .join(',')

export const MAX_UPLOAD_BYTES = 15 * 1024 * 1024
export const MAX_ARCHIVE_UPLOAD_BYTES = 100 * 1024 * 1024
export const MAX_ATTACHMENT_COUNT = 5

/*
 * @Author Leon-liao
 * @Function: fileExtension(name)
 * @Description //取出文件扩展名（小写），无扩展名时返回空串
 * @Date :2026/10/28 11:22:40
 * @Param: name: 文件名，字符串
 * @return：扩展名小写字符串
 */
export const fileExtension = (name: string) => {
  const index = name.lastIndexOf('.')
  if (index < 0 || index === name.length - 1) {
    return ''
  }
  return name.slice(index + 1).toLowerCase()
}

/*
 * @Author Leon-liao
 * @Function: classifyUpload(file)
 * @Description //按扩展名判定是否图片/压缩包/允许上传，规则与主站聊天卡片一致
 * @Date :2026/10/28 11:22:40
 * @Param: file: 浏览器 File 对象
 * @return：{ isImage, isArchive, allowed }
 */
export const classifyUpload = (file: File) => {
  const extension = fileExtension(file.name)
  const isImage = IMAGE_EXTENSIONS.has(extension)
  const isArchive = ARCHIVE_EXTENSIONS.has(extension)
  const allowed =
    isImage || DOCUMENT_EXTENSIONS.has(extension) || isArchive
  return { isImage, isArchive, allowed }
}
