<template>
  <div class="page-stack">
    <div class="page-heading">
      <div>
        <h2>复杂行为挖掘</h2>
        <p>识别高价值读者群体、连续访问行为、空间峰值与馆藏流通效率。</p>
      </div>
      <div class="button-row">
        <el-button :loading="loading" @click="loadAdvanced">重新请求</el-button>
      </div>
    </div>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
      description="请稍后重试或检查数据服务状态。"
    />

    <section class="advanced-hero panel">
      <div>
        <div class="hero-kicker">ADVANCED SQL MINING</div>
        <h3>从数据统计进入行为洞察</h3>
        <p>通过集合运算、窗口函数与事件流分析，挖掘图书馆服务运营中的关键模式。</p>
      </div>
      <div class="advanced-stats">
        <div>
          <strong>{{ queryPanels.length }}</strong>
          <span>高级查询</span>
        </div>
        <div>
          <strong>{{ categories.length }}</strong>
          <span>分析主题</span>
        </div>
      </div>
    </section>

    <el-tabs v-if="queryPanels.length" v-model="activeCategory" class="advanced-tabs">
      <el-tab-pane v-for="category in categories" :key="category" :label="category" :name="category">
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
              max-height="320"
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
import { computed, onMounted, ref } from 'vue'
import { getAdvancedQueries } from '../api/client'
import { buildQueryPanelOption } from '../utils/chartFactory'
import EChartPanel from './EChartPanel.vue'

const loading = ref(false)
const error = ref('')
const queryPanels = ref([])
const reportSections = ref([])
const aiSkill = ref('')
const activeCategory = ref('')

const categories = computed(() => [...new Set(queryPanels.value.map((panel) => panel.category || '其他'))])

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

async function loadAdvanced() {
  loading.value = true
  error.value = ''
  try {
    const payload = await getAdvancedQueries()
    queryPanels.value = payload.queryPanels || []
    reportSections.value = payload.reportSections || []
    aiSkill.value = payload.aiSkill || ''
    activeCategory.value = categories.value[0] || ''
  } catch (err) {
    queryPanels.value = []
    reportSections.value = []
    aiSkill.value = ''
    error.value = err.message || '复杂行为挖掘加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadAdvanced)
</script>
