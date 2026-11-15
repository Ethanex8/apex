import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import Layout from './Layout.vue'
import MermaidDiagram from './MermaidDiagram.vue'
import TwosComplementWorkbench from './components/brain01/TwosComplementWorkbench.vue'
import RiscvBitfieldDecoder from './components/brain01/RiscvBitfieldDecoder.vue'
import OracleStepTracer from './components/brain01/OracleStepTracer.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout,
  enhanceApp({ app }) {
    app.component('MermaidDiagram', MermaidDiagram)
    app.component('TwosComplementWorkbench', TwosComplementWorkbench)
    app.component('RiscvBitfieldDecoder', RiscvBitfieldDecoder)
    app.component('OracleStepTracer', OracleStepTracer)
  },
} satisfies Theme
