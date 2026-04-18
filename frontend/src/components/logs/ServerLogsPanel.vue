<script setup lang="ts">
import Card from 'primevue/card'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'

import type { GameServerLogEntry } from '@/types/game'

defineProps<{
  items: GameServerLogEntry[]
}>()
</script>

<template>
  <Card class="panel-card">
    <template #title>Игровые Логи Сервера</template>
    <template #content>
      <DataTable :value="items" scrollable scroll-height="72vh" striped-rows show-gridlines>
        <Column field="time" header="Время" style="min-width: 10rem" />
        <Column field="message" header="Сообщение" style="min-width: 28rem" />
      </DataTable>
    </template>
  </Card>
</template>
