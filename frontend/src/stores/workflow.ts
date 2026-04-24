import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { WorkflowStep } from '@/types'
import { StepStatus } from '@/types'

export const useWorkflowStore = defineStore('workflow', () => {
  const steps = ref<WorkflowStep[]>([])
  const currentStepIndex = ref(0)

  const currentStep = computed(() => steps.value[currentStepIndex.value] ?? null)

  const progress = computed(() => {
    if (steps.value.length === 0) return 0
    const completed = steps.value.filter((s) => s.status === StepStatus.COMPLETED).length
    return Math.round((completed / steps.value.length) * 100)
  })

  const isRunning = computed(() =>
    steps.value.some((s) => s.status === StepStatus.RUNNING)
  )

  function setSteps(newSteps: WorkflowStep[]) {
    steps.value = newSteps
    currentStepIndex.value = 0
  }

  function advanceStep() {
    if (currentStepIndex.value < steps.value.length - 1) {
      steps.value[currentStepIndex.value].status = StepStatus.COMPLETED
      currentStepIndex.value++
      steps.value[currentStepIndex.value].status = StepStatus.RUNNING
    }
  }

  function failCurrentStep() {
    if (currentStep.value) {
      currentStep.value.status = StepStatus.FAILED
    }
  }

  function reset() {
    steps.value = []
    currentStepIndex.value = 0
  }

  return {
    steps,
    currentStepIndex,
    currentStep,
    progress,
    isRunning,
    setSteps,
    advanceStep,
    failCurrentStep,
    reset
  }
})
