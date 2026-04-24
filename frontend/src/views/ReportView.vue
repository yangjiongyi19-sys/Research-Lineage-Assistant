<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { reportApi } from '@/services/api'
import type { ResearchReportResponse } from '@/types'
import AppLoading from '@/components/common/AppLoading.vue'
import AppCard from '@/components/common/AppCard.vue'

const route = useRoute()
const report = ref<ResearchReportResponse | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const { data } = await reportApi.getById(route.params.id as string)
    report.value = data
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="report-view">
    <AppLoading v-if="loading" text="Loading report..." size="large" />

    <div v-else-if="error" class="report-view__error">
      {{ error }}
    </div>

    <template v-else-if="report">
      <div class="report-view__header">
        <h2 class="report-view__title">Research report</h2>
        <span class="report-view__time">{{ report.format }}</span>
      </div>

      <AppCard padding="large" class="report-view__content">
        <pre class="report-view__body">{{ report.content }}</pre>
      </AppCard>

      <section v-if="report.sources.length > 0" class="report-view__sources">
        <h3 class="report-view__sources-title">Sources</h3>
        <div class="report-view__sources-list">
          <AppCard
            v-for="source in report.sources"
            :key="source.url"
            padding="small"
            class="report-view__source"
          >
            <a :href="source.url" target="_blank" rel="noreferrer" class="report-view__source-link">
              {{ source.title }}
            </a>
            <p class="report-view__source-snippet">{{ source.content }}</p>
          </AppCard>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.report-view__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.report-view__title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.report-view__time {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.report-view__body {
  white-space: pre-wrap;
  line-height: 1.8;
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--text-base);
  margin: 0;
}

.report-view__error {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-error);
}

.report-view__sources {
  margin-top: var(--space-6);
}

.report-view__sources-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 var(--space-3) 0;
}

.report-view__sources-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.report-view__source-link {
  color: var(--color-primary-600);
  text-decoration: none;
  font-weight: 500;
  font-size: var(--text-sm);
}

.report-view__source-link:hover {
  text-decoration: underline;
}

.report-view__source-snippet {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  margin: var(--space-1) 0 0 0;
  line-height: 1.4;
}
</style>
