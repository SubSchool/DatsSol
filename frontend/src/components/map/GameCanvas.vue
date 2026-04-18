<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Application, Container, Graphics, Rectangle, Text } from 'pixi.js'

import type { Coordinate, ManualDirectiveKind, PlannedActionView, WorldSnapshot } from '@/types/game'

const props = defineProps<{
  world: WorldSnapshot | null
  commandMode: boolean
  manualActionKind: ManualDirectiveKind
  selectedPlantationIds: string[]
}>()

const emit = defineEmits<{
  (event: 'selection-change', value: string[]): void
  (event: 'inspect-change', value: { entityKind: string; entityId?: string; position: Coordinate; own?: boolean } | null): void
  (event: 'command-target', value: { entityKind: string; entityId?: string; position: Coordinate; own?: boolean }): void
}>()

const host = ref<HTMLDivElement | null>(null)
const selectedSet = computed(() => new Set(props.selectedPlantationIds))

const cellSize = 28
const boardPadding = 110

let app: Application | null = null
let stage: Container | null = null
let resizeObserver: ResizeObserver | null = null
let dragging = false
let dragOrigin = { x: 0, y: 0 }
let layerOrigin = { x: 0, y: 0 }
let lastDimensions = ''
let hasInitialFit = false

function boardWidth() {
  return (props.world?.width ?? 0) * cellSize + boardPadding * 2
}

function boardHeight() {
  return (props.world?.height ?? 0) * cellSize + boardPadding * 2
}

function cellOrigin(position: Coordinate) {
  return {
    x: boardPadding + position.x * cellSize,
    y: boardPadding + position.y * cellSize,
  }
}

function cellCenter(position: Coordinate) {
  const origin = cellOrigin(position)
  return {
    x: origin.x + cellSize / 2,
    y: origin.y + cellSize / 2,
  }
}

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function toWorldCoordinate(screenX: number, screenY: number): Coordinate | null {
  if (!stage || !props.world) return null
  const localX = (screenX - stage.position.x) / stage.scale.x - boardPadding
  const localY = (screenY - stage.position.y) / stage.scale.y - boardPadding
  const x = Math.floor(localX / cellSize)
  const y = Math.floor(localY / cellSize)
  if (x < 0 || y < 0 || x >= props.world.width || y >= props.world.height) {
    return null
  }
  return { x, y }
}

function toggleSelection(id: string) {
  const next = selectedSet.value.has(id)
    ? props.selectedPlantationIds.filter((item) => item !== id)
    : [...props.selectedPlantationIds, id]
  emit('selection-change', next)
}

function syncSelectionWithWorld() {
  if (!props.world) return
  const alive = new Set(props.world.plantations.map((item) => item.id))
  const next = props.selectedPlantationIds.filter((id) => alive.has(id))
  if (next.length !== props.selectedPlantationIds.length) {
    emit('selection-change', next)
  }
}

function clampWorld() {
  if (!host.value || !stage || !props.world) return
  const scaledWidth = boardWidth() * stage.scale.x
  const scaledHeight = boardHeight() * stage.scale.y
  const minX = Math.min(40, host.value.clientWidth - scaledWidth - 40)
  const minY = Math.min(40, host.value.clientHeight - scaledHeight - 40)

  stage.position.x = clamp(stage.position.x, minX, 40)
  stage.position.y = clamp(stage.position.y, minY, 40)
}

function fitWorld(force = false) {
  if (!host.value || !stage || !props.world) return
  if (hasInitialFit && !force) return

  const width = boardWidth()
  const height = boardHeight()
  const scale = clamp(
    Math.min(host.value.clientWidth / width, host.value.clientHeight / height),
    0.22,
    1.6,
  )
  stage.scale.set(scale)
  stage.position.set(
    (host.value.clientWidth - width * scale) / 2,
    (host.value.clientHeight - height * scale) / 2,
  )
  clampWorld()
  hasInitialFit = true
}

