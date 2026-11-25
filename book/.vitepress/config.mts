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
  const metaPath = process.env.APEX_PR_META_FILE
  if (!metaPath || !fs.existsSync(metaPath)) return empty
  try {
    const parsed = JSON.parse(fs.readFileSync(metaPath, 'utf-8')) as Partial<PrReviewMeta>
    if (!parsed.enabled || !parsed.repo || !parsed.prNumber) return empty
    return {
      enabled: true,
      repo: parsed.repo,
      prNumber: parsed.prNumber,
      baseSha: parsed.baseSha ?? '',
      headSha: parsed.headSha ?? '',
      prUrl: parsed.prUrl ?? `https://github.com/${parsed.repo}/pull/${parsed.prNumber}`,
      files: parsed.files ?? {},
    }
  } catch {
    return empty
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
      "try{const s=localStorage.getItem('apex-book-serif');if(s===null||s==='1')document.documentElement.classList.add('book-serif-mode')}catch{}",
    ],
  ],

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
    '**/BOM.md',
    '**/REVIEW_CHECKLIST.md',
    '**/node_modules/**',
  ],

  rewrites: {
    'book/index.md': 'index.md',
    'VISION.md': 'vision.md',
    'systems/:sys/README.md': ':sys/index.md',
    'systems/:sys/chapters/:chapter.md': ':sys/:chapter.md',
  },

  markdown: {
    math: true,
    lineNumbers: true,
    anchor: {
      slugify: (str) =>
        str
          .trim()
          .toLowerCase()
          .replace(/[\u2013\u2014]/g, '-')
          .replace(/[^\w\u00C0-\u024f\s-]/g, '')
          .replace(/[\s_-]+/g, '-')
          .replace(/^-+|-+$/g, ''),
    },
    config: (md) => {
      repoCodeLinksPlugin(md, REPO_ROOT)

      const defaultFence =
        md.renderer.rules.fence ??
        ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))

      md.renderer.rules.fence = (tokens, idx, options, env, self) => {
        const token = tokens[idx] as typeof tokens[number] & { src?: [string, string] }

        // Support exact 1-indexed line-range transclusions:
        // <<< @/systems/brain/sim/oracle.py#L138-L144
        if (token.src) {
          const [srcPath, regionName] = token.src
          const lineMatch = regionName?.match(/^L(\d+)(?:-L?(\d+))?$/)
          if (srcPath && lineMatch && fs.existsSync(srcPath)) {
            const startLine = Number.parseInt(lineMatch[1], 10)
            const endLine = lineMatch[2] ? Number.parseInt(lineMatch[2], 10) : startLine
            if (env?.includes && Array.isArray(env.includes)) {
              env.includes.push(srcPath)
            }
            const allLines = fs.readFileSync(srcPath, 'utf-8').replace(/\r\n/g, '\n').split('\n')
            token.content = allLines.slice(Math.max(0, startLine - 1), endLine).join('\n') + '\n'
            const baseName = path.basename(srcPath)
            const rangeLabel = startLine === endLine ? `L${startLine}` : `L${startLine}–L${endLine}`
            token.info = token.info.replace(
              /\[([^\]]+)\]/,
              `[${baseName} (${rangeLabel})]`,
            )
            if (!token.info.includes(':line-numbers')) {
              token.info = `${token.info.trim()} :line-numbers=${startLine}`
            }
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
        name: 'apex-pr-review-virtual-meta',
        resolveId(id: string) {
          if (id === 'virtual:apex-pr-review') return '\0virtual:apex-pr-review'
          return null
        },
        load(id: string) {
          if (id === '\0virtual:apex-pr-review') {
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
      chunkSizeWarningLimit: 1600,
    },
    server: {
      allowedHosts: true,
      fs: {
        allow: [REPO_ROOT],
      },
    },
  },

  themeConfig: {
    nav: [
      { text: 'Cover', link: '/' },
      { text: 'Prologue', link: '/vision' },
      {
        text: 'Parts',
        items: [
          { text: 'Part I — Digital Logic and Processor Architecture', link: '/#part-i-digital-logic-and-processor-architecture' },
          { text: 'Part II — Circuit-Board Physics and Memory Interconnects', link: '/#part-ii-circuit-board-physics-and-memory-interconnects' },
          { text: 'Part III — Compilers and Real-Time Operating Systems', link: '/#part-iii-compilers-and-real-time-operating-systems' },
          { text: 'Part IV — Brushless Motors and Power Inverters', link: '/#part-iv-brushless-motors-and-power-inverters' },
          { text: 'Part V — Battery Systems and Solid-State Protection', link: '/#part-v-battery-systems-and-solid-state-protection' },
          { text: 'Part VI — Rigid-Body Kinematics and Compliant Limbs', link: '/#part-vi-rigid-body-kinematics-and-compliant-limbs' },
          { text: 'Part VII — Optimal Balance and Learned Locomotion', link: '/#part-vii-optimal-balance-and-learned-locomotion' },
          { text: 'Part VIII — Stereo Vision and Autonomous Navigation', link: '/#part-viii-stereo-vision-and-autonomous-navigation' },
        ],
      },
      {
        text: 'Subsystems',
        items: [
          { text: '1. brain — Processor, Board, Compiler, and RTOS', link: '/brain/' },
          { text: '2. drive — Brushless Actuator and Gearbox', link: '/drive/' },
          { text: '3. power — Battery Spine and Protection', link: '/power/' },
          { text: '4. limb — Articulated Hopping Leg', link: '/limb/' },
          { text: '5. walker — Dynamic Quadruped Platform', link: '/walker/' },
          { text: '6. sight — Stereo Vision and Navigation', link: '/sight/' },
        ],
      },
    ],

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
