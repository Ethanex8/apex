/**
 * Purpose: VitePress site, markdown plugin, code transclusion, and PR preview configuration for the Apex textbook.
 * Usage: Evaluated automatically by VitePress (`npm --prefix book run build|dev`); reads `BOOK_BASE` and `APEX_PR_META_FILE`.
 * Invariants: Treats `..` (repo root) as `srcDir`, rewrites chapters cleanly to `:<sys>/<chapter>`, and fails fast on invalid line transclusions or malformed explicit PR metadata.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitepress'
import { repoCodeLinksPlugin } from './plugins/repoCodeLinks.mts'
import { sourceLineMapPlugin } from './plugins/sourceLineMap.mts'
import { buildTextbookSidebar } from './roadmapSidebar.mts'
import type { PrReviewMeta } from './theme/review/types.ts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '../..')

/** Bundle chunk-size warning threshold (KB); MathJax SVG + KaTeX vendor bundle sits just above Vite's default 500 KB. */
const MAX_CHUNK_WARNING_KB = 1600
const VIRTUAL_PR_META_ID = 'virtual:apex-pr-review'
const RESOLVED_VIRTUAL_PR_META_ID = `\0${VIRTUAL_PR_META_ID}`

/**
 * Load PR preview review metadata from `APEX_PR_META_FILE` when explicitly configured.
 * Returns disabled metadata when `APEX_PR_META_FILE` is unset or explicitly `{ enabled: false }`;
 * throws on missing files, malformed JSON, or enabled metadata missing `repo` or a positive integer `prNumber`.
 */
function loadPrReviewMeta(): PrReviewMeta {
  const empty: PrReviewMeta = {
    enabled: false,
    repo: '',
    prNumber: 0,
    baseSha: '',
    headSha: '',
    prUrl: '',
    files: {},
  }
  const metaPath = process.env.APEX_PR_META_FILE?.trim()
  if (!metaPath) return empty
  if (!fs.existsSync(metaPath)) {
    throw new Error(`APEX_PR_META_FILE points to a missing file: ${metaPath}`)
  }
  const rawParsed: unknown = JSON.parse(fs.readFileSync(metaPath, 'utf-8'))
  if (typeof rawParsed !== 'object' || rawParsed === null || Array.isArray(rawParsed)) {
    throw new Error(`Invalid PR review metadata in ${metaPath}: expected JSON object`)
  }
  const parsed = rawParsed as Record<string, unknown>
  if (typeof parsed.enabled !== 'boolean') {
    throw new Error(`Invalid PR review metadata in ${metaPath}: boolean enabled field required`)
  }
  if (!parsed.enabled) return empty
  const repo = typeof parsed.repo === 'string' ? parsed.repo.trim() : ''
  const prNumber = typeof parsed.prNumber === 'number' ? parsed.prNumber : Number.NaN
  if (!repo || !Number.isInteger(prNumber) || prNumber <= 0) {
    throw new Error(`Enabled PR review metadata in ${metaPath} requires non-empty repo and positive integer prNumber`)
  }
  return {
    enabled: true,
    repo,
    prNumber,
    baseSha: typeof parsed.baseSha === 'string' ? parsed.baseSha : '',
    headSha: typeof parsed.headSha === 'string' ? parsed.headSha : '',
    prUrl: typeof parsed.prUrl === 'string' ? parsed.prUrl : `https://github.com/${repo}/pull/${prNumber}`,
    files: (typeof parsed.files === 'object' && parsed.files !== null && !Array.isArray(parsed.files)
      ? parsed.files
      : {}) as PrReviewMeta['files'],
  }
}

const PR_REVIEW_META = loadPrReviewMeta()

