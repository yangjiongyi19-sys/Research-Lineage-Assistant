<script setup lang="ts">
withDefaults(defineProps<{
  size?: 'small' | 'medium' | 'large'
  text?: string
}>(), {
  size: 'medium',
  text: '加载中...'
})
</script>

<template>
  <div class="app-loading" :class="`app-loading--${size}`">
    <div class="app-loading__spinner" />
    <span v-if="text" class="app-loading__text">{{ text }}</span>
  </div>
</template>

<style scoped>
.app-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.app-loading__spinner {
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary-600);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.app-loading--small .app-loading__spinner {
  width: 16px;
  height: 16px;
}
.app-loading--medium .app-loading__spinner {
  width: 24px;
  height: 24px;
}
.app-loading--large .app-loading__spinner {
  width: 40px;
  height: 40px;
}

.app-loading__text {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
