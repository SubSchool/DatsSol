<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

import Tag from 'primevue/tag'

import { useCommandCenterStore } from '@/stores/commandCenter'

const store = useCommandCenterStore()
const route = useRoute()

const statusSeverity = computed(() => {
  if (store.runtime?.status === 'running') return 'success'
  if (store.runtime?.status === 'error') return 'danger'
  return 'warn'
})

const submitModeSeverity = computed(() => {
  if (store.runtime?.submit_mode === 'live') return 'danger'
  if (store.runtime?.submit_mode === 'dry-run') return 'info'
  return 'secondary'
})

onMounted(() => {
  void store.bootstrap()
})
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="brand-block">
        <p class="eyebrow">DatsSol Command Bridge</p>
        <h1>Desert Bloom Operations</h1>
        <p class="subhead">
          Тактическая консоль для связной экспансии, переноса ЦУ, boosted-клеток, бобров и ручных override-команд.
        </p>
      </div>

      <div class="header-meta">
        <div class="meta-chip">
          <span class="meta-label">Provider</span>
          <strong>{{ store.runtime?.provider_label ?? 'Booting' }}</strong>
        </div>
        <div class="meta-chip">
          <span class="meta-label">Turn</span>
          <strong>{{ store.runtime?.current_turn ?? 0 }}</strong>
        </div>
        <div class="meta-chip">
          <span class="meta-label">Strategy</span>
          <strong>{{ store.runtime?.active_strategy_key ?? 'frontier' }}</strong>
        </div>
        <Tag rounded :severity="statusSeverity" :value="store.runtime?.status ?? 'booting'" />
        <Tag rounded :severity="submitModeSeverity" :value="store.runtime?.submit_mode ?? 'mock'" />
      </div>
    </header>

    <div v-if="store.runtime?.provider_status?.message" class="provider-banner">
      <span>{{ store.runtime.provider_status.message }}</span>
    </div>

    <nav class="main-nav">
      <RouterLink
        to="/visualization"
        class="nav-link"
        :class="{ active: route.path.startsWith('/visualization') }"
      >
        Карта И Управление
      </RouterLink>
      <RouterLink
        to="/logs"
        class="nav-link"
        :class="{ active: route.path.startsWith('/logs') }"
      >
        Логи И Экспорт
      </RouterLink>
    </nav>

    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>
