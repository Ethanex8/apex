<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useData, useRoute, useRouter, withBase } from 'vitepress'
import prReviewMeta from 'virtual:apex-pr-review'
import {
  fetchPrThreads,
  formatMarkdownBundle,
  replyToThread,
  setThreadResolved,
  submitBatchedReview,
  verifyGitHubToken,
} from './githubClient'
import {
  buildGitHubDiffUrl,
  findAnchorElementForLine,
  isRangeInAddedDiff,
  resolveBlockTarget,
  resolveSelectionTarget,
} from './sourceMapper'
import type {
  AuthState,
  CommentTarget,
  DraftComment,
  RemoteReviewThread,
  ReviewSubmitEvent,
} from './types'
import './review.css'

interface GutterMark {
  key: string
  top: number
  left: number
  height: number
}

interface ThreadMarkerGroup {
  key: string
  top: number
  left: number
  line: number | null
  allResolved: boolean
  threads: RemoteReviewThread[]
}

interface AnnotateChip {
  key: string
  top: number
  left: number
  label: string
  target: CommentTarget
}

interface HoverBlockMark {
  top: number
  left: number
  startLine: number
  endLine: number
  el: HTMLElement
}

const { page } = useData()
const route = useRoute()
const router = useRouter()

const meta = prReviewMeta
const draftStorageKey = `apex-pr-review-drafts:${meta.repo}#${meta.prNumber}`
const authStorageKey = `apex-pr-review-auth:${meta.repo}`

const isMobile = ref(false)
const annotateMode = ref(false)
const showGutter = ref(true)
const showResolved = ref(false)

const auth = ref<AuthState>({
  token: '',
  login: '',
  avatarUrl: '',
  persistLocal: true,
})
const tokenInput = ref('')
const persistLocalToggle = ref(true)
const authBusy = ref(false)
const authError = ref('')

const drafts = ref<DraftComment[]>([])
const summaryBody = ref('')
const submitEvent = ref<ReviewSubmitEvent>('COMMENT')
const submitBusy = ref(false)
const submitNotice = ref('')
const submitError = ref('')

const threads = ref<RemoteReviewThread[]>([])
const threadsLoading = ref(false)
const threadsLoadedOnce = ref(false)
const threadsError = ref('')

const drawerOpen = ref(false)
const drawerTab = ref<'drafts' | 'threads' | 'auth'>('drafts')
const threadScope = ref<'page' | 'all'>('page')

const selectionTarget = ref<CommentTarget | null>(null)
const selectionRect = ref<{ x: number; y: number } | null>(null)

const composerTarget = ref<CommentTarget | null>(null)
const composerBody = ref('')
const composerBusy = ref(false)
const composerError = ref('')

const activeThread = ref<RemoteReviewThread | null>(null)
const activeThreadDiffUrl = ref('')
const replyBody = ref('')
const threadActionBusy = ref(false)
const threadActionError = ref('')

const gutterMarks = ref<GutterMark[]>([])
const threadMarkers = ref<ThreadMarkerGroup[]>([])
const annotateChips = ref<AnnotateChip[]>([])
const hoverMark = ref<HoverBlockMark | null>(null)

const pendingScrollLine = ref<number | null>(null)

let selectionTimer: number | null = null
let layoutRaf: number | null = null
let docObserver: MutationObserver | null = null
let docResizeObserver: ResizeObserver | null = null

const currentRepoPath = computed(() => {
  const raw = (page.value as { repoSourcePath?: string }).repoSourcePath
  return typeof raw === 'string' ? raw : ''
})

const pageThreads = computed(() =>
  threads.value.filter(
    (t) =>
      t.path === currentRepoPath.value && (showResolved.value || !t.isResolved),
  ),
)

const filteredDrawerThreads = computed(() => {
  const base =
    threadScope.value === 'page'
      ? threads.value.filter((t) => t.path === currentRepoPath.value)
      : threads.value
  return showResolved.value ? base : base.filter((t) => !t.isResolved)
})

const openPageThreadCount = computed(
  () =>
    threads.value.filter(
      (t) => t.path === currentRepoPath.value && !t.isResolved,
    ).length,
)

function mapRepoPathToRoute(repoPath: string): string | null {
  if (repoPath === 'book/index.md') return '/'
  if (repoPath === 'VISION.md') return '/vision'
  const readme = repoPath.match(/^systems\/([a-z0-9_-]+)\/README\.md$/)
  if (readme) return `/${readme[1]}/`
  const chapter = repoPath.match(/^systems\/([a-z0-9_-]+)\/chapters\/([^/]+)\.md$/)
  if (chapter) return `/${chapter[1]}/${chapter[2]}`
  return null
}

function formatLineLabel(start: number, end: number): string {
  return end > start ? `L${start}–L${end}` : `L${start}`
}

function modeBadgeLabel(mode: CommentTarget['mode']): string {
  if (mode === 'inline') return 'Native inline PR thread'
  if (mode === 'file') return 'File-level PR thread (outside hunk)'
  return 'PR conversation comment (unchanged file)'
}

