import axios from 'axios'
import type {
  ChatHistoryResponse,
  ChatMessage,
  CreateResearchRequest,
  Research,
  ResearchReportResponse,
  WikiLintResult,
  WikiLog,
  WikiPage,
  WikiSaveResponse,
  WikiSearchResult,
  WorkflowState
} from '@/types'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message || 'Request failed'
    return Promise.reject(new Error(message))
  }
)

export const researchApi = {
  getAll: () => api.get<Research[]>('/research'),

  getById: (id: string) => api.get<Research>(`/research/${id}`),

  create: (data: CreateResearchRequest) => api.post<Research>('/research', data),

  start: (researchId: string) => api.post(`/research/${researchId}/start`),

  confirmReport: (researchId: string) => api.post(`/research/${researchId}/confirm-report`),

  delete: (id: string) => api.delete(`/research/${id}`)
}

export const workflowApi = {
  start: (researchId: string) => researchApi.start(researchId),

  getState: (researchId: string) => api.get<WorkflowState>(`/workflow/${researchId}/state`),

  getReport: (researchId: string) => api.get<ResearchReportResponse>(`/workflow/${researchId}/report`)
}

export const chatApi = {
  getHistory: (researchId: string) => api.get<ChatHistoryResponse>(`/research/${researchId}/chat`),

  stream: async (
    researchId: string,
    message: string,
    handlers: {
      onUserMessage?: (message: ChatMessage) => void
      onDelta?: (chunk: string) => void
      onDone?: (message: ChatMessage) => void
      onError?: (message: string) => void
    }
  ) => {
    const response = await fetch(`/api/v1/research/${researchId}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    })

    if (!response.ok || !response.body) {
      const detail = await response.text()
      throw new Error(detail || 'Chat request failed')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const parseEvent = (raw: string) => {
      const lines = raw.split('\n')
      const event = lines.find((line) => line.startsWith('event:'))?.replace('event:', '').trim()
      const data = lines
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.replace('data:', '').trim())
        .join('\n')

      if (!event || !data) return
      const payload = JSON.parse(data)
      if (event === 'user_message') handlers.onUserMessage?.(payload.message)
      if (event === 'delta') handlers.onDelta?.(payload.chunk ?? '')
      if (event === 'done') handlers.onDone?.(payload.message)
      if (event === 'error') handlers.onError?.(payload.detail ?? 'Chat stream failed')
    }

    while (true) {
      const { value, done } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const events = buffer.split('\n\n')
      buffer = events.pop() ?? ''
      events.forEach(parseEvent)
    }

    if (buffer.trim()) parseEvent(buffer)
  }
}

export const wikiApi = {
  getPages: () => api.get<WikiPage[]>('/wiki/pages'),

  getPage: (id: string) => api.get<WikiPage>(`/wiki/pages/${id}`),

  search: (query: string) => api.get<WikiSearchResult[]>('/wiki/search', { params: { query } }),

  getLogs: () => api.get<WikiLog[]>('/wiki/logs'),

  reindex: () => api.post<{ count: number; message: string }>('/wiki/reindex'),

  lint: () => api.post<WikiLintResult[]>('/wiki/lint'),

  saveResearch: (researchId: string) => api.post<WikiSaveResponse>(`/wiki/research/${researchId}/save`)
}

export const reportApi = {
  getById: (id: string) => workflowApi.getReport(id)
}

export default api
