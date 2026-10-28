/*
 * 生成 UUID v4。
 * crypto.randomUUID 只在安全上下文（https / localhost）里存在，
 * 用 http 打开页面时它是 undefined，直接调用会抛 TypeError。
 * 这里优先用原生实现，拿不到时退化成等价的随机字符串。
 */
export const genUuid = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  const hex = '0123456789abcdef'
  let out = ''
  for (let i = 0; i < 36; i += 1) {
    if (i === 8 || i === 13 || i === 18 || i === 23) {
      out += '-'
    } else if (i === 14) {
      out += '4'
    } else if (i === 19) {
      out += hex[((Math.random() * 4) | 0) + 8]
    } else {
      out += hex[(Math.random() * 16) | 0]
    }
  }
  return out
}
