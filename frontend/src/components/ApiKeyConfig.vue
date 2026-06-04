<template>
  <div class="page-stack">
    <div class="page-heading">
      <div>
        <h2>模型配置</h2>
        <p>配置智能问答所使用的模型服务。</p>
      </div>
    </div>

    <el-form :model="form" label-position="top" class="config-form">
      <el-row :gutter="16">
        <el-col :xs="24" :md="8">
          <el-form-item label="模型供应商">
            <el-select v-model="form.provider" placeholder="选择供应商">
              <el-option label="DeepSeek" value="deepseek" />
              <el-option label="通义千问 Qwen" value="qwen" />
              <el-option label="Kimi" value="kimi" />
              <el-option label="OpenAI 兼容服务" value="openai-compatible" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-form-item label="模型名称">
            <el-input v-model="form.model" placeholder="例如 deepseek-chat / qwen-plus" />
          </el-form-item>
        </el-col>
        <el-col :xs="24" :md="8">
          <el-form-item label="Base URL">
            <el-input v-model="form.base_url" placeholder="https://api.deepseek.com" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="API Key">
        <el-input
          v-model="form.api_key"
          type="password"
          show-password
          placeholder="sk-..."
          autocomplete="off"
        />
      </el-form-item>

      <el-form-item label="系统约束">
        <el-input v-model="form.skill" type="textarea" :rows="7" />
      </el-form-item>

      <div class="button-row">
        <el-button :loading="testing" @click="testConfig">测试连接</el-button>
        <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { saveAiConfig, testAiConfig } from '../api/client'

const emit = defineEmits(['saved'])

const defaultSkill = `你是 SmartLib 的数据问答助手。请根据智慧图书馆数据结构和用户问题生成只读 SELECT SQL，并返回推荐图表类型。禁止生成 DROP、DELETE、UPDATE、INSERT、ALTER 等危险语句。`

const form = reactive({
  provider: 'deepseek',
  model: 'deepseek-chat',
  base_url: 'https://api.deepseek.com',
  api_key: '',
  skill: defaultSkill
})

const testing = ref(false)
const saving = ref(false)

function validate() {
  if (!form.provider || !form.model || !form.base_url || !form.api_key) {
    ElMessage.warning('请完整填写供应商、模型、Base URL 和 API Key。')
    return false
  }
  return true
}

async function testConfig() {
  if (!validate()) return
  testing.value = true
  try {
    await testAiConfig(form)
    ElMessage.success('AI 配置测试成功。')
  } catch (error) {
    ElMessage.error(error.message || 'AI 配置测试失败。')
  } finally {
    testing.value = false
  }
}

async function saveConfig() {
  if (!validate()) return
  saving.value = true
  try {
    await saveAiConfig(form)
    ElMessage.success('模型配置已保存。')
    form.api_key = ''
    emit('saved')
  } catch (error) {
    ElMessage.error(error.message || 'AI Key 保存失败。')
  } finally {
    saving.value = false
  }
}
</script>
