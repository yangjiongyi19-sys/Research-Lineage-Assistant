<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useResearchStore } from '@/stores/research'
import { ResearchStatus } from '@/types'

const route = useRoute()
const router = useRouter()
const researchStore = useResearchStore()

const researches = computed(() => researchStore.researches.slice(0, 30))

function statusLabel(status: ResearchStatus) {
  if (status === ResearchStatus.AWAITING_REPORT) return 'ready'
  if (status === ResearchStatus.COMPLETED) return 'done'
  if (status === ResearchStatus.ERROR || status === ResearchStatus.FAILED) return 'error'
  if (status === ResearchStatus.PENDING) return 'draft'
  return 'running'
}

function openResearch(id: string) {
  router.push({ name: 'research-detail', params: { id } })
}

onMounted(() => {
  researchStore.fetchResearches()
})
</script>

<template>
  <aside class="app-sidebar">
    <div class="app-sidebar__brand" @click="router.push({ name: 'home' })">
      <span class="app-sidebar__mark">R</span>
      <div>
        <strong>Research Agent</strong>
        <span>Deep research workspace</span>
      </div>
    </div>

    <button class="app-sidebar__new" @click="router.push({ name: 'home' })">
      <span>+</span>
      New research
    </button>

    <nav class="app-sidebar__nav">
      <router-link :to="{ name: 'home' }" class="app-sidebar__link">
        Home
      </router-link>
      <router-link :to="{ name: 'research-list' }" class="app-sidebar__link">
        All research
      </router-link>
      <router-link :to="{ name: 'wiki' }" class="app-sidebar__link">
        LLM Wiki
      </router-link>
    </nav>

    <div class="app-sidebar__history">
      <p class="app-sidebar__section">Recent</p>
      <button
        v-for="item in researches"
        :key="item.id"
        class="app-sidebar__item"
        :class="{ 'app-sidebar__item--active': route.params.id === item.id }"
        @click="openResearch(item.id)"
      >
        <span class="app-sidebar__item-title">{{ item.title }}</span>
        <span class="app-sidebar__item-status">{{ statusLabel(item.status) }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  height: 100vh;
  padding: var(--space-4);
  background: #f7f7f5;
  border-right: 1px solid #e6e4df;
  overflow-y: auto;
}

.app-sidebar__brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  padding: var(--space-2);
}

.app-sidebar__mark {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
  background: #171717;
  color: #fff;
  font-weight: 700;
}

.app-sidebar__brand strong,
.app-sidebar__brand span,
.app-sidebar__item-title,
.app-sidebar__item-status {
  display: block;
}

.app-sidebar__brand strong {
  color: #171717;
  font-size: var(--text-sm);
}

.app-sidebar__brand span {
  color: #77736b;
  font-size: var(--text-xs);
}

.app-sidebar__new {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  border: 1px solid #dedbd3;
  border-radius: var(--radius-xl);
  background: #fff;
  color: #171717;
  padding: var(--space-3);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.app-sidebar__new span {
  font-size: var(--text-lg);
  line-height: 1;
}

.app-sidebar__nav {
  display: grid;
  gap: var(--space-1);
}

.app-sidebar__link,
.app-sidebar__item {
  border-radius: var(--radius-lg);
  color: #4b4945;
  text-align: left;
  text-decoration: none;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.app-sidebar__link {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
}

.app-sidebar__link:hover,
.app-sidebar__link.router-link-active,
.app-sidebar__item:hover,
.app-sidebar__item--active {
  background: #ebe8df;
  color: #171717;
}

.app-sidebar__history {
  min-height: 0;
}

.app-sidebar__section {
  color: #8b867c;
  font-size: var(--text-xs);
  font-weight: 700;
  letter-spacing: 0.08em;
  margin: var(--space-2) var(--space-3);
  text-transform: uppercase;
}

.app-sidebar__item {
  display: grid;
  width: 100%;
  gap: var(--space-1);
  border: 0;
  background: transparent;
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
}

.app-sidebar__item-title {
  overflow: hidden;
  color: inherit;
  font-size: var(--text-sm);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-sidebar__item-status {
  color: #8b867c;
  font-size: var(--text-xs);
}

@media (max-width: 860px) {
  .app-sidebar {
    position: sticky;
    top: 0;
    z-index: 20;
    height: auto;
    max-height: 72px;
    flex-direction: row;
    align-items: center;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .app-sidebar__brand span,
  .app-sidebar__nav,
  .app-sidebar__history {
    display: none;
  }

  .app-sidebar__new {
    width: auto;
    white-space: nowrap;
  }
}
</style>
