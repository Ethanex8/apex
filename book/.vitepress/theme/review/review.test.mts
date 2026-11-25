/**
 * Purpose: Standalone Node test suite for the VitePress PR preview review overlay, GitHub client, layout engine, and pure overlay helpers.
 * Usage: Executed via `node --test book/.vitepress/theme/review/review.test.mts`.
 * Invariants: Every test validates a single focused contract with mocked HTTP/DOM fixtures, fail-fast routing, and zero network side effects.
 */

import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import { createMarkdownRenderer } from 'vitepress'
import { sourceLineMapPlugin } from '../../plugins/sourceLineMap.mts'
import {
  computeBlockAnnotationLayout,
  computeThreadChipPosition,
} from './annotationLayout.ts'
import {
  canAutoRefreshThreads,
  clampSelectionPopover,
  createDraftComment,
  createReplyDraft,
  createResolveDraft,
  effectiveThreadResolved,
  formatLineLabel,
  isAnnotatableBlock,
  isValidDraftComment,
  mapRepoPathToRoute,
  modeBadgeLabel,
  parseStoredDrafts,
  SUMMARY_TRUNCATE_CHARS,
  summarizeComment,
  threadStatusLabel,
} from './overlayHelpers.ts'
import {
  buildGitHubDiffUrl,
  classifyTargetMode,
  detectBlockKind,
  findAnchorElementForLine,
  isJumpableThreadPath,
  isRangeInAddedDiff,
  normalizeQuote,
  shouldTriggerJumpOnClick,
} from './sourceMapper.ts'
import {
  fetchPrHeadInfo,
  fetchPrThreads,
  formatGitHubPermissionError,
  formatMarkdownBundle,
  parsePreviewLocationMarker,
  replyToThread,
  setThreadResolved,
  submitBatchedReview,
  verifyGitHubToken,
  type FetchLike,
} from './githubClient.ts'
import type { DraftComment, PrReviewMeta, RemoteReviewThread } from './types.ts'

const REPO_ROOT = path.resolve(import.meta.dirname, '../../../..')
const TEST_REPO = 'Ethanex8/apex'
const TEST_PR_NUMBER = 42
const TEST_HEAD_SHA = '2222222'
const TEST_PAT = 'pat_test_123'
const TEST_CHAPTER_PATH = 'systems/brain/chapters/01_isa.md'
const TEST_CHAPTER_ROUTE = '/brain/01_isa_and_binary_arithmetic'
const TEST_CHAPTER_FULL = 'systems/brain/chapters/01_isa_and_binary_arithmetic.md'
const TEST_TIMESTAMP = '2026-11-24T00:00:00Z'
const TEST_INLINE_COMMENT_ID = 101
const TEST_FILE_COMMENT_ID = 200
const TEST_BOT_BANNER_ID = 300
const TEST_ISSUE_COMMENT_ID = 301
const TEST_REVIEW_COMMENT_ID = 501
const TEST_INLINE_LINE = 14
const TEST_FILE_LINE = 31
const TEST_ISSUE_LINE = 8
const TEST_PAGE2_CURSOR = 'C1'
const TEST_PAGE2_THREAD_ID = 'T2'
const TEST_PAGE2_LINE = 18

// Layout viewport and clearance constants matching `annotationLayout.ts` and `overlayHelpers.ts`.
const DESKTOP_WIDTH_PX = 1280
const MOBILE_WIDTH_PX = 390
const DOC_MARGIN_LEFT_PX = 24
const DESKTOP_DOC_LEFT_PX = 320
const LIST_MARKER_LEFT_PX = 44
const GUTTER_WIDTH_PX = 3
const MIN_BLOCK_HEIGHT_PX = 12
const BLOCK_BUTTON_WIDTH_PX = 20
const VIEWPORT_EDGE_PAD_PX = 8
const NARROW_WIDTH_PX = 120

// Auto-refresh polling cooldown test timestamps (ms).
const INITIAL_FETCH_MS = 5_000
const SHORT_RETRY_MS = 10_000
const AFTER_AUTH_COOLDOWN_MS = 21_000
const AFTER_ANON_COOLDOWN_MS = 70_000

// Text-truncation fixture strings derived directly from `SUMMARY_TRUNCATE_CHARS`.
const SHORT_BODY = 'Check sign bit.'
const TRUNCATED_PREFIX_CHARS = SUMMARY_TRUNCATE_CHARS - 1
const LONG_BODY = 'x'.repeat(SUMMARY_TRUNCATE_CHARS + 16)
const LONG_BODY_EXPECTED_RE = new RegExp(`^x{${TRUNCATED_PREFIX_CHARS}}…$`)

/** Recorded HTTP request metadata captured by `makeGitHubStub` for contract assertions. */
interface RecordedCall {
  /** Requested full GitHub REST or GraphQL URL. */
  url: string
  /** HTTP verb (`GET`, `POST`, `PATCH`, `PUT`). */
  method: string
  /** Parsed JSON request body or `null` when empty. */
  body: unknown
  /** Sent `Authorization` header value or `null` when anonymous. */
  auth: string | null
}

/** Build a deterministic sample PR review metadata fixture spanning two diff hunks. */
function makeMeta(): PrReviewMeta {
  return {
    enabled: true,
    repo: TEST_REPO,
    prNumber: TEST_PR_NUMBER,
    baseSha: '1111111',
    headSha: TEST_HEAD_SHA,
    prUrl: `https://github.com/${TEST_REPO}/pull/${TEST_PR_NUMBER}`,
    files: {
      [TEST_CHAPTER_PATH]: {
        commentable: [
          [10, 25],
          [50, 60],
        ],
        added: [[12, 20]],
      },
    },
  }
}

/** Construct a reusable valid `DraftComment` fixture without repeating boilerplate fields. */
function makeDraft(overrides: Partial<DraftComment> & { id: string; body: string }): DraftComment {
  return {
    kind: 'comment',
    path: TEST_CHAPTER_PATH,
    startLine: TEST_INLINE_LINE,
    endLine: TEST_INLINE_LINE,
    apiStartLine: TEST_INLINE_LINE,
    apiLine: TEST_INLINE_LINE,
    mode: 'inline',
    quote: 'Sentence A.',
    sectionTitle: 'Sec 1',
    blockKind: 'Paragraph',
    createdAt: TEST_TIMESTAMP,
    ...overrides,
  }
}

/** Construct a reusable issue-target `CommentTarget` fixture for top-level / VISION drafts. */
function makeValidCommentDraft(): DraftComment {
  return createDraftComment(
    {
      path: 'VISION.md',
      startLine: 3,
      endLine: 3,
      apiStartLine: 3,
      apiLine: 3,
      mode: 'issue',
      quote: '',
      sectionTitle: 'Goal',
      blockKind: 'Paragraph',
    },
    'Check alignment',
  )
}