function centerOnPosition(position: Coordinate, preferredScale?: number) {
  if (!host.value || !stage) return
  const center = cellCenter(position)
  const nextScale = clamp(preferredScale ?? Math.max(stage.scale.x, 0.72), 0.18, 2.8)
  stage.scale.set(nextScale)
  stage.position.set(
    host.value.clientWidth / 2 - center.x * nextScale,
    host.value.clientHeight / 2 - center.y * nextScale,
  )
  clampWorld()
}

function focusMainPlantation() {
  const main = props.world?.plantations.find((item) => item.is_main)
  if (!main) return
  centerOnPosition(main.position)
}

function createLabel(text: string, x: number, y: number, size = 12, tint = '#f7f0d8') {
  const label = new Text(text, {
    fontFamily: 'IBM Plex Mono',
    fontSize: size,
    fill: tint,
    fontWeight: '600',
  })
  label.position.set(x, y)
  return label
}

function drawBoardBackdrop(layer: Container) {
  if (!props.world) return

  const backdrop = new Graphics()
  backdrop.beginFill(0x1a120e, 1)
  backdrop.drawRoundedRect(0, 0, boardWidth(), boardHeight(), 36)
  backdrop.endFill()

  backdrop.beginFill(0x3d2416, 1)
  backdrop.drawRoundedRect(boardPadding - 18, boardPadding - 18, props.world.width * cellSize + 36, props.world.height * cellSize + 36, 28)
  backdrop.endFill()

  for (let index = 0; index < 260; index += 1) {
    const x = ((index * 89) % Math.max(1, boardWidth() - 40)) + 20
    const y = ((index * 131) % Math.max(1, boardHeight() - 40)) + 20
    const radius = index % 7 === 0 ? 2.6 : 1.4
    backdrop.beginFill(index % 11 === 0 ? 0xf0c572 : 0xffffff, index % 9 === 0 ? 0.1 : 0.04)
    backdrop.drawCircle(x, y, radius)
    backdrop.endFill()
  }

  layer.addChild(backdrop)

  const grid = new Graphics()
  grid.lineStyle(1, 0xc9a96b, 0.11)
  for (let x = 0; x <= props.world.width; x += 1) {
    const xPos = boardPadding + x * cellSize
    grid.moveTo(xPos, boardPadding)
    grid.lineTo(xPos, boardPadding + props.world.height * cellSize)
  }
  for (let y = 0; y <= props.world.height; y += 1) {
    const yPos = boardPadding + y * cellSize
    grid.moveTo(boardPadding, yPos)
    grid.lineTo(boardPadding + props.world.width * cellSize, yPos)
  }
  layer.addChild(grid)
}

function drawBoostedCells(layer: Container) {
  if (!props.world) return
  const boosted = new Graphics()
  for (let x = 0; x < props.world.width; x += 7) {
    for (let y = 0; y < props.world.height; y += 7) {
      const origin = cellOrigin({ x, y })
      boosted.beginFill(0xf1a743, 0.08)
      boosted.drawRect(origin.x, origin.y, cellSize, cellSize)
      boosted.endFill()
      boosted.lineStyle(1.5, 0xf3bf63, 0.28)
      boosted.drawRect(origin.x + 1, origin.y + 1, cellSize - 2, cellSize - 2)
    }
  }
  layer.addChild(boosted)
}

function drawKnownCells(layer: Container) {
  if (!props.world) return
  const terrain = new Graphics()
  props.world.cells.forEach((cell) => {
    const origin = cellOrigin(cell.position)
    const alpha = 0.08 + cell.terraformation_progress / 180
    const color = cell.is_boosted ? 0x3fc591 : 0x4ea979
    terrain.beginFill(color, alpha)
    terrain.drawRect(origin.x + 1, origin.y + 1, cellSize - 2, cellSize - 2)
    terrain.endFill()
  })
  props.world.mountains.forEach((mountain) => {
    const origin = cellOrigin(mountain)
    terrain.beginFill(0x5d4a3e, 0.86)
    terrain.drawRect(origin.x + 1, origin.y + 1, cellSize - 2, cellSize - 2)
    terrain.endFill()
    terrain.lineStyle(1, 0x8f735d, 0.8)
    terrain.moveTo(origin.x + 4, origin.y + cellSize - 5)
    terrain.lineTo(origin.x + cellSize / 2, origin.y + 4)
    terrain.lineTo(origin.x + cellSize - 4, origin.y + cellSize - 6)
  })
  layer.addChild(terrain)
}

