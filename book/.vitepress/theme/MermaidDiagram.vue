<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useData } from 'vitepress'

const props = defineProps<{
  code: string
}>()

const { isDark } = useData()
const svgHtml = ref<string>('')
const errorMsg = ref<string>('')

async function renderChart() {
  if (typeof window === 'undefined') return
  try {
    const mermaidMod = await import('mermaid')
    const mermaid = mermaidMod.default
    mermaid.initialize({
      startOnLoad: false,
      theme: isDark.value ? 'dark' : 'neutral',
      securityLevel: 'strict',
      fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      themeVariables: {
        fontSize: '14px',
        fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      },
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        padding: 18,
        nodeSpacing: 32,
        rankSpacing: 38,
      },
      sequence: {
        useMaxWidth: true,
        diagramMarginX: 12,
        diagramMarginY: 10,
        actorMargin: 28,
        width: 125,
        boxMargin: 6,
        noteMargin: 6,
        messageMargin: 26,
      },
    })
    const decoded = decodeURIComponent(props.code)
    const id = `mermaid-${Math.random().toString(36).slice(2, 10)}`
    const { svg } = await mermaid.render(id, decoded)
    svgHtml.value = svg
    errorMsg.value = ''
  } catch (err) {
    errorMsg.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(() => {
  renderChart()
})

watch(isDark, () => {
  renderChart()
})
</script>

<template>
  <div class="mermaid-book-figure">
    <div v-if="errorMsg" class="mermaid-error">{{ errorMsg }}</div>
    <div v-else class="mermaid-svg-wrap" v-html="svgHtml"></div>
  </div>
</template>
