<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useResearchStore } from '@/stores/research'

const router = useRouter()
const researchStore = useResearchStore()
const topic = ref('')

const examples = [
  '研究 LLM 在漏洞检测中的应用',
  'AI agents for scientific literature review',
  'Open-source code security benchmarks'
]

async function startResearch() {
  const query = topic.value.trim()
  if (!query) return

  const result = await researchStore.createResearch({
    title: query,
    query
  })

  if (result) {
    await researchStore.startResearch(result.id)
    router.push({ name: 'research-detail', params: { id: result.id } })
  }
}

function useExample(example: string) {
  topic.value = example
}
</script>

<template>
  <main class="home">
    <section class="home__workspace">
      <p class="home__eyebrow">Deep research assistant</p>
      <h1 class="home__title">What should we research?</h1>
      <p class="home__subtitle">
        Start with one question. The agent will search, analyze, synthesize, then wait for your approval before writing the final report.
      </p>

      <form class="home__composer" @submit.prevent="startResearch">
        <textarea
          v-model="topic"
          class="home__input"
          rows="4"
          placeholder="Ask a research question..."
          :disabled="researchStore.loading"
          @keydown.enter.exact.prevent="startResearch"
        />
        <div class="home__composer-footer">
          <span>{{ topic.length ? `${topic.length} chars` : 'Enter to start' }}</span>
          <button class="home__send" :disabled="researchStore.loading || !topic.trim()">
            {{ researchStore.loading ? 'Starting' : 'Start' }}
          </button>
        </div>
      </form>

      <p v-if="researchStore.error" class="home__error">{{ researchStore.error }}</p>

      <div class="home__examples">
        <button v-for="example in examples" :key="example" @click="useExample(example)">
          {{ example }}
        </button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.home {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: var(--space-8);
  background:
    radial-gradient(circle at 50% 20%, rgba(79, 70, 229, 0.08), transparent 34rem),
    #fff;
}

.home__workspace {
  width: min(820px, 100%);
  text-align: center;
}

.home__eyebrow {
  color: #77736b;
  font-size: var(--text-sm);
  font-weight: 700;
  letter-spacing: 0.08em;
  margin-bottom: var(--space-4);
  text-transform: uppercase;
}

.home__title {
  color: #171717;
  font-size: clamp(2.4rem, 7vw, 4.6rem);
  letter-spacing: -0.055em;
  margin: 0;
}

.home__subtitle {
  max-width: 650px;
  color: #68645d;
  font-size: var(--text-lg);
  line-height: 1.7;
  margin: var(--space-4) auto var(--space-8);
}

.home__composer {
  overflow: hidden;
  border: 1px solid #dedbd3;
  border-radius: 28px;
  background: #fff;
  box-shadow: 0 18px 70px rgb(23 23 23 / 0.1);
  text-align: left;
}

.home__input {
  width: 100%;
  border: 0;
  resize: none;
  outline: none;
  padding: var(--space-5);
  color: #171717;
  font: inherit;
  font-size: var(--text-lg);
  line-height: 1.6;
}

.home__composer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid #f0eee8;
  padding: var(--space-3) var(--space-4);
  color: #8b867c;
  font-size: var(--text-sm);
}

.home__send {
  border: 0;
  border-radius: var(--radius-full);
  background: #171717;
  color: #fff;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: var(--space-2) var(--space-5);
}

.home__send:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.home__examples {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-6);
}

.home__examples button {
  border: 1px solid #e8e5de;
  border-radius: var(--radius-full);
  background: #fbfaf7;
  color: #4b4945;
  cursor: pointer;
  font: inherit;
  font-size: var(--text-sm);
  padding: var(--space-2) var(--space-4);
}

.home__error {
  color: var(--color-error);
  margin-top: var(--space-4);
}

@media (max-width: 640px) {
  .home {
    align-items: start;
    padding: var(--space-8) var(--space-4);
  }
}
</style>
