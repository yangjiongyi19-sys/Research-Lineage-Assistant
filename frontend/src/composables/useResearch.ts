import { ref } from 'vue'
import { useResearchStore } from '@/stores/research'
import type { CreateResearchRequest } from '@/types'

export function useResearch() {
  const store = useResearchStore()
  const searchQuery = ref('')

  async function search() {
    if (!searchQuery.value.trim()) return null
    const request: CreateResearchRequest = {
      title: searchQuery.value.trim(),
      query: searchQuery.value.trim()
    }
    const result = await store.createResearch(request)
    if (result) {
      searchQuery.value = ''
    }
    return result
  }

  async function loadResearch(id: string) {
    await store.fetchResearchById(id)
    return store.currentResearch
  }

  async function loadResearchList() {
    await store.fetchResearches()
    return store.researches
  }

  async function chat(researchId: string, message: string) {
    if (!message.trim()) return
  }

  return {
    searchQuery,
    search,
    loadResearch,
    loadResearchList,
    chat,
    researches: store.researches,
    currentResearch: store.currentResearch,
    loading: store.loading,
    error: store.error
  }
}
