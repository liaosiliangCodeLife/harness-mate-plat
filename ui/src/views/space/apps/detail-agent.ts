import type { InjectionKey, Ref } from 'vue'
import type { Agent } from '@/models/agent'

// 详情页布局与会话卡片共享同一份智能体，网关连接参数与顶部展示一致
export const detailAgentKey: InjectionKey<Ref<Agent | null>> = Symbol('detailAgent')

// 布局页新建会话成功后递增，会话列表据此按当前搜索词重载第一页
export const conversationListVersionKey: InjectionKey<Ref<number>> = Symbol(
  'conversationListVersion',
)

// 会话通道连上后刷新详情里的智能体，让头部和卡片读到同一次在线结果
export const reloadDetailAgentKey: InjectionKey<() => void> = Symbol('reloadDetailAgent')
