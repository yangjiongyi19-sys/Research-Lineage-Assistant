<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useResearchStore } from '@/stores/research'
import { chatApi, wikiApi } from '@/services/api'
import {
  ResearchStatus,
  type ChatMessage as ChatMessageType,
  type ProgressLog,
  type StreamEvent,
  type WorkflowTask
} from '@/types'
import AppLoading from '@/components/common/AppLoading.vue'
import ChatMessage from '@/components/research/ChatMessage.vue'

const route = useRoute()
const researchStore = useResearchStore()
const { currentResearch, loading, error } = storeToRefs(researchStore)

const polling = ref<number | null>(null)
const eventSource = ref<EventSource | null>(null)
const streamReport = ref('')
const liveLogs = ref<ProgressLog[]>([])
const liveTasks = ref<WorkflowTask[]>([])
const reportCollapsed = ref(false)
const processCollapsed = ref(false)
const chatMessages = ref<ChatMessageType[]>([])
const chatInput = ref('')
const chatStreaming = ref(false)
const chatError = ref<string | null>(null)
const chatEndRef = ref<HTMLElement | null>(null)
const wikiSaving = ref(false)
const wikiSaveMessage = ref<string | null>(null)
const wikiSaveError = ref<string | null>(null)

const researchId = computed(() => route.params.id as string)
const metadata = computed(() => currentResearch.value?.metadata ?? null)
const tasks = computed(() => liveTasks.value.length ? liveTasks.value : metadata.value?.tasks ?? [])
const logs = computed(() => liveLogs.value.length ? liveLogs.value : metadata.value?.logs ?? [])
const recentLogs = computed(() => logs.value.slice(-8).reverse())
const finalReport = computed(() => currentResearch.value?.final_report || streamReport.value)
const sources = computed(() => currentResearch.value?.search_results ?? [])
const isAwaitingReport = computed(() => currentResearch.value?.status === ResearchStatus.AWAITING_REPORT)
const isCompleted = computed(() => currentResearch.value?.status === ResearchStatus.COMPLETED)
const isError = computed(() => currentResearch.value?.status === ResearchStatus.ERROR || currentResearch.value?.status === ResearchStatus.FAILED)
const canChat = computed(() => isCompleted.value && Boolean(finalReport.value))
const isTerminal = computed(() => isAwaitingReport.value || isCompleted.value || isError.value)
const wikiPages = computed(() => (metadata.value?.wiki_pages as Array<{ title: string; path: string }> | undefined) ?? [])
const wikiSufficiency = computed(() => (metadata.value?.wiki_sufficiency as string | undefined) ?? 'insufficient')
const wikiUpdatedPages = computed(() => (metadata.value?.wiki_updated_pages as string[] | undefined) ?? [])

const completedTaskCount = computed(() => tasks.value.filter((task) => task.status === 'completed').length)
const sourceSummary = computed(() => {
  const counts = sources.value.reduce<Record<string, number>>((acc, source) => {
    acc[source.source] = (acc[source.source] ?? 0) + 1
    return acc
  }, {})
  return Object.entries(counts).map(([source, count]) => `${source}: ${count}`).join(' / ')
})

const progress = computed(() => {
  if (isCompleted.value) return 100
  if (isAwaitingReport.value) return 90
  if (tasks.value.length) {
    return Math.round((completedTaskCount.value / tasks.value.length) * 100)
  }
  return 0
})

const phaseTitle = computed(() => {
  if (isCompleted.value) return 'Final report is ready'
  if (isAwaitingReport.value) return 'Review the completed tasks'
  if (isError.value) return 'Research stopped'
  return 'Research is running'
})

const phaseDescription = computed(() => {
  if (isCompleted.value) return 'The task list has been replaced by the final report. You can collapse it or ask follow-up questions.'
  if (isAwaitingReport.value) return 'Search, analysis, and synthesis are complete. Confirm when you want the agent to write the final report.'
  if (isError.value) return currentResearch.value?.error_message || 'The workflow encountered an error.'
  return 'The agent is planning, searching, analyzing, and synthesizing evidence.'
})

async function refresh() {
  await researchStore.fetchResearchById(researchId.value)
  hydrateFromMetadata()
  if (canChat.value && !chatStreaming.value) {
    await loadChatHistory()
  }
  if (isTerminal.value) {
    stopPolling()
    stopStream()
  }
}