function saveDraftState() {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(
      draftStorageKey,
      JSON.stringify({ drafts: drafts.value, summaryBody: summaryBody.value }),
    )
  } catch {
    // ignore storage errors
  }
}

function loadDraftState() {
  if (typeof window === 'undefined') return
  try {
    const raw = localStorage.getItem(draftStorageKey)
    if (!raw) return
    const parsed = JSON.parse(raw) as {
      drafts?: DraftComment[]
      summaryBody?: string
    }
    if (Array.isArray(parsed.drafts)) {
      drafts.value = parsed.drafts
    }
    if (typeof parsed.summaryBody === 'string') {
      summaryBody.value = parsed.summaryBody
    }
  } catch {
    // ignore corrupted local drafts
  }
}

function saveAuthToken(token: string, persistLocal: boolean) {
  if (typeof window === 'undefined') return
  try {
    localStorage.removeItem(authStorageKey)
    sessionStorage.removeItem(authStorageKey)
    if (!token) return
    const payload = JSON.stringify({ token, persistLocal })
    if (persistLocal) {
      localStorage.setItem(authStorageKey, payload)
    } else {
      sessionStorage.setItem(authStorageKey, payload)
    }
  } catch {
    // ignore storage errors
  }
}

async function restoreAuth() {
  if (typeof window === 'undefined') return
  let savedRaw: string | null = null
  let savedLocal = true
  try {
    savedRaw = localStorage.getItem(authStorageKey)
    if (!savedRaw) {
      savedRaw = sessionStorage.getItem(authStorageKey)
      savedLocal = false
    }
  } catch {
    return
  }
  if (!savedRaw) return
  try {
    const parsed = JSON.parse(savedRaw) as { token?: string; persistLocal?: boolean }
    const token = (parsed.token ?? '').trim()
    if (!token) return
    persistLocalToggle.value = parsed.persistLocal ?? savedLocal
    const user = await verifyGitHubToken(token)
    auth.value = {
      token,
      login: user.login,
      avatarUrl: user.avatarUrl,
      persistLocal: persistLocalToggle.value,
    }
  } catch {
    // Keep UI non-blocking if stored token expired; clear invalid token.
    saveAuthToken('', true)
  }
}

async function connectToken() {
  const cleaned = tokenInput.value.trim()
  if (!cleaned) {
    authError.value = 'Paste a fine-grained GitHub PAT first.'
    return
  }
  authBusy.value = true
  authError.value = ''
  try {
    const user = await verifyGitHubToken(cleaned)
    auth.value = {
      token: cleaned,
      login: user.login,
      avatarUrl: user.avatarUrl,
      persistLocal: persistLocalToggle.value,
    }
    saveAuthToken(cleaned, persistLocalToggle.value)
    tokenInput.value = ''
    await refreshThreads()
  } catch (err) {
    authError.value = err instanceof Error ? err.message : 'Failed to verify GitHub token'
  } finally {
    authBusy.value = false
  }
}

function forgetToken() {
  auth.value = { token: '', login: '', avatarUrl: '', persistLocal: true }
  saveAuthToken('', true)
  refreshThreads()
}

async function refreshThreads() {
  threadsLoading.value = true
  threadsError.value = ''
  try {
    threads.value = await fetchPrThreads(meta.repo, meta.prNumber, auth.value.token)
    threadsLoadedOnce.value = true
    if (activeThread.value) {
      const updated = threads.value.find((t) => t.id === activeThread.value?.id)
      activeThread.value = updated ?? null
    }
  } catch (err) {
    threadsError.value =
      err instanceof Error ? err.message : 'Failed to load PR threads'
  } finally {
    threadsLoading.value = false
    scheduleMeasure()
  }
}

function openThreadsDrawer() {
  drawerOpen.value = true
  drawerTab.value = 'threads'
  if (!threadsLoadedOnce.value && !threadsLoading.value) {
    refreshThreads()
  }
}

function updateViewportMode() {
  if (typeof window === 'undefined') return
  isMobile.value = window.innerWidth < 768
}

