<template>
  <div class="chat-layout">
    <section class="chat-main panel">
      <div class="chat-header">
        <div>
          <h2>智能问答</h2>
          <p>用自然语言探索馆藏、借阅、空间与读者行为数据。</p>
        </div>
        <el-button v-if="!aiConfigured" type="warning" @click="$emit('open-config')">配置 AI Key</el-button>
      </div>

      <el-alert
        v-if="!aiConfigured"
        title="模型尚未配置"
        type="warning"
        show-icon
        :closable="false"
        description="请先完成模型配置。"
      />

      <div class="messages">
        <div v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
          <div class="bubble">
            <div class="message-role">{{ message.role === 'user' ? '用户' : 'SmartLib Assistant' }}</div>
            <div class="message-content">{{ message.content }}</div>

            <el-collapse v-if="message.payload?.sql" class="sql-collapse">
              <el-collapse-item title="查看查询语句" name="sql">
                <pre>{{ message.payload.sql }}</pre>
              </el-collapse-item>
            </el-collapse>

            <EChartPanel v-if="chartOption(message.payload)" :option="chartOption(message.payload)" />

            <el-table
              v-if="message.payload?.data?.length"
              :data="message.payload.data"
              border
              stripe
              class="result-table"
              max-height="320"
            >
              <el-table-column
                v-for="column in tableColumns(message.payload)"
                :key="column"
                :prop="column"
                :label="column"
                min-width="120"
              />
            </el-table>
          </div>
        </div>
      </div>

      <div class="input-row">
        <el-input
          v-model="question"
          :disabled="loading || !aiConfigured"
          type="textarea"
          :rows="2"
          resize="none"
          placeholder="例如：帮我统计各学院在 2017 年的借阅排行并画柱状图"
          @keydown.ctrl.enter="sendQuestion"
        />
        <el-button type="primary" :loading="loading" :disabled="!aiConfigured" @click="sendQuestion">发送</el-button>
      </div>
    </section>

    <aside class="side-panel panel">
      <h3>推荐问题</h3>
      <el-button v-for="item in examples" :key="item" text class="example-button" @click="question = item">
        {{ item }}
      </el-button>
      <el-divider />
    </aside>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { askNl2Sql, getAdvancedSkill } from '../api/client'
import { buildResponseChartOption } from '../utils/chartFactory'
import EChartPanel from './EChartPanel.vue'

const props = defineProps({
  aiConfigured: {
    type: Boolean,
    default: false
  }
})

defineEmits(['open-config'])

const question = ref('')
const loading = ref(false)
const advancedSkill = ref('')
const messages = ref([
  {
    role: 'assistant',
    content: '你好，我可以帮助你查询图书馆业务数据，并把结果整理成表格或图表。'
  }
])

const examples = [
  '帮我统计各学院借阅次数排行并画柱状图',
  '找出沉浸自习但极低借阅的读者',
  '找出学院内部借阅量超过本院平均两倍的卷王',
  '找出 2018 年 6 月连续打卡满 7 天的读者',
  '计算各阅览室历史瞬时最高并发人数',
  '展示图书分类流通率对比',
  '找出频繁进馆但从未借阅实体书的自习型读者',
  '展示近 12 个月借阅趋势折线图'
]

function tableColumns(payload) {
  if (!payload?.data?.length) return []
  return payload.columns?.length ? payload.columns : Object.keys(payload.data[0])
}

function chartOption(payload) {
  return buildResponseChartOption(payload)
}

function historyPayload() {
  return messages.value.slice(-8).map((message) => ({
    role: message.role,
    content: message.content
  }))
}

async function sendQuestion() {
  const text = question.value.trim()
  if (!text) return
  if (!props.aiConfigured) {
    ElMessage.warning('请先完成模型配置。')
    return
  }

  messages.value.push({ role: 'user', content: text })
  question.value = ''
  loading.value = true

  try {
    const payload = await askNl2Sql({
      question: text,
      history: historyPayload(),
      skill: advancedSkill.value
    })
    messages.value.push({
      role: 'assistant',
      content: payload.answer || '查询完成。',
      payload
    })
  } catch (error) {
    messages.value.push({
      role: 'assistant',
      content: error.message || '暂时无法完成查询，请稍后重试。'
    })
  } finally {
    loading.value = false
  }
}

async function reloadAdvancedSkill() {
  try {
    const payload = await getAdvancedSkill()
    advancedSkill.value = payload.skill || ''
  } catch (error) {
    advancedSkill.value = ''
  }
}

onMounted(reloadAdvancedSkill)
</script>
