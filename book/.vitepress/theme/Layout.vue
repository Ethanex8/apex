<script setup lang="ts">
/**
 * Purpose: Wrap VitePress DefaultTheme Layout with reading progress bar, serif toggle, sidebar chapter outline, and PR review overlay.
 * Usage: Registered as the root layout component in `book/.vitepress/theme/index.ts`.
 * Invariants: Keeps `serifMode` at its SSR default (`true`) during initial hydration, syncing persisted preference on mount.
 */
import { defineAsyncComponent, defineComponent, onErrorCaptured, onMounted, onUnmounted, ref } from 'vue'
import DefaultTheme from 'vitepress/theme'
import prReviewMeta from 'virtual:apex-pr-review'
import InChapterSidebarNav from './InChapterSidebarNav.vue'

const { Layout } = DefaultTheme
const PrReviewOverlay = prReviewMeta.enabled
  ? defineAsyncComponent(() => import('./review/PrReviewOverlay.vue'))
  : null

/** Isolate PR review overlay render/lifecycle errors so book content cannot freeze or lose navigation. */
const OverlayBoundary = defineComponent({
  name: 'PrReviewOverlayBoundary',
  setup(_, { slots }) {
    const failed = ref(false)
    onErrorCaptured((err) => {
      if (typeof document !== 'undefined') {
        document.documentElement.style.overflow = ''
        document.body.style.overflow = ''
      }
      console.error('[apex-review-overlay] Disabled after runtime error:', err)
      failed.value = true
      return false
    })
    return () => (failed.value ? null : slots.default?.())
  },
})

const SERIF_STORAGE_KEY = 'apex-book-serif'
const SERIF_CLASS_NAME = 'book-serif-mode'
const MAX_PROGRESS_PCT = 100

const progress = ref(0)
const serifMode = ref(true)

/** Read stored serif preference (`true` when unset); defaults safely if storage is blocked. */
function readStoredSerifPreference(): boolean {
  try {
    const saved = localStorage.getItem(SERIF_STORAGE_KEY)
    return saved === null ? true : saved === '1'
  } catch {
    // Private-browsing or disabled-storage contexts throw SecurityError; keep default serif mode.
    return true
  }
}

/** Update top reading progress bar percentage `[0, 100]` from current scroll offset. */
function updateProgress() {
  const scrollTop = window.scrollY || document.documentElement.scrollTop
  const docHeight =
    document.documentElement.scrollHeight - document.documentElement.clientHeight
  progress.value =
    docHeight > 0
      ? Math.min(MAX_PROGRESS_PCT, Math.max(0, (scrollTop / docHeight) * MAX_PROGRESS_PCT))
      : 0
}

/** Toggle root document typography class between serif textbook prose and sans-serif. */
function applyTypography(useSerif: boolean) {
  document.documentElement.classList.toggle(SERIF_CLASS_NAME, useSerif)
}

/** Flip reader typography mode and persist the choice to `localStorage` when permitted. */
function toggleTypography() {
  serifMode.value = !serifMode.value
  applyTypography(serifMode.value)
  try {
    localStorage.setItem(SERIF_STORAGE_KEY, serifMode.value ? '1' : '0')
  } catch {
    // Ignore storage SecurityError/QuotaExceededError so in-memory toggle still works.
  }
}

onMounted(() => {
  // Defer reactive serifMode hydration until mount so SSR and initial client VNodes match cleanly.
  serifMode.value = readStoredSerifPreference()
  applyTypography(serifMode.value)
  updateProgress()
  window.addEventListener('scroll', updateProgress, { passive: true })
  window.addEventListener('resize', updateProgress, { passive: true })
})

onUnmounted(() => {
  window.removeEventListener('scroll', updateProgress)
  window.removeEventListener('resize', updateProgress)
})
</script>

<template>
  <div class="book-progress-track" aria-hidden="true">
    <div class="book-progress-fill" :style="{ width: `${progress}%` }" />
  </div>
  <Layout>
    <template #sidebar-nav-before>
      <InChapterSidebarNav />
    </template>
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
    <OverlayBoundary v-if="PrReviewOverlay">
      <PrReviewOverlay />
    </OverlayBoundary>
  </ClientOnly>
</template>