function hydrateFromMetadata() {
  const meta = currentResearch.value?.metadata
  if (!meta) return
  if (meta.tasks?.length) liveTasks.value = meta.tasks
  if (meta.logs?.length) liveLogs.value = meta.logs
  if (!streamReport.value && meta.stream_events?.length) {
    streamReport.value = meta.stream_events
      .filter((event: StreamEvent) => event.type === 'report_chunk')
      .map((event: StreamEvent) => event.payload?.chunk ?? '')
      .join('')
  }
}

function startPolling() {
  stopPolling()
  polling.value = window.setInterval(refresh, 2000)
}

function stopPolling() {
  if (polling.value !== null) {
    window.clearInterval(polling.value)
    polling.value = null
  }
}

function startStream({ resetReport = false }: { resetReport?: boolean } = {}) {
  stopStream()
  if (resetReport) streamReport.value = ''
  eventSource.value = new EventSource(`/api/v1/workflow/${researchId.value}/stream`)

  eventSource.value.addEventListener('state', (event) => {
    const payload = JSON.parse((event as MessageEvent).data)
    if (payload.tasks) liveTasks.value = payload.tasks
    if (payload.logs) liveLogs.value = payload.logs
    if (payload.final_report) streamReport.value = payload.final_report
    if (
      payload.status === ResearchStatus.AWAITING_REPORT ||
      payload.status === ResearchStatus.COMPLETED ||
      payload.status === ResearchStatus.ERROR
    ) {
      refresh()
      stopStream()
    }
  })

  eventSource.value.addEventListener('report_chunk', (event) => {
    const payload = JSON.parse((event as MessageEvent).data)
    streamReport.value += payload.payload?.chunk ?? ''
  })

  eventSource.value.addEventListener('workflow_failed', () => {
    refresh()
    stopStream()
  })
}

function stopStream() {
  eventSource.value?.close()
  eventSource.value = null
}

async function startWorkflow() {
  await researchStore.startResearch(researchId.value)
  await refresh()
  startStream({ resetReport: true })
  startPolling()
}

async function confirmReport() {
  await researchStore.confirmReport(researchId.value)
  reportCollapsed.value = false
  streamReport.value = ''
  startStream({ resetReport: true })
  startPolling()
}

async function loadChatHistory() {
  try {
    const { data } = await chatApi.getHistory(researchId.value)
    chatMessages.value = data.messages
    await scrollChatToEnd()
  } catch (e) {
    chatError.value = (e as Error).message
  }
}

async function sendChatMessage() {
  const message = chatInput.value.trim()
  if (!message || chatStreaming.value || !canChat.value) return

  chatInput.value = ''
  chatError.value = null
  chatStreaming.value = true

  const assistantMessage: ChatMessageType = {
    id: `streaming-${Date.now()}`,
    role: 'assistant',
    content: '',
    created_at: new Date().toISOString()
  }
  let assistantAdded = false

  try {
    await chatApi.stream(researchId.value, message, {
      onUserMessage: async (savedMessage) => {
        chatMessages.value.push(savedMessage)
        await scrollChatToEnd()
      },
      onDelta: async (chunk) => {
        if (!assistantAdded) {
          chatMessages.value.push(assistantMessage)
          assistantAdded = true
        }
        assistantMessage.content += chunk
        await scrollChatToEnd()
      },
      onDone: async (savedMessage) => {
        if (assistantAdded) {
          Object.assign(assistantMessage, savedMessage)
        } else {
          chatMessages.value.push(savedMessage)
        }
        await scrollChatToEnd()
      },
      onError: (message) => {
        chatError.value = message
      }
    })
  } catch (e) {
    chatError.value = (e as Error).message
  } finally {
    chatStreaming.value = false
  }
}

async function saveReportToWiki() {
  if (!currentResearch.value?.id || wikiSaving.value) return
  wikiSaving.value = true
  wikiSaveError.value = null
  wikiSaveMessage.value = null
  try {
    const { data } = await wikiApi.saveResearch(currentResearch.value.id)
    wikiSaveMessage.value = data.message
    await refresh()
  } catch (e) {
    wikiSaveError.value = (e as Error).message
  } finally {
    wikiSaving.value = false
  }
}

async function scrollChatToEnd() {
  await nextTick()
  chatEndRef.value?.scrollIntoView({ behavior: 'smooth', block: 'end' })
}

function taskClass(status: string) {
  return `research-detail__task--${status}`
}

