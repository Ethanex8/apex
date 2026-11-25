/**
 * Purpose: GitHub REST and GraphQL client for fetching PR review threads, verifying PATs, and submitting batched reviews.
 * Usage: Imported by `PrReviewOverlay.vue` and tested independently in `review.test.mts` with injected `FetchLike` stubs.
 * Invariants: All network entrypoints fail fast on invalid repo/PR slugs, pagination loops are bounded, and zero hidden DOM state is mutated.
 */

import type {
  DraftComment,
  DraftReplyTarget,
  DraftResolveTarget,
  PrReviewMeta,
  RemoteReviewThread,
  RemoteThreadComment,
  ReviewSubmitEvent,
  ReviewThreadSource,
  SubmitBatchResult,
  SubmitDraftOutcome,
} from './types.ts'

/** Fetch function signature accepted by all network entrypoints for deterministic test injection. */
export type FetchLike = typeof fetch

/** Permission-formatting context classifying which GitHub PAT scopes an API operation requires. */
export type GitHubErrorContext = 'read' | 'rest_write' | 'graphql_resolve'

const GITHUB_API = 'https://api.github.com'
const REST_PER_PAGE = 100
const MAX_REST_PAGES = 50
const GRAPHQL_PAGE_SIZE = 100
const MAX_GRAPHQL_PAGES = 50
const DEFAULT_AUTHOR_LOGIN = 'ghost'
const PR_SUMMARY_PATH = 'PR Summary'
const PR_CONVERSATION_PATH = 'PR Conversation'
const PREVIEW_BOT_MARKER = '<!-- apex-book-preview -->'
const PREVIEW_RESOLVED_MARKER = '<!-- apex-preview-resolved: 1 -->'
const PREVIEW_LOC_RE =
  /<!--\s*apex-preview-loc:\s*path=([^\s>]+?)(?:\s+line=(\d+)(?:-(\d+))?)?\s*-->/
const PREVIEW_RESOLVED_RE = /<!--\s*apex-preview-resolved:\s*1\s*-->/
const PREVIEW_REPLY_RE = /<!--\s*apex-preview-reply-to:\s*(\d+)\s*-->/
const PREVIEW_STATE_RE =
  /<!--\s*apex-preview-state:\s*root=(\d+)\s+resolved=(0|1)\s*-->/
const AGENT_ATTRIBUTION_RE =
  /^\s*(?:🤖\s*)?(?:\*\*\s*)?\[Antigravity\]\s*(?:\*\*)?(?:[:\-—]\s*|\s*\n+)?/i
const VALID_SLUG_SEGMENT_RE = /^[A-Za-z0-9_.-]+$/
const EDIT_FORBIDDEN_OR_MISSING_RE = /^(403|404)\b/

const REVIEW_THREADS_GQL = `
query($owner: String!, $name: String!, $pr: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $pr) {
      reviewThreads(first: ${GRAPHQL_PAGE_SIZE}, after: $after) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          id
          isResolved
          isOutdated
          path
          line
          startLine
          originalLine
          originalStartLine
          comments(first: ${GRAPHQL_PAGE_SIZE}) {
            pageInfo {
              hasNextPage
            }
            nodes {
              databaseId
              body
              createdAt
              url
              author {
                login
                avatarUrl
              }
            }
          }
        }
      }
    }
  }
}
`.trim()

const RESOLVE_THREAD_GQL = `
mutation($threadId: ID!) {
  resolveReviewThread(input: { threadId: $threadId }) {
    thread { id isResolved }
  }
}
`.trim()

const UNRESOLVE_THREAD_GQL = `
mutation($threadId: ID!) {
  unresolveReviewThread(input: { threadId: $threadId }) {
    thread { id isResolved }
  }
}
`.trim()

/** Format the hidden HTML marker pinning a fallback comment to a repo file and line range. */
function buildPreviewLocMarker(path: string, lineSpec: string): string {
  return `<!-- apex-preview-loc: path=${path} line=${lineSpec} -->`
}

/** Format the hidden HTML marker linking a conversation reply back to its parent root comment ID. */
function buildPreviewReplyMarker(rootCommentId: number): string {
  return `<!-- apex-preview-reply-to: ${rootCommentId} -->`
}

/** Format the hidden HTML state-override marker recording resolve/reopen actions on unowned threads. */
function buildPreviewStateMarker(rootCommentId: number, resolved: boolean): string {
  return `<!-- apex-preview-state: root=${rootCommentId} resolved=${resolved ? 1 : 0} -->`
}

/** Prefix every line of a multi-line excerpt so Markdown blockquotes never break onto plain text lines. */
function formatMarkdownBlockquote(text: string, prefix = '> '): string {
  return text
    .split(/\r?\n/)
    .map((line) => `${prefix}${line}`)
    .join('\n')
}

/**
 * Parse and strip hidden `apex-preview-*` HTML location, reply-target, and resolved markers
 * from a GitHub comment or review body.
 */
export function parsePreviewLocationMarker(body: string): {
  path: string | null
  startLine: number | null
  line: number | null
  isResolved: boolean
  replyToId: number | null
  cleanedBody: string
} {
  const locMatch = PREVIEW_LOC_RE.exec(body)
  const replyMatch = PREVIEW_REPLY_RE.exec(body)
  const isResolved = PREVIEW_RESOLVED_RE.test(body)
  const rangeStart = locMatch?.[2] ? Number.parseInt(locMatch[2], 10) : null
  const rangeEnd = locMatch?.[3] ? Number.parseInt(locMatch[3], 10) : null
  // Single-line markers (`line=N`) encode `startLine=null, line=N`; ranges (`line=A-B`) populate both endpoints.
  const startLine = rangeEnd !== null ? rangeStart : null
  const line = rangeEnd ?? rangeStart
  const replyToId = replyMatch?.[1] ? Number.parseInt(replyMatch[1], 10) : null
  const cleanedBody = body
    .replace(new RegExp(PREVIEW_LOC_RE.source, 'g'), '')
    .replace(new RegExp(PREVIEW_RESOLVED_RE.source, 'g'), '')
    .replace(new RegExp(PREVIEW_REPLY_RE.source, 'g'), '')
    .trim()
  return {
    path: locMatch?.[1] ?? null,
    startLine,
    line,
    isResolved,
    replyToId,
    cleanedBody,
  }
}

/** Detect and strip a leading Antigravity agent attribution marker so preview cards distinguish agent replies. */
export function parseAgentAttribution(body: string): {
  isAgent: boolean
  cleanedBody: string
} {
  const match = AGENT_ATTRIBUTION_RE.exec(body)
  if (!match) {
    return { isAgent: false, cleanedBody: body }
  }
  const stripped = body.slice(match[0].length).trim()
  return {
    isAgent: true,
    cleanedBody: stripped || body,
  }
}