/** Construct a reusable resolve/reopen `DraftComment` fixture. */
function makeResolveDraft(
  id: string,
  resolved: boolean,
  source: 'inline' | 'issue' = 'inline',
  rawRootBody?: string,
): DraftComment {
  const isIssue = source === 'issue'
  return makeDraft({
    id,
    kind: 'resolve',
    path: isIssue ? '' : TEST_CHAPTER_PATH,
    startLine: isIssue ? 1 : TEST_INLINE_LINE,
    endLine: isIssue ? 1 : TEST_INLINE_LINE,
    apiStartLine: isIssue ? 1 : TEST_INLINE_LINE,
    apiLine: isIssue ? 1 : TEST_INLINE_LINE,
    mode: isIssue ? 'issue' : 'inline',
    quote: isIssue ? 'General note' : 'Clarify bit slice.',
    sectionTitle: resolved ? 'Resolve thread' : 'Reopen thread',
    blockKind: resolved ? 'Resolve' : 'Reopen',
    body: resolved ? 'Resolve thread' : 'Reopen thread',
    resolveTarget: {
      threadId: isIssue ? `ISSUE_${TEST_BOT_BANNER_ID}` : 'PRRT_1',
      rootCommentId: isIssue ? TEST_BOT_BANNER_ID : TEST_INLINE_COMMENT_ID,
      source,
      path: isIssue ? '' : TEST_CHAPTER_PATH,
      line: isIssue ? null : TEST_INLINE_LINE,
      resolved,
      rawRootBody,
    },
  })
}

/** Build a single GraphQL PR review thread fixture node. */
function makeGraphqlThreadNode(id: string, line: number, commentId: number) {
  return {
    id,
    isResolved: false,
    isOutdated: false,
    path: TEST_CHAPTER_PATH,
    line,
    startLine: null,
    originalLine: line,
    comments: {
      nodes: [
        {
          databaseId: commentId,
          body: 'Clarify bit slice.',
          createdAt: TEST_TIMESTAMP,
          url: `https://github.com/${TEST_REPO}/pull/${TEST_PR_NUMBER}#discussion_r${commentId}`,
          author: { login: 'Ethanex8', avatarUrl: '' },
        },
      ],
    },
  }
}

/** Handle `/graphql` pagination and resolve/unresolve thread mutations deterministically. */
function mockGraphqlRoute(body: unknown): Response {
  const gqlBody = body as { query: string; variables: Record<string, unknown> }
  if (/\bunresolveReviewThread\b/.test(gqlBody.query)) {
    return new Response(
      JSON.stringify({ data: { unresolveReviewThread: { thread: { id: 'T1', isResolved: false } } } }),
      { status: 200 },
    )
  }
  if (/\bresolveReviewThread\b/.test(gqlBody.query)) {
    return new Response(
      JSON.stringify({ data: { resolveReviewThread: { thread: { id: 'T1', isResolved: true } } } }),
      { status: 200 },
    )
  }
  // Return page 1 with `endCursor: 'C1'` and page 2 with thread `T2` so cursor pagination is genuinely exercised.
  if (!gqlBody.variables.after) {
    return new Response(
      JSON.stringify({
        data: {
          repository: {
            pullRequest: {
              reviewThreads: {
                pageInfo: { hasNextPage: true, endCursor: TEST_PAGE2_CURSOR },
                nodes: [makeGraphqlThreadNode('T1', TEST_INLINE_LINE, TEST_INLINE_COMMENT_ID)],
              },
            },
          },
        },
      }),
      { status: 200 },
    )
  }
  return new Response(
    JSON.stringify({
      data: {
        repository: {
          pullRequest: {
            reviewThreads: {
              pageInfo: { hasNextPage: false, endCursor: null },
              nodes: [makeGraphqlThreadNode(TEST_PAGE2_THREAD_ID, TEST_PAGE2_LINE, 102)],
            },
          },
        },
      },
    }),
    { status: 200 },
  )
}

/** Handle pull-request REST endpoints (`/comments`, `/reviews`). */
function mockPullReviewRoutes(url: string, method: string): Response | null {
  if (url.includes(`/pulls/${TEST_PR_NUMBER}/comments?per_page=100`)) {
    // Include a null-line file comment whose location marker recovers line 31 during REST fallback parsing.
    return new Response(
      JSON.stringify([
        {
          id: TEST_FILE_COMMENT_ID,
          path: TEST_CHAPTER_PATH,
          line: null,
          original_line: null,
          body: `File comment.\n\n<!-- apex-preview-loc: path=${TEST_CHAPTER_PATH} line=${TEST_FILE_LINE} -->`,
          user: { login: 'Ethanex8' },
        },
        { id: 201, in_reply_to_id: TEST_FILE_COMMENT_ID, path: TEST_CHAPTER_PATH, body: 'Reply here', user: { login: 'bot' } },
      ]),
      { status: 200 },
    )
  }
  if (url.includes(`/pulls/${TEST_PR_NUMBER}/reviews?per_page=100`)) {
    return new Response(
      JSON.stringify([
        {
          id: 400,
          state: 'COMMENTED',
          body: 'Overall summary note.',
          submitted_at: '2026-11-24T01:00:00Z',
          html_url: `https://github.com/${TEST_REPO}/pull/${TEST_PR_NUMBER}#pullrequestreview-400`,
          user: { login: 'Ethanex8', type: 'User' },
        },
      ]),
      { status: 200 },
    )
  }
  if (method === 'POST' && (url.endsWith(`/pulls/${TEST_PR_NUMBER}/reviews`) || url.endsWith(`/pulls/${TEST_PR_NUMBER}/comments`) || url.endsWith(`/comments/${TEST_INLINE_COMMENT_ID}/replies`))) {
    return new Response(JSON.stringify({ id: 901 }), { status: 201 })
  }
  return null
}

/** Handle issue comment GET/POST/PATCH endpoints including bot banners and reply markers. */
function mockIssueRoutes(url: string, method: string): Response | null {
  if (url.includes(`/issues/${TEST_PR_NUMBER}/comments`)) {
    if (method === 'GET') {
      // Bot preview banner is filtered out, while human issue comment #301 merges reply #303 via reply-to marker.
      return new Response(
        JSON.stringify([
          { id: TEST_BOT_BANNER_ID, body: '<!-- apex-book-preview -->\nPreview bot', user: { login: 'github-actions[bot]', type: 'Bot' } },
          { id: TEST_ISSUE_COMMENT_ID, body: `Check typo.\n\n<!-- apex-preview-loc: path=VISION.md line=${TEST_ISSUE_LINE} -->`, user: { login: 'Ethanex8', type: 'User' } },
          { id: 303, body: `Fixed typo.\n\n<!-- apex-preview-reply-to: ${TEST_ISSUE_COMMENT_ID} -->`, user: { login: 'Ethanex8', type: 'User' } },
        ]),
        { status: 200 },
      )
    }
    if (method === 'POST') return new Response(JSON.stringify({ id: 302 }), { status: 201 })
  }
  if ((url.includes(`/issues/comments/${TEST_ISSUE_COMMENT_ID}`) || url.includes(`/issues/comments/${TEST_BOT_BANNER_ID}`)) && method === 'PATCH') {
    return new Response(JSON.stringify({ id: TEST_ISSUE_COMMENT_ID }), { status: 200 })
  }
  return null
}

