/**
 * Purpose: Compile the VitePress left-hand textbook sidebar dynamically from `roadmap.yaml`.
 * Usage: Called at config evaluation time from `book/.vitepress/config.mts`.
 * Invariants: Only chapters present on disk under `systems/<system>/chapters/<slug>.md` receive active links; missing chapters render muted as upcoming entries.
 */
import fs from 'node:fs'
import path from 'node:path'
import yaml from 'js-yaml'
import type { DefaultTheme } from 'vitepress'

/** Metadata for one textbook chapter entry inside `roadmap.yaml` `book.parts[].chapters`. */
interface BookChapter {
  id: string
  /** 1-indexed book-wide sequential chapter number. */
  number: number
  /** Filename stem (without `.md`) resolved under `systems/<system>/chapters/<slug>.md`. */
  slug: string
  title: string
  steps: string[]
}

/** Syllabus part grouping one subsystem's chapters under a Roman numeral heading. */
interface BookPart {
  id: string
  /** Roman numeral identifier (e.g., `"I"`..`"VIII"`), formatted as `Part <number>`. */
  number: string
  title: string
  system: string
  chapters: BookChapter[]
}

/** Top-level parsed `roadmap.yaml` subset consumed to build the textbook sidebar. */
interface RoadmapData {
  /** Textbook part and chapter syllabus tree. */
  book: {
    parts: BookPart[]
  }
}

/** Parse `<resolvedRoot>/roadmap.yaml` and return the typed `RoadmapData` tree, failing fast on schema drift. */
function loadValidatedRoadmap(resolvedRoot: string): RoadmapData {
  const roadmapPath = path.join(resolvedRoot, 'roadmap.yaml')
  const raw = fs.readFileSync(roadmapPath, 'utf-8')
  const data = yaml.load(raw) as Partial<RoadmapData> | null
  if (!data?.book || !Array.isArray(data.book.parts)) {
    throw new Error(`Invalid roadmap schema in ${roadmapPath}: missing book.parts array`)
  }
  for (const part of data.book.parts) {
    if (
      !part ||
      typeof part.number !== 'string' ||
      !part.number.trim() ||
      typeof part.title !== 'string' ||
      !part.title.trim() ||
      typeof part.system !== 'string' ||
      !part.system.trim() ||
      !Array.isArray(part.chapters)
    ) {
      throw new Error(`Invalid part entry in ${roadmapPath}: ${JSON.stringify(part)}`)
    }
    for (const chap of part.chapters) {
      if (
        !chap ||
        !Number.isInteger(chap.number) ||
        chap.number < 1 ||
        typeof chap.slug !== 'string' ||
        !chap.slug.trim() ||
        typeof chap.title !== 'string' ||
        !chap.title.trim()
      ) {
        throw new Error(`Invalid chapter entry under part ${part.number} in ${roadmapPath}`)
      }
    }
  }
  return data as RoadmapData
}

/**
 * Build the VitePress textbook sidebar tree (`Front Matter` + `Part I–VIII`) from `<repoRoot>/roadmap.yaml`.
 * Collapses parts with zero published chapter files and marks unpublished syllabus rows as upcoming.
 */
export function buildTextbookSidebar(repoRoot: string): DefaultTheme.SidebarItem[] {
  if (typeof repoRoot !== 'string' || !repoRoot.trim()) {
    throw new Error('buildTextbookSidebar requires a non-empty repoRoot path')
  }
  const resolvedRoot = path.resolve(repoRoot)
  const data = loadValidatedRoadmap(resolvedRoot)

  const sidebar: DefaultTheme.SidebarItem[] = [
    {
      text: 'Front Matter',
      collapsed: false,
      items: [
        { text: 'About This Book', link: '/' },
        { text: 'Prologue — System Architecture and Contracts', link: '/vision' },
      ],
    },
  ]

  for (const part of data.book.parts) {
    const chapDir = path.join(resolvedRoot, 'systems', part.system, 'chapters')
    const partItems: DefaultTheme.SidebarItem[] = []
    let hasPublished = false

    for (const chap of part.chapters) {
      const mdPath = path.join(chapDir, `${chap.slug}.md`)
      if (fs.existsSync(mdPath)) {
        hasPublished = true
        partItems.push({
          text: `${chap.number}. ${chap.title}`,
          link: `/${part.system}/${chap.slug}`,
        })
      } else {
        partItems.push({
          text: `${chap.number}. ${chap.title} · Upcoming`,
        })
      }
    }

    sidebar.push({
      text: `Part ${part.number} — ${part.title}`,
      collapsed: !hasPublished,
      items: partItems,
    })
  }

  return sidebar
}