/** Build a fallback comment body quoting the target passage and embedding a parseable location marker. */
export function formatPreviewLocationBody(
  body: string,
  path: string,
  startLine: number,
  endLine: number,
  quote?: string,
  sectionTitle?: string,
): string {
  const trimmedPath = path.trim()
  if (!trimmedPath || /[\s>]/.test(trimmedPath)) {
    throw new Error(`Invalid preview location path "${path}".`)
  }
  if (
    !Number.isInteger(startLine) ||
    startLine < 1 ||
    !Number.isInteger(endLine) ||
    endLine < startLine
  ) {
    throw new Error(
      `Invalid preview location line range ${String(startLine)}-${String(endLine)} for "${trimmedPath}".`,
    )
  }
  const trimmed = body.trim()
  const rangeLabel = endLine > startLine ? `${startLine}-${endLine}` : `${startLine}`
  const marker = buildPreviewLocMarker(trimmedPath, rangeLabel)
  if (!quote) {
    return `${trimmed}\n\n${marker}`
  }
  const ctx = sectionTitle ? ` (${sectionTitle})` : ''
  return `> **\`${trimmedPath}:${rangeLabel}\`**${ctx}\n${formatMarkdownBlockquote(quote)}\n\n${trimmed}\n\n${marker}`
}

/** Strip any prior resolved markers and append `PREVIEW_RESOLVED_MARKER` iff `resolved` is true. */
function toggleResolvedMarker(rawBody: string, resolved: boolean): string {
  const stripped = rawBody
    .replace(new RegExp(PREVIEW_RESOLVED_RE.source, 'g'), '')
    .trimEnd()
  return resolved ? `${stripped}\n\n${PREVIEW_RESOLVED_MARKER}` : stripped
}

/** Expand opaque GitHub Fine-Grained PAT permission errors into actionable scope instructions. */
export function formatGitHubPermissionError(
  message: string,
  context: GitHubErrorContext,
): string {
  if (!/resource not accessible by personal access token/i.test(message)) {
    return message
  }
  if (context === 'graphql_resolve') {
    return (
      'Resource not accessible by personal access token. ' +
      'GitHub requires a Fine-Grained PAT with BOTH "Pull requests: Read and write" ' +
      'and "Contents: Read and write" to resolve or reopen inline threads via GraphQL. ' +
      'Open Settings to update your token.'
    )
  }
  return (
    'Resource not accessible by personal access token. ' +
    'Verify in Settings that your Fine-Grained PAT targets this repo with ' +
    '"Pull requests: Read and write", "Contents: Read and write", and "Issues: Read and write".'
  )
}

/** Validate a single owner or repository name slug segment without permitting traversal tokens. */
function isValidSlugSegment(segment: string): boolean {
  return segment !== '.' && segment !== '..' && VALID_SLUG_SEGMENT_RE.test(segment)
}

/** Validate and split a `"owner/repo"` slug without permitting empty, traversal, or query-bearing segments. */
function splitRepoSlug(repo: string): [string, string] {
  const parts = repo.trim().split('/')
  if (
    parts.length !== 2 ||
    !isValidSlugSegment(parts[0]) ||
    !isValidSlugSegment(parts[1])
  ) {
    throw new Error(`Invalid repository slug "${repo}" (expected "owner/repo").`)
  }
  return [parts[0], parts[1]]
}

/** Fail fast on invalid repository slugs or non-positive PR numbers before issuing requests. */
function requireValidRepoAndPr(repo: string, prNumber: number): [string, string] {
  if (!Number.isInteger(prNumber) || prNumber <= 0) {
    throw new Error(`Invalid pull request number: ${String(prNumber)}`)
  }
  return splitRepoSlug(repo)
}

/** Validate a positive integer comment database ID before targeting REST comment endpoints. */
function requirePositiveCommentId(rootCommentId: number): number {
  if (!Number.isInteger(rootCommentId) || rootCommentId <= 0) {
    throw new Error(`Invalid comment root ID: ${String(rootCommentId)}.`)
  }
  return rootCommentId
}

/** Normalize raw comment body metadata (`apex-preview-*` + agent attribution) into a `RemoteThreadComment`. */
function buildThreadComment(params: {
  id: number
  authorLogin?: string | null
  avatarUrl?: string | null
  cleanedBody: string
  createdAt?: string | null
  url?: string | null
}): RemoteThreadComment {
  const agentAttr = parseAgentAttribution(params.cleanedBody)
  return {
    id: params.id,
    author: params.authorLogin ?? DEFAULT_AUTHOR_LOGIN,
    avatarUrl: params.avatarUrl ?? '',
    isAgent: agentAttr.isAgent,
    body: agentAttr.cleanedBody,
    createdAt: params.createdAt ?? '',
    url: params.url ?? '',
  }
}

/** Execute a GitHub REST or GraphQL request, enforcing JSON validity and structured permission diagnostics. */
async function apiRequest<T>(
  url: string,
  init: RequestInit,
  token: string,
  fetcher: FetchLike,
  errorContext?: GitHubErrorContext,
): Promise<T> {
  const cleanedToken = token.trim()
  const extraHeaders: Record<string, string> =
    init.headers instanceof Headers || Array.isArray(init.headers)
      ? Object.fromEntries(new Headers(init.headers).entries())
      : { ...(init.headers as Record<string, string> | undefined) }
  const headers: Record<string, string> = {
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    ...extraHeaders,
  }
  if (cleanedToken) {
    headers.Authorization = `Bearer ${cleanedToken}`
  }
  if (init.body && !headers['Content-Type'] && !headers['content-type']) {
    headers['Content-Type'] = 'application/json'
  }
  const resp = await fetcher(url, { ...init, headers })
  const text = await resp.text()
  let parsed: unknown = {}
  if (text) {
    try {
      parsed = JSON.parse(text)
    } catch (err) {
      if (resp.ok) {
        throw new Error(
          `Invalid JSON response from GitHub (${resp.status}): ${err instanceof Error ? err.message : String(err)}`,
        )
      }
      // Non-2xx proxy/gateway HTML errors lack JSON; fall back so the HTTP status message still surfaces.
      parsed = {}
    }
    if (resp.ok && (parsed === null || typeof parsed !== 'object')) {
      throw new Error(`Invalid JSON response from GitHub (${resp.status}): expected JSON object or array.`)
    }
  }
  if (!resp.ok) {
    const rawMsg =
      parsed !== null && typeof parsed === 'object' && typeof (parsed as Record<string, unknown>).message === 'string'
        ? ((parsed as Record<string, unknown>).message as string)
        : `GitHub API error (${resp.status})`
    const resolvedCtx: GitHubErrorContext =
      errorContext ?? (init.method && init.method.toUpperCase() !== 'GET' ? 'rest_write' : 'read')
    throw new Error(`${resp.status}: ${formatGitHubPermissionError(rawMsg, resolvedCtx)}`)
  }
  return parsed as T
}

