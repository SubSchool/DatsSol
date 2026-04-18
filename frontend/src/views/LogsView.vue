<script setup lang="ts">
import { onMounted, ref } from 'vue'

import ApiTraceTable from '@/components/logs/ApiTraceTable.vue'
import LogsTable from '@/components/logs/LogsTable.vue'
import ServerLogsPanel from '@/components/logs/ServerLogsPanel.vue'
import { useCommandCenterStore } from '@/stores/commandCenter'
import type { LogFilters } from '@/types/game'

const store = useCommandCenterStore()
const activeTab = ref<'planner' | 'api'>('planner')

onMounted(() => {
  if (store.logs.length === 0 && store.apiLogs.length === 0) {
    void Promise.all([store.fetchLogs(), store.fetchApiLogs(), store.fetchServerLogs()])
  }
})

function refresh(filters: Partial<LogFilters>) {
  void store.fetchLogs(filters)
}

function refreshApi(filters: Partial<LogFilters>) {
  void store.fetchApiLogs(filters)
}
</script>

<template>
  <section class="logs-grid">
    <div class="logs-primary">
      <div class="log-tab-nav">
        <button type="button" class="log-tab-button" :class="{ 'log-tab-button--active': activeTab === 'planner' }" @click="activeTab = 'planner'">
          Логи Планировщика
        </button>
        <button type="button" class="log-tab-button" :class="{ 'log-tab-button--active': activeTab === 'api' }" @click="activeTab = 'api'">
          API Trace
        </button>
      </div>

      <LogsTable
        v-if="activeTab === 'planner'"
        :items="store.logs"
        :total="store.logTotal"
        :loading="store.logsLoading"
        :filters="store.logFilters"
        @refresh="refresh"
        @export="store.exportLogs()"
      />

      <ApiTraceTable
        v-else
        :items="store.apiLogs"
        :total="store.apiLogTotal"
        :loading="store.apiLogsLoading"
        :filters="store.apiLogFilters"
        @refresh="refreshApi"
        @export="store.exportApiLogs()"
      />
    </div>
    <ServerLogsPanel :items="store.serverLogs" />
  </section>
</template>
