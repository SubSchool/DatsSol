<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import Button from 'primevue/button'
import Card from 'primevue/card'
import Divider from 'primevue/divider'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Slider from 'primevue/slider'
import Tag from 'primevue/tag'
import ToggleButton from 'primevue/togglebutton'

import { useCommandCenterStore } from '@/stores/commandCenter'
import type { ManualDirectiveKind, RuntimeSnapshot, SubmitMode, WorldSnapshot } from '@/types/game'

const props = defineProps<{
  runtime: RuntimeSnapshot | null
  world: WorldSnapshot | null
  selectedPlantationIds: string[]
  commandMode: boolean
  manualActionKind: ManualDirectiveKind
}>()

const emit = defineEmits<{
  (event: 'update:commandMode', value: boolean): void
  (event: 'update:manualActionKind', value: ManualDirectiveKind): void
}>()

const store = useCommandCenterStore()

const strategyState = reactive({
  selectedStrategy: 'frontier',
  expansion_bias: 0.88,
  support_bias: 0.76,
  boosted_cell_bias: 0.95,
  safety_bias: 0.72,
  beaver_hunt_bias: 0.42,
  sabotage_bias: 0.28,
})

const providerKey = ref<'datssol-mock' | 'datssol-live'>('datssol-mock')
const submitMode = ref<SubmitMode>('mock')
const forcedUpgrade = ref('')

watch(
  () => props.runtime,
  (runtime) => {
    if (!runtime) return
    strategyState.selectedStrategy = runtime.active_strategy_key
    strategyState.expansion_bias = runtime.weights.expansion_bias
    strategyState.support_bias = runtime.weights.support_bias
    strategyState.boosted_cell_bias = runtime.weights.boosted_cell_bias
    strategyState.safety_bias = runtime.weights.safety_bias
    strategyState.beaver_hunt_bias = runtime.weights.beaver_hunt_bias
    strategyState.sabotage_bias = runtime.weights.sabotage_bias
    providerKey.value = runtime.provider as 'datssol-mock' | 'datssol-live'
    submitMode.value = runtime.submit_mode
  },
  { immediate: true },
)

watch(
  () => props.world?.recommended_upgrade?.name,
  (value) => {
    if (value) forcedUpgrade.value = value
  },
  { immediate: true },
)

const commandModeModel = computed({
  get: () => props.commandMode,
  set: (value: boolean) => emit('update:commandMode', value),
})

const manualActionModel = computed({
  get: () => props.manualActionKind,
  set: (value: ManualDirectiveKind) => emit('update:manualActionKind', value),
})

const strategyOptions = computed(
  () =>
    props.runtime?.strategies.map((strategy) => ({
      label: strategy.label,
      value: strategy.key,
    })) ?? [],
)

const providerOptions = [
  { label: 'Mock Sandbox', value: 'datssol-mock' },
  { label: 'Live API', value: 'datssol-live' },
]

const submitModeOptions = [
  { label: 'Mock', value: 'mock' },
  { label: 'Dry Run', value: 'dry-run' },
  { label: 'Live Submit', value: 'live' },
]

const manualActionOptions = [
  { label: 'Стройка', value: 'build' },
  { label: 'Ремонт', value: 'repair' },
  { label: 'Диверсия', value: 'sabotage' },
  { label: 'Бобры', value: 'beaver_attack' },
  { label: 'Перенос ЦУ', value: 'relocate_main' },
]

const upgradeOptions = computed(
  () =>
    props.world?.upgrades.tiers
      .filter((tier) => tier.current < tier.max)
      .map((tier) => ({
        label: `${tier.name} (${tier.current}/${tier.max})`,
        value: tier.name,
      })) ?? [],
)

