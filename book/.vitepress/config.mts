import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vitepress'
import { repoCodeLinksPlugin } from './plugins/repoCodeLinks.mts'
import { buildTextbookSidebar } from './roadmapSidebar.mts'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = path.resolve(__dirname, '../..')

export default defineConfig({
  title: 'Apex Systems Textbook',
  description:
    'Digital Silicon, Circuit Boards, Compilers, Real-Time Operating Systems & Quadruped Robotics — An Integrated Systems Engineering Textbook',
  base: process.env.BOOK_BASE ?? '/',
  srcDir: '..',
  cleanUrls: true,
  ignoreDeadLinks: false,
  lastUpdated: false,

  srcExclude: [
    'README.md',
    'ROADMAP.md',
    'GEMINI.md',
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
    },
  },

  vite: {
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
          { text: 'Part I — Digital Logic & Processor Architecture', link: '/#part-i-digital-logic-and-processor-architecture' },
          { text: 'Part II — High-Speed Board Physics & SoC', link: '/#part-ii-high-speed-board-physics-and-system-on-chip-interconnects' },
          { text: 'Part III — Compilers, RTOS & Silicon Validation', link: '/#part-iii-compilers-real-time-operating-systems-and-silicon-validation' },
          { text: 'Part IV — Brushless Electromechanics & FOC', link: '/#part-iv-brushless-electromechanics-power-inverters-and-force-actuation' },
          { text: 'Part V — Electrochemical Energy & Protection', link: '/#part-v-electrochemical-energy-and-solid-state-power-protection' },
          { text: 'Part VI — Spatial Kinematics & Compliant Limbs', link: '/#part-vi-spatial-kinematics-dynamics-and-compliant-limbs' },
          { text: 'Part VII — Whole-Body Control & RL Locomotion', link: '/#part-vii-whole-body-optimal-control-and-learned-locomotion' },
          { text: 'Part VIII — Stereo Vision & Autonomous Navigation', link: '/#part-viii-stereo-vision-state-estimation-and-autonomous-navigation' },
        ],
      },
      {
        text: 'Subsystems',
        items: [
          { text: '1. brain — CPU, PCB, Compiler & RTOS', link: '/brain/' },
          { text: '2. drive — FOC Motor & Gearbox', link: '/drive/' },
          { text: '3. power — Electronic Breaker & BMS', link: '/power/' },
          { text: '4. limb — 3-DOF Leg & Hopping', link: '/limb/' },
          { text: '5. walker — Quadruped & Sim-to-Real RL', link: '/walker/' },
          { text: '6. sight — Stereo Vision & Navigation', link: '/sight/' },
        ],
      },
    ],

    sidebar: buildTextbookSidebar(REPO_ROOT),

    outline: {
      level: [2, 3],
      label: 'In This Chapter',
    },

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
