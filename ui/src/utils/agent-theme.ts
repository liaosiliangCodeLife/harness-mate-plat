/*
 * 智能体类型对应的页面底色和空会话标签色。
 * HERMES 浅蓝，DEEPSEEK_HARNESS 浅紫，其它或空值浅灰。
 * 未知类型没有文案 key，调用方不要渲染类型标签。
 */

export type AgentTypeLabelKey = 'space.hermesAgent' | 'space.deepseekAgent'

export type AgentTypeTheme = {
  bg: string
  tagBg: string
  tagColor: string
  labelKey: AgentTypeLabelKey | null
}

const hermesTheme: AgentTypeTheme = {
  bg: '#EFF6FF',
  tagBg: '#EFF6FF',
  tagColor: '#1D4ED8',
  labelKey: 'space.hermesAgent',
}

const deepseekTheme: AgentTypeTheme = {
  bg: '#F5F3FF',
  tagBg: '#F5F3FF',
  tagColor: '#6D28D9',
  labelKey: 'space.deepseekAgent',
}

const fallbackTheme: AgentTypeTheme = {
  bg: '#FAFAFA',
  tagBg: '#FAFAFA',
  tagColor: '#52525B',
  labelKey: null,
}

/*
 * @Function: agentTypeTheme(agentType?: string)
 * @Description //按智能体类型返回详情页背景和类型标签颜色
 * @Param: agentType: 智能体类型，HERMES 或 DEEPSEEK_HARNESS，可空
 * @return：背景色、标签底色、标签文字色，以及 i18n key；未知类型的 labelKey 为 null
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
