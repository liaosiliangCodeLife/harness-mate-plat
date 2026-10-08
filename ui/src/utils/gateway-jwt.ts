// 把字节转成 JWT 用的 base64url，不带填充
const bytesToBase64Url = (bytes: Uint8Array): string => {
  let binary = ''
  const chunkSize = 0x8000
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + chunkSize))
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

// 把 JSON 编码成 JWT 段
const encodeJson = (value: Record<string, unknown>): string => {
  return bytesToBase64Url(new TextEncoder().encode(JSON.stringify(value)))
}

// 用 gateway_key 做 HS256，签发 24 小时有效的网关 JWT
export const signGatewayJwt = async (gatewayKey: string, wsSessionId: string): Promise<string> => {
  const now = Math.floor(Date.now() / 1000)
  const header = encodeJson({ alg: 'HS256', typ: 'JWT' })
  const payload = encodeJson({
    ws_session_id: wsSessionId,
    exp: now + 24 * 60 * 60,
    iat: now,
  })
  const unsigned = `${header}.${payload}`
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(gatewayKey),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  )
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(unsigned))
  return `${unsigned}.${bytesToBase64Url(new Uint8Array(signature))}`
}

// 把 JWT 拼到网关地址的 token 查询参数上
export const buildGatewayUrl = (gatewayUrl: string, token: string): string => {
  const url = new URL(gatewayUrl)
  url.searchParams.set('token', token)
  return url.toString()
}
