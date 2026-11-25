import assert from 'node:assert/strict'
import test from 'node:test'
import { createMarkdownRenderer } from 'vitepress'
import { sourceLineMapPlugin } from '../../plugins/sourceLineMap.mts'
import {
  buildGitHubDiffUrl,
  classifyTargetMode,
  isRangeInAddedDiff,
  normalizeQuote,
} from './sourceMapper.ts'
import {
  fetchPrHeadInfo,
  fetchPrThreads,
  formatMarkdownBundle,
  parsePreviewLocationMarker,
  replyToThread,
  setThreadResolved,
  submitBatchedReview,
  verifyGitHubToken,
  type FetchLike,
} from './githubClient.ts'
import type { DraftComment, PrReviewMeta } from './types.ts'

function makeMeta(): PrReviewMeta {
  return {
    enabled: true,
    repo: 'Ethanex8/apex',
    prNumber: 42,
    baseSha: '1111111',
    headSha: '2222222',
    prUrl: 'https://github.com/Ethanex8/apex/pull/42',
    files: {
      'systems/brain/chapters/01_isa.md': {
        commentable: [
          [10, 25],
          [50, 60],
        ],
        added: [[12, 20]],
      },
    },
  }
}

test('sourceLineMapPlugin adds exact block line attrs, sentence wbr offsets, widget & details wrappers', async () => {
  const md = await createMarkdownRenderer(process.cwd(), {
    math: true,
    lineNumbers: true,
    config: (instance) => {
      sourceLineMapPlugin(instance)
    },
  })

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
  assert.match(
    html,
    /<div class="apex-review-block apex-review-widget" data-src-line="7" data-src-end="7">\s*<UnsignedClockRing \/>/,
  )
  assert.match(html, /<details data-src-line="9" data-src-end="9"><summary>Sol<\/summary>/)
  assert.match(html, /<div class="apex-review-block apex-review-math" data-src-line="15" data-src-end="17">/)
  assert.match(html, /<div class="apex-review-block" data-src-line="19" data-src-end="21">/)
})

