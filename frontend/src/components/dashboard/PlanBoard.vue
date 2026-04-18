<script setup lang="ts">
import Card from 'primevue/card'
import Tag from 'primevue/tag'

import type { WorldSnapshot } from '@/types/game'

defineProps<{
  world: WorldSnapshot | null
}>()

function alertSeverity(level: string) {
  if (level === 'danger') return 'danger'
  if (level === 'warn') return 'warn'
  return 'info'
}

function pipelineSeverity(level: string) {
  if (level === 'error') return 'danger'
  if (level === 'warn') return 'warn'
  return 'success'
}
</script>

<template>
  <div class="plan-board">
    <Card class="summary-card">
      <template #title>Алерты И Хайлайты</template>
      <template #content>
        <div v-if="world?.alerts?.length" class="alert-list">
          <div v-for="alert in world.alerts" :key="alert.title" class="alert-item">
            <Tag :severity="alertSeverity(alert.severity)" :value="alert.title" />
            <p>{{ alert.description }}</p>
          </div>
        </div>
        <p v-else class="empty-state">Активных алертов нет.</p>

        <ul v-if="world?.highlights?.length" class="highlight-list top-gap">
          <li v-for="line in world.highlights" :key="line">{{ line }}</li>
        </ul>
      </template>
    </Card>

    <Card class="summary-card">
      <template #title>Target Ladder</template>
      <template #content>
        <div v-if="world?.recommended_targets?.length" class="target-list">
          <div v-for="target in world.recommended_targets.slice(0, 8)" :key="`${target.position.x}-${target.position.y}`" class="target-item">
            <div>
              <strong>{{ target.position.x }}, {{ target.position.y }}</strong>
              <p>{{ target.reason }}</p>
            </div>
            <div class="target-score">
              <Tag :severity="target.boosted ? 'success' : target.threatened ? 'warn' : 'secondary'" :value="target.kind" />
              <strong>{{ target.score.toFixed(1) }}</strong>
            </div>
          </div>
        </div>
        <p v-else class="empty-state">Кандидаты на расширение появятся после анализа хода.</p>
      </template>
    </Card>

    <Card class="summary-card">
      <template #title>Intent Queue</template>
      <template #content>
        <div v-if="world?.planned_relocate_main" class="compact-item emphasis-item">
          <strong>relocate main</strong>
          <span>
            {{ world.planned_relocate_main.from_position.x }},{{ world.planned_relocate_main.from_position.y }}
            →
            {{ world.planned_relocate_main.to_position.x }},{{ world.planned_relocate_main.to_position.y }}
          </span>
          <small>{{ world.planned_relocate_main.reason }}</small>
        </div>

        <div v-if="world?.intents?.length" class="compact-list top-gap">
          <div v-for="intent in world.intents.slice(0, 10)" :key="intent.id" class="compact-item">
            <strong>{{ intent.kind }}</strong>
            <span>{{ intent.summary }}</span>
            <small>priority {{ intent.priority }} · {{ intent.source }} · {{ intent.reason }}</small>
          </div>
        </div>
        <p v-else class="empty-state">Очередь intents пока пуста.</p>

        <div v-if="world?.planned_actions?.length" class="compact-list top-gap">
          <div v-for="action in world.planned_actions.slice(0, 8)" :key="`${action.author_id}-${action.kind}-${action.target_position.x}-${action.target_position.y}`" class="compact-item">
            <strong>{{ action.kind }}</strong>
            <span>{{ action.author_id }} → {{ action.target_position.x }},{{ action.target_position.y }}</span>
            <small>exit {{ action.exit_position.x }},{{ action.exit_position.y }} · power {{ action.estimated_power }}</small>
          </div>
        </div>
      </template>
    </Card>

    <Card class="summary-card">
      <template #title>Pipeline И Submit</template>
      <template #content>
        <div v-if="world?.last_submission" class="summary-lines">
          <div class="summary-line">
            <span>Последний submit</span>
            <Tag :severity="world.last_submission.accepted ? 'success' : 'danger'" :value="world.last_submission.dry_run ? 'dry-run' : 'sent'" />
          </div>
          <div class="summary-line">
            <span>Ошибки</span>
            <strong>{{ world.last_submission.errors.length }}</strong>
          </div>
        </div>

        <div class="pipeline-list top-gap">
          <div v-for="step in world?.pipeline_steps ?? []" :key="step.name" class="pipeline-item">
            <div class="pipeline-topline">
              <strong>{{ step.name }}</strong>
              <div class="inline-stack">
                <Tag :severity="pipelineSeverity(step.status)" :value="step.status" />
                <span>{{ step.duration_ms.toFixed(2) }} ms</span>
              </div>
            </div>
            <p>{{ step.summary }}</p>
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>