/** Build a fail-fast mock GitHub API `fetch` stub recording every outgoing call. */
function makeGitHubStub(): { calls: RecordedCall[]; mockFetch: FetchLike } {
  const calls: RecordedCall[] = []
  const mockFetch: FetchLike = async (input, init) => {
    const url = typeof input === 'string' ? input : input.toString()
    const method = init?.method ?? 'GET'
    const headers = (init?.headers ?? {}) as Record<string, string>
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : null
    calls.push({ url, method, body, auth: headers.Authorization ?? null })

    if (url.endsWith('/user')) {
      return new Response(JSON.stringify({ login: 'Ethanex8', avatar_url: 'https://a/1.png' }), { status: 200 })
    }
    if (url.endsWith('/graphql')) return mockGraphqlRoute(body)
    const pullRes = mockPullReviewRoutes(url, method)
    if (pullRes) return pullRes
    const issueRes = mockIssueRoutes(url, method)
    if (issueRes) return issueRes
    return new Response(JSON.stringify({ message: `Unmocked ${method} ${url}` }), { status: 404 })
  }
  return { calls, mockFetch }
}

test('sourceLineMapPlugin emits exact block line attrs, sentence wbr offsets, and widget wrappers', async () => {
  const md = await createMarkdownRenderer(REPO_ROOT, {
    math: true,
    lineNumbers: true,
    config: (instance) => {
      sourceLineMapPlugin(instance)
    },
  })

  // Opening `<details>` maps `data-src-end="9"` to its summary line while block prose spans lines 3..5.
  const src = [
    '# Title',
    '',
    'Sentence one.',
    'Sentence two.',
    'Sentence three.',
    '',
    '<UnsignedClockRing />',
    '',
    '<details><summary>Sol</summary>',
    '',
    'Answer line.',
    '',
    '</details>',
    '',
    '$$',
    'a = 1',
    '$$',
    '',
    '```python',
    'x = 1',
    '```',
  ].join('\n')
  const html = md.render(src)
  assert.match(html, /<h1[^>]*data-src-line="1" data-src-end="1"/)
  assert.match(html, /<p data-src-line="3" data-src-end="5">/)
  assert.match(html, /<wbr data-apex-line="3">Sentence one\./)
  assert.match(html, /<wbr data-apex-line="4">Sentence two\./)
  assert.match(html, /<wbr data-apex-line="5">Sentence three\./)
  assert.match(html, /<div class="apex-review-block apex-review-widget" data-src-line="7" data-src-end="7">\s*<UnsignedClockRing \/>/)
  assert.match(html, /<details data-src-line="9" data-src-end="9"><summary>Sol<\/summary>/)
  assert.match(html, /<div class="apex-review-block apex-review-math" data-src-line="15" data-src-end="17">/)
  assert.match(html, /<div class="apex-review-block" data-src-line="19" data-src-end="21">/)
})

test('classifyTargetMode handles inline hunks, reversed/enclosing bounds, file fallback, and NaN lines', () => {
  const meta = makeMeta()
  assert.deepEqual(classifyTargetMode(TEST_CHAPTER_PATH, 12, 15, meta.files), { mode: 'inline', apiStartLine: 12, apiLine: 15 })
  assert.deepEqual(classifyTargetMode(TEST_CHAPTER_PATH, 8, 12, meta.files), { mode: 'inline', apiStartLine: 10, apiLine: 12 })
  assert.deepEqual(classifyTargetMode(TEST_CHAPTER_PATH, 23, 28, meta.files), { mode: 'inline', apiStartLine: 23, apiLine: 25 })
  assert.deepEqual(classifyTargetMode(TEST_CHAPTER_PATH, 20, 12, meta.files), { mode: 'inline', apiStartLine: 12, apiLine: 20 })
  assert.deepEqual(classifyTargetMode(TEST_CHAPTER_PATH, 8, 28, meta.files), { mode: 'inline', apiStartLine: 10, apiLine: 25 })
  assert.deepEqual(classifyTargetMode(TEST_CHAPTER_PATH, 30, 32, meta.files), { mode: 'file', apiStartLine: 30, apiLine: 32 })
  assert.deepEqual(classifyTargetMode('VISION.md', Number.NaN, Number.NaN, meta.files), { mode: 'issue', apiStartLine: 1, apiLine: 1 })
})

test('sourceMapper added-diff check, quote normalization, and GitHub SHA-256 URLs match contracts', async () => {
  const meta = makeMeta()
  assert.equal(isRangeInAddedDiff(TEST_CHAPTER_PATH, 19, 22, meta.files), true)
  assert.equal(isRangeInAddedDiff(TEST_CHAPTER_PATH, 22, 19, meta.files), true)
  assert.equal(isRangeInAddedDiff(TEST_CHAPTER_PATH, 50, 55, meta.files), false)
  assert.equal(isRangeInAddedDiff('UNKNOWN.md', 1, 5, meta.files), false)
  assert.equal(normalizeQuote('  hello   world  '), 'hello world')
  assert.equal(normalizeQuote('abcdefghij', 6), 'abcde…')
  assert.equal(normalizeQuote('abc', 0), '')

  const visionHash = createHash('sha256').update('VISION.md').digest('hex')
  assert.equal(await buildGitHubDiffUrl(TEST_REPO, TEST_PR_NUMBER, 'VISION.md', 12), `https://github.com/${TEST_REPO}/pull/${TEST_PR_NUMBER}/files#diff-${visionHash}R12`)
  assert.equal(await buildGitHubDiffUrl(TEST_REPO, TEST_PR_NUMBER, 'VISION.md', null), `https://github.com/${TEST_REPO}/pull/${TEST_PR_NUMBER}/files#diff-${visionHash}`)
})

test('detectBlockKind classifies widgets, equations, mermaid diagrams, code blocks, and headings', () => {
  const makeBlock = (tagName: string, cls = '', matchSelector = '') => ({
    tagName,
    classList: { contains: (c: string) => c === cls },
    querySelector: (sel: string) => (matchSelector && sel.includes(matchSelector) ? {} : null),
  }) as unknown as HTMLElement
  assert.equal(detectBlockKind(makeBlock('H2')), 'Heading')
  assert.equal(detectBlockKind(makeBlock('DIV', 'apex-review-widget')), 'Interactive Widget')
  assert.equal(detectBlockKind(makeBlock('DIV', 'apex-review-math')), 'Equation')
  assert.equal(detectBlockKind(makeBlock('DIV', '', '.mermaid-book-figure')), 'Mermaid Diagram')
  assert.equal(detectBlockKind(makeBlock('DIV', '', 'pre.vp-code')), 'Code Block')
})

