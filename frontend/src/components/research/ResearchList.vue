<script setup lang="ts">
import type { Research } from '@/types'
import ResearchCard from './ResearchCard.vue'
import AppLoading from '@/components/common/AppLoading.vue'

defineProps<{
  researches: Research[]
  loading?: boolean
}>()
</script>

<template>
  <div class="research-list">
    <AppLoading v-if="loading" text="Loading research..." />
    <div v-else-if="researches.length === 0" class="research-list__empty">
      No research threads yet.
    </div>
    <div v-else class="research-list__grid">
      <ResearchCard
        v-for="research in researches"
        :key="research.id"
        :research="research"
      />
    </div>
  </div>
</template>

<style scoped>
.research-list__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-4);
}

.research-list__empty {
  text-align: center;
  padding: var(--space-8) 0;
  color: var(--color-text-secondary);
  font-size: var(--text-base);
}
</style>
