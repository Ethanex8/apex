<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useData, useRoute, useRouter, withBase } from 'vitepress'
import prReviewMeta from 'virtual:apex-pr-review'
import {
  fetchPrHeadInfo,
  fetchPrThreads,
  formatMarkdownBundle,
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
  RemoteThreadComment,
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

interface BlockAddButton {
  key: string
  top: number
  left: number
  line: number
  el: HTMLElement
}

const { page } = useData()
const route = useRoute()
const router = useRouter()

const meta = prReviewMeta
const draftStorageKey = `apex-pr-review-drafts:${meta.repo}#${meta.prNumber}`
const authStorageKey = `apex-pr-review-auth:${meta.repo}`

const isMobile = ref(false)
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
const submitBusy = ref(false)
const submitNotice = ref('')
const submitError = ref('')

const threads = ref<RemoteReviewThread[]>([])
const threadsLoading = ref(false)
const threadsLoadedOnce = ref(false)
const threadsError = ref('')
const remoteHeadSha = ref('')
const isPreviewStale = computed(() =>
  Boolean(remoteHeadSha.value && remoteHeadSha.value !== meta.headSha),
)
let lastRefreshAt = 0

const drawerOpen = ref(false)
const drawerView = ref<'main' | 'setup'>('main')
const threadScope = ref<'page' | 'all'>('page')

const selectionTarget = ref<CommentTarget | null>(null)
const selectionRect = ref<{ x: number; y: number } | null>(null)

const composerTarget = ref<CommentTarget | null>(null)
const composerBody = ref('')
const composerError = ref('')

const activeThread = ref<RemoteReviewThread | null>(null)
const activeThreadDiffUrl = ref('')
const replyBody = ref('')
const inlineReplyThreadId = ref<string | null>(null)
const inlineReplyBody = ref('')
const expandedCommentKeys = ref<Set<string>>(new Set())
const threadActionBusy = ref(false)
const threadActionError = ref('')

const gutterMarks = ref<GutterMark[]>([])
const threadMarkers = ref<ThreadMarkerGroup[]>([])
const blockAddButtons = ref<BlockAddButton[]>([])

const pendingScrollLine = ref<number | null>(null)

const visibleBlocks = new Set<HTMLElement>()
let selectionTimer: number | null = null
let layoutRaf: number | null = null
let docObserver: MutationObserver | null = null
let docResizeObserver: ResizeObserver | null = null
let blockIntersectionObserver: IntersectionObserver | null = null

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
      ? threads.value.filter(
          (t) =>
            t.path === currentRepoPath.value ||
            t.path === 'PR Summary' ||
            t.path === 'PR Conversation',
        )
      : threads.value
  return showResolved.value ? base : base.filter((t) => !t.isResolved)
})

const openPageThreadCount = computed(
  () =>
    threads.value.filter(
      (t) => t.path === currentRepoPath.value && !t.isResolved,
    ).length,
)