test('findAnchorElementForLine selects tightest span and skips occluded or malformed non-positive attrs', () => {
  const makeNode = (srcLine: string, srcEnd: string, occluded = false) => ({
    dataset: { srcLine, srcEnd },
    closest: () => (occluded ? {} : null),
  })
  const badEl = makeNode('bad', '20')
  const zeroEl = makeNode('0', '20')
  const negEl = makeNode('-1', '20')
  const occludedEl = makeNode('14', '14', true)
  const gapEl = makeNode('8', '')
  const wideEl = makeNode('10', '20')
  const exactEl = makeNode('12', '15')
  const docRoot = { querySelectorAll: () => [badEl, zeroEl, negEl, occludedEl, gapEl, wideEl, exactEl] } as unknown as Element
  assert.equal(findAnchorElementForLine(docRoot, 14), exactEl)
  assert.equal(findAnchorElementForLine(docRoot, 8), gapEl)
  assert.equal(findAnchorElementForLine(docRoot, 18), wideEl)
  // `line === null` returns the first `[data-src-line]` DOM node unconditionally before line-range parsing.
  assert.equal(findAnchorElementForLine(docRoot, null), badEl)
})

test('verifyGitHubToken authenticates valid PATs and fails fast on malformed or error HTTP responses', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const user = await verifyGitHubToken(TEST_PAT, mockFetch)
  assert.equal(user.login, 'Ethanex8')
  assert.equal(calls[0].auth, `Bearer ${TEST_PAT}`)
  await assert.rejects(verifyGitHubToken(TEST_PAT, async () => new Response('<html>bad</html>', { status: 200 })), /Invalid JSON response from GitHub \(200\)/)
  await assert.rejects(verifyGitHubToken(TEST_PAT, async () => new Response('<html>Gateway Error</html>', { status: 502 })), /502: GitHub API error \(502\)/)
})

test('fetchPrThreads paginates GraphQL cursor C1 and merges issue and review threads', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const authThreads = await fetchPrThreads(TEST_REPO, TEST_PR_NUMBER, TEST_PAT, mockFetch)
  const gqlCalls = calls.filter((c) => c.url.endsWith('/graphql'))
  assert.equal(gqlCalls.length, 2)
  assert.equal((gqlCalls[1].body as { variables: { after: string | null } }).variables.after, TEST_PAGE2_CURSOR)
  assert.equal(authThreads.length, 4)
  assert.equal(authThreads[1].id, TEST_PAGE2_THREAD_ID)
  assert.equal(authThreads[1].line, TEST_PAGE2_LINE)

  const issueThread = authThreads.find((t) => t.source === 'issue')
  assert.ok(issueThread)
  assert.equal(issueThread.path, 'VISION.md')
  assert.equal(issueThread.line, TEST_ISSUE_LINE)
  assert.equal(issueThread.comments[1].body, 'Fixed typo.')
})

test('fetchPrThreads falls back to REST endpoints cleanly when unauthenticated', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const anonThreads = await fetchPrThreads(TEST_REPO, TEST_PR_NUMBER, '', mockFetch)
  assert.equal(calls.some((c) => c.url.endsWith('/graphql')), false)
  assert.equal(anonThreads.length, 3)
  assert.equal(anonThreads[0].source, 'file')
  assert.equal(anonThreads[0].line, TEST_FILE_LINE)
  assert.equal(anonThreads[0].comments.length, 2)
})

test('submitBatchedReview dispatches inline, file, and issue drafts accurately', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const drafts: DraftComment[] = [
    makeDraft({ id: 'd1', body: 'Single line inline comment' }),
    makeDraft({ id: 'd2', startLine: 15, endLine: 17, apiStartLine: 15, apiLine: 17, body: 'Multi-line inline comment' }),
    makeDraft({ id: 'd3', startLine: 30, endLine: 30, apiStartLine: 30, apiLine: 30, mode: 'file', body: 'File-level fallback' }),
    makeDraft({ id: 'd4', path: 'VISION.md', startLine: 7, endLine: 7, apiStartLine: 7, apiLine: 7, mode: 'issue', body: 'Untouched page comment' }),
  ]

  const result = await submitBatchedReview(makeMeta(), drafts, 'Overall solid', 'COMMENT', TEST_PAT, mockFetch)
  assert.equal(result.summaryOk, true)
  assert.deepEqual(result.outcomes.map((o) => o.ok), [true, true, true, true])

  const reviewCall = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/pulls/${TEST_PR_NUMBER}/reviews`))
  assert.ok(reviewCall)
  const reviewBody = reviewCall.body as { commit_id: string; body: string; event: string; comments: Array<Record<string, unknown>> }
  assert.equal(reviewBody.commit_id, TEST_HEAD_SHA)
  assert.equal(reviewBody.event, 'COMMENT')
  assert.equal(reviewBody.comments.length, 2)
  // Single-line REST review comments must omit `start_line` to satisfy GitHub's single-line schema.
  assert.equal('start_line' in reviewBody.comments[0], false)
  assert.equal(reviewBody.comments[1].start_line, 15)

  const fileCall = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/pulls/${TEST_PR_NUMBER}/comments`))
  assert.ok(fileCall)
  assert.equal((fileCall.body as Record<string, unknown>).subject_type, 'file')

  const issueCall = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/issues/${TEST_PR_NUMBER}/comments`))
  assert.ok(issueCall)
  assert.match(String((issueCall.body as { body: string }).body), /<!-- apex-preview-loc: path=VISION\.md line=7 -->/)
})

test('submitBatchedReview omits commit_id and comments for summary-only reviews', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const summaryOnly = await submitBatchedReview(makeMeta(), [], 'Only overall note', 'COMMENT', TEST_PAT, mockFetch)
  assert.equal(summaryOnly.summaryOk, true)
  const post = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/pulls/${TEST_PR_NUMBER}/reviews`))
  assert.ok(post)
  const payload = post.body as Record<string, unknown>
  assert.equal('commit_id' in payload, false)
  assert.equal('comments' in payload, false)
  assert.equal(payload.body, 'Only overall note')
  assert.equal(payload.event, 'COMMENT')
})