function recomputeDocAnnotations() {
  if (typeof window === 'undefined') return
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot || !currentRepoPath.value) {
    gutterMarks.value = []
    threadMarkers.value = []
    annotateChips.value = []
    return
  }

  const scrollX = window.scrollX
  const scrollY = window.scrollY
  const docWidth = document.documentElement.clientWidth

  const nextGutters: GutterMark[] = []
  const nextAnnotate: AnnotateChip[] = []

  const blocks = Array.from(
    docRoot.querySelectorAll<HTMLElement>('[data-src-line]'),
  ).filter((el) => !el.closest('.apex-review-ui'))

  for (let i = 0; i < blocks.length; i += 1) {
    const el = blocks[i]
    const rect = el.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) continue

    const startLine = Number.parseInt(el.dataset.srcLine ?? '0', 10)
    const endLine = Number.parseInt(el.dataset.srcEnd ?? String(startLine), 10)
    if (startLine <= 0) continue

    if (
      showGutter.value &&
      el.tagName !== 'TR' &&
      isRangeInAddedDiff(currentRepoPath.value, startLine, endLine, meta.files)
    ) {
      nextGutters.push({
        key: `g:${i}:${startLine}`,
        top: rect.top + scrollY,
        left: Math.max(4, rect.left + scrollX - 10),
        height: Math.max(12, rect.height),
      })
    }

    if (annotateMode.value && el.tagName !== 'TR') {
      const target = resolveBlockTarget(el, docRoot, currentRepoPath.value, meta.files)
      if (target) {
        nextAnnotate.push({
          key: `a:${i}:${startLine}`,
          top: Math.max(4, rect.top + scrollY - 11),
          left: Math.min(docWidth - 68, Math.max(8, rect.right + scrollX - 58)),
          label: `+ L${startLine}`,
          target,
        })
      }
    }
  }

  const anchorGroups = new Map<
    HTMLElement,
    { line: number | null; items: RemoteReviewThread[] }
  >()
  for (const t of pageThreads.value) {
    const anchor = findAnchorElementForLine(docRoot, t.line)
    if (!anchor) continue
    const existing = anchorGroups.get(anchor)
    if (existing) {
      existing.items.push(t)
    } else {
      anchorGroups.set(anchor, { line: t.line, items: [t] })
    }
  }

  const nextThreadMarkers: ThreadMarkerGroup[] = []
  let idx = 0
  for (const [el, group] of anchorGroups.entries()) {
    const rect = el.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) continue
    const chipLeft =
      rect.right + 10 + 96 <= docWidth
        ? rect.right + scrollX + 8
        : Math.max(8, Math.min(docWidth - 100, rect.right + scrollX - 96))
    nextThreadMarkers.push({
      key: `tm:${idx}:${group.items[0].id}`,
      top: rect.top + scrollY + (chipLeft < rect.right + scrollX ? -10 : 2),
      left: chipLeft,
      line: group.line,
      allResolved: group.items.every((item) => item.isResolved),
      threads: group.items,
    })
    idx += 1
  }

  gutterMarks.value = nextGutters
  annotateChips.value = nextAnnotate
  threadMarkers.value = nextThreadMarkers
}

function scheduleMeasure() {
  if (typeof window === 'undefined') return
  if (layoutRaf !== null) {
    window.cancelAnimationFrame(layoutRaf)
  }
  layoutRaf = window.requestAnimationFrame(() => {
    layoutRaf = null
    recomputeDocAnnotations()
  })
}

function handleDocMouseMove(ev: MouseEvent) {
  if (isMobile.value || annotateMode.value) {
    hoverMark.value = null
    return
  }
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot || !(ev.target instanceof Element)) {
    hoverMark.value = null
    return
  }
  if (!docRoot.contains(ev.target) || ev.target.closest('.apex-review-ui')) {
    return
  }
  const block = ev.target.closest<HTMLElement>('[data-src-line]')
  if (!block || !docRoot.contains(block)) {
    hoverMark.value = null
    return
  }
  const rect = block.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) {
    hoverMark.value = null
    return
  }
  const startLine = Number.parseInt(block.dataset.srcLine ?? '1', 10)
  const endLine = Number.parseInt(block.dataset.srcEnd ?? String(startLine), 10)
  hoverMark.value = {
    top: rect.top + window.scrollY + 2,
    left: Math.max(8, rect.left + window.scrollX - 34),
    startLine,
    endLine,
    el: block,
  }
}

function updateSelectionAction() {
  if (typeof window === 'undefined') return
  const docRoot = document.querySelector('.vp-doc')
  const sel = window.getSelection()
  const target = resolveSelectionTarget(
    sel,
    docRoot,
    currentRepoPath.value,
    meta.files,
  )
  if (!target || !sel || sel.rangeCount === 0) {
    selectionTarget.value = null
    selectionRect.value = null
    return
  }
  const rect = sel.getRangeAt(0).getBoundingClientRect()
  if (rect.width <= 0 && rect.height <= 0) {
    selectionTarget.value = null
    selectionRect.value = null
    return
  }
  selectionTarget.value = target
  const x = Math.min(window.innerWidth - 90, Math.max(90, rect.left + rect.width / 2))
  const y = rect.top > 72 ? rect.top - 8 : rect.bottom + 36
  selectionRect.value = { x, y }
}

function scheduleSelectionCheck() {
  if (typeof window === 'undefined') return
  if (selectionTimer !== null) {
    window.clearTimeout(selectionTimer)
  }
  selectionTimer = window.setTimeout(updateSelectionAction, 110)
}

function openComposer(target: CommentTarget) {
  composerTarget.value = target
  composerBody.value = ''
  composerError.value = ''
  selectionTarget.value = null
  selectionRect.value = null
}

function openComposerFromHover() {
  if (!hoverMark.value) return
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot) return
  const target = resolveBlockTarget(
    hoverMark.value.el,
    docRoot,
    currentRepoPath.value,
    meta.files,
  )
  if (target) openComposer(target)
}

