<template>
  <el-container class="app-shell">
    <el-aside width="248px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">SL</div>
        <div>
          <div class="brand-title">SmartLib</div>
          <div class="brand-subtitle">智慧图书馆分析平台</div>
        </div>
      </div>

      <el-menu :default-active="activeView" class="nav-menu" @select="activeView = $event">
        <el-menu-item index="dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>数据大屏</span>
        </el-menu-item>
        <el-menu-item index="chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        <el-menu-item index="advanced">
          <el-icon><DataAnalysis /></el-icon>
          <span>复杂行为挖掘</span>
        </el-menu-item>
        <el-menu-item index="config">
          <el-icon><Setting /></el-icon>
          <span>模型配置</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <el-tag :type="aiConfigured ? 'success' : 'warning'" effect="light">
          {{ aiConfigured ? 'AI 已配置' : '等待 AI Key' }}
        </el-tag>
        <div class="api-base">SmartLib Analytics</div>
      </div>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div>
          <h1>智慧图书馆数据库问答系统</h1>
          <p>融合馆藏、借阅、门禁与座位日志，呈现可交互的数据洞察。</p>
        </div>
        <el-button type="primary" :icon="Refresh" @click="refreshStatus">刷新状态</el-button>
      </el-header>

      <el-main class="main-view">
        <DashboardView v-if="activeView === 'dashboard'" />
        <ChatView v-else-if="activeView === 'chat'" :ai-configured="aiConfigured" @open-config="activeView = 'config'" />
        <AdvancedMiningView v-else-if="activeView === 'advanced'" />
        <ApiKeyConfig v-else @saved="refreshStatus" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ChatDotRound, DataAnalysis, DataBoard, Refresh, Setting } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { API_BASE, getAiConfigStatus } from './api/client'
import DashboardView from './components/DashboardView.vue'
import ChatView from './components/ChatView.vue'
import AdvancedMiningView from './components/AdvancedMiningView.vue'
import ApiKeyConfig from './components/ApiKeyConfig.vue'

const activeView = ref('dashboard')
const aiConfigured = ref(false)
const apiBase = API_BASE

async function refreshStatus() {
  try {
    const status = await getAiConfigStatus()
    aiConfigured.value = Boolean(status.configured)
  } catch (error) {
    aiConfigured.value = false
    ElMessage.warning('模型状态暂不可用。')
  }
}

onMounted(refreshStatus)
</script>
