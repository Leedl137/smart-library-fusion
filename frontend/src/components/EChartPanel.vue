<template>
  <div ref="chartRef" class="echart-panel"></div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: {
    type: Object,
    required: true
  }
})

const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null
let intersectionObserver = null

function renderChart() {
  if (!chartRef.value) return
  const rect = chartRef.value.getBoundingClientRect()
  // 容器被隐藏（display:none）时不初始化，避免在 0 宽度下渲染
  if (rect.width === 0 || rect.height === 0) return
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption(props.option, true)
  nextTick(() => chartInstance?.resize())
}

function resizeChart() {
  chartInstance?.resize()
}

onMounted(() => {
  renderChart()
  window.addEventListener('resize', resizeChart)

  // ResizeObserver：监听容器尺寸变化
  if (typeof ResizeObserver !== 'undefined' && chartRef.value) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          chartInstance?.resize()
        }
      }
    })
    resizeObserver.observe(chartRef.value)
  }

  // IntersectionObserver：检测从 display:none 恢复为可见时重新渲染
  if (typeof IntersectionObserver !== 'undefined' && chartRef.value) {
    intersectionObserver = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          nextTick(() => {
            renderChart()
            chartInstance?.resize()
          })
        }
      }
    })
    intersectionObserver.observe(chartRef.value)
  }
})

watch(() => props.option, renderChart, { deep: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  resizeObserver?.disconnect()
  intersectionObserver?.disconnect()
  chartInstance?.dispose()
  chartInstance = null
})
</script>
