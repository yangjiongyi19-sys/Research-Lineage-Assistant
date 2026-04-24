<script setup lang="ts">
import type { Research } from '@/types'
import { ResearchStatus } from '@/types'
import AppCard from '@/components/common/AppCard.vue'

defineProps<{
  research: Research
}>()

defineEmits<{
  click: []
}>()

const statusLabel: Record<ResearchStatus, string> = {
  [ResearchStatus.PENDING]: 'Pending',
  [ResearchStatus.SEARCHING]: 'Searching',
  [ResearchStatus.ANALYZING]: 'Analyzing',
  [ResearchStatus.SYNTHESIZING]: 'Synthesizing',
  [ResearchStatus.AWAITING_REPORT]: 'Ready for report',
  [ResearchStatus.COMPLETED]: 'Completed',
  [ResearchStatus.ERROR]: 'Error',
  [ResearchStatus.FAILED]: 'Failed'
}

const statusClass: Record<ResearchStatus, string> = {
  [ResearchStatus.PENDING]: 'research-card__status--pending',
  [ResearchStatus.SEARCHING]: 'research-card__status--searching',
  [ResearchStatus.ANALYZING]: 'research-card__status--analyzing',
  [ResearchStatus.SYNTHESIZING]: 'research-card__status--synthesizing',
  [ResearchStatus.AWAITING_REPORT]: 'research-card__status--awaiting',
  [ResearchStatus.COMPLETED]: 'research-card__status--completed',
  [ResearchStatus.ERROR]: 'research-card__status--failed',
  [ResearchStatus.FAILED]: 'research-card__status--failed'
}

const formatDate = (date: string) =>
  new Date(date).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
</script>

<template>
  <div class="research-card-link" @click="$emit('click')">
    <AppCard hoverable>
      <template #header>
        <div class="research-card__header">
          <h3 class="research-card__title">{{ research.title }}</h3>
          <span class="research-card__status" :class="statusClass[research.status]">
            {{ statusLabel[research.status] }}
          </span>
        </div>
      </template>

      <p class="research-card__description">
        {{ research.description || research.query }}
      </p>

      <template #footer>
        <div class="research-card__footer">
          <span>{{ formatDate(research.created_at) }}</span>
          <span>{{ research.iterations }} / {{ research.max_iterations }}</span>
        </div>
      </template>
    </AppCard>
  </div>
</template>

<style scoped>
.research-card-link {
  text-decoration: none;
  color: inherit;
  display: block;
  cursor: pointer;
}

.research-card__header,
.research-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.research-card__title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.research-card__status {
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
  flex-shrink: 0;
}

.research-card__status--pending {
  background: var(--color-status-pending-bg);
  color: var(--color-status-pending);
}

.research-card__status--searching {
  background: var(--color-status-searching-bg);
  color: var(--color-status-searching);
}

.research-card__status--analyzing {
  background: var(--color-status-analyzing-bg);
  color: var(--color-status-analyzing);
}

.research-card__status--synthesizing {
  background: var(--color-status-synthesizing-bg);
  color: var(--color-status-synthesizing);
}

.research-card__status--awaiting {
  background: var(--color-warning-light);
  color: var(--color-warning-dark);
}

.research-card__status--completed {
  background: var(--color-status-completed-bg);
  color: var(--color-status-completed);
}

.research-card__status--failed {
  background: var(--color-status-error-bg);
  color: var(--color-status-error);
}

.research-card__description {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  margin: 0;
  line-height: var(--leading-relaxed);
}

.research-card__footer {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}
</style>