function addDraftToCart() {
  if (!composerTarget.value) return
  const text = composerBody.value.trim()
  if (!text) {
    composerError.value = 'Write a comment before adding.'
    return
  }
  const target = composerTarget.value
  drafts.value.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    ...target,
    body: text,
    createdAt: new Date().toISOString(),
  })
  saveDraftState()
  composerTarget.value = null
  composerBody.value = ''
  submitNotice.value = `Queued comment at ${target.path}:${target.startLine}`
}

async function postComposerNow() {
  if (!composerTarget.value || !auth.value.token) return
  const text = composerBody.value.trim()
  if (!text) {
    composerError.value = 'Write a comment first.'
    return
  }
  composerBusy.value = true
  composerError.value = ''
  const draft: DraftComment = {
    id: `${Date.now()}`,
    ...composerTarget.value,
    body: text,
    createdAt: new Date().toISOString(),
  }
  try {
    const outcomes = await submitBatchedReview(
      meta,
      [draft],
      '',
      'COMMENT',
      auth.value.token,
    )
    const failed = outcomes.find((o) => !o.ok)
    if (failed) {
      composerError.value = failed.error ?? 'Failed to post comment'
      return
    }
    composerTarget.value = null
    composerBody.value = ''
    submitNotice.value = 'Posted inline comment to PR.'
    await refreshThreads()
  } finally {
    composerBusy.value = false
  }
}

function removeDraft(id: string) {
  drafts.value = drafts.value.filter((d) => d.id !== id)
  saveDraftState()
}

async function submitQueuedReview() {
  if (!auth.value.token) {
    drawerTab.value = 'auth'
    return
  }
  if (drafts.value.length === 0 && !summaryBody.value.trim() && submitEvent.value === 'COMMENT') {
    submitError.value = 'Add at least one draft comment or review summary.'
    return
  }
  submitBusy.value = true
  submitError.value = ''
  submitNotice.value = ''
  try {
    const outcomes = await submitBatchedReview(
      meta,
      drafts.value,
      summaryBody.value,
      submitEvent.value,
      auth.value.token,
    )
    const failedIds = new Set(outcomes.filter((o) => !o.ok).map((o) => o.draftId))
    const succeededCount = outcomes.filter((o) => o.ok).length
    drafts.value = drafts.value.filter((d) => failedIds.has(d.id))
    if (failedIds.size === 0) {
      summaryBody.value = ''
      submitNotice.value = `Submitted ${succeededCount || 1} review item(s) to PR #${meta.prNumber}.`
    } else {
      const firstErr = outcomes.find((o) => !o.ok)?.error ?? 'Some comments failed'
      submitError.value = `${failedIds.size} draft(s) kept in cart: ${firstErr}`
    }
    saveDraftState()
    await refreshThreads()
  } catch (err) {
    submitError.value = err instanceof Error ? err.message : 'Review submission failed'
  } finally {
    submitBusy.value = false
  }
}

async function copyMarkdownCart() {
  const md = formatMarkdownBundle(meta, drafts.value, summaryBody.value)
  try {
    await navigator.clipboard.writeText(md)
    submitNotice.value = 'Copied formatted Markdown review bundle to clipboard.'
    submitError.value = ''
  } catch {
    submitError.value = 'Clipboard access denied; copy manually from browser.'
  }
}

async function openThreadCard(thread: RemoteReviewThread) {
  activeThread.value = thread
  replyBody.value = ''
  threadActionError.value = ''
  activeThreadDiffUrl.value =
    thread.url || (await buildGitHubDiffUrl(meta.repo, meta.prNumber, thread.path, thread.line))
}

async function sendThreadReply() {
  if (!activeThread.value || !auth.value.token || !replyBody.value.trim()) return
  threadActionBusy.value = true
  threadActionError.value = ''
  try {
    await replyToThread(
      meta.repo,
      meta.prNumber,
      activeThread.value.rootCommentId,
      replyBody.value,
      auth.value.token,
    )
    replyBody.value = ''
    await refreshThreads()
  } catch (err) {
    threadActionError.value = err instanceof Error ? err.message : 'Reply failed'
  } finally {
    threadActionBusy.value = false
  }
}

async function toggleThreadResolved(thread: RemoteReviewThread) {
  if (!auth.value.token || !thread.canResolve) return
  threadActionBusy.value = true
  threadActionError.value = ''
  try {
    await setThreadResolved(thread.id, !thread.isResolved, auth.value.token)
    await refreshThreads()
  } catch (err) {
    threadActionError.value = err instanceof Error ? err.message : 'Failed to update thread state'
  } finally {
    threadActionBusy.value = false
  }
}

async function jumpToLocation(repoPath: string, line: number | null) {
  const bookRoute = mapRepoPathToRoute(repoPath)
  if (!bookRoute) {
    const url = await buildGitHubDiffUrl(meta.repo, meta.prNumber, repoPath, line)
    window.open(url, '_blank', 'noreferrer')
    return
  }
  drawerOpen.value = false
  if (repoPath === currentRepoPath.value) {
    scrollToSourceLine(line)
  } else {
    pendingScrollLine.value = line
    await router.go(withBase(bookRoute))
  }
}