test('replyToThread and setThreadResolved send expected GraphQL and marker payloads', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const authThreads = await fetchPrThreads(TEST_REPO, TEST_PR_NUMBER, TEST_PAT, mockFetch)
  const inlineThread = authThreads[0]
  const issueThread = authThreads.find((t) => t.source === 'issue')
  assert.ok(issueThread)

  await replyToThread(TEST_REPO, TEST_PR_NUMBER, inlineThread, 'Thanks!', TEST_PAT, mockFetch)
  const inlineReply = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/comments/${TEST_INLINE_COMMENT_ID}/replies`))
  assert.ok(inlineReply)
  assert.equal((inlineReply.body as { body: string }).body, 'Thanks!')

  await replyToThread(TEST_REPO, TEST_PR_NUMBER, issueThread, 'Follow-up!', TEST_PAT, mockFetch)
  const issueReply = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/issues/${TEST_PR_NUMBER}/comments`))
  assert.ok(issueReply)
  assert.match(String((issueReply.body as { body: string }).body), new RegExp(`<!-- apex-preview-reply-to: ${TEST_ISSUE_COMMENT_ID} -->`))

  assert.equal(await setThreadResolved(TEST_REPO, TEST_PR_NUMBER, inlineThread, true, TEST_PAT, mockFetch), true)
  assert.equal(await setThreadResolved(TEST_REPO, TEST_PR_NUMBER, inlineThread, false, TEST_PAT, mockFetch), false)
  assert.equal(await setThreadResolved(TEST_REPO, TEST_PR_NUMBER, issueThread, true, TEST_PAT, mockFetch), true)
  const issuePatch = calls.find((c) => c.method === 'PATCH' && c.url.endsWith(`/issues/comments/${TEST_ISSUE_COMMENT_ID}`))
  assert.ok(issuePatch)
  assert.match(String((issuePatch.body as { body: string }).body), /<!-- apex-preview-resolved: 1 -->/)
})

test('parsePreviewLocationMarker extracts path, line, resolved flag, and reply target', () => {
  assert.equal(parsePreviewLocationMarker('plain').line, null)
  const parsed = parsePreviewLocationMarker(`Note.\n\n<!-- apex-preview-loc: path=${TEST_CHAPTER_PATH} line=22 -->\n<!-- apex-preview-resolved: 1 -->\n<!-- apex-preview-reply-to: 99 -->`)
  assert.equal(parsed.path, TEST_CHAPTER_PATH)
  assert.equal(parsed.line, 22)
  assert.equal(parsed.isResolved, true)
  assert.equal(parsed.replyToId, 99)
  assert.equal(parsed.cleanedBody, 'Note.')
})

test('formatMarkdownBundle formats multi-line comments, replies, and reopen entries cleanly', () => {
  const commentDraft = makeDraft({ id: 'd2', startLine: 15, endLine: 17, apiStartLine: 15, apiLine: 17, body: 'Multi-line inline comment' })
  const reopenDraft = makeResolveDraft('res_open', false, 'inline')
  const bundle = formatMarkdownBundle(makeMeta(), [commentDraft, reopenDraft], 'Summary')
  assert.match(bundle, new RegExp(`Inline Preview Review — PR #${TEST_PR_NUMBER}`))
  assert.match(bundle, /\*\*L15-L17\*\*/)
  assert.match(bundle, new RegExp(`- \\*\\*Reopen thread\\*\\* \\(L${TEST_INLINE_LINE}, #${TEST_INLINE_COMMENT_ID}\\)$`, 'm'))
})

test('submitBatchedReview routes queued reply drafts for both inline and review threads', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const replyDrafts: DraftComment[] = [
    makeDraft({ id: 'r1', kind: 'reply', sectionTitle: 'Reply to @Ethanex8', blockKind: 'reply', body: 'Staged inline reply', replyTarget: { threadId: 'PRRT_1', rootCommentId: TEST_INLINE_COMMENT_ID, source: 'inline', author: 'Ethanex8', path: TEST_CHAPTER_PATH, line: TEST_INLINE_LINE } }),
    makeDraft({ id: 'r2', kind: 'reply', path: '', startLine: 1, endLine: 1, apiStartLine: 1, apiLine: 1, mode: 'issue', quote: 'Review summary.', sectionTitle: 'Reply to @Ethanex8', blockKind: 'reply', body: 'Staged review reply', replyTarget: { threadId: 'REV_1', rootCommentId: TEST_REVIEW_COMMENT_ID, source: 'review', author: 'Ethanex8', path: '', line: null } }),
  ]
  const replyResult = await submitBatchedReview(makeMeta(), replyDrafts, '', 'COMMENT', TEST_PAT, mockFetch)
  assert.deepEqual(replyResult.outcomes.map((o) => o.ok), [true, true])

  const inlinePost = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/comments/${TEST_INLINE_COMMENT_ID}/replies`))
  assert.ok(inlinePost)
  assert.equal((inlinePost.body as { body: string }).body, 'Staged inline reply')

  const reviewIssuePost = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/issues/${TEST_PR_NUMBER}/comments`))
  assert.ok(reviewIssuePost)
  assert.match(String((reviewIssuePost.body as { body: string }).body), /Staged review reply/)

  const replyMd = formatMarkdownBundle(makeMeta(), replyDrafts, '')
  assert.match(replyMd, new RegExp(`\\*\\*Reply to @Ethanex8\\*\\* \\(L${TEST_INLINE_LINE}, #${TEST_INLINE_COMMENT_ID}\\): Staged inline reply`))
  assert.match(replyMd, new RegExp(`\\*\\*Reply to @Ethanex8\\*\\* \\(#${TEST_REVIEW_COMMENT_ID}\\): Staged review reply`))
})

test('fetchPrHeadInfo requests cache-busted head SHA and state', async () => {
  const headInfo = await fetchPrHeadInfo(TEST_REPO, TEST_PR_NUMBER, TEST_PAT, async (input) => {
    assert.match(String(input), new RegExp(`/pulls/${TEST_PR_NUMBER}\\?_t=\\d+$`))
    return new Response(JSON.stringify({ head: { sha: 'deadbeef1234' }, state: 'open' }), { status: 200 })
  })
  assert.deepEqual(headInfo, { headSha: 'deadbeef1234', state: 'open' })
})

test('submitBatchedReview posts staged top-level PR comment drafts', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const meta = makeMeta()
  const topDraft = [createDraftComment({ path: '', startLine: 1, endLine: 1, apiStartLine: 1, apiLine: 1, mode: 'issue', quote: '', sectionTitle: `PR #${TEST_PR_NUMBER}`, blockKind: 'PR Comment' }, 'Staged top-level PR note')]
  const topRes = await submitBatchedReview(meta, topDraft, '', 'COMMENT', TEST_PAT, mockFetch)
  assert.equal(topRes.outcomes[0].ok, true)
  const post = calls.find((c) => c.method === 'POST' && c.url.endsWith(`/issues/${TEST_PR_NUMBER}/comments`))
  assert.ok(post)
  assert.equal((post.body as { body: string }).body, 'Staged top-level PR note')
  assert.match(formatMarkdownBundle(meta, topDraft, ''), /\*\*Top-level PR comment\*\*: Staged top-level PR note/)
})

