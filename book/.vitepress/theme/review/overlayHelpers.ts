/**
 * Purpose: Pure routing, draft validation/creation, thread status, and DOM-predicate helpers for `PrReviewOverlay.vue`.
 * Usage: Imported by `PrReviewOverlay.vue` at runtime and tested directly under `node --test` in `review.test.mts`.
 * Invariants: All functions are browser-DOM-optional and side-effect-free (no DOM, storage, or network mutations; ID/timestamp helpers sample clock/random); invalid stored drafts fail closed.
 */

import type {
  CommentTarget,
  DraftComment,
  RemoteReviewThread,
  RemoteThreadComment,
} from './types.ts'

export const MOBILE_VIEWPORT_MAX_WIDTH = 768
export const COMPACT_DOC_MAX_WIDTH = 960
export const SUMMARY_TRUNCATE_CHARS = 64
export const QUOTE_SNIPPET_MAX_CHARS = 140
export const POPOVER_X_MARGIN_PX = 90
export const POPOVER_TOP_THRESHOLD_PX = 72
export const POPOVER_ABOVE_OFFSET_PX = 8
export const POPOVER_BELOW_OFFSET_PX = 36
export const AUTH_REFRESH_COOLDOWN_MS = 15_000
export const ANON_REFRESH_COOLDOWN_MS = 60_000

const ALLOWED_DRAFT_MODES = new Set<CommentTarget['mode']>(['inline', 'file', 'issue'])
const ALLOWED_DRAFT_KINDS = new Set<NonNullable<DraftComment['kind']>>(['comment', 'reply', 'resolve'])
const ALLOWED_THREAD_SOURCES = new Set<RemoteReviewThread['source']>(['inline', 'file', 'issue', 'review'])

/** Minimal structural DOM interface so block-annotation filtering can be unit-tested without a full browser DOM. */
export interface BlockLike {
  closest(selector: string): unknown
  tagName: string
  querySelector(selector: string): unknown
}

/** Map a repository markdown path to its published VitePress textbook route, or `null` when non-book. */
export function mapRepoPathToRoute(repoPath: string): string | null {
  if (repoPath === 'book/index.md') return '/'
  if (repoPath === 'VISION.md') return '/vision'
  const chapter = repoPath.match(/^systems\/([a-z0-9_-]+)\/chapters\/([^/]+)\.md$/)
  if (chapter) return `/${chapter[1]}/${chapter[2]}`
  return null
}

/** Format a 1-indexed inclusive source range (`L12` or `L12–L18`). */
export function formatLineLabel(start: number, end: number): string {
  return end > start ? `L${start}–L${end}` : `L${start}`
}

/** Return the human-readable GitHub API posting mode label shown in the review composer. */
export function modeBadgeLabel(mode: CommentTarget['mode']): string {
  if (mode === 'inline') return 'Native inline PR thread'
  if (mode === 'file') return 'File-level PR thread (outside hunk)'
  return 'PR conversation comment (unchanged file)'
}

/** Condense a thread comment body into a single truncated preview line for collapsed history items. */
export function summarizeComment(msg: RemoteThreadComment): string {
  const firstLine = msg.body.replace(/\s+/g, ' ').trim()
  return firstLine.length > SUMMARY_TRUNCATE_CHARS
    ? `${firstLine.slice(0, SUMMARY_TRUNCATE_CHARS - 1)}…`
    : firstLine
}

/** Return true when a `[data-src-line]` element should receive its own margin bar and `+` comment trigger. */
export function isAnnotatableBlock(el: BlockLike): boolean {
  // Skip controls inside our own overlay shadow/drawer containers, raw table rows, and list wrappers whose child <p> carries the block anchor.
  if (el.closest('.apex-review-ui')) return false
  if (el.tagName === 'TR') return false
  if (el.tagName === 'LI' && el.querySelector(':scope > p[data-src-line]')) {
    return false
  }
  return true
}

/** Generate a uniform unique identifier for locally queued PR review drafts. */
export function makeDraftId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

/** Build the default conversation-level `CommentTarget` for general PR comments not tied to a book block. */
export function buildTopLevelTarget(prNumber: number): CommentTarget {
  return {
    path: '',
    startLine: 1,
    endLine: 1,
    apiStartLine: 1,
    apiLine: 1,
    mode: 'issue',
    quote: '',
    sectionTitle: `PR #${prNumber}`,
    blockKind: 'PR Comment',
  }
}

/** Type guard for non-null plain JSON objects. */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Type guard for positive 1-indexed integers. */
function isPositiveInt(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1
}