/** Fetch all pages of a GitHub REST list endpoint with strict `per_page` and page-cap guards. */
export async function fetchPaginatedRest<T>(
  baseUrl: string,
  token: string,
  fetcher: FetchLike = fetch,
): Promise<T[]> {
  if (/[?&]page=/.test(baseUrl)) {
    throw new Error(`Paginated REST URL must not specify page= directly: ${baseUrl}`)
  }
  const rawMatch = /[?&]per_page=([^&]*)/.exec(baseUrl)
  const normalizedUrl = rawMatch
    ? baseUrl
    : `${baseUrl}${baseUrl.includes('?') ? '&' : '?'}per_page=${REST_PER_PAGE}`
  const pageLimit = rawMatch
    ? (/^\d+$/.test(rawMatch[1]) ? Number.parseInt(rawMatch[1], 10) : Number.NaN)
    : REST_PER_PAGE
  if (!Number.isInteger(pageLimit) || pageLimit <= 0 || pageLimit > REST_PER_PAGE) {
    throw new Error(`Invalid per_page limit in REST URL (expected 1..${REST_PER_PAGE}): ${baseUrl}`)
  }
  const results: T[] = []
  const sep = normalizedUrl.includes('?') ? '&' : '?'
  for (let page = 1; page <= MAX_REST_PAGES; page += 1) {
    const pagedUrl = page === 1 ? normalizedUrl : `${normalizedUrl}${sep}page=${page}`
    const chunk = await apiRequest<T[]>(pagedUrl, { method: 'GET' }, token, fetcher)
    if (!Array.isArray(chunk)) {
      throw new Error(`Unexpected non-array REST response from ${baseUrl}`)
    }
    results.push(...chunk)
    if (chunk.length < pageLimit) {
      return results
    }
  }
  throw new Error(`Exceeded maximum pagination limit (${MAX_REST_PAGES} pages) fetching ${baseUrl}.`)
}

/** Verify a Personal Access Token against `/user` and return the authenticated account identity. */
export async function verifyGitHubToken(
  token: string,
  fetcher: FetchLike = fetch,
): Promise<{ login: string; avatarUrl: string }> {
  const cleaned = token.trim()
  if (!cleaned) {
    throw new Error('Personal access token cannot be empty.')
  }
  const user = await apiRequest<{ login?: string; avatar_url?: string }>(
    `${GITHUB_API}/user`,
    { method: 'GET' },
    cleaned,
    fetcher,
  )
  const login = typeof user.login === 'string' ? user.login.trim() : ''
  if (!login) {
    throw new Error('GitHub user response omitted authenticated login.')
  }
  return {
    login,
    avatarUrl: user.avatar_url ?? '',
  }
}

/** Fetch live head commit SHA and open/closed state for a pull request without stale CDN caching. */
export async function fetchPrHeadInfo(
  repo: string,
  prNumber: number,
  token = '',
  fetcher: FetchLike = fetch,
): Promise<{ headSha: string; state: string }> {
  const [owner, name] = requireValidRepoAndPr(repo, prNumber)
  // Cache-bust PR polling so quick pushes or closes immediately invalidate browser/CDN caches.
  const pr = await apiRequest<{ head?: { sha?: string }; state?: string }>(
    `${GITHUB_API}/repos/${owner}/${name}/pulls/${prNumber}?_t=${Date.now()}`,
    { method: 'GET' },
    token,
    fetcher,
  )
  const headSha = typeof pr.head?.sha === 'string' ? pr.head.sha.trim() : ''
  const state = typeof pr.state === 'string' ? pr.state.trim() : ''
  if (!headSha || !state) {
    throw new Error(`GitHub PR #${prNumber} response omitted head SHA or state.`)
  }
  return { headSha, state }
}

/** GraphQL pull request review thread node shape returned by `REVIEW_THREADS_GQL`. */
interface GqlThreadNode {
  id: string
  isResolved: boolean
  isOutdated: boolean
  path: string
  line: number | null
  startLine: number | null
  originalLine: number | null
  originalStartLine?: number | null
  comments?: {
    pageInfo?: { hasNextPage?: boolean }
    nodes?: Array<{
      databaseId?: number | null
      body?: string
      createdAt?: string
      url?: string
      author?: { login?: string; avatarUrl?: string } | null
    }>
  }
}

/** Convert a single GraphQL `reviewThreads` node into a unified `RemoteReviewThread`. */
function normalizeGraphQlThreadNode(node: GqlThreadNode): RemoteReviewThread | null {
  if (node.comments?.pageInfo?.hasNextPage) {
    throw new Error(
      `GraphQL thread ${node.id} exceeds ${GRAPHQL_PAGE_SIZE} comments; cannot load truncated thread safely.`,
    )
  }
  const rawComments = node.comments?.nodes ?? []
  if (rawComments.length === 0) return null
  const gqlLine = node.line ?? null
  const gqlOrigLine = node.originalLine ?? null
  const parsedRoot = parsePreviewLocationMarker(rawComments[0].body ?? '')
  const effectiveLine = gqlLine ?? gqlOrigLine ?? parsedRoot.line
  const comments: RemoteThreadComment[] = rawComments.map((c, idx) => {
    if (typeof c.databaseId !== 'number' || !Number.isInteger(c.databaseId) || c.databaseId <= 0) {
      throw new Error(`GraphQL thread ${node.id} contained comment missing valid databaseId.`)
    }
    const cleaned =
      idx === 0
        ? parsedRoot.cleanedBody
        : parsePreviewLocationMarker(c.body ?? '').cleanedBody
    return buildThreadComment({
      id: c.databaseId,
      authorLogin: c.author?.login,
      avatarUrl: c.author?.avatarUrl,
      cleanedBody: cleaned,
      createdAt: c.createdAt,
      url: c.url,
    })
  })
  // GitHub GraphQL sets both `line` and `originalLine` to null for file-level (`subject_type: 'file'`) threads.
  const source: ReviewThreadSource = gqlLine === null && gqlOrigLine === null ? 'file' : 'inline'
  return {
    id: node.id,
    rootCommentId: comments[0].id,
    path: node.path || parsedRoot.path || '',
    line: effectiveLine,
    startLine: node.startLine ?? node.originalStartLine ?? parsedRoot.startLine,
    isResolved: Boolean(node.isResolved),
    isOutdated: Boolean(node.isOutdated),
    canResolve: true,
    source,
    url: comments[0].url,
    comments,
  }
}

