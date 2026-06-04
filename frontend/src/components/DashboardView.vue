<template>
  <div class="page-stack">
    <div class="page-heading">
      <div>
        <h2>数据大屏</h2>
        <p>汇总读者规模、馆藏资源、借阅热度与空间使用趋势。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadDashboard">重新请求</el-button>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      description="请稍后重试或检查数据服务状态。"
    />

    <el-row :gutter="14">
      <el-col v-for="metric in metrics" :key="metric.label" :xs="24" :sm="12" :lg="6">
        <div class="metric-card">
          <div class="metric-label">{{ metric.label }}</div>
          <div class="metric-value">{{ formatNumber(metric.value) }}</div>
          <div class="metric-delta">{{ metric.delta || '在线数据' }}</div>
        </div>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && !error && !charts.length" description="暂无图表数据" />

    <el-row :gutter="14">
      <el-col v-for="(chart, index) in chartOptions" :key="index" :xs="24" :lg="wideChart(index) ? 24 : 12">
        <div class="panel chart-card">
          <EChartPanel :option="chart" />
        </div>
      </el-col>
    </el-row>

    <section v-if="queryPanels.length" class="panel report-block">
      <div class="report-heading">
        <div>
          <h3>核心指标分析</h3>
          <p>围绕访问流量、空间热度、学院借阅与读者画像展开多维分析。</p>
        </div>
        <el-tag effect="light">Insight</el-tag>
      </div>

      <el-tabs v-model="activeCategory">
        <el-tab-pane v-for="category in categories" :key="category" :label="category" :name="category" lazy>
          <div class="query-grid">
            <article v-for="panel in panelsByCategory(category)" :key="panel.title" class="query-card">
              <div class="query-card-head">
                <div>
                  <h4>{{ panel.title }}</h4>
                  <p>{{ panel.meaning }}</p>
                </div>
                <el-tag v-if="panel.type !== 'table'" size="small">{{ panel.type }}</el-tag>
              </div>

              <el-alert v-if="panel.error" :title="panel.error" type="warning" show-icon :closable="false" />

              <EChartPanel v-if="panelChart(panel)" :option="panelChart(panel)" />

              <el-table
                v-if="panel.data?.length"
                :data="panel.data"
                border
                stripe
                class="dashboard-table"
                max-height="280"
              >
                <el-table-column
                  v-for="column in panelColumns(panel)"
                  :key="column"
                  :prop="column"
                  :label="column"
                  min-width="130"
                  show-overflow-tooltip
                />
              </el-table>

              <el-empty v-if="!panel.error && !panel.data?.length" description="暂无结果" />

              <el-collapse class="sql-collapse">
                <el-collapse-item title="查看查询语句" name="sql">
                  <pre>{{ panel.sql }}</pre>
                </el-collapse-item>
              </el-collapse>
            </article>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>

    <section v-if="reportSections.length" class="report-summary">
      <div v-for="section in reportSections" :key="section.title" class="panel report-card">
        <h3>{{ section.title }}</h3>
        <ul>
          <li v-for="item in section.items" :key="item">{{ item }}</li>
        </ul>
        <el-collapse v-if="section.sql">
          <el-collapse-item title="查看优化语句" name="sql">
            <pre>{{ section.sql }}</pre>
          </el-collapse-item>
        </el-collapse>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { getDashboardOverview, getDashboardExtra } from '../api/client'
import { buildFixedChartOption, buildQueryPanelOption } from '../utils/chartFactory'
import EChartPanel from './EChartPanel.vue'

const loading = ref(false)
const error = ref('')
const metrics = ref([])
const charts = ref([])
const queryPanels = ref([])
const reportSections = ref([])
const activeCategory = ref('')

// tab 切换后延迟触发图表 resize，解决 el-tabs display:none 导致的尺寸挤压
watch(activeCategory, () => {
  nextTick(() => {
    setTimeout(() => {
      window.dispatchEvent(new Event('resize'))
    }, 150)
  })
})

const chartOptions = computed(() => charts.value.map((chart) => buildFixedChartOption(chart)))
const categories = computed(() => [...new Set(queryPanels.value.map((panel) => panel.category || '其他'))])

function wideChart(index) {
  return index === 2 || index === 3
}

function formatNumber(value) {
  if (typeof value === 'number') return value.toLocaleString('zh-CN')
  return value ?? '-'
}

function panelsByCategory(category) {
  return queryPanels.value.filter((panel) => (panel.category || '其他') === category)
}

function panelColumns(panel) {
  if (panel.columns?.length) return panel.columns
  if (panel.data?.length) return Object.keys(panel.data[0])
  return []
}

function panelChart(panel) {
  return buildQueryPanelOption(panel)
}

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const payload = await getDashboardOverview()
    metrics.value = payload.metrics || []
    charts.value = payload.charts || []
    queryPanels.value = payload.queryPanels || []
    reportSections.value = payload.reportSections || []
    activeCategory.value = categories.value[0] || ''
  } catch (err) {
    metrics.value = []
    charts.value = []
    queryPanels.value = []
    reportSections.value = []
    error.value = err.message || '数据大屏加载失败'
  } finally {
    loading.value = false
  }

  // 异步加载扩展图表（不阻塞核心大屏）
  try {
    const extra = await getDashboardExtra()
    if (extra.charts?.length) {
      charts.value.push(...extra.charts)
    }
    if (extra.queryPanels?.length) {
      queryPanels.value.push(...extra.queryPanels)
    }
    if (extra.reportSections?.length) {
      reportSections.value.push(...extra.reportSections)
    }
  } catch (err) {
    console.warn('扩展图表加载失败:', err)
  }
}

onMounted(loadDashboard)
</script>
