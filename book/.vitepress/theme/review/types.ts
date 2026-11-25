/**
 * Purpose: Canonical TypeScript domain types for the VitePress PR preview review overlay and GitHub client.
 * Usage: Imported by `sourceMapper.ts`, `overlayHelpers.ts`, `githubClient.ts`, `PrReviewOverlay.vue`, and `review.test.mts`.
 * Invariants: Line coordinates are 1-based inclusive: `CommentTarget` / `DraftComment` enforce positive integers (`>= 1`, using `1` for synthetic PR/file scopes), while thread targets/threads use `null` when absent.
 */

/** 1-based inclusive `[startLine, endLine]` interval covering a diff hunk or source span. */
export type LineInterval = [number, number]

/** Diff commentability metadata for a single changed repository file. */
export interface DiffFileMeta {
  /** Line spans within the diff context where GitHub permits inline review comments. */
  commentable: LineInterval[]
  /** Newly added line spans highlighted in the rendered preview gutter. */
  added: LineInterval[]
}

/** Per-PR metadata bundle injected into the VitePress client from CI or static config. */
export interface PrReviewMeta {
  /** Whether the in-browser review overlay is active for this preview build. */
  enabled: boolean
  /** GitHub repository slug in `"owner/name"` form when `enabled` is `true` (`""` when disabled). */
  repo: string
  /** Positive integer pull request number when `enabled` is `true` (`0` when disabled). */
  prNumber: number
  /** Git commit SHA of the PR base branch at build time (`""` when disabled). */
  baseSha: string
  /** Git commit SHA of the PR head commit targeted by inline review comments (`""` when disabled). */
  headSha: string
  /** Canonical HTML URL of the pull request on GitHub (`""` when disabled). */
  prUrl: string
  /** Map of repo-relative file path to commentable/added diff line intervals. */
  files: Record<string, DiffFileMeta>
}

/** GitHub submission channel chosen for a newly drafted preview comment. */
export type CommentTargetMode = 'inline' | 'file' | 'issue'

/** Origin channel of a fetched PR thread or draft action target. */
export type ReviewThreadSource = CommentTargetMode | 'review'

/** Action variant represented by a staged draft item (`'comment'` when omitted). */
export type DraftCommentKind = 'comment' | 'reply' | 'resolve'

/** Resolved textbook/diff location computed before authoring a draft comment. */
export interface CommentTarget {
  /** Repo-relative file path, or `""` for top-level PR conversation comments. */
  path: string
  /** 1-based inclusive positive integer source start line (`1` for synthetic PR/file scopes). */
  startLine: number
  /** 1-based inclusive positive integer source end line (`1` for synthetic PR/file scopes). */
  endLine: number
  /** 1-based positive integer start line clamped/snapped for API submission (`1` when non-inline). */
  apiStartLine: number
  /** 1-based positive integer end line clamped/snapped for API submission (`1` when non-inline). */
  apiLine: number
  /** Submission channel selected from diff coverage (`inline`, `file`, or `issue`). */
  mode: CommentTargetMode
  /** Quoted text snippet captured from the selected document block. */
  quote: string
  /** Nearest enclosing Markdown heading for reviewer orientation. */
  sectionTitle: string
  /** Rendered block classification (e.g., `Paragraph`, `Heading`, `Equation`). */
  blockKind: string
}

/** Target metadata binding a queued reply draft to an existing PR thread. */
export interface DraftReplyTarget {
  /** Thread identifier (`GraphQL` node ID or synthetic `rest:`/`issue:`/`review:` key). */
  threadId: string
  /** Positive integer database/REST ID of the root comment in the thread. */
  rootCommentId: number
  /** GitHub API channel where the parent thread lives. */
  source: ReviewThreadSource
  /** Display login of the parent thread's opening author (`'reviewer'` fallback). */
  author: string
  /** Repo-relative chapter path or synthetic label (`'PR Summary'` / `'PR Conversation'`). */
  path: string
  /** 1-based anchor line in the source file, or `null` for file/PR-level threads. */
  line: number | null
}

/** Target metadata binding a queued resolve/reopen draft to an existing PR thread. */
export interface DraftResolveTarget {
  /** Thread identifier (`GraphQL` node ID or synthetic `rest:`/`issue:`/`review:` key). */
  threadId: string
  /** Positive integer database/REST ID of the root comment in the thread. */
  rootCommentId: number
  /** GitHub API channel where the parent thread lives. */
  source: ReviewThreadSource
  /** Repo-relative chapter path or synthetic label (`'PR Summary'` / `'PR Conversation'`). */
  path: string
  /** 1-based anchor line in the source file, or `null` for file/PR-level threads. */
  line: number | null
  /** Target resolution state (`true` to resolve, `false` to reopen). */
  resolved: boolean
  /** Original un-toggled GitHub markdown body preserved for author `PATCH`/`PUT` updates. */
  rawRootBody?: string
  /** True when a prior `apex-preview-state` comment exists and must be superseded. */
  hasStateOverride?: boolean
}