function drawForecasts(layer: Container) {
  if (!props.world) return
  props.world.forecasts.forEach((forecast) => {
    if (forecast.kind !== 'sandstorm' || !forecast.position || forecast.radius === null) {
      return
    }
    const center = cellCenter(forecast.position)
    const radius = (forecast.radius + 0.5) * cellSize
    const storm = new Graphics()
    storm.lineStyle(3, forecast.forming ? 0xf3bf63 : 0xff8a3d, 0.9)
    storm.beginFill(forecast.forming ? 0xf3bf63 : 0xff8a3d, forecast.forming ? 0.08 : 0.12)
    storm.drawRoundedRect(center.x - radius, center.y - radius, radius * 2, radius * 2, 24)
    storm.endFill()
    layer.addChild(storm)

    const label = createLabel(
      `${forecast.id ?? 'storm'} · ${forecast.forming ? 'forming' : 'moving'}`,
      center.x - radius,
      center.y - radius - 20,
      11,
      '#ffd79f',
    )
    layer.addChild(label)
  })
}

function drawNetwork(layer: Container) {
  if (!props.world) return
  const network = new Graphics()
  props.world.network_edges.forEach((edge) => {
    const from = cellCenter(edge.from_position)
    const to = cellCenter(edge.to_position)
    network.lineStyle(edge.kind === 'planned' ? 2 : 3, edge.kind === 'planned' ? 0xb8ffe7 : 0x52d9a6, edge.kind === 'planned' ? 0.4 : 0.76)
    network.moveTo(from.x, from.y)
    network.lineTo(to.x, to.y)
  })
  layer.addChild(network)
}

function actionColor(action: PlannedActionView) {
  if (action.kind === 'repair') return 0x5eead4
  if (action.kind === 'sabotage') return 0xff6b6b
  if (action.kind === 'beaver_attack') return 0xffc86b
  return 0x9af7c3
}

function drawPlans(layer: Container) {
  if (!props.world) return
  const plans = new Graphics()

  props.world.planned_actions.forEach((action) => {
    const [author, exitPosition, target] = action.path.map((item) => cellCenter(item))
    const color = actionColor(action)
    plans.lineStyle(2.5, color, 0.9)
    plans.moveTo(author.x, author.y)
    plans.lineTo(exitPosition.x, exitPosition.y)
    plans.lineTo(target.x, target.y)
    plans.beginFill(color, 0.95)
    plans.drawCircle(target.x, target.y, 4.5)
    plans.endFill()
  })

  props.world.manual_directives.forEach((directive) => {
    if (!directive.target_position) return
    const target = cellCenter(directive.target_position)
    plans.lineStyle(2, 0xff93c8, 0.75)
    plans.drawRect(target.x - 9, target.y - 9, 18, 18)
  })

  layer.addChild(plans)
}

function drawSelectionRanges(layer: Container) {
  if (!props.world) return
  const selectedPlantations = props.world.plantations.filter((item) => selectedSet.value.has(item.id))
  if (selectedPlantations.length === 0) return

  const ranges = new Graphics()
  selectedPlantations.forEach((plantation) => {
    const origin = cellOrigin({
      x: plantation.position.x - props.world!.action_range,
      y: plantation.position.y - props.world!.action_range,
    })
    const size = (props.world!.action_range * 2 + 1) * cellSize
    ranges.lineStyle(2, 0xb2fff0, 0.46)
    ranges.drawRoundedRect(origin.x, origin.y, size, size, 12)
  })
  layer.addChild(ranges)
}

function drawBackgroundInteractionLayer(layer: Container) {
  if (!props.world) return

  const background = new Graphics()
  background.beginFill(0xffffff, 0.001)
  background.drawRect(boardPadding, boardPadding, props.world.width * cellSize, props.world.height * cellSize)
  background.endFill()
  background.interactive = true
  background.cursor = props.commandMode ? 'crosshair' : 'grab'
  background.on('pointertap', (event) => {
    const coordinate = toWorldCoordinate(event.data.global.x, event.data.global.y)
    if (!coordinate) return
    emit('inspect-change', { entityKind: 'cell', position: coordinate })
    if (props.commandMode && props.manualActionKind === 'build') {
      emit('command-target', { entityKind: 'cell', position: coordinate })
    }
  })
  layer.addChild(background)
}

