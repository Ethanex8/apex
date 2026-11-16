import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import Layout from './Layout.vue'
import MermaidDiagram from './MermaidDiagram.vue'
import ModularRingAdder from './components/brain01/ModularRingAdder.vue'
import SignExtensionShifter from './components/brain01/SignExtensionShifter.vue'
import RiscvBitfieldDecoder from './components/brain01/RiscvBitfieldDecoder.vue'
import OracleStepTracer from './components/brain01/OracleStepTracer.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout,
  enhanceApp({ app }) {
    app.component('MermaidDiagram', MermaidDiagram)
    app.component('ModularRingAdder', ModularRingAdder)
    app.component('SignExtensionShifter', SignExtensionShifter)
    app.component('RiscvBitfieldDecoder', RiscvBitfieldDecoder)
    app.component('OracleStepTracer', OracleStepTracer)
  },
} satisfies Theme