onMounted(async () => {
  await refresh()
  hydrateFromMetadata()
  if (canChat.value) await loadChatHistory()
  if (!isTerminal.value) {
    startStream()
    startPolling()
  }
})

onBeforeUnmount(() => {
  stopPolling()
  stopStream()
})
</script>

<template>
  <div class="research-detail">
    <AppLoading v-if="loading && !currentResearch" text="Loading research..." size="large" />
    <p v-else-if="error" class="research-detail__error">{{ error }}</p>

    <template v-else-if="currentResearch">
      <section class="research-detail__hero">
        <div>
          <p class="research-detail__eyebrow">Research thread</p>
          <h1>{{ currentResearch.title }}</h1>
          <p>{{ currentResearch.query }}</p>
        </div>
        <div class="research-detail__status-pill" :class="`research-detail__status-pill--${currentResearch.status}`">
          {{ currentResearch.status.replace('_', ' ') }}
        </div>
      </section>

      <section class="research-detail__phase">
        <div class="research-detail__phase-copy">
          <h2>{{ phaseTitle }}</h2>
          <p>{{ phaseDescription }}</p>
        </div>
        <div class="research-detail__meter">
          <span>{{ progress }}%</span>
          <div>
            <i :style="{ width: `${progress}%` }" />
          </div>
        </div>
      </section>

      <section v-if="!finalReport" class="research-detail__panel research-detail__process">
        <div class="research-detail__panel-header">
          <div>
            <h2>Task list</h2>
            <p>{{ completedTaskCount }} of {{ tasks.length }} subtasks completed</p>
          </div>
          <button
            v-if="currentResearch.status === ResearchStatus.PENDING"
            class="research-detail__primary"
            :disabled="loading"
            @click="startWorkflow"
          >
            Start workflow
          </button>
          <button
            v-else-if="isAwaitingReport"
            class="research-detail__primary"
            :disabled="loading"
            @click="confirmReport"
          >
            Confirm and generate report
          </button>
        </div>

        <div class="research-detail__task-list">
          <div
            v-for="task in tasks"
            :key="task.id"
            class="research-detail__task"
            :class="taskClass(task.status)"
          >
            <span class="research-detail__task-dot" />
            <div>
              <strong>{{ task.name }}</strong>
              <p v-if="task.summary">{{ task.summary }}</p>
              <p v-if="task.error" class="research-detail__error">{{ task.error }}</p>
            </div>
            <em>{{ task.status }}</em>
          </div>
        </div>

        <div class="research-detail__summary-strip">
          <span>Sources: {{ sources.length }}</span>
          <span v-if="sourceSummary">{{ sourceSummary }}</span>
          <span>Iteration: {{ currentResearch.iterations }} / {{ currentResearch.max_iterations }}</span>
          <span>Wiki: {{ wikiPages.length }} page(s), {{ wikiSufficiency }}</span>
        </div>

        <div v-if="wikiPages.length" class="research-detail__wiki-strip">
          <h3>Wiki context</h3>
          <span v-for="page in wikiPages.slice(0, 6)" :key="page.path">
            {{ page.title }}
          </span>
        </div>

        <div class="research-detail__log-preview">
          <h3>Recent progress</h3>
          <div v-for="log in recentLogs" :key="`${log.timestamp}-${log.message}`">
            <span>{{ new Date(log.timestamp).toLocaleTimeString() }}</span>
            <p>{{ log.message }}</p>
          </div>
        </div>
      </section>

      <section v-else class="research-detail__panel research-detail__report-shell">
        <div class="research-detail__panel-header">
          <div>
            <h2>Final report</h2>
            <p>{{ sources.length }} sources referenced. The task list is available as process history.</p>
          </div>
          <button class="research-detail__ghost" @click="reportCollapsed = !reportCollapsed">
            {{ reportCollapsed ? 'Expand report' : 'Collapse report' }}
          </button>
          <button class="research-detail__ghost" :disabled="wikiSaving" @click="saveReportToWiki">
            {{ wikiSaving ? 'Saving Wiki' : 'Save to Wiki' }}
          </button>
        </div>

        <p v-if="wikiSaveMessage" class="research-detail__wiki-message">{{ wikiSaveMessage }}</p>
        <p v-if="wikiSaveError" class="research-detail__error">{{ wikiSaveError }}</p>

        <div v-if="wikiUpdatedPages.length" class="research-detail__wiki-strip">
          <h3>Wiki files</h3>
          <span v-for="path in wikiUpdatedPages.slice(0, 12)" :key="path">{{ path }}</span>
        </div>

        <transition name="report">
          <pre v-if="!reportCollapsed" class="research-detail__report">{{ finalReport }}</pre>
        </transition>

        <button class="research-detail__process-toggle" @click="processCollapsed = !processCollapsed">
          {{ processCollapsed ? 'Show process history' : 'Hide process history' }}
        </button>
        <div v-if="!processCollapsed" class="research-detail__compact-tasks">
          <span v-for="task in tasks" :key="task.id" :class="`research-detail__compact-task--${task.status}`">
            {{ task.name }}
          </span>
        </div>
      </section>

      <section v-if="finalReport" class="research-detail__chat">
        <div class="research-detail__chat-messages">
          <p v-if="!chatMessages.length" class="research-detail__empty">
            Ask a follow-up question grounded in this report.
          </p>
          <ChatMessage v-for="message in chatMessages" :key="message.id" :message="message" />
          <span ref="chatEndRef" />
        </div>

        <p v-if="chatError" class="research-detail__error">{{ chatError }}</p>

        <form class="research-detail__composer" @submit.prevent="sendChatMessage">
          <textarea
            v-model="chatInput"
            :disabled="!canChat || chatStreaming"
            rows="2"
            placeholder="Ask a follow-up question..."
            @keydown.enter.exact.prevent="sendChatMessage"
          />
          <button :disabled="!chatInput.trim() || !canChat || chatStreaming">
            {{ chatStreaming ? 'Answering' : 'Send' }}
          </button>
        </form>
      </section>
    </template>
  </div>