const totalOpenThreadCount = computed(
  () => threads.value.filter((t) => !t.isResolved).length,
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

function isCommentExpanded(
  threadId: string,
  commentId: number,
  idx: number,
  total: number,
): boolean {
  if (idx >= total - 1) return true
  return expandedCommentKeys.value.has(`${threadId}:${commentId}`)
}

function toggleCommentExpanded(threadId: string, commentId: number) {
  const key = `${threadId}:${commentId}`
  const next = new Set(expandedCommentKeys.value)
  if (next.has(key)) {
    next.delete(key)
  } else {
    next.add(key)
  }
  expandedCommentKeys.value = next
}

function summarizeComment(msg: RemoteThreadComment): string {
  const firstLine = msg.body.replace(/\s+/g, ' ').trim()
  return firstLine.length > 64 ? `${firstLine.slice(0, 63)}…` : firstLine
}

function saveDraftState() {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(draftStorageKey, JSON.stringify({ drafts: drafts.value }))
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
    if (typeof parsed.summaryBody === 'string' && parsed.summaryBody.trim()) {
      drafts.value.push({
        id: `${Date.now()}-migrated`,
        kind: 'comment',
        path: '',
        startLine: 1,
        endLine: 1,
        apiStartLine: 1,
        apiLine: 1,
        mode: 'issue',
        quote: '',
        sectionTitle: `PR #${meta.prNumber}`,
        blockKind: 'PR Comment',
        body: parsed.summaryBody.trim(),
        createdAt: new Date().toISOString(),
      })
      saveDraftState()
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
    drawerView.value = 'main'
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
    const [fetchedThreads, headInfo] = await Promise.all([
      fetchPrThreads(meta.repo, meta.prNumber, auth.value.token),
      fetchPrHeadInfo(meta.repo, meta.prNumber, auth.value.token).catch(() => null),
    ])
    threads.value = fetchedThreads
    if (headInfo?.headSha) {
      remoteHeadSha.value = headInfo.headSha
    }
    threadsLoadedOnce.value = true
    lastRefreshAt = Date.now()
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

function maybeAutoRefreshThreads() {
  if (threadsLoading.value) return
  const minCooldownMs = auth.value.token ? 15_000 : 60_000
  if (!threadsLoadedOnce.value || Date.now() - lastRefreshAt > minCooldownMs) {
    refreshThreads()
  }
}

function openReviewDrawer(view: 'main' | 'setup' = 'main') {
  drawerOpen.value = true
  drawerView.value = view
  if (view === 'main') {
    maybeAutoRefreshThreads()
  }
}

function updateViewportMode() {
  if (typeof window === 'undefined') return
  isMobile.value = window.innerWidth < 768
}

function isAnnotatableBlock(el: HTMLElement): boolean {
  if (el.closest('.apex-review-ui')) return false
  if (el.tagName === 'TR') return false
  if (el.tagName === 'LI' && el.querySelector(':scope > p[data-src-line]')) {
    return false
  }
  return true
}

function observeDocumentBlocks() {
  visibleBlocks.clear()
  blockIntersectionObserver?.disconnect()
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot) return

  const blocks = Array.from(
    docRoot.querySelectorAll<HTMLElement>('[data-src-line]'),
  ).filter(isAnnotatableBlock)

  if (typeof IntersectionObserver === 'undefined') {
    for (const b of blocks) visibleBlocks.add(b)
    scheduleMeasure()
    return
  }

  blockIntersectionObserver = new IntersectionObserver(
    (entries) => {
      let changed = false
      for (const entry of entries) {
        const el = entry.target as HTMLElement
        if (entry.isIntersecting) {
          if (!visibleBlocks.has(el)) {
            visibleBlocks.add(el)
            changed = true
          }
        } else if (visibleBlocks.delete(el)) {
          changed = true
        }
      }
      if (changed) scheduleMeasure()
    },
    { rootMargin: '250px 0px' },
  )

  for (const el of blocks) {
    blockIntersectionObserver.observe(el)
  }
}

function recomputeDocAnnotations() {
  if (typeof window === 'undefined') return
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot || !currentRepoPath.value) {
    gutterMarks.value = []
    threadMarkers.value = []
    blockAddButtons.value = []
    return
  }

  const scrollX = window.scrollX
  const scrollY = window.scrollY
  const docWidth = document.documentElement.clientWidth
  const compactMode = docWidth < 960

  const nextGutters: GutterMark[] = []
  const nextButtons: BlockAddButton[] = []

  let idx = 0
  for (const el of visibleBlocks) {
    if (!docRoot.contains(el)) {
      visibleBlocks.delete(el)
      continue
    }
    const rect = el.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) continue

    const startLine = Number.parseInt(el.dataset.srcLine ?? '0', 10)
    const endLine = Number.parseInt(el.dataset.srcEnd ?? String(startLine), 10)
    if (startLine <= 0) continue

    if (
      showGutter.value &&
      isRangeInAddedDiff(currentRepoPath.value, startLine, endLine, meta.files)
    ) {
      nextGutters.push({
        key: `g:${idx}:${startLine}`,
        top: rect.top + scrollY,
        left: Math.max(3, rect.left + scrollX - 10),
        height: Math.max(12, rect.height),
      })
    }

    const btnLeft = compactMode
      ? Math.min(docWidth - 26, Math.max(8, rect.right + scrollX - 22))
      : Math.max(6, rect.left + scrollX - 30)
    const btnTop = compactMode
      ? Math.max(4, rect.top + scrollY - 10)
      : rect.top + scrollY + 3

    nextButtons.push({
      key: `b:${idx}:${startLine}`,
      top: btnTop,
      left: btnLeft,
      line: startLine,
      el,
    })
    idx += 1
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
  let tIdx = 0
  for (const [el, group] of anchorGroups.entries()) {
    const rect = el.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) continue
    const chipLeft =
      rect.right + 10 + 92 <= docWidth
        ? rect.right + scrollX + 8
        : Math.max(8, Math.min(docWidth - 96, rect.right + scrollX - 92))
    nextThreadMarkers.push({
      key: `tm:${tIdx}:${group.items[0].id}`,
      top: rect.top + scrollY + (chipLeft < rect.right + scrollX ? -12 : 2),
      left: chipLeft,
      line: group.line,
      allResolved: group.items.every((item) => item.isResolved),
      threads: group.items,
    })
    tIdx += 1
  }

  gutterMarks.value = nextGutters
  blockAddButtons.value = nextButtons
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

function openComposerForBlock(el: HTMLElement) {
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot) return
  const target = resolveBlockTarget(el, docRoot, currentRepoPath.value, meta.files)
  if (target) openComposer(target)
}

