import { ref } from 'vue'
import { Message } from '@arco-design/web-vue'
import {
  createAgent,
  createAgentConversation,
  deleteAgent,
  deleteAgentConversation,
  getAgent,
  getAgentsWithPage,
  getConversationsWithPage,
  updateAgent,
  updateAgentConversation,
} from '@/services/agent'
import type {
  Agent,
  CreateAgentRequest,
  GetAgentsWithPageResponse,
  UpdateAgentRequest,
} from '@/models/agent'
import type {
  CreateAgentConversationRequest,
  GetAgentConversationsWithPageResponse,
  UpdateAgentConversationRequest,
} from '@/models/agent-conversation'

// 构造一份独立的默认分页器，避免多次初始化时共享同一个对象
const buildDefaultPaginator = () => ({
  current_page: 1,
  page_size: 20,
  total_page: 0,
  total_record: 0,
})

export const useGetAgentsWithPage = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)
  const agents = ref<GetAgentsWithPageResponse['data']['list']>([])
  const paginator = ref(buildDefaultPaginator())

  // 2.定义加载数据函数
  const loadAgents = async (init: boolean = false, search_word: string = '') => {
    // 2.1 判断是否是初始化，如果是的话则先初始化分页器
    if (init) {
      paginator.value = buildDefaultPaginator()
    } else if (paginator.value.current_page > paginator.value.total_page) {
      return
    }

    // 2.2 加载数据并更新
    try {
      loading.value = true
      const resp = await getAgentsWithPage({
        current_page: paginator.value.current_page,
        page_size: paginator.value.page_size,
        search_word,
      })
      const data = resp.data

      // 2.3 更新分页器
      paginator.value = data.paginator

      // 2.4 判断是否存在更多数据
      if (paginator.value.current_page <= paginator.value.total_page) {
        paginator.value.current_page += 1
      }

      // 2.5 追加或者是覆盖数据
      if (init) {
        agents.value = data.list
      } else {
        agents.value.push(...data.list)
      }
    } finally {
      loading.value = false
    }
  }

  return { loading, agents, paginator, loadAgents }
}

export const useCreateAgent = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义创建智能体处理器
  const handleCreateAgent = async (req: CreateAgentRequest) => {
    try {
      loading.value = true
      const resp = await createAgent(req)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleCreateAgent }
}

export const useUpdateAgent = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义更新智能体处理器
  const handleUpdateAgent = async (agent_id: string, req: UpdateAgentRequest) => {
    try {
      loading.value = true
      const resp = await updateAgent(agent_id, req)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleUpdateAgent }
}

export const useDeleteAgent = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义删除智能体处理器
  const handleDeleteAgent = async (agent_id: string) => {
    try {
      loading.value = true
      const resp = await deleteAgent(agent_id)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleDeleteAgent }
}

export const useGetAgent = () => {
  // 1.定义hooks所需的基础数据
  const loading = ref(false)
  const agent = ref<Agent | null>(null)

  // 2.定义加载数据所需的函数
  const loadAgent = async (agent_id: string) => {
    try {
      loading.value = true
      const resp = await getAgent(agent_id)
      agent.value = resp.data
    } finally {
      loading.value = false
    }
  }

  return { loading, agent, loadAgent }
}

export const useGetAgentConversations = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)
  const conversations = ref<GetAgentConversationsWithPageResponse['data']['list']>([])
  const paginator = ref(buildDefaultPaginator())

  // 2.定义加载数据函数
  const loadConversations = async (
    agent_id: string,
    init: boolean = false,
    search_word: string = '',
  ) => {
    // 2.1 判断是否是初始化，如果是的话则先初始化分页器
    if (init) {
      paginator.value = buildDefaultPaginator()
    } else if (paginator.value.current_page > paginator.value.total_page) {
      return
    }

    // 2.2 加载数据并更新
    try {
      loading.value = true
      const resp = await getConversationsWithPage(agent_id, {
        current_page: paginator.value.current_page,
        page_size: paginator.value.page_size,
        search_word,
      })
      const data = resp.data

      // 2.3 更新分页器
      paginator.value = data.paginator

      // 2.4 判断是否存在更多数据
      if (paginator.value.current_page <= paginator.value.total_page) {
        paginator.value.current_page += 1
      }

      // 2.5 追加或者是覆盖数据
      if (init) {
        conversations.value = data.list
      } else {
        conversations.value.push(...data.list)
      }
    } finally {
      loading.value = false
    }
  }

  return { loading, conversations, paginator, loadConversations }
}

export const useCreateAgentConversation = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义创建会话处理器
  const handleCreateAgentConversation = async (
    agent_id: string,
    req: CreateAgentConversationRequest,
  ) => {
    try {
      loading.value = true
      await createAgentConversation(agent_id, req)
      Message.success('会话已创建')
    } finally {
      loading.value = false
    }
  }

  return { loading, handleCreateAgentConversation }
}

export const useUpdateAgentConversation = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义更新会话处理器，只提交调用方传入的字段
  const handleUpdateAgentConversation = async (
    agent_id: string,
    conversation_id: string,
    req: UpdateAgentConversationRequest,
  ) => {
    try {
      loading.value = true
      const resp = await updateAgentConversation(agent_id, conversation_id, req)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleUpdateAgentConversation }
}

export const useDeleteAgentConversation = () => {
  // 1.定义hooks所需数据
  const loading = ref(false)

  // 2.定义删除会话处理器
  const handleDeleteAgentConversation = async (agent_id: string, conversation_id: string) => {
    try {
      loading.value = true
      const resp = await deleteAgentConversation(agent_id, conversation_id)
      Message.success(resp.message)
    } finally {
      loading.value = false
    }
  }

  return { loading, handleDeleteAgentConversation }
}