</template>

<style scoped>
.research-detail {
  width: min(960px, 100%);
  min-height: 100vh;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-4);
}

.research-detail__hero,
.research-detail__phase,
.research-detail__panel-header,
.research-detail__summary-strip,
.research-detail__task {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
}

.research-detail__hero {
  margin-bottom: var(--space-8);
}

.research-detail__eyebrow {
  color: #8b867c;
  font-size: var(--text-xs);
  font-weight: 800;
  letter-spacing: 0.1em;
  margin-bottom: var(--space-2);
  text-transform: uppercase;
}

.research-detail__hero h1 {
  color: #171717;
  font-size: clamp(2rem, 4vw, 3.5rem);
  letter-spacing: -0.045em;
  margin: 0;
}

.research-detail__hero p,
.research-detail__phase p,
.research-detail__panel-header p,
.research-detail__task p,
.research-detail__empty {
  color: #68645d;
  line-height: 1.65;
  margin: var(--space-2) 0 0;
}

.research-detail__status-pill {
  border: 1px solid #dedbd3;
  border-radius: var(--radius-full);
  background: #fbfaf7;
  color: #4b4945;
  flex-shrink: 0;
  font-size: var(--text-sm);
  font-weight: 700;
  padding: var(--space-2) var(--space-4);
  text-transform: capitalize;
}

.research-detail__status-pill--awaiting_report {
  background: #fff7d6;
  border-color: #ead17a;
}

.research-detail__phase {
  align-items: center;
  border-bottom: 1px solid #eeeae2;
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-6);
}

.research-detail__phase h2,
.research-detail__panel-header h2 {
  color: #171717;
  font-size: var(--text-2xl);
  letter-spacing: -0.025em;
  margin: 0;
}

.research-detail__meter {
  width: min(260px, 100%);
  color: #68645d;
  font-size: var(--text-sm);
  font-weight: 700;
}

.research-detail__meter div {
  height: 8px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: #eeeae2;
  margin-top: var(--space-2);
}

.research-detail__meter i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #171717;
  transition: width 220ms ease;
}

.research-detail__panel {
  border: 1px solid #e7e2d8;
  border-radius: 28px;
  background: #fff;
  box-shadow: 0 18px 70px rgb(23 23 23 / 0.06);
  padding: var(--space-6);
}

.research-detail__primary,
.research-detail__ghost,
.research-detail__process-toggle,
.research-detail__composer button {
  border: 0;
  border-radius: var(--radius-full);
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.research-detail__primary,
.research-detail__composer button {
  background: #171717;
  color: #fff;
  padding: var(--space-3) var(--space-5);
}

.research-detail__ghost,
.research-detail__process-toggle {
  background: #f2efe8;
  color: #3b3935;
  padding: var(--space-2) var(--space-4);
}

.research-detail__primary:hover,
.research-detail__ghost:hover,
.research-detail__process-toggle:hover,
.research-detail__composer button:hover {
  transform: translateY(-1px);
}

.research-detail__primary:disabled,
.research-detail__ghost:disabled,
.research-detail__composer button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  transform: none;
}

