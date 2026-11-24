import type {
  DraftComment,
  PrReviewMeta,
  RemoteReviewThread,
  RemoteThreadComment,
  ReviewSubmitEvent,
  SubmitDraftOutcome,
} from './types.ts'

export type FetchLike = typeof fetch

const GITHUB_API = 'https://api.github.com'
const PREVIEW_BOT_MARKER = '<!-- apex-book-preview -->'
const PREVIEW_LOC_RE =
  /<!--\s*apex-preview-loc:\s*path=([^\s>]+?)(?:\s+line=(\d+)(?:-\d+)?)?\s*-->/

const REVIEW_THREADS_GQL = `
query($owner: String!, $name: String!, $pr: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $after) {
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
          comments(first: 100) {
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

export function parsePreviewLocationMarker(body: string): {
  path: string | null
  line: number | null
  cleanedBody: string
} {
  const m = PREVIEW_LOC_RE.exec(body)
  if (!m) {
    return { path: null, line: null, cleanedBody: body.trim() }
  }
  const line = m[2] ? Number.parseInt(m[2], 10) : null
  const cleanedBody = body.replace(PREVIEW_LOC_RE, '').trim()
  return { path: m[1], line, cleanedBody }
}

export function formatPreviewLocationBody(
  body: string,
  path: string,
  startLine: number,
  endLine: number,
  quote?: string,
  sectionTitle?: string,
): string {
  const trimmed = body.trim()
  const rangeLabel = endLine > startLine ? `${startLine}-${endLine}` : `${startLine}`
  const marker = `<!-- apex-preview-loc: path=${path} line=${rangeLabel} -->`
  if (!quote) {
    return `${trimmed}\n\n${marker}`
  }
  const ctx = sectionTitle ? ` (${sectionTitle})` : ''
  return `> **\`${path}:${rangeLabel}\`**${ctx}\n> ${quote}\n\n${trimmed}\n\n${marker}`
}

async function apiRequest<T>(
  url: string,
  init: RequestInit,
  token: string,
  fetcher: FetchLike,
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    ...(init.headers as Record<string, string> | undefined),
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  if (init.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  const resp = await fetcher(url, { ...init, headers })
  const text = await resp.text()
  const parsed = text ? (JSON.parse(text) as Record<string, unknown>) : {}
  if (!resp.ok) {
    const msg =
      typeof parsed?.message === 'string'
        ? parsed.message
        : `GitHub API error (${resp.status})`
    throw new Error(`${resp.status}: ${msg}`)
  }
  return parsed as T
}

export async function verifyGitHubToken(
  token: string,
  fetcher: FetchLike = fetch,
): Promise<{ login: string; avatarUrl: string }> {
  const user = await apiRequest<{ login: string; avatar_url?: string }>(
    `${GITHUB_API}/user`,
    { method: 'GET' },
    token.trim(),
    fetcher,
  )
  return {
    login: user.login,
    avatarUrl: user.avatar_url ?? '',
  }
}

interface GqlThreadNode {
  id: string
  isResolved: boolean
  isOutdated: boolean
  path: string
  line: number | null
  startLine: number | null
  originalLine: number | null
  comments?: {
    nodes?: Array<{
      databaseId?: number
      body?: string
      createdAt?: string
      url?: string
      author?: { login?: string; avatarUrl?: string } | null
    }>
  }
}

async function fetchGraphQlThreads(
  repo: string,
  prNumber: number,
  token: string,
  fetcher: FetchLike,
): Promise<RemoteReviewThread[]> {
  const [owner, name] = repo.split('/', 2)
  const threads: RemoteReviewThread[] = []
  let cursor: string | null = null

  while (true) {
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
    )
    if (payload.errors?.length) {
      throw new Error(payload.errors.map((e) => e.message).join('; '))
    }
    const conn = payload.data?.repository?.pullRequest?.reviewThreads
    for (const node of conn?.nodes ?? []) {
      const rawComments = node.comments?.nodes ?? []
      if (rawComments.length === 0) continue
      const parsedRoot = parsePreviewLocationMarker(rawComments[0].body ?? '')
      const effectiveLine = node.line ?? node.originalLine ?? parsedRoot.line
      const comments: RemoteThreadComment[] = rawComments.map((c, idx) => {
        const cleaned =
          idx === 0
            ? parsedRoot.cleanedBody
            : parsePreviewLocationMarker(c.body ?? '').cleanedBody
        return {
          id: c.databaseId ?? 0,
          author: c.author?.login ?? 'ghost',
          avatarUrl: c.author?.avatarUrl ?? '',
          body: cleaned,
          createdAt: c.createdAt ?? '',
          url: c.url ?? '',
        }
      })
      threads.push({
        id: node.id,
        rootCommentId: comments[0].id,
        path: node.path || parsedRoot.path || '',
        line: effectiveLine,
        startLine: node.startLine,
        isResolved: Boolean(node.isResolved),
        isOutdated: Boolean(node.isOutdated),
        canResolve: true,
        source: effectiveLine && node.line === null && node.originalLine === null ? 'file' : 'inline',
        url: comments[0].url,
        comments,
      })
    }
    if (!conn?.pageInfo?.hasNextPage) break
    cursor = conn.pageInfo.endCursor ?? null
    if (!cursor) break
  }

  return threads
}

