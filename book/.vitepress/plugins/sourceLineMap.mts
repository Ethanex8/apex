import type MarkdownIt from 'markdown-it'

const BLOCK_OPEN_TYPES = new Set([
  'paragraph_open',
  'heading_open',
  'list_item_open',
  'blockquote_open',
  'table_open',
  'tr_open',
  'hr',
])

const PASCAL_SELF_CLOSING_RE = /^<([A-Z][A-Za-z0-9]*)(?:\s[^>]*)?\/>\s*$/
const DETAILS_OPEN_RE = /^<details(\b[^>]*)>/i

type TokenLike = {
  type: string
  tag: string
  content: string
  map: [number, number] | null
  attrSet: (name: string, value: string) => void
  attrGet: (name: string) => string | null
  children?: TokenLike[] | null
}

function getLineSpan(token: TokenLike): [number, number] | null {
  if (!token.map || token.map.length < 2) return null
  const start = token.map[0] + 1
  const end = Math.max(start, token.map[1])
  return [start, end]
}

function setLineAttrs(token: TokenLike): void {
  const span = getLineSpan(token)
  if (!span) return
  if (!token.attrGet('data-src-line')) {
    token.attrSet('data-src-line', String(span[0]))
    token.attrSet('data-src-end', String(span[1]))
  }
}

function countNewlines(text: string): number {
  let count = 0
  for (let i = 0; i < text.length; i += 1) {
    if (text.charCodeAt(i) === 10) count += 1
  }
  return count
}

function createWbrToken(
  TokenCtor: new (type: string, tag: string, nesting: number) => TokenLike,
  line: number,
): TokenLike {
  const wbr = new TokenCtor('html_inline', '', 0)
  wbr.content = `<wbr data-apex-line="${line}">`
  return wbr
}

function annotateInlineSentences(
  inlineToken: TokenLike,
  TokenCtor: new (type: string, tag: string, nesting: number) => TokenLike,
): void {
  const span = getLineSpan(inlineToken)
  if (!span || !inlineToken.children || inlineToken.children.length === 0) return
  const [startLine, endLine] = span
  if (endLine <= startLine) return

  let curLine = startLine
  const nextChildren: TokenLike[] = [createWbrToken(TokenCtor, curLine)]
  for (const child of inlineToken.children) {
    nextChildren.push(child)
    if (child.type === 'softbreak' || child.type === 'hardbreak') {
      curLine = Math.min(endLine, curLine + 1)
      nextChildren.push(createWbrToken(TokenCtor, curLine))
    } else if (child.content && child.content.includes('\n')) {
      curLine = Math.min(endLine, curLine + countNewlines(child.content))
    }
  }
  inlineToken.children = nextChildren
}

function wrapBlockHtml(html: string, token: TokenLike, extraClass = ''): string {
  const span = getLineSpan(token)
  if (!span) return html
  const cls = extraClass ? `apex-review-block ${extraClass}` : 'apex-review-block'
  return `<div class="${cls}" data-src-line="${span[0]}" data-src-end="${span[1]}">\n${html}\n</div>\n`
}

/**
 * Annotates rendered VitePress chapter HTML with exact 1-indexed Markdown source
 * line numbers (`data-src-line`, `data-src-end`, and sentence-level `<wbr data-apex-line>`).
 * Activated strictly on PR preview builds so production `main` HTML stays untouched.
 */
export function sourceLineMapPlugin(md: MarkdownIt): void {
  md.core.ruler.push('apex_source_line_map', (state) => {
    const TokenCtor = state.Token as unknown as new (
      type: string,
      tag: string,
      nesting: number,
    ) => TokenLike

    for (const token of state.tokens as unknown as TokenLike[]) {
      if (BLOCK_OPEN_TYPES.has(token.type)) {
        setLineAttrs(token)
      } else if (token.type === 'inline') {
        annotateInlineSentences(token, TokenCtor)
      }
    }
  })

  const prevFence =
    md.renderer.rules.fence ??
    ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  md.renderer.rules.fence = (tokens, idx, options, env, self) => {
    const rendered = prevFence(tokens, idx, options, env, self)
    return wrapBlockHtml(rendered, tokens[idx] as unknown as TokenLike)
  }

  const prevMathBlock = md.renderer.rules.math_block
  if (prevMathBlock) {
    md.renderer.rules.math_block = (tokens, idx, options, env, self) => {
      const rendered = prevMathBlock(tokens, idx, options, env, self)
      return wrapBlockHtml(rendered, tokens[idx] as unknown as TokenLike, 'apex-review-math')
    }
  }

  const prevHtmlBlock =
    md.renderer.rules.html_block ??
    ((tokens, idx) => tokens[idx].content)

  md.renderer.rules.html_block = (tokens, idx, options, env, self) => {
    const token = tokens[idx] as unknown as TokenLike
    const raw = prevHtmlBlock(tokens, idx, options, env, self)
    const trimmed = raw.trim()
    if (PASCAL_SELF_CLOSING_RE.test(trimmed)) {
      return wrapBlockHtml(raw, token, 'apex-review-widget')
    }
    const span = getLineSpan(token)
    if (span && DETAILS_OPEN_RE.test(trimmed)) {
      return raw.replace(
        DETAILS_OPEN_RE,
        `<details$1 data-src-line="${span[0]}" data-src-end="${span[1]}">`,
      )
    }
    return raw
  }

  const prevHtmlInline =
    md.renderer.rules.html_inline ??
    ((tokens, idx) => tokens[idx].content)

  md.renderer.rules.html_inline = (tokens, idx, options, env, self) => {
    const token = tokens[idx] as unknown as TokenLike
    const raw = prevHtmlInline(tokens, idx, options, env, self)
    if (token.map && PASCAL_SELF_CLOSING_RE.test(raw.trim())) {
      return wrapBlockHtml(raw, token, 'apex-review-widget')
    }
    return raw
  }
}