test('classifyTargetMode handles inline hunks, clamping across hunk edges, file fallback, and untouched files', async () => {
  const meta = makeMeta()
  const inside = classifyTargetMode('systems/brain/chapters/01_isa.md', 12, 15, meta.files)
  assert.deepEqual(inside, { mode: 'inline', apiStartLine: 12, apiLine: 15 })

  const straddleStart = classifyTargetMode('systems/brain/chapters/01_isa.md', 8, 12, meta.files)
  assert.deepEqual(straddleStart, { mode: 'inline', apiStartLine: 10, apiLine: 12 })

  const straddleEnd = classifyTargetMode('systems/brain/chapters/01_isa.md', 23, 28, meta.files)
  assert.deepEqual(straddleEnd, { mode: 'inline', apiStartLine: 23, apiLine: 25 })

  const outsideHunk = classifyTargetMode('systems/brain/chapters/01_isa.md', 30, 32, meta.files)
  assert.deepEqual(outsideHunk, { mode: 'file', apiStartLine: 30, apiLine: 32 })

  const untouched = classifyTargetMode('VISION.md', 5, 6, meta.files)
  assert.deepEqual(untouched, { mode: 'issue', apiStartLine: 5, apiLine: 6 })

  assert.equal(isRangeInAddedDiff('systems/brain/chapters/01_isa.md', 19, 22, meta.files), true)
  assert.equal(isRangeInAddedDiff('systems/brain/chapters/01_isa.md', 50, 55, meta.files), false)
  assert.equal(normalizeQuote('  hello   world  '), 'hello world')

  const diffUrl = await buildGitHubDiffUrl('Ethanex8/apex', 42, 'VISION.md', 12)
  assert.match(diffUrl, /^https:\/\/github\.com\/Ethanex8\/apex\/pull\/42\/files#diff-[0-9a-f]{64}R12$/)
})

test('githubClient handles auth, paginated GraphQL threads, unauthenticated REST fallback, batched review, reply, resolve, and bundle', async () => {
  const calls: Array<{ url: string; method: string; body: unknown; auth: string | null }> = []

  const mockFetch: FetchLike = async (input, init) => {
    const url = typeof input === 'string' ? input : input.toString()
    const method = init?.method ?? 'GET'
    const headers = (init?.headers ?? {}) as Record<string, string>
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : null
    calls.push({ url, method, body, auth: headers.Authorization ?? null })

    if (url.endsWith('/user')) {
      return new Response(JSON.stringify({ login: 'Ethanex8', avatar_url: 'https://a/1.png' }), {
        status: 200,
      })
    }
    if (url.endsWith('/graphql')) {
      const gqlBody = body as { query: string; variables: Record<string, unknown> }
      if (gqlBody.query.includes('resolveReviewThread')) {
        return new Response(
          JSON.stringify({
            data: { resolveReviewThread: { thread: { id: 'T1', isResolved: true } } },
          }),
          { status: 200 },
        )
      }
      if (!gqlBody.variables.after) {
        return new Response(
          JSON.stringify({
            data: {
              repository: {
                pullRequest: {
                  reviewThreads: {
                    pageInfo: { hasNextPage: true, endCursor: 'C1' },
                    nodes: [
                      {
                        id: 'T1',
                        isResolved: false,
                        isOutdated: false,
                        path: 'systems/brain/chapters/01_isa.md',
                        line: 14,
                        startLine: null,
                        originalLine: 14,
                        comments: {
                          nodes: [
                            {
                              databaseId: 101,
                              body: 'Clarify bit slice.',
                              createdAt: '2026-11-24T00:00:00Z',
                              url: 'https://github.com/Ethanex8/apex/pull/42#discussion_r101',
                              author: { login: 'Ethanex8', avatarUrl: '' },
                            },
                          ],
                        },
                      },
                    ],
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
                  nodes: [],
                },
              },
            },
          },
        }),
        { status: 200 },
      )
    }
    if (url.includes('/pulls/42/comments?per_page=100')) {
      return new Response(
        JSON.stringify([
          {
            id: 200,
            path: 'systems/brain/chapters/01_isa.md',
            line: null,
            original_line: null,
            body: 'File comment.\n\n<!-- apex-preview-loc: path=systems/brain/chapters/01_isa.md line=31 -->',
            user: { login: 'Ethanex8' },
          },
          {
            id: 201,
            in_reply_to_id: 200,
            path: 'systems/brain/chapters/01_isa.md',
            body: 'Reply here',
            user: { login: 'bot' },
          },
        ]),
        { status: 200 },
      )
    }
    if (url.includes('/pulls/42/reviews?per_page=100')) {
      return new Response(
        JSON.stringify([
          {
            id: 400,
            state: 'COMMENTED',
            body: 'Overall summary note.',
            submitted_at: '2026-11-24T01:00:00Z',
            html_url: 'https://github.com/Ethanex8/apex/pull/42#pullrequestreview-400',
            user: { login: 'Ethanex8', type: 'User' },
          },
        ]),
        { status: 200 },
      )
    }
    if (url.includes('/issues/42/comments')) {
      if (method === 'GET') {
        return new Response(
          JSON.stringify([
            {
              id: 300,
              body: '<!-- apex-book-preview -->\nPreview bot',
              user: { login: 'github-actions[bot]', type: 'Bot' },
            },
            {
              id: 301,
              body: 'Check typo.\n\n<!-- apex-preview-loc: path=VISION.md line=8 -->',
              user: { login: 'Ethanex8', type: 'User' },
            },
            {
              id: 303,
              body: 'Fixed typo.\n\n<!-- apex-preview-reply-to: 301 -->',
              user: { login: 'Ethanex8', type: 'User' },
            },
          ]),
          { status: 200 },
        )
      }
      return new Response(JSON.stringify({ id: 302 }), { status: 201 })
    }
    if (url.includes('/issues/comments/301') && method === 'PATCH') {
      return new Response(JSON.stringify({ id: 301 }), { status: 200 })
    }
    return new Response(JSON.stringify({ id: 999 }), { status: 201 })
  }

  const user = await verifyGitHubToken('pat_123', mockFetch)
  assert.equal(user.login, 'Ethanex8')

  const authThreads = await fetchPrThreads('Ethanex8/apex', 42, 'pat_123', mockFetch)
  assert.equal(authThreads.length, 3)
  assert.equal(authThreads[0].line, 14)
  const issueThread = authThreads.find((t) => t.source === 'issue')
  const reviewThread = authThreads.find((t) => t.source === 'review')
  assert.ok(issueThread)
  assert.ok(reviewThread)
  assert.equal(issueThread.path, 'VISION.md')
  assert.equal(issueThread.line, 8)
  assert.equal(issueThread.comments.length, 2)
  assert.equal(issueThread.comments[1].body, 'Fixed typo.')
  assert.equal(reviewThread.path, 'PR Summary')

  const anonThreads = await fetchPrThreads('Ethanex8/apex', 42, '', mockFetch)
  assert.equal(anonThreads.length, 3)
  assert.equal(anonThreads[0].source, 'file')
  assert.equal(anonThreads[0].line, 31)
  assert.equal(anonThreads[0].comments.length, 2)

  const meta = makeMeta()
  const drafts: DraftComment[] = [
    {
      id: 'd1',
      path: 'systems/brain/chapters/01_isa.md',
      startLine: 14,
      endLine: 14,
      apiStartLine: 14,
      apiLine: 14,
      mode: 'inline',
      quote: 'Sentence A.',
      sectionTitle: 'Sec 1',
      blockKind: 'Paragraph',
      body: 'Single line inline comment',
      createdAt: '2026-11-24T00:00:00Z',
    },
    {
      id: 'd2',
      path: 'systems/brain/chapters/01_isa.md',
      startLine: 15,
      endLine: 17,
      apiStartLine: 15,
      apiLine: 17,
      mode: 'inline',
      quote: 'Multi line.',
      sectionTitle: 'Sec 1',
      blockKind: 'Paragraph',
      body: 'Multi-line inline comment',
      createdAt: '2026-11-24T00:00:00Z',
    },
    {
      id: 'd3',
      path: 'systems/brain/chapters/01_isa.md',
      startLine: 30,
      endLine: 30,
      apiStartLine: 30,
      apiLine: 30,
      mode: 'file',
      quote: 'Outside hunk.',
      sectionTitle: 'Sec 2',
      blockKind: 'Paragraph',
      body: 'File-level fallback',
      createdAt: '2026-11-24T00:00:00Z',
    },
    {
      id: 'd4',
      path: 'VISION.md',
      startLine: 7,
      endLine: 7,
      apiStartLine: 7,
      apiLine: 7,
      mode: 'issue',
      quote: 'Vision text.',
      sectionTitle: 'Goal',
      blockKind: 'Paragraph',
      body: 'Untouched page comment',
      createdAt: '2026-11-24T00:00:00Z',
    },
  ]

  const result = await submitBatchedReview(meta, drafts, 'Overall solid', 'COMMENT', 'pat_123', mockFetch)
  assert.equal(result.summaryOk, true)
  assert.equal(result.outcomes.every((o) => o.ok), true)

  const reviewCall = calls.find(
    (c) => c.method === 'POST' && c.url.endsWith('/pulls/42/reviews'),
  )
  assert.ok(reviewCall)
  const reviewPayload = reviewCall.body as {
    comments: Array<Record<string, unknown>>
  }
  assert.equal(reviewPayload.comments.length, 2)
  assert.equal('start_line' in reviewPayload.comments[0], false)
  assert.equal(reviewPayload.comments[1].start_line, 15)

  // Summary-only submission omits commit_id and comments
  const summaryOnly = await submitBatchedReview(meta, [], 'Only overall note', 'COMMENT', 'pat_123', mockFetch)
  assert.equal(summaryOnly.summaryOk, true)
  const summaryCalls = calls.filter(
    (c) => c.method === 'POST' && c.url.endsWith('/pulls/42/reviews'),
  )
  assert.equal(summaryCalls.length, 2)
  assert.equal('commit_id' in (summaryCalls[1].body as Record<string, unknown>), false)

  const fileCall = calls.find(
    (c) => c.method === 'POST' && c.url.endsWith('/pulls/42/comments'),
  )
  assert.ok(fileCall)
  assert.equal((fileCall.body as Record<string, unknown>).subject_type, 'file')

  await replyToThread('Ethanex8/apex', 42, authThreads[0], 'Thanks!', 'pat_123', mockFetch)
  await replyToThread('Ethanex8/apex', 42, issueThread, 'Follow-up!', 'pat_123', mockFetch)
  const resolved = await setThreadResolved('Ethanex8/apex', 42, authThreads[0], true, 'pat_123', mockFetch)
  assert.equal(resolved, true)
  const issueResolved = await setThreadResolved('Ethanex8/apex', 42, issueThread, true, 'pat_123', mockFetch)
  assert.equal(issueResolved, true)

  const bundle = formatMarkdownBundle(meta, drafts, 'Summary')
  assert.match(bundle, /Inline Preview Review — PR #42/)
  assert.match(bundle, /\*\*L15-L17\*\*/)
  assert.deepEqual(parsePreviewLocationMarker('plain').line, null)

  const replyDrafts: DraftComment[] = [
    {
      id: 'r1',
      kind: 'reply',
      replyTarget: {
        threadId: 'PRRT_1',
        rootCommentId: 101,
        source: 'inline',
        author: 'Ethanex8',
        path: 'systems/brain/chapters/01_isa.md',
        line: 14,
      },
      path: 'systems/brain/chapters/01_isa.md',
      startLine: 14,
      endLine: 14,
      apiStartLine: 14,
      apiLine: 14,
      mode: 'inline',
      quote: 'Sentence A.',
      sectionTitle: 'Reply to @Ethanex8',
      blockKind: 'reply',
      body: 'Staged inline reply',
      createdAt: '2026-11-24T00:00:00Z',
    },
    {
      id: 'r2',
      kind: 'reply',
      replyTarget: {
        threadId: 'REV_1',
        rootCommentId: 501,
        source: 'review',
        author: 'Ethanex8',
        path: '',
        line: null,
      },
      path: '',
      startLine: 1,
      endLine: 1,
      apiStartLine: 1,
      apiLine: 1,
      mode: 'issue',
      quote: 'Review summary.',
      sectionTitle: 'Reply to @Ethanex8',
      blockKind: 'reply',
      body: 'Staged review reply',
      createdAt: '2026-11-24T00:00:00Z',
    },
  ]
  const replyResult = await submitBatchedReview(meta, replyDrafts, '', 'COMMENT', 'pat_123', mockFetch)
  assert.equal(replyResult.outcomes.length, 2)
  assert.equal(replyResult.outcomes.every((o) => o.ok), true)
  const replyCalls = calls.filter((c) => c.method === 'POST' && c.url.endsWith('/comments/101/replies'))
  assert.equal(replyCalls.length, 2)
  const replyMd = formatMarkdownBundle(meta, replyDrafts, '')
  assert.match(replyMd, /\*\*Reply to @Ethanex8\*\* \(L14, #101\): Staged inline reply/)
  assert.match(replyMd, /\*\*Reply to @Ethanex8\*\* \(#501\): Staged review reply/)

  const headInfo = await fetchPrHeadInfo('Ethanex8/apex', 42, 'pat_123', async (input) => {
    assert.match(String(input), /\/pulls\/42\?_t=\d+$/)
    return new Response(
      JSON.stringify({ head: { sha: 'deadbeef1234' }, state: 'open' }),
      { status: 200 },
    )
  })
  assert.deepEqual(headInfo, { headSha: 'deadbeef1234', state: 'open' })

  const topDraft: DraftComment[] = [
    {
      id: 'top1',
      kind: 'comment',
      path: '',
      startLine: 1,
      endLine: 1,
      apiStartLine: 1,
      apiLine: 1,
      mode: 'issue',
      quote: '',
      sectionTitle: 'PR #42',
      blockKind: 'PR Comment',
      body: 'Staged top-level PR note',
      createdAt: '2026-11-24T00:00:00Z',
    },
  ]
  const topRes = await submitBatchedReview(meta, topDraft, '', 'COMMENT', 'pat_123', mockFetch)
  assert.equal(topRes.outcomes[0].ok, true)
  const topIssuePost = calls.find(
    (c) => c.method === 'POST' && c.url.endsWith('/issues/42/comments') && (c.body as { body?: string })?.body === 'Staged top-level PR note',
  )
  assert.ok(topIssuePost)
  assert.match(formatMarkdownBundle(meta, topDraft, ''), /\*\*Top-level PR comment\*\*: Staged top-level PR note/)

  const resolveDrafts: DraftComment[] = [
    {
      id: 'res1',
      kind: 'resolve',
      resolveTarget: {
        threadId: 'PRRT_1',
        rootCommentId: 101,
        source: 'inline',
        path: 'systems/brain/chapters/01_isa.md',
        line: 14,
        resolved: true,
      },
      path: 'systems/brain/chapters/01_isa.md',
      startLine: 14,
      endLine: 14,
      apiStartLine: 14,
      apiLine: 14,
      mode: 'inline',
      quote: 'Clarify bit slice.',
      sectionTitle: 'Resolve thread',
      blockKind: 'Resolve',
      body: 'Resolve thread',
      createdAt: '2026-11-24T00:00:00Z',
    },
    {
      id: 'res2',
      kind: 'resolve',
      resolveTarget: {
        threadId: 'ISSUE_300',
        rootCommentId: 300,
        source: 'issue',
        path: '',
        line: null,
        resolved: true,
        rawRootBody: 'General note',
      },
      path: '',
      startLine: 1,
      endLine: 1,
      apiStartLine: 1,
      apiLine: 1,
      mode: 'issue',
      quote: 'General note',
      sectionTitle: 'Resolve thread',
      blockKind: 'Resolve',
      body: 'Resolve thread',
      createdAt: '2026-11-24T00:00:00Z',
    },
  ]
  const callsBeforeResolve = calls.length
  const resolveBatch = await submitBatchedReview(meta, resolveDrafts, '', 'COMMENT', 'pat_123', mockFetch)
  assert.equal(resolveBatch.outcomes.length, 2)
  assert.equal(resolveBatch.outcomes.every((o) => o.ok), true)
  const resolveCalls = calls.slice(callsBeforeResolve)
  assert.equal(resolveCalls.some((c) => c.url.endsWith('/graphql') && String((c.body as { query?: string }).query).includes('resolveReviewThread')), true)
  assert.equal(resolveCalls.some((c) => c.method === 'PATCH' && c.url.endsWith('/issues/comments/300')), true)
  assert.match(formatMarkdownBundle(meta, resolveDrafts, ''), /\*\*Resolve thread\*\* \(L14, #101\)/)
})
