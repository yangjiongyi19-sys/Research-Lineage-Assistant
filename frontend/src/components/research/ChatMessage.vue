<script setup lang="ts">
import type { ChatMessage as ChatMessageType, MessageRole } from '@/types'

defineProps<{
  message: ChatMessageType
}>()

const roleLabel: Record<MessageRole, string> = {
  user: 'You',
  assistant: 'Assistant'
}
</script>

<template>
  <div class="chat-message" :class="`chat-message--${message.role}`">
    <div class="chat-message__avatar">
      {{ message.role === 'user' ? 'U' : 'A' }}
    </div>
    <div class="chat-message__content">
      <div class="chat-message__header">
        <span class="chat-message__role">{{ roleLabel[message.role] }}</span>
        <span class="chat-message__time">{{ new Date(message.created_at).toLocaleTimeString() }}</span>
      </div>
      <div class="chat-message__body">{{ message.content }}</div>
    </div>
  </div>
</template>

<style scoped>
.chat-message {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3) 0;
}

.chat-message--assistant {
  flex-direction: row;
}

.chat-message--user {
  flex-direction: row-reverse;
}

.chat-message__avatar {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  background: var(--color-bg-secondary);
  color: var(--color-text);
  font-size: var(--text-sm);
  font-weight: 700;
  flex-shrink: 0;
}

.chat-message--user .chat-message__avatar {
  background: var(--color-primary-600);
  color: var(--color-bg);
}

.chat-message__content {
  max-width: 78%;
}

.chat-message__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.chat-message--user .chat-message__header {
  justify-content: flex-end;
}

.chat-message__role {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text);
}

.chat-message__time {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.chat-message__body {
  background: var(--color-bg-secondary);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  line-height: 1.65;
  color: var(--color-text);
  white-space: pre-wrap;
}

.chat-message--user .chat-message__body {
  background: var(--color-primary-600);
  color: var(--color-bg);
}
</style>