interface RestPullComment {
  id: number
  in_reply_to_id?: number | null
  path?: string
  line?: number | null
  start_line?: number | null
  original_line?: number | null
  body?: string
  created_at?: string
  html_url?: string
  user?: { login?: string; avatar_url?: string } | null
}

async function fetchRestPullThreads(
  repo: string,
  prNumber: number,
  fetcher: FetchLike,
): Promise<RemoteReviewThread[]> {
  const raw = await apiRequest<RestPullComment[]>(
    `${GITHUB_API}/repos/${repo}/pulls/${prNumber}/comments?per_page=100`,
    { method: 'GET' },
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
    const parsedRoot = parsePreviewLocationMarker(root.body ?? '')
    const effectiveLine = root.line ?? root.original_line ?? parsedRoot.line
    threads.push({
      id: `rest:${rootId}`,
      rootCommentId: rootId,
      path: root.path || parsedRoot.path || '',
      line: effectiveLine,
      startLine: root.start_line ?? null,
      isResolved: false,
      isOutdated: root.line === null && root.original_line !== null,
      canResolve: false,
      source: effectiveLine && root.line === null && root.original_line === null ? 'file' : 'inline',
      url: root.html_url ?? '',
      comments: items.map((c, idx) => ({
        id: c.id,
        author: c.user?.login ?? 'ghost',
        avatarUrl: c.user?.avatar_url ?? '',
        body: idx === 0 ? parsedRoot.cleanedBody : (c.body ?? '').trim(),
        createdAt: c.created_at ?? '',
        url: c.html_url ?? '',
      })),
    })
  }
  return threads
}

interface RestIssueComment {
  id: number
  body?: string
  created_at?: string
  html_url?: string
  user?: { login?: string; avatar_url?: string; type?: string } | null
}

async function fetchIssueAnchoredThreads(
  repo: string,
  prNumber: number,
  token: string,
  fetcher: FetchLike,
): Promise<RemoteReviewThread[]> {
  const raw = await apiRequest<RestIssueComment[]>(
    `${GITHUB_API}/repos/${repo}/issues/${prNumber}/comments?per_page=100`,
    { method: 'GET' },
    token,
    fetcher,
  )
  const out: RemoteReviewThread[] = []
  for (const item of raw) {
    const body = item.body ?? ''
    if (!body || body.includes(PREVIEW_BOT_MARKER)) continue
    if (item.user?.type?.toLowerCase() === 'bot') continue
    const parsed = parsePreviewLocationMarker(body)
    if (!parsed.path) continue
    out.push({
      id: `issue:${item.id}`,
      rootCommentId: item.id,
      path: parsed.path,
      line: parsed.line,
      startLine: null,
      isResolved: false,
      isOutdated: false,
      canResolve: false,
      source: 'issue',
      url: item.html_url ?? '',
      comments: [
        {
          id: item.id,
          author: item.user?.login ?? 'ghost',
          avatarUrl: item.user?.avatar_url ?? '',
          body: parsed.cleanedBody,
          createdAt: item.created_at ?? '',
          url: item.html_url ?? '',
        },
      ],
    })
  }
  return out
}

/**
 * Fetches inline, file-level, and location-tagged issue PR threads. Uses GraphQL when a
 * PAT is provided and falls back to public REST read-only access otherwise.
 */
export async function fetchPrThreads(
  repo: string,
  prNumber: number,
  token: string,
  fetcher: FetchLike = fetch,
): Promise<RemoteReviewThread[]> {
  const reviewThreads = token
    ? await fetchGraphQlThreads(repo, prNumber, token, fetcher)
    : await fetchRestPullThreads(repo, prNumber, fetcher)
  const issueThreads = await fetchIssueAnchoredThreads(repo, prNumber, token, fetcher)
  return [...reviewThreads, ...issueThreads]
}

/**
 * Submits queued drafts as an atomic GitHub PR review (inline hunks) plus file-level
 * and issue-comment fallbacks, returning per-draft success outcomes so failed items stay saved.
 */
