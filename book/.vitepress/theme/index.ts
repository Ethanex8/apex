import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import Layout from './Layout.vue'
import MermaidDiagram from './MermaidDiagram.vue'
import BinaryAdditionCarryDiagram from './components/brain01/BinaryAdditionCarryDiagram.vue'
import UnsignedClockRing from './components/brain01/UnsignedClockRing.vue'
import ModularRingAdder from './components/brain01/ModularRingAdder.vue'
import SignExtensionWidener from './components/brain01/SignExtensionWidener.vue'
import RightShiftComparator from './components/brain01/RightShiftComparator.vue'
import RiscvBitfieldDecoder from './components/brain01/RiscvBitfieldDecoder.vue'
import OracleStepTracer from './components/brain01/OracleStepTracer.vue'
import RiscvFormatMatrix from './components/brain01/RiscvFormatMatrix.vue'
import Product64SplitDiagram from './components/brain01/Product64SplitDiagram.vue'
import LuiBiasCarryDiagram from './components/brain01/LuiBiasCarryDiagram.vue'
import TimerRolloverTearDiagram from './components/brain01/TimerRolloverTearDiagram.vue'
import TruncatingDivisionComparator from './components/brain01/TruncatingDivisionComparator.vue'
import XapexMacDatapath from './components/brain01/XapexMacDatapath.vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout,
  enhanceApp({ app }) {
    app.component('MermaidDiagram', MermaidDiagram)
    app.component('BinaryAdditionCarryDiagram', BinaryAdditionCarryDiagram)
    app.component('UnsignedClockRing', UnsignedClockRing)
    app.component('ModularRingAdder', ModularRingAdder)
    app.component('SignExtensionWidener', SignExtensionWidener)
    app.component('RightShiftComparator', RightShiftComparator)
    app.component('RiscvBitfieldDecoder', RiscvBitfieldDecoder)
    app.component('OracleStepTracer', OracleStepTracer)
    app.component('RiscvFormatMatrix', RiscvFormatMatrix)
    app.component('Product64SplitDiagram', Product64SplitDiagram)
    app.component('LuiBiasCarryDiagram', LuiBiasCarryDiagram)
    app.component('TimerRolloverTearDiagram', TimerRolloverTearDiagram)
    app.component('TruncatingDivisionComparator', TruncatingDivisionComparator)
    app.component('XapexMacDatapath', XapexMacDatapath)
  },
} satisfies Theme