function drawConstructions(layer: Container) {
  if (!props.world) return
  props.world.constructions.forEach((construction) => {
    const origin = cellOrigin(construction.position)
    const node = new Container()
    node.interactive = true
    node.cursor = props.commandMode && props.manualActionKind === 'build' ? 'crosshair' : 'pointer'
    node.hitArea = new Rectangle(origin.x, origin.y, cellSize, cellSize)

    const shape = new Graphics()
    shape.lineStyle(2, construction.threatened ? 0xff8c6b : 0x9de3b9, 0.96)
    shape.beginFill(construction.threatened ? 0x683124 : 0x264235, 0.9)
    shape.drawRoundedRect(origin.x + 3, origin.y + 3, cellSize - 6, cellSize - 6, 8)
    shape.endFill()
    shape.beginFill(0xf7e6a8, 0.9)
    shape.drawRoundedRect(origin.x + 5, origin.y + cellSize - 7, ((cellSize - 10) * construction.progress) / 50, 4, 2)
    shape.endFill()
    node.addChild(shape)
    node.addChild(createLabel(`${construction.progress}`, origin.x + 7, origin.y + 5, 10, '#f8f3dc'))

    node.on('pointertap', () => {
      emit('inspect-change', { entityKind: 'construction', position: construction.position })
      if (props.commandMode && props.manualActionKind === 'build') {
        emit('command-target', { entityKind: 'construction', position: construction.position })
      }
    })
    layer.addChild(node)
  })
}

function drawPlantations(layer: Container) {
  if (!props.world) return
  props.world.plantations.forEach((plantation) => {
    const center = cellCenter(plantation.position)
    const node = new Container()
    node.interactive = true
    node.cursor = props.commandMode ? 'crosshair' : 'pointer'
    node.hitArea = new Rectangle(center.x - cellSize / 2, center.y - cellSize / 2, cellSize, cellSize)

    const body = new Graphics()
    const selected = selectedSet.value.has(plantation.id)
    const stroke = plantation.is_main ? 0xffd48a : plantation.connected ? 0x91f1cf : 0xa19082
    const fill = plantation.is_main ? 0x4a6a4f : plantation.connected ? 0x1b5d49 : 0x463a31
    body.lineStyle(selected ? 4 : 2.4, selected ? 0xffffff : stroke, 1)
    body.beginFill(fill, 0.96)
    body.drawRoundedRect(center.x - 10, center.y - 10, 20, 20, plantation.is_main ? 8 : 6)
    body.endFill()

    if (plantation.is_main) {
      body.lineStyle(2, 0xffd48a, 0.95)
      body.drawCircle(center.x, center.y, 15)
    }
    if (plantation.is_boosted_cell) {
      body.beginFill(0xf4b648, 0.9)
      body.drawCircle(center.x + 9, center.y - 9, 4)
      body.endFill()
    }
    node.addChild(body)

    const hp = new Graphics()
    hp.beginFill(0x140d0a, 0.82)
    hp.drawRoundedRect(center.x - 12, center.y + 11, 24, 4, 2)
    hp.endFill()
    hp.beginFill(plantation.hp < 20 ? 0xff7a5c : 0x8ff3ca, 0.95)
    hp.drawRoundedRect(center.x - 12, center.y + 11, Math.max(4, (24 * plantation.hp) / 50), 4, 2)
    hp.endFill()
    node.addChild(hp)

    if (plantation.is_main || selected) {
      node.addChild(createLabel(plantation.is_main ? 'ЦУ' : plantation.id, center.x - 14, center.y - 28, 10, '#fff5dd'))
    }

    node.on('pointertap', () => {
      emit('inspect-change', {
        entityKind: 'plantation',
        entityId: plantation.id,
        position: plantation.position,
        own: true,
      })
      if (!props.commandMode) {
        toggleSelection(plantation.id)
        return
      }
      if (props.manualActionKind === 'repair' || props.manualActionKind === 'relocate_main') {
        emit('command-target', {
          entityKind: 'plantation',
          entityId: plantation.id,
          position: plantation.position,
          own: true,
        })
      }
    })
    layer.addChild(node)
  })
}