const commandHint = computed(() => {
  if (props.manualActionKind === 'build') {
    return 'В режиме просмотра можно выделить авторов, затем перейти в command mode и кликнуть по клетке или стройке. Если авторы не выделены, planner выберет их сам.'
  }
  if (props.manualActionKind === 'repair') {
    return 'Сначала выдели плантации-исполнители в browse mode при необходимости. В command mode кликни по своей плантации, которую нужно чинить.'
  }
  if (props.manualActionKind === 'sabotage') {
    return 'В command mode кликни по вражеской плантации. Выделение авторов опционально.'
  }
  if (props.manualActionKind === 'beaver_attack') {
    return 'В command mode кликни по логову бобров. Выделение авторов опционально.'
  }
  return 'В command mode кликни по своей плантации, куда нужно перенести ЦУ. Авторы для переноса не нужны.'
})

async function applyStrategy() {
  await store.setStrategy(strategyState.selectedStrategy)
}

async function applyWeights() {
  await store.updateWeights({
    expansion_bias: strategyState.expansion_bias,
    support_bias: strategyState.support_bias,
    boosted_cell_bias: strategyState.boosted_cell_bias,
    safety_bias: strategyState.safety_bias,
    beaver_hunt_bias: strategyState.beaver_hunt_bias,
    sabotage_bias: strategyState.sabotage_bias,
  })
}

async function applyProvider() {
  await store.setProvider(providerKey.value)
}

async function applySubmitMode() {
  await store.setSubmitMode(submitMode.value)
}

async function forceUpgrade() {
  if (!forcedUpgrade.value) return
  await store.createDirective({
    kind: 'upgrade',
    upgrade_name: forcedUpgrade.value,
    note: `force upgrade ${forcedUpgrade.value}`,
  })
}
</script>

