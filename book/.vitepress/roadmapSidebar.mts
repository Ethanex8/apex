import fs from 'node:fs'
import path from 'node:path'
import yaml from 'js-yaml'
import type { DefaultTheme } from 'vitepress'

interface RoadmapPhase {
  id: string
  name: string
}

interface RoadmapSystem {
  id: string
  order: number
  name: string
  phases: RoadmapPhase[]
}

interface RoadmapStep {
  id: string
  system: string
  phase: string
  mode: 'couch' | 'bench'
  title: string
  status: 'pending' | 'in_review' | 'approved'
}

interface RoadmapData {
  systems: RoadmapSystem[]
  steps: RoadmapStep[]
}

const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI']

function extractReadingTime(mdPath: string): string | null {
  try {
    const head = fs.readFileSync(mdPath, 'utf-8').slice(0, 1200)
    const match = head.match(/\*\*Reading Time\*\*:\s*([^\n\r]+)/)
    if (!match) return null
    const mins = match[1].match(/(\d+(?:[–-]\d+)?)\s*min/)
    return mins ? `${mins[1]}m` : null
  } catch {
    return null
  }
}

export function buildTextbookSidebar(repoRoot: string): DefaultTheme.SidebarItem[] {
  const roadmapPath = path.join(repoRoot, 'roadmap.yaml')
  const raw = fs.readFileSync(roadmapPath, 'utf-8')
  const data = yaml.load(raw) as RoadmapData

  const sidebar: DefaultTheme.SidebarItem[] = [
    {
      text: 'Front Matter',
      collapsed: false,
      items: [
        { text: 'About This Textbook', link: '/' },
        { text: 'Prologue: System Vision & Contracts', link: '/vision' },
      ],
    },
  ]

  for (const sys of data.systems) {
    const volNum = ROMAN[sys.order - 1] ?? String(sys.order)
    const chapDir = path.join(repoRoot, 'systems', sys.id, 'chapters')
    const chapterFiles = fs.existsSync(chapDir)
      ? fs.readdirSync(chapDir).filter((f) => f.endsWith('.md')).sort()
      : []

    const fileByStepNum = new Map<number, string>()
    for (const file of chapterFiles) {
      const m = file.match(/^(\d+)_(.+)\.md$/)
      if (m) {
        fileByStepNum.set(Number.parseInt(m[1], 10), file.replace(/\.md$/, ''))
      }
    }

    const sysSteps = data.steps.filter((s) => s.system === sys.id)
    const approvedCount = sysSteps.filter((s) => s.status === 'approved').length

    const volumeItems: DefaultTheme.SidebarItem[] = [
      {
        text: `Volume ${volNum} Overview (${approvedCount}/${sysSteps.length} steps)`,
        link: `/${sys.id}/`,
      },
    ]

    for (const phase of sys.phases) {
      const phaseSteps = sysSteps.filter((s) => s.phase === phase.id)
      const publishedPhaseItems: DefaultTheme.SidebarItem[] = []

      for (const st of phaseSteps) {
        const numMatch = st.id.match(/-(\d+)$/)
        if (!numMatch) continue
        const stepNum = Number.parseInt(numMatch[1], 10)
        const slug = fileByStepNum.get(stepNum)
        if (slug) {
          const fullMdPath = path.join(chapDir, `${slug}.md`)
          const readBadge = extractReadingTime(fullMdPath)
          const badge = readBadge ? ` (${readBadge})` : ''
          publishedPhaseItems.push({
            text: `${stepNum}. ${st.title}${badge}`,
            link: `/${sys.id}/${slug}`,
          })
        }
      }

      if (publishedPhaseItems.length > 0) {
        volumeItems.push({
          text: phase.name,
          collapsed: false,
          items: publishedPhaseItems,
        })
      }
    }

    sidebar.push({
      text: `Vol. ${volNum}: ${sys.id.toUpperCase()}`,
      collapsed: sys.order !== 1 && chapterFiles.length === 0,
      items: volumeItems,
    })
  }

  return sidebar
}