function scrollToSourceLine(line: number | null) {
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot) return
  const el = findAnchorElementForLine(docRoot, line)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}

function attachDocObservers() {
  docObserver?.disconnect()
  docResizeObserver?.disconnect()
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot) return
  docObserver = new MutationObserver(() => scheduleMeasure())
  docObserver.observe(docRoot, { childList: true, subtree: true })
  if (typeof ResizeObserver !== 'undefined') {
    docResizeObserver = new ResizeObserver(() => scheduleMeasure())
    docResizeObserver.observe(docRoot)
  }
}

watch(
  () => route.path,
  async () => {
    selectionTarget.value = null
    hoverMark.value = null
    await nextTick()
    attachDocObservers()
    scheduleMeasure()
    if (pendingScrollLine.value !== null) {
      const targetLine = pendingScrollLine.value
      pendingScrollLine.value = null
      window.setTimeout(() => scrollToSourceLine(targetLine), 120)
    }
  },
)

watch([annotateMode, showGutter, showResolved], () => {
  scheduleMeasure()
})

watch(
  [drafts, summaryBody],
  () => saveDraftState(),
  { deep: true },
)

onMounted(async () => {
  updateViewportMode()
  loadDraftState()
  await restoreAuth()
  if (auth.value.token) {
    await refreshThreads()
  }
  await nextTick()
  attachDocObservers()
  scheduleMeasure()
  window.addEventListener('resize', updateViewportMode, { passive: true })
  window.addEventListener('resize', scheduleMeasure, { passive: true })
  window.addEventListener('mousemove', handleDocMouseMove, { passive: true })
  document.addEventListener('selectionchange', scheduleSelectionCheck)
  document.addEventListener('mouseup', scheduleSelectionCheck)
  document.addEventListener('touchend', scheduleSelectionCheck)
})

onUnmounted(() => {
  docObserver?.disconnect()
  docResizeObserver?.disconnect()
  if (selectionTimer !== null) window.clearTimeout(selectionTimer)
  if (layoutRaf !== null) window.cancelAnimationFrame(layoutRaf)
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateViewportMode)
    window.removeEventListener('resize', scheduleMeasure)
    window.removeEventListener('mousemove', handleDocMouseMove)
    document.removeEventListener('selectionchange', scheduleSelectionCheck)
    document.removeEventListener('mouseup', scheduleSelectionCheck)
    document.removeEventListener('touchend', scheduleSelectionCheck)
  }
})
</script>

