<script setup lang="ts">
import { computed } from 'vue'

import Card from 'primevue/card'
import Tag from 'primevue/tag'

import type { WorldSnapshot } from '@/types/game'

const props = defineProps<{
  world: WorldSnapshot | null
  inspected: {
    entityKind: string
    entityId?: string
    position: { x: number; y: number }
    own?: boolean
  } | null
}>()

const plantation = computed(() =>
  props.inspected?.entityKind === 'plantation'
    ? props.world?.plantations.find((item) => item.id === props.inspected?.entityId)
    : null,
)

const enemy = computed(() =>
  props.inspected?.entityKind === 'enemy'
    ? props.world?.enemy.find((item) => item.id === props.inspected?.entityId)
    : null,
)

const beaver = computed(() =>
  props.inspected?.entityKind === 'beaver'
    ? props.world?.beavers.find((item) => item.id === props.inspected?.entityId)
    : null,
)

const construction = computed(() =>
  props.inspected?.entityKind === 'construction'
    ? props.world?.constructions.find(
        (item) =>
          item.position.x === props.inspected?.position.x &&
          item.position.y === props.inspected?.position.y,
      )
    : null,
)

const cell = computed(
  () =>
    props.world?.cells.find(
      (item) =>
        item.position.x === props.inspected?.position.x &&
        item.position.y === props.inspected?.position.y,
    ) ?? null,
)

function yesNoSeverity(value: boolean) {
  return value ? 'success' : 'secondary'
}
</script>

<template>
  <Card class="summary-card inspector-card">
    <template #title>Инспектор</template>
    <template #content>
      <div v-if="inspected" class="inspector-stack">
        <div class="summary-line">
          <span>Клетка</span>
          <strong>{{ inspected.position.x }}, {{ inspected.position.y }}</strong>
        </div>
        <div class="summary-line">
          <span>Boosted</span>
          <Tag :severity="yesNoSeverity(inspected.position.x % 7 === 0 && inspected.position.y % 7 === 0)" :value="inspected.position.x % 7 === 0 && inspected.position.y % 7 === 0 ? 'да' : 'нет'" />
        </div>

        <template v-if="plantation">
          <div class="summary-line"><span>Плантация</span><strong>{{ plantation.id }}</strong></div>
          <div class="summary-line"><span>HP</span><strong>{{ plantation.hp }}</strong></div>
          <div class="summary-line"><span>Роль</span><strong>{{ plantation.role }}</strong></div>
          <div class="summary-line"><span>Connected</span><Tag :severity="yesNoSeverity(plantation.connected)" :value="plantation.connected ? 'да' : 'нет'" /></div>
          <div class="summary-line"><span>Immunity until</span><strong>{{ plantation.immunity_until_turn }}</strong></div>
          <div class="summary-line"><span>Terraform</span><strong>{{ plantation.terraform_progress }}%</strong></div>
          <div class="summary-line"><span>До исчезновения</span><strong>{{ plantation.turns_to_completion ?? '-' }}</strong></div>
          <div class="summary-line"><span>Доход/ход</span><strong>{{ plantation.projected_income_per_turn }}</strong></div>
        </template>

        <template v-else-if="enemy">
          <div class="summary-line"><span>Enemy</span><strong>{{ enemy.id }}</strong></div>
          <div class="summary-line"><span>HP</span><strong>{{ enemy.hp }}</strong></div>
        </template>

        <template v-else-if="beaver">
          <div class="summary-line"><span>Логово</span><strong>{{ beaver.id }}</strong></div>
          <div class="summary-line"><span>HP</span><strong>{{ beaver.hp }}</strong></div>
          <div class="summary-line"><span>Threat</span><strong>{{ beaver.threat_score.toFixed(1) }}</strong></div>
        </template>

        <template v-else-if="construction">
          <div class="summary-line"><span>Стройка</span><strong>{{ construction.progress }}/50</strong></div>
          <div class="summary-line"><span>Boosted</span><Tag :severity="yesNoSeverity(construction.is_boosted_cell)" :value="construction.is_boosted_cell ? 'да' : 'нет'" /></div>
          <div class="summary-line"><span>Под угрозой</span><Tag :severity="construction.threatened ? 'warn' : 'secondary'" :value="construction.threatened ? 'да' : 'нет'" /></div>
        </template>

        <template v-if="cell">
          <div class="summary-line"><span>Cell Progress</span><strong>{{ cell.terraformation_progress }}%</strong></div>
          <div class="summary-line"><span>Деградация через</span><strong>{{ cell.turns_until_degradation }}</strong></div>
          <div class="summary-line"><span>Общая ценность</span><strong>{{ cell.total_value }}</strong></div>
          <div class="summary-line"><span>Доход/ход</span><strong>{{ cell.income_per_tick }}</strong></div>
        </template>
      </div>
      <p v-else class="empty-state">Кликни по клетке, плантации, стройке, врагу или логову бобров, чтобы посмотреть детали.</p>
    </template>
  </Card>
</template>
