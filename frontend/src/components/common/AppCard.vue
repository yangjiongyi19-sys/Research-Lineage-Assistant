<script setup lang="ts">
withDefaults(defineProps<{
  hoverable?: boolean
  padding?: 'none' | 'small' | 'medium' | 'large'
}>(), {
  hoverable: false,
  padding: 'medium'
})
</script>

<template>
  <div
    class="app-card"
    :class="[hoverable && 'app-card--hoverable', `app-card--padding-${padding}`]"
  >
    <div v-if="$slots.header" class="app-card__header">
      <slot name="header" />
    </div>
    <div class="app-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="app-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<style scoped>
.app-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.app-card--hoverable {
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}
.app-card--hoverable:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.app-card--padding-none { padding: 0; }
.app-card--padding-small { padding: var(--space-2); }
.app-card--padding-medium { padding: var(--space-4); }
.app-card--padding-large { padding: var(--space-6); }

.app-card__header {
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-3);
  font-weight: 600;
}

.app-card__footer {
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border);
  margin-top: var(--space-3);
}
</style>
