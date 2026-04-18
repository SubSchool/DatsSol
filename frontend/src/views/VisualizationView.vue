<script setup lang="ts">
import { ref } from 'vue'

import Card from 'primevue/card'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

import ControlPanel from '@/components/control/ControlPanel.vue'
import InspectorCard from '@/components/dashboard/InspectorCard.vue'
import PlanBoard from '@/components/dashboard/PlanBoard.vue'
import GameCanvas from '@/components/map/GameCanvas.vue'
import { useCommandCenterStore } from '@/stores/commandCenter'
import type { Coordinate, ManualDirectiveKind } from '@/types/game'

const store = useCommandCenterStore()

const commandMode = ref(false)
const manualActionKind = ref<ManualDirectiveKind>('build')
const selectedPlantationIds = ref<string[]>([])
const controlDrawerOpen = ref(false)
const canvasRef = ref<InstanceType<typeof GameCanvas> | null>(null)
const inspected = ref<{
  entityKind: string
  entityId?: string
  position: Coordinate
  own?: boolean
} | null>(null)

function focusMainPlantation() {
  canvasRef.value?.focusMainPlantation()
}

async function onCommandTarget(payload: {
  entityKind: string
  entityId?: string
  position: Coordinate
  own?: boolean
}) {
  if (!commandMode.value || !store.world) return

  if (manualActionKind.value === 'build') {
    await store.createDirective({
      kind: 'build',
      author_ids: selectedPlantationIds.value,
      target_position: payload.position,
      ttl_turns: 4,
      note: `manual build ${payload.position.x},${payload.position.y}`,
    })
    return
  }

  if (manualActionKind.value === 'repair' && payload.entityKind === 'plantation' && payload.own && payload.entityId) {
    await store.createDirective({
      kind: 'repair',
      author_ids: selectedPlantationIds.value,
      target_position: payload.position,
      target_entity_id: payload.entityId,
      ttl_turns: 2,
      note: `manual repair ${payload.entityId}`,
    })
    return
  }

  if (manualActionKind.value === 'sabotage' && payload.entityKind === 'enemy' && payload.entityId) {
    await store.createDirective({
      kind: 'sabotage',
      author_ids: selectedPlantationIds.value,
      target_position: payload.position,
      target_entity_id: payload.entityId,
      ttl_turns: 2,
      note: `manual sabotage ${payload.entityId}`,
    })
    return
  }

  if (manualActionKind.value === 'beaver_attack' && payload.entityKind === 'beaver' && payload.entityId) {
    await store.createDirective({
      kind: 'beaver_attack',
      author_ids: selectedPlantationIds.value,
      target_position: payload.position,
      target_entity_id: payload.entityId,
      ttl_turns: 2,
      note: `manual beaver focus ${payload.entityId}`,
    })
    return
  }

  if (manualActionKind.value === 'relocate_main' && payload.entityKind === 'plantation' && payload.own && payload.entityId) {
    await store.createDirective({
      kind: 'relocate_main',
      relocate_to_id: payload.entityId,
      ttl_turns: 2,
      note: `manual relocate main ${payload.entityId}`,
    })
  }
}

function readinessSeverity(connected: number, isolated: number) {
  if (connected === 0) return 'danger'
  if (isolated > 0) return 'warn'
  return 'success'
}
</script>