export default defineConfig({
  title: 'Apex Systems Engineering',
  description:
    'Digital Silicon, Circuit Boards, Compilers, Real-Time Operating Systems, and Quadruped Robotics',
  base: process.env.BOOK_BASE ?? '/',
  srcDir: '..',
  cleanUrls: true,
  ignoreDeadLinks: false,
  lastUpdated: false,
  head: [
    [
      'script',
      {},
      // Apply serif typography synchronously before Vue hydration to prevent flash of unstyled/sans text; unset defaults to serif.
      "try{const s=localStorage.getItem('apex-book-serif');if(s===null||s==='1')document.documentElement.classList.add('book-serif-mode')}catch{}",
    ],
  ],

  /** Attach repository-relative `repoSourcePath` (forward slashes) to every page for PR review routing. */
  transformPageData(pageData) {
    return {
      repoSourcePath: (pageData.filePath || pageData.relativePath).replace(/\\/g, '/'),
    }
  },

  srcExclude: [
    'README.md',
    'ROADMAP.md',
    'GEMINI.md',
    'docs/**',
    '.agents/**',
    '.github/**',
    '.tools/**',
    '.venv/**',
    'scripts/**',
    'book/node_modules/**',
    'book/.vitepress/**',
    'systems/*/README.md',
    '**/BOM.md',
    '**/REVIEW_CHECKLIST.md',
    '**/node_modules/**',
  ],

  rewrites: {
    'book/index.md': 'index.md',
    'VISION.md': 'vision.md',
    'systems/:sys/chapters/:chapter.md': ':sys/:chapter.md',
  },

  markdown: {
    math: true,
    lineNumbers: true,
    anchor: {
      /** Match textbook heading anchors by folding en/em dashes into `-` and keeping Latin-Extended accents. */
      slugify: (str) =>
        str
          .trim()
          .toLowerCase()
          .replace(/[\u2013\u2014]/g, '-')
          .replace(/[^\w\u00C0-\u024f\s-]/g, '')
          .replace(/[\s_-]+/g, '-')
          .replace(/^-+|-+$/g, ''),
    },
    /** Register repository source links, strict `#L` line-slice fences, Mermaid containers, and PR line-map attrs. */
    config: (md) => {
      repoCodeLinksPlugin(md, REPO_ROOT)

      const defaultFence =
        md.renderer.rules.fence ??
        ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

      /** Render transcluded source line ranges, Mermaid SVGs, or default highlighted code blocks. */
      md.renderer.rules.fence = (tokens, idx, options, env, self) => {
        const token = tokens[idx] as typeof tokens[number] & { src?: [string, string] }

        // Support exact 1-indexed line-range transclusions:
        // <<< @/systems/brain/sim/oracle.py#L138-L144
        if (token.src) {
          const [srcPath, regionName] = token.src
          const lineMatch = regionName?.match(/^L(\d+)(?:-L?(\d+))?$/)
          // Catch malformed `#L...` line selectors (e.g., `#L`, `#L10-abc`) without blocking named `#L...` regions such as `#Loop`.
          if (srcPath && regionName && /^L(?:\d|[^a-zA-Z]|$)/.test(regionName) && !lineMatch) {
            throw new Error(`Malformed line transclusion selector #${regionName} for ${srcPath}`)
          }
          if (srcPath && lineMatch) {
            if (!fs.existsSync(srcPath)) {
              throw new Error(`Transclusion source file not found: ${srcPath}#${regionName}`)
            }
            const startLine = Number.parseInt(lineMatch[1], 10)
            const endLine = lineMatch[2] ? Number.parseInt(lineMatch[2], 10) : startLine
            const rawText = fs.readFileSync(srcPath, 'utf-8').replace(/\r\n/g, '\n')
            const rawLines = rawText.split('\n')
            const allLines = rawText.endsWith('\n') ? rawLines.slice(0, -1) : rawLines
            if (startLine < 1 || endLine < startLine || endLine > allLines.length) {
              throw new Error(
                `Invalid transclusion range #${regionName} for ${srcPath} (${allLines.length} lines)`,
              )
            }
            // Register the source file with VitePress HMR so edits trigger live rebuilds.
            if (env?.includes && Array.isArray(env.includes)) {
              env.includes.push(srcPath)
            }
            token.content = allLines.slice(startLine - 1, endLine).join('\n') + '\n'
            const baseName = path.basename(srcPath)
            const rangeLabel = startLine === endLine ? `L${startLine}` : `L${startLine}–L${endLine}`
            token.info = token.info.replace(
              /\[([^\]]+)\]/,
              `[${baseName} (${rangeLabel})]`,
            )
            if (/:line-numbers\b/.test(token.info)) {
              token.info = token.info.replace(/:line-numbers(?:=\d+)?/, `:line-numbers=${startLine}`)
            } else {
              token.info = `${token.info.trim()} :line-numbers=${startLine}`
            }
            // Clear `token.src` so VitePress's downstream snippet processor does not overwrite our slice.
            delete token.src
          }
        }

        if (token.info.trim() === 'mermaid') {
          const encoded = encodeURIComponent(token.content)
          return `<MermaidDiagram code="${encoded}" />\n`
        }
        return defaultFence(tokens, idx, options, env, self)
      }

      if (PR_REVIEW_META.enabled) {
        sourceLineMapPlugin(md)
      }
    },
  },

  vite: {
    plugins: [
      {
        // Expose CI-generated PR metadata via `virtual:apex-pr-review` so client components stay runtime-config-free.
        name: 'apex-pr-review-virtual-meta',
        /** Resolve the synthetic `virtual:apex-pr-review` module specifier for Rollup/Vite. */
        resolveId(id: string) {
          if (id === VIRTUAL_PR_META_ID) return RESOLVED_VIRTUAL_PR_META_ID
          return null
        },
        /** Emit the validated build-time `PR_REVIEW_META` object as a static ES module export. */
        load(id: string) {
          if (id === RESOLVED_VIRTUAL_PR_META_ID) {
            return `export default ${JSON.stringify(PR_REVIEW_META)};`
          }
          return null
        },
      },
    ],
    resolve: {
      alias: {
        vue: path.resolve(__dirname, '../node_modules/vue'),
      },
    },
    build: {
      chunkSizeWarningLimit: MAX_CHUNK_WARNING_KB,
    },
    server: {
      // Allow VM preview tunnels and local port-forwarded hosts during `vitepress dev` / `preview`.
      allowedHosts: true,
      fs: {
        allow: [REPO_ROOT],
      },
    },
  },

  themeConfig: {
    nav: [],

    sidebar: buildTextbookSidebar(REPO_ROOT),

    aside: false,

    search: {
      provider: 'local',
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/Ethanex8/apex' },
    ],

    docFooter: {
      prev: 'Previous Chapter',
      next: 'Next Chapter',
    },
  },
})
