import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import Layout from './Layout.vue'
import MermaidDiagram from './MermaidDiagram.vue'
import ModularRingAdder from './components/brain01/ModularRingAdder.vue'
import SignExtensionShifter from './components/brain01/SignExtensionShifter.vue'
import RiscvBitfieldDecoder from './components/brain01/RiscvBitfieldDecoder.vue'
import OracleStepTracer from './components/brain01/OracleStepTracer.vue'
import RiscvFormatMatrix from './components/brain01/RiscvFormatMatrix.vue'
import Product64Inspector from './components/brain01/Product64Inspector.vue'
import TruncatingDivisionComparator from './components/brain01/TruncatingDivisionComparator.vue'
import XapexMacDatapath from './components/brain01/XapexMacDatapath.vue'
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
    app.component('RiscvFormatMatrix', RiscvFormatMatrix)
    app.component('Product64Inspector', Product64Inspector)
    app.component('TruncatingDivisionComparator', TruncatingDivisionComparator)
    app.component('XapexMacDatapath', XapexMacDatapath)
  },
} satisfies Theme