export async function submitBatchedReview(
  meta: PrReviewMeta,
  drafts: DraftComment[],
  summaryBody: string,
  event: ReviewSubmitEvent,
  token: string,
  fetcher: FetchLike = fetch,
): Promise<SubmitDraftOutcome[]> {
  const outcomes: SubmitDraftOutcome[] = []
  const inlineDrafts = drafts.filter((d) => d.mode === 'inline')
  const fileDrafts = drafts.filter((d) => d.mode === 'file')
  const issueDrafts = drafts.filter((d) => d.mode === 'issue')

  if (inlineDrafts.length > 0 || summaryBody.trim().length > 0 || event !== 'COMMENT') {
    try {
      await apiRequest(
        `${GITHUB_API}/repos/${meta.repo}/pulls/${meta.prNumber}/reviews`,
        {
          method: 'POST',
          body: JSON.stringify({
            commit_id: meta.headSha,
            event,
            body: summaryBody.trim(),
            comments: inlineDrafts.map((d) => {
              const entry: Record<string, unknown> = {
                path: d.path,
                line: d.apiLine,
                side: 'RIGHT',
                body: d.body.trim(),
              }
              if (d.apiStartLine < d.apiLine) {
                entry.start_line = d.apiStartLine
                entry.start_side = 'RIGHT'
              }
              return entry
            }),
          }),
        },
        token,
        fetcher,
      )
      for (const d of inlineDrafts) {
        outcomes.push({ draftId: d.id, ok: true })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      for (const d of inlineDrafts) {
        outcomes.push({ draftId: d.id, ok: false, error: msg })
      }
    }
  }

  for (const d of fileDrafts) {
    try {
      await apiRequest(
        `${GITHUB_API}/repos/${meta.repo}/pulls/${meta.prNumber}/comments`,
        {
          method: 'POST',
          body: JSON.stringify({
            commit_id: meta.headSha,
            path: d.path,
            subject_type: 'file',
            body: formatPreviewLocationBody(
              d.body,
              d.path,
              d.startLine,
              d.endLine,
              d.quote,
              d.sectionTitle,
            ),
          }),
        },
        token,
        fetcher,
      )
      outcomes.push({ draftId: d.id, ok: true })
    } catch (err) {
      outcomes.push({
        draftId: d.id,
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      })
    }
  }

  for (const d of issueDrafts) {
    try {
      await apiRequest(
        `${GITHUB_API}/repos/${meta.repo}/issues/${meta.prNumber}/comments`,
        {
          method: 'POST',
          body: JSON.stringify({
            body: formatPreviewLocationBody(
              d.body,
              d.path,
              d.startLine,
              d.endLine,
              d.quote,
              d.sectionTitle,
            ),
          }),
        },
        token,
        fetcher,
      )
      outcomes.push({ draftId: d.id, ok: true })
    } catch (err) {
      outcomes.push({
        draftId: d.id,
        ok: false,
        error: err instanceof Error ? err.message : String(err),
      })
    }
  }

  return outcomes
}

export async function replyToThread(
  repo: string,
  prNumber: number,
  rootCommentId: number,
  body: string,
  token: string,
  fetcher: FetchLike = fetch,
): Promise<void> {
  await apiRequest(
    `${GITHUB_API}/repos/${repo}/pulls/${prNumber}/comments/${rootCommentId}/replies`,
    {
      method: 'POST',
      body: JSON.stringify({ body: body.trim() }),
    },
    token,
    fetcher,
  )
}

export async function setThreadResolved(
  threadId: string,
  resolved: boolean,
  token: string,
  fetcher: FetchLike = fetch,
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
    {
      method: 'POST',
      body: JSON.stringify({ query, variables: { threadId } }),
    },
    token,
    fetcher,
  )
  if (payload.errors?.length) {
    throw new Error(payload.errors.map((e) => e.message).join('; '))
  }
  return Boolean(
    resolved
      ? payload.data?.resolveReviewThread?.thread?.isResolved
      : payload.data?.unresolveReviewThread?.thread?.isResolved,
  )
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
    lines.push('', `### \`${filePath}\``)
    for (const item of items) {
      const span =
        item.endLine > item.startLine
          ? `L${item.startLine}-L${item.endLine}`
          : `L${item.startLine}`
      const ctx = item.sectionTitle ? ` — ${item.sectionTitle}` : ''
      lines.push(`- **${span}** (${item.blockKind}${ctx}): ${item.body.trim()}`)
      if (item.quote) {
        lines.push(`  > ${item.quote}`)
      }
    }
  }
  return lines.join('\n')
}