/** Paginate all GraphQL review threads for an authenticated viewer, enforcing cursor progress and page bounds. */
async function fetchGraphQlThreads(
  repo: string,
  prNumber: number,
  token: string,
  fetcher: FetchLike,
): Promise<RemoteReviewThread[]> {
  const [owner, name] = requireValidRepoAndPr(repo, prNumber)
  const threads: RemoteReviewThread[] = []
  let cursor: string | null = null

  for (let page = 0; page < MAX_GRAPHQL_PAGES; page += 1) {
    const payload = await apiRequest<{
      data?: {
        repository?: {
          pullRequest?: {
            reviewThreads?: {
              pageInfo?: { hasNextPage?: boolean; endCursor?: string | null }
              nodes?: GqlThreadNode[]
            }
          }
        }
      }
      errors?: Array<{ message?: string }>
    }>(
      `${GITHUB_API}/graphql`,
      {
        method: 'POST',
        body: JSON.stringify({
          query: REVIEW_THREADS_GQL,
          variables: { owner, name, pr: prNumber, after: cursor },
        }),
      },
      token,
      fetcher,
      'read',
    )
    if (payload.errors?.length) {
      const combined = payload.errors.map((e) => e.message ?? '').join('; ')
      throw new Error(formatGitHubPermissionError(combined, 'read'))
    }
    const conn = payload.data?.repository?.pullRequest?.reviewThreads
    if (!conn) {
      throw new Error(`GitHub GraphQL response missing pullRequest/reviewThreads for ${owner}/${name}#${prNumber}.`)
    }
    for (const node of conn.nodes ?? []) {
      const normalized = normalizeGraphQlThreadNode(node)
      if (normalized) threads.push(normalized)
    }
    if (!conn.pageInfo?.hasNextPage) return threads
    const nextCursor = conn.pageInfo.endCursor ?? null
    if (!nextCursor) {
      throw new Error('GraphQL reviewThreads pagination returned hasNextPage=true with empty endCursor.')
    }
    if (nextCursor === cursor) {
      throw new Error(`GraphQL reviewThreads pagination stalled on repeated endCursor "${cursor}".`)
    }
    cursor = nextCursor
  }

  throw new Error(`Exceeded maximum GraphQL pagination limit (${MAX_GRAPHQL_PAGES} pages) for ${owner}/${name}#${prNumber}.`)
}

/** GitHub REST pull request review comment shape. */
interface RestPullComment {
  id: number
  in_reply_to_id?: number | null
  path?: string
  line?: number | null
  start_line?: number | null
  original_line?: number | null
  original_start_line?: number | null
  body?: string
  created_at?: string
  html_url?: string
  user?: { login?: string; avatar_url?: string } | null
}

/** Fetch pull request inline and file-level threads via anonymous REST fallback when unauthenticated. */
async function fetchRestPullThreads(
  repo: string,
  prNumber: number,
  fetcher: FetchLike,
): Promise<RemoteReviewThread[]> {
  const [owner, name] = requireValidRepoAndPr(repo, prNumber)
  // Cache-bust REST pull-comment reads so recently pushed/resolved comments appear immediately.
  const raw = await fetchPaginatedRest<RestPullComment>(
    `${GITHUB_API}/repos/${owner}/${name}/pulls/${prNumber}/comments?per_page=${REST_PER_PAGE}&_t=${Date.now()}`,
    '',
    fetcher,
  )
  const buckets = new Map<number, RestPullComment[]>()
  for (const item of raw) {
    const rootId = item.in_reply_to_id ?? item.id
    const list = buckets.get(rootId) ?? []
    list.push(item)
    buckets.set(rootId, list)
  }

  const threads: RemoteReviewThread[] = []
  for (const [rootId, items] of buckets.entries()) {
    items.sort((a, b) => a.id - b.id)
    const root = items[0]
    const rootLine = root.line ?? null
    const rootOrigLine = root.original_line ?? null
    const parsedRoot = parsePreviewLocationMarker(root.body ?? '')
    const effectiveLine = rootLine ?? rootOrigLine ?? parsedRoot.line
    // GitHub clears `line` when a diff hunk moves while keeping `original_line`; both null marks file-level comments.
    const isOutdated = rootLine === null && rootOrigLine !== null
    const source: ReviewThreadSource = rootLine === null && rootOrigLine === null ? 'file' : 'inline'
    threads.push({
      id: `rest:${rootId}`,
      rootCommentId: rootId,
      path: root.path || parsedRoot.path || '',
      line: effectiveLine,
      startLine: root.start_line ?? root.original_start_line ?? parsedRoot.startLine,
      isResolved: false,
      isOutdated,
      canResolve: false,
      source,
      url: root.html_url ?? '',
      comments: items.map((c, idx) =>
        buildThreadComment({
          id: c.id,
          authorLogin: c.user?.login,
          avatarUrl: c.user?.avatar_url,
          cleanedBody:
            idx === 0
              ? parsedRoot.cleanedBody
              : parsePreviewLocationMarker(c.body ?? '').cleanedBody,
          createdAt: c.created_at,
          url: c.html_url,
        }),
      ),
    })
  }
  return threads
}

/** GitHub REST issue-conversation comment shape. */
interface RestIssueComment {
  id: number
  body?: string
  created_at?: string
  updated_at?: string
  html_url?: string
  user?: { login?: string; avatar_url?: string; type?: string } | null
}

/** GitHub REST pull-request review summary shape. */
interface RestPrReview {
  id: number
  state?: string
  body?: string
  submitted_at?: string
  html_url?: string
  user?: { login?: string; avatar_url?: string; type?: string } | null
}

/** Latest parsed `apex-preview-state` override associated with a thread root comment ID. */
interface PreviewStateOverride {
  resolved: boolean
  timestampMs: number
}

/** Parse an ISO timestamp string to epoch milliseconds, returning `0` when absent or invalid. */
function parseTimestampMs(raw?: string): number {
  if (!raw) return 0
  const ms = Date.parse(raw)
  return Number.isFinite(ms) ? ms : 0
}