function drawEnemies(layer: Container) {
  if (!props.world) return
  props.world.enemy.forEach((enemy) => {
    const center = cellCenter(enemy.position)
    const node = new Container()
    node.interactive = true
    node.cursor = props.commandMode && props.manualActionKind === 'sabotage' ? 'crosshair' : 'pointer'
    node.hitArea = new Rectangle(center.x - cellSize / 2, center.y - cellSize / 2, cellSize, cellSize)

    const body = new Graphics()
    body.lineStyle(2.5, 0xff8878, 1)
    body.beginFill(0x5f251f, 0.96)
    body.moveTo(center.x, center.y - 12)
    body.lineTo(center.x + 11, center.y + 10)
    body.lineTo(center.x - 11, center.y + 10)
    body.lineTo(center.x, center.y - 12)
    body.endFill()
    node.addChild(body)
    node.addChild(createLabel(`${enemy.hp}`, center.x - 8, center.y + 13, 10, '#ffd7cf'))

    node.on('pointertap', () => {
      emit('inspect-change', {
        entityKind: 'enemy',
        entityId: enemy.id,
        position: enemy.position,
      })
      if (props.commandMode && props.manualActionKind === 'sabotage') {
        emit('command-target', {
          entityKind: 'enemy',
          entityId: enemy.id,
          position: enemy.position,
        })
      }
    })
    layer.addChild(node)
  })
}

function drawBeavers(layer: Container) {
  if (!props.world) return
  props.world.beavers.forEach((beaver) => {
    const center = cellCenter(beaver.position)
    const node = new Container()
    node.interactive = true
    node.cursor = props.commandMode && props.manualActionKind === 'beaver_attack' ? 'crosshair' : 'pointer'
    node.hitArea = new Rectangle(center.x - cellSize / 2, center.y - cellSize / 2, cellSize, cellSize)

    const body = new Graphics()
    body.lineStyle(2.5, 0xf9cb8e, 1)
    body.beginFill(0x6a4828, 0.96)
    body.drawCircle(center.x, center.y, 10)
    body.endFill()
    body.beginFill(0x6a4828, 0.96)
    body.drawCircle(center.x - 6, center.y - 7, 3)
    body.drawCircle(center.x + 6, center.y - 7, 3)
    body.endFill()
    node.addChild(body)
    node.addChild(createLabel(`${beaver.hp}`, center.x - 10, center.y + 13, 10, '#fff0d6'))

    node.on('pointertap', () => {
      emit('inspect-change', {
        entityKind: 'beaver',
        entityId: beaver.id,
        position: beaver.position,
      })
      if (props.commandMode && props.manualActionKind === 'beaver_attack') {
        emit('command-target', {
          entityKind: 'beaver',
          entityId: beaver.id,
          position: beaver.position,
        })
      }
    })
    layer.addChild(node)
  })
}

function drawAxisLabels(layer: Container) {
  if (!props.world) return
  const axis = new Container()
  for (let x = 0; x < props.world.width; x += Math.max(1, Math.floor(props.world.width / 10))) {
    axis.addChild(createLabel(`${x}`, boardPadding + x * cellSize, boardPadding - 28, 11, '#d7be92'))
  }
  for (let y = 0; y < props.world.height; y += Math.max(1, Math.floor(props.world.height / 8))) {
    axis.addChild(createLabel(`${y}`, boardPadding - 34, boardPadding + y * cellSize, 11, '#d7be92'))
  }
  layer.addChild(axis)
}

function renderWorld() {
  if (!stage || !props.world) return
  syncSelectionWithWorld()
  stage.removeChildren()

  const layer = new Container()
  stage.addChild(layer)

  drawBoardBackdrop(layer)
  drawBoostedCells(layer)
  drawKnownCells(layer)
  drawBackgroundInteractionLayer(layer)
  drawForecasts(layer)
  drawNetwork(layer)
  drawSelectionRanges(layer)
  drawPlans(layer)
  drawConstructions(layer)
  drawPlantations(layer)
  drawEnemies(layer)
  drawBeavers(layer)
  drawAxisLabels(layer)
}

