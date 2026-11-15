import fs from 'node:fs'
import path from 'node:path'
import type MarkdownIt from 'markdown-it'

const GITHUB_REF = process.env.GITHUB_REF_NAME || 'main'
const GITHUB_BLOB_BASE = `https://github.com/Ethanex8/apex/blob/${GITHUB_REF}`

function mapRepoPathToBookRoute(repoRel: string): string | null {
  if (repoRel === 'book/index.md') return '/'
  if (repoRel === 'VISION.md') return '/vision'

  const sysReadme = repoRel.match(/^systems\/([a-z0-9_-]+)\/README\.md$/)
  if (sysReadme) return `/${sysReadme[1]}/`

  const sysChapter = repoRel.match(/^systems\/([a-z0-9_-]+)\/chapters\/([^/]+)\.md$/)
  if (sysChapter) return `/${sysChapter[1]}/${sysChapter[2]}`

  return null
}

/**
 * Rewrites relative links inside Markdown chapters and system READMEs:
 * 1. Links to included book Markdown files map cleanly to rewritten VitePress routes.
 * 2. Links to repo source files (e.g. `../sim/oracle.py#L138-L144` or `./pcb/BOM.md`)
 *    map to exact GitHub blob/line URLs styled with `.repo-source-link`.
 */
export function repoCodeLinksPlugin(md: MarkdownIt, repoRoot: string): void {
  const defaultLinkOpen =
    md.renderer.rules.link_open ??
    ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

  md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
    const token = tokens[idx]
    const hrefIdx = token.attrIndex('href')
    const titleIdx = token.attrIndex('title')
    if (titleIdx >= 0 && token.attrs && token.attrs[titleIdx][1].startsWith('anchor:')) {
      token.attrs.splice(titleIdx, 1)
    }
    if (hrefIdx >= 0 && token.attrs) {
      const rawHref = token.attrs[hrefIdx][1]
      if (
        rawHref &&
        !rawHref.startsWith('http://') &&
        !rawHref.startsWith('https://') &&
        !rawHref.startsWith('mailto:') &&
        !rawHref.startsWith('#') &&
        !rawHref.startsWith('/')
      ) {
        const sourcePath: string | undefined = env?.realPath || env?.path
        if (sourcePath) {
          const hashPos = rawHref.indexOf('#')
          const relFile = hashPos >= 0 ? rawHref.slice(0, hashPos) : rawHref
          const hash = hashPos >= 0 ? rawHref.slice(hashPos) : ''

          const absTarget = path.resolve(path.dirname(sourcePath), relFile)
          const repoRel = path.relative(repoRoot, absTarget).split(path.sep).join('/')

          if (!repoRel.startsWith('..')) {
            const bookRoute = mapRepoPathToBookRoute(repoRel)
            if (bookRoute) {
              token.attrs[hrefIdx][1] = `${bookRoute}${hash}`
            } else if (fs.existsSync(absTarget)) {
              token.attrs[hrefIdx][1] = `${GITHUB_BLOB_BASE}/${repoRel}${hash}`
              token.attrSet('target', '_blank')
              token.attrSet('rel', 'noreferrer')
              token.attrJoin('class', 'repo-source-link')
            }
          }
        }
      }
    }
    return defaultLinkOpen(tokens, idx, options, env, self)
  }
}