.research-detail__task-list {
  display: grid;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.research-detail__task {
  border: 1px solid #efebe3;
  border-radius: var(--radius-xl);
  padding: var(--space-3);
}

.research-detail__task strong {
  color: #242321;
}

.research-detail__task em {
  color: #8b867c;
  font-size: var(--text-xs);
  font-style: normal;
  font-weight: 800;
  text-transform: uppercase;
}

.research-detail__task-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  background: #c9c3b8;
  flex-shrink: 0;
  margin-top: 0.45rem;
}

.research-detail__task--running .research-detail__task-dot {
  background: #171717;
  box-shadow: 0 0 0 5px rgb(23 23 23 / 0.1);
}

.research-detail__task--completed .research-detail__task-dot,
.research-detail__compact-task--completed {
  background: #dff3e8;
  color: #116039;
}

.research-detail__task--failed .research-detail__task-dot,
.research-detail__compact-task--failed {
  background: #ffe1df;
  color: #a12219;
}

.research-detail__summary-strip {
  flex-wrap: wrap;
  border-top: 1px solid #f0ece4;
  border-bottom: 1px solid #f0ece4;
  color: #68645d;
  font-size: var(--text-sm);
  margin: var(--space-5) 0;
  padding: var(--space-3) 0;
}

.research-detail__wiki-strip {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-4) 0;
}

.research-detail__wiki-strip h3 {
  width: 100%;
  color: #171717;
  font-size: var(--text-base);
  margin: 0;
}

.research-detail__wiki-strip span {
  border-radius: var(--radius-full);
  background: #f2efe8;
  color: #4b4945;
  font-size: var(--text-xs);
  font-weight: 700;
  padding: var(--space-1) var(--space-3);
}

.research-detail__wiki-message {
  color: #116039;
  font-weight: 700;
}

.research-detail__log-preview {
  display: grid;
  gap: var(--space-3);
}

.research-detail__log-preview h3 {
  color: #171717;
  font-size: var(--text-base);
  margin: 0;
}

.research-detail__log-preview div {
  border-left: 2px solid #dedbd3;
  padding-left: var(--space-3);
}

.research-detail__log-preview span {
  color: #9a948a;
  font-size: var(--text-xs);
}

.research-detail__log-preview p {
  color: #4b4945;
  margin: var(--space-1) 0 0;
}

.research-detail__report {
  max-height: none;
  color: #242321;
  font-family: var(--font-sans);
  line-height: 1.75;
  margin: var(--space-6) 0;
  white-space: pre-wrap;
}

.research-detail__process-toggle {
  margin-top: var(--space-3);
}

.research-detail__compact-tasks {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
}

.research-detail__compact-tasks span {
  border-radius: var(--radius-full);
  background: #f3f0e9;
  color: #4b4945;
  font-size: var(--text-xs);
  font-weight: 700;
  padding: var(--space-1) var(--space-3);
}

.research-detail__chat {
  display: grid;
  gap: var(--space-4);
  margin-top: var(--space-6);
}

.research-detail__chat-messages {
  max-height: 520px;
  overflow-y: auto;
  padding-right: var(--space-2);
}

.research-detail__composer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space-3);
  position: sticky;
  bottom: var(--space-4);
  border: 1px solid #dedbd3;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 18px 60px rgb(23 23 23 / 0.1);
  padding: var(--space-3);
}

.research-detail__composer textarea {
  border: 0;
  resize: none;
  outline: none;
  color: #171717;
  font: inherit;
  line-height: 1.6;
  padding: var(--space-2);
}

.research-detail__error {
  color: var(--color-error);
}

.report-enter-active,
.report-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.report-enter-from,
.report-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 720px) {
  .research-detail {
    padding: var(--space-6) var(--space-4);
  }

  .research-detail__hero,
  .research-detail__phase,
  .research-detail__panel-header,
  .research-detail__task,
  .research-detail__composer {
    display: flex;
    flex-direction: column;
  }

  .research-detail__meter {
    width: 100%;
  }

  .research-detail__composer {
    align-items: stretch;
  }
}
</style>
