import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { CreateResearchRequest, Research } from '@/types'
import { ResearchStatus } from '@/types'
import { researchApi } from '@/services/api'

export const useResearchStore = defineStore('research', () => {
  const researches = ref<Research[]>([])
  const currentResearch = ref<Research | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const activeResearches = computed(() =>
    researches.value.filter((r) =>
      r.status !== ResearchStatus.COMPLETED &&
      r.status !== ResearchStatus.ERROR &&
      r.status !== ResearchStatus.FAILED
    )
  )

  const completedResearches = computed(() =>
    researches.value.filter((r) => r.status === ResearchStatus.COMPLETED)
  )

  async function fetchResearches() {
    loading.value = true
    error.value = null
    try {
      const { data } = await researchApi.getAll()
      researches.value = data
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function fetchResearchById(id: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await researchApi.getById(id)
      currentResearch.value = data
      return data
    } catch (e) {
      error.value = (e as Error).message
      return null
    } finally {
      loading.value = false
    }
  }

  async function createResearch(request: CreateResearchRequest) {
    loading.value = true
    error.value = null
    try {
      const { data } = await researchApi.create(request)
      researches.value.unshift(data)
      currentResearch.value = data
      return data
    } catch (e) {
      error.value = (e as Error).message
      return null
    } finally {
      loading.value = false
    }
  }

  async function startResearch(id: string) {
    error.value = null
    try {
      await researchApi.start(id)
      await fetchResearchById(id)
    } catch (e) {
      error.value = (e as Error).message
      throw e
    }
  }

  async function confirmReport(id: string) {
    error.value = null
    try {
      await researchApi.confirmReport(id)
      await fetchResearchById(id)
    } catch (e) {
      error.value = (e as Error).message
      throw e
    }
  }

  async function deleteResearch(id: string) {
    try {
      await researchApi.delete(id)
      researches.value = researches.value.filter((r) => r.id !== id)
      if (currentResearch.value?.id === id) {
        currentResearch.value = null
      }
    } catch (e) {
      error.value = (e as Error).message
      throw e
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    researches,
    currentResearch,
    loading,
    error,
    activeResearches,
    completedResearches,
    fetchResearches,
    fetchResearchById,
    createResearch,
    startResearch,
    confirmReport,
    deleteResearch,
    clearError
  }
})