<template>
  <div class="control-panel">
    <Card class="panel-card control-panel-card">
      <template #title>Командный Центр</template>
      <template #content>
        <div class="panel-grid">
          <div class="button-row">
            <Button icon="pi pi-play" label="Старт" @click="store.startRuntime()" />
            <Button icon="pi pi-pause" severity="secondary" label="Стоп" @click="store.stopRuntime()" />
            <Button icon="pi pi-refresh" severity="contrast" label="Рестарт" @click="store.restartRuntime()" />
            <Button icon="pi pi-step-forward" severity="help" label="1 Ход" @click="store.tickOnce()" />
          </div>

          <div class="stat-grid">
            <div class="stat-item">
              <span class="stat-label">Плантации</span>
              <strong class="stat-value">{{ world?.plantations.length ?? 0 }}</strong>
            </div>
            <div class="stat-item">
              <span class="stat-label">Connected</span>
              <strong class="stat-value">{{ world?.stats.connected_plantations ?? 0 }}</strong>
            </div>
            <div class="stat-item">
              <span class="stat-label">Выделено</span>
              <strong class="stat-value">{{ selectedPlantationIds.length }}</strong>
            </div>
            <div class="stat-item">
              <span class="stat-label">Очки апгрейда</span>
              <strong class="stat-value">{{ world?.upgrades.points ?? 0 }}</strong>
            </div>
          </div>

          <Divider />

          <div class="stacked-section">
            <div class="section-header">
              <div>
                <label class="section-label">Провайдер и Сабмит</label>
                <p class="section-subtitle">{{ runtime?.provider_status?.message }}</p>
              </div>
              <Tag :severity="runtime?.provider_status?.ready ? 'success' : 'warn'" :value="runtime?.provider_status?.ready ? 'готов' : 'нужна настройка'" />
            </div>
            <div class="form-row">
              <Select v-model="providerKey" :options="providerOptions" option-label="label" option-value="value" />
              <Button label="Применить" icon="pi pi-send" severity="secondary" @click="applyProvider" />
            </div>
            <div class="form-row">
              <Select v-model="submitMode" :options="submitModeOptions" option-label="label" option-value="value" />
              <Button label="Режим сабмита" icon="pi pi-bolt" severity="secondary" @click="applySubmitMode" />
            </div>
          </div>

          <Divider />

          <div class="stacked-section">
            <label class="section-label">Стратегия</label>
            <SelectButton
              v-model="strategyState.selectedStrategy"
              :options="strategyOptions"
              option-label="label"
              option-value="value"
            />
            <Button label="Переключить стратегию" icon="pi pi-compass" @click="applyStrategy" />
          </div>

          <Divider />

          <div class="stacked-section">
            <div class="section-header">
              <div>
                <label class="section-label">Веса Стратегии</label>
                <p class="section-subtitle">Эти веса правят выбор frontier, плотность сети, охоту на бобров и агрессию.</p>
              </div>
              <Button label="Применить веса" icon="pi pi-sliders-h" severity="secondary" @click="applyWeights" />
            </div>

            <div class="weight-row">
              <span>Экспансия</span>
              <Slider v-model="strategyState.expansion_bias" :min="0" :max="1" :step="0.01" />
              <InputNumber v-model="strategyState.expansion_bias" :min="0" :max="1" :step="0.01" mode="decimal" :min-fraction-digits="2" :max-fraction-digits="2" />
            </div>
            <div class="weight-row">
              <span>Поддержка</span>
              <Slider v-model="strategyState.support_bias" :min="0" :max="1" :step="0.01" />
              <InputNumber v-model="strategyState.support_bias" :min="0" :max="1" :step="0.01" mode="decimal" :min-fraction-digits="2" :max-fraction-digits="2" />
            </div>
            <div class="weight-row">
              <span>Boosted</span>
              <Slider v-model="strategyState.boosted_cell_bias" :min="0" :max="1" :step="0.01" />
              <InputNumber v-model="strategyState.boosted_cell_bias" :min="0" :max="1" :step="0.01" mode="decimal" :min-fraction-digits="2" :max-fraction-digits="2" />
            </div>
            <div class="weight-row">
              <span>Безопасность</span>
              <Slider v-model="strategyState.safety_bias" :min="0" :max="1" :step="0.01" />
              <InputNumber v-model="strategyState.safety_bias" :min="0" :max="1" :step="0.01" mode="decimal" :min-fraction-digits="2" :max-fraction-digits="2" />
            </div>
            <div class="weight-row">
              <span>Бобры</span>
              <Slider v-model="strategyState.beaver_hunt_bias" :min="0" :max="1" :step="0.01" />
              <InputNumber v-model="strategyState.beaver_hunt_bias" :min="0" :max="1" :step="0.01" mode="decimal" :min-fraction-digits="2" :max-fraction-digits="2" />
            </div>
            <div class="weight-row">
              <span>Диверсии</span>
              <Slider v-model="strategyState.sabotage_bias" :min="0" :max="1" :step="0.01" />
              <InputNumber v-model="strategyState.sabotage_bias" :min="0" :max="1" :step="0.01" mode="decimal" :min-fraction-digits="2" :max-fraction-digits="2" />
            </div>
          </div>

          <Divider />

          <div class="stacked-section">
            <div class="section-header">
              <div>
                <label class="section-label">Ручное Управление</label>
                <p class="section-subtitle">Выделение плантаций делается в browse mode. В command mode выбирается цель.</p>
              </div>
              <ToggleButton
                v-model="commandModeModel"
                on-label="Command"
                off-label="Browse"
                on-icon="pi pi-crosshairs"
                off-icon="pi pi-eye"
              />
            </div>
            <SelectButton
              v-model="manualActionModel"
              :options="manualActionOptions"
              option-label="label"
              option-value="value"
            />
            <p class="hint-text">{{ commandHint }}</p>
          </div>

          <Divider />

          <div class="stacked-section">
            <div class="section-header">
              <div>
                <label class="section-label">Форс Апгрейда</label>
                <p class="section-subtitle">{{ world?.recommended_upgrade?.reason ?? 'Пока автоматическая рекомендация не сформирована.' }}</p>
              </div>
              <Tag v-if="world?.recommended_upgrade" severity="info" :value="`auto: ${world.recommended_upgrade.name}`" />
            </div>
            <div class="form-row">
              <Select v-model="forcedUpgrade" :options="upgradeOptions" option-label="label" option-value="value" placeholder="Выбрать апгрейд" />
              <Button label="Поставить в очередь" icon="pi pi-plus" severity="secondary" @click="forceUpgrade" />
            </div>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>
