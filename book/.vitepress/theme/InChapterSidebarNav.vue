<script setup lang="ts">
/**
 * Purpose: Render an automatically expanded "In This Chapter" section list inside the left sidebar.
 * Usage: Mounted in Layout.vue via `#sidebar-nav-before` so section links stay visible when `< 1280px`.
 * Invariants: Tracks `h2`/`h3` elements inside `.vp-doc` and cleans up scroll/resize listeners on unmount.
 */
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { onContentUpdated, useData } from 'vitepress'

/** Parsed chapter heading entry for in-sidebar outline navigation. */
interface ChapterHeading {
  id: string
  text: string
  level: 2 | 3
}

const SCROLLSPY_OFFSET_PX = 96
const EXCLUDED_HEADING_PARENTS = '.apex-review-ui, .hw-widget, .sr-only'

const headings = ref<ChapterHeading[]>([])
const activeId = ref('')
const { frontmatter } = useData()

/** Extract readable heading text while stripping VitePress anchor `#` suffixes and zero-width spaces. */
function cleanHeadingText(el: Element): string {
  const raw = (el.textContent ?? '').replace(/\u200b/g, '').trim()
  return raw.replace(/\s*#$/, '').trim()
}

/** Recompute current section highlight from the vertical scroll position of `.vp-doc` headings. */
function updateActiveSection() {
  if (typeof window === 'undefined' || headings.value.length === 0) return
  let current = headings.value[0].id
  for (const h of headings.value) {
    const el = document.getElementById(h.id)
    if (!el) continue
    if (el.getBoundingClientRect().top <= SCROLLSPY_OFFSET_PX) {
      current = h.id
    } else {
      break
    }
  }
  activeId.value = current
}

/** Collect visible `h2`/`h3` chapter headings from `.vp-doc` after route/content updates. */
function refreshHeadings() {
  if (typeof document === 'undefined') return
  const docRoot = document.querySelector('.vp-doc')
  if (!docRoot) {
    headings.value = []
    activeId.value = ''
    return
  }
  const collected: ChapterHeading[] = []
  const nodes = docRoot.querySelectorAll('h2[id], h3[id]')
  for (const el of nodes) {
    if (el.closest(EXCLUDED_HEADING_PARENTS)) continue
    const text = cleanHeadingText(el)
    if (!text) continue
    collected.push({
      id: el.id,
      text,
      level: el.tagName === 'H3' ? 3 : 2,
    })
  }
  headings.value = collected
  updateActiveSection()
}

/** Close any open mobile sidebar drawer when selecting a section anchor. */
function onSectionClick(id: string) {
  activeId.value = id
  if (typeof document === 'undefined') return
  // Trigger VitePress's native mobile drawer backdrop if open so hash jumps reveal the chapter immediately.
  document.querySelector<HTMLElement>('.VPSidebarBackdrop')?.click()
}

onContentUpdated(async () => {
  await nextTick()
  refreshHeadings()
})

onMounted(() => {
  refreshHeadings()
  if (typeof window !== 'undefined') {
    window.addEventListener('scroll', updateActiveSection, { passive: true })
    window.addEventListener('resize', updateActiveSection, { passive: true })
  }
})

onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('scroll', updateActiveSection)
    window.removeEventListener('resize', updateActiveSection)
  }
})
</script>

<template>
  <nav
    v-if="headings.length > 0 && frontmatter.layout !== 'home'"
    aria-label="In This Chapter"
    class="sidebar-in-chapter"
  >
    <div class="sidebar-in-chapter-title">In This Chapter</div>
    <ul class="sidebar-in-chapter-list">
      <li
        v-for="item in headings"
        :key="item.id"
        class="sidebar-in-chapter-item"
        :class="{ 'is-sub': item.level === 3, 'is-active': activeId === item.id }"
      >
        <a
          :href="`#${item.id}`"
          class="sidebar-in-chapter-link"
          @click="onSectionClick(item.id)"
        >
          {{ item.text }}
        </a>
      </li>
    </ul>
  </nav>
</template>