/** Collect the newest `apex-preview-state` resolution override comment per root comment ID. */
function collectPreviewStateOverrides(
  issueComments: RestIssueComment[],
): Map<number, PreviewStateOverride> {
  const stateMap = new Map<number, PreviewStateOverride>()
  for (const item of issueComments) {
    const m = PREVIEW_STATE_RE.exec(item.body ?? '')
    if (m) {
      const rootId = Number.parseInt(m[1], 10)
      const ts = parseTimestampMs(item.updated_at ?? item.created_at)
      const prev = stateMap.get(rootId)
      if (!prev || ts >= prev.timestampMs) {
        stateMap.set(rootId, { resolved: m[2] === '1', timestampMs: ts })
      }
    }
  }
  return stateMap
}

/** Resolve effective thread status: newer or equal-timestamp override markers take precedence over root edits. */
function resolveThreadState(
  override: PreviewStateOverride | undefined,
  rootUpdatedAt: string | undefined,
  bodyResolved: boolean,
): boolean {
  if (!override) return bodyResolved
  const rootMs = parseTimestampMs(rootUpdatedAt)
  return override.timestampMs >= rootMs ? override.resolved : bodyResolved
}

/** Build top-level PR review summary threads from non-pending, human-authored PR reviews. */
function buildReviewSummaryThreads(
  rawReviews: RestPrReview[],
  stateOverrides: Map<number, PreviewStateOverride>,
  canResolve: boolean,
): Map<number, RemoteReviewThread> {
  const reviewThreads = new Map<number, RemoteReviewThread>()
  for (const rev of rawReviews) {
    const rawBody = rev.body ?? ''
    if (!rawBody.trim() || rev.state?.toUpperCase() === 'PENDING') continue
    if (rev.user?.type?.toLowerCase() === 'bot') continue
    const parsed = parsePreviewLocationMarker(rawBody)
    if (!parsed.cleanedBody) continue
    const override = stateOverrides.get(rev.id)
    reviewThreads.set(rev.id, {
      id: `review:${rev.id}`,
      rootCommentId: rev.id,
      path: PR_SUMMARY_PATH,
      line: null,
      startLine: null,
      isResolved: resolveThreadState(override, rev.submitted_at, parsed.isResolved),
      isOutdated: false,
      canResolve,
      hasStateOverride: Boolean(override),
      source: 'review',
      url: rev.html_url ?? '',
      rawRootBody: rawBody,
      comments: [
        buildThreadComment({
          id: rev.id,
          authorLogin: rev.user?.login,
          avatarUrl: rev.user?.avatar_url,
          cleanedBody: parsed.cleanedBody,
          createdAt: rev.submitted_at,
          url: rev.html_url,
        }),
      ],
    })
  }
  return reviewThreads
}

/** Partition issue comments into root conversation threads and reply buckets keyed by `replyToId`. */
function collectIssueAndReplyThreads(
  rawIssues: RestIssueComment[],
  stateOverrides: Map<number, PreviewStateOverride>,
  canResolve: boolean,
): {
  issueThreads: Map<number, RemoteReviewThread>
  repliesByRootId: Map<number, RemoteReviewThread[]>
} {
  const issueThreads = new Map<number, RemoteReviewThread>()
  const repliesByRootId = new Map<number, RemoteReviewThread[]>()
  for (const item of rawIssues) {
    const rawBody = item.body ?? ''
    if (!rawBody || rawBody.includes(PREVIEW_BOT_MARKER)) continue
    if (PREVIEW_STATE_RE.test(rawBody)) continue
    if (item.user?.type?.toLowerCase() === 'bot') continue
    const parsed = parsePreviewLocationMarker(rawBody)
    if (!parsed.cleanedBody) continue
    const override = stateOverrides.get(item.id)
    const threadEntry: RemoteReviewThread = {
      id: `issue:${item.id}`,
      rootCommentId: item.id,
      path: parsed.path ?? PR_CONVERSATION_PATH,
      line: parsed.line,
      startLine: parsed.startLine,
      isResolved: resolveThreadState(override, item.updated_at ?? item.created_at, parsed.isResolved),
      isOutdated: false,
      canResolve,
      hasStateOverride: Boolean(override),
      source: 'issue',
      url: item.html_url ?? '',
      rawRootBody: rawBody,
      comments: [
        buildThreadComment({
          id: item.id,
          authorLogin: item.user?.login,
          avatarUrl: item.user?.avatar_url,
          cleanedBody: parsed.cleanedBody,
          createdAt: item.created_at,
          url: item.html_url,
        }),
      ],
    }
    if (parsed.replyToId) {
      const bucket = repliesByRootId.get(parsed.replyToId) ?? []
      bucket.push(threadEntry)
      repliesByRootId.set(parsed.replyToId, bucket)
    } else {
      issueThreads.set(item.id, threadEntry)
    }
  }
  return { issueThreads, repliesByRootId }
}

/** Attach collected conversation replies to matching issue/review parents, promoting orphan replies to roots. */
function mergeConversationReplies(
  repliesByRootId: Map<number, RemoteReviewThread[]>,
  reviewThreads: Map<number, RemoteReviewThread>,
  issueThreads: Map<number, RemoteReviewThread>,
): RemoteReviewThread[] {
  for (const [rootId, replies] of repliesByRootId.entries()) {
    const parent = issueThreads.get(rootId) ?? reviewThreads.get(rootId)
    if (parent) {
      parent.comments.push(...replies.flatMap((r) => r.comments))
    } else {
      // Promote orphan replies (e.g., deleted root or cross-channel link) instead of silently dropping them.
      for (const orphan of replies) {
        issueThreads.set(orphan.rootCommentId, orphan)
      }
    }
  }
  return [...reviewThreads.values(), ...issueThreads.values()]
}

/** Fetch PR issue comments and review summaries, folding state overrides and cross-channel replies cleanly. */
async function fetchConversationAndReviewThreads(
  repo: string,
  prNumber: number,
  token: string,
  fetcher: FetchLike,
): Promise<RemoteReviewThread[]> {
  const [owner, name] = requireValidRepoAndPr(repo, prNumber)
  // Cache-bust REST reads so fresh replies and state-override comments reflect immediately after submission.
  const bust = Date.now()
  const [rawIssues, rawReviews] = await Promise.all([
    fetchPaginatedRest<RestIssueComment>(
      `${GITHUB_API}/repos/${owner}/${name}/issues/${prNumber}/comments?per_page=${REST_PER_PAGE}&_t=${bust}`,
      token,
      fetcher,
    ),
    fetchPaginatedRest<RestPrReview>(
      `${GITHUB_API}/repos/${owner}/${name}/pulls/${prNumber}/reviews?per_page=${REST_PER_PAGE}&_t=${bust}`,
      token,
      fetcher,
    ),
  ])

  const stateOverrides = collectPreviewStateOverrides(rawIssues)
  const canResolve = Boolean(token)
  const reviewThreads = buildReviewSummaryThreads(rawReviews, stateOverrides, canResolve)
  const { issueThreads, repliesByRootId } = collectIssueAndReplyThreads(
    rawIssues,
    stateOverrides,
    canResolve,
  )
  return mergeConversationReplies(repliesByRootId, reviewThreads, issueThreads)
}

