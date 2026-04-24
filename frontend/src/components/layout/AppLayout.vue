<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <main class="app-layout__main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  min-height: 100vh;
  background: var(--color-bg);
}

.app-layout__main {
  min-width: 0;
  height: 100vh;
  overflow-y: auto;
}

@media (max-width: 860px) {
  .app-layout {
    grid-template-columns: 1fr;
  }

  .app-layout__main {
    height: auto;
    min-height: calc(100vh - 72px);
  }
}
</style>
