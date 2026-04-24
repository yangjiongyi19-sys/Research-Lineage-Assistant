<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'primary' | 'secondary' | 'danger'
  size?: 'small' | 'medium' | 'large'
  disabled?: boolean
}>(), {
  type: 'primary',
  size: 'medium',
  disabled: false
})

defineEmits<{
  click: []
}>()
</script>

<template>
  <button
    class="app-button"
    :class="[`app-button--${type}`, `app-button--${size}`]"
    :disabled="disabled"
    @click="$emit('click')"
  >
    <slot />
  </button>
</template>

<style scoped>
.app-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.app-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.app-button--primary {
  background: var(--color-primary-600);
  color: var(--color-text-on-primary);
}
.app-button--primary:hover:not(:disabled) {
  background: var(--color-primary-700);
}

.app-button--secondary {
  background: transparent;
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.app-button--secondary:hover:not(:disabled) {
  background: var(--color-bg-secondary);
}

.app-button--danger {
  background: var(--color-error);
  color: var(--color-text-inverse);
}
.app-button--danger:hover:not(:disabled) {
  background: var(--color-error-dark);
}

.app-button--small {
  padding: var(--space-1) var(--space-2);
  font-size: var(--text-sm);
}
.app-button--medium {
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-base);
}
.app-button--large {
  padding: var(--space-3) var(--space-6);
  font-size: var(--text-lg);
}
</style>