test('submitBatchedReview sends GraphQL resolve variables and preserves issue rawRootBody on PATCH', async () => {
  const { calls, mockFetch } = makeGitHubStub()
  const resolveDrafts = [makeResolveDraft('res1', true, 'inline'), makeResolveDraft('res2', true, 'issue', 'General note')]
  const resolveBatch = await submitBatchedReview(makeMeta(), resolveDrafts, '', 'COMMENT', TEST_PAT, mockFetch)
  assert.deepEqual(resolveBatch.outcomes.map((o) => o.ok), [true, true])

  const gqlCall = calls.find((c) => c.url.endsWith('/graphql'))
  assert.ok(gqlCall)
  const gqlPayload = gqlCall.body as { query: string; variables: { threadId: string } }
  assert.match(gqlPayload.query, /\bresolveReviewThread\b/)
  assert.equal(gqlPayload.variables.threadId, 'PRRT_1')

  const patchCall = calls.find((c) => c.method === 'PATCH' && c.url.endsWith(`/issues/comments/${TEST_BOT_BANNER_ID}`))
  assert.ok(patchCall)
  assert.match(String((patchCall.body as { body: string }).body), /^General note[\s\S]*<!-- apex-preview-resolved: 1 -->/)

  const bundle = formatMarkdownBundle(makeMeta(), resolveDrafts, '')
  assert.match(bundle, new RegExp(`- \\*\\*Resolve thread\\*\\* \\(L${TEST_INLINE_LINE}, #${TEST_INLINE_COMMENT_ID}\\)$`, 'm'))
  assert.match(bundle, new RegExp(`- \\*\\*Resolve thread\\*\\* \\(#${TEST_BOT_BANNER_ID}\\)$`, 'm'))
})

test('computeBlockAnnotationLayout keeps gutter bars clear of list markers and clamps min height', () => {
  // Mobile `390px`: `.vp-doc` left edge sits at `24px`; `<ol>` markers occupy `24..44px`, so gutters stay at `14px`.
  const mobilePara = computeBlockAnnotationLayout({ top: 100, left: DOC_MARGIN_LEFT_PX, right: 366, height: 40 }, DOC_MARGIN_LEFT_PX, 0, 500, MOBILE_WIDTH_PX, true)
  assert.equal(mobilePara.gutterLeft, 14)

  const mobileListItem = computeBlockAnnotationLayout({ top: 160, left: LIST_MARKER_LEFT_PX, right: 366, height: 80 }, DOC_MARGIN_LEFT_PX, 0, 500, MOBILE_WIDTH_PX, true)
  assert.equal(mobileListItem.gutterLeft, 14)
  assert.equal(mobileListItem.gutterLeft + GUTTER_WIDTH_PX <= DOC_MARGIN_LEFT_PX, true)
  // Vertical coordinate adds scrollY (`160 + 500 = 660`) and button aligns to right padding margin (`344`).
  assert.equal(mobileListItem.gutterTop, 660)
  assert.equal(mobileListItem.buttonLeft, 344)

  const mobileCode = computeBlockAnnotationLayout({ top: 260, left: 0, right: MOBILE_WIDTH_PX, height: 60 }, DOC_MARGIN_LEFT_PX, 0, 0, MOBILE_WIDTH_PX, true)
  assert.equal(mobileCode.gutterLeft, GUTTER_WIDTH_PX)

  // Desktop `1280px` places gutter at `docLeft - 10 = 310` and `+` button at `310 - 24 = 286`.
  const desktopListItem = computeBlockAnnotationLayout({ top: 120, left: 340, right: 940, height: 90 }, DESKTOP_DOC_LEFT_PX, 0, 100, DESKTOP_WIDTH_PX, false)
  assert.equal(desktopListItem.gutterLeft, 310)
  assert.equal(desktopListItem.buttonLeft, 286)
  assert.equal(desktopListItem.buttonLeft + BLOCK_BUTTON_WIDTH_PX < desktopListItem.gutterLeft, true)

  // Collapsed zero-width viewport clamps button inside `8px` margin and enforces `MIN_BLOCK_HEIGHT_PX = 12`.
  const collapsed = computeBlockAnnotationLayout({ top: 0, left: DOC_MARGIN_LEFT_PX, right: 20, height: 10 }, DOC_MARGIN_LEFT_PX, 0, 0, 0, true)
  assert.equal(collapsed.buttonLeft, VIEWPORT_EDGE_PAD_PX)
  assert.equal(collapsed.buttonTop, 4)
  assert.equal(collapsed.gutterTop, 0)
  assert.equal(collapsed.gutterHeight, MIN_BLOCK_HEIGHT_PX)
})

test('computeThreadChipPosition places desktop/mobile chips and clamps scrolled viewport edges', () => {
  // Desktop places chip `8px` right of block (`940 + 8 = 948`); mobile pulls inside viewport right margin (`274`).
  assert.deepEqual(computeThreadChipPosition({ top: 120, left: DESKTOP_DOC_LEFT_PX, right: 940, height: 40 }, 0, 50, DESKTOP_WIDTH_PX), { top: 172, left: 948 })
  assert.deepEqual(computeThreadChipPosition({ top: 120, left: LIST_MARKER_LEFT_PX, right: 366, height: 40 }, 0, 50, MOBILE_WIDTH_PX), { top: 158, left: 274 })

  // Scrolling down near the top clamps negative `top` to `0` (`top=4, height=30 -> 4 + 0 - 12 = -8` clamped to `0`).
  const topScrolledChip = computeThreadChipPosition({ top: 4, left: DOC_MARGIN_LEFT_PX, right: 366, height: 30 }, 0, 0, MOBILE_WIDTH_PX)
  assert.equal(topScrolledChip.top, 0)
  assert.equal(topScrolledChip.left >= VIEWPORT_EDGE_PAD_PX, true)
})

test('formatGitHubPermissionError explains Fine-Grained PAT scopes for GraphQL resolve and REST failures', async () => {
  assert.equal(formatGitHubPermissionError('Not Found', 'read'), 'Not Found')
  const resolveMsg = formatGitHubPermissionError('Resource not accessible by personal access token', 'graphql_resolve')
  assert.match(resolveMsg, /Pull requests: Read and write/)
  assert.match(resolveMsg, /Contents: Read and write/)

  const meta = makeMeta()
  const gql403Fetch: FetchLike = async () => new Response(JSON.stringify({ errors: [{ message: 'Resource not accessible by personal access token' }] }), { status: 200 })
  const gqlOut = await submitBatchedReview(meta, [makeResolveDraft('res_err', true, 'inline')], '', 'COMMENT', TEST_PAT, gql403Fetch)
  assert.equal(gqlOut.outcomes[0].ok, false)
  assert.match(gqlOut.outcomes[0].error ?? '', /Contents: Read and write/)

  const rest403Fetch: FetchLike = async () => new Response(JSON.stringify({ message: 'Resource not accessible by personal access token' }), { status: 403 })
  const restOut = await submitBatchedReview(meta, [makeDraft({ id: 'iss_err', path: '', startLine: 1, endLine: 1, apiStartLine: 1, apiLine: 1, mode: 'issue', quote: '', sectionTitle: `PR #${TEST_PR_NUMBER}`, blockKind: 'PR Comment', body: 'Top-level note' })], '', 'COMMENT', TEST_PAT, rest403Fetch)
  assert.equal(restOut.outcomes[0].ok, false)
  assert.match(restOut.outcomes[0].error ?? '', /403: Resource not accessible by personal access token/)
  assert.match(restOut.outcomes[0].error ?? '', /Issues: Read and write/)
})

