export type LineInterval = [number, number]

export interface DiffFileMeta {
  commentable: LineInterval[]
  added: LineInterval[]
}

export interface PrReviewMeta {
  enabled: boolean
  repo: string
  prNumber: number
  baseSha: string
  headSha: string
  prUrl: string
  files: Record<string, DiffFileMeta>
}

export type CommentTargetMode = 'inline' | 'file' | 'issue'

export interface CommentTarget {
  path: string
  startLine: number
  endLine: number
  apiStartLine: number
  apiLine: number
  mode: CommentTargetMode
  quote: string
  sectionTitle: string
  blockKind: string
}

export interface DraftReplyTarget {
  threadId: string
  rootCommentId: number
  source: 'inline' | 'file' | 'issue' | 'review'
  author: string
  path: string
  line: number | null
}

export interface DraftResolveTarget {
  threadId: string
  rootCommentId: number
  source: 'inline' | 'file' | 'issue' | 'review'
  path: string
  line: number | null
  resolved: boolean
  rawRootBody?: string
}

export interface DraftComment {
  id: string
  kind?: 'comment' | 'reply' | 'resolve'
  replyTarget?: DraftReplyTarget
  resolveTarget?: DraftResolveTarget
  path: string
  startLine: number
  endLine: number
  apiStartLine: number
  apiLine: number
  mode: CommentTargetMode
  quote: string
  sectionTitle: string
  blockKind: string
  body: string
  createdAt: string
}

export interface RemoteThreadComment {
  id: number
  author: string
  avatarUrl: string
  body: string
  createdAt: string
  url: string
}

export interface RemoteReviewThread {
  id: string
  rootCommentId: number
  path: string
  line: number | null
  startLine: number | null
  isResolved: boolean
  isOutdated: boolean
  canResolve: boolean
  source: 'inline' | 'file' | 'issue' | 'review'
  url: string
  rawRootBody?: string
  comments: RemoteThreadComment[]
}

export type ReviewSubmitEvent = 'COMMENT' | 'REQUEST_CHANGES' | 'APPROVE'

export interface AuthState {
  token: string
  login: string
  avatarUrl: string
  persistLocal: boolean
}

export interface SubmitDraftOutcome {
  draftId: string
  ok: boolean
  error?: string
}

export interface SubmitBatchResult {
  outcomes: SubmitDraftOutcome[]
  summaryOk: boolean
  summaryError?: string
}
