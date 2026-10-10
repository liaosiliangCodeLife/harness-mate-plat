<script setup lang="ts">
import { computed, type PropType } from 'vue'
import type { ChatMessage } from '@/models/agent-message'
import { formatFileSize, splitMessageFiles } from '@/utils/chat-files'
import { stripCursorGlyphs } from '@/utils/hermes-channel'
import { renderMarkdown } from '@/utils/markdown'

// 1.定义自定义组件所需数据
const props = defineProps({
  message: {
    type: Object as PropType<ChatMessage>,
    required: true,
  },
  avatar: { type: String, default: '' },
  name: { type: String, default: '' },
})
const isUser = computed(() => props.message.role === 'user')
const avatarUrl = computed(() => (props.avatar || '').trim())
const generating = computed(
  () => !isUser.value && !props.message.fromHistory && props.message.status === 0,
)
const parts = computed(() =>
  splitMessageFiles(stripCursorGlyphs(props.message.content || ''), props.message.files),
)
const imageFiles = computed(() => parts.value.files.filter((file) => file.media_kind === 'image'))
const audioFiles = computed(() => parts.value.files.filter((file) => file.media_kind === 'audio'))
const videoFiles = computed(() => parts.value.files.filter((file) => file.media_kind === 'video'))
const otherFiles = computed(() => parts.value.files.filter((file) => file.media_kind === 'file'))
const html = computed(() => renderMarkdown(parts.value.text))
</script>

<template>
  <div class="flex gap-2">
    <a-avatar
      v-if="avatarUrl"
      :size="30"
      shape="circle"
      class="flex-shrink-0"
      :image-url="avatarUrl"
    />
    <a-avatar v-else :size="30" shape="circle" class="flex-shrink-0 bg-blue-700">
      <icon-user v-if="isUser" />
      <icon-robot v-else />
    </a-avatar>
    <div class="flex-1 min-w-0 flex flex-col items-start gap-2">
      <div class="text-gray-700 font-bold">{{ name }}</div>
      <div
        :class="`w-fit max-w-full min-w-0 break-words px-3 py-2 rounded-2xl border ${
          isUser
            ? 'bg-blue-100 border-blue-200 text-gray-700'
            : 'markdown-body !bg-gray-100 border-gray-200 !text-gray-700'
        }`"
      >
        <div
          v-if="(message.thinking || generating) && !message.content && !parts.files.length"
          class="text-gray-500"
        >
          思考中<span class="thinking-dots"><i>.</i><i>.</i><i>.</i></span>
        </div>
        <template v-else>
          <a-image-preview-group v-if="imageFiles.length">
            <div class="mb-2 flex flex-wrap gap-2">
              <a-image
                v-for="file in imageFiles"
                :key="file.url"
                :src="file.url"
                :alt="file.name"
                fit="contain"
                class="chat-image overflow-hidden rounded-lg"
              >
                <template #error>
                  <a
                    class="flex max-w-[240px] items-center px-2 py-1.5 text-xs text-blue-600"
                    :href="file.url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >{{ file.name }}</a>
                </template>
              </a-image>
            </div>
          </a-image-preview-group>
          <div v-if="audioFiles.length" class="mb-2 flex max-w-full flex-col gap-2">
            <audio
              v-for="file in audioFiles"
              :key="file.url"
              class="chat-player"
              controls
              preload="metadata"
              :src="file.url"
            />
          </div>
          <div v-if="videoFiles.length" class="mb-2 flex max-w-full flex-col gap-2">
            <video
              v-for="file in videoFiles"
              :key="file.url"
              class="chat-player"
              controls
              playsinline
              preload="metadata"
              :src="file.url"
            />
          </div>
          <div v-if="otherFiles.length" class="mb-2 flex flex-col gap-2">
            <a
              v-for="file in otherFiles"
              :key="file.url"
              class="flex max-w-full items-center gap-2 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-gray-700 no-underline hover:border-blue-300"
              :href="file.url"
              target="_blank"
              rel="noopener noreferrer"
            >
              <icon-file class="flex-shrink-0 text-gray-500" :size="16" />
              <span class="min-w-0 flex-1 truncate text-sm">{{ file.name }}</span>
              <span v-if="formatFileSize(file.size)" class="flex-shrink-0 text-xs text-gray-400">
                {{ formatFileSize(file.size) }}
              </span>
            </a>
          </div>
          <div
            v-if="parts.text"
            class="markdown-body chat-markdown break-all"
            v-html="html"
          ></div>
          <div v-if="generating" class="mt-1 text-xs text-gray-500">生成中…</div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-image {
  max-width: min(100%, 240px);
  line-height: 0;
}

.chat-player {
  display: block;
  width: 100%;
  max-width: 100%;
  border-radius: 0.5rem;
}

video.chat-player {
  max-height: 240px;
  background-color: #111827;
}

.chat-image :deep(.arco-image-img) {
  display: block;
  width: auto;
  height: auto;
  max-width: min(100%, 240px);
  max-height: 240px;
  object-fit: contain;
}

.chat-markdown {
  background-color: transparent;
  font-size: 14px;
  line-height: 1.35;
  color: inherit;
  max-width: 100%;
}

.chat-markdown :deep(> :first-child) {
  margin-top: 0;
}

.chat-markdown :deep(> :last-child) {
  margin-bottom: 0;
}

.chat-markdown :deep(p),
.chat-markdown :deep(li > p) {
  margin: 0.3em 0;
}

.chat-markdown :deep(ul),
.chat-markdown :deep(ol) {
  margin: 0.3em 0;
  padding-left: 1.4em;
}

.chat-markdown :deep(li) {
  margin: 0.12em 0;
}

.chat-markdown :deep(h1),
.chat-markdown :deep(h2),
.chat-markdown :deep(h3),
.chat-markdown :deep(h4),
.chat-markdown :deep(h5),
.chat-markdown :deep(h6) {
  margin: 0.5em 0 0.3em;
  padding-top: 0;
}

.chat-markdown :deep(pre),
.chat-markdown :deep(table) {
  margin: 0.4em 0;
  max-width: 100%;
}

.chat-markdown :deep(pre) {
  overflow-x: auto;
}

.thinking-dots {
  display: inline-flex;
  align-items: flex-end;
  height: 1em;
  margin-left: 1px;
}

.thinking-dots i {
  display: inline-block;
  font-style: normal;
  line-height: 1;
  animation: thinking-dot-wave 1.2s ease-in-out infinite;
}

.thinking-dots i:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots i:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-dot-wave {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.25;
  }

  30% {
    transform: translateY(-4px);
    opacity: 1;
  }
}
</style>