function onPointerDown(event: PointerEvent) {
  if (!stage) return
  dragging = true
  dragOrigin = { x: event.clientX, y: event.clientY }
  layerOrigin = { x: stage.position.x, y: stage.position.y }
}

function onPointerMove(event: PointerEvent) {
  if (!stage || !dragging) return
  stage.position.set(
    layerOrigin.x + (event.clientX - dragOrigin.x),
    layerOrigin.y + (event.clientY - dragOrigin.y),
  )
  clampWorld()
}

function onPointerUp() {
  dragging = false
}

function onWheel(event: WheelEvent) {
  if (!host.value || !stage || !props.world) return
  event.preventDefault()
  const rect = host.value.getBoundingClientRect()
  const offsetX = event.clientX - rect.left
  const offsetY = event.clientY - rect.top
  const worldX = (offsetX - stage.position.x) / stage.scale.x
  const worldY = (offsetY - stage.position.y) / stage.scale.y
  const nextScale = clamp(stage.scale.x * (event.deltaY > 0 ? 0.9 : 1.1), 0.18, 2.8)
  stage.scale.set(nextScale)
  stage.position.set(offsetX - worldX * nextScale, offsetY - worldY * nextScale)
  clampWorld()
}

onMounted(() => {
  if (!host.value) return
  app = new Application({
    backgroundAlpha: 0,
    antialias: true,
    resizeTo: host.value,
  })
  host.value.appendChild(app.view as HTMLCanvasElement)
  stage = new Container()
  app.stage.addChild(stage)

  host.value.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  host.value.addEventListener('wheel', onWheel, { passive: false })

  resizeObserver = new ResizeObserver(() => {
    fitWorld(true)
    renderWorld()
  })
  resizeObserver.observe(host.value)

  renderWorld()
  fitWorld(true)
})

watch(
  () => props.world,
  (world) => {
    if (!world) return
    const dimensions = `${world.width}x${world.height}`
    if (dimensions !== lastDimensions) {
      hasInitialFit = false
      lastDimensions = dimensions
    }
    renderWorld()
    fitWorld()
  },
  { deep: true, immediate: true },
)

watch(
  () => `${props.commandMode}-${props.manualActionKind}-${props.selectedPlantationIds.join(',')}`,
  () => {
    renderWorld()
  },
)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  if (host.value) {
    host.value.removeEventListener('pointerdown', onPointerDown)
    host.value.removeEventListener('wheel', onWheel)
  }
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  app?.destroy(true)
  app = null
  stage = null
})

defineExpose({
  fitWorld,
  focusMainPlantation,
})
</script>

<template>
  <div class="canvas-shell">
    <div ref="host" class="canvas-host" />

    <div class="canvas-overlay">
      <div class="overlay-pill">
        <span class="overlay-label">Карта</span>
        <strong class="overlay-value">{{ world?.width ?? 0 }} × {{ world?.height ?? 0 }}</strong>
      </div>
      <div class="overlay-pill">
        <span class="overlay-label">Выделено</span>
        <strong class="overlay-value">{{ selectedPlantationIds.length }}</strong>
      </div>
      <div class="overlay-pill">
        <span class="overlay-label">Режим</span>
        <strong class="overlay-value">{{ commandMode ? 'command' : 'browse' }}</strong>
      </div>
      <div class="overlay-pill">
        <span class="overlay-label">Действие</span>
        <strong class="overlay-value">{{ manualActionKind }}</strong>
      </div>
    </div>

    <div class="canvas-legend">
      <div class="legend-row">
        <span class="legend-swatch boosted" />
        <span>boosted</span>
      </div>
      <div class="legend-row">
        <span class="legend-swatch allied" />
        <span>свои</span>
      </div>
      <div class="legend-row">
        <span class="legend-swatch enemy" />
        <span>враг</span>
      </div>
      <div class="legend-row">
        <span class="legend-swatch beaver" />
        <span>бобры</span>
      </div>
    </div>
  </div>
</template>
