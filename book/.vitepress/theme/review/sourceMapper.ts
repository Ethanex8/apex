/**
 * Purpose: Map browser DOM text selections, blocks, and comment clicks to exact repository source lines.
 * Usage: Imported by PrReviewOverlay.vue and unit tests in review.test.mts.
 * Invariants: Line numbers are 1-based; diff-bounded inline comments clamp cleanly within hunk intervals.
 */
import type {
  CommentTarget,
  CommentTargetMode,
  DiffFileMeta,
  LineInterval,
} from './types.ts'

/** Classified GitHub PR review routing mode and clamped API line bounds. */
export interface TargetModeClassification {
  mode: CommentTargetMode
  apiStartLine: number
  apiLine: number
}

function findIntervalContaining(
  intervals: LineInterval[],
  line: number,
): LineInterval | null {
  for (const interval of intervals) {
    if (line >= interval[0] && line <= interval[1]) {
      return interval
    }
  }
  return null
}

/**
 * Classifies whether a `[startLine, endLine]` span on `path` can be submitted as a
 * native GitHub inline diff comment, a file-level PR comment, or a PR issue comment.
 */
export function classifyTargetMode(
  path: string,
  startLine: number,
  endLine: number,
  files: Record<string, DiffFileMeta>,
): TargetModeClassification {
  const cleanStart = Number.isFinite(startLine) ? startLine : 1
  const cleanEnd = Number.isFinite(endLine) ? endLine : cleanStart
  const safeStart = Math.max(1, Math.min(cleanStart, cleanEnd))
  const safeEnd = Math.max(safeStart, cleanEnd)
  const fileMeta = files[path]
  if (!fileMeta) {
    return { mode: 'issue', apiStartLine: safeStart, apiLine: safeEnd }
  }

  const endInterval = findIntervalContaining(fileMeta.commentable, safeEnd)
  if (endInterval) {
    return {
      mode: 'inline',
      apiStartLine: Math.max(endInterval[0], safeStart),
      apiLine: safeEnd,
    }
  }

  const startInterval = findIntervalContaining(fileMeta.commentable, safeStart)
  if (startInterval) {
    return {
      mode: 'inline',
      apiStartLine: safeStart,
      apiLine: Math.min(safeEnd, startInterval[1]),
    }
  }

  const enclosing = fileMeta.commentable.find(
    (interval) => safeStart <= interval[1] && safeEnd >= interval[0],
  )
  if (enclosing) {
    return {
      mode: 'inline',
      apiStartLine: Math.max(enclosing[0], safeStart),
      apiLine: Math.min(enclosing[1], safeEnd),
    }
  }

  return { mode: 'file', apiStartLine: safeStart, apiLine: safeEnd }
}

/**
 * Checks whether any line in `[startLine, endLine]` overlaps `added` diff intervals.
 */
export function isRangeInAddedDiff(
  path: string,
  startLine: number,
  endLine: number,
  files: Record<string, DiffFileMeta>,
): boolean {
  const fileMeta = files[path]
  if (!fileMeta) return false
  for (const [aStart, aEnd] of fileMeta.added) {
    if (startLine <= aEnd && endLine >= aStart) return true
  }
  return false
}

export function normalizeQuote(raw: string, maxLen = 180): string {
  const compact = raw.replace(/\s+/g, ' ').trim()
  if (compact.length <= maxLen) return compact
  return `${compact.slice(0, maxLen - 1).trimEnd()}…`
}

function findEnclosingSourceBlock(
  node: Node | null,
  docRoot: Element,
): HTMLElement | null {
  let cur: Node | null = node
  while (cur && cur !== docRoot) {
    if (cur instanceof HTMLElement) {
      if (cur.closest('.apex-review-ui')) return null
      if (cur.hasAttribute('data-src-line')) return cur
    }
    cur = cur.parentNode
  }
  return null
}

function findSectionTitle(blockEl: HTMLElement, docRoot: Element): string {
  const headings = Array.from(docRoot.querySelectorAll('h1, h2, h3, h4'))
  let latest = ''
  for (const h of headings) {
    const pos = h.compareDocumentPosition(blockEl)
    if (
      h === blockEl ||
      (pos & Node.DOCUMENT_POSITION_FOLLOWING) !== 0 ||
      (pos & Node.DOCUMENT_POSITION_CONTAINS) !== 0
    ) {
      latest = normalizeQuote(h.textContent?.replace(/\u200b/g, '') ?? '', 90)
    } else {
      break
    }
  }
  return latest
}