/** Build shared `DraftComment` location and timestamp fields derived from a remote review thread. */
function buildThreadDraftBase(
  thread: RemoteReviewThread,
): Pick<
  DraftComment,
  'id' | 'path' | 'startLine' | 'endLine' | 'apiStartLine' | 'apiLine' | 'mode' | 'quote' | 'createdAt'
> {
  const firstSnippet = thread.comments[0]?.body.split('\n')[0]?.slice(0, QUOTE_SNIPPET_MAX_CHARS) ?? ''
  const lineNum = isPositiveInt(thread.line) ? thread.line : 1
  return {
    id: makeDraftId(),
    path: thread.path,
    startLine: lineNum,
    endLine: lineNum,
    apiStartLine: lineNum,
    apiLine: lineNum,
    mode: thread.source === 'review' ? 'issue' : thread.source,
    quote: firstSnippet,
    createdAt: new Date().toISOString(),
  }
}

/** Create a queued review comment draft from a resolved target and trimmed body text. */
export function createDraftComment(target: CommentTarget, body: string): DraftComment {
  return {
    id: makeDraftId(),
    kind: 'comment',
    ...target,
    body,
    createdAt: new Date().toISOString(),
  }
}

/** Create a queued reply draft targeting an existing remote PR review thread. */
export function createReplyDraft(thread: RemoteReviewThread, body: string): DraftComment {
  const targetAuthor = thread.comments[0]?.author ?? 'reviewer'
  return {
    ...buildThreadDraftBase(thread),
    kind: 'reply',
    replyTarget: {
      threadId: thread.id,
      rootCommentId: thread.rootCommentId,
      source: thread.source,
      author: targetAuthor,
      path: thread.path,
      line: thread.line,
    },
    sectionTitle: `Reply to @${targetAuthor}`,
    blockKind: 'reply',
    body,
  }
}

/** Create a queued thread resolve/reopen draft toggling `thread.isResolved`. */
export function createResolveDraft(thread: RemoteReviewThread): DraftComment {
  const nextResolved = !thread.isResolved
  return {
    ...buildThreadDraftBase(thread),
    kind: 'resolve',
    resolveTarget: {
      threadId: thread.id,
      rootCommentId: thread.rootCommentId,
      source: thread.source,
      path: thread.path,
      line: thread.line,
      resolved: nextResolved,
      rawRootBody: thread.rawRootBody,
    },
    sectionTitle: nextResolved ? 'Resolve thread' : 'Reopen thread',
    blockKind: nextResolved ? 'Resolve' : 'Reopen',
    body: nextResolved ? 'Resolve thread' : 'Reopen thread',
  }
}

/** Validate `replyTarget` or `resolveTarget` sub-objects attached to reply/resolve drafts. */
function isValidThreadActionTarget(
  target: unknown,
  isResolve: boolean,
): boolean {
  if (!isRecord(target)) return false
  if (
    typeof target.threadId !== 'string' ||
    !target.threadId ||
    !isPositiveInt(target.rootCommentId) ||
    typeof target.source !== 'string' ||
    !ALLOWED_THREAD_SOURCES.has(target.source as RemoteReviewThread['source']) ||
    typeof target.path !== 'string' ||
    (target.line !== null && !isPositiveInt(target.line))
  ) {
    return false
  }
  if (!isResolve) {
    return typeof target.author === 'string' && target.author.length > 0
  }
  return (
    typeof target.resolved === 'boolean' &&
    (target.rawRootBody === undefined || typeof target.rawRootBody === 'string')
  )
}

/** Validate a deserialized `localStorage` draft record before allowing it into the active submission queue. */
export function isValidDraftComment(raw: unknown): raw is DraftComment {
  if (!isRecord(raw)) return false
  if (
    typeof raw.id !== 'string' ||
    !raw.id ||
    typeof raw.path !== 'string' ||
    !isPositiveInt(raw.startLine) ||
    !isPositiveInt(raw.endLine) ||
    !isPositiveInt(raw.apiStartLine) ||
    !isPositiveInt(raw.apiLine) ||
    raw.endLine < raw.startLine ||
    raw.apiLine < raw.apiStartLine ||
    typeof raw.mode !== 'string' ||
    !ALLOWED_DRAFT_MODES.has(raw.mode as CommentTarget['mode']) ||
    (raw.mode !== 'issue' && !raw.path.trim()) ||
    typeof raw.quote !== 'string' ||
    typeof raw.sectionTitle !== 'string' ||
    typeof raw.blockKind !== 'string' ||
    typeof raw.createdAt !== 'string' ||
    typeof raw.body !== 'string' ||
    !raw.body.trim()
  ) {
    return false
  }
  const kind = raw.kind ?? 'comment'
  if (typeof kind !== 'string' || !ALLOWED_DRAFT_KINDS.has(kind as NonNullable<DraftComment['kind']>)) {
    return false
  }
  if (kind === 'reply') return isValidThreadActionTarget(raw.replyTarget, false)
  if (kind === 'resolve') return isValidThreadActionTarget(raw.resolveTarget, true)
  return true
}

