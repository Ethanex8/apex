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
      fontFamily: 'var(--vp-font-family-base)',
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
