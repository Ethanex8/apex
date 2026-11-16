import fs from 'node:fs'
import path from 'node:path'
import yaml from 'js-yaml'
import type { DefaultTheme } from 'vitepress'

interface RoadmapSystem {
  id: string
  order: number
  name: string
}

interface RoadmapStep {
  id: string
  system: string
  status: 'pending' | 'in_review' | 'approved'
}

interface BookChapter {
  id: string
  number: number
  slug: string
  title: string
  steps: string[]
}

interface BookPart {
  id: string
  number: string
  title: string
  system: string
  chapters: BookChapter[]
}

interface RoadmapData {
  systems: RoadmapSystem[]
  steps: RoadmapStep[]
  book: {
    parts: BookPart[]
  }
}

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
        { text: 'About This Book', link: '/' },
        { text: 'Prologue: System Architecture & Contracts', link: '/vision' },
      ],
    },
  ]

  for (const part of data.book.parts) {
    const chapDir = path.join(repoRoot, 'systems', part.system, 'chapters')
    const partItems: DefaultTheme.SidebarItem[] = []
    let hasPublished = false

    for (const chap of part.chapters) {
      const mdPath = path.join(chapDir, `${chap.slug}.md`)
      if (fs.existsSync(mdPath)) {
        hasPublished = true
        const readBadge = extractReadingTime(mdPath)
        const badge = readBadge ? ` (${readBadge})` : ''
        partItems.push({
          text: `${chap.number}. ${chap.title}${badge}`,
          link: `/${part.system}/${chap.slug}`,
        })
      } else {
        partItems.push({
          text: `${chap.number}. ${chap.title} · Upcoming`,
        })
      }
    }

    sidebar.push({
      text: `Part ${part.number}: ${part.title}`,
      collapsed: !hasPublished,
      items: partItems,
    })
  }

  const subsystemItems: DefaultTheme.SidebarItem[] = data.systems.map((sys) => {
    const sysSteps = data.steps.filter((s) => s.system === sys.id)
    const approvedCount = sysSteps.filter((s) => s.status === 'approved').length
    return {
      text: `${sys.order}. ${sys.id} (${approvedCount}/${sysSteps.length})`,
      link: `/${sys.id}/`,
    }
  })

  sidebar.push({
    text: 'Hardware Subsystems',
    collapsed: true,
    items: subsystemItems,
  })

  return sidebar
}