<template>
  <Teleport to="body">
    <div class="apex-review-ui apex-doc-markers" aria-hidden="false">
      <div
        v-for="g in gutterMarks"
        :key="g.key"
        class="apex-gutter-bar"
        :style="{ top: `${g.top}px`, left: `${g.left}px`, height: `${g.height}px` }"
        title="Modified in this PR"
      />

      <button
        v-if="hoverMark"
        type="button"
        class="apex-hover-add-btn"
        :style="{ top: `${hoverMark.top}px`, left: `${hoverMark.left}px` }"
        :title="`Comment on ${formatLineLabel(hoverMark.startLine, hoverMark.endLine)}`"
        :aria-label="`Add inline comment on ${formatLineLabel(hoverMark.startLine, hoverMark.endLine)}`"
        @click="openComposerFromHover"
      >
        +
      </button>

      <button
        v-for="chip in annotateChips"
        :key="chip.key"
        type="button"
        class="apex-annotate-chip"
        :style="{ top: `${chip.top}px`, left: `${chip.left}px` }"
        @click="openComposer(chip.target)"
      >
        {{ chip.label }}
      </button>

      <button
        v-for="tm in threadMarkers"
        :key="tm.key"
        type="button"
        class="apex-thread-chip"
        :class="{ 'is-resolved': tm.allResolved }"
        :style="{ top: `${tm.top}px`, left: `${tm.left}px` }"
        @click="openThreadCard(tm.threads[0])"
      >
        <span>{{ tm.allResolved ? '✓' : '💬' }}</span>
        <span>{{ tm.threads.length }}</span>
        <span v-if="tm.line">· L{{ tm.line }}</span>
      </button>
    </div>

    <button
      v-if="selectionTarget && selectionRect && !isMobile"
      type="button"
      class="apex-review-ui apex-selection-pill"
      :style="{ left: `${selectionRect.x}px`, top: `${selectionRect.y}px` }"
      @mousedown.prevent
      @click="openComposer(selectionTarget)"
    >
      💬 Comment ({{ formatLineLabel(selectionTarget.startLine, selectionTarget.endLine) }})
    </button>

    <div
      v-if="selectionTarget && isMobile"
      class="apex-review-ui apex-mobile-selection-bar"
    >
      <span class="apex-mono-path">
        {{ formatLineLabel(selectionTarget.startLine, selectionTarget.endLine) }} · {{ selectionTarget.blockKind }}
      </span>
      <div style="display: flex; gap: 6px">
        <button
          type="button"
          class="apex-rev-btn"
          @click="selectionTarget = null"
        >
          Dismiss
        </button>
        <button
          type="button"
          class="apex-rev-btn is-primary"
          @click="openComposer(selectionTarget)"
        >
          Comment
        </button>
      </div>
    </div>

    <div class="apex-review-ui apex-floating-dock" data-testid="apex-pr-dock">
      <button
        type="button"
        class="apex-rev-btn is-pill"
        :class="{ 'is-active': drawerOpen && drawerTab === 'threads' }"
        @click="openThreadsDrawer"
      >
        <span>PR #{{ meta.prNumber }}</span>
        <span v-if="openPageThreadCount > 0" class="apex-badge-count">{{ openPageThreadCount }}</span>
      </button>

      <button
        type="button"
        class="apex-rev-btn is-pill"
        :class="{ 'is-active': annotateMode }"
        title="Show tap targets on every paragraph, equation, diagram, and widget"
        @click="annotateMode = !annotateMode"
      >
        {{ annotateMode ? 'Done' : '+ Annotate' }}
      </button>

      <button
        type="button"
        class="apex-rev-btn is-pill"
        :class="{ 'is-primary': drafts.length > 0 }"
        @click="drawerOpen = true; drawerTab = 'drafts'"
      >
        <span>Review</span>
        <span v-if="drafts.length > 0" class="apex-badge-count">{{ drafts.length }}</span>
      </button>

      <button
        type="button"
        class="apex-rev-btn is-pill"
        :title="auth.login ? `Connected as @${auth.login}` : 'Connect GitHub PAT'"
        @click="drawerOpen = true; drawerTab = 'auth'"
      >
        {{ auth.login ? `@${auth.login}` : 'Connect' }}
      </button>
    </div>

    <div
      v-if="composerTarget"
      class="apex-review-ui apex-modal-backdrop"
      @click.self="composerTarget = null"
    >
      <div class="apex-modal-card" role="dialog" aria-label="Draft inline PR comment">
        <div class="apex-meta-row">
          <span class="apex-mono-path">
            {{ composerTarget.path }}:{{ formatLineLabel(composerTarget.startLine, composerTarget.endLine) }}
          </span>
          <span
            class="apex-mode-badge"
            :class="{ 'is-warn': composerTarget.mode !== 'inline' }"
          >
            {{ modeBadgeLabel(composerTarget.mode) }}
          </span>
        </div>

        <blockquote v-if="composerTarget.quote" class="apex-quote-box">
          {{ composerTarget.quote }}
        </blockquote>

        <textarea
          v-model="composerBody"
          rows="4"
          class="apex-textarea"
          placeholder="Write your inline review comment..."
          @keydown.meta.enter.prevent="addDraftToCart"
          @keydown.ctrl.enter.prevent="addDraftToCart"
        />

        <div v-if="composerError" class="apex-error-banner">{{ composerError }}</div>

        <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px">
          <button type="button" class="apex-rev-btn" @click="composerTarget = null">
            Cancel
          </button>
          <button
            v-if="auth.token"
            type="button"
            class="apex-rev-btn"
            :disabled="composerBusy"
            @click="postComposerNow"
          >
            {{ composerBusy ? 'Posting…' : 'Post Now' }}
          </button>
          <button
            type="button"
            class="apex-rev-btn is-primary"
            @click="addDraftToCart"
          >
            Add to Review Cart
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="activeThread"
      class="apex-review-ui apex-modal-backdrop"
      @click.self="activeThread = null"
    >
      <div class="apex-modal-card" role="dialog" aria-label="PR Review Thread">
        <div class="apex-meta-row">
          <span class="apex-mono-path">
            {{ activeThread.path }}<template v-if="activeThread.line">:L{{ activeThread.line }}</template>
          </span>
          <div style="display: flex; gap: 6px; align-items: center">
            <span
              class="apex-mode-badge"
              :class="activeThread.isResolved ? 'is-ok' : 'is-warn'"
            >
              {{ activeThread.isResolved ? 'Resolved' : activeThread.isOutdated ? 'Outdated' : 'Open' }}
            </span>
            <a
              v-if="activeThreadDiffUrl"
              :href="activeThreadDiffUrl"
              target="_blank"
              rel="noreferrer"
              class="apex-rev-btn"
              style="text-decoration: none"
            >
              GitHub ↗
            </a>
          </div>
        </div>

        <div
          v-for="msg in activeThread.comments"
          :key="msg.id"
          class="apex-card"
        >
          <div class="apex-meta-row">
            <strong>@{{ msg.author }}</strong>
            <span>{{ msg.createdAt ? msg.createdAt.slice(0, 10) : '' }}</span>
          </div>
          <div style="white-space: pre-wrap; font-size: 13.5px; line-height: 1.5">
            {{ msg.body }}
          </div>
        </div>

        <div v-if="threadActionError" class="apex-error-banner">{{ threadActionError }}</div>

        <template v-if="auth.token">
          <textarea
            v-if="activeThread.source !== 'issue'"
            v-model="replyBody"
            rows="3"
            class="apex-textarea"
            placeholder="Write a reply on this PR thread..."
          />
          <div style="display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px">
            <button
              v-if="activeThread.canResolve"
              type="button"
              class="apex-rev-btn"
              :disabled="threadActionBusy"
              @click="toggleThreadResolved(activeThread)"
            >
              {{ activeThread.isResolved ? 'Reopen Thread' : 'Resolve Thread' }}
            </button>
            <span v-else />
            <div style="display: flex; gap: 8px">
              <button type="button" class="apex-rev-btn" @click="activeThread = null">
                Close
              </button>
              <button
                v-if="activeThread.source !== 'issue'"
                type="button"
                class="apex-rev-btn is-primary"
                :disabled="threadActionBusy || !replyBody.trim()"
                @click="sendThreadReply"
              >
                {{ threadActionBusy ? 'Sending…' : 'Reply' }}
              </button>
            </div>
          </div>
        </template>
        <div v-else style="display: flex; justify-content: space-between; gap: 8px">
          <button
            type="button"
            class="apex-rev-btn is-primary"
            @click="activeThread = null; drawerOpen = true; drawerTab = 'auth'"
          >
            Connect PAT to Reply / Resolve
          </button>
          <button type="button" class="apex-rev-btn" @click="activeThread = null">
            Close
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="drawerOpen"
      class="apex-review-ui apex-drawer-backdrop"
      @click.self="drawerOpen = false"
    >
      <aside class="apex-drawer-panel" aria-label="PR Inline Review Drawer">
        <div class="apex-drawer-header">
          <div>
            <strong>PR #{{ meta.prNumber }} Review</strong>
            <div class="apex-mono-path" style="color: var(--vp-c-text-2)">
              {{ meta.repo }} · {{ meta.headSha.slice(0, 7) }}
            </div>
          </div>
          <div style="display: flex; gap: 6px">
            <a
              :href="meta.prUrl"
              target="_blank"
              rel="noreferrer"
              class="apex-rev-btn"
              style="text-decoration: none"
            >
              PR ↗
            </a>
            <button type="button" class="apex-rev-btn" @click="drawerOpen = false">
              ✕
            </button>
          </div>
        </div>

        <div class="apex-drawer-tabs">
          <button
            type="button"
            class="apex-rev-btn"
            :class="{ 'is-active': drawerTab === 'drafts' }"
            @click="drawerTab = 'drafts'"
          >
            Drafts ({{ drafts.length }})
          </button>
          <button
            type="button"
            class="apex-rev-btn"
            :class="{ 'is-active': drawerTab === 'threads' }"
            @click="openThreadsDrawer"
          >
            Threads ({{ threads.filter((t) => !t.isResolved).length }})
          </button>
          <button
            type="button"
            class="apex-rev-btn"
            :class="{ 'is-active': drawerTab === 'auth' }"
            @click="drawerTab = 'auth'"
          >
            {{ auth.login ? `@${auth.login}` : 'Setup' }}
          </button>
        </div>

        <div v-if="drawerTab === 'drafts'" class="apex-drawer-body">
          <div v-if="submitNotice" class="apex-status-banner">{{ submitNotice }}</div>
          <div v-if="submitError" class="apex-error-banner">{{ submitError }}</div>

          <div v-if="drafts.length === 0" class="apex-card">
            <div style="font-size: 13px; color: var(--vp-c-text-2)">
              Highlight any sentence, hover a paragraph <code>+</code> trigger, or tap <strong>+ Annotate</strong> to queue inline comments.
            </div>
          </div>

          <div v-for="d in drafts" :key="d.id" class="apex-card">
            <div class="apex-meta-row">
              <button
                type="button"
                class="apex-rev-btn"
                @click="jumpToLocation(d.path, d.startLine)"
              >
                {{ d.path.split('/').pop() }}:{{ formatLineLabel(d.startLine, d.endLine) }}
              </button>
              <button type="button" class="apex-rev-btn" @click="removeDraft(d.id)">
                Delete
              </button>
            </div>
            <blockquote v-if="d.quote" class="apex-quote-box">{{ d.quote }}</blockquote>
            <textarea v-model="d.body" rows="2" class="apex-textarea" />
            <span class="apex-mode-badge" :class="{ 'is-warn': d.mode !== 'inline' }">
              {{ modeBadgeLabel(d.mode) }}
            </span>
          </div>
        </div>

        <div v-if="drawerTab === 'drafts'" class="apex-drawer-footer">
          <textarea
            v-model="summaryBody"
            rows="2"
            class="apex-textarea"
            placeholder="Optional overall PR review summary..."
          />
          <div style="display: flex; gap: 8px; align-items: center">
            <select v-model="submitEvent" class="apex-select" style="flex: 1">
              <option value="COMMENT">Comment</option>
              <option value="REQUEST_CHANGES">Request changes</option>
              <option value="APPROVE">Approve</option>
            </select>
            <button
              type="button"
              class="apex-rev-btn"
              :disabled="drafts.length === 0 && !summaryBody.trim()"
              @click="copyMarkdownCart"
            >
              Copy MD
            </button>
            <button
              type="button"
              class="apex-rev-btn is-primary"
              :disabled="submitBusy"
              @click="submitQueuedReview"
            >
              {{ submitBusy ? 'Submitting…' : auth.token ? `Submit (${drafts.length})` : 'Connect & Submit' }}
            </button>
          </div>
        </div>

        <div v-if="drawerTab === 'threads'" class="apex-drawer-body">
          <div style="display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: space-between">
            <div style="display: flex; gap: 6px">
              <button
                type="button"
                class="apex-rev-btn"
                :class="{ 'is-active': threadScope === 'page' }"
                @click="threadScope = 'page'"
              >
                This page
              </button>
              <button
                type="button"
                class="apex-rev-btn"
                :class="{ 'is-active': threadScope === 'all' }"
                @click="threadScope = 'all'"
              >
                All PR files
              </button>
            </div>
            <div style="display: flex; gap: 6px; align-items: center">
              <label style="font-size: 12px; display: flex; align-items: center; gap: 4px; cursor: pointer">
                <input v-model="showResolved" type="checkbox" />
                Resolved
              </label>
              <button type="button" class="apex-rev-btn" :disabled="threadsLoading" @click="refreshThreads">
                {{ threadsLoading ? '…' : 'Refresh' }}
              </button>
            </div>
          </div>

          <div v-if="threadsError" class="apex-error-banner">{{ threadsError }}</div>

          <div v-if="filteredDrawerThreads.length === 0" class="apex-card">
            <div style="font-size: 13px; color: var(--vp-c-text-2)">
              No matching PR threads.
            </div>
          </div>

          <div v-for="t in filteredDrawerThreads" :key="t.id" class="apex-card">
            <div class="apex-meta-row">
              <button
                type="button"
                class="apex-rev-btn"
                @click="jumpToLocation(t.path, t.line)"
              >
                {{ t.path.split('/').pop() }}<template v-if="t.line">:L{{ t.line }}</template>
              </button>
              <span class="apex-mode-badge" :class="t.isResolved ? 'is-ok' : 'is-warn'">
                {{ t.isResolved ? 'Resolved' : 'Open' }}
              </span>
            </div>
            <div style="font-size: 13px; line-height: 1.45">
              <strong>@{{ t.comments[0]?.author }}:</strong>
              {{ t.comments[0]?.body }}
            </div>
            <div class="apex-meta-row">
              <span>{{ t.comments.length }} message(s)</span>
              <button type="button" class="apex-rev-btn" @click="openThreadCard(t)">
                Open Thread
              </button>
            </div>
          </div>
        </div>

        <div v-if="drawerTab === 'auth'" class="apex-drawer-body">
          <div class="apex-card">
            <strong>Direct GitHub PR Posting</strong>
            <div style="font-size: 13px; color: var(--vp-c-text-2); line-height: 1.5">
              Create a <strong>Fine-Grained Personal Access Token</strong> restricted strictly to
              <code>{{ meta.repo }}</code> with <strong>Pull requests: Read and write</strong> only.
            </div>
            <a
              href="https://github.com/settings/personal-access-tokens/new"
              target="_blank"
              rel="noreferrer"
              class="apex-rev-btn"
              style="text-decoration: none; align-self: flex-start"
            >
              Create Scoped Token on GitHub ↗
            </a>
          </div>

          <div v-if="auth.token" class="apex-card">
            <div class="apex-meta-row">
              <span>Connected as <strong>@{{ auth.login }}</strong></span>
              <span class="apex-mode-badge is-ok">
                {{ auth.persistLocal ? 'Saved in browser' : 'Tab session only' }}
              </span>
            </div>
            <button type="button" class="apex-rev-btn" @click="forgetToken">
              Forget Token
            </button>
          </div>

          <div v-else class="apex-card">
            <input
              v-model="tokenInput"
              type="password"
              class="apex-input"
              placeholder="github_pat_..."
              autocomplete="off"
            />
            <label style="font-size: 12.5px; display: flex; align-items: center; gap: 6px; cursor: pointer">
              <input v-model="persistLocalToggle" type="checkbox" />
              Remember token in this browser (uncheck for tab-only)
            </label>
            <div v-if="authError" class="apex-error-banner">{{ authError }}</div>
            <button
              type="button"
              class="apex-rev-btn is-primary"
              :disabled="authBusy"
              @click="connectToken"
            >
              {{ authBusy ? 'Verifying…' : 'Verify & Connect' }}
            </button>
          </div>

          <div class="apex-card">
            <strong>Display Options</strong>
            <label style="font-size: 13px; display: flex; align-items: center; gap: 6px; cursor: pointer">
              <input v-model="showGutter" type="checkbox" />
              Highlight added PR lines in left gutter
            </label>
            <label style="font-size: 13px; display: flex; align-items: center; gap: 6px; cursor: pointer">
              <input v-model="annotateMode" type="checkbox" />
              Show tap-to-comment badges on all blocks
            </label>
          </div>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
