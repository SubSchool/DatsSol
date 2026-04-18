<script setup lang="ts">
import { reactive, watch } from 'vue'

import Button from 'primevue/button'
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import type { LogEventItem, LogFilters } from '@/types/game'

const props = defineProps<{
  items: LogEventItem[]
  total: number
  loading: boolean
  filters: LogFilters
}>()

const emit = defineEmits<{
  (event: 'refresh', value: Partial<LogFilters>): void
  (event: 'export'): void
}>()

const localFilters = reactive<LogFilters>({ ...props.filters })

watch(
  () => props.filters,
  (value) => Object.assign(localFilters, value),
  { deep: true },
)

const levelOptions = [
  { label: 'Все уровни', value: '' },
  { label: 'Info', value: 'info' },
  { label: 'Warn', value: 'warn' },
  { label: 'Error', value: 'error' },
]

const sourceOptions = [
  { label: 'Все endpoints', value: '' },
  { label: 'arena', value: 'arena' },
  { label: 'command', value: 'command' },
]

function severity(level: string) {
  if (level === 'error') return 'danger'
  if (level === 'warn') return 'warn'
  if (level === 'info') return 'info'
  return 'secondary'
}

function requestPreview(item: LogEventItem) {
  return JSON.stringify((item.payload?.request ?? {}) as Record<string, unknown>, null, 2)
}

function responsePreview(item: LogEventItem) {
  if (item.payload?.response) {
    return JSON.stringify(item.payload.response as Record<string, unknown>, null, 2)
  }
  if (item.payload?.error) {
    return String(item.payload.error)
  }
  return '{}'
}
</script>

<template>
  <Card class="panel-card">
    <template #title>API Trace Игры</template>
    <template #content>
      <div class="filters-toolbar">
        <div class="toolbar-grid toolbar-grid--api">
          <Select v-model="localFilters.level" :options="levelOptions" option-label="label" option-value="value" placeholder="Уровень" />
          <Select v-model="localFilters.source" :options="sourceOptions" option-label="label" option-value="value" placeholder="Endpoint" />
          <InputText v-model="localFilters.search" placeholder="Поиск по endpoint / payload" />
          <InputNumber v-model="localFilters.tickFrom" placeholder="Ход от" />
          <InputNumber v-model="localFilters.tickTo" placeholder="Ход до" />
        </div>
        <div class="filters-actions">
          <Button icon="pi pi-filter" label="Применить" @click="emit('refresh', { ...localFilters, category: 'api' })" />
          <Button icon="pi pi-download" label="CSV" severity="secondary" @click="emit('export')" />
        </div>
      </div>

      <div class="table-meta">
        <span>Всего API-событий: {{ total }}</span>
      </div>

      <DataTable :value="items" :loading="loading" scrollable scroll-height="72vh" striped-rows show-gridlines data-key="id">
        <Column field="created_at" header="Время" style="min-width: 12rem">
          <template #body="{ data }">
            {{ new Date(data.created_at).toLocaleString() }}
          </template>
        </Column>
        <Column field="turn_number" header="Ход" style="min-width: 6rem" />
        <Column field="level" header="Level" style="min-width: 7rem">
          <template #body="{ data }">
            <Tag :severity="severity(data.level)" :value="data.level" />
          </template>
        </Column>
        <Column field="source" header="Source" style="min-width: 7rem" />
        <Column field="message" header="Endpoint" style="min-width: 14rem" />
        <Column header="Request" style="min-width: 22rem">
          <template #body="{ data }">
            <pre class="payload-preview">{{ requestPreview(data) }}</pre>
          </template>
        </Column>
        <Column header="Response / Error" style="min-width: 24rem">
          <template #body="{ data }">
            <pre class="payload-preview">{{ responsePreview(data) }}</pre>
          </template>
        </Column>
      </DataTable>
    </template>
  </Card>
</template>
