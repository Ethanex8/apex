<script setup lang="ts">
/**
 * Purpose: Embed the active chapter's section outline directly under its expanded entry in the left sidebar.
 * Usage: Mounted in Layout.vue via `#sidebar-nav-before`; teleports into `.VPSidebarItem.is-active` on client navigation.
 * Invariants: Scans `.vp-doc` `h2`/`h3` headings after mount/content updates and cleans listeners on unmount.
 */
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { onContentUpdated, useData } from 'vitepress'

/** Parsed heading entry rendered beneath the active chapter link in the left sidebar. */
interface ChapterHeading {
  id: string
  text: string
  level: 2 | 3
}

const SCROLLSPY_OFFSET_PX = 96
const SCROLLSPY_BOTTOM_EPSILON_PX = 2
const EXCLUDED_HEADING_PARENTS = '.apex-review-ui, .hw-widget, .sr-only'
const ACTIVE_SIDEBAR_ITEM_SELECTOR = '#VPSidebarNav .VPSidebarItem.is-active'

const headings = ref<ChapterHeading[]>([])
const activeId = ref('')
const teleportTarget = ref<HTMLElement | null>(null)
const { frontmatter } = useData()

/** Locate the active sidebar item element so section links embed directly under that chapter. */
function resolveTeleportTarget(): HTMLElement | null {
  if (typeof document === 'undefined') return null
  return document.querySelector<HTMLElement>(ACTIVE_SIDEBAR_ITEM_SELECTOR)
}

/** Extract readable heading text while stripping VitePress anchor `#` suffixes and zero-width spaces. */
function cleanHeadingText(el: Element): string {
  const raw = (el.textContent ?? '').replace(/\u200b/g, '').trim()
  return raw.replace(/\s*#$/, '').trim()
}

/** Recompute current section highlight from the vertical scroll position of `.vp-doc` headings. */
function updateActiveSection() {
  if (typeof window === 'undefined' || headings.value.length === 0) return
  const docEl = document.documentElement
  // Keep short trailing sections (for example, closing verification) active when scrolled all the way to the bottom.
  if (
    window.scrollY > 0 &&
    window.innerHeight + window.scrollY >= docEl.scrollHeight - SCROLLSPY_BOTTOM_EPSILON_PX
  ) {
    activeId.value = headings.value[headings.value.length - 1].id
    return
  }
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

/** Collect visible `h2`/`h3` headings and attach the outline inside the active sidebar entry. */
function refreshHeadings() {
  if (typeof document === 'undefined') return
  teleportTarget.value = resolveTeleportTarget()
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

let isUnmounted = false

onContentUpdated(async () => {
  await nextTick()
  if (isUnmounted) return
  refreshHeadings()
})

onMounted(async () => {
  // Wait one tick after mount so VPSidebar renders `.VPSidebarItem.is-active` before resolving teleport target.
  await nextTick()
  if (isUnmounted) return
  refreshHeadings()
  if (typeof window !== 'undefined') {
    window.addEventListener('scroll', updateActiveSection, { passive: true })
    window.addEventListener('resize', updateActiveSection, { passive: true })
  }
})

onUnmounted(() => {
  isUnmounted = true
  teleportTarget.value = null
  if (typeof window !== 'undefined') {
    window.removeEventListener('scroll', updateActiveSection)
    window.removeEventListener('resize', updateActiveSection)
  }
})
</script>

<template>
  <Teleport :to="teleportTarget ?? 'body'" :disabled="!teleportTarget">
    <nav
      v-if="headings.length > 0 && frontmatter.layout !== 'home'"
      aria-label="In This Chapter"
      class="sidebar-in-chapter"
      :class="{ 'is-nested': Boolean(teleportTarget) }"
    >
      <div v-if="!teleportTarget" class="sidebar-in-chapter-title">In This Chapter</div>
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
  </Teleport>
</template>