test('isJumpableThreadPath excludes PR summary and conversation synthetic paths', () => {
  assert.equal(isJumpableThreadPath(TEST_CHAPTER_PATH), true)
  assert.equal(isJumpableThreadPath('PR Summary'), false)
  assert.equal(isJumpableThreadPath('PR Conversation'), false)
  assert.equal(isJumpableThreadPath(''), false)
})

test('shouldTriggerJumpOnClick ignores nested buttons and active text selections', () => {
  assert.equal(shouldTriggerJumpOnClick({ closest: () => null }, ''), true)
  assert.equal(shouldTriggerJumpOnClick({ closest: () => null }, 'copied text'), false)
  assert.equal(shouldTriggerJumpOnClick({ closest: (sel) => (sel.includes('button') ? {} : null) }, ''), false)
  assert.equal(shouldTriggerJumpOnClick(null, ''), true)
})

test('setThreadResolved fails fast when GraphQL response omits updated resolution state', async () => {
  await assert.rejects(
    setThreadResolved(
      TEST_REPO,
      TEST_PR_NUMBER,
      { id: 'T1', rootCommentId: TEST_INLINE_COMMENT_ID, path: TEST_CHAPTER_PATH, line: TEST_INLINE_LINE, startLine: null, isResolved: false, isOutdated: false, canResolve: true, source: 'inline', url: '', comments: [] },
      false,
      TEST_PAT,
      async () => new Response(JSON.stringify({ data: { unresolveReviewThread: {} } }), { status: 200 }),
    ),
    /omitted updated thread resolution state/,
  )
})

test('overlayHelpers mapRepoPathToRoute resolves textbook routes and rejects subsystem contracts', () => {
  assert.equal(mapRepoPathToRoute('book/index.md'), '/')
  assert.equal(mapRepoPathToRoute('VISION.md'), '/vision')
  assert.equal(mapRepoPathToRoute(TEST_CHAPTER_FULL), TEST_CHAPTER_ROUTE)
  assert.equal(mapRepoPathToRoute('systems/brain/README.md'), null)
})

test('overlayHelpers label and summary formatters format lines, modes, and 64-char summaries', () => {
  assert.equal(formatLineLabel(12, 12), 'L12')
  assert.equal(formatLineLabel(12, 18), 'L12–L18')
  assert.equal(modeBadgeLabel('inline'), 'Native inline PR thread')
  assert.equal(modeBadgeLabel('file'), 'File-level PR thread (outside hunk)')
  assert.equal(modeBadgeLabel('issue'), 'PR conversation comment (unchanged file)')
  assert.equal(summarizeComment({ id: 1, author: 'a', avatarUrl: '', body: SHORT_BODY, createdAt: '', url: '' }), SHORT_BODY)
  assert.match(summarizeComment({ id: 1, author: 'a', avatarUrl: '', body: LONG_BODY, createdAt: '', url: '' }), LONG_BODY_EXPECTED_RE)
})

test('overlayHelpers filters overlay controls, table rows, and child-paragraph list wrappers', () => {
  assert.equal(isAnnotatableBlock({ closest: () => ({}), tagName: 'P', querySelector: () => null }), false)
  assert.equal(isAnnotatableBlock({ closest: () => null, tagName: 'TR', querySelector: () => null }), false)
  assert.equal(isAnnotatableBlock({ closest: () => null, tagName: 'LI', querySelector: () => ({}) }), false)
  assert.equal(isAnnotatableBlock({ closest: () => null, tagName: 'LI', querySelector: () => null }), true)
  assert.equal(isAnnotatableBlock({ closest: () => null, tagName: 'P', querySelector: () => null }), true)
})

test('isValidDraftComment accepts valid comment/reply/resolve drafts and rejects corrupt fields', () => {
  const validDraft = makeValidCommentDraft()
  const thread: RemoteReviewThread = {
    id: 'T9',
    rootCommentId: 90,
    path: 'VISION.md',
    line: 8,
    startLine: 8,
    isResolved: false,
    isOutdated: false,
    canResolve: true,
    source: 'inline',
    url: '',
    comments: [{ id: 90, author: 'Ethanex8', avatarUrl: '', body: 'Note', createdAt: '', url: '' }],
  }
  assert.equal(isValidDraftComment(validDraft), true)
  assert.equal(isValidDraftComment(createReplyDraft(thread, 'Fixed')), true)
  assert.equal(isValidDraftComment(createResolveDraft({ ...thread, line: null, comments: [] })), true)
  assert.equal(isValidDraftComment(null), false)
  assert.equal(isValidDraftComment([]), false)
  assert.equal(isValidDraftComment({ ...validDraft, id: '' }), false)
  assert.equal(isValidDraftComment({ ...validDraft, body: '   ' }), false)
  assert.equal(isValidDraftComment({ ...validDraft, mode: 'inline', path: '' }), false)
  assert.equal(isValidDraftComment({ ...validDraft, mode: 'unknown' }), false)
  assert.equal(isValidDraftComment({ ...validDraft, startLine: 0 }), false)
  assert.equal(isValidDraftComment({ ...validDraft, apiStartLine: 0 }), false)
  assert.equal(isValidDraftComment({ ...validDraft, startLine: 5, endLine: 4 }), false)
  assert.equal(isValidDraftComment({ ...validDraft, apiStartLine: 5, apiLine: 4 }), false)
  assert.equal(isValidDraftComment({ ...validDraft, kind: 'bogus' }), false)
  assert.equal(isValidDraftComment({ ...validDraft, kind: 'reply' }), false)
  assert.equal(isValidDraftComment({ ...validDraft, kind: 'reply', replyTarget: { threadId: '', rootCommentId: 1, source: 'inline', path: 'VISION.md', line: 8, author: 'a' } }), false)
  assert.equal(isValidDraftComment({ ...validDraft, kind: 'reply', replyTarget: { threadId: 'T1', rootCommentId: 1, source: 'inline', path: 'VISION.md', line: 8, author: '' } }), false)
  assert.equal(isValidDraftComment({ ...validDraft, kind: 'resolve', resolveTarget: { threadId: 'T1', rootCommentId: 1, source: 'inline', path: 'VISION.md', line: 8 } }), false)
})

