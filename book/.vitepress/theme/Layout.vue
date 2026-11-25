<script setup lang="ts">
import { defineAsyncComponent, onMounted, onUnmounted, ref } from 'vue'
import DefaultTheme from 'vitepress/theme'
import prReviewMeta from 'virtual:apex-pr-review'

const { Layout } = DefaultTheme
const PrReviewOverlay = prReviewMeta.enabled
  ? defineAsyncComponent(() => import('./review/PrReviewOverlay.vue'))
  : null

const progress = ref(0)
const serifMode = ref(true)

function updateProgress() {
  if (typeof window === 'undefined') return
  const scrollTop = window.scrollY || document.documentElement.scrollTop
  const docHeight =
    document.documentElement.scrollHeight - document.documentElement.clientHeight
  progress.value = docHeight > 0 ? Math.min(100, Math.max(0, (scrollTop / docHeight) * 100)) : 0
}

function applyTypography(useSerif: boolean) {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('book-serif-mode', useSerif)
}

function toggleTypography() {
  serifMode.value = !serifMode.value
  applyTypography(serifMode.value)
  try {
    localStorage.setItem('apex-book-serif', serifMode.value ? '1' : '0')
  } catch {
    // ignore storage errors
  }
}

if (typeof window !== 'undefined') {
  try {
    const saved = localStorage.getItem('apex-book-serif')
    serifMode.value = saved === null ? true : saved === '1'
  } catch {
    serifMode.value = true
  }
  applyTypography(serifMode.value)
}

onMounted(() => {
  applyTypography(serifMode.value)
  updateProgress()
  window.addEventListener('scroll', updateProgress, { passive: true })
  window.addEventListener('resize', updateProgress, { passive: true })
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('scroll', updateProgress)
    window.removeEventListener('resize', updateProgress)
  }
})
</script>

<template>
  <div class="book-progress-track" aria-hidden="true">
    <div class="book-progress-fill" :style="{ width: `${progress}%` }" />
  </div>
  <Layout>
    <template #nav-bar-content-after>
      <button
        type="button"
        class="reader-font-toggle"
        :title="serifMode ? 'Switch to Sans-Serif prose' : 'Switch to Textbook Serif prose'"
        @click="toggleTypography"
      >
        <span class="font-badge">{{ serifMode ? 'Aa Serif' : 'Aa Sans' }}</span>
      </button>
    </template>
  </Layout>
  <ClientOnly>
    <PrReviewOverlay v-if="PrReviewOverlay" />
  </ClientOnly>
</template>
