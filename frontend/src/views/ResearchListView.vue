<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useResearchStore } from '@/stores/research'
import ResearchCard from '@/components/research/ResearchCard.vue'
import AppLoading from '@/components/common/AppLoading.vue'

const router = useRouter()
const researchStore = useResearchStore()
const { researches, loading } = storeToRefs(researchStore)

onMounted(() => {
  researchStore.fetchResearches()
})

function createNew() {
  router.push({ name: 'home' })
}

function goToDetail(id: string) {
  router.push({ name: 'research-detail', params: { id } })
}
</script>

<template>
  <main class="research-list-view">
    <header class="research-list-view__header">
      <div>
        <p>Research history</p>
        <h1>All threads</h1>
      </div>
      <button class="research-list-view__new" @click="createNew">New research</button>
    </header>

    <AppLoading v-if="loading" text="Loading research..." size="large" />

    <section v-else-if="researches.length === 0" class="research-list-view__empty">
      <h2>No research threads yet</h2>
      <p>Start with a question and the agent will build a task plan before writing the report.</p>
      <button class="research-list-view__new" @click="createNew">Start research</button>
    </section>

    <section v-else class="research-list-view__grid">
      <ResearchCard
        v-for="research in researches"
        :key="research.id"
        :research="research"
        @click="goToDetail(research.id)"
      />
    </section>
  </main>
</template>

<style scoped>
.research-list-view {
  width: min(1120px, 100%);
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
}

.research-list-view__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-4);
  border-bottom: 1px solid #eeeae2;
  margin-bottom: var(--space-8);
  padding-bottom: var(--space-6);
}

.research-list-view__header p {
  color: #8b867c;
  font-size: var(--text-xs);
  font-weight: 800;
  letter-spacing: 0.1em;
  margin: 0 0 var(--space-2);
  text-transform: uppercase;
}

.research-list-view__header h1 {
  color: #171717;
  font-size: clamp(2rem, 4vw, 3.8rem);
  letter-spacing: -0.05em;
  margin: 0;
}

.research-list-view__new {
  border: 0;
  border-radius: var(--radius-full);
  background: #171717;
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: var(--space-3) var(--space-5);
}

.research-list-view__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}

.research-list-view__empty {
  display: grid;
  justify-items: center;
  gap: var(--space-3);
  padding: var(--space-20) var(--space-6);
  text-align: center;
}

.research-list-view__empty h2 {
  color: #171717;
  margin: 0;
}

.research-list-view__empty p {
  max-width: 520px;
  color: #68645d;
  line-height: 1.7;
  margin: 0 0 var(--space-3);
}

@media (max-width: 720px) {
  .research-list-view__header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