/**
 * Fetches inline, file-level, location-tagged issue, and PR review summary threads.
 */
export async function fetchPrThreads(
  repo: string,
  prNumber: number,
  token: string,
  fetcher: FetchLike = fetch,
): Promise<RemoteReviewThread[]> {
  const [reviewThreads, convThreads] = await Promise.all([
    token
      ? fetchGraphQlThreads(repo, prNumber, token, fetcher)
      : fetchRestPullThreads(repo, prNumber, fetcher),
    fetchConversationAndReviewThreads(repo, prNumber, token, fetcher),
  ])
  return [...reviewThreads, ...convThreads]
}

/** Typed buckets produced by validating and partitioning queued review drafts before submission. */
interface PartitionedReviewDrafts {
  outcomes: SubmitDraftOutcome[]
  inlineDrafts: DraftComment[]
  fileDrafts: DraftComment[]
  issueDrafts: DraftComment[]
  replyDrafts: Array<{ draft: DraftComment; target: DraftReplyTarget }>
  resolveDrafts: Array<{ draft: DraftComment; target: DraftResolveTarget }>
}

/** Validate draft preconditions per channel and partition queued drafts without aborting valid siblings. */
function partitionReviewDrafts(drafts: DraftComment[]): PartitionedReviewDrafts {
  const outcomes: SubmitDraftOutcome[] = []
  const inlineDrafts: DraftComment[] = []
  const fileDrafts: DraftComment[] = []
  const issueDrafts: DraftComment[] = []
  const replyDrafts: Array<{ draft: DraftComment; target: DraftReplyTarget }> = []
  const resolveDrafts: Array<{ draft: DraftComment; target: DraftResolveTarget }> = []
  for (const d of drafts) {
    if (d.kind === 'resolve') {
      const target = (d as { resolveTarget?: DraftResolveTarget }).resolveTarget
      if (target) resolveDrafts.push({ draft: d, target })
      else outcomes.push({ draftId: d.id, ok: false, error: 'Resolve draft missing target metadata.' })
      continue
    }
    if (typeof d.body !== 'string' || !d.body.trim()) {
      outcomes.push({ draftId: d.id, ok: false, error: 'Comment body cannot be empty.' })
      continue
    }
    if (d.kind === 'reply') {
      const target = (d as { replyTarget?: DraftReplyTarget }).replyTarget
      if (target) replyDrafts.push({ draft: d, target })
      else outcomes.push({ draftId: d.id, ok: false, error: 'Reply draft missing target metadata.' })
    } else if (d.mode === 'inline') {
      if (!d.path?.trim() || !Number.isInteger(d.apiLine) || d.apiLine < 1) {
        outcomes.push({ draftId: d.id, ok: false, error: 'Inline draft requires a valid file path and positive line.' })
      } else {
        inlineDrafts.push(d)
      }
    } else if (d.mode === 'file') {
      if (!d.path?.trim()) {
        outcomes.push({ draftId: d.id, ok: false, error: 'File draft requires a non-empty file path.' })
      } else {
        fileDrafts.push(d)
      }
    } else if (d.mode === 'issue') {
      issueDrafts.push(d)
    } else {
      outcomes.push({ draftId: d.id, ok: false, error: `Unsupported draft mode: ${String(d.mode)}` })
    }
  }
  return { outcomes, inlineDrafts, fileDrafts, issueDrafts, replyDrafts, resolveDrafts }
}

/** Format a thrown network or validation error consistently into a failed `SubmitDraftOutcome`. */
function toFailedOutcome(draftId: string, err: unknown): SubmitDraftOutcome {
  return {
    draftId,
    ok: false,
    error: err instanceof Error ? err.message : String(err),
  }
}

/** Execute a single queued draft network call and capture its per-draft outcome cleanly. */
async function executeDraftTask(
  draftId: string,
  work: () => Promise<void>,
): Promise<SubmitDraftOutcome> {
  try {
    await work()
    return { draftId, ok: true }
  } catch (err) {
    return toFailedOutcome(draftId, err)
  }
}

/** Format a queued file-level or issue-level draft body with optional pinned location markers. */
function buildFallbackDraftBody(draft: DraftComment): string {
  return draft.path
    ? formatPreviewLocationBody(
        draft.body,
        draft.path,
        draft.startLine,
        draft.endLine,
        draft.quote,
        draft.sectionTitle,
      )
    : draft.body.trim()
}