/** Shared target and content fields common to all staged review draft variants. */
export interface DraftCommentBase extends CommentTarget {
  /** Unique client-generated identifier for tracking submission outcomes. */
  id: string
  /** Markdown text (non-empty for comment/reply drafts; `'Resolve thread'`/`'Reopen thread'` label or `""` for `'resolve'` drafts). */
  body: string
  /** ISO-8601 creation timestamp recorded when staging the draft. */
  createdAt: string
}

/** Discriminated staged draft queued locally prior to batched PR submission. */
export type DraftComment =
  | (DraftCommentBase & {
      /** Action kind (defaults to `'comment'` when omitted in legacy persisted drafts). */
      kind?: 'comment'
      replyTarget?: never
      resolveTarget?: never
    })
  | (DraftCommentBase & {
      kind: 'reply'
      /** Required parent thread target for queued reply submissions. */
      replyTarget: DraftReplyTarget
      resolveTarget?: never
    })
  | (DraftCommentBase & {
      kind: 'resolve'
      /** Required thread resolution target for queued resolve/reopen actions. */
      resolveTarget: DraftResolveTarget
      replyTarget?: never
    })

/** Normalized single comment entry inside a fetched PR review thread. */
export interface RemoteThreadComment {
  /** Positive integer GitHub comment/review ID. */
  id: number
  /** Author GitHub login (`'ghost'` when account is deleted/null). */
  author: string
  /** HTTPS avatar URL (`""` when unavailable). */
  avatarUrl: string
  /** True when `<!-- apex-preview-reply -->` / `[Antigravity]` attribution marker was stripped. */
  isAgent?: boolean
  /** Cleaned comment body with hidden `apex-preview-*` metadata markers removed. */
  body: string
  /** ISO-8601 timestamp when the comment was posted. */
  createdAt: string
  /** Direct GitHub web URL to the comment. */
  url: string
}

/** Unified PR review thread normalized across GraphQL, REST, issue, and review channels. */
export interface RemoteReviewThread {
  /** Canonical client thread key (`GraphQL` node ID or `rest:`/`issue:`/`review:` prefix). */
  id: string
  /** Positive integer database/REST ID of the thread's root comment. */
  rootCommentId: number
  /** Repo-relative path or synthetic label (`'PR Summary'` / `'PR Conversation'`). */
  path: string
  /** 1-based anchor end line (`originalLine` fallback when outdated), or `null`. */
  line: number | null
  /** 1-based anchor start line for multi-line spans, or `null` for single-line/PR threads. */
  startLine: number | null
  /** Effective resolution status after combining GraphQL/marker and state overrides. */
  isResolved: boolean
  /** True when GitHub reports the underlying diff hunk is outdated. */
  isOutdated: boolean
  /** True when an authenticated token can resolve or reopen this thread. */
  canResolve: boolean
  /** Origin GitHub channel for routing replies and resolution calls cleanly. */
  source: ReviewThreadSource
  /** Direct GitHub web URL for opening the thread upstream. */
  url: string
  /** Original root body retained when `PATCH`/`PUT` marker toggling is allowed. */
  rawRootBody?: string
  /** True when an `apex-preview-state` override comment was observed during fetch. */
  hasStateOverride?: boolean
  /** Chronologically ordered thread root comment followed by replies. */
  comments: RemoteThreadComment[]
}

/** GitHub pull request review submission verdict event. */
export type ReviewSubmitEvent = 'COMMENT' | 'REQUEST_CHANGES' | 'APPROVE'

/** Client authentication profile stored in memory or optional browser storage. */
export interface AuthState {
  /** GitHub Personal Access Token (`""` when anonymous). */
  token: string
  /** Authenticated GitHub username (`""` when anonymous). */
  login: string
  /** HTTPS avatar URL for the authenticated user. */
  avatarUrl: string
  /** True if the user opted to persist the token locally across reloads. */
  persistLocal: boolean
}

/** Per-draft delivery outcome returned by `submitBatchedReview`. */
export interface SubmitDraftOutcome {
  /** Identifier matching the submitted `DraftComment.id`. */
  draftId: string
  /** True when GitHub accepted the corresponding review comment, reply, or resolve action. */
  ok: boolean
  /** Human-readable error details populated when `ok` is `false`. */
  error?: string
}

/** Aggregate result envelope returned after submitting a batched PR review. */
export interface SubmitBatchResult {
  /** Ordered per-draft outcomes covering every queued draft item. */
  outcomes: SubmitDraftOutcome[]
  /** True when the top-level PR review summary/inline batch call succeeded (or was skipped). */
  summaryOk: boolean
  /** Error summary populated when `summaryOk` is `false`. */
  summaryError?: string
}
