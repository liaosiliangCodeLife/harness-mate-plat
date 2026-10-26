/*
 * 智能体类型对应的浅色背景。
 * HERMES 浅蓝，DEEPSEEK_HARNESS 浅紫，其它或空值浅灰。
 */

export type AgentTypeTheme = {
  bg: string
}

const hermesTheme: AgentTypeTheme = {
  bg: '#EFF6FF',
}

const deepseekTheme: AgentTypeTheme = {
  bg: '#F5F3FF',
}

const fallbackTheme: AgentTypeTheme = {
  bg: '#FAFAFA',
}

/*
 * @Function: agentTypeTheme(agentType?: string)
 * @Description //按智能体类型返回页面和空会话卡片使用的背景色
 * @Param: agentType: 智能体类型，HERMES 或 DEEPSEEK_HARNESS，可空
 * @return：背景色。未知类型为浅灰
 */
export const agentTypeTheme = (agentType?: string): AgentTypeTheme => {
  const value = agentType?.trim() ?? ''
  if (value === 'HERMES') {
    return hermesTheme
  }
  if (value === 'DEEPSEEK_HARNESS') {
    return deepseekTheme
  }
  return fallbackTheme
}