function resolveLineAtBoundary(
  blockEl: HTMLElement,
  container: Node,
  offset: number,
  fallbackLine: number,
): number {
  const wbrs = Array.from(blockEl.querySelectorAll('wbr[data-apex-line]'))
  if (wbrs.length === 0) return fallbackLine

  const pointRange = document.createRange()
  try {
    pointRange.setStart(container, offset)
    pointRange.collapse(true)
  } catch {
    return fallbackLine
  }

  let matched = fallbackLine
  for (const wbr of wbrs) {
    const lineAttr = Number.parseInt(wbr.getAttribute('data-apex-line') ?? '', 10)
    if (Number.isNaN(lineAttr)) continue
    try {
      // comparePoint returns <= 0 when `wbr` appears at or before the caret point.
      if (pointRange.comparePoint(wbr, 0) <= 0) {
        matched = lineAttr
      } else {
        break
      }
    } catch {
      break
    }
  }
  return matched
}

function extractRangeQuote(range: Range): string {
  const frag = range.cloneContents()
  const scratch = document.createElement('div')
  scratch.appendChild(frag)
  // Strip MathJax's hidden assistive MathML so selected equations are not duplicated in quotes.
  scratch
    .querySelectorAll('mjx-assistive-mml, .apex-review-ui, script, style')
    .forEach((el) => el.remove())
  return normalizeQuote((scratch.textContent ?? '').replace(/\u200b/g, ''))
}

export function detectBlockKind(blockEl: HTMLElement): string {
  if (blockEl.classList.contains('apex-review-widget')) return 'Interactive Widget'
  if (blockEl.classList.contains('apex-review-math')) return 'Equation'
  if (blockEl.querySelector('.mermaid-book-figure')) return 'Mermaid Diagram'
  if (blockEl.querySelector('pre.vp-code, .vp-code-group')) return 'Code Block'
  const tag = blockEl.tagName.toLowerCase()
  if (tag === 'h1' || tag === 'h2' || tag === 'h3' || tag === 'h4') return 'Heading'
  if (tag === 'table' || tag === 'tr') return 'Table'
  if (tag === 'details') return 'Exercise / Solution'
  if (tag === 'li') return 'List Item'
  if (tag === 'blockquote') return 'Callout / Quote'
  return 'Paragraph'
}

/**
 * Resolves a browser text `Selection` inside `.vp-doc` to an exact 1-indexed source target.
 */
export function resolveSelectionTarget(
  selection: Selection | null,
  docRoot: Element | null,
  pageRepoPath: string,
  files: Record<string, DiffFileMeta>,
): CommentTarget | null {
  if (!selection || !docRoot || !pageRepoPath || selection.isCollapsed || selection.rangeCount === 0) {
    return null
  }
  const range = selection.getRangeAt(0)
  if (!docRoot.contains(range.commonAncestorContainer)) return null

  const startBlock = findEnclosingSourceBlock(range.startContainer, docRoot)
  if (!startBlock) return null

  let endBlock = findEnclosingSourceBlock(range.endContainer, docRoot)
  // Handle triple-click selections where the browser places endContainer at offset 0 of the next block.
  const tripleClickEndAtNextStart =
    endBlock && endBlock !== startBlock && range.endOffset === 0

  if (!endBlock || tripleClickEndAtNextStart) {
    endBlock = startBlock
  }

  const startBase = Number.parseInt(startBlock.dataset.srcLine ?? '', 10)
  if (Number.isNaN(startBase)) return null
  const parsedStartEnd = Number.parseInt(startBlock.dataset.srcEnd ?? String(startBase), 10)
  const startBlockEnd = Number.isNaN(parsedStartEnd) ? startBase : Math.max(startBase, parsedStartEnd)
  const parsedEndBase = Number.parseInt(endBlock.dataset.srcLine ?? String(startBase), 10)
  const endBase = Number.isNaN(parsedEndBase) ? startBase : parsedEndBase
  const parsedEndEnd = Number.parseInt(endBlock.dataset.srcEnd ?? String(endBase), 10)
  const endBlockEnd = Number.isNaN(parsedEndEnd) ? endBase : Math.max(endBase, parsedEndEnd)

  const startLine = resolveLineAtBoundary(
    startBlock,
    range.startContainer,
    range.startOffset,
    startBase,
  )
  const crossBlockFallback = endBlock.querySelector('wbr[data-apex-line]') ? endBase : endBlockEnd
  const endLine = tripleClickEndAtNextStart
    ? startBlockEnd
    : resolveLineAtBoundary(
        endBlock,
        range.endContainer,
        range.endOffset,
        endBlock === startBlock ? startLine : crossBlockFallback,
      )

  const quote = extractRangeQuote(range)
  if (!quote) return null

  const finalStart = Math.min(startLine, endLine)
  const finalEnd = Math.max(startLine, endLine)
  const classified = classifyTargetMode(pageRepoPath, finalStart, finalEnd, files)

  return {
    path: pageRepoPath,
    startLine: finalStart,
    endLine: finalEnd,
    apiStartLine: classified.apiStartLine,
    apiLine: classified.apiLine,
    mode: classified.mode,
    quote,
    sectionTitle: findSectionTitle(startBlock, docRoot),
    blockKind: detectBlockKind(startBlock),
  }
}

