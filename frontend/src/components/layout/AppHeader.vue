<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <header class="app-header">
    <button class="app-header__brand" @click="router.push({ name: 'home' })">
      Research Agent
    </button>
  </header>
</template>

<style scoped>
.app-header {
  display: none;
}

.app-header__brand {
  border: 0;
  background: transparent;
  color: var(--color-text);
  font: inherit;
  font-weight: 700;
}
</style>