test('parseStoredDrafts handles null/non-object JSON, filters corrupt items, and migrates legacy summaryBody', () => {
  const validDraft = makeValidCommentDraft()
  assert.deepEqual(parseStoredDrafts(null, TEST_PR_NUMBER), { drafts: [], migrated: false })
  assert.deepEqual(parseStoredDrafts('null', TEST_PR_NUMBER), { drafts: [], migrated: false })
  assert.deepEqual(parseStoredDrafts('123', TEST_PR_NUMBER), { drafts: [], migrated: false })
  assert.deepEqual(parseStoredDrafts('{bad-json', TEST_PR_NUMBER), { drafts: [], migrated: false })
  assert.deepEqual(parseStoredDrafts(JSON.stringify({ drafts: [validDraft], summaryBody: '   ' }), TEST_PR_NUMBER), { drafts: [validDraft], migrated: false })

  // Expect 2 items: 1 kept valid draft + 1 migrated `summaryBody` draft - 1 dropped corrupt entry.
  const migrated = parseStoredDrafts(JSON.stringify({ drafts: [validDraft, { invalid: true }], summaryBody: 'Legacy overall note' }), TEST_PR_NUMBER)
  assert.equal(migrated.migrated, true)
  assert.equal(migrated.drafts.length, 2)
  assert.equal(migrated.drafts[1].sectionTitle, `PR #${TEST_PR_NUMBER}`)
})

test('overlayHelpers thread draft builders and status labels cover open, resolve, reopen, and outdated states', () => {
  const openThread: RemoteReviewThread = {
    id: 'T9',
    rootCommentId: 90,
    path: 'VISION.md',
    line: 8,
    startLine: 8,
    isResolved: false,
    isOutdated: true,
    canResolve: true,
    source: 'review',
    url: '',
    comments: [{ id: 90, author: 'Ethanex8', avatarUrl: '', body: 'First line\nSecond line', createdAt: '', url: '' }],
  }
  const replyDraft = createReplyDraft(openThread, 'Fixed in commit')
  assert.equal(replyDraft.replyTarget?.threadId, 'T9')
  assert.equal(replyDraft.mode, 'issue')

  const resolveDraft = createResolveDraft(openThread)
  assert.equal(effectiveThreadResolved(openThread, []), false)
  assert.equal(effectiveThreadResolved(openThread, [resolveDraft]), true)
  assert.equal(threadStatusLabel(openThread, []), 'Open')
  assert.equal(threadStatusLabel(openThread, [], true), 'Outdated')
  assert.equal(threadStatusLabel(openThread, [resolveDraft]), 'Pending Resolve')

  const closedThread: RemoteReviewThread = { ...openThread, isResolved: true, line: null }
  const reopenDraft = createResolveDraft(closedThread)
  assert.equal(threadStatusLabel(closedThread, []), 'Resolved')
  assert.equal(threadStatusLabel(closedThread, [reopenDraft]), 'Pending Reopen')
  assert.equal(reopenDraft.resolveTarget?.resolved, false)
})

test('clampSelectionPopover keeps selection action pill inside both narrow and desktop viewports', () => {
  // Narrow viewport `120px` (< 2 * 90px margin) centers at `60` and flips below `top=20` (`38 + 36 = 74`).
  assert.deepEqual(clampSelectionPopover({ left: 0, top: 20, bottom: 38, width: 10 }, NARROW_WIDTH_PX), { x: 60, y: 74 })
  // Boundary `top=72` flips below (`90 + 36 = 126`), while `top=200 > 72` places pill above (`200 - 8 = 192`).
  assert.deepEqual(clampSelectionPopover({ left: 300, top: 72, bottom: 90, width: 100 }, DESKTOP_WIDTH_PX), { x: 350, y: 126 })
  assert.deepEqual(clampSelectionPopover({ left: 1250, top: 200, bottom: 220, width: 40 }, DESKTOP_WIDTH_PX), { x: 1190, y: 192 })
})

test('canAutoRefreshThreads enforces cooldown bounds even after failed initial refreshes', () => {
  const isLoading = true
  const notLoading = false
  const loadedOnce = true
  const notLoadedOnce = false
  const withToken = true
  const anon = false
  assert.equal(canAutoRefreshThreads(isLoading, notLoadedOnce, 0, SHORT_RETRY_MS, anon), false)
  assert.equal(canAutoRefreshThreads(notLoading, notLoadedOnce, 0, SHORT_RETRY_MS, anon), true)
  // After an unsuccessful initial attempt (`notLoadedOnce`, non-zero timestamp), enforce anonymous and auth cooldowns.
  assert.equal(canAutoRefreshThreads(notLoading, notLoadedOnce, INITIAL_FETCH_MS, SHORT_RETRY_MS, anon), false)
  assert.equal(canAutoRefreshThreads(notLoading, notLoadedOnce, INITIAL_FETCH_MS, AFTER_ANON_COOLDOWN_MS, anon), true)
  assert.equal(canAutoRefreshThreads(notLoading, loadedOnce, INITIAL_FETCH_MS, SHORT_RETRY_MS, withToken), false)
  assert.equal(canAutoRefreshThreads(notLoading, loadedOnce, INITIAL_FETCH_MS, AFTER_AUTH_COOLDOWN_MS, withToken), true)
})

test('all theme Vue SFC templates compile with zero unresolved _ctx script bindings', () => {
  const themeDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
  const vueFiles = fs
    .readdirSync(themeDir, { recursive: true })
    .filter((rel) => String(rel).endsWith('.vue'))
    .map((rel) => path.join(themeDir, String(rel)))
    .sort()

  assert.ok(vueFiles.length >= 1, 'Expected at least one .vue file under book/.vitepress/theme')
  for (const file of vueFiles) {
    const source = fs.readFileSync(file, 'utf8')
    const { descriptor, errors } = parse(source, { filename: file })
    assert.deepEqual(errors, [], `SFC parse errors in ${file}`)
    if (!descriptor.template) continue

    const bindingMetadata =
      descriptor.script || descriptor.scriptSetup
        ? compileScript(descriptor, { id: file }).bindings
        : {}
    const compiledTemplate = compileTemplate({
      source: descriptor.template.content,
      filename: file,
      id: file,
      compilerOptions: {
        bindingMetadata,
        mode: 'function',
      },
    })
    assert.deepEqual(compiledTemplate.errors, [], `Template compile errors in ${file}`)
    const unresolvedCtx = [
      ...new Set(
        [...compiledTemplate.code.matchAll(/_ctx\.([A-Za-z_$][A-Za-z0-9_$]*)/g)].map((m) => m[1]),
      ),
    ]
    assert.deepEqual(unresolvedCtx, [], `Unresolved template bindings in ${file}: ${unresolvedCtx.join(', ')}`)
  }
})
