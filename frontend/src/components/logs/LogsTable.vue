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
  { label: 'Debug', value: 'debug' },
  { label: 'Info', value: 'info' },
  { label: 'Warn', value: 'warn' },
  { label: 'Error', value: 'error' },
]

const categoryOptions = [
  { label: 'Все категории', value: '' },
  { label: 'observe', value: 'observe' },
  { label: 'analyze', value: 'analyze' },
  { label: 'decide', value: 'decide' },
  { label: 'execute', value: 'execute' },
  { label: 'submit', value: 'submit' },
  { label: 'manual', value: 'manual' },
  { label: 'runtime', value: 'runtime' },
  { label: 'command', value: 'command' },
  { label: 'strategy', value: 'strategy' },
]

const sourceOptions = [
  { label: 'Все источники', value: '' },
  { label: 'control', value: 'control' },
  { label: 'pipeline', value: 'pipeline' },
  { label: 'planner', value: 'planner' },
  { label: 'provider', value: 'provider' },
  { label: 'engine', value: 'engine' },
  { label: 'operator', value: 'operator' },
]

function severity(level: string) {
  if (level === 'error') return 'danger'
  if (level === 'warn') return 'warn'
  if (level === 'info') return 'info'
  return 'secondary'
}
</script>

<template>
  <Card class="panel-card">
    <template #title>Логи Планировщика</template>
    <template #content>
      <div class="filters-toolbar">
        <div class="toolbar-grid">
          <Select v-model="localFilters.level" :options="levelOptions" option-label="label" option-value="value" placeholder="Уровень" />
          <Select v-model="localFilters.category" :options="categoryOptions" option-label="label" option-value="value" placeholder="Категория" />
          <Select v-model="localFilters.source" :options="sourceOptions" option-label="label" option-value="value" placeholder="Источник" />
          <InputText v-model="localFilters.search" placeholder="Поиск по сообщению" />
          <InputNumber v-model="localFilters.tickFrom" placeholder="Ход от" />
          <InputNumber v-model="localFilters.tickTo" placeholder="Ход до" />
        </div>
        <div class="filters-actions">
          <Button icon="pi pi-filter" label="Применить" @click="emit('refresh', localFilters)" />
          <Button icon="pi pi-download" label="CSV" severity="secondary" @click="emit('export')" />
        </div>
      </div>

      <div class="table-meta">
        <span>Всего строк: {{ total }}</span>
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
        <Column field="category" header="Category" style="min-width: 8rem" />
        <Column field="source" header="Source" style="min-width: 8rem" />
        <Column field="message" header="Сообщение" style="min-width: 24rem" />
        <Column field="payload" header="Payload" style="min-width: 24rem">
          <template #body="{ data }">
            <pre class="payload-preview">{{ JSON.stringify(data.payload, null, 2) }}</pre>
          </template>
        </Column>
      </DataTable>
    </template>
  </Card>
</template>