function openTopLevelComposer() {
  openComposer({
    path: '',
    startLine: 1,
    endLine: 1,
    apiStartLine: 1,
    apiLine: 1,
    mode: 'issue',
    quote: '',
    sectionTitle: `PR #${meta.prNumber}`,
    blockKind: 'PR Comment',
  })
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
    kind: 'comment',
    ...target,
    body: text,
    createdAt: new Date().toISOString(),
  })
  saveDraftState()
  composerTarget.value = null
  composerBody.value = ''
  submitNotice.value = target.path
    ? `Queued comment at ${target.path}:${target.startLine}`
    : 'Queued top-level PR comment draft.'
}

function removeDraft(id: string) {
  drafts.value = drafts.value.filter((d) => d.id !== id)
  saveDraftState()
}

async function submitQueuedReview() {
  if (!auth.value.token) {
    drawerView.value = 'setup'
    return
  }
  if (drafts.value.length === 0) {
    submitError.value = 'Add at least one draft comment before submitting.'
    return
  }
  submitBusy.value = true
  submitError.value = ''
  submitNotice.value = ''
  try {
    const result = await submitBatchedReview(
      meta,
      drafts.value,
      '',
      'COMMENT',
      auth.value.token,
    )
    const failedIds = new Set(result.outcomes.filter((o) => !o.ok).map((o) => o.draftId))
    const succeededCount = result.outcomes.filter((o) => o.ok).length
    drafts.value = drafts.value.filter((d) => failedIds.has(d.id))
    if (failedIds.size === 0 && result.summaryOk) {
      submitNotice.value = `Submitted ${succeededCount} item(s) to PR #${meta.prNumber}.`
    } else {
      const firstErr =
        result.summaryError ??
        result.outcomes.find((o) => !o.ok)?.error ??
        'Submission failed'
      submitError.value = firstErr
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
  const md = formatMarkdownBundle(meta, drafts.value, '')
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

function queuedRepliesFor(threadId: string): DraftComment[] {
  return drafts.value.filter((d) => d.kind === 'reply' && d.replyTarget?.threadId === threadId)
}

function stageThreadReply(thread: RemoteReviewThread, text: string, fromDrawer = false) {
  const trimmed = text.trim()
  if (!trimmed) return
  const targetAuthor = thread.comments[0]?.author ?? 'reviewer'
  const firstSnippet = thread.comments[0]?.body.split('\n')[0]?.slice(0, 140) ?? ''
  const lineNum = thread.line ?? 1
  drafts.value.push({
    id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    kind: 'reply',
    replyTarget: {
      threadId: thread.id,
      rootCommentId: thread.rootCommentId,
      source: thread.source,
      author: targetAuthor,
      path: thread.path,
      line: thread.line,
    },
    path: thread.path,
    startLine: lineNum,
    endLine: lineNum,
    apiStartLine: lineNum,
    apiLine: lineNum,
    mode: thread.source === 'review' ? 'issue' : thread.source,
    quote: firstSnippet,
    sectionTitle: `Reply to @${targetAuthor}`,
    blockKind: 'reply',
    body: trimmed,
    createdAt: new Date().toISOString(),
  })
  saveDraftState()
  submitNotice.value = `Staged reply to @${targetAuthor}. Click Submit in the drawer when ready to send.`
  submitError.value = ''
  threadActionError.value = ''
  threadsError.value = ''
  if (fromDrawer) {
    inlineReplyThreadId.value = null
    inlineReplyBody.value = ''
  } else {
    replyBody.value = ''
  }
}

async function toggleThreadResolved(thread: RemoteReviewThread) {
  if (!auth.value.token || !thread.canResolve) return
  threadActionBusy.value = true
  threadActionError.value = ''
  threadsError.value = ''
  try {
    const nextResolved = await setThreadResolved(
      meta.repo,
      meta.prNumber,
      thread,
      !thread.isResolved,
      auth.value.token,
    )
    threads.value = threads.value.map((item) =>
      item.id === thread.id ? { ...item, isResolved: nextResolved } : item,
    )
    if (activeThread.value?.id === thread.id) {
      activeThread.value = { ...activeThread.value, isResolved: nextResolved }
    }
    scheduleMeasure()
    await refreshThreads()
  } catch (err) {
    const msg = err instanceof Error ? err.message : 'Failed to update thread state'
    threadActionError.value = msg
    threadsError.value = msg
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
  observeDocumentBlocks()
  docObserver = new MutationObserver(() => {
    observeDocumentBlocks()
    scheduleMeasure()
  })
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

watch([showGutter, showResolved], () => {
  scheduleMeasure()
})

watch(
  drafts,
  () => saveDraftState(),
  { deep: true },
)

function syncBodyScrollLock(locked: boolean) {
  if (typeof document === 'undefined') return
  const val = locked ? 'hidden' : ''
  document.documentElement.style.overflow = val
  document.body.style.overflow = val
}

watch(
  [drawerOpen, composerTarget, activeThread],
  ([drawer, composer, thread]) => {
    syncBodyScrollLock(Boolean(drawer || composer || thread))
  },
)

function handleWindowFocus() {
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
  maybeAutoRefreshThreads()
}

function reloadPreviewPage() {
  if (typeof window !== 'undefined') {
    window.location.reload()
  }
}

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
  window.addEventListener('focus', handleWindowFocus)
  document.addEventListener('visibilitychange', handleWindowFocus)
  document.addEventListener('selectionchange', scheduleSelectionCheck)
  document.addEventListener('mouseup', scheduleSelectionCheck)
  document.addEventListener('touchend', scheduleSelectionCheck)
})

onUnmounted(() => {
  syncBodyScrollLock(false)
  docObserver?.disconnect()
  docResizeObserver?.disconnect()
  blockIntersectionObserver?.disconnect()
  if (selectionTimer !== null) window.clearTimeout(selectionTimer)
  if (layoutRaf !== null) window.cancelAnimationFrame(layoutRaf)
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateViewportMode)
    window.removeEventListener('resize', scheduleMeasure)
    window.removeEventListener('focus', handleWindowFocus)
    document.removeEventListener('visibilitychange', handleWindowFocus)
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
        v-for="btn in blockAddButtons"
        :key="btn.key"
        type="button"
        class="apex-block-add-btn"
        :style="{ top: `${btn.top}px`, left: `${btn.left}px` }"
        :data-src-btn-line="btn.line"
        :title="`Add comment at L${btn.line}`"
        :aria-label="`Add comment at line ${btn.line}`"
        @click="openComposerForBlock(btn.el)"
      >
        +
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
        :class="{ 'is-primary': drafts.length > 0, 'is-active': drawerOpen && drafts.length === 0 }"
        :title="`Open PR #${meta.prNumber} review drawer`"
        @click="openReviewDrawer('main')"
      >
        <span>Review</span>
        <span v-if="drafts.length > 0" class="apex-badge-count">{{ drafts.length }}</span>
        <span v-else-if="openPageThreadCount > 0" class="apex-badge-count is-warn">{{ openPageThreadCount }}</span>
      </button>
    </div>

    <div
      v-if="composerTarget"
      class="apex-review-ui apex-modal-backdrop"
      @click.self="composerTarget = null"
      @wheel.self.prevent
      @touchmove.self.prevent
    >
      <div class="apex-modal-card" role="dialog" aria-label="Draft PR comment">
        <div class="apex-meta-row">
          <span class="apex-mono-path">
            {{ composerTarget.path ? `${composerTarget.path}:${formatLineLabel(composerTarget.startLine, composerTarget.endLine)}` : `PR #${meta.prNumber}` }}
          </span>
          <span
            class="apex-mode-badge"
            :class="{ 'is-warn': composerTarget.mode !== 'inline' && Boolean(composerTarget.path) }"
          >
            {{ !composerTarget.path ? 'Top-level PR comment' : modeBadgeLabel(composerTarget.mode) }}
          </span>
        </div>

        <blockquote v-if="composerTarget.quote" class="apex-quote-box">
          {{ composerTarget.quote }}
        </blockquote>

        <textarea
          v-model="composerBody"
          rows="4"
          class="apex-textarea"
          :placeholder="composerTarget.path ? 'Write your inline review comment...' : 'Write a top-level PR comment...'"
          @keydown.meta.enter.prevent="addDraftToCart"
          @keydown.ctrl.enter.prevent="addDraftToCart"
        />

        <div v-if="composerError" class="apex-error-banner">{{ composerError }}</div>

        <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px">
          <button type="button" class="apex-rev-btn" @click="composerTarget = null">
            Cancel
          </button>
          <button
            type="button"
            class="apex-rev-btn is-primary"
            @click="addDraftToCart"
          >
            Add
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="activeThread"
      class="apex-review-ui apex-modal-backdrop"
      @click.self="activeThread = null"
      @wheel.self.prevent
      @touchmove.self.prevent
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

        <template v-for="(msg, mIdx) in activeThread.comments" :key="msg.id">
          <button
            v-if="!isCommentExpanded(activeThread.id, msg.id, mIdx, activeThread.comments.length)"
            type="button"
            class="apex-collapsed-msg"
            @click="toggleCommentExpanded(activeThread.id, msg.id)"
          >
            <span>▸</span>
            <strong>@{{ msg.author }}</strong>
            <span class="apex-collapsed-snippet">{{ summarizeComment(msg) }}</span>
          </button>
          <div v-else class="apex-expanded-msg">
            <div class="apex-meta-row">
              <strong>@{{ msg.author }}</strong>
              <div style="display: flex; gap: 8px; align-items: center">
                <span>{{ msg.createdAt ? msg.createdAt.slice(0, 10) : '' }}</span>
                <button
                  v-if="mIdx < activeThread.comments.length - 1"
                  type="button"
                  class="apex-rev-btn"
                  style="padding: 1px 6px; font-size: 11px"
                  @click="toggleCommentExpanded(activeThread.id, msg.id)"
                >
                  Collapse
                </button>
              </div>
            </div>
            <div style="white-space: pre-wrap; font-size: 13.5px; line-height: 1.5">
              {{ msg.body }}
            </div>
          </div>
        </template>

        <div
          v-for="qr in queuedRepliesFor(activeThread.id)"
          :key="qr.id"
          class="apex-expanded-msg"
          style="border-style: dashed; border-color: var(--vp-c-brand-1)"
        >
          <div class="apex-meta-row">
            <strong>Staged reply draft</strong>
            <button
              type="button"
              class="apex-rev-btn"
              style="padding: 1px 6px; font-size: 11px"
              @click="removeDraft(qr.id)"
            >
              Remove
            </button>
          </div>
          <div style="white-space: pre-wrap; font-size: 13.5px; line-height: 1.5">
            {{ qr.body }}
          </div>
        </div>

        <div v-if="threadActionError" class="apex-error-banner">{{ threadActionError }}</div>

        <textarea
          v-model="replyBody"
          rows="3"
          class="apex-textarea"
          placeholder="Stage a reply draft on this thread..."
          @keydown.meta.enter.prevent="stageThreadReply(activeThread, replyBody, false)"
          @keydown.ctrl.enter.prevent="stageThreadReply(activeThread, replyBody, false)"
        />
        <div style="display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px">
          <button
            v-if="auth.token && activeThread.canResolve"
            type="button"
            class="apex-rev-btn"
            :disabled="threadActionBusy"
            @click="toggleThreadResolved(activeThread)"
          >
            {{ activeThread.isResolved ? 'Reopen Thread' : 'Resolve Thread' }}
          </button>
          <button
            v-else-if="activeThread.canResolve"
            type="button"
            class="apex-rev-btn"
            @click="activeThread = null; openReviewDrawer('setup')"
          >
            Connect PAT to Resolve
          </button>
          <span v-else />
          <div style="display: flex; gap: 8px">
            <button type="button" class="apex-rev-btn" @click="activeThread = null">
              Close
            </button>
            <button
              type="button"
              class="apex-rev-btn is-primary"
              :disabled="!replyBody.trim()"
              @click="stageThreadReply(activeThread, replyBody, false)"
            >
              Add Reply
            </button>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="drawerOpen"
      class="apex-review-ui apex-drawer-backdrop"
      @click.self="drawerOpen = false"
      @wheel.self.prevent
      @touchmove.self.prevent
    >
      <aside class="apex-drawer-panel" aria-label="PR Inline Review Drawer">
        <div class="apex-drawer-header">
          <div>
            <strong>Review</strong>
            <div class="apex-mono-path" style="color: var(--vp-c-text-2)">
              PR #{{ meta.prNumber }} · {{ meta.headSha.slice(0, 7) }}
            </div>
          </div>
          <div style="display: flex; gap: 6px">
            <button
              type="button"
              class="apex-rev-btn"
              :class="{ 'is-active': drawerView === 'setup' }"
              :title="auth.login ? `GitHub token & settings (connected as @${auth.login})` : 'GitHub token & review settings'"
              @click="drawerView = drawerView === 'setup' ? 'main' : 'setup'"
            >
              {{ drawerView === 'setup' ? '← Review' : 'Settings' }}
            </button>
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

        <template v-if="drawerView === 'main'">
          <div class="apex-drawer-body">
            <div
              v-if="isPreviewStale"
              class="apex-status-banner"
              style="display: flex; align-items: center; justify-content: space-between; gap: 8px"
            >
              <span>
                PR updated to <code>{{ remoteHeadSha.slice(0, 7) }}</code> (this preview is
                <code>{{ meta.headSha.slice(0, 7) }}</code>). Reload once deploy completes; drafts stay saved.
              </span>
              <button type="button" class="apex-rev-btn" @click="reloadPreviewPage">
                Reload
              </button>
            </div>
            <div v-if="submitNotice" class="apex-status-banner">{{ submitNotice }}</div>
            <div v-if="submitError" class="apex-error-banner">{{ submitError }}</div>

            <div class="apex-section-heading">
              <span>Pending Drafts ({{ drafts.length }})</span>
              <button
                type="button"
                class="apex-rev-btn"
                style="text-transform: none; letter-spacing: 0; font-weight: 500"
                @click="openTopLevelComposer"
              >
                + PR Comment
              </button>
            </div>

            <div v-if="drafts.length === 0" class="apex-card">
              <div style="font-size: 13px; color: var(--vp-c-text-2)">
                Highlight any sentence, click <strong>+</strong> beside any block, or use <strong>+ PR Comment</strong> to queue drafts.
              </div>
            </div>

            <div v-for="d in drafts" :key="d.id" class="apex-card">
              <div class="apex-meta-row">
                <button
                  v-if="d.path"
                  type="button"
                  class="apex-rev-btn"
                  @click="jumpToLocation(d.path, d.startLine)"
                >
                  {{ d.kind === 'reply' && d.replyTarget ? `Reply · ${d.path.split('/').pop()}:L${d.replyTarget.line ?? d.startLine}` : `${d.path.split('/').pop()}:${formatLineLabel(d.startLine, d.endLine)}` }}
                </button>
                <span v-else class="apex-mono-path">
                  {{ d.kind === 'reply' && d.replyTarget ? `Reply to @${d.replyTarget.author}` : `PR #${meta.prNumber}` }}
                </span>
                <button type="button" class="apex-rev-btn" @click="removeDraft(d.id)">
                  Delete
                </button>
              </div>
              <blockquote v-if="d.quote" class="apex-quote-box">{{ d.quote }}</blockquote>
              <textarea v-model="d.body" rows="2" class="apex-textarea" />
              <span
                class="apex-mode-badge"
                :class="{ 'is-warn': d.kind !== 'reply' && d.mode !== 'inline' && Boolean(d.path) }"
              >
                {{ d.kind === 'reply' && d.replyTarget ? `Reply to @${d.replyTarget.author}` : !d.path ? 'Top-level PR comment' : modeBadgeLabel(d.mode) }}
              </span>
            </div>

            <div class="apex-section-heading" style="margin-top: 8px">
              <span>PR Threads ({{ totalOpenThreadCount }} open)</span>
              <div style="display: flex; gap: 6px; align-items: center; text-transform: none; letter-spacing: 0">
                <label style="font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 4px; cursor: pointer">
                  <input v-model="showResolved" type="checkbox" />
                  Resolved
                </label>
                <button type="button" class="apex-rev-btn" :disabled="threadsLoading" @click="refreshThreads">
                  {{ threadsLoading ? '…' : 'Refresh' }}
                </button>
              </div>
            </div>

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
                <div style="display: flex; gap: 6px; align-items: center">
                  <span class="apex-mode-badge" :class="t.isResolved ? 'is-ok' : 'is-warn'">
                    {{ t.isResolved ? 'Resolved' : 'Open' }}
                  </span>
                  <button
                    v-if="t.canResolve && auth.token"
                    type="button"
                    class="apex-rev-btn"
                    style="padding: 2px 8px; font-size: 11.5px"
                    :disabled="threadActionBusy"
                    @click="toggleThreadResolved(t)"
                  >
                    {{ t.isResolved ? 'Reopen' : 'Resolve' }}
                  </button>
                </div>
              </div>

              <template v-for="(msg, mIdx) in t.comments" :key="msg.id">
                <button
                  v-if="!isCommentExpanded(t.id, msg.id, mIdx, t.comments.length)"
                  type="button"
                  class="apex-collapsed-msg"
                  @click="toggleCommentExpanded(t.id, msg.id)"
                >
                  <span>▸</span>
                  <strong>@{{ msg.author }}</strong>
                  <span class="apex-collapsed-snippet">{{ summarizeComment(msg) }}</span>
                </button>
                <div v-else class="apex-expanded-msg">
                  <div class="apex-meta-row">
                    <strong>@{{ msg.author }}</strong>
                    <div style="display: flex; gap: 6px; align-items: center">
                      <span>{{ msg.createdAt ? msg.createdAt.slice(0, 10) : '' }}</span>
                      <button
                        v-if="mIdx < t.comments.length - 1"
                        type="button"
                        class="apex-rev-btn"
                        style="padding: 1px 6px; font-size: 11px"
                        @click="toggleCommentExpanded(t.id, msg.id)"
                      >
                        Collapse
                      </button>
                    </div>
                  </div>
                  <div style="white-space: pre-wrap; font-size: 13px; line-height: 1.45">
                    {{ msg.body }}
                  </div>
                </div>
              </template>

              <div
                v-for="qr in queuedRepliesFor(t.id)"
                :key="qr.id"
                class="apex-expanded-msg"
                style="border-style: dashed; border-color: var(--vp-c-brand-1)"
              >
                <div class="apex-meta-row">
                  <strong>Staged reply draft</strong>
                  <button
                    type="button"
                    class="apex-rev-btn"
                    style="padding: 1px 6px; font-size: 11px"
                    @click="removeDraft(qr.id)"
                  >
                    Remove
                  </button>
                </div>
                <div style="white-space: pre-wrap; font-size: 13px; line-height: 1.45">
                  {{ qr.body }}
                </div>
              </div>

              <div v-if="inlineReplyThreadId === t.id" style="display: flex; flex-direction: column; gap: 6px">
                <textarea
                  v-model="inlineReplyBody"
                  rows="2"
                  class="apex-textarea"
                  placeholder="Stage a reply draft..."
                  @keydown.meta.enter.prevent="stageThreadReply(t, inlineReplyBody, true)"
                  @keydown.ctrl.enter.prevent="stageThreadReply(t, inlineReplyBody, true)"
                />
                <div style="display: flex; justify-content: flex-end; gap: 6px">
                  <button
                    type="button"
                    class="apex-rev-btn"
                    @click="inlineReplyThreadId = null; inlineReplyBody = ''"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    class="apex-rev-btn is-primary"
                    :disabled="!inlineReplyBody.trim()"
                    @click="stageThreadReply(t, inlineReplyBody, true)"
                  >
                    Add Reply
                  </button>
                </div>
              </div>

              <div class="apex-meta-row">
                <span>{{ t.comments.length }} comment(s)</span>
                <div style="display: flex; gap: 6px">
                  <button
                    v-if="inlineReplyThreadId !== t.id"
                    type="button"
                    class="apex-rev-btn"
                    @click="inlineReplyThreadId = t.id; inlineReplyBody = ''"
                  >
                    Reply
                  </button>
                  <button type="button" class="apex-rev-btn" @click="openThreadCard(t)">
                    Open
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="apex-drawer-footer">
            <div style="display: flex; gap: 8px; justify-content: flex-end">
              <button
                type="button"
                class="apex-rev-btn"
                :disabled="drafts.length === 0"
                @click="copyMarkdownCart"
              >
                Copy MD
              </button>
              <button
                type="button"
                class="apex-rev-btn is-primary"
                :disabled="submitBusy || (Boolean(auth.token) && drafts.length === 0)"
                @click="submitQueuedReview"
              >
                {{ submitBusy ? 'Submitting…' : auth.token ? (drafts.length > 0 ? `Submit (${drafts.length})` : 'Submit') : 'Connect & Submit' }}
              </button>
            </div>
          </div>
        </template>

        <div v-else class="apex-drawer-body">
          <div class="apex-card">
            <strong>One-Time GitHub Setup per Browser</strong>
            <div style="font-size: 13px; color: var(--vp-c-text-2); line-height: 1.5">
              Save a single <strong>Fine-Grained PAT</strong> restricted strictly to
              <code>{{ meta.repo }}</code> with <strong>Pull requests: Read and write</strong> only.
              It is reused automatically across all future Apex PR previews until expiration.
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
                {{ auth.persistLocal ? 'Saved across all PRs' : 'This tab only' }}
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
              Remember across all PR previews in this browser
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
          </div>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