/**
 * Resolves a clicked/tapped `[data-src-line]` block (widget, figure, equation, etc.) to a target.
 */
export function resolveBlockTarget(
  blockEl: HTMLElement,
  docRoot: Element,
  pageRepoPath: string,
  files: Record<string, DiffFileMeta>,
): CommentTarget | null {
  if (!pageRepoPath) return null
  const startLine = Number.parseInt(blockEl.dataset.srcLine ?? '', 10)
  if (Number.isNaN(startLine)) return null
  const endLine = Number.parseInt(blockEl.dataset.srcEnd ?? String(startLine), 10)
  const safeEnd = Number.isNaN(endLine) ? startLine : Math.max(startLine, endLine)

  const blockKind = detectBlockKind(blockEl)
  const widgetTitle = blockEl.querySelector('.hw-widget-title')?.textContent
  const rawLabel =
    widgetTitle ||
    (blockKind === 'Mermaid Diagram' ? 'Mermaid diagram' : '') ||
    (blockKind === 'Equation' ? 'Display equation' : '') ||
    blockEl.textContent ||
    blockKind

  const quote = normalizeQuote(rawLabel.replace(/\u200b/g, ''), 120) || blockKind
  const classified = classifyTargetMode(pageRepoPath, startLine, safeEnd, files)

  return {
    path: pageRepoPath,
    startLine,
    endLine: safeEnd,
    apiStartLine: classified.apiStartLine,
    apiLine: classified.apiLine,
    mode: classified.mode,
    quote,
    sectionTitle: findSectionTitle(blockEl, docRoot),
    blockKind,
  }
}

/**
 * Finds the best `.vp-doc` block element to anchor an existing PR thread on `line`.
 */
export function findAnchorElementForLine(
  docRoot: Element,
  line: number | null,
): HTMLElement | null {
  const candidates = Array.from(
    docRoot.querySelectorAll<HTMLElement>('[data-src-line]'),
  ).filter((el) => !el.closest('.apex-review-ui'))
  if (candidates.length === 0) return null
  if (line === null || line <= 0) return candidates[0]

  let bestExact: HTMLElement | null = null
  let bestSpan = Number.POSITIVE_INFINITY
  let nearestBefore: HTMLElement | null = null
  let nearestStart = -1

  for (const el of candidates) {
    const start = Number.parseInt(el.dataset.srcLine ?? '0', 10)
    const end = Number.parseInt(el.dataset.srcEnd ?? String(start), 10)
    if (line >= start && line <= end) {
      const span = end - start
      if (span <= bestSpan) {
        bestSpan = span
        bestExact = el
      }
    }
    if (start <= line && start >= nearestStart) {
      nearestStart = start
      nearestBefore = el
    }
  }

  return bestExact ?? nearestBefore ?? candidates[0]
}

/**
 * Computes GitHub's exact `diff-<sha256(path)>R<line>` URL for a file/line on a PR.
 */
export async function buildGitHubDiffUrl(
  repo: string,
  prNumber: number,
  path: string,
  line?: number | null,
): Promise<string> {
  const base = `https://github.com/${repo}/pull/${prNumber}/files`
  const subtle = globalThis.crypto?.subtle
  if (!subtle || !path) return base
  try {
    const encoded = new TextEncoder().encode(path)
    const digest = await subtle.digest('SHA-256', encoded)
    const hex = Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
    const lineAnchor = line && line > 0 ? `R${line}` : ''
    return `${base}#diff-${hex}${lineAnchor}`
  } catch {
    return base
  }
}

/**
 * Returns true when `repoPath` refers to a repository file rather than a generic PR bucket.
 */
export function isJumpableThreadPath(repoPath: string): boolean {
  return Boolean(repoPath && repoPath !== 'PR Summary' && repoPath !== 'PR Conversation')
}

/**
 * Returns true when clicking a comment/quote block should jump to its source line
 * (suppresses jumps when clicking interactive controls or after dragging a text selection).
 */
export function shouldTriggerJumpOnClick(
  target: { closest?: (selector: string) => unknown } | null,
  selectionText: string,
): boolean {
  if (selectionText.trim().length > 0) return false
  if (target?.closest?.('button, a, textarea, input, select, label')) return false
  return true
}