/** Submit all inline comments plus any PR summary review verdict in one atomic GitHub PR review request. */
async function submitInlineReviewBatch(
  repoSlug: string,
  meta: PrReviewMeta,
  inlineDrafts: DraftComment[],
  trimmedSummary: string,
  event: ReviewSubmitEvent,
  token: string,
  fetcher: FetchLike,
): Promise<{ outcomes: SubmitDraftOutcome[]; summaryOk: boolean; summaryError?: string }> {
  if (inlineDrafts.length === 0 && trimmedSummary.length === 0 && event === 'COMMENT') {
    return { outcomes: [], summaryOk: true }
  }
  const payload: Record<string, unknown> = {
    event,
    body: trimmedSummary,
  }
  if (inlineDrafts.length > 0) {
    payload.commit_id = meta.headSha
    payload.comments = inlineDrafts.map((d) => {
      const entry: Record<string, unknown> = {
        path: d.path,
        line: d.apiLine,
        side: 'RIGHT',
        body: d.body.trim(),
      }
      // GitHub rejects `start_line` equal to `line` or `<= 0`; only emit span fields for valid multi-line ranges.
      if (Number.isInteger(d.apiStartLine) && d.apiStartLine >= 1 && d.apiStartLine < d.apiLine) {
        entry.start_line = d.apiStartLine
        entry.start_side = 'RIGHT'
      }
      return entry
    })
  }
  try {
    await apiRequest(
      `${GITHUB_API}/repos/${repoSlug}/pulls/${meta.prNumber}/reviews`,
      { method: 'POST', body: JSON.stringify(payload) },
      token,
      fetcher,
    )
    return {
      outcomes: inlineDrafts.map((d) => ({ draftId: d.id, ok: true })),
      summaryOk: true,
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return {
      outcomes: inlineDrafts.map((d) => ({ draftId: d.id, ok: false, error: msg })),
      summaryOk: false,
      summaryError: msg,
    }
  }
}

/** Post queued file-level and conversation-fallback comment drafts sequentially, returning per-draft outcomes. */
async function submitFallbackCommentDrafts(
  repoSlug: string,
  meta: PrReviewMeta,
  fileDrafts: DraftComment[],
  issueDrafts: DraftComment[],
  token: string,
  fetcher: FetchLike,
): Promise<SubmitDraftOutcome[]> {
  const outcomes: SubmitDraftOutcome[] = []
  for (const d of fileDrafts) {
    outcomes.push(
      await executeDraftTask(d.id, async () => {
        await apiRequest(
          `${GITHUB_API}/repos/${repoSlug}/pulls/${meta.prNumber}/comments`,
          {
            method: 'POST',
            body: JSON.stringify({
              commit_id: meta.headSha,
              path: d.path,
              subject_type: 'file',
              body: buildFallbackDraftBody(d),
            }),
          },
          token,
          fetcher,
        )
      }),
    )
  }
  for (const d of issueDrafts) {
    outcomes.push(
      await executeDraftTask(d.id, async () => {
        await apiRequest(
          `${GITHUB_API}/repos/${repoSlug}/issues/${meta.prNumber}/comments`,
          { method: 'POST', body: JSON.stringify({ body: buildFallbackDraftBody(d) }) },
          token,
          fetcher,
        )
      }),
    )
  }
  return outcomes
}

/** Dispatch queued thread replies and resolve/reopen actions sequentially, returning per-draft outcomes. */
async function submitFollowUpDrafts(
  repoSlug: string,
  prNumber: number,
  replyDrafts: Array<{ draft: DraftComment; target: DraftReplyTarget }>,
  resolveDrafts: Array<{ draft: DraftComment; target: DraftResolveTarget }>,
  token: string,
  fetcher: FetchLike,
): Promise<SubmitDraftOutcome[]> {
  const outcomes: SubmitDraftOutcome[] = []
  for (const { draft, target } of replyDrafts) {
    const targetThread: RemoteReviewThread = {
      id: target.threadId,
      rootCommentId: target.rootCommentId,
      path: target.path,
      line: target.line,
      startLine: null,
      isResolved: false,
      isOutdated: false,
      canResolve: false,
      source: target.source,
      url: '',
      comments: [],
    }
    outcomes.push(
      await executeDraftTask(draft.id, () =>
        replyToThread(repoSlug, prNumber, targetThread, draft.body, token, fetcher),
      ),
    )
  }
  for (const { draft, target } of resolveDrafts) {
    // Seed pre-transition `isResolved` opposite to the requested state; `url`/`comments` are unused by `setThreadResolved`.
    const targetThread: RemoteReviewThread = {
      id: target.threadId,
      rootCommentId: target.rootCommentId,
      path: target.path,
      line: target.line,
      startLine: null,
      isResolved: !target.resolved,
      isOutdated: false,
      canResolve: true,
      hasStateOverride: target.hasStateOverride,
      source: target.source,
      url: '',
      rawRootBody: target.rawRootBody,
      comments: [],
    }
    outcomes.push(
      await executeDraftTask(draft.id, async () => {
        await setThreadResolved(repoSlug, prNumber, targetThread, target.resolved, token, fetcher)
      }),
    )
  }
  return outcomes
}

/**
 * Submits queued drafts as an atomic GitHub PR review (inline hunks) plus file-level
 * and issue-comment fallbacks, returning explicit per-draft and overall summary outcomes.
 */
export async function submitBatchedReview(
  meta: PrReviewMeta,
  drafts: DraftComment[],
  summaryBody: string,
  event: ReviewSubmitEvent = 'COMMENT',
  token: string,
  fetcher: FetchLike = fetch,
): Promise<SubmitBatchResult> {
  const [owner, name] = requireValidRepoAndPr(meta.repo, meta.prNumber)
  const repoSlug = `${owner}/${name}`
  const partitioned = partitionReviewDrafts(drafts)
  const inlineResult = await submitInlineReviewBatch(
    repoSlug,
    meta,
    partitioned.inlineDrafts,
    summaryBody.trim(),
    event,
    token,
    fetcher,
  )
  const fallbackOutcomes = await submitFallbackCommentDrafts(
    repoSlug,
    meta,
    partitioned.fileDrafts,
    partitioned.issueDrafts,
    token,
    fetcher,
  )
  const followUpOutcomes = await submitFollowUpDrafts(
    repoSlug,
    meta.prNumber,
    partitioned.replyDrafts,
    partitioned.resolveDrafts,
    token,
    fetcher,
  )
  return {
    outcomes: [
      ...partitioned.outcomes,
      ...inlineResult.outcomes,
      ...fallbackOutcomes,
      ...followUpOutcomes,
    ],
    summaryOk: inlineResult.summaryOk,
    summaryError: inlineResult.summaryError,
  }
}

/** Post a reply to an inline, file-level, issue-conversation, or PR-review-summary thread. */
export async function replyToThread(
  repo: string,
  prNumber: number,
  thread: RemoteReviewThread,
  body: string,
  token: string,
  fetcher: FetchLike = fetch,
): Promise<void> {
  const [owner, name] = requireValidRepoAndPr(repo, prNumber)
  const rootId = requirePositiveCommentId(thread.rootCommentId)
  const trimmed = body.trim()
  if (!trimmed) {
    throw new Error('Reply body cannot be empty.')
  }
  if (thread.source === 'inline' || thread.source === 'file') {
    await apiRequest(
      `${GITHUB_API}/repos/${owner}/${name}/pulls/${prNumber}/comments/${rootId}/replies`,
      { method: 'POST', body: JSON.stringify({ body: trimmed }) },
      token,
      fetcher,
    )
    return
  }

  const locMarker =
    thread.path && thread.line ? `\n${buildPreviewLocMarker(thread.path, String(thread.line))}` : ''
  await apiRequest(
    `${GITHUB_API}/repos/${owner}/${name}/issues/${prNumber}/comments`,
    {
      method: 'POST',
      body: JSON.stringify({
        body: `${trimmed}\n\n${buildPreviewReplyMarker(rootId)}${locMarker}`,
      }),
    },
    token,
    fetcher,
  )
}

/** Execute GraphQL `resolveReviewThread` or `unresolveReviewThread` and validate boolean confirmation. */
async function setGraphQlThreadResolved(
  threadId: string,
  resolved: boolean,
  token: string,
  fetcher: FetchLike,
): Promise<boolean> {
  const query = resolved ? RESOLVE_THREAD_GQL : UNRESOLVE_THREAD_GQL
  const payload = await apiRequest<{
    data?: {
      resolveReviewThread?: { thread?: { isResolved?: boolean } }
      unresolveReviewThread?: { thread?: { isResolved?: boolean } }
    }
    errors?: Array<{ message?: string }>
  }>(
    `${GITHUB_API}/graphql`,
    { method: 'POST', body: JSON.stringify({ query, variables: { threadId } }) },
    token,
    fetcher,
  )
  if (payload.errors?.length) {
    const combined = payload.errors.map((e) => e.message ?? '').join('; ')
    throw new Error(formatGitHubPermissionError(combined, 'graphql_resolve'))
  }
  const threadState = resolved
    ? payload.data?.resolveReviewThread?.thread?.isResolved
    : payload.data?.unresolveReviewThread?.thread?.isResolved
  if (typeof threadState !== 'boolean') {
    throw new Error('GitHub GraphQL response omitted updated thread resolution state.')
  }
  return threadState
}

/** Post a durable `apex-preview-state` fallback comment when direct root-body marker edits cannot resolve cleanly. */
async function postPreviewStateOverride(
  owner: string,
  name: string,
  prNumber: number,
  rootCommentId: number,
  resolved: boolean,
  token: string,
  fetcher: FetchLike,
): Promise<void> {
  await apiRequest(
    `${GITHUB_API}/repos/${owner}/${name}/issues/${prNumber}/comments`,
    {
      method: 'POST',
      body: JSON.stringify({ body: buildPreviewStateMarker(rootCommentId, resolved) }),
    },
    token,
    fetcher,
  )
}

/** Attempt an author-owned `PATCH` or `PUT` resolved-marker edit, returning `false` only on `403`/`404`. */
async function tryUpdateResolvedRootMarker(
  url: string,
  method: 'PATCH' | 'PUT',
  rawRootBody: string,
  resolved: boolean,
  token: string,
  fetcher: FetchLike,
): Promise<boolean> {
  try {
    await apiRequest(
      url,
      { method, body: JSON.stringify({ body: toggleResolvedMarker(rawRootBody, resolved) }) },
      token,
      fetcher,
    )
    return true
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    if (!EDIT_FORBIDDEN_OR_MISSING_RE.test(msg)) throw err
    return false
  }
}

/** Resolve or reopen a GraphQL, issue-conversation, or PR-review thread and return the new state. */
export async function setThreadResolved(
  repo: string,
  prNumber: number,
  thread: RemoteReviewThread,
  resolved: boolean,
  token: string,
  fetcher: FetchLike = fetch,
): Promise<boolean> {
  const [owner, name] = requireValidRepoAndPr(repo, prNumber)
  if (thread.source === 'inline' || thread.source === 'file') {
    if (!thread.id.trim()) {
      throw new Error('Thread ID cannot be empty for GraphQL thread resolution.')
    }
    return setGraphQlThreadResolved(thread.id, resolved, token, fetcher)
  }
  const rootId = requirePositiveCommentId(thread.rootCommentId)

  if (thread.source === 'issue' && thread.rawRootBody !== undefined) {
    const updated = await tryUpdateResolvedRootMarker(
      `${GITHUB_API}/repos/${owner}/${name}/issues/comments/${rootId}`,
      'PATCH',
      thread.rawRootBody,
      resolved,
      token,
      fetcher,
    )
    // Even after a successful root edit, emit a fresh state comment when an earlier override exists so timestamps supersede it.
    if (updated && !thread.hasStateOverride) return resolved
  }

  if (thread.source === 'review' && thread.rawRootBody !== undefined) {
    const updated = await tryUpdateResolvedRootMarker(
      `${GITHUB_API}/repos/${owner}/${name}/pulls/${prNumber}/reviews/${rootId}`,
      'PUT',
      thread.rawRootBody,
      resolved,
      token,
      fetcher,
    )
    // Review PUT responses lack an updated_at override check; supersede any prior state marker deterministically.
    if (updated && !thread.hasStateOverride) return resolved
  }

  await postPreviewStateOverride(owner, name, prNumber, rootId, resolved, token, fetcher)
  return resolved
}

/**
 * Formats queued drafts into a portable Markdown review checklist for zero-token fallback.
 */
export function formatMarkdownBundle(
  meta: PrReviewMeta,
  drafts: DraftComment[],
  summaryBody: string,
): string {
  const lines: string[] = [`## Inline Preview Review — PR #${meta.prNumber}`]
  if (summaryBody.trim()) {
    lines.push('', summaryBody.trim())
  }
  const byFile = new Map<string, DraftComment[]>()
  for (const d of drafts) {
    const bucket = byFile.get(d.path) ?? []
    bucket.push(d)
    byFile.set(d.path, bucket)
  }
  for (const [filePath, items] of byFile.entries()) {
    lines.push('', `### \`${filePath || `PR #${meta.prNumber}`}\``)
    for (const item of items) {
      if (item.kind === 'reply') {
        const target = (item as { replyTarget?: DraftReplyTarget }).replyTarget
        if (!target) throw new Error(`Reply draft "${item.id}" is missing replyTarget metadata.`)
        const loc = target.line ? `L${target.line}, ` : ''
        lines.push(`- **Reply to @${target.author}** (${loc}#${target.rootCommentId}): ${item.body.trim()}`)
        continue
      }
      if (item.kind === 'resolve') {
        const target = (item as { resolveTarget?: DraftResolveTarget }).resolveTarget
        if (!target) throw new Error(`Resolve draft "${item.id}" is missing resolveTarget metadata.`)
        const loc = target.line ? `L${target.line}, ` : ''
        const verb = target.resolved ? 'Resolve' : 'Reopen'
        lines.push(`- **${verb} thread** (${loc}#${target.rootCommentId})`)
        continue
      }
      if (!item.path) {
        lines.push(`- **Top-level PR comment**: ${item.body.trim()}`)
        continue
      }
      const span =
        item.endLine > item.startLine
          ? `L${item.startLine}-L${item.endLine}`
          : `L${item.startLine}`
      const ctx = item.sectionTitle ? ` — ${item.sectionTitle}` : ''
      lines.push(`- **${span}** (${item.blockKind}${ctx}): ${item.body.trim()}`)
      if (item.quote) {
        lines.push(formatMarkdownBlockquote(item.quote, '  > '))
      }
    }
  }
  return lines.join('\n')
}