<template>
  <section class="view-grid">
    <div class="visualization-toolbar">
      <div class="visualization-toolbar__meta">
        <Tag severity="info" :value="`Ход ${store.world?.turn ?? 0}`" />
        <Tag severity="success" :value="`Сеть ${store.world?.stats.connected_plantations ?? 0}`" />
        <Tag severity="warn" :value="`Бобры ${store.world?.stats.visible_beavers ?? 0}`" />
        <Tag severity="secondary" :value="`Выделено ${selectedPlantationIds.length}`" />
      </div>
      <div class="visualization-toolbar__actions">
        <Button
          icon="pi pi-crosshairs"
          label="Найти ЦУ"
          severity="secondary"
          outlined
          @click="focusMainPlantation"
        />
        <Button
          icon="pi pi-sliders-h"
          label="Панель управления"
          class="drawer-toggle-button"
          @click="controlDrawerOpen = true"
        />
      </div>
    </div>

    <Card class="canvas-card canvas-card--wide">
      <template #content>
        <GameCanvas
          ref="canvasRef"
          :world="store.world"
          :command-mode="commandMode"
          :manual-action-kind="manualActionKind"
          :selected-plantation-ids="selectedPlantationIds"
          @selection-change="selectedPlantationIds = $event"
          @command-target="onCommandTarget"
          @inspect-change="inspected = $event"
        />
      </template>
    </Card>

    <Drawer v-model:visible="controlDrawerOpen" position="right" class="control-drawer">
      <template #header>
        <div class="drawer-header">
          <div class="drawer-header__copy">
            <span class="drawer-eyebrow">DatsSol Ops</span>
            <strong>Командный Центр</strong>
          </div>
          <Tag :severity="store.runtime?.status === 'running' ? 'success' : store.runtime?.status === 'error' ? 'danger' : 'warn'" :value="store.runtime?.status ?? 'booting'" />
        </div>
      </template>

      <ControlPanel
        :runtime="store.runtime"
        :world="store.world"
        :selected-plantation-ids="selectedPlantationIds"
        :command-mode="commandMode"
        :manual-action-kind="manualActionKind"
        @update:command-mode="commandMode = $event"
        @update:manual-action-kind="manualActionKind = $event"
      />
    </Drawer>

    <div class="summary-grid">
      <Card class="summary-card">
        <template #title>Пульс Раунда</template>
        <template #content>
          <div class="summary-lines">
            <div class="summary-line"><span>Ход</span><strong>{{ store.world?.turn ?? 0 }}</strong></div>
            <div class="summary-line"><span>Следующий ход</span><strong>{{ store.world?.next_turn_in?.toFixed(2) ?? '0.00' }}s</strong></div>
            <div class="summary-line"><span>Стратегия</span><strong>{{ store.runtime?.active_strategy_key ?? 'frontier' }}</strong></div>
            <div class="summary-line"><span>Режим сабмита</span><strong>{{ store.runtime?.submit_mode ?? 'mock' }}</strong></div>
          </div>
        </template>
      </Card>

      <Card class="summary-card">
        <template #title>Оперативное Здоровье</template>
        <template #content>
          <div class="force-badges">
            <Tag severity="info" :value="`Доход ${store.world?.stats.current_income_per_tick ?? 0}/ход`" />
            <Tag severity="success" :value="`Сеть ${store.world?.stats.connected_plantations ?? 0}`" />
            <Tag severity="warn" :value="`Изолировано ${store.world?.stats.isolated_plantations ?? 0}`" />
            <Tag severity="secondary" :value="`Лимит ${store.world?.stats.available_settlement_headroom ?? 0}`" />
            <Tag severity="contrast" :value="`Бобры ${store.world?.stats.visible_beavers ?? 0}`" />
          </div>
          <div class="summary-lines top-gap">
            <div class="summary-line">
              <span>Состояние сети</span>
              <Tag
                :severity="readinessSeverity(store.world?.stats.connected_plantations ?? 0, store.world?.stats.isolated_plantations ?? 0)"
                :value="(store.world?.stats.isolated_plantations ?? 0) > 0 ? 'нужен ремонт сети' : 'стабильна'"
              />
            </div>
            <div class="summary-line"><span>Очки апгрейда</span><strong>{{ store.world?.upgrades.points ?? 0 }}</strong></div>
            <div class="summary-line"><span>Выделено авторов</span><strong>{{ selectedPlantationIds.length }}</strong></div>
          </div>
        </template>
      </Card>

      <InspectorCard :world="store.world" :inspected="inspected" />
    </div>

    <PlanBoard :world="store.world" />
  </section>
</template>