/**
 * Deserialize stored drafts from `localStorage`, filtering malformed records and migrating legacy `summaryBody` fields.
 * Sets `migrated` to true when legacy data was converted so callers can persist the upgraded structure.
 */
export function parseStoredDrafts(
  rawJson: string | null,
  prNumber: number,
): { drafts: DraftComment[]; migrated: boolean } {
  if (!rawJson) return { drafts: [], migrated: false }
  try {
    const rawParsed: unknown = JSON.parse(rawJson)
    if (!isRecord(rawParsed)) {
      return { drafts: [], migrated: false }
    }
    const validDrafts = Array.isArray(rawParsed.drafts) ? rawParsed.drafts.filter(isValidDraftComment) : []
    // Migrate legacy `summaryBody` field from early preview versions into a standard top-level comment draft.
    if (typeof rawParsed.summaryBody === 'string' && rawParsed.summaryBody.trim()) {
      validDrafts.push(createDraftComment(buildTopLevelTarget(prNumber), rawParsed.summaryBody.trim()))
      return { drafts: validDrafts, migrated: true }
    }
    return { drafts: validDrafts, migrated: false }
  } catch {
    return { drafts: [], migrated: false }
  }
}

/** Find a queued thread state toggle draft (`resolve` / `reopen`) for `threadId`, if any. */
export function findQueuedResolve(
  threadId: string,
  drafts: readonly DraftComment[],
): DraftComment | undefined {
  return drafts.find((d) => d.kind === 'resolve' && d.resolveTarget?.threadId === threadId)
}

/** Compute effective thread resolution state after applying any staged resolve/reopen draft. */
export function effectiveThreadResolved(
  thread: RemoteReviewThread,
  drafts: readonly DraftComment[],
): boolean {
  const queued = findQueuedResolve(thread.id, drafts)
  return queued?.resolveTarget ? queued.resolveTarget.resolved : thread.isResolved
}

/** Return the compact badge label summarizing a thread's remote + staged status. */
export function threadStatusLabel(
  thread: RemoteReviewThread,
  drafts: readonly DraftComment[],
  showOutdated = false,
): string {
  const queued = findQueuedResolve(thread.id, drafts)
  if (queued?.resolveTarget) {
    return queued.resolveTarget.resolved ? 'Pending Resolve' : 'Pending Reopen'
  }
  if (thread.isResolved) return 'Resolved'
  if (showOutdated && thread.isOutdated) return 'Outdated'
  return 'Open'
}

/** Position the text-selection action pill safely inside narrow and wide viewports. */
export function clampSelectionPopover(
  rect: { left: number; top: number; bottom: number; width: number },
  viewportWidth: number,
): { x: number; y: number } {
  const center = rect.left + rect.width / 2
  const maxX = Math.max(POPOVER_X_MARGIN_PX, viewportWidth - POPOVER_X_MARGIN_PX)
  const x = viewportWidth < POPOVER_X_MARGIN_PX * 2
    ? Math.max(0, Math.round(viewportWidth / 2))
    : Math.min(maxX, Math.max(POPOVER_X_MARGIN_PX, center))
  const y = rect.top > POPOVER_TOP_THRESHOLD_PX
    ? rect.top - POPOVER_ABOVE_OFFSET_PX
    : rect.bottom + POPOVER_BELOW_OFFSET_PX
  return { x, y }
}

/** Gate background `focus` / `visibilitychange` refreshes with a cooldown even after failed initial fetches. */
export function canAutoRefreshThreads(
  loading: boolean,
  threadsLoadedOnce: boolean,
  lastRefreshAt: number,
  nowMs: number,
  hasToken: boolean,
): boolean {
  if (loading) return false
  if (lastRefreshAt === 0 && !threadsLoadedOnce) return true
  const minCooldownMs = hasToken ? AUTH_REFRESH_COOLDOWN_MS : ANON_REFRESH_COOLDOWN_MS
  return nowMs - lastRefreshAt > minCooldownMs
}
